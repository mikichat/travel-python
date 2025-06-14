from flask import Blueprint, render_template, request, jsonify, current_app, make_response, redirect, url_for, flash
from datetime import datetime
import csv
import io
from database import get_db_connection
from app.utils.errors import APIError
from app.utils.auth import jwt_required
from app.utils.filters import format_date, format_datetime, format_currency
from app.utils.audit import log_schedule_change
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
            raise APIError('제목, 시작일, 종료일, 목적지는 필수입니다.', 400)

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
        
        # 변경 로그 기록
        log_schedule_change(new_schedule_id, 'CREATE', 'all', None, f'일정 생성: {title}', 'admin')
        
        cursor.execute('SELECT * FROM schedules WHERE id = ?', (new_schedule_id,))
        new_schedule = cursor.fetchone()
        conn.close()

        if not new_schedule:
            raise APIError('일정 등록 후 정보를 찾을 수 없습니다.', 500)

        new_schedule_data = dict(new_schedule)
        new_schedule_data['createdAt'] = new_schedule_data.pop('created_at')
        new_schedule_data['updatedAt'] = new_schedule_data.pop('updated_at')
        return jsonify(new_schedule_data), 201
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
            raise APIError('제목, 시작일, 종료일, 목적지는 필수입니다.', 400)

        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().isoformat()

        cursor.execute("""
            UPDATE schedules
            SET title = ?, description = ?, start_date = ?, end_date = ?, destination = ?,
                price = ?, max_people = ?, status = ?, duration = ?, region = ?, 
                meeting_date = ?, meeting_time = ?, meeting_place = ?, manager = ?,
                reservation_maker = ?, reservation_maker_contact = ?, important_docs = ?,
                currency_info = ?, other_items = ?, memo = ?, updated_at = ?
            WHERE id = ?
        """, (
            title, description, start_date, end_date, destination, price, max_people, status,
            duration, region, meeting_date, meeting_time, meeting_place, manager,
            reservation_maker, reservation_maker_contact, important_docs, currency_info,
            other_items, memo, current_time, schedule_id
        ))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            raise APIError('일정을 찾을 수 없습니다.', 404)
        
        # 변경 로그 기록
        log_schedule_change(schedule_id, 'UPDATE', 'all', None, f'일정 수정: {title}', 'admin')
        
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
        
        # 변경 로그 기록
        log_schedule_change(schedule_id, 'DELETE', 'all', None, f'일정 삭제: {schedule_title}', 'admin')
        
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
        writer.writerow(['제목', '시작일', '종료일', '목적지', '가격', '최대인원', '상태', '생성일', '수정일'])
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
            errors['start_date'] = '시작일은 필수입니다.'
        if not end_date:
            errors['end_date'] = '종료일은 필수입니다.'
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
            errors['start_date'] = '시작일은 필수입니다.'
        if not end_date:
            errors['end_date'] = '종료일은 필수입니다.'
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
            
            # 변경 로그 기록
            log_schedule_change(schedule_id, 'UPDATE', 'all', None, f'일정 수정: {title}', 'admin')
            
            conn.close()
            return redirect(url_for('schedule.schedules_page'))
        except Exception as e:
            conn.close()
            print(f'일정 수정 오류: {e}')
            return render_template('edit_schedule.html', schedule=schedule, error='일정 수정 중 오류가 발생했습니다.')
    
    return render_template('edit_schedule.html', schedule=schedule) 