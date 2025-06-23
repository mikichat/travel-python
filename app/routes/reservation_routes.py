from flask import Blueprint, render_template, request, jsonify, current_app, make_response, redirect, url_for, flash, g
from datetime import datetime
import csv
import io
from database import get_db_connection
from app.utils.errors import APIError
from app.utils.auth import jwt_required
from app.utils.filters import format_date, format_datetime, format_currency, get_status_color, get_status_text
from app.utils.audit import log_reservation_change
from app.utils.excel_utils import export_reservations_to_excel, import_reservations_from_excel
import sqlite3
from app.utils import ValidationError
from app.utils import generate_reservation_code
import qrcode
import base64
from config import Config

reservation_bp = Blueprint('reservation', __name__)

# 예약 상태 순서 정의
STATUS_ORDER = {
    "REQUESTED": 1,
    "IN_PROGRESS": 2,
    "PENDING_DEPOSIT": 3,
    "CONTRACT_CONFIRMED": 4,
    "FULLY_PAID": 5,
    "COMPLETED": 6,
    "VIP_CUSTOMER": 7,
    "COMPLAINT": 8,
    "PROCESSED": 9
}

# 필터 등록
@reservation_bp.app_template_filter('format_date')
def format_date_filter(date_str):
    return format_date(date_str)

@reservation_bp.app_template_filter('format_datetime')
def format_datetime_filter(datetime_str):
    return format_datetime(datetime_str)

@reservation_bp.app_template_filter('format_currency')
def format_currency_filter(amount):
    return format_currency(amount)

@reservation_bp.app_template_filter('get_status_color')
def get_status_color_filter(status):
    return get_status_color(status)

@reservation_bp.app_template_filter('get_status_text')
def get_status_text_filter(status):
    return get_status_text(status)

@reservation_bp.route('/')
@jwt_required(current_app)
def reservations_page():
    try:
        # 검색 파라미터 가져오기
        customer_name = request.args.get('customer_name', '').strip()
        schedule_title = request.args.get('schedule_title', '').strip()
        status_filter = request.args.get('status', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        conn = get_db_connection()
        cursor = conn.cursor()

        # 전체 예약 수 가져오기
        count_query = """
            SELECT COUNT(*)
            FROM reservations r
            LEFT JOIN customers c ON r.customer_id = c.id
            LEFT JOIN schedules s ON r.schedule_id = s.id
        """
        count_conditions = []
        count_params = []

        if customer_name:
            count_conditions.append("c.name LIKE ?")
            count_params.append(f"%{customer_name}%")
        
        if schedule_title:
            count_conditions.append("s.title LIKE ?")
            count_params.append(f"%{schedule_title}%")
        
        if status_filter:
            count_conditions.append("r.status = ?")
            count_params.append(status_filter)
        
        if date_from:
            count_conditions.append("s.start_date >= ?")
            count_params.append(date_from)
        
        if date_to:
            count_conditions.append("s.start_date <= ?")
            count_params.append(date_to)

        if count_conditions:
            count_query += " WHERE " + " AND ".join(count_conditions) + " AND r.deleted_at IS NULL"
        else:
            count_query += " WHERE r.deleted_at IS NULL"
        
        cursor.execute(count_query, count_params)
        total_reservations_count = cursor.fetchone()[0]

        # 총 페이지 수 계산
        total_pages = (total_reservations_count + per_page - 1) // per_page
        if page < 1: page = 1
        if page > total_pages and total_pages > 0: page = total_pages

        offset = (page - 1) * per_page

        # 기본 쿼리 - schedules 테이블의 start_date, end_date도 조인
        query = """
            SELECT r.*, c.name as customer_name, s.title as schedule_title, 
                   s.start_date as travel_start_date, s.end_date as travel_end_date
            FROM reservations r
            LEFT JOIN customers c ON r.customer_id = c.id
            LEFT JOIN schedules s ON r.schedule_id = s.id
        """
        
        # WHERE 조건 구성
        conditions = []
        params = []
        
        if customer_name:
            conditions.append("c.name LIKE ?")
            params.append(f"%{customer_name}%")
        
        if schedule_title:
            conditions.append("s.title LIKE ?")
            params.append(f"%{schedule_title}%")
        
        if status_filter:
            conditions.append("r.status = ?")
            params.append(status_filter)
        
        if date_from:
            conditions.append("s.start_date >= ?")
            params.append(date_from)
        
        if date_to:
            conditions.append("s.start_date <= ?")
            params.append(date_to)
        
        # WHERE 절 추가
        if conditions:
            query += " WHERE " + " AND ".join(conditions) + " AND r.deleted_at IS NULL"
        
        # 정렬 및 LIMIT/OFFSET
        query += " ORDER BY r.created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        # 쿼리 실행
        cursor.execute(query, params)
        reservations = cursor.fetchall()
        conn.close()
        
        # sqlite3.Row 객체를 딕셔너리로 변환
        reservations_list = []
        for reservation in reservations:
            reservation_dict = dict(reservation)
            # 템플릿에서 사용하는 필드들로 매핑
            reservation_dict['customerName'] = reservation_dict.get('customer_name', '알 수 없음')
            reservation_dict['scheduleTitle'] = reservation_dict.get('schedule_title', '알 수 없음')
            reservation_dict['bookingDate'] = reservation_dict.get('booking_date', '')
            reservation_dict['numberOfPeople'] = reservation_dict.get('number_of_people', 0)
            reservation_dict['totalPrice'] = reservation_dict.get('total_price', 0)
            # 여행 날짜 추가
            reservation_dict['travelStartDate'] = reservation_dict.get('travel_start_date', '')
            reservation_dict['travelEndDate'] = reservation_dict.get('travel_end_date', '')
            reservations_list.append(reservation_dict)
        
        return render_template('reservations.html', 
                               reservations=reservations_list,
                               total_reservations_count=total_reservations_count,
                               customer_name=customer_name,
                               schedule_title=schedule_title,
                               status_filter=status_filter,
                               date_from=date_from,
                               date_to=date_to,
                               page=page,
                               per_page=per_page,
                               total_pages=total_pages)
    except Exception as e:
        print(f'예약 목록 조회 오류: {e}')
        return render_template('reservations.html', error='예약 목록을 불러오는 중 오류가 발생했습니다.')

@reservation_bp.route('/api/reservations/paginated', methods=['GET'])
@jwt_required(current_app)
def get_paginated_reservations_api():
    """페이지네이션 및 검색/정렬을 지원하는 예약 목록 API"""
    try:
        offset = request.args.get('offset', type=int, default=0)
        limit = request.args.get('limit', type=int, default=10)
        customer_name = request.args.get('customer_name', '').strip()
        schedule_title = request.args.get('schedule_title', '').strip()
        status_filter = request.args.get('status', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')

        conn = get_db_connection()
        cursor = conn.cursor()

        # 전체 예약 수 가져오기
        count_query = """
            SELECT COUNT(*)
            FROM reservations r
            LEFT JOIN customers c ON r.customer_id = c.id
            LEFT JOIN schedules s ON r.schedule_id = s.id
        """
        count_conditions = []
        count_params = []

        if customer_name:
            count_conditions.append("c.name LIKE ?")
            count_params.append(f"%{customer_name}%")

        if schedule_title:
            count_conditions.append("s.title LIKE ?")
            count_params.append(f"%{schedule_title}%")

        if status_filter:
            count_conditions.append("r.status = ?")
            count_params.append(status_filter)

        if date_from:
            count_conditions.append("s.start_date >= ?")
            count_params.append(date_from)

        if date_to:
            count_conditions.append("s.start_date <= ?")
            count_params.append(date_to)

        if count_conditions:
            count_query += " WHERE " + " AND ".join(count_conditions) + " AND r.deleted_at IS NULL"
        else:
            count_query += " WHERE r.deleted_at IS NULL"

        cursor.execute(count_query, count_params)
        total_reservations_count = cursor.fetchone()[0]

        query = """
            SELECT r.*, c.name as customer_name, s.title as schedule_title,
                   s.start_date as travel_start_date, s.end_date as travel_end_date
            FROM reservations r
            LEFT JOIN customers c ON r.customer_id = c.id
            LEFT JOIN schedules s ON r.schedule_id = s.id
        """
        conditions = []
        params = []

        if customer_name:
            conditions.append("c.name LIKE ?")
            params.append(f"%{customer_name}%")

        if schedule_title:
            conditions.append("s.title LIKE ?")
            params.append(f"%{schedule_title}%")

        if status_filter:
            conditions.append("r.status = ?")
            params.append(status_filter)

        if date_from:
            conditions.append("s.start_date >= ?")
            params.append(date_from)

        if date_to:
            conditions.append("s.start_date <= ?")
            params.append(date_to)

        if conditions:
            query += " WHERE " + " AND ".join(conditions) + " AND r.deleted_at IS NULL"
        else:
            query += " WHERE r.deleted_at IS NULL"

        # 정렬
        valid_sort_fields = ['created_at', 'booking_date', 'total_price', 'customer_name', 'schedule_title', 'status']
        if sort_by not in valid_sort_fields:
            sort_by = 'created_at'

        # Joins 때문에 컬럼 이름에 테이블 프리픽스를 붙여야 할 수 있음
        sort_field_map = {
            'created_at': 'r.created_at',
            'booking_date': 'r.booking_date',
            'total_price': 'r.total_price',
            'customer_name': 'c.name',
            'schedule_title': 's.title',
            'status': 'r.status'
        }
        actual_sort_field = sort_field_map.get(sort_by, 'r.created_at')

        sort_direction = 'DESC' if sort_order == 'desc' else 'ASC'
        query += f" ORDER BY {actual_sort_field} {sort_direction} LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        reservations = cursor.fetchall()
        conn.close()
        reservations_list = []
        for res in reservations:
            res_data = dict(res)
            res_data['createdAt'] = res_data.pop('created_at')
            res_data['updatedAt'] = res_data.pop('updated_at')
            res_data['customerName'] = res_data.pop('customer_name', '알 수 없음')
            res_data['scheduleTitle'] = res_data.pop('schedule_title', '알 수 없음')
            res_data['travelStartDate'] = res_data.pop('travel_start_date', '')
            res_data['travelEndDate'] = res_data.pop('travel_end_date', '')
            res_data['bookingDate'] = res_data.get('booking_date', '')
            res_data['numberOfPeople'] = res_data.get('number_of_people', 0)
            res_data['totalPrice'] = res_data.get('total_price', 0)
            reservations_list.append(res_data)
        return jsonify(reservations_list=reservations_list, total_count=total_reservations_count)
    except Exception as e:
        print(f'예약 페이지네이션 API 조회 실패: {e}')
        raise APIError('예약 목록 조회 중 오류가 발생했습니다.', 500)

@reservation_bp.route('/api/reservations', methods=['GET'])
@jwt_required(current_app)
def get_reservations():
    """모든 예약 목록을 반환하는 API 엔드포인트"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reservations WHERE deleted_at IS NULL ORDER BY created_at DESC')
    reservations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(reservations)

@reservation_bp.route('/api/reservations', methods=['POST'])
@jwt_required(current_app)
def create_reservation():
    try:
        data = request.get_json()
        customer_id = data.get('customerId')
        schedule_id = data.get('scheduleId')
        status = data.get('status', 'REQUESTED')
        booking_date = data.get('bookingDate', datetime.now().isoformat())
        number_of_people = data.get('numberOfPeople', 1)
        total_price = data.get('totalPrice', 0)
        notes = data.get('notes', '')

        if not customer_id or not schedule_id:
            raise APIError('고객과 일정 정보는 필수입니다.', 400)

        reservation_code = generate_reservation_code()
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO reservations (customer_id, schedule_id, status, booking_date, number_of_people, total_price, notes, reservation_code, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (customer_id, schedule_id, status, booking_date, number_of_people, total_price, notes, reservation_code, current_time, current_time))
        conn.commit()

        # 변경 로그 기록 (CREATE)
        new_reservation_id = cursor.lastrowid
        changed_by = g.user['username'] if 'username' in g.user else g.user.get('username', 'unknown')

        # 각 필드에 대한 변경 로그 기록
        fields_to_log = {
            'customer_id': customer_id,
            'schedule_id': schedule_id,
            'status': status,
            'booking_date': booking_date,
            'number_of_people': number_of_people,
            'total_price': total_price,
            'notes': notes,
            'reservation_code': reservation_code
        }

        for field_name, new_value in fields_to_log.items():
            log_reservation_change(
                reservation_id=new_reservation_id,
                action='CREATE',
                field_name=field_name,
                old_value='',  # 신규 등록이므로 이전 값은 없음
                new_value=str(new_value),
                changed_by=changed_by,
                details=f'새 예약 {field_name} 등록'
            )

        conn.close()
        return jsonify(new_reservation_data), 201
    except APIError:
        raise
    except Exception as e:
        print(f'예약 등록 오류: {e}')
        raise APIError('예약 등록 중 오류가 발생했습니다.', 500)

@reservation_bp.route('/api/reservations/<int:reservation_id>', methods=['GET'])
@jwt_required(current_app)
def get_reservation_by_id(reservation_id):
    """단일 예약 정보를 반환하는 API 엔드포인트"""
    conn = get_db_connection()
    cursor = conn.cursor()
    # deleted_at이 NULL인 (삭제되지 않은) 예약만 조회
    cursor.execute('SELECT * FROM reservations WHERE id = ? AND deleted_at IS NULL', (reservation_id,))
    reservation = cursor.fetchone()
    conn.close()
    if reservation:
        return jsonify(dict(reservation))
    raise APIError('예약을 찾을 수 없습니다.', 404)

@reservation_bp.route('/api/reservations/<int:reservation_id>', methods=['PUT'])
@jwt_required(current_app)
def update_reservation(reservation_id):
    try:
        data = request.get_json()
        status = data.get('status', 'REQUESTED')
        booking_date = data.get('bookingDate')
        number_of_people = data.get('numberOfPeople', 1)
        total_price = data.get('totalPrice', 0)
        notes = data.get('notes', '')

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 기존 예약 정보 조회
        cursor.execute('SELECT status, booking_date, number_of_people, total_price, notes FROM reservations WHERE id = ?', (reservation_id,))
        old_reservation = cursor.fetchone()
        
        if not old_reservation:
            conn.close()
            raise APIError('예약을 찾을 수 없습니다.', 404)
        
        current_time = datetime.now().isoformat()

        cursor.execute("""
            UPDATE reservations
            SET status = ?, booking_date = ?, number_of_people = ?, total_price = ?, notes = ?, updated_at = ?
            WHERE id = ?
        """, (status, booking_date, number_of_people, total_price, notes, current_time, reservation_id))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            raise APIError('예약을 찾을 수 없습니다.', 404)
        
        # 변경된 필드 추적 및 로그 기록
        changes = []
        if old_reservation['status'] != status:
            changes.append(f"상태: {old_reservation['status']} → {status}")
            log_reservation_change(reservation_id, 'UPDATE', 'status', old_reservation['status'], status, 'admin')
        if old_reservation['booking_date'] != booking_date:
            changes.append(f"예약일: {old_reservation['booking_date']} → {booking_date}")
            log_reservation_change(reservation_id, 'UPDATE', 'booking_date', old_reservation['booking_date'], booking_date, 'admin')
        if old_reservation['number_of_people'] != number_of_people:
            changes.append(f"인원수: {old_reservation['number_of_people']} → {number_of_people}")
            log_reservation_change(reservation_id, 'UPDATE', 'number_of_people', str(old_reservation['number_of_people']), str(number_of_people), 'admin')
        if old_reservation['total_price'] != total_price:
            changes.append(f"총금액: {old_reservation['total_price']} → {total_price}")
            log_reservation_change(reservation_id, 'UPDATE', 'total_price', str(old_reservation['total_price']), str(total_price), 'admin')
        if old_reservation['notes'] != notes:
            changes.append(f"메모: {old_reservation['notes']} → {notes}")
            log_reservation_change(reservation_id, 'UPDATE', 'notes', old_reservation['notes'], notes, 'admin')
        
        cursor.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,))
        updated_reservation = cursor.fetchone()
        conn.close()
        updated_reservation_data = dict(updated_reservation)
        updated_reservation_data['createdAt'] = updated_reservation_data.pop('created_at')
        updated_reservation_data['updatedAt'] = updated_reservation_data.pop('updated_at')
        return jsonify(updated_reservation_data)
    except APIError:
        raise
    except Exception as e:
        print(f'예약 수정 오류: {e}')
        raise APIError('예약 수정 중 오류가 발생했습니다.', 500)

@reservation_bp.route('/api/reservations/<int:reservation_id>', methods=['DELETE'])
@jwt_required(current_app)
def delete_reservation(reservation_id):
    """예약을 논리적으로 삭제하는 API 엔드포인트"""
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = datetime.now().isoformat()
    try:
        # 삭제할 예약이 존재하는지 확인
        cursor.execute('SELECT id FROM reservations WHERE id = ? AND deleted_at IS NULL', (reservation_id,))
        reservation = cursor.fetchone()
        if not reservation:
            raise APIError('예약을 찾을 수 없거나 이미 삭제되었습니다.', 404)
        
        # 논리적 삭제 (deleted_at 필드 업데이트)
        cursor.execute('UPDATE reservations SET deleted_at = ?, updated_at = ? WHERE id = ?', (current_time, current_time, reservation_id))
        conn.commit()

        log_reservation_change(reservation_id, 'SOFT_DELETE', 'deleted_at', None, current_time, 'admin')
        
        conn.close()
        return jsonify({'message': '예약이 성공적으로 삭제되었습니다.'})
    except APIError as e:
        conn.close()
        return jsonify({'error': str(e)}), e.status_code
    except Exception as e:
        conn.close()
        print(f'예약 삭제 오류: {e}')
        return jsonify({'error': '예약 삭제 중 오류가 발생했습니다.'}), 500

@reservation_bp.route('/delete/<int:reservation_id>', methods=['POST'])
@jwt_required(current_app)
def delete_reservation_page(reservation_id):
    """예약을 논리적으로 삭제하고 예약 목록 페이지로 리다이렉트"""
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = datetime.now().isoformat()
    try:
        # 삭제할 예약이 존재하는지 확인
        cursor.execute('SELECT id FROM reservations WHERE id = ? AND deleted_at IS NULL', (reservation_id,))
        reservation = cursor.fetchone()
        if not reservation:
            flash('예약을 찾을 수 없거나 이미 삭제되었습니다.', 'error')
            return redirect(url_for('reservation.reservations_page'))

        # 논리적 삭제 (deleted_at 필드 업데이트)
        cursor.execute('UPDATE reservations SET deleted_at = ?, updated_at = ? WHERE id = ?', (current_time, current_time, reservation_id))
        conn.commit()

        log_reservation_change(reservation_id, 'SOFT_DELETE', 'deleted_at', None, current_time, 'admin')
        
        conn.close()
        flash('예약이 성공적으로 삭제되었습니다.', 'success')
        return redirect(url_for('reservation.reservations_page'))
    except Exception as e:
        conn.close()
        print(f'예약 삭제 오류: {e}')
        flash('예약 삭제 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('reservation.reservations_page'))

@reservation_bp.route('/restore/<int:reservation_id>', methods=['POST'])
@jwt_required(current_app)
def restore_reservation_page(reservation_id):
    """예약을 복원하고 예약 목록 페이지로 리다이렉트"""
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = datetime.now().isoformat()
    try:
        # 복원할 예약이 존재하는지 확인 (논리적으로 삭제된 예약만)
        cursor.execute('SELECT id FROM reservations WHERE id = ? AND deleted_at IS NOT NULL', (reservation_id,))
        reservation = cursor.fetchone()
        if not reservation:
            flash('예약을 찾을 수 없거나 이미 활성 상태입니다.', 'error')
            return redirect(url_for('reservation.reservations_page'))

        # 예약 복원 (deleted_at 필드를 NULL로 업데이트)
        cursor.execute('UPDATE reservations SET deleted_at = NULL, updated_at = ? WHERE id = ?', (current_time, reservation_id))
        conn.commit()

        log_reservation_change(reservation_id, 'RESTORE', 'deleted_at', current_time, None, 'admin')
        
        conn.close()
        flash('예약이 성공적으로 복원되었습니다.', 'success')
        return redirect(url_for('reservation.reservations_page'))
    except Exception as e:
        conn.close()
        print(f'예약 복원 오류: {e}')
        flash('예약 복원 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('reservation.reservations_page'))

@reservation_bp.route('/export-csv')
@jwt_required(current_app)
def export_reservations_csv():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM reservations ORDER BY created_at DESC')
        reservations = cursor.fetchall()
        conn.close()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['고객ID', '일정ID', '상태', '예약일', '인원수', '총금액', '메모', '생성일', '수정일'])
        for res in reservations:
            writer.writerow([
                res['customer_id'],
                res['schedule_id'],
                res['status'],
                res['booking_date'],
                res['number_of_people'],
                res['total_price'],
                res['notes'],
                res['created_at'],
                res['updated_at']
            ])
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = 'attachment; filename=reservations.csv'
        return response
    except Exception as e:
        print(f'CSV 내보내기 오류: {e}')
        raise APIError('CSV 내보내기 중 오류가 발생했습니다.', 500)

@reservation_bp.route('/export-excel')
@jwt_required(current_app)
def export_reservations_excel():
    """예약 데이터를 엑셀 파일로 내보내기"""
    try:
        excel_data = export_reservations_to_excel()
        
        response = make_response(excel_data)
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=reservations.xlsx'
        
        return response
    except Exception as e:
        print(f'예약 엑셀 내보내기 오류: {e}')
        flash('엑셀 파일 생성 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('reservation.reservations_page'))

@reservation_bp.route('/import-excel', methods=['GET', 'POST'])
@jwt_required(current_app)
def import_reservations_excel():
    """엑셀 파일에서 예약 데이터 가져오기"""
    if request.method == 'GET':
        return render_template('import_reservations_excel.html')
    
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
        result = import_reservations_from_excel(file_content)
        
        if result['success_count'] > 0:
            flash(f'{result["success_count"]}개의 예약이 성공적으로 추가되었습니다.', 'success')
        
        if result['error_count'] > 0:
            flash(f'{result["error_count"]}개의 오류가 발생했습니다.', 'error')
            for error in result['errors']:
                flash(error, 'error')
        
        return redirect(url_for('reservation.reservations_page'))
        
    except Exception as e:
        print(f'예약 엑셀 가져오기 오류: {e}')
        flash('엑셀 파일 처리 중 오류가 발생했습니다.', 'error')
        return redirect(request.url)

@reservation_bp.route('/api/customers_paginated', methods=['GET'])
@jwt_required(current_app)
def get_paginated_customers():
    try:
        offset = request.args.get('offset', type=int, default=0)
        limit = request.args.get('limit', type=int, default=10)
        search_term = request.args.get('search', type=str, default='').strip()
        search_id = request.args.get('search_id', type=int)

        conn = get_db_connection()
        cursor = conn.cursor()

        query = 'SELECT id, name, phone FROM customers'
        params = []

        if search_id:
            query += ' WHERE id = ?'
            params.append(search_id)
        elif search_term:
            query += ' WHERE name LIKE ? OR phone LIKE ?'
            params.append(f'%{search_term}%')
            params.append(f'%{search_term}%')

        query += ' ORDER BY name LIMIT ? OFFSET ?'
        params.append(limit)
        params.append(offset)

        cursor.execute(query, params)
        customers = cursor.fetchall()
        conn.close()

        customers_list = [dict(c) for c in customers]
        return jsonify(customers_list)
    except Exception as e:
        print(f'고객 페이지네이션 조회 오류: {e}')
        return jsonify({'error': '고객 목록을 불러오는 중 오류가 발생했습니다.'}), 500

@reservation_bp.route('/api/schedules_paginated', methods=['GET'])
@jwt_required(current_app)
def get_paginated_schedules():
    try:
        offset = request.args.get('offset', type=int, default=0)
        limit = request.args.get('limit', type=int, default=10)
        search_term = request.args.get('search', type=str, default='').strip()
        search_id = request.args.get('search_id', type=int)

        conn = get_db_connection()
        cursor = conn.cursor()

        query = 'SELECT id, title, start_date, end_date FROM schedules WHERE status = "Active"'
        params = []

        if search_id:
            query += ' AND id = ?'
            params.append(search_id)
        elif search_term:
            query += ' AND (title LIKE ?)'
            params.append(f'%{search_term}%')

        query += ' ORDER BY start_date LIMIT ? OFFSET ?'
        params.append(limit)
        params.append(offset)

        cursor.execute(query, params)
        schedules = cursor.fetchall()
        conn.close()

        schedules_list = []
        for s in schedules:
            s_dict = dict(s)
            s_dict['start_date'] = s_dict['start_date'].split('T')[0]
            s_dict['end_date'] = s_dict['end_date'].split('T')[0]
            schedules_list.append(s_dict)
        return jsonify(schedules_list)
    except Exception as e:
        print(f'일정 페이지네이션 조회 오류: {e}')
        return jsonify({'error': '일정 목록을 불러오는 중 오류가 발생했습니다.'}), 500

@reservation_bp.route('/create', methods=['GET', 'POST'])
@jwt_required(current_app)
def create_reservation_page():
    # 오늘 날짜를 기본값으로 설정하기 위해 미리 계산
    today_date = datetime.now().isoformat().split('T')[0]

    if request.method == 'POST':
        # 폼 데이터 가져오기 및 위생 처리
        customer_id = request.form.get('customer_id', '').strip()
        schedule_id = request.form.get('schedule_id', '').strip()
        status = request.form.get('status', 'Pending').strip()
        booking_date = request.form.get('booking_date', '').strip()
        number_of_people = request.form.get('number_of_people', 1)
        total_price = request.form.get('total_price', 0)
        notes = request.form.get('notes', '').strip()

        # 필수 필드 검증
        if not customer_id or not schedule_id:
            raise ValidationError('필수 정보를 모두 입력해주세요.')
        try:
            number_of_people = int(number_of_people) if number_of_people else 1
            total_price = float(total_price) if total_price else 0
        except ValueError:
            raise ValidationError('인원수와 가격은 숫자로 입력해주세요.')

        reservation_code = generate_reservation_code()
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().isoformat()
        try:
            cursor.execute("""
                INSERT INTO reservations (customer_id, schedule_id, status, booking_date, number_of_people, total_price, notes, reservation_code, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (customer_id, schedule_id, status, booking_date, number_of_people, total_price, notes, reservation_code, current_time, current_time))
            conn.commit()

            # 변경 로그 기록 (CREATE)
            new_reservation_id = cursor.lastrowid
            changed_by = g.user['username'] if 'username' in g.user else g.user.get('username', 'unknown')

            # 각 필드에 대한 변경 로그 기록
            fields_to_log = {
                'customer_id': customer_id,
                'schedule_id': schedule_id,
                'status': status,
                'booking_date': booking_date,
                'number_of_people': number_of_people,
                'total_price': total_price,
                'notes': notes,
                'reservation_code': reservation_code
            }

            for field_name, new_value in fields_to_log.items():
                log_reservation_change(
                    reservation_id=new_reservation_id,
                    action='CREATE',
                    field_name=field_name,
                    old_value='',  # 신규 등록이므로 이전 값은 없음
                    new_value=str(new_value),
                    changed_by=changed_by,
                    details=f'새 예약 {field_name} 등록'
                )

            conn.close()
            return redirect(url_for('reservation.reservations_page'))
        except Exception as e:
            conn.close()
            print(f'예약 등록 오류: {e}')
            return render_template('create_reservation.html', error='예약 등록 중 오류가 발생했습니다.', today_date=today_date)
    
    # GET 요청 시 고객과 일정 목록을 가져와서 템플릿에 전달
    # 초기 30개 고객/일정만 로드 (프론트엔드에서 추가 로드)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, phone FROM customers ORDER BY name LIMIT 30 OFFSET 0')
    customers = cursor.fetchall()
    cursor.execute('SELECT id, title, start_date, end_date FROM schedules WHERE status = "Active" ORDER BY start_date LIMIT 30 OFFSET 0')
    schedules = cursor.fetchall()
    conn.close()
    
    return render_template('create_reservation.html', customers=customers, schedules=schedules, today_date=today_date)

@reservation_bp.route('/edit/<int:reservation_id>', methods=['GET', 'POST'])
@jwt_required(current_app)
def edit_reservation_page(reservation_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,))
    reservation = cursor.fetchone()
    
    if not reservation:
        conn.close()
        return render_template('edit_reservation.html', reservation=None, error='예약을 찾을 수 없습니다.')
    
    # 논리적으로 삭제된 예약은 수정 페이지에 접근할 수 없음
    if reservation['deleted_at'] is not None:
        conn.close()
        flash('이미 삭제된 예약입니다. 복원 후 수정해주세요.', 'error')
        return redirect(url_for('reservation.reservations_page'))
    
    # 고객과 일정 목록을 가져오기 (edit 페이지는 모든 목록을 가져옴)
    cursor.execute('SELECT id, name, phone FROM customers ORDER BY name')
    customers = cursor.fetchall()
    cursor.execute('SELECT id, title, start_date, end_date FROM schedules WHERE status = "Active" ORDER BY start_date')
    schedules = cursor.fetchall()
    conn.close()

    # QR 코드 생성 (GET 요청 시에만)
    qr_code_base64 = None
    if reservation and reservation['reservation_code']:
        qr_url = f"{Config.BASE_DOMAIN_URL}/{reservation['reservation_code']}"
        qr = qrcode.make(qr_url)
        buf = io.BytesIO()
        qr.save(buf, format='PNG')
        qr_code_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    if request.method == 'POST':
        # 폼 데이터 가져오기
        customer_id = request.form.get('customer_id')
        schedule_id = request.form.get('schedule_id')
        status = request.form.get('status', 'Pending')
        booking_date = request.form.get('booking_date')
        number_of_people = request.form.get('number_of_people', 1)
        total_price = request.form.get('total_price', 0)
        notes = request.form.get('notes', '')

        # 필수 필드 검증
        errors = {}
        if not customer_id:
            errors['customer_id'] = '고객을 선택해주세요.'
        if not schedule_id:
            errors['schedule_id'] = '일정을 선택해주세요.'
        if not booking_date:
            errors['booking_date'] = '예약일을 입력해주세요.'

        if errors:
            return render_template('edit_reservation.html', reservation=reservation, customers=customers, schedules=schedules, errors=errors, error='필수 정보를 모두 입력해주세요.', qr_code_base64=qr_code_base64)

        # 숫자 변환
        try:
            number_of_people = int(number_of_people) if number_of_people else 1
            total_price = float(total_price) if total_price else 0
        except ValueError:
            return render_template('edit_reservation.html', reservation=reservation, customers=customers, schedules=schedules, error='인원수와 가격은 숫자로 입력해주세요.', qr_code_base64=qr_code_base64)

        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().isoformat()
        
        try:
            # 변경된 필드 추적
            changes = []
            if str(reservation['customer_id']) != str(customer_id):
                changes.append(f"고객ID: {reservation['customer_id']} → {customer_id}")
                log_reservation_change(reservation_id, 'UPDATE', 'customer_id', str(reservation['customer_id']), str(customer_id), 'admin')
            if str(reservation['schedule_id']) != str(schedule_id):
                changes.append(f"일정ID: {reservation['schedule_id']} → {schedule_id}")
                log_reservation_change(reservation_id, 'UPDATE', 'schedule_id', str(reservation['schedule_id']), str(schedule_id), 'admin')
            if reservation['status'] != status:
                # 예약 상태 변경 로직 추가
                current_status_order = STATUS_ORDER.get(reservation['status'])
                new_status_order = STATUS_ORDER.get(status)

                if current_status_order is None or new_status_order is None:
                    flash('유효하지 않은 예약 상태입니다.', 'error')
                    return render_template('edit_reservation.html', reservation=reservation, customers=customers, schedules=schedules, errors=errors, qr_code_base64=qr_code_base64)
                
                # VIP_CUSTOMER, COMPLAINT, PROCESSED 상태는 특별히 처리 (모든 상태에서 이동 가능하도록)
                if status in ["VIP_CUSTOMER", "COMPLAINT", "PROCESSED"]:
                    # 특별 상태로의 변경은 항상 허용
                    pass
                elif abs(new_status_order - current_status_order) > 1:
                    flash('예약 상태는 한 단계씩만 변경할 수 있습니다.', 'error')
                    return render_template('edit_reservation.html', reservation=reservation, customers=customers, schedules=schedules, errors=errors, qr_code_base64=qr_code_base64)

                changes.append(f"상태: {reservation['status']} → {status}")
                log_reservation_change(reservation_id, 'UPDATE', 'status', reservation['status'], status, 'admin')
            if reservation['booking_date'] != booking_date:
                changes.append(f"예약일: {reservation['booking_date']} → {booking_date}")
                log_reservation_change(reservation_id, 'UPDATE', 'booking_date', reservation['booking_date'], booking_date, 'admin')
            if reservation['number_of_people'] != number_of_people:
                changes.append(f"인원수: {reservation['number_of_people']} → {number_of_people}")
                log_reservation_change(reservation_id, 'UPDATE', 'number_of_people', str(reservation['number_of_people']), str(number_of_people), 'admin')
            if reservation['total_price'] != total_price:
                changes.append(f"총금액: {reservation['total_price']} → {total_price}")
                log_reservation_change(reservation_id, 'UPDATE', 'total_price', str(reservation['total_price']), str(total_price), 'admin')
            if reservation['notes'] != notes:
                changes.append(f"메모: {reservation['notes']} → {notes}")
                log_reservation_change(reservation_id, 'UPDATE', 'notes', reservation['notes'], notes, 'admin')
            
            cursor.execute("""
                UPDATE reservations
                SET customer_id = ?, schedule_id = ?, status = ?, booking_date = ?, number_of_people = ?, total_price = ?, notes = ?, updated_at = ?
                WHERE id = ?
            """, (customer_id, schedule_id, status, booking_date, number_of_people, total_price, notes, current_time, reservation_id))
            conn.commit()
            
            # 전체 변경 로그 기록 (제거됨)
            # if changes:
            #     change_description = f'예약 수정: {", ".join(changes)}'
            # else:
            #     change_description = '예약 수정 (변경사항 없음)'
            # log_reservation_change(reservation_id, 'UPDATE', 'all', None, change_description, 'admin')
            
            conn.close()
            flash('예약이 성공적으로 수정되었습니다.', 'success')
            return redirect(url_for('reservation.reservations_page'))
        except Exception as e:
            conn.close()
            print(f'예약 수정 오류: {e}')
            return render_template('edit_reservation.html', reservation=reservation, customers=customers, schedules=schedules, error='예약 수정 중 오류가 발생했습니다.', qr_code_base64=qr_code_base64)
    
    return render_template('edit_reservation.html', reservation=reservation, customers=customers, schedules=schedules, qr_code_base64=qr_code_base64) 