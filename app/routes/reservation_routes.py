from flask import Blueprint, render_template, request, jsonify, current_app, make_response, redirect, url_for, flash
from datetime import datetime
import csv
import io
from database import get_db_connection
from app.utils.errors import APIError
from app.utils.auth import jwt_required
from app.utils.filters import format_date, format_datetime, format_currency, get_status_color, get_status_text
from app.utils.audit import log_reservation_change
import sqlite3

reservation_bp = Blueprint('reservation', __name__)

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
        status = request.args.get('status', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
        
        if status:
            conditions.append("r.status = ?")
            params.append(status)
        
        if date_from:
            conditions.append("s.start_date >= ?")
            params.append(date_from)
        
        if date_to:
            conditions.append("s.start_date <= ?")
            params.append(date_to)
        
        # WHERE 절 추가
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        # 정렬
        query += " ORDER BY r.created_at DESC"
        
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
        
        return render_template('reservations.html', reservations=reservations_list)
    except Exception as e:
        print(f'예약 목록 조회 오류: {e}')
        return render_template('reservations.html', error='예약 목록을 불러오는 중 오류가 발생했습니다.')

@reservation_bp.route('/api/reservations', methods=['GET'])
@jwt_required(current_app)
def get_reservations():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 고객명과 일정명을 조인하여 조회 - 여행 날짜도 포함
        cursor.execute("""
            SELECT r.*, c.name as customer_name, s.title as schedule_title,
                   s.start_date as travel_start_date, s.end_date as travel_end_date
            FROM reservations r
            LEFT JOIN customers c ON r.customer_id = c.id
            LEFT JOIN schedules s ON r.schedule_id = s.id
            ORDER BY r.created_at DESC
        """)
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
            reservations_list.append(res_data)
        return jsonify(reservations_list)
    except Exception as e:
        print(f'예약 조회 실패: {e}')
        raise APIError('예약 조회 중 오류가 발생했습니다.', 500)

@reservation_bp.route('/api/reservations', methods=['POST'])
@jwt_required(current_app)
def create_reservation():
    try:
        data = request.get_json()
        customer_id = data.get('customerId')
        schedule_id = data.get('scheduleId')
        status = data.get('status', 'Confirmed')
        booking_date = data.get('bookingDate', datetime.now().isoformat())
        number_of_people = data.get('numberOfPeople', 1)
        total_price = data.get('totalPrice', 0)
        notes = data.get('notes', '')

        if not customer_id or not schedule_id:
            raise APIError('고객과 일정 정보는 필수입니다.', 400)

        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO reservations (customer_id, schedule_id, status, booking_date, number_of_people, total_price, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (customer_id, schedule_id, status, booking_date, number_of_people, total_price, notes, current_time, current_time))
        conn.commit()

        new_reservation_id = cursor.lastrowid
        
        # 변경 로그 기록
        log_reservation_change(new_reservation_id, 'CREATE', 'all', None, f'예약 생성: 고객ID {customer_id}, 일정ID {schedule_id}', 'admin')
        
        cursor.execute('SELECT * FROM reservations WHERE id = ?', (new_reservation_id,))
        new_reservation = cursor.fetchone()
        conn.close()

        if not new_reservation:
            raise APIError('예약 등록 후 정보를 찾을 수 없습니다.', 500)

        new_reservation_data = dict(new_reservation)
        new_reservation_data['createdAt'] = new_reservation_data.pop('created_at')
        new_reservation_data['updatedAt'] = new_reservation_data.pop('updated_at')
        return jsonify(new_reservation_data), 201
    except APIError:
        raise
    except Exception as e:
        print(f'예약 등록 오류: {e}')
        raise APIError('예약 등록 중 오류가 발생했습니다.', 500)

@reservation_bp.route('/api/reservations/<int:reservation_id>', methods=['GET'])
@jwt_required(current_app)
def get_reservation_by_id(reservation_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,))
        reservation = cursor.fetchone()
        conn.close()
        if not reservation:
            raise APIError('예약을 찾을 수 없습니다.', 404)
        reservation_data = dict(reservation)
        reservation_data['createdAt'] = reservation_data.pop('created_at')
        reservation_data['updatedAt'] = reservation_data.pop('updated_at')
        return jsonify(reservation_data)
    except APIError:
        raise
    except Exception as e:
        print(f'예약 조회 실패: {e}')
        raise APIError('예약 조회 중 오류가 발생했습니다.', 500)

@reservation_bp.route('/api/reservations/<int:reservation_id>', methods=['PUT'])
@jwt_required(current_app)
def update_reservation(reservation_id):
    try:
        data = request.get_json()
        status = data.get('status', 'Confirmed')
        booking_date = data.get('bookingDate')
        number_of_people = data.get('numberOfPeople', 1)
        total_price = data.get('totalPrice', 0)
        notes = data.get('notes', '')

        conn = get_db_connection()
        cursor = conn.cursor()
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
        
        # 변경 로그 기록
        log_reservation_change(reservation_id, 'UPDATE', 'all', None, f'예약 수정: 상태 {status}, 인원 {number_of_people}', 'admin')
        
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
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 삭제 전 예약 정보 조회
        cursor.execute('SELECT customer_id, schedule_id FROM reservations WHERE id = ?', (reservation_id,))
        reservation = cursor.fetchone()
        customer_id = reservation[0] if reservation else 'Unknown'
        schedule_id = reservation[1] if reservation else 'Unknown'
        
        cursor.execute('DELETE FROM reservations WHERE id = ?', (reservation_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            raise APIError('예약을 찾을 수 없습니다.', 404)
        
        # 변경 로그 기록
        log_reservation_change(reservation_id, 'DELETE', 'all', None, f'예약 삭제: 고객ID {customer_id}, 일정ID {schedule_id}', 'admin')
        
        conn.close()
        return jsonify({'message': '예약이 삭제되었습니다.'})
    except APIError:
        raise
    except Exception as e:
        print(f'예약 삭제 오류: {e}')
        raise APIError('예약 삭제 중 오류가 발생했습니다.', 500)

@reservation_bp.route('/delete/<int:reservation_id>', methods=['POST'])
@jwt_required(current_app)
def delete_reservation_page(reservation_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 삭제 전 예약 정보 조회
        cursor.execute('SELECT customer_id, schedule_id FROM reservations WHERE id = ?', (reservation_id,))
        reservation = cursor.fetchone()
        customer_id = reservation[0] if reservation else 'Unknown'
        schedule_id = reservation[1] if reservation else 'Unknown'
        
        cursor.execute('DELETE FROM reservations WHERE id = ?', (reservation_id,))
        conn.commit()
        
        # 변경 로그 기록
        log_reservation_change(reservation_id, 'DELETE', 'all', None, f'예약 삭제: 고객ID {customer_id}, 일정ID {schedule_id}', 'admin')
        
        conn.close()
        return redirect(url_for('reservation.reservations_page'))
    except Exception as e:
        print(f'예약 삭제 오류: {e}')
        return render_template('reservations.html', error='예약 삭제 중 오류가 발생했습니다.')

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

@reservation_bp.route('/create', methods=['GET', 'POST'])
@jwt_required(current_app)
def create_reservation_page():
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
            # 고객과 일정 목록을 가져와서 템플릿에 전달
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, phone FROM customers ORDER BY name')
            customers = cursor.fetchall()
            cursor.execute('SELECT id, title, start_date, end_date FROM schedules WHERE status = "Active" ORDER BY start_date')
            schedules = cursor.fetchall()
            conn.close()
            return render_template('create_reservation.html', customers=customers, schedules=schedules, errors=errors, error='필수 정보를 모두 입력해주세요.')

        # 숫자 변환
        try:
            number_of_people = int(number_of_people) if number_of_people else 1
            total_price = float(total_price) if total_price else 0
        except ValueError:
            return render_template('create_reservation.html', error='인원수와 가격은 숫자로 입력해주세요.')

        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().isoformat()
        
        try:
            cursor.execute("""
                INSERT INTO reservations (customer_id, schedule_id, status, booking_date, number_of_people, total_price, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (customer_id, schedule_id, status, booking_date, number_of_people, total_price, notes, current_time, current_time))
            conn.commit()
            conn.close()
            return redirect(url_for('reservation.reservations_page'))
        except Exception as e:
            conn.close()
            print(f'예약 등록 오류: {e}')
            return render_template('create_reservation.html', error='예약 등록 중 오류가 발생했습니다.')
    
    # GET 요청 시 고객과 일정 목록을 가져와서 템플릿에 전달
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, phone FROM customers ORDER BY name')
    customers = cursor.fetchall()
    cursor.execute('SELECT id, title, start_date, end_date FROM schedules WHERE status = "Active" ORDER BY start_date')
    schedules = cursor.fetchall()
    conn.close()
    
    return render_template('create_reservation.html', customers=customers, schedules=schedules)

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
    
    # 고객과 일정 목록을 가져오기
    cursor.execute('SELECT id, name, phone FROM customers ORDER BY name')
    customers = cursor.fetchall()
    cursor.execute('SELECT id, title, start_date, end_date FROM schedules WHERE status = "Active" ORDER BY start_date')
    schedules = cursor.fetchall()
    conn.close()
    
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
            return render_template('edit_reservation.html', reservation=reservation, customers=customers, schedules=schedules, errors=errors, error='필수 정보를 모두 입력해주세요.')

        # 숫자 변환
        try:
            number_of_people = int(number_of_people) if number_of_people else 1
            total_price = float(total_price) if total_price else 0
        except ValueError:
            return render_template('edit_reservation.html', reservation=reservation, customers=customers, schedules=schedules, error='인원수와 가격은 숫자로 입력해주세요.')

        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().isoformat()
        
        try:
            cursor.execute("""
                UPDATE reservations
                SET customer_id = ?, schedule_id = ?, status = ?, booking_date = ?, number_of_people = ?, total_price = ?, notes = ?, updated_at = ?
                WHERE id = ?
            """, (customer_id, schedule_id, status, booking_date, number_of_people, total_price, notes, current_time, reservation_id))
            conn.commit()
            
            # 변경 로그 기록
            log_reservation_change(reservation_id, 'UPDATE', 'all', None, f'예약 수정: 상태 {status}, 인원 {number_of_people}', 'admin')
            
            cursor.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,))
            updated_reservation = cursor.fetchone()
            conn.close()
            updated_reservation_data = dict(updated_reservation)
            updated_reservation_data['createdAt'] = updated_reservation_data.pop('created_at')
            updated_reservation_data['updatedAt'] = updated_reservation_data.pop('updated_at')
            return jsonify(updated_reservation_data)
        except Exception as e:
            conn.close()
            print(f'예약 수정 오류: {e}')
            return render_template('edit_reservation.html', reservation=reservation, customers=customers, schedules=schedules, error='예약 수정 중 오류가 발생했습니다.')
    
    return render_template('edit_reservation.html', reservation=reservation, customers=customers, schedules=schedules) 