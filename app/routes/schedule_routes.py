from flask import Blueprint, render_template, request, jsonify, current_app, make_response, redirect, url_for, flash
from datetime import datetime
import csv
import io
from database import get_db_connection
from app.utils.errors import APIError
from app.utils.auth import jwt_required
from app.utils.filters import format_date, format_datetime, format_currency
from app.utils.audit import log_schedule_change
from app.utils.excel_utils import export_schedules_to_excel, import_schedules_from_excel
import sqlite3

schedule_bp = Blueprint('schedule', __name__)

# 필터 등록
@schedule_bp.app_template_filter('format_date')
def format_date_filter(date_str):
    return format_date(date_str)

@schedule_bp.app_template_filter('format_datetime')
def format_datetime_filter(datetime_str):
    return format_datetime(datetime_str)

@schedule_bp.app_template_filter('format_currency')
def format_currency_filter(amount):
    return format_currency(amount)

@schedule_bp.route('/')
@jwt_required(current_app)
def schedules_page():
    try:
        # 검색 및 필터링 파라미터 가져오기
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort_by', 'created_at')
        order = request.args.get('order', 'desc')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 기본 쿼리 - 일정과 예약된 슬롯 수를 조인하여 조회
        query = """
            SELECT s.*, COALESCE(SUM(r.number_of_people), 0) as booked_slots
            FROM schedules s
            LEFT JOIN reservations r ON s.id = r.schedule_id AND r.status != 'Cancelled'
        """
        
        # WHERE 조건 구성
        conditions = []
        params = []
        
        if search:
            conditions.append("(s.title LIKE ? OR s.destination LIKE ? OR s.description LIKE ? OR s.region LIKE ?)")
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
        
        # WHERE 절 추가
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        # GROUP BY 추가
        query += " GROUP BY s.id"
        
        # 정렬
        valid_sort_fields = ['destination', 'start_date', 'max_people', 'created_at', 'title', 'price']
        if sort_by not in valid_sort_fields:
            sort_by = 'created_at'
        
        # 정렬 필드 매핑
        sort_field_mapping = {
            'destination': 's.destination',
            'date': 's.start_date',
            'capacity': 's.max_people',
            'created_at': 's.created_at',
            'title': 's.title',
            'price': 's.price'
        }
        
        sort_field = sort_field_mapping.get(sort_by, 's.created_at')
        sort_direction = 'DESC' if order == 'desc' else 'ASC'
        query += f" ORDER BY {sort_field} {sort_direction}"
        
        # 쿼리 실행
        cursor.execute(query, params)
        schedules = cursor.fetchall()
        conn.close()
        
        # sqlite3.Row 객체를 딕셔너리로 변환하고 템플릿에 맞는 필드 매핑
        schedules_list = []
        for schedule in schedules:
            schedule_dict = dict(schedule)
            # 템플릿에서 사용하는 필드들로 매핑
            schedule_dict['date'] = schedule_dict.get('start_date', '')
            schedule_dict['time'] = schedule_dict.get('meeting_time', '')
            schedule_dict['capacity'] = schedule_dict.get('max_people', 0)
            schedule_dict['booked_slots'] = schedule_dict.get('booked_slots', 0)
            schedules_list.append(schedule_dict)
        
        return render_template('schedules.html', schedules=schedules_list, total_schedules=len(schedules_list))
    except Exception as e:
        print(f'일정 목록 조회 오류: {e}')
        return render_template('schedules.html', error='일정 목록을 불러오는 중 오류가 발생했습니다.')

@schedule_bp.route('/api/schedules', methods=['GET'])
@jwt_required(current_app)
def get_schedules():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 일정과 예약된 슬롯 수를 조인하여 조회
        cursor.execute("""
            SELECT s.*, COALESCE(SUM(r.number_of_people), 0) as booked_slots
            FROM schedules s
            LEFT JOIN reservations r ON s.id = r.schedule_id AND r.status != 'Cancelled'
            GROUP BY s.id
            ORDER BY s.created_at DESC
        """)
        schedules = cursor.fetchall()
        conn.close()
        schedules_list = []
        for schedule in schedules:
            schedule_data = dict(schedule)
            schedule_data['createdAt'] = schedule_data.pop('created_at')
            schedule_data['updatedAt'] = schedule_data.pop('updated_at')
            schedule_data['bookedSlots'] = schedule_data.pop('booked_slots', 0)
            schedules_list.append(schedule_data)
        return jsonify(schedules_list)
    except Exception as e:
        print(f'일정 조회 실패: {e}')
        raise APIError('일정 조회 중 오류가 발생했습니다.', 500)

@schedule_bp.route('/api/schedules', methods=['POST'])
@jwt_required(current_app)
def create_schedule():
    try:
        data = request.get_json()
        title = data.get('title')
        description = data.get('description', '')
        start_date = data.get('startDate')
        end_date = data.get('endDate')
        destination = data.get('destination')
        price = data.get('price', 0)
        max_people = data.get('maxPeople', 1)
        status = data.get('status', 'Active')
        duration = data.get('duration', '')
        region = data.get('region', '')
        meeting_date = data.get('meetingDate', '')
        meeting_time = data.get('meetingTime', '')
        meeting_place = data.get('meetingPlace', '')
        manager = data.get('manager', '')
        reservation_maker = data.get('reservationMaker', '')
        reservation_maker_contact = data.get('reservationMakerContact', '')
        important_docs = data.get('importantDocs', '')
        currency_info = data.get('currencyInfo', '')
        other_items = data.get('otherItems', '')
        memo = data.get('memo', '')

        if not title or not start_date or not end_date or not destination:
            raise APIError('제목, 출발일, 도착일, 목적지는 필수입니다.', 400)

        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO schedules (title, description, start_date, end_date, destination, price, max_people, status, duration, region, meeting_date, meeting_time, meeting_place, manager, reservation_maker, reservation_maker_contact, important_docs, currency_info, other_items, memo, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title, description, start_date, end_date, destination, price, max_people, status,
            duration, region, meeting_date, meeting_time, meeting_place, manager, 
            reservation_maker, reservation_maker_contact, important_docs, currency_info,
            other_items, memo, current_time, current_time
        ))
        conn.commit()

        new_schedule_id = cursor.lastrowid
        
        cursor.execute('SELECT * FROM schedules WHERE id = ?', (new_schedule_id,))
        new_schedule = cursor.fetchone()
        conn.close()
        flash('일정이 성공적으로 추가되었습니다.', 'success')
        return jsonify(dict(new_schedule)), 201
    except APIError:
        raise
    except Exception as e:
        print(f'일정 등록 오류: {e}')
        raise APIError('일정 등록 중 오류가 발생했습니다.', 500)

@schedule_bp.route('/api/schedules/<int:schedule_id>', methods=['GET'])
@jwt_required(current_app)
def get_schedule_by_id(schedule_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,))
        schedule = cursor.fetchone()
        conn.close()
        if not schedule:
            raise APIError('일정을 찾을 수 없습니다.', 404)
        schedule_data = dict(schedule)
        schedule_data['createdAt'] = schedule_data.pop('created_at')
        schedule_data['updatedAt'] = schedule_data.pop('updated_at')
        return jsonify(schedule_data)
    except APIError:
        raise
    except Exception as e:
        print(f'일정 조회 실패: {e}')
        raise APIError('일정 조회 중 오류가 발생했습니다.', 500)

@schedule_bp.route('/api/schedules/<int:schedule_id>', methods=['PUT'])
@jwt_required(current_app)
def update_schedule(schedule_id):
    try:
        data = request.get_json()
        title = data.get('title')
        description = data.get('description', '')
        start_date = data.get('startDate')
        end_date = data.get('endDate')
        destination = data.get('destination')
        price = data.get('price', 0)
        max_people = data.get('maxPeople', 1)
        status = data.get('status', 'Active')
        duration = data.get('duration', '')
        region = data.get('region', '')
        meeting_date = data.get('meetingDate', '')
        meeting_time = data.get('meetingTime', '')
        meeting_place = data.get('meetingPlace', '')
        manager = data.get('manager', '')
        reservation_maker = data.get('reservationMaker', '')
        reservation_maker_contact = data.get('reservationMakerContact', '')
        important_docs = data.get('importantDocs', '')
        currency_info = data.get('currencyInfo', '')
        other_items = data.get('otherItems', '')
        memo = data.get('memo', '')

        if not title or not start_date or not end_date or not destination:
            raise APIError('제목, 출발일, 도착일, 목적지는 필수입니다.', 400)

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 기존 일정 정보 조회
        cursor.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,))
        old_schedule = cursor.fetchone()
        
        if not old_schedule:
            conn.close()
            raise APIError('일정을 찾을 수 없습니다.', 404)
        
        current_time = datetime.now().isoformat()

        # 변경된 필드 추적
        changes = []
        if old_schedule['title'] != title:
            changes.append(f"제목: {old_schedule['title']} → {title}")
            log_schedule_change(schedule_id, 'UPDATE', 'title', old_schedule['title'], title, 'admin')
        if old_schedule['description'] != description:
            changes.append(f"설명: {old_schedule['description']} → {description}")
            log_schedule_change(schedule_id, 'UPDATE', 'description', old_schedule['description'], description, 'admin')
        if old_schedule['start_date'] != start_date:
            changes.append(f"출발일: {old_schedule['start_date']} → {start_date}")
            log_schedule_change(schedule_id, 'UPDATE', 'start_date', old_schedule['start_date'], start_date, 'admin')
        if old_schedule['end_date'] != end_date:
            changes.append(f"도착일: {old_schedule['end_date']} → {end_date}")
            log_schedule_change(schedule_id, 'UPDATE', 'end_date', old_schedule['end_date'], end_date, 'admin')
        if old_schedule['destination'] != destination:
            changes.append(f"목적지: {old_schedule['destination']} → {destination}")
            log_schedule_change(schedule_id, 'UPDATE', 'destination', old_schedule['destination'], destination, 'admin')
        if old_schedule['price'] != price:
            changes.append(f"가격: {old_schedule['price']} → {price}")
            log_schedule_change(schedule_id, 'UPDATE', 'price', str(old_schedule['price']), str(price), 'admin')
        if old_schedule['max_people'] != max_people:
            changes.append(f"최대인원: {old_schedule['max_people']} → {max_people}")
            log_schedule_change(schedule_id, 'UPDATE', 'max_people', str(old_schedule['max_people']), str(max_people), 'admin')
        if old_schedule['status'] != status:
            changes.append(f"상태: {old_schedule['status']} → {status}")
            log_schedule_change(schedule_id, 'UPDATE', 'status', old_schedule['status'], status, 'admin')
        if old_schedule['duration'] != duration:
            changes.append(f"기간: {old_schedule['duration']} → {duration}")
            log_schedule_change(schedule_id, 'UPDATE', 'duration', old_schedule['duration'], duration, 'admin')
        if old_schedule['region'] != region:
            changes.append(f"지역: {old_schedule['region']} → {region}")
            log_schedule_change(schedule_id, 'UPDATE', 'region', old_schedule['region'], region, 'admin')
        if old_schedule['meeting_date'] != meeting_date:
            changes.append(f"모임일: {old_schedule['meeting_date']} → {meeting_date}")
            log_schedule_change(schedule_id, 'UPDATE', 'meeting_date', old_schedule['meeting_date'], meeting_date, 'admin')
        if old_schedule['meeting_time'] != meeting_time:
            changes.append(f"모임시간: {old_schedule['meeting_time']} → {meeting_time}")
            log_schedule_change(schedule_id, 'UPDATE', 'meeting_time', old_schedule['meeting_time'], meeting_time, 'admin')
        if old_schedule['meeting_place'] != meeting_place:
            changes.append(f"모임장소: {old_schedule['meeting_place']} → {meeting_place}")
            log_schedule_change(schedule_id, 'UPDATE', 'meeting_place', old_schedule['meeting_place'], meeting_place, 'admin')
        if old_schedule['manager'] != manager:
            changes.append(f"담당자: {old_schedule['manager']} → {manager}")
            log_schedule_change(schedule_id, 'UPDATE', 'manager', old_schedule['manager'], manager, 'admin')
        if old_schedule['reservation_maker'] != reservation_maker:
            changes.append(f"예약담당자: {old_schedule['reservation_maker']} → {reservation_maker}")
            log_schedule_change(schedule_id, 'UPDATE', 'reservation_maker', old_schedule['reservation_maker'], reservation_maker, 'admin')
        if old_schedule['reservation_maker_contact'] != reservation_maker_contact:
            changes.append(f"예약담당자연락처: {old_schedule['reservation_maker_contact']} → {reservation_maker_contact}")
            log_schedule_change(schedule_id, 'UPDATE', 'reservation_maker_contact', old_schedule['reservation_maker_contact'], reservation_maker_contact, 'admin')
        if old_schedule['important_docs'] != important_docs:
            changes.append(f"중요문서: {old_schedule['important_docs']} → {important_docs}")
            log_schedule_change(schedule_id, 'UPDATE', 'important_docs', old_schedule['important_docs'], important_docs, 'admin')
        if old_schedule['currency_info'] != currency_info:
            changes.append(f"통화정보: {old_schedule['currency_info']} → {currency_info}")
            log_schedule_change(schedule_id, 'UPDATE', 'currency_info', old_schedule['currency_info'], currency_info, 'admin')
        if old_schedule['other_items'] != other_items:
            changes.append(f"기타항목: {old_schedule['other_items']} → {other_items}")
            log_schedule_change(schedule_id, 'UPDATE', 'other_items', old_schedule['other_items'], other_items, 'admin')
        if old_schedule['memo'] != memo:
            changes.append(f"메모: {old_schedule['memo']} → {memo}")
            log_schedule_change(schedule_id, 'UPDATE', 'memo', old_schedule['memo'], memo, 'admin')
        
        cursor.execute("""
            UPDATE schedules
            SET title = ?, description = ?, start_date = ?, end_date = ?, destination = ?,
                price = ?, max_people = ?, status = ?, duration = ?, region = ?, 
                meeting_date = ?, meeting_time = ?, meeting_place = ?, manager = ?,
                reservation_maker = ?, reservation_maker_contact = ?, important_docs = ?,
                currency_info = ?, other_items = ?, memo = ?, updated_at = ?
            WHERE id = ?
        """, (
            title, description, start_date, end_date, destination, price, max_people,
            status, duration, region, meeting_date, meeting_time, meeting_place,
            manager, reservation_maker, reservation_maker_contact, important_docs,
            currency_info, other_items, memo, current_time, schedule_id
        ))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            raise APIError('일정을 찾을 수 없습니다.', 404)
        
        cursor.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,))
        updated_schedule = cursor.fetchone()
        conn.close()
        updated_schedule_data = dict(updated_schedule)
        updated_schedule_data['createdAt'] = updated_schedule_data.pop('created_at')
        updated_schedule_data['updatedAt'] = updated_schedule_data.pop('updated_at')
        return jsonify(updated_schedule_data)
    except APIError:
        raise
    except Exception as e:
        print(f'일정 수정 오류: {e}')
        raise APIError('일정 수정 중 오류가 발생했습니다.', 500)

@schedule_bp.route('/api/schedules/<int:schedule_id>', methods=['DELETE'])
@jwt_required(current_app)
def delete_schedule(schedule_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM reservations WHERE schedule_id = ?', (schedule_id,))
        reservations_count = cursor.fetchone()[0]
        if reservations_count > 0:
            conn.close()
            raise APIError('예약이 있는 일정은 삭제할 수 없습니다.', 400)
        
        # 삭제 전 일정 정보 조회
        cursor.execute('SELECT title FROM schedules WHERE id = ?', (schedule_id,))
        schedule = cursor.fetchone()
        schedule_title = schedule[0] if schedule else 'Unknown'
        
        cursor.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            raise APIError('일정을 찾을 수 없습니다.', 404)
        
        conn.close()
        return jsonify({'message': '일정이 삭제되었습니다.'})
    except APIError:
        raise
    except Exception as e:
        print(f'일정 삭제 오류: {e}')
        raise APIError('일정 삭제 중 오류가 발생했습니다.', 500)

@schedule_bp.route('/delete/<int:schedule_id>', methods=['POST'])
@jwt_required(current_app)
def delete_schedule_page(schedule_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM reservations WHERE schedule_id = ?', (schedule_id,))
        reservations_count = cursor.fetchone()[0]
        if reservations_count > 0:
            conn.close()
            return render_template('schedules.html', error='예약이 있는 일정은 삭제할 수 없습니다.')
        cursor.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('schedule.schedules_page'))
    except Exception as e:
        print(f'일정 삭제 오류: {e}')
        return render_template('schedules.html', error='일정 삭제 중 오류가 발생했습니다.')

@schedule_bp.route('/export-csv')
@jwt_required(current_app)
def export_schedules_csv():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT title, start_date, end_date, destination, price, max_people, status, created_at, updated_at FROM schedules ORDER BY created_at DESC')
        schedules = cursor.fetchall()
        conn.close()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['제목', '출발일', '도착일', '목적지', '가격', '최대인원', '상태', '생성일', '수정일'])
        for schedule in schedules:
            writer.writerow([
                schedule['title'],
                schedule['start_date'],
                schedule['end_date'],
                schedule['destination'],
                schedule['price'],
                schedule['max_people'],
                schedule['status'],
                schedule['created_at'],
                schedule['updated_at']
            ])
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = 'attachment; filename=schedules.csv'
        return response
    except Exception as e:
        print(f'CSV 내보내기 오류: {e}')
        raise APIError('CSV 내보내기 중 오류가 발생했습니다.', 500)

@schedule_bp.route('/export-excel')
@jwt_required(current_app)
def export_schedules_excel():
    """일정 데이터를 엑셀 파일로 내보내기"""
    try:
        excel_data = export_schedules_to_excel()
        
        response = make_response(excel_data)
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=schedules.xlsx'
        
        return response
    except Exception as e:
        print(f'일정 엑셀 내보내기 오류: {e}')
        flash('엑셀 파일 생성 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('schedule.schedules_page'))

@schedule_bp.route('/import-excel', methods=['GET', 'POST'])
@jwt_required(current_app)
def import_schedules_excel():
    """엑셀 파일에서 일정 데이터 가져오기"""
    if request.method == 'GET':
        return render_template('import_schedules_excel.html')
    
    try:
        if 'file' not in request.files:
            flash('파일을 선택해주세요.', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('파일을 선택해주세요.', 'error')
            return redirect(request.url)
        
        if not file.filename.endswith(('.xlsx', '.xls')):
            flash('엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.', 'error')
            return redirect(request.url)
        
        # 파일 내용 읽기
        file_content = file.read()
        
        # 엑셀 데이터 가져오기
        result = import_schedules_from_excel(file_content)
        
        if result['success_count'] > 0:
            flash(f'{result["success_count"]}개의 일정이 성공적으로 추가되었습니다.', 'success')
        
        if result['error_count'] > 0:
            flash(f'{result["error_count"]}개의 오류가 발생했습니다.', 'error')
            for error in result['errors']:
                flash(error, 'error')
        
        return redirect(url_for('schedule.schedules_page'))
        
    except Exception as e:
        print(f'일정 엑셀 가져오기 오류: {e}')
        flash('엑셀 파일 처리 중 오류가 발생했습니다.', 'error')
        return redirect(request.url)

@schedule_bp.route('/create', methods=['GET', 'POST'])
@jwt_required(current_app)
def create_schedule_page():
    if request.method == 'POST':
        # 폼 데이터 가져오기
        title = request.form.get('title')
        description = request.form.get('description', '')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        destination = request.form.get('destination')
        price = request.form.get('price', 0)
        max_people = request.form.get('max_people', 1)
        status = request.form.get('status', 'Active')
        duration = request.form.get('duration', '')
        region = request.form.get('region', '')
        meeting_date = request.form.get('meeting_date', '')
        meeting_time = request.form.get('meeting_time', '')
        meeting_place = request.form.get('meeting_place', '')
        manager = request.form.get('manager', '')
        reservation_maker = request.form.get('reservation_maker', '')
        reservation_maker_contact = request.form.get('reservation_maker_contact', '')
        important_docs = request.form.get('important_docs', '')
        currency_info = request.form.get('currency_info', '')
        other_items = request.form.get('other_items', '')
        memo = request.form.get('memo', '')

        # 필수 필드 검증
        errors = {}
        if not title:
            errors['title'] = '일정 제목은 필수입니다.'
        if not start_date:
            errors['start_date'] = '출발일은 필수입니다.'
        if not end_date:
            errors['end_date'] = '도착일은 필수입니다.'
        if not destination:
            errors['destination'] = '목적지는 필수입니다.'

        if errors:
            return render_template('create_schedule.html', errors=errors, error='필수 정보를 모두 입력해주세요.')

        # 가격과 최대 인원 숫자 변환
        try:
            price = float(price) if price else 0
            max_people = int(max_people) if max_people else 1
        except ValueError:
            return render_template('create_schedule.html', error='가격과 최대 인원은 숫자로 입력해주세요.')

        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().isoformat()
        
        try:
            cursor.execute("""
                INSERT INTO schedules (
                    title, description, start_date, end_date, destination, price, max_people, 
                    status, duration, region, meeting_date, meeting_time, meeting_place, 
                    manager, reservation_maker, reservation_maker_contact, important_docs, 
                    currency_info, other_items, memo, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title, description, start_date, end_date, destination, price, max_people,
                status, duration, region, meeting_date, meeting_time, meeting_place,
                manager, reservation_maker, reservation_maker_contact, important_docs,
                currency_info, other_items, memo, current_time, current_time
            ))
            conn.commit()
            
            conn.close()
            flash('일정이 성공적으로 추가되었습니다.', 'success')
            return redirect(url_for('schedule.schedules_page'))
        except Exception as e:
            conn.close()
            print(f'일정 등록 오류: {e}')
            return render_template('create_schedule.html', error='일정 등록 중 오류가 발생했습니다.')
    
    return render_template('create_schedule.html')

@schedule_bp.route('/<int:schedule_id>', methods=['GET', 'POST'])
@jwt_required(current_app)
def edit_schedule_page(schedule_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,))
    schedule = cursor.fetchone()
    conn.close()
    
    if not schedule:
        return render_template('edit_schedule.html', schedule=None, error='일정을 찾을 수 없습니다.')
    
    if request.method == 'POST':
        # 폼 데이터 가져오기
        title = request.form.get('title')
        description = request.form.get('description', '')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        destination = request.form.get('destination')
        price = request.form.get('price', 0)
        max_people = request.form.get('max_people', 1)
        status = request.form.get('status', 'Active')
        duration = request.form.get('duration', '')
        region = request.form.get('region', '')
        meeting_date = request.form.get('meeting_date', '')
        meeting_time = request.form.get('meeting_time', '')
        meeting_place = request.form.get('meeting_place', '')
        manager = request.form.get('manager', '')
        reservation_maker = request.form.get('reservation_maker', '')
        reservation_maker_contact = request.form.get('reservation_maker_contact', '')
        important_docs = request.form.get('important_docs', '')
        currency_info = request.form.get('currency_info', '')
        other_items = request.form.get('other_items', '')
        memo = request.form.get('memo', '')

        # 필수 필드 검증
        errors = {}
        if not title:
            errors['title'] = '일정 제목은 필수입니다.'
        if not start_date:
            errors['start_date'] = '출발일은 필수입니다.'
        if not end_date:
            errors['end_date'] = '도착일은 필수입니다.'
        if not destination:
            errors['destination'] = '목적지는 필수입니다.'

        if errors:
            return render_template('edit_schedule.html', schedule=schedule, errors=errors, error='필수 정보를 모두 입력해주세요.')

        # 가격과 최대 인원 숫자 변환
        try:
            price = float(price) if price else 0
            max_people = int(max_people) if max_people else 1
        except ValueError:
            return render_template('edit_schedule.html', schedule=schedule, error='가격과 최대 인원은 숫자로 입력해주세요.')

        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().isoformat()
        
        try:
            # 변경된 필드 추적
            changes = []
            if schedule['title'] != title:
                changes.append(f"제목: {schedule['title']} → {title}")
                log_schedule_change(schedule_id, 'UPDATE', 'title', schedule['title'], title, 'admin')
            if schedule['description'] != description:
                changes.append(f"설명: {schedule['description']} → {description}")
                log_schedule_change(schedule_id, 'UPDATE', 'description', schedule['description'], description, 'admin')
            if schedule['start_date'] != start_date:
                changes.append(f"출발일: {schedule['start_date']} → {start_date}")
                log_schedule_change(schedule_id, 'UPDATE', 'start_date', schedule['start_date'], start_date, 'admin')
            if schedule['end_date'] != end_date:
                changes.append(f"도착일: {schedule['end_date']} → {end_date}")
                log_schedule_change(schedule_id, 'UPDATE', 'end_date', schedule['end_date'], end_date, 'admin')
            if schedule['destination'] != destination:
                changes.append(f"목적지: {schedule['destination']} → {destination}")
                log_schedule_change(schedule_id, 'UPDATE', 'destination', schedule['destination'], destination, 'admin')
            if schedule['price'] != price:
                changes.append(f"가격: {schedule['price']} → {price}")
                log_schedule_change(schedule_id, 'UPDATE', 'price', str(schedule['price']), str(price), 'admin')
            if schedule['max_people'] != max_people:
                changes.append(f"최대인원: {schedule['max_people']} → {max_people}")
                log_schedule_change(schedule_id, 'UPDATE', 'max_people', str(schedule['max_people']), str(max_people), 'admin')
            if schedule['status'] != status:
                changes.append(f"상태: {schedule['status']} → {status}")
                log_schedule_change(schedule_id, 'UPDATE', 'status', schedule['status'], status, 'admin')
            if schedule['duration'] != duration:
                changes.append(f"기간: {schedule['duration']} → {duration}")
                log_schedule_change(schedule_id, 'UPDATE', 'duration', schedule['duration'], duration, 'admin')
            if schedule['region'] != region:
                changes.append(f"지역: {schedule['region']} → {region}")
                log_schedule_change(schedule_id, 'UPDATE', 'region', schedule['region'], region, 'admin')
            if schedule['meeting_date'] != meeting_date:
                changes.append(f"모임일: {schedule['meeting_date']} → {meeting_date}")
                log_schedule_change(schedule_id, 'UPDATE', 'meeting_date', schedule['meeting_date'], meeting_date, 'admin')
            if schedule['meeting_time'] != meeting_time:
                changes.append(f"모임시간: {schedule['meeting_time']} → {meeting_time}")
                log_schedule_change(schedule_id, 'UPDATE', 'meeting_time', schedule['meeting_time'], meeting_time, 'admin')
            if schedule['meeting_place'] != meeting_place:
                changes.append(f"모임장소: {schedule['meeting_place']} → {meeting_place}")
                log_schedule_change(schedule_id, 'UPDATE', 'meeting_place', schedule['meeting_place'], meeting_place, 'admin')
            if schedule['manager'] != manager:
                changes.append(f"담당자: {schedule['manager']} → {manager}")
                log_schedule_change(schedule_id, 'UPDATE', 'manager', schedule['manager'], manager, 'admin')
            if schedule['reservation_maker'] != reservation_maker:
                changes.append(f"예약담당자: {schedule['reservation_maker']} → {reservation_maker}")
                log_schedule_change(schedule_id, 'UPDATE', 'reservation_maker', schedule['reservation_maker'], reservation_maker, 'admin')
            if schedule['reservation_maker_contact'] != reservation_maker_contact:
                changes.append(f"예약담당자연락처: {schedule['reservation_maker_contact']} → {reservation_maker_contact}")
                log_schedule_change(schedule_id, 'UPDATE', 'reservation_maker_contact', schedule['reservation_maker_contact'], reservation_maker_contact, 'admin')
            if schedule['important_docs'] != important_docs:
                changes.append(f"중요문서: {schedule['important_docs']} → {important_docs}")
                log_schedule_change(schedule_id, 'UPDATE', 'important_docs', schedule['important_docs'], important_docs, 'admin')
            if schedule['currency_info'] != currency_info:
                changes.append(f"통화정보: {schedule['currency_info']} → {currency_info}")
                log_schedule_change(schedule_id, 'UPDATE', 'currency_info', schedule['currency_info'], currency_info, 'admin')
            if schedule['other_items'] != other_items:
                changes.append(f"기타항목: {schedule['other_items']} → {other_items}")
                log_schedule_change(schedule_id, 'UPDATE', 'other_items', schedule['other_items'], other_items, 'admin')
            if schedule['memo'] != memo:
                changes.append(f"메모: {schedule['memo']} → {memo}")
                log_schedule_change(schedule_id, 'UPDATE', 'memo', schedule['memo'], memo, 'admin')
            
            cursor.execute("""
                UPDATE schedules
                SET title = ?, description = ?, start_date = ?, end_date = ?, destination = ?,
                    price = ?, max_people = ?, status = ?, duration = ?, region = ?, 
                    meeting_date = ?, meeting_time = ?, meeting_place = ?, manager = ?,
                    reservation_maker = ?, reservation_maker_contact = ?, important_docs = ?,
                    currency_info = ?, other_items = ?, memo = ?, updated_at = ?
                WHERE id = ?
            """, (
                title, description, start_date, end_date, destination, price, max_people,
                status, duration, region, meeting_date, meeting_time, meeting_place,
                manager, reservation_maker, reservation_maker_contact, important_docs,
                currency_info, other_items, memo, current_time, schedule_id
            ))
            conn.commit()
            
            conn.close()
            flash('일정이 성공적으로 수정되었습니다.', 'success')
            return redirect(url_for('schedule.schedules_page'))
        except Exception as e:
            conn.close()
            print(f'일정 수정 오류: {e}')
            return render_template('edit_schedule.html', schedule=schedule, error='일정 수정 중 오류가 발생했습니다.')
    
    return render_template('edit_schedule.html', schedule=schedule) 