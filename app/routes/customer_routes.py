import time
from flask import Blueprint, render_template, request, jsonify, current_app, make_response, redirect, url_for, flash, g
from flask_login import login_required, current_user
from datetime import datetime
import csv
import io
from database import get_db_connection
from app.utils.errors import APIError
from app.utils.auth import jwt_required
from app.utils.filters import format_date, format_datetime
from app.utils.audit import log_customer_change
from app.utils.excel_utils import export_customers_to_excel, import_customers_from_excel
import sqlite3
import os
import uuid
from werkzeug.utils import secure_filename
from app.utils import ValidationError
from app.utils.ocr_utils import extract_text_from_image, extract_passport_info

customer_bp = Blueprint('customer', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 필터 등록
@customer_bp.app_template_filter('format_date')
def format_date_filter(date_str):
    return format_date(date_str)

@customer_bp.app_template_filter('format_datetime')
def format_datetime_filter(datetime_str):
    return format_datetime(datetime_str)

@customer_bp.route('/')
@login_required
def customers_page():
    """고객 목록 페이지"""
    try:
        # 검색 및 필터링 파라미터 가져오기
        search_term = request.args.get('search_term', '').strip()
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        has_email = request.args.get('has_email') == 'true'
        has_phone = request.args.get('has_phone') == 'true'
        has_address = request.args.get('has_address') == 'true'
        page = request.args.get('page', 1, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT items_per_page FROM user_settings WHERE user_id = ?', (current_user.id,))
        user_setting = cursor.fetchone()
        conn.close()
        
        per_page = user_setting['items_per_page'] if user_setting and user_setting['items_per_page'] else 25
        per_page = request.args.get('per_page', per_page, type=int)

        conn = get_db_connection()
        cursor = conn.cursor()

        # 전체 고객 수 가져오기 (페이지네이션을 위해)
        count_query = 'SELECT COUNT(*) FROM customers'
        count_conditions = []
        count_params = []

        if search_term:
            count_conditions.append("(name LIKE ? OR email LIKE ? OR phone LIKE ? OR address LIKE ? OR notes LIKE ?)")
            search_pattern = f"%{search_term}%"
            count_params.extend([search_pattern, search_pattern, search_pattern, search_pattern, search_pattern])

        if has_email:
            count_conditions.append("email IS NOT NULL AND email != ''")

        if has_phone:
            count_conditions.append("phone IS NOT NULL AND phone != ''")

        if has_address:
            count_conditions.append("address IS NOT NULL AND address != ''")

        if count_conditions:
            count_query += " WHERE " + " AND ".join(count_conditions)

        cursor.execute(count_query, count_params)
        total_customers_count = cursor.fetchone()[0]

        # 총 페이지 수 계산
        total_pages = (total_customers_count + per_page - 1) // per_page
        if page < 1: page = 1
        if page > total_pages and total_pages > 0: page = total_pages

        offset = (page - 1) * per_page

        query = 'SELECT id, name, phone, email, address, notes, created_at, updated_at FROM customers'

        conditions = []
        params = []

        if search_term:
            conditions.append("(name LIKE ? OR email LIKE ? OR phone LIKE ? OR address LIKE ? OR notes LIKE ?)")
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern, search_pattern, search_pattern, search_pattern, search_pattern])

        if has_email:
            conditions.append("email IS NOT NULL AND email != ''")

        if has_phone:
            conditions.append("phone IS NOT NULL AND phone != ''")

        if has_address:
            conditions.append("address IS NOT NULL AND address != ''")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        valid_sort_fields = ['name', 'email', 'created_at', 'phone', 'address']
        if sort_by not in valid_sort_fields:
            sort_by = 'created_at'

        sort_direction = 'DESC' if sort_order == 'desc' else 'ASC'
        query += f" ORDER BY {sort_by} {sort_direction} LIMIT ? OFFSET ?"
        params.extend([per_page, offset])

        cursor.execute(query, params)
        customers = cursor.fetchall()
        conn.close()

        customers_list = [dict(customer) for customer in customers]

        return render_template('customers.html',
                             customers=customers_list,
                             total_customers_count=total_customers_count,
                             search_term=search_term,
                             sort_by=sort_by,
                             sort_order=sort_order,
                             has_email=has_email,
                             has_phone=has_phone,
                             has_address=has_address,
                             page=page,
                             per_page=per_page,
                             total_pages=total_pages)
    except Exception as e:
        print(f'고객 목록 조회 오류: {e}')
        return render_template('customers.html', error='고객 목록을 불러오는 중 오류가 발생했습니다.')

@customer_bp.route('/api/customers/paginated', methods=['GET'])
@jwt_required(current_app)
def get_paginated_customers_api():
    """페이지네이션 및 검색/정렬을 지원하는 고객 목록 API"""
    try:
        offset = request.args.get('offset', type=int, default=0)
        limit = request.args.get('limit', type=int, default=10)
        search_term = request.args.get('search_term', '').strip()
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        has_email = request.args.get('has_email') == 'true'
        has_phone = request.args.get('has_phone') == 'true'
        has_address = request.args.get('has_address') == 'true'

        conn = get_db_connection()
        cursor = conn.cursor()

        # 전체 고객 수 가져오기
        count_query = 'SELECT COUNT(*) FROM customers'
        count_conditions = []
        count_params = []

        if search_term:
            count_conditions.append("(name LIKE ? OR email LIKE ? OR phone LIKE ? OR address LIKE ? OR notes LIKE ?)")
            search_pattern = f"%{search_term}%"
            count_params.extend([search_pattern, search_pattern, search_pattern, search_pattern, search_pattern])

        if has_email:
            count_conditions.append("email IS NOT NULL AND email != ''")

        if has_phone:
            count_conditions.append("phone IS NOT NULL AND phone != ''")

        if has_address:
            count_conditions.append("address IS NOT NULL AND address != ''")

        if count_conditions:
            count_query += " WHERE " + " AND ".join(count_conditions)

        cursor.execute(count_query, count_params)
        total_customers_count = cursor.fetchone()[0]

        query = 'SELECT id, name, phone, email, address, notes, created_at, updated_at FROM customers'

        conditions = []
        params = []

        if search_term:
            conditions.append("(name LIKE ? OR email LIKE ? OR phone LIKE ? OR address LIKE ? OR notes LIKE ?)")
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern, search_pattern, search_pattern, search_pattern, search_pattern])

        if has_email:
            conditions.append("email IS NOT NULL AND email != ''")

        if has_phone:
            conditions.append("phone IS NOT NULL AND phone != ''")

        if has_address:
            conditions.append("address IS NOT NULL AND address != ''")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        valid_sort_fields = ['name', 'email', 'created_at', 'phone', 'address']
        if sort_by not in valid_sort_fields:
            sort_by = 'created_at'

        sort_direction = 'DESC' if sort_order == 'desc' else 'ASC'
        query += f" ORDER BY {sort_by} {sort_direction} LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        customers = cursor.fetchall()
        conn.close()

        customers_list = []
        for customer in customers:
            customer_data = dict(customer)
            customer_data['createdAt'] = customer_data.pop('created_at')
            customer_data['updatedAt'] = customer_data.pop('updated_at')
            customers_list.append(customer_data)

        return jsonify(customers_list=customers_list, total_count=total_customers_count)
    except Exception as e:
        print(f'고객 페이지네이션 API 조회 실패: {e}')
        raise APIError('고객 목록 조회 중 오류가 발생했습니다.', 500)

@customer_bp.route('/api/customers', methods=['GET'])
@jwt_required(current_app)
def get_customers():
    """모든 고객 목록을 반환하는 API 엔드포인트"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM customers WHERE deleted_at IS NULL ORDER BY created_at DESC') # 논리적 삭제된 고객 제외
    customers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(customers)

@customer_bp.route('/api/customers', methods=['POST'])
@jwt_required(current_app)
def create_customer():
    """고객 생성 API"""
    try:
        data = request.get_json()
        name = data.get('name')
        phone = data.get('phone')
        email = data.get('email', '')
        address = data.get('address', '')
        notes = data.get('notes', '')

        if not name or not phone:
            raise APIError('이름과 전화번호는 필수입니다.', 400)

        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().isoformat()
        new_customer_id = str(time.time_ns())

        # 고객 생성
        cursor.execute("""
            INSERT INTO customers (id, name, email, phone, address, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (new_customer_id, name, email, phone, address, current_time, current_time))
        
        conn.commit()
        
        cursor.execute('SELECT * FROM customers WHERE id = ?', (new_customer_id,))
        new_customer = cursor.fetchone()
        
        conn.close()
        
        return jsonify(dict(new_customer)), 201
    except APIError:
        raise
    except Exception as e:
        print(f'고객 등록 오류: {e}')
        raise APIError('고객 등록 중 오류가 발생했습니다.', 500)

@customer_bp.route('/api/customers/<string:customer_id>', methods=['GET'])
@jwt_required(current_app)
def get_customer_by_id(customer_id):
    """단일 고객 정보를 반환하는 API 엔드포인트"""
    conn = get_db_connection()
    cursor = conn.cursor()
    # deleted_at이 NULL인 (삭제되지 않은) 고객만 조회
    cursor.execute('SELECT * FROM customers WHERE id = ? AND deleted_at IS NULL', (customer_id,))
    customer = cursor.fetchone()
    conn.close()
    if customer:
        return jsonify(dict(customer))
    raise APIError('고객을 찾을 수 없습니다.', 404)

@customer_bp.route('/api/customers/<string:customer_id>', methods=['PUT'])
@jwt_required(current_app)
def update_customer(customer_id):
    """고객 수정 API"""
    try:
        data = request.get_json()
        name = data.get('name')
        phone = data.get('phone')
        email = data.get('email', '')
        address = data.get('address', '')
        notes = data.get('notes', '')

        if not name or not phone:
            raise APIError('이름과 전화번호는 필수입니다.', 400)

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 기존 고객 정보 조회
        cursor.execute('SELECT * FROM customers WHERE id = ?', (customer_id,))
        existing_customer = cursor.fetchone()
        
        if not existing_customer:
            conn.close()
            raise APIError('고객을 찾을 수 없습니다.', 404)
        
        # 논리적으로 삭제된 고객은 수정할 수 없음
        if existing_customer['deleted_at'] is not None:
            raise APIError('삭제된 고객은 수정할 수 없습니다.', 400)

        current_time = datetime.now().isoformat()

        cursor.execute("""
            UPDATE customers
            SET name = ?, phone = ?, email = ?, address = ?, notes = ?, updated_at = ?
            WHERE id = ?
        """, (name, phone, email, address, notes, current_time, customer_id))
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            raise APIError('고객을 찾을 수 없습니다.', 404)

        # 변경된 필드 추적 및 로그 기록
        changes = []
        if existing_customer['name'] != name:
            changes.append(f"이름: {existing_customer['name']} → {name}")
            log_customer_change(customer_id, 'UPDATE', 'name', existing_customer['name'], name, 'admin')
        if existing_customer['phone'] != phone:
            changes.append(f"전화번호: {existing_customer['phone']} → {phone}")
            log_customer_change(customer_id, 'UPDATE', 'phone', existing_customer['phone'], phone, 'admin')
        if existing_customer['email'] != email:
            changes.append(f"이메일: {existing_customer['email']} → {email}")
            log_customer_change(customer_id, 'UPDATE', 'email', existing_customer['email'], email, 'admin')
        if existing_customer['address'] != address:
            changes.append(f"주소: {existing_customer['address']} → {address}")
            log_customer_change(customer_id, 'UPDATE', 'address', existing_customer['address'], address, 'admin')
        if existing_customer['notes'] != notes:
            changes.append(f"메모: {existing_customer['notes']} → {notes}")
            log_customer_change(customer_id, 'UPDATE', 'notes', existing_customer['notes'], notes, 'admin')
        
        cursor.execute('SELECT id, name, phone, email, address, notes, created_at, updated_at FROM customers WHERE id = ?', (customer_id,))
        updated_customer = cursor.fetchone()
        conn.close()

        updated_customer_data = dict(updated_customer)
        updated_customer_data['createdAt'] = updated_customer_data.pop('created_at')
        updated_customer_data['updatedAt'] = updated_customer_data.pop('updated_at')

        return jsonify(updated_customer_data)
    except APIError:
        raise
    except Exception as e:
        print(f'고객 수정 오류: {e}')
        raise APIError('고객 수정 중 오류가 발생했습니다.', 500)

@customer_bp.route('/api/customers/<string:customer_id>', methods=['DELETE'])
@jwt_required(current_app)
def delete_customer(customer_id):
    """고객을 논리적으로 삭제하는 API 엔드포인트"""
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = datetime.now().isoformat()
    try:
        # 삭제할 고객이 존재하는지 확인
        cursor.execute('SELECT id FROM customers WHERE id = ? AND deleted_at IS NULL', (customer_id,))
        customer = cursor.fetchone()
        if not customer:
            raise APIError('고객을 찾을 수 없거나 이미 삭제되었습니다.', 404)
        
        # 논리적 삭제 (deleted_at 필드 업데이트)
        cursor.execute('UPDATE customers SET deleted_at = ?, updated_at = ? WHERE id = ?', (current_time, current_time, customer_id))
        conn.commit()

        log_customer_change(customer_id, 'SOFT_DELETE', 'deleted_at', None, current_time, 'admin')
        
        conn.close()
        return jsonify({'message': '고객이 성공적으로 삭제되었습니다.'})
    except APIError as e:
        conn.close()
        return jsonify({'error': str(e)}), e.status_code
    except Exception as e:
        conn.close()
        print(f'고객 삭제 오류: {e}')
        return jsonify({'error': '고객 삭제 중 오류가 발생했습니다.'}), 500

@customer_bp.route('/delete/<string:customer_id>', methods=['POST'])
@jwt_required(current_app)
def delete_customer_page(customer_id):
    """고객을 논리적으로 삭제하고 고객 목록 페이지로 리다이렉트"""
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = datetime.now().isoformat()
    try:
        # 삭제할 고객이 존재하는지 확인
        cursor.execute('SELECT id FROM customers WHERE id = ? AND deleted_at IS NULL', (customer_id,))
        customer = cursor.fetchone()
        if not customer:
            flash('고객을 찾을 수 없거나 이미 삭제되었습니다.', 'error')
            return redirect(url_for('customer.customers_page'))

        # 논리적 삭제 (deleted_at 필드 업데이트)
        cursor.execute('UPDATE customers SET deleted_at = ?, updated_at = ? WHERE id = ?', (current_time, current_time, customer_id))
        conn.commit()

        log_customer_change(customer_id, 'SOFT_DELETE', 'deleted_at', None, current_time, 'admin')
        
        conn.close()
        flash('고객이 성공적으로 삭제되었습니다.', 'success')
        return redirect(url_for('customer.customers_page'))
    except Exception as e:
        conn.close()
        print(f'고객 삭제 오류: {e}')
        flash('고객 삭제 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('customer.customers_page'))

@customer_bp.route('/restore/<string:customer_id>', methods=['POST'])
@jwt_required(current_app)
def restore_customer_page(customer_id):
    """고객을 복원하고 고객 목록 페이지로 리다이렉트"""
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = datetime.now().isoformat()
    try:
        # 복원할 고객이 존재하는지 확인 (논리적으로 삭제된 고객만)
        cursor.execute('SELECT id FROM customers WHERE id = ? AND deleted_at IS NOT NULL', (customer_id,))
        customer = cursor.fetchone()
        if not customer:
            flash('고객을 찾을 수 없거나 이미 활성 상태입니다.', 'error')
            return redirect(url_for('customer.customers_page'))

        # 고객 복원 (deleted_at 필드를 NULL로 업데이트)
        cursor.execute('UPDATE customers SET deleted_at = NULL, updated_at = ? WHERE id = ?', (current_time, customer_id))
        conn.commit()

        log_customer_change(customer_id, 'RESTORE', 'deleted_at', current_time, None, 'admin')
        
        conn.close()
        flash('고객이 성공적으로 복원되었습니다.', 'success')
        return redirect(url_for('customer.customers_page'))
    except Exception as e:
        conn.close()
        print(f'고객 복원 오류: {e}')
        flash('고객 복원 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('customer.customers_page'))

@customer_bp.route('/export-csv')
@jwt_required(current_app)
def export_customers_csv():
    """고객 목록 CSV 내보내기"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT name, phone, email, address, notes, created_at, updated_at FROM customers ORDER BY created_at DESC')
        customers = cursor.fetchall()
        conn.close()

        # CSV 데이터 생성
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 헤더 작성
        writer.writerow(['이름', '전화번호', '이메일', '주소', '메모', '생성일', '수정일'])
        
        # 데이터 작성
        for customer in customers:
            writer.writerow([
                customer['name'],
                customer['phone'],
                customer['email'],
                customer['address'],
                customer['notes'],
                customer['created_at'],
                customer['updated_at']
            ])

        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = 'attachment; filename=customers.csv'
        
        return response
    except Exception as e:
        print(f'CSV 내보내기 오류: {e}')
        raise APIError('CSV 내보내기 중 오류가 발생했습니다.', 500)

@customer_bp.route('/create', methods=['GET', 'POST'])
@jwt_required(current_app)
def create_customer_page():
    """새 고객 생성 페이지 및 처리"""
    errors = {}
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        address = request.form.get('address')
        passport_number = request.form.get('passport_number')
        last_name_eng = request.form.get('last_name_eng')
        first_name_eng = request.form.get('first_name_eng')
        expiry_date = request.form.get('expiry_date')
        notes = request.form.get('notes')
        passport_photo = request.files.get('passport_photo')

        if not name:
            errors['name'] = '이름은 필수입니다.'
        if not phone:
            errors['phone'] = '전화번호는 필수입니다.'

        passport_photo_filename = None
        current_app.logger.debug(f"Passport photo received: {bool(passport_photo)}")
        if passport_photo and passport_photo.filename != '':
            current_app.logger.debug(f"Passport photo filename: {passport_photo.filename}")
            current_app.logger.debug(f"Is allowed file: {allowed_file(passport_photo.filename)}")

        if passport_photo and allowed_file(passport_photo.filename):
            filename = secure_filename(passport_photo.filename)
            unique_filename = str(uuid.uuid4()) + os.path.splitext(filename)[1]
            current_app.logger.debug(f"Generated unique filename: {unique_filename}")
            try:
                os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
                passport_photo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                current_app.logger.debug(f"UPLOAD_FOLDER: {current_app.config['UPLOAD_FOLDER']}")
                current_app.logger.debug(f"Full passport photo path: {passport_photo_path}")
                passport_photo.save(passport_photo_path)
                passport_photo_filename = unique_filename
            except Exception as e:
                errors['passport_photo'] = f'파일 저장 중 오류가 발생했습니다: {e}'
        elif passport_photo and passport_photo.filename != '':
            errors['passport_photo'] = '허용되지 않는 파일 형식입니다. (png, jpg, jpeg, gif, pdf만 허용)'

        if errors:
            # 오류 발생 시 JSON 응답 반환 (디버깅용)
            return jsonify(errors=errors), 400 # HTTP 400 Bad Request

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            current_time = datetime.now().isoformat()
            customer_id = str(time.time_ns())

            # 고객 생성
            cursor.execute("""
                INSERT INTO customers (id, name, email, phone, address, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (customer_id, name, email, phone, address, notes, current_time, current_time))

            passport_info_id = None
            any_passport_field = any([passport_number, last_name_eng, first_name_eng, expiry_date, passport_photo_filename])

            if any_passport_field:
                # PassportInfo 테이블에 삽입 (customer_id와 함께)
                cursor.execute("""
                    INSERT INTO passport_info (customer_id, passport_number, last_name_eng, first_name_eng, expiry_date, passport_photo_path, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (customer_id, passport_number, last_name_eng, first_name_eng, expiry_date, passport_photo_filename, current_time, current_time))
                passport_info_id = cursor.lastrowid

                # 고객 테이블에 passport_info_id 업데이트
                cursor.execute("""
                    UPDATE customers SET passport_info_id = ? WHERE id = ?
                """, (passport_info_id, customer_id))

            conn.commit()
            # g.user 객체 내용 디버그 로그 출력
            current_app.logger.debug(f"g.user type: {type(g.user)}")
            current_app.logger.debug(f"g.user content: {g.user}")

            current_user_name = g.user['username'] if 'username' in g.user else g.user.get('username', 'unknown_user')
            log_customer_change(customer_id, 'CREATE', 'all', None, name, current_user_name, '새 고객 생성')
            return redirect(url_for('customer.customers_page'))
        except sqlite3.IntegrityError as e:
            conn.rollback()
            errors['database'] = f'데이터베이스 오류: {e}'
            return jsonify(errors=errors), 500
        except Exception as e:
            if conn: conn.rollback()
            current_app.logger.error(f"고객 생성 오류: {e}")
            errors['general'] = f'고객 생성 중 오류가 발생했습니다: {e}'
            return jsonify(errors=errors), 500
        finally:
            if conn: conn.close()
    
    return render_template('create_customer.html')

@customer_bp.route('/<string:customer_id>', methods=['GET', 'POST'])
@jwt_required(current_app)
def edit_customer_page(customer_id):
    """고객 수정 페이지"""
    conn = None
    errors = {}
    customer = None
    passport_info = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 고객 정보와 연결된 passport_info_id 가져오기
        cursor.execute('SELECT id, name, phone, email, address, notes, passport_info_id FROM customers WHERE id = ?', (customer_id,))
        customer = cursor.fetchone()

        if not customer:
            flash('고객을 찾을 수 없습니다.', 'error')
            return redirect(url_for('customer.customers_page'))

        # 고객 ID로 PassportInfo 가져오기 또는 생성 (만약 없다면)
        if customer['passport_info_id']:
            cursor.execute('SELECT * FROM passport_info WHERE id = ?', (customer['passport_info_id'],))
            passport_info = cursor.fetchone()

        if request.method == 'POST':
            name = request.form.get('name')
            phone = request.form.get('phone')
            email = request.form.get('email')
            address = request.form.get('address')
            notes = request.form.get('notes')
            passport_number = request.form.get('passport_number')
            last_name_eng = request.form.get('last_name_eng')
            first_name_eng = request.form.get('first_name_eng')
            expiry_date = request.form.get('expiry_date')
            delete_passport_photo = request.form.get('delete_passport_photo') == 'true'
            passport_photo_file = request.files.get('passport_photo')

            if not name:
                errors['name'] = '이름은 필수입니다.'
            if not phone:
                errors['phone'] = '전화번호는 필수입니다.'
            
            if errors:
                # 에러 발생 시 현재 고객 및 여권 정보, 제출된 폼 데이터를 다시 템플릿으로 전달
                return render_template('edit_customer.html', customer=customer, passport_info=passport_info, errors=errors, request_form=request.form)

            current_time = datetime.now().isoformat()
            updated_passport_photo_filename = passport_info['passport_photo_path'] if passport_info else None

            # 변경 사항을 추적하기 위한 기존 고객 데이터 저장
            old_customer_data = dict(customer)
            old_passport_info_data = dict(passport_info) if passport_info else {}

            current_app.logger.debug(f"Edit Customer - Passport photo received: {bool(passport_photo_file)}")
            if passport_photo_file and passport_photo_file.filename != '':
                current_app.logger.debug(f"Edit Customer - Passport photo filename: {passport_photo_file.filename}")
                current_app.logger.debug(f"Edit Customer - Is allowed file: {allowed_file(passport_photo_file.filename)}")

            # 기존 파일 삭제 요청 처리
            if delete_passport_photo and updated_passport_photo_filename:
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], updated_passport_photo_filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    current_app.logger.debug(f"Existing passport photo deleted: {file_path}")
                updated_passport_photo_filename = None

            # 새 파일 업로드 처리
            if passport_photo_file and allowed_file(passport_photo_file.filename):
                filename = secure_filename(passport_photo_file.filename)
                unique_filename = str(uuid.uuid4()) + os.path.splitext(filename)[1]
                current_app.logger.debug(f"Edit Customer - Generated unique filename: {unique_filename}")
                try:
                    os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
                    passport_photo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                    current_app.logger.debug(f"Edit Customer - UPLOAD_FOLDER: {current_app.config['UPLOAD_FOLDER']}")
                    current_app.logger.debug(f"Edit Customer - Full passport photo path: {passport_photo_path}")
                    passport_photo_file.save(passport_photo_path)
                    updated_passport_photo_filename = unique_filename
                    current_app.logger.debug(f"Edit Customer - New passport photo saved: {updated_passport_photo_filename}")
                except Exception as e:
                    errors['passport_photo'] = f'새 파일 저장 중 오류가 발생했습니다: {e}'
            elif passport_photo_file and passport_photo_file.filename != '':
                errors['passport_photo'] = '허용되지 않는 파일 형식입니다. (png, jpg, jpeg, gif, pdf만 허용)'
            
            if errors:
                return render_template('edit_customer.html', customer=customer, passport_info=passport_info, errors=errors, request_form=request.form)

            # 고객 정보 업데이트
            cursor.execute("""
                UPDATE customers
                SET name = ?, phone = ?, email = ?, address = ?, notes = ?, updated_at = ?
                WHERE id = ?
            """, (name, phone, email, address, notes, current_time, customer_id))
            
            passport_info_data = (
                passport_number, last_name_eng, first_name_eng, expiry_date, updated_passport_photo_filename,
                current_time
            )

            if passport_info:
                # 기존 여권 정보 업데이트
                cursor.execute("""
                    UPDATE passport_info
                    SET passport_number = ?, last_name_eng = ?, first_name_eng = ?, expiry_date = ?, passport_photo_path = ?, updated_at = ?
                    WHERE id = ?
                """, (*passport_info_data, passport_info['id']))
            else:
                # 새 여권 정보 삽입 및 고객에 연결
                current_app.logger.debug(f"Inserting new passport_info for customer_id: {customer_id}")
                current_app.logger.debug(f"Passport info data: {passport_info_data}")
                cursor.execute("""
                    INSERT INTO passport_info (customer_id, passport_number, last_name_eng, first_name_eng, expiry_date, passport_photo_path, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (customer_id, *passport_info_data, current_time))
                new_passport_info_id = cursor.lastrowid
                cursor.execute("""
                    UPDATE customers SET passport_info_id = ? WHERE id = ?
                """, (new_passport_info_id, customer_id))
            
            conn.commit()

            # 변경 로그 기록
            changed_by = g.user['username'] if 'username' in g.user else g.user.get('username', 'unknown')
            
            # 고객 상세 정보 필드 비교 및 로깅
            customer_fields = ['name', 'phone', 'email', 'address', 'notes']
            for field in customer_fields:
                old_value = old_customer_data.get(field, '') or ''
                new_value = request.form.get(field, '') or ''
                if old_value != new_value:
                    log_customer_change(customer_id, 'UPDATE', field, old_value, new_value, changed_by, f'{field} 변경')

            # 여권 정보 필드 비교 및 로깅
            passport_fields = {
                'passport_number': passport_number,
                'last_name_eng': last_name_eng,
                'first_name_eng': first_name_eng,
                'expiry_date': expiry_date,
                'passport_photo_path': updated_passport_photo_filename
            }

            for field, new_val in passport_fields.items():
                old_val = old_passport_info_data.get(field, '') or ''
                # passport_photo_path는 파일명만 비교
                if field == 'passport_photo_path':
                    # 기존 경로에서 파일명만 추출 (full_file_path로 저장된 경우)
                    old_filename = os.path.basename(old_val) if old_val else ''
                    new_filename = os.path.basename(new_val) if new_val else ''
                    if old_filename != new_filename:
                         log_customer_change(customer_id, 'UPDATE', field, old_filename, new_filename, changed_by, f'{field} 변경')
                elif old_val != (new_val or ''):
                    log_customer_change(customer_id, 'UPDATE', field, old_val, (new_val or ''), changed_by, f'{field} 변경')

            flash('고객 정보가 성공적으로 업데이트되었습니다.', 'success')
            return redirect(url_for('customer.edit_customer_page', customer_id=customer_id))

    except sqlite3.IntegrityError as e:
        if conn: conn.rollback()
        current_app.logger.error(f"고객 수정 중 데이터베이스 무결성 오류: {e}")
        errors['database'] = f'데이터베이스 오류: {e}'
    except Exception as e:
        if conn: conn.rollback()
        current_app.logger.error(f"고객 수정 오류: {e}")
        errors['general'] = f'고객 수정 중 오류가 발생했습니다: {e}'
    finally:
        if conn: conn.close()
    
    # 에러 발생 또는 GET 요청 시 템플릿 렌더링
    return render_template('edit_customer.html', customer=customer, passport_info=passport_info, errors=errors, request_form=request.form if errors else None)

@customer_bp.route('/api/customers/extract-passport-info', methods=['POST'])
@jwt_required(current_app)
def extract_passport_info_api():
    """업로드된 여권 사진에서 정보를 추출하는 API 엔드포인트"""
    file = request.files.get('passport_photo')
    existing_photo_path_relative = request.form.get('existing_photo_path')
    
    file_path_to_ocr = None
    temp_file_created = False

    if file and file.filename != '':
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = str(uuid.uuid4()) + os.path.splitext(filename)[1]
            file_path_to_ocr = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(file_path_to_ocr)
            temp_file_created = True
        else:
            return jsonify({'error': '허용되지 않는 파일 형식입니다. (png, jpg, jpeg, gif, pdf만 허용)'}), 400
    elif existing_photo_path_relative:
        file_path_to_ocr = os.path.join(current_app.config['UPLOAD_FOLDER'], existing_photo_path_relative)
        current_app.logger.debug(f"Attempting to access existing file at: {file_path_to_ocr}")
        current_app.logger.debug(f"File exists: {os.path.exists(file_path_to_ocr)}")
        if not os.path.exists(file_path_to_ocr):
            return jsonify({'error': '기존 여권 사진 파일을 찾을 수 없습니다.'}), 404
    else:
        return jsonify({'error': '파일이 없거나 파일 이름이 없습니다.'}), 400

    try:
        # OCR을 사용하여 텍스트 추출
        extracted_text = extract_text_from_image(file_path_to_ocr)
        
        # 추출된 텍스트에서 여권 정보 파싱
        passport_data = extract_passport_info(extracted_text)
        
        # 임시 파일 삭제 (새로 업로드된 파일인 경우에만)
        if temp_file_created and os.path.exists(file_path_to_ocr):
            os.remove(file_path_to_ocr)

        if not passport_data or all(value is None for value in passport_data.values()):
            return jsonify({'message': '여권 정보를 추출할 수 없습니다. 더 선명한 사진을 사용하거나 수동으로 입력해주세요.', 'extracted_data': {}}), 200

        return jsonify({'message': '여권 정보가 성공적으로 추출되었습니다.', 'extracted_data': passport_data}), 200

    except Exception as e:
        current_app.logger.error(f"여권 정보 추출 오류: {e}")
        # 오류 발생 시 임시 파일 삭제 시도
        if temp_file_created and os.path.exists(file_path_to_ocr):
            os.remove(file_path_to_ocr)
        return jsonify({'error': f'여권 정보 추출 중 오류가 발생했습니다: {e}'}), 500

@customer_bp.route('/export-excel')
@jwt_required(current_app)
def export_customers_excel():
    """고객 데이터를 엑셀 파일로 내보내기"""
    try:
        excel_data = export_customers_to_excel()
        
        response = make_response(excel_data)
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=customers.xlsx'
        
        return response
    except Exception as e:
        print(f'고객 엑셀 내보내기 오류: {e}')
        flash('엑셀 파일 생성 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('customer.customers_page'))

@customer_bp.route('/import-excel', methods=['GET', 'POST'])
@jwt_required(current_app)
def import_customers_excel():
    """엑셀 파일에서 고객 데이터 가져오기"""
    if request.method == 'GET':
        return render_template('import_customers_excel.html')
    
    try:
        if 'file' not in request.files:
            flash('파일을 선택해주세요.', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('파일을 선택해주세요.', 'error')
            return redirect(request.url)
        
        # 파일 업로드 시 확장자 체크 강화
        allowed_ext = ('.xlsx', '.xls')
        if not file.filename.lower().endswith(allowed_ext):
            raise ValidationError('엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.')
        
        # 파일 내용 읽기
        file_content = file.read()
        
        # 엑셀 데이터 가져오기
        result = import_customers_from_excel(file_content)
        
        if result['success_count'] > 0:
            flash(f'{result["success_count"]}명의 고객이 성공적으로 추가되었습니다.', 'success')
        
        if result['error_count'] > 0:
            flash(f'{result["error_count"]}개의 오류가 발생했습니다.', 'error')
            for error in result['errors']:
                flash(error, 'error')
        
        return redirect(url_for('customer.customers_page'))
        
    except Exception as e:
        print(f'고객 엑셀 가져오기 오류: {e}')
        flash('엑셀 파일 처리 중 오류가 발생했습니다.', 'error')
        return redirect(request.url)
