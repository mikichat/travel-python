from flask import Blueprint, render_template, request, jsonify, current_app, make_response, redirect, url_for, flash
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

customer_bp = Blueprint('customer', __name__)

# 필터 등록
@customer_bp.app_template_filter('format_date')
def format_date_filter(date_str):
    return format_date(date_str)

@customer_bp.app_template_filter('format_datetime')
def format_datetime_filter(datetime_str):
    return format_datetime(datetime_str)

@customer_bp.route('/')
@jwt_required(current_app)
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
        per_page = request.args.get('per_page', 10, type=int)

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
    """고객 목록 API (기존) - 이제 사용되지 않거나 다른 목적으로 사용될 수 있음"""
    # 이 API는 이제 사용되지 않거나, 전체 목록이 필요한 경우에만 호출될 수 있습니다.
    # pagination API를 사용하는 것이 좋습니다.
    return get_paginated_customers_api(offset=0, limit=100000) # 더미 값으로 무한대를 대체합니다.

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

        # 고객 생성
        cursor.execute("""
            INSERT INTO customers (name, email, phone, address, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, email, phone, address, current_time, current_time))
        
        new_customer_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        flash('고객이 성공적으로 추가되었습니다.', 'success')
        return redirect(url_for('customer.customers_page'))
    except APIError:
        raise
    except Exception as e:
        print(f'고객 등록 오류: {e}')
        raise APIError('고객 등록 중 오류가 발생했습니다.', 500)

@customer_bp.route('/api/customers/<int:customer_id>', methods=['GET'])
@jwt_required(current_app)
def get_customer_by_id(customer_id):
    """특정 고객 조회 API"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, phone, email, address, notes, created_at, updated_at FROM customers WHERE id = ?', (customer_id,))
        customer = cursor.fetchone()
        conn.close()

        if not customer:
            raise APIError('고객을 찾을 수 없습니다.', 404)

        customer_data = dict(customer)
        customer_data['createdAt'] = customer_data.pop('created_at')
        customer_data['updatedAt'] = customer_data.pop('updated_at')

        return jsonify(customer_data)
    except APIError:
        raise
    except Exception as e:
        print(f'고객 조회 실패: {e}')
        raise APIError('고객 조회 중 오류가 발생했습니다.', 500)

@customer_bp.route('/api/customers/<int:customer_id>', methods=['PUT'])
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
        cursor.execute('SELECT name, phone, email, address, notes FROM customers WHERE id = ?', (customer_id,))
        old_customer = cursor.fetchone()
        
        if not old_customer:
            conn.close()
            raise APIError('고객을 찾을 수 없습니다.', 404)
        
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
        if old_customer['name'] != name:
            changes.append(f"이름: {old_customer['name']} → {name}")
            log_customer_change(customer_id, 'UPDATE', 'name', old_customer['name'], name, 'admin')
        if old_customer['phone'] != phone:
            changes.append(f"전화번호: {old_customer['phone']} → {phone}")
            log_customer_change(customer_id, 'UPDATE', 'phone', old_customer['phone'], phone, 'admin')
        if old_customer['email'] != email:
            changes.append(f"이메일: {old_customer['email']} → {email}")
            log_customer_change(customer_id, 'UPDATE', 'email', old_customer['email'], email, 'admin')
        if old_customer['address'] != address:
            changes.append(f"주소: {old_customer['address']} → {address}")
            log_customer_change(customer_id, 'UPDATE', 'address', old_customer['address'], address, 'admin')
        if old_customer['notes'] != notes:
            changes.append(f"메모: {old_customer['notes']} → {notes}")
            log_customer_change(customer_id, 'UPDATE', 'notes', old_customer['notes'], notes, 'admin')
        
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

@customer_bp.route('/api/customers/<int:customer_id>', methods=['DELETE'])
@jwt_required(current_app)
def delete_customer(customer_id):
    """고객 삭제 API"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 예약이 있는지 확인
        cursor.execute('SELECT COUNT(*) FROM reservations WHERE customer_id = ?', (customer_id,))
        reservations_count = cursor.fetchone()[0]

        if reservations_count > 0:
            conn.close()
            raise APIError('예약이 있는 고객은 삭제할 수 없습니다.', 400)

        # 삭제 전 고객 정보 조회
        cursor.execute('SELECT name FROM customers WHERE id = ?', (customer_id,))
        customer = cursor.fetchone()
        customer_name = customer[0] if customer else 'Unknown'

        cursor.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
        conn.commit()
        
        conn.close()

        return redirect(url_for('customer.customers_page'))
    except APIError:
        raise
    except Exception as e:
        print(f'고객 삭제 오류: {e}')
        raise APIError('고객 삭제 중 오류가 발생했습니다.', 500)

@customer_bp.route('/delete/<int:customer_id>', methods=['POST'])
@jwt_required(current_app)
def delete_customer_page(customer_id):
    """고객 삭제 페이지"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 예약이 있는지 확인
        cursor.execute('SELECT COUNT(*) FROM reservations WHERE customer_id = ?', (customer_id,))
        reservations_count = cursor.fetchone()[0]

        if reservations_count > 0:
            conn.close()
            return render_template('customers.html', error='예약이 있는 고객은 삭제할 수 없습니다.')

        cursor.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
        conn.commit()
        conn.close()

        return redirect(url_for('customer.customers_page'))
    except Exception as e:
        print(f'고객 삭제 오류: {e}')
        return render_template('customers.html', error='고객 삭제 중 오류가 발생했습니다.')

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
    """고객 생성 페이지"""
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email', '')
        address = request.form.get('address', '')
        notes = request.form.get('notes', '')

        if not name or not phone:
            return render_template('create_customer.html', error='이름과 전화번호는 필수입니다.')

        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().isoformat()

        try:
            cursor.execute("""
                INSERT INTO customers (name, phone, email, address, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, phone, email, address, notes, current_time, current_time))
            conn.commit()
            
            # 새로 생성된 고객 ID 가져오기
            new_customer_id = cursor.lastrowid
            
            conn.close()
            return redirect(url_for('customer.customers_page'))
        except Exception as e:
            conn.close()
            print(f'고객 등록 오류: {e}')
            return render_template('create_customer.html', error='고객 등록 중 오류가 발생했습니다.')

    return render_template('create_customer.html')

@customer_bp.route('/<int:customer_id>', methods=['GET', 'POST'])
@jwt_required(current_app)
def edit_customer_page(customer_id):
    """고객 수정 페이지"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, phone, email, address, notes FROM customers WHERE id = ?', (customer_id,))
    customer = cursor.fetchone()
    conn.close()

    if not customer:
        return render_template('customers.html', error='고객을 찾을 수 없습니다.')

    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email', '')
        address = request.form.get('address', '')
        notes = request.form.get('notes', '')

        if not name or not phone:
            return render_template('edit_customer.html', customer=customer, error='이름과 전화번호는 필수입니다.')

        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().isoformat()

        try:
            # 변경된 필드 추적
            changes = []
            if customer['name'] != name:
                changes.append(f"이름: {customer['name']} → {name}")
                log_customer_change(customer_id, 'UPDATE', 'name', customer['name'], name, 'admin')
            if customer['phone'] != phone:
                changes.append(f"전화번호: {customer['phone']} → {phone}")
                log_customer_change(customer_id, 'UPDATE', 'phone', customer['phone'], phone, 'admin')
            if customer['email'] != email:
                changes.append(f"이메일: {customer['email']} → {email}")
                log_customer_change(customer_id, 'UPDATE', 'email', customer['email'], email, 'admin')
            if customer['address'] != address:
                changes.append(f"주소: {customer['address']} → {address}")
                log_customer_change(customer_id, 'UPDATE', 'address', customer['address'], address, 'admin')
            if customer['notes'] != notes:
                changes.append(f"메모: {customer['notes']} → {notes}")
                log_customer_change(customer_id, 'UPDATE', 'notes', customer['notes'], notes, 'admin')
            
            cursor.execute("""
                UPDATE customers
                SET name = ?, phone = ?, email = ?, address = ?, notes = ?, updated_at = ?
                WHERE id = ?
            """, (name, phone, email, address, notes, current_time, customer_id))
            conn.commit()
            
            conn.close()
            return redirect(url_for('customer.customers_page'))
        except Exception as e:
            conn.close()
            print(f'고객 수정 오류: {e}')
            return render_template('edit_customer.html', customer=customer, error='고객 수정 중 오류가 발생했습니다.')

    return render_template('edit_customer.html', customer=customer)

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
        
        if not file.filename.endswith(('.xlsx', '.xls')):
            flash('엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.', 'error')
            return redirect(request.url)
        
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
