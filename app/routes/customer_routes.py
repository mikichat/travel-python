from flask import Blueprint, render_template, request, jsonify, current_app, make_response, redirect, url_for
from datetime import datetime
import csv
import io
from database import get_db_connection
from app.utils.errors import APIError
from app.utils.auth import jwt_required

customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/')
@jwt_required(current_app)
def customers_page():
    """고객 목록 페이지"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, phone, email, address, notes, created_at, updated_at FROM customers ORDER BY created_at DESC')
        customers = cursor.fetchall()
        conn.close()
        
        # sqlite3.Row 객체를 딕셔너리로 변환
        customers_list = []
        for customer in customers:
            customer_dict = dict(customer)
            customers_list.append(customer_dict)
        
        # 페이지네이션 변수들 설정 (현재는 단순화)
        total_customers_count = len(customers_list)
        current_page = 1
        items_per_page = 20
        total_pages = 1
        
        return render_template('customers.html', 
                             customers=customers_list,
                             total_customers_count=total_customers_count,
                             current_page=current_page,
                             items_per_page=items_per_page,
                             total_pages=total_pages)
    except Exception as e:
        print(f'고객 목록 조회 오류: {e}')
        return render_template('customers.html', error='고객 목록을 불러오는 중 오류가 발생했습니다.')

@customer_bp.route('/api/customers', methods=['GET'])
@jwt_required(current_app)
def get_customers():
    """고객 목록 API"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, phone, email, address, notes, created_at, updated_at FROM customers ORDER BY created_at DESC')
        customers = cursor.fetchall()
        conn.close()

        # 컬럼 이름을 camelCase로 변환
        customers_list = []
        for customer in customers:
            customer_data = dict(customer)
            customer_data['createdAt'] = customer_data.pop('created_at')
            customer_data['updatedAt'] = customer_data.pop('updated_at')
            customers_list.append(customer_data)

        return jsonify(customers_list)
    except Exception as e:
        print(f'고객 조회 실패: {e}')
        raise APIError('고객 조회 중 오류가 발생했습니다.', 500)

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

        cursor.execute("""
            INSERT INTO customers (name, phone, email, address, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, phone, email, address, notes, current_time, current_time))
        conn.commit()

        new_customer_id = cursor.lastrowid
        cursor.execute('SELECT id, name, phone, email, address, notes, created_at, updated_at FROM customers WHERE id = ?', (new_customer_id,))
        new_customer = cursor.fetchone()
        conn.close()

        if not new_customer:
            raise APIError('고객 등록 후 정보를 찾을 수 없습니다.', 500)

        new_customer_data = dict(new_customer)
        new_customer_data['createdAt'] = new_customer_data.pop('created_at')
        new_customer_data['updatedAt'] = new_customer_data.pop('updated_at')

        return jsonify(new_customer_data), 201
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
    """고객 정보 수정 API"""
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

        cursor.execute("""
            UPDATE customers
            SET name = ?, phone = ?, email = ?, address = ?, notes = ?, updated_at = ?
            WHERE id = ?
        """, (name, phone, email, address, notes, current_time, customer_id))
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            raise APIError('고객을 찾을 수 없습니다.', 404)

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

        cursor.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            raise APIError('고객을 찾을 수 없습니다.', 404)
        
        conn.close()
        return jsonify({'message': '고객이 삭제되었습니다.'})
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
