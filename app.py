from flask import Flask, render_template, request, jsonify, session, redirect, url_for, make_response
import os
import bcrypt
import jwt
from database import get_db_connection, initialize_database
from functools import wraps
from datetime import datetime
from math import ceil
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('JWT_SECRET', 'your-secret-key') # JWT secret key
app.config['FLASK_SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', os.urandom(24)) # Flask session secret key

# Jinja2 사용자 정의 필터 등록
@app.template_filter('get_emoji_for_rank')
def get_emoji_for_rank(rank):
    if rank == 1: return '🥇'
    if rank == 2: return '🥈'
    if rank == 3: return '🥉'
    return '🏅'

@app.template_filter('get_status_color')
def get_status_color(status):
    if status == 'Confirmed': return 'bg-green-100 text-green-600'
    if status == 'Pending': return 'bg-yellow-100 text-yellow-600'
    if status == 'Cancelled': return 'bg-red-100 text-red-600'
    return 'bg-gray-100 text-gray-600'

@app.template_filter('get_status_text')
def get_status_text(status):
    if status == 'Confirmed': return '확정'
    if status == 'Pending': return '대기'
    if status == 'Cancelled': return '취소'
    return status

# JWT 인증 데코레이터
def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # 웹 페이지 요청인 경우 Flask 세션을 먼저 확인
        if not request.path.startswith('/api/') and session.get('logged_in'):
            request.user_id = session.get('user_id')
            return f(*args, **kwargs)

        # API 호출이거나 Flask 세션에 로그인 정보가 없는 경우 JWT 확인
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            if request.path.startswith('/api/') or request.path.startswith('/auth/'): # auth/register도 포함
                return jsonify({'success': False, 'error': '인증 토큰이 필요합니다.'}), 401
            else:
                session.pop('logged_in', None)
                session.pop('user_id', None)
                session.pop('username', None)
                return redirect(url_for('login_page', error='세션이 만료되었거나 인증 토큰이 없습니다. 다시 로그인해주세요.'))

        token = auth_header.split(' ')[1]

        try:
            decoded_token = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user_id = decoded_token['userId']  # 사용자 ID를 request 객체에 저장
        except jwt.ExpiredSignatureError:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': '인증 토큰이 만료되었습니다.'}), 401
            else:
                session.pop('logged_in', None)
                session.pop('user_id', None)
                session.pop('username', None)
                return redirect(url_for('login_page', error='세션이 만료되었습니다. 다시 로그인해주세요.'))
        except jwt.InvalidTokenError:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': '유효하지 않은 인증 토큰입니다.'}), 401
            else:
                session.pop('logged_in', None)
                session.pop('user_id', None)
                session.pop('username', None)
                return redirect(url_for('login_page', error='유효하지 않은 세션입니다. 다시 로그인해주세요.'))
        except Exception as e:
            print(f'JWT 인증 오류: {e}')
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': '인증 확인 중 오류가 발생했습니다.'}), 500
            else:
                session.pop('logged_in', None)
                session.pop('user_id', None)
                session.pop('username', None)
                return redirect(url_for('login_page', error='인증 확인 중 오류가 발생했습니다.'))

        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['logged_in'] = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard')) # 로그인 성공 시 대시보드로 리디렉션
        else:
            error = '사용자명 또는 비밀번호가 올바르지 않습니다.'
            return render_template('login.html', error=error, username=username)
    return render_template('login.html')

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'success': False, 'error': '사용자명과 비밀번호를 입력해주세요.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, password, created_at, updated_at FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            return jsonify({'success': False, 'error': '사용자명 또는 비밀번호가 올바르지 않습니다.'}), 401

        token = jwt.encode(
            {'userId': user['id'], 'username': user['username']},
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )

        user_data = dict(user)
        user_data.pop('password') # 비밀번호는 응답에서 제외
        user_data['createdAt'] = user['created_at']
        user_data['updatedAt'] = user['updated_at']

        return jsonify({
            'success': True,
            'user': user_data,
            'token': token
        }), 200
    except Exception as e:
        print(f'로그인 오류: {e}')
        return jsonify({'success': False, 'error': '로그인 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/auth/me', methods=['GET'])
@jwt_required
def me():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, email, created_at, updated_at FROM users WHERE id = ?', (request.user_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({'success': False, 'error': '사용자를 찾을 수 없습니다.'}), 404

    user_data = dict(user)
    user_data['createdAt'] = user['created_at']
    user_data['updatedAt'] = user['updated_at']

    return jsonify({'success': True, 'user': user_data})

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        error = None

        if not username or not email or not password or not confirm_password:
            error = '모든 필드를 입력해주세요.'
        elif password != confirm_password:
            error = '비밀번호가 일치하지 않습니다.'
        elif len(username) < 3:
            error = '사용자명은 3자 이상이어야 합니다.'
        elif len(password) < 6:
            error = '비밀번호는 6자 이상이어야 합니다.'
        
        if error:
            return render_template('register.html', error=error, username=username, email=email)

        conn = get_db_connection()
        cursor = conn.cursor()

        # 사용자명 중복 확인
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        existing_user = cursor.fetchone()
        if existing_user:
            conn.close()
            error = '이미 사용 중인 사용자명입니다.'
            return render_template('register.html', error=error, username=username, email=email)

        # 이메일 중복 확인
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        existing_email = cursor.fetchone()
        if existing_email:
            conn.close()
            error = '이미 사용 중인 이메일입니다.'
            return render_template('register.html', error=error, username=username, email=email)

        # 비밀번호 해시화
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')

        try:
            cursor.execute("""
                INSERT INTO users (username, email, password, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (username, email, hashed_password, datetime.now().isoformat(), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return redirect(url_for('login_page')) # 회원가입 성공 시 로그인 페이지로 리디렉션
        except Exception as e:
            conn.close()
            print(f'회원가입 오류: {e}')
            error = '회원가입 처리 중 오류가 발생했습니다. 다시 시도해주세요.'
            return render_template('register.html', error=error, username=username, email=email)

    return render_template('register.html')

@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not username or not email or not password:
            return jsonify({'success': False, 'error': '모든 필드를 입력해주세요.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 사용자명 중복 확인
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        existing_user = cursor.fetchone()
        if existing_user:
            conn.close()
            return jsonify({'success': False, 'error': '이미 사용 중인 사용자명입니다.'}), 400

        # 이메일 중복 확인
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        existing_email = cursor.fetchone()
        if existing_email:
            conn.close()
            return jsonify({'success': False, 'error': '이미 사용 중인 이메일입니다.'}), 400

        # 비밀번호 해시화
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')

        # 사용자 등록
        cursor.execute("""
            INSERT INTO users (username, email, password, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (username, email, hashed_password, datetime.now().isoformat(), datetime.now().isoformat()))
        conn.commit()

        # 등록된 사용자 정보 조회
        new_user_id = cursor.lastrowid
        cursor.execute('SELECT id, username, email, created_at, updated_at FROM users WHERE id = ?', (new_user_id,))
        new_user = cursor.fetchone()
        conn.close()

        if not new_user:
            return jsonify({'success': False, 'error': '사용자 등록 후 정보를 찾을 수 없습니다.'}), 500

        # JWT 토큰 생성
        token = jwt.encode(
            {'userId': new_user['id'], 'username': new_user['username']},
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )

        new_user_data = dict(new_user)
        # password는 애초에 조회하지 않았으므로 del 필요 없음
        new_user_data['createdAt'] = new_user['created_at']
        new_user_data['updatedAt'] = new_user['updated_at']

        return jsonify({
            'success': True,
            'user': new_user_data,
            'token': token
        }), 201

    except Exception as e:
        print(f'회원가입 오류: {e}')
        return jsonify({'success': False, 'error': '회원가입 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/customers', methods=['GET'])
@jwt_required
def get_customers():
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
        return jsonify({'error': '고객 조회 실패'}), 500

@app.route('/api/customers', methods=['POST'])
@jwt_required
def create_customer():
    try:
        data = request.get_json()
        name = data.get('name')
        phone = data.get('phone')
        email = data.get('email', '')
        address = data.get('address', '')
        notes = data.get('notes', '')

        if not name or not phone:
            return jsonify({'error': '이름과 전화번호는 필수입니다.'}), 400

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
            return jsonify({'error': '고객 등록 후 정보를 찾을 수 없습니다.'}), 500

        new_customer_data = dict(new_customer)
        new_customer_data['createdAt'] = new_customer_data.pop('created_at')
        new_customer_data['updatedAt'] = new_customer_data.pop('updated_at')

        return jsonify(new_customer_data), 201
    except Exception as e:
        print(f'고객 등록 오류: {e}')
        return jsonify({'error': '고객 등록 실패'}), 500

@app.route('/api/customers/<int:customer_id>', methods=['GET'])
@jwt_required
def get_customer_by_id(customer_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, phone, email, address, notes, created_at, updated_at FROM customers WHERE id = ?', (customer_id,))
        customer = cursor.fetchone()
        conn.close()

        if not customer:
            return jsonify({'error': '고객을 찾을 수 없습니다.'}), 404
        
        customer_data = dict(customer)
        customer_data['createdAt'] = customer_data.pop('created_at')
        customer_data['updatedAt'] = customer_data.pop('updated_at')

        return jsonify(customer_data)
    except Exception as e:
        print(f'고객 조회 실패: {e}')
        return jsonify({'error': '고객 조회 실패'}), 500

@app.route('/api/customers/<int:customer_id>', methods=['PUT'])
@jwt_required
def update_customer(customer_id):
    try:
        data = request.get_json()
        name = data.get('name')
        phone = data.get('phone')
        email = data.get('email', '')
        address = data.get('address', '')
        notes = data.get('notes', '')

        if not name or not phone:
            return jsonify({'error': '이름과 전화번호는 필수입니다.'}), 400

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
            return jsonify({'error': '고객을 찾을 수 없습니다.'}), 404

        cursor.execute('SELECT id, name, phone, email, address, notes, created_at, updated_at FROM customers WHERE id = ?', (customer_id,))
        updated_customer = cursor.fetchone()
        conn.close()

        updated_customer_data = dict(updated_customer)
        updated_customer_data['createdAt'] = updated_customer_data.pop('created_at')
        updated_customer_data['updatedAt'] = updated_customer_data.pop('updated_at')

        return jsonify(updated_customer_data)
    except Exception as e:
        print(f'고객 수정 오류: {e}')
        return jsonify({'error': '고객 수정 실패'}), 500

@app.route('/api/customers/<int:customer_id>', methods=['DELETE'])
@jwt_required
def delete_customer(customer_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 예약이 있는지 확인
        cursor.execute('SELECT COUNT(*) FROM reservations WHERE customer_id = ?', (customer_id,))
        reservations_count = cursor.fetchone()[0]

        if reservations_count > 0:
            conn.close()
            return jsonify({'error': '예약이 있는 고객은 삭제할 수 없습니다.'}), 400

        cursor.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': '고객을 찾을 수 없습니다.'}), 404
        
        conn.close()
        return jsonify({'message': '고객이 삭제되었습니다.'})
    except Exception as e:
        print(f'고객 삭제 오류: {e}')
        return jsonify({'error': '고객 삭제 실패'}), 500

@app.route('/api/schedules', methods=['GET'])
@jwt_required
def get_schedules():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, description, start_date, end_date, destination, price, max_people, status, duration, region, meeting_date, meeting_time, meeting_place, manager, reservation_maker, reservation_maker_contact, important_docs, currency_info, other_items, memo, created_at, updated_at FROM schedules ORDER BY start_date DESC')
        schedules = cursor.fetchall()
        conn.close()

        schedules_list = []
        for schedule in schedules:
            schedule_data = dict(schedule)
            # camelCase로 변환
            schedule_data['startDate'] = schedule_data.pop('start_date')
            schedule_data['endDate'] = schedule_data.pop('end_date')
            schedule_data['maxPeople'] = schedule_data.pop('max_people')
            schedule_data['meetingDate'] = schedule_data.pop('meeting_date')
            schedule_data['meetingTime'] = schedule_data.pop('meeting_time')
            schedule_data['meetingPlace'] = schedule_data.pop('meeting_place')
            schedule_data['reservationMaker'] = schedule_data.pop('reservation_maker')
            schedule_data['reservationMakerContact'] = schedule_data.pop('reservation_maker_contact')
            schedule_data['importantDocs'] = schedule_data.pop('important_docs')
            schedule_data['currencyInfo'] = schedule_data.pop('currency_info')
            schedule_data['otherItems'] = schedule_data.pop('other_items')
            schedule_data['createdAt'] = schedule_data.pop('created_at')
            schedule_data['updatedAt'] = schedule_data.pop('updated_at')
            schedules_list.append(schedule_data)

        return jsonify(schedules_list)
    except Exception as e:
        print(f'일정 조회 실패: {e}')
        return jsonify({'error': '일정 조회 실패'}), 500

@app.route('/api/schedules', methods=['POST'])
@jwt_required
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
            return jsonify({'error': '제목, 시작일, 종료일, 목적지는 필수입니다.'}), 400

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
        cursor.execute('SELECT id, title, description, start_date, end_date, destination, price, max_people, status, duration, region, meeting_date, meeting_time, meeting_place, manager, reservation_maker, reservation_maker_contact, important_docs, currency_info, other_items, memo, created_at, updated_at FROM schedules WHERE id = ?', (new_schedule_id,))
        new_schedule = cursor.fetchone()
        conn.close()

        if not new_schedule:
            return jsonify({'error': '일정 등록 후 정보를 찾을 수 없습니다.'}), 500

        new_schedule_data = dict(new_schedule)
        new_schedule_data['startDate'] = new_schedule_data.pop('start_date')
        new_schedule_data['endDate'] = new_schedule_data.pop('end_date')
        new_schedule_data['maxPeople'] = new_schedule_data.pop('max_people')
        new_schedule_data['meetingDate'] = new_schedule_data.pop('meeting_date')
        new_schedule_data['meetingTime'] = new_schedule_data.pop('meeting_time')
        new_schedule_data['meetingPlace'] = new_schedule_data.pop('meeting_place')
        new_schedule_data['reservationMaker'] = new_schedule_data.pop('reservation_maker')
        new_schedule_data['reservationMakerContact'] = new_schedule_data.pop('reservation_maker_contact')
        new_schedule_data['importantDocs'] = new_schedule_data.pop('important_docs')
        new_schedule_data['currencyInfo'] = new_schedule_data.pop('currency_info')
        new_schedule_data['otherItems'] = new_schedule_data.pop('other_items')
        new_schedule_data['createdAt'] = new_schedule_data.pop('created_at')
        new_schedule_data['updatedAt'] = new_schedule_data.pop('updated_at')

        return jsonify(new_schedule_data), 201
    except Exception as e:
        print(f'일정 등록 오류: {e}')
        return jsonify({'error': '일정 등록 실패'}), 500

@app.route('/api/schedules/<int:schedule_id>', methods=['GET'])
@jwt_required
def get_schedule_by_id(schedule_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, description, start_date, end_date, destination, price, max_people, status, duration, region, meeting_date, meeting_time, meeting_place, manager, reservation_maker, reservation_maker_contact, important_docs, currency_info, other_items, memo, created_at, updated_at FROM schedules WHERE id = ?', (schedule_id,))
        schedule = cursor.fetchone()
        conn.close()

        if not schedule:
            return jsonify({'error': '일정을 찾을 수 없습니다.'}), 404

        schedule_data = dict(schedule)
        schedule_data['startDate'] = schedule_data.pop('start_date')
        schedule_data['endDate'] = schedule_data.pop('end_date')
        schedule_data['maxPeople'] = schedule_data.pop('max_people')
        schedule_data['meetingDate'] = schedule_data.pop('meeting_date')
        schedule_data['meetingTime'] = schedule_data.pop('meeting_time')
        schedule_data['meetingPlace'] = schedule_data.pop('meeting_place')
        schedule_data['reservationMaker'] = schedule_data.pop('reservation_maker')
        schedule_data['reservationMakerContact'] = schedule_data.pop('reservation_maker_contact')
        schedule_data['importantDocs'] = schedule_data.pop('important_docs')
        schedule_data['currencyInfo'] = schedule_data.pop('currency_info')
        schedule_data['otherItems'] = schedule_data.pop('other_items')
        schedule_data['createdAt'] = schedule_data.pop('created_at')
        schedule_data['updatedAt'] = schedule_data.pop('updated_at')

        return jsonify(schedule_data)
    except Exception as e:
        print(f'일정 조회 실패: {e}')
        return jsonify({'error': '일정 조회 실패'}), 500

@app.route('/api/schedules/<int:schedule_id>', methods=['PUT'])
@jwt_required
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
            return jsonify({'error': '제목, 시작일, 종료일, 목적지는 필수입니다.'}), 400

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
            return jsonify({'error': '일정을 찾을 수 없습니다.'}), 404

        cursor.execute('SELECT id, title, description, start_date, end_date, destination, price, max_people, status, duration, region, meeting_date, meeting_time, meeting_place, manager, reservation_maker, reservation_maker_contact, important_docs, currency_info, other_items, memo, created_at, updated_at FROM schedules WHERE id = ?', (schedule_id,))
        updated_schedule = cursor.fetchone()
        conn.close()

        updated_schedule_data = dict(updated_schedule)
        updated_schedule_data['startDate'] = updated_schedule_data.pop('start_date')
        updated_schedule_data['endDate'] = updated_schedule_data.pop('end_date')
        updated_schedule_data['maxPeople'] = updated_schedule_data.pop('max_people')
        updated_schedule_data['meetingDate'] = updated_schedule_data.pop('meeting_date')
        updated_schedule_data['meetingTime'] = updated_schedule_data.pop('meeting_time')
        updated_schedule_data['meetingPlace'] = updated_schedule_data.pop('meeting_place')
        updated_schedule_data['reservationMaker'] = updated_schedule_data.pop('reservation_maker')
        updated_schedule_data['reservationMakerContact'] = updated_schedule_data.pop('reservation_maker_contact')
        updated_schedule_data['importantDocs'] = updated_schedule_data.pop('important_docs')
        updated_schedule_data['currencyInfo'] = updated_schedule_data.pop('currency_info')
        updated_schedule_data['otherItems'] = updated_schedule_data.pop('other_items')
        updated_schedule_data['createdAt'] = updated_schedule_data.pop('created_at')
        updated_schedule_data['updatedAt'] = updated_schedule_data.pop('updated_at')

        return jsonify(updated_schedule_data)
    except Exception as e:
        print(f'일정 수정 오류: {e}')
        return jsonify({'error': '일정 수정 실패'}), 500

@app.route('/api/schedules/<int:schedule_id>', methods=['DELETE'])
@jwt_required
def delete_schedule(schedule_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 예약이 있는지 확인
        cursor.execute('SELECT COUNT(*) FROM reservations WHERE schedule_id = ?', (schedule_id,))
        reservations_count = cursor.fetchone()[0]

        if reservations_count > 0:
            conn.close()
            return jsonify({'error': '예약이 있는 일정은 삭제할 수 없습니다.'}), 400

        cursor.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': '일정을 찾을 수 없습니다.'}), 404
        
        conn.close()
        return jsonify({'message': '일정이 삭제되었습니다.'})
    except Exception as e:
        print(f'일정 삭제 오류: {e}')
        return jsonify({'error': '일정 삭제 실패'}), 500

@app.route('/api/reservations', methods=['GET'])
@jwt_required
def get_reservations():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                r.id,
                r.customer_id,
                r.schedule_id,
                r.status,
                r.booking_date,
                r.number_of_people,
                r.total_price,
                r.notes,
                r.created_at,
                r.updated_at,
                c.name as customer_name,
                c.phone as customer_phone,
                c.email as customer_email,
                s.title as schedule_title,
                s.destination as schedule_destination,
                s.start_date as schedule_start_date,
                s.end_date as schedule_end_date
            FROM reservations r
            LEFT JOIN customers c ON r.customer_id = c.id
            LEFT JOIN schedules s ON r.schedule_id = s.id
            ORDER BY r.booking_date DESC
        """)
        reservations = cursor.fetchall()
        conn.close()

        reservations_list = []
        for res in reservations:
            res_data = dict(res)
            # camelCase 변환
            res_data['customerId'] = res_data.pop('customer_id')
            res_data['scheduleId'] = res_data.pop('schedule_id')
            res_data['bookingDate'] = res_data.pop('booking_date')
            res_data['numberOfPeople'] = res_data.pop('number_of_people')
            res_data['totalPrice'] = res_data.pop('total_price')
            res_data['createdAt'] = res_data.pop('created_at')
            res_data['updatedAt'] = res_data.pop('updated_at')
            res_data['customerName'] = res_data.pop('customer_name')
            res_data['customerPhone'] = res_data.pop('customer_phone')
            res_data['customerEmail'] = res_data.pop('customer_email')
            res_data['scheduleTitle'] = res_data.pop('schedule_title')
            res_data['scheduleDestination'] = res_data.pop('schedule_destination')
            res_data['scheduleStartDate'] = res_data.pop('schedule_start_date')
            res_data['scheduleEndDate'] = res_data.pop('schedule_end_date')
            reservations_list.append(res_data)

        return jsonify(reservations_list)
    except Exception as e:
        print(f'예약 조회 실패: {e}')
        return jsonify({'error': '예약 조회 실패'}), 500

@app.route('/api/reservations', methods=['POST'])
@jwt_required
def create_reservation():
    try:
        data = request.get_json()
        customer_id = data.get('customerId')
        schedule_id = data.get('scheduleId')
        status = data.get('status', 'Pending')
        booking_date = data.get('bookingDate')
        number_of_people = data.get('numberOfPeople', 1)
        total_price = data.get('totalPrice', 0)
        notes = data.get('notes', '')

        if not customer_id or not schedule_id or not booking_date:
            return jsonify({'error': '고객, 일정, 예약일은 필수입니다.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 고객 존재 확인
        cursor.execute('SELECT id FROM customers WHERE id = ?', (customer_id,))
        customer = cursor.fetchone()
        if not customer:
            conn.close()
            return jsonify({'error': '존재하지 않는 고객입니다.'}), 400

        # 일정 존재 확인
        cursor.execute('SELECT id, max_people FROM schedules WHERE id = ?', (schedule_id,))
        schedule = cursor.fetchone()
        if not schedule:
            conn.close()
            return jsonify({'error': '존재하지 않는 일정입니다.'}), 400

        # 예약 인원 확인
        cursor.execute("""
            SELECT COALESCE(SUM(number_of_people), 0) FROM reservations
            WHERE schedule_id = ? AND status != 'Cancelled'
        """, (schedule_id,))
        current_reservations_count = cursor.fetchone()[0]

        if current_reservations_count + number_of_people > schedule['max_people']:
            conn.close()
            return jsonify({'error': '예약 가능 인원을 초과했습니다.'}), 400

        current_time = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO reservations (customer_id, schedule_id, status, booking_date, number_of_people, total_price, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_id, schedule_id, status, booking_date, number_of_people, total_price, notes,
            current_time, current_time
        ))
        conn.commit()

        new_reservation_id = cursor.lastrowid
        cursor.execute("""
            SELECT
                r.id,
                r.customer_id,
                r.schedule_id,
                r.status,
                r.booking_date,
                r.number_of_people,
                r.total_price,
                r.notes,
                r.created_at,
                r.updated_at,
                c.name as customer_name,
                c.phone as customer_phone,
                c.email as customer_email,
                s.title as schedule_title,
                s.destination as schedule_destination,
                s.start_date as schedule_start_date,
                s.end_date as schedule_end_date
            FROM reservations r
            LEFT JOIN customers c ON r.customer_id = c.id
            LEFT JOIN schedules s ON r.schedule_id = s.id
            WHERE r.id = ?
        """, (new_reservation_id,))
        new_reservation = cursor.fetchone()
        conn.close()

        if not new_reservation:
            return jsonify({'error': '예약 등록 후 정보를 찾을 수 없습니다.'}), 500

        new_res_data = dict(new_reservation)
        new_res_data['customerId'] = new_res_data.pop('customer_id')
        new_res_data['scheduleId'] = new_res_data.pop('schedule_id')
        new_res_data['bookingDate'] = new_res_data.pop('booking_date')
        new_res_data['numberOfPeople'] = new_res_data.pop('number_of_people')
        new_res_data['totalPrice'] = new_res_data.pop('total_price')
        new_res_data['createdAt'] = new_res_data.pop('created_at')
        new_res_data['updatedAt'] = new_res_data.pop('updated_at')
        new_res_data['customerName'] = new_res_data.pop('customer_name')
        new_res_data['customerPhone'] = new_res_data.pop('customer_phone')
        new_res_data['customerEmail'] = new_res_data.pop('customer_email')
        new_res_data['scheduleTitle'] = new_res_data.pop('schedule_title')
        new_res_data['scheduleDestination'] = new_res_data.pop('schedule_destination')
        new_res_data['scheduleStartDate'] = new_res_data.pop('schedule_start_date')
        new_res_data['scheduleEndDate'] = new_res_data.pop('schedule_end_date')

        return jsonify(new_res_data), 201
    except Exception as e:
        print(f'예약 등록 오류: {e}')
        return jsonify({'error': '예약 등록 실패'}), 500

@app.route('/api/reservations', methods=['DELETE'])
@jwt_required
def delete_all_reservations():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM reservations')
        conn.commit()
        conn.close()
        return jsonify({'message': '모든 예약이 삭제되었습니다.'})
    except Exception as e:
        print(f'모든 예약 삭제 오류: {e}')
        return jsonify({'error': '모든 예약 삭제 실패'}), 500

@app.route('/api/reservations/<int:reservation_id>', methods=['GET'])
@jwt_required
def get_reservation_by_id(reservation_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                r.id,
                r.customer_id,
                r.schedule_id,
                r.status,
                r.booking_date,
                r.number_of_people,
                r.total_price,
                r.notes,
                r.created_at,
                r.updated_at,
                c.name as customer_name,
                c.phone as customer_phone,
                c.email as customer_email,
                s.title as schedule_title,
                s.destination as schedule_destination,
                s.start_date as schedule_start_date,
                s.end_date as schedule_end_date,
                s.price as schedule_price,
                s.max_people as schedule_max_people
            FROM reservations r
            LEFT JOIN customers c ON r.customer_id = c.id
            LEFT JOIN schedules s ON r.schedule_id = s.id
            WHERE r.id = ?
        """, (reservation_id,))
        reservation = cursor.fetchone()
        conn.close()

        if not reservation:
            return jsonify({'error': '예약을 찾을 수 없습니다.'}), 404

        res_data = dict(reservation)
        res_data['customerId'] = res_data.pop('customer_id')
        res_data['scheduleId'] = res_data.pop('schedule_id')
        res_data['bookingDate'] = res_data.pop('booking_date')
        res_data['numberOfPeople'] = res_data.pop('number_of_people')
        res_data['totalPrice'] = res_data.pop('total_price')
        res_data['createdAt'] = res_data.pop('created_at')
        res_data['updatedAt'] = res_data.pop('updated_at')
        res_data['customerName'] = res_data.pop('customer_name')
        res_data['customerPhone'] = res_data.pop('customer_phone')
        res_data['customerEmail'] = res_data.pop('customer_email')
        res_data['scheduleTitle'] = res_data.pop('schedule_title')
        res_data['scheduleDestination'] = res_data.pop('schedule_destination')
        res_data['scheduleStartDate'] = res_data.pop('schedule_start_date')
        res_data['scheduleEndDate'] = res_data.pop('schedule_end_date')
        res_data['schedulePrice'] = res_data.pop('schedule_price')
        res_data['scheduleMaxPeople'] = res_data.pop('schedule_max_people')

        return jsonify(res_data)
    except Exception as e:
        print(f'예약 조회 실패: {e}')
        return jsonify({'error': '예약 조회 실패'}), 500

@app.route('/api/reservations/<int:reservation_id>', methods=['PUT'])
@jwt_required
def update_reservation(reservation_id):
    try:
        data = request.get_json()
        customer_id = data.get('customerId')
        schedule_id = data.get('scheduleId')
        status = data.get('status', 'Pending')
        booking_date = data.get('bookingDate')
        number_of_people = data.get('numberOfPeople', 1)
        total_price = data.get('totalPrice', 0)
        notes = data.get('notes', '')

        if not customer_id or not schedule_id or not booking_date:
            return jsonify({'error': '고객, 일정, 예약일은 필수입니다.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 고객 존재 확인
        cursor.execute('SELECT id FROM customers WHERE id = ?', (customer_id,))
        customer = cursor.fetchone()
        if not customer:
            conn.close()
            return jsonify({'error': '존재하지 않는 고객입니다.'}), 400

        # 일정 존재 확인
        cursor.execute('SELECT id, max_people FROM schedules WHERE id = ?', (schedule_id,))
        schedule = cursor.fetchone()
        if not schedule:
            conn.close()
            return jsonify({'error': '존재하지 않는 일정입니다.'}), 400

        # 예약 인원 확인
        cursor.execute("""
            SELECT COALESCE(SUM(number_of_people), 0) FROM reservations
            WHERE schedule_id = ? AND status != 'Cancelled' AND id != ?
        """, (schedule_id, reservation_id))
        current_reservations_count = cursor.fetchone()[0]

        if current_reservations_count + number_of_people > schedule['max_people']:
            conn.close()
            return jsonify({'error': '예약 가능 인원을 초과했습니다.'}), 400

        current_time = datetime.now().isoformat()
        cursor.execute("""
            UPDATE reservations
            SET customer_id = ?, schedule_id = ?, status = ?, booking_date = ?,
                number_of_people = ?, total_price = ?, notes = ?, updated_at = ?
            WHERE id = ?
        """, (
            customer_id, schedule_id, status, booking_date,
            number_of_people, total_price, notes, current_time, reservation_id
        ))
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': '예약을 찾을 수 없습니다.'}), 404

        cursor.execute("""
            SELECT
                r.id,
                r.customer_id,
                r.schedule_id,
                r.status,
                r.booking_date,
                r.number_of_people,
                r.total_price,
                r.notes,
                r.created_at,
                r.updated_at,
                c.name as customer_name,
                c.phone as customer_phone,
                c.email as customer_email,
                s.title as schedule_title,
                s.destination as schedule_destination,
                s.start_date as schedule_start_date,
                s.end_date as schedule_end_date
            FROM reservations r
            LEFT JOIN customers c ON r.customer_id = c.id
            LEFT JOIN schedules s ON r.schedule_id = s.id
            WHERE r.id = ?
        """, (reservation_id,))
        updated_reservation = cursor.fetchone()
        conn.close()

        updated_res_data = dict(updated_reservation)
        updated_res_data['customerId'] = updated_res_data.pop('customer_id')
        updated_res_data['scheduleId'] = updated_res_data.pop('schedule_id')
        updated_res_data['bookingDate'] = updated_res_data.pop('booking_date')
        updated_res_data['numberOfPeople'] = updated_res_data.pop('number_of_people')
        updated_res_data['totalPrice'] = updated_res_data.pop('total_price')
        updated_res_data['createdAt'] = updated_res_data.pop('created_at')
        updated_res_data['updatedAt'] = updated_res_data.pop('updated_at')
        updated_res_data['customerName'] = updated_res_data.pop('customer_name')
        updated_res_data['customerPhone'] = updated_res_data.pop('customer_phone')
        updated_res_data['customerEmail'] = updated_res_data.pop('customer_email')
        updated_res_data['scheduleTitle'] = updated_res_data.pop('schedule_title')
        updated_res_data['scheduleDestination'] = updated_res_data.pop('schedule_destination')
        updated_res_data['scheduleStartDate'] = updated_res_data.pop('schedule_start_date')
        updated_res_data['scheduleEndDate'] = updated_res_data.pop('schedule_end_date')

        return jsonify(updated_res_data)
    except Exception as e:
        print(f'예약 수정 오류: {e}')
        return jsonify({'error': '예약 수정 실패'}), 500

@app.route('/api/reservations/<int:reservation_id>', methods=['DELETE'])
@jwt_required
def delete_reservation(reservation_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM reservations WHERE id = ?', (reservation_id,))
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': '예약을 찾을 수 없습니다.'}), 404
        
        conn.close()
        return jsonify({'message': '예약이 삭제되었습니다.'})
    except Exception as e:
        print(f'예약 삭제 오류: {e}')
        return jsonify({'error': '예약 삭제 실패'}), 500

@app.route('/dashboard')
@jwt_required # 실제 대시보드 페이지는 JWT 인증 필요 (브라우저 세션 기반이므로 실제로는 jwt_required가 필요 없을 수 있지만, API 호출 시 필요)
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 모든 고객, 일정, 예약 데이터 가져오기
    customers = cursor.execute('SELECT id, name FROM customers').fetchall()
    schedules = cursor.execute('SELECT id, title, destination, price, max_people FROM schedules').fetchall()
    reservations = cursor.execute('SELECT id, customer_id, schedule_id, status, booking_date, number_of_people, total_price FROM reservations').fetchall()
    conn.close()

    # 통계 계산
    total_customers = len(customers)
    total_schedules = len(schedules)
    total_reservations = len(reservations)

    confirmed_reservations = [r for r in reservations if r['status'] == 'Confirmed']
    pending_reservations = [r for r in reservations if r['status'] == 'Pending']
    cancelled_reservations = [r for r in reservations if r['status'] == 'Cancelled']

    total_revenue = sum(r['total_price'] for r in confirmed_reservations if r['total_price'] is not None)
    average_reservation_value = total_revenue / len(confirmed_reservations) if len(confirmed_reservations) > 0 else 0

    destination_counts = {}
    for schedule in schedules:
        count = sum(1 for r in reservations if r['schedule_id'] == schedule['id'])
        destination_counts[schedule['destination']] = destination_counts.get(schedule['destination'], 0) + count

    top_destinations = sorted(destination_counts.items(), key=lambda item: item[1], reverse=True)[:5]
    top_destinations = [{'destination': dest, 'count': count} for dest, count in top_destinations]

    recent_reservations = sorted(reservations, key=lambda r: datetime.strptime(r['booking_date'], '%Y-%m-%dT%H:%M:%S.%f') if '.' in r['booking_date'] else datetime.strptime(r['booking_date'], '%Y-%m-%dT%H:%M:%S'), reverse=True)[:5]
    recent_reservations_formatted = []
    for res in recent_reservations:
        customer_name = next((c['name'] for c in customers if c['id'] == res['customer_id']), 'Unknown')
        schedule_title = next((s['title'] for s in schedules if s['id'] == res['schedule_id']), 'Unknown')
        recent_reservations_formatted.append({
            'id': res['id'],
            'customerName': customer_name,
            'scheduleTitle': schedule_title,
            'bookingDate': res['booking_date'].split('T')[0], # 날짜만 표시
            'status': res['status'],
            'totalPrice': res['total_price'] or 0,
        })

    stats = {
        'totalCustomers': total_customers,
        'totalSchedules': total_schedules,
        'totalReservations': total_reservations,
        'confirmedReservations': len(confirmed_reservations),
        'pendingReservations': len(pending_reservations),
        'cancelledReservations': len(cancelled_reservations),
        'totalRevenue': total_revenue,
        'averageReservationValue': average_reservation_value,
        'topDestinations': top_destinations,
        'recentReservations': recent_reservations_formatted,
    }

    return render_template('dashboard.html', stats=stats)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('login_page'))

@app.route('/customers')
@jwt_required
def customers_page():
    conn = get_db_connection()
    cursor = conn.cursor()

    search_term = request.args.get('search_term', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    has_email = request.args.get('has_email', 'false') == 'true'
    has_phone = request.args.get('has_phone', 'false') == 'true'
    has_address = request.args.get('has_address', 'false') == 'true'
    page = int(request.args.get('page', 1))
    items_per_page = 20

    query = 'SELECT id, name, phone, email, address, notes, created_at, updated_at FROM customers WHERE 1=1'
    params = []

    if search_term:
        query += ' AND (name LIKE ? OR email LIKE ? OR phone LIKE ? OR address LIKE ?)'
        search_pattern = f'%{search_term}%'
        params.extend([search_pattern, search_pattern, search_pattern, search_pattern])

    if has_email:
        query += ' AND email IS NOT NULL AND email != '''
    if has_phone:
        query += ' AND phone IS NOT NULL AND phone != '''
    if has_address:
        query += ' AND address IS NOT NULL AND address != '''

    # 정렬
    if sort_by == 'name':
        query += ' ORDER BY name'
    elif sort_by == 'email':
        query += ' ORDER BY email'
    elif sort_by == 'created_at':
        query += ' ORDER BY created_at'

    if sort_order == 'desc':
        query += ' DESC'
    else:
        query += ' ASC'

    # 전체 고객 수 계산 (페이지네이션용)
    total_customers_query = query.replace('id, name, phone, email, address, notes, created_at, updated_at', 'COUNT(*)')
    cursor.execute(total_customers_query, params)
    total_customers_count = cursor.fetchone()[0]
    
    total_pages = ceil(total_customers_count / items_per_page)

    # 페이지네이션 적용
    offset = (page - 1) * items_per_page
    query += f' LIMIT {items_per_page} OFFSET {offset}'

    cursor.execute(query, params)
    customers = cursor.fetchall()
    conn.close()

    return render_template('customers.html',
                           customers=customers,
                           filtered_customers=customers, # filtered_customers는 실제 필터링된 전체 목록이어야 하나, 여기서는 편의상 현재 페이지 고객만 전달
                           total_pages=total_pages,
                           current_page=page,
                           request=request) # 템플릿에서 request.args를 직접 사용하기 위해 전달

@app.route('/customers/delete/<int:customer_id>', methods=['POST'])
@jwt_required
def delete_customer_page(customer_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 예약이 있는지 확인
        cursor.execute('SELECT COUNT(*) FROM reservations WHERE customer_id = ?', (customer_id,))
        reservations_count = cursor.fetchone()[0]

        if reservations_count > 0:
            conn.close()
            return redirect(url_for('customers_page', error='예약이 있는 고객은 삭제할 수 없습니다.'))

        cursor.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            return redirect(url_for('customers_page', error='고객을 찾을 수 없습니다.'))
        
        conn.close()
        return redirect(url_for('customers_page', message='고객이 삭제되었습니다.'))
    except Exception as e:
        print(f'고객 삭제 오류: {e}')
        return redirect(url_for('customers_page', error='고객 삭제 실패'))

@app.route('/customers/export-csv')
@jwt_required
def export_customers_csv():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 필터링 로직을 그대로 사용 (페이지네이션 제외)
    search_term = request.args.get('search_term', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    has_email = request.args.get('has_email', 'false') == 'true'
    has_phone = request.args.get('has_phone', 'false') == 'true'
    has_address = request.args.get('has_address', 'false') == 'true'

    query = 'SELECT id, name, phone, email, address, notes, created_at FROM customers WHERE 1=1'
    params = []

    if search_term:
        query += ' AND (name LIKE ? OR email LIKE ? OR phone LIKE ? OR address LIKE ?)'
        search_pattern = f'%{search_term}%'
        params.extend([search_pattern, search_pattern, search_pattern, search_pattern])

    if has_email:
        query += ' AND email IS NOT NULL AND email != '''
    if has_phone:
        query += ' AND phone IS NOT NULL AND phone != '''
    if has_address:
        query += ' AND address IS NOT NULL AND address != '''

    if sort_by == 'name':
        query += ' ORDER BY name'
    elif sort_by == 'email':
        query += ' ORDER BY email'
    elif sort_by == 'created_at':
        query += ' ORDER BY created_at'

    if sort_order == 'desc':
        query += ' DESC'
    else:
        query += ' ASC'
    
    cursor.execute(query, params)
    all_customers = cursor.fetchall()
    conn.close()

    # CSV 헤더 및 내용 생성
    headers = ['ID', '이름', '이메일', '전화번호', '주소', '메모', '등록일']
    csv_rows = [headers]
    for customer in all_customers:
        csv_rows.append([
            customer['id'],
            customer['name'],
            customer['email'] or '',
            customer['phone'] or '',
            customer['address'] or '',
            customer['notes'] or '',
            customer['created_at'].split('T')[0] if customer['created_at'] else ''
        ])
    
    csv_content = "\n".join([','.join(map(str, row)) for row in csv_rows])

    response = make_response(csv_content)
    response.headers["Content-Disposition"] = "attachment; filename=customers.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    return response

@app.route('/customers/create', methods=['GET', 'POST'])
@jwt_required
def create_customer_page():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        address = request.form.get('address')
        notes = request.form.get('notes')

        errors = {}
        if not name or len(name.strip()) < 2:
            errors['name'] = '이름은 2자 이상이어야 합니다.'
        if not phone or not phone.strip():
            errors['phone'] = '전화번호는 필수입니다.'
        elif not phone.replace('-', '').isdigit(): # 숫자와 하이픈만 허용
            errors['phone'] = '올바른 전화번호 형식이 아닙니다.'
        if email and not re.match(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            errors['email'] = '올바른 이메일 형식이 아닙니다.'

        if errors:
            return render_template('create_customer.html', errors=errors, request=request)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            current_time = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO customers (name, phone, email, address, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, phone, email, address, notes, current_time, current_time))
            conn.commit()
            conn.close()
            return redirect(url_for('customers_page', message='고객이 성공적으로 등록되었습니다.'))
        except Exception as e:
            print(f'고객 등록 오류: {e}')
            return render_template('create_customer.html', error='고객 등록에 실패했습니다. 다시 시도해주세요.', request=request)
    return render_template('create_customer.html', request=request)

@app.route('/customers/<int:customer_id>', methods=['GET', 'POST'])
@jwt_required
def edit_customer_page(customer_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    customer = cursor.execute('SELECT id, name, phone, email, address, notes, created_at, updated_at FROM customers WHERE id = ?', (customer_id,)).fetchone()
    if not customer:
        conn.close()
        return render_template('edit_customer.html', customer=None) # 고객을 찾을 수 없을 때

    # 해당 고객의 예약 목록 가져오기
    customer_reservations = cursor.execute("""
        SELECT 
            r.id, r.booking_date, r.status, r.number_of_people, r.total_price,
            s.title as schedule_title
        FROM reservations r
        JOIN schedules s ON r.schedule_id = s.id
        WHERE r.customer_id = ?
        ORDER BY r.booking_date DESC
    """, (customer_id,)).fetchall()
    
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        address = request.form.get('address')
        notes = request.form.get('notes')

        errors = {}
        if not name or len(name.strip()) < 2:
            errors['name'] = '이름은 2자 이상이어야 합니다.'
        if not phone or not phone.strip():
            errors['phone'] = '전화번호는 필수입니다.'
        elif not phone.replace('-', '').isdigit():
            errors['phone'] = '올바른 전화번호 형식이 아닙니다.'
        if email and not re.match(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            errors['email'] = '올바른 이메일 형식이 아닙니다.'

        if errors:
            conn.close()
            return render_template('edit_customer.html', customer=customer, is_editing=True, errors=errors, request=request, customer_reservations=customer_reservations)

        try:
            current_time = datetime.now().isoformat()
            cursor.execute("""
                UPDATE customers
                SET name = ?, phone = ?, email = ?, address = ?, notes = ?, updated_at = ?
                WHERE id = ?
            """, (name, phone, email, address, notes, current_time, customer_id))
            conn.commit()
            
            # 업데이트된 고객 정보 다시 로드
            updated_customer = cursor.execute('SELECT id, name, phone, email, address, notes, created_at, updated_at FROM customers WHERE id = ?', (customer_id,)).fetchone()
            conn.close()
            return render_template('edit_customer.html', customer=updated_customer, is_editing=False, message='고객 정보가 성공적으로 수정되었습니다.', customer_reservations=customer_reservations)
        except Exception as e:
            conn.close()
            print(f'고객 수정 오류: {e}')
            return render_template('edit_customer.html', customer=customer, is_editing=True, error='고객 정보 수정에 실패했습니다.', request=request, customer_reservations=customer_reservations)
    
    conn.close()
    return render_template('edit_customer.html', customer=customer, is_editing=False, customer_reservations=customer_reservations)

@app.route('/schedules')
@jwt_required
def schedules_page():
    conn = get_db_connection()
    cursor = conn.cursor()

    search_term = request.args.get('search_term', '')
    sort_by = request.args.get('sort_by', 'startDate')
    sort_order = request.args.get('sort_order', 'desc')
    status_filter = request.args.get('status', '')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')
    start_date_filter = request.args.get('start_date', '')
    end_date_filter = request.args.get('end_date', '')
    page = int(request.args.get('page', 1))
    items_per_page = 20

    query = 'SELECT id, title, description, start_date, end_date, destination, price, max_people, status, duration, region, meeting_date, meeting_time, meeting_place, manager, reservation_maker, reservation_maker_contact, important_docs, currency_info, other_items, memo, created_at, updated_at FROM schedules WHERE 1=1'
    params = []

    if search_term:
        query += ' AND (title LIKE ? OR description LIKE ? OR destination LIKE ?)'
        search_pattern = f'%{search_term}%'
        params.extend([search_pattern, search_pattern, search_pattern])

    if status_filter:
        query += ' AND status = ?'
        params.append(status_filter)

    if min_price:
        query += ' AND price >= ?'
        params.append(float(min_price))
    if max_price:
        query += ' AND price <= ?'
        params.append(float(max_price))

    if start_date_filter:
        query += ' AND start_date >= ?'
        params.append(start_date_filter)
    if end_date_filter:
        query += ' AND end_date <= ?'
        params.append(end_date_filter)

    # 정렬
    if sort_by == 'title':
        query += ' ORDER BY title'
    elif sort_by == 'destination':
        query += ' ORDER BY destination'
    elif sort_by == 'startDate':
        query += ' ORDER BY start_date'
    elif sort_by == 'price':
        query += ' ORDER BY price'
    elif sort_by == 'created_at':
        query += ' ORDER BY created_at'

    if sort_order == 'desc':
        query += ' DESC'
    else:
        query += ' ASC'

    # 전체 일정 수 계산 (페이지네이션용)
    total_schedules_query = query.replace('id, title, description, start_date, end_date, destination, price, max_people, status, duration, region, meeting_date, meeting_time, meeting_place, manager, reservation_maker, reservation_maker_contact, important_docs, currency_info, other_items, memo, created_at, updated_at', 'COUNT(*)')
    cursor.execute(total_schedules_query, params)
    total_schedules_count = cursor.fetchone()[0]
    
    total_pages = ceil(total_schedules_count / items_per_page)

    # 페이지네이션 적용
    offset = (page - 1) * items_per_page
    query += f' LIMIT {items_per_page} OFFSET {offset}'

    cursor.execute(query, params)
    raw_schedules = cursor.fetchall()
    
    schedules_for_template = []
    for schedule in raw_schedules:
        schedule_dict = dict(schedule) # sqlite3.Row 객체를 딕셔너리로 변환
        
        # 예약된 좌석 수 계산
        cursor.execute("SELECT SUM(number_of_people) FROM reservations WHERE schedule_id = ? AND status != 'Cancelled'", (schedule_dict['id'],))
        booked_slots = cursor.fetchone()[0] or 0
        
        schedule_dict['booked_slots'] = booked_slots
        schedule_dict['capacity'] = schedule_dict['max_people'] # max_people을 capacity로 사용
        
        schedules_for_template.append(schedule_dict)

    conn.close()

    return render_template('schedules.html',
                           schedules=schedules_for_template,
                           filtered_schedules=schedules_for_template, # filtered_schedules는 실제 필터링된 전체 목록이어야 하나, 여기서는 편의상 현재 페이지 일정만 전달
                           total_pages=total_pages,
                           current_page=page,
                           request=request) # 템플릿에서 request.args를 직접 사용하기 위해 전달

@app.route('/schedules/delete/<int:schedule_id>', methods=['POST'])
@jwt_required
def delete_schedule_page(schedule_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 예약이 있는지 확인
        cursor.execute('SELECT COUNT(*) FROM reservations WHERE schedule_id = ?', (schedule_id,))
        reservations_count = cursor.fetchone()[0]

        if reservations_count > 0:
            conn.close()
            return redirect(url_for('schedules_page', error='예약이 있는 일정은 삭제할 수 없습니다.'))

        cursor.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            return redirect(url_for('schedules_page', error='일정을 찾을 수 없습니다.'))
        
        conn.close()
        return redirect(url_for('schedules_page', message='일정이 삭제되었습니다.'))
    except Exception as e:
        print(f'일정 삭제 오류: {e}')
        return redirect(url_for('schedules_page', error='일정 삭제 실패'))

@app.route('/schedules/export-csv')
@jwt_required
def export_schedules_csv():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 필터링 로직을 그대로 사용 (페이지네이션 제외)
    search_term = request.args.get('search_term', '')
    sort_by = request.args.get('sort_by', 'startDate')
    sort_order = request.args.get('sort_order', 'desc')
    status_filter = request.args.get('status', '')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')
    start_date_filter = request.args.get('start_date', '')
    end_date_filter = request.args.get('end_date', '')

    query = 'SELECT id, title, description, start_date, end_date, destination, price, max_people, status, duration, region, meeting_date, meeting_time, meeting_place, manager, reservation_maker, reservation_maker_contact, important_docs, currency_info, other_items, memo, created_at FROM schedules WHERE 1=1'
    params = []

    if search_term:
        query += ' AND (title LIKE ? OR description LIKE ? OR destination LIKE ?)'
        search_pattern = f'%{search_term}%'
        params.extend([search_pattern, search_pattern, search_pattern])

    if status_filter:
        query += ' AND status = ?'
        params.append(status_filter)

    if min_price:
        query += ' AND price >= ?'
        params.append(float(min_price))
    if max_price:
        query += ' AND price <= ?'
        params.append(float(max_price))

    if start_date_filter:
        query += ' AND start_date >= ?'
        params.append(start_date_filter)
    if end_date_filter:
        query += ' AND end_date <= ?'
        params.append(end_date_filter)

    if sort_by == 'title':
        query += ' ORDER BY title'
    elif sort_by == 'destination':
        query += ' ORDER BY destination'
    elif sort_by == 'startDate':
        query += ' ORDER BY start_date'
    elif sort_by == 'price':
        query += ' ORDER BY price'
    elif sort_by == 'created_at':
        query += ' ORDER BY created_at'

    if sort_order == 'desc':
        query += ' DESC'
    else:
        query += ' ASC'
    
    cursor.execute(query, params)
    all_schedules = cursor.fetchall()
    conn.close()

    # CSV 헤더 및 내용 생성
    headers = ['ID', '제목', '목적지', '시작일', '종료일', '가격', '최대인원', '상태', '설명', '등록일']
    csv_rows = [headers]
    for schedule in all_schedules:
        csv_rows.append([
            schedule['id'],
            schedule['title'],
            schedule['destination'],
            schedule['start_date'].split('T')[0] if schedule['start_date'] else '',
            schedule['end_date'].split('T')[0] if schedule['end_date'] else '',
            schedule['price'] or 0,
            schedule['max_people'],
            schedule['status'],
            schedule['description'] or '',
            schedule['created_at'].split('T')[0] if schedule['created_at'] else ''
        ])
    
    csv_content = "\n".join([','.join(map(str, row)) for row in csv_rows])

    response = make_response(csv_content)
    response.headers["Content-Disposition"] = "attachment; filename=schedules.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    return response

@app.route('/reservations')
@jwt_required
def reservations_page():
    conn = get_db_connection()
    cursor = conn.cursor()

    search_term = request.args.get('search_term', '')
    sort_by = request.args.get('sort_by', 'bookingDate')
    sort_order = request.args.get('sort_order', 'desc')
    status_filter = request.args.get('status', '')
    customer_id_filter = request.args.get('customer_id', '')
    schedule_id_filter = request.args.get('schedule_id', '')
    min_people = request.args.get('min_people', '')
    max_people = request.args.get('max_people', '')
    booking_date_start = request.args.get('booking_date_start', '')
    booking_date_end = request.args.get('booking_date_end', '')
    page = int(request.args.get('page', 1))
    items_per_page = 20 # AG-Grid 내장 페이지네이션을 사용하므로, 백엔드에서는 전체 데이터를 넘겨주고 프론트엔드에서 처리합니다.

    query = """
        SELECT
            r.id,
            r.customer_id,
            r.schedule_id,
            r.status,
            r.booking_date,
            r.number_of_people,
            r.total_price,
            r.notes,
            r.created_at,
            r.updated_at,
            c.name as customer_name,
            c.phone as customer_phone,
            c.email as customer_email,
            s.title as schedule_title,
            s.destination as schedule_destination,
            s.start_date as schedule_start_date,
            s.end_date as schedule_end_date,
            s.price as schedule_price,
            s.max_people as schedule_max_people
        FROM reservations r
        LEFT JOIN customers c ON r.customer_id = c.id
        LEFT JOIN schedules s ON r.schedule_id = s.id
        WHERE 1=1
    """
    params = []

    if search_term:
        query += ' AND (c.name LIKE ? OR s.title LIKE ? OR r.notes LIKE ?)'
        search_pattern = f'%{search_term}%'
        params.extend([search_pattern, search_pattern, search_pattern])

    if status_filter:
        query += ' AND r.status = ?'
        params.append(status_filter)

    if customer_id_filter:
        query += ' AND r.customer_id = ?'
        params.append(int(customer_id_filter))
    
    if schedule_id_filter:
        query += ' AND r.schedule_id = ?'
        params.append(int(schedule_id_filter))

    if min_people:
        query += ' AND r.number_of_people >= ?'
        params.append(int(min_people))
    if max_people:
        query += ' AND r.number_of_people <= ?'
        params.append(int(max_people))

    if booking_date_start:
        query += ' AND r.booking_date >= ?'
        params.append(booking_date_start)
    if booking_date_end:
        query += ' AND r.booking_date <= ?'
        params.append(booking_date_end)

    # 정렬
    if sort_by == 'bookingDate':
        query += ' ORDER BY r.booking_date'
    elif sort_by == 'customerName':
        query += ' ORDER BY c.name'
    elif sort_by == 'scheduleTitle':
        query += ' ORDER BY s.title'
    elif sort_by == 'totalPrice':
        query += ' ORDER BY r.total_price'
    elif sort_by == 'status':
        query += ' ORDER BY r.status'
    elif sort_by == 'created_at':
        query += ' ORDER BY r.created_at'

    if sort_order == 'desc':
        query += ' DESC'
    else:
        query += ' ASC'

    cursor.execute(query, params)
    reservations_raw = cursor.fetchall()

    # AG-Grid가 사용할 수 있도록 데이터 형식 변경 (camelCase)
    reservations = []
    for res in reservations_raw:
        res_data = dict(res)
        res_data['customerId'] = res_data.pop('customer_id')
        res_data['scheduleId'] = res_data.pop('schedule_id')
        res_data['bookingDate'] = res_data.pop('booking_date')
        res_data['numberOfPeople'] = res_data.pop('number_of_people')
        res_data['totalPrice'] = res_data.pop('total_price')
        res_data['createdAt'] = res_data.pop('created_at')
        res_data['updatedAt'] = res_data.pop('updated_at')
        res_data['customerName'] = res_data.pop('customer_name')
        res_data['customerPhone'] = res_data.pop('customer_phone')
        res_data['customerEmail'] = res_data.pop('customer_email')
        res_data['scheduleTitle'] = res_data.pop('schedule_title')
        res_data['scheduleDestination'] = res_data.pop('schedule_destination')
        res_data['scheduleStartDate'] = res_data.pop('schedule_start_date')
        res_data['scheduleEndDate'] = res_data.pop('schedule_end_date')
        res_data['schedulePrice'] = res_data.pop('schedule_price')
        res_data['scheduleMaxPeople'] = res_data.pop('schedule_max_people')
        reservations.append(res_data)
    
    conn.close()

    # AG-Grid는 클라이언트 측에서 페이지네이션을 처리하므로, 여기서는 전체 필터링된 데이터를 넘겨줍니다.
    # 총 페이지 수 등은 프론트엔드에서 계산합니다.
    return render_template('reservations.html',
                           reservations=reservations,
                           request=request)

@app.route('/reservations/delete/<int:reservation_id>', methods=['POST'])
@jwt_required
def delete_reservation_page(reservation_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM reservations WHERE id = ?', (reservation_id,))
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return redirect(url_for('reservations_page', error='예약을 찾을 수 없습니다.'))
        conn.close()
        return redirect(url_for('reservations_page', message='예약이 삭제되었습니다.'))
    except Exception as e:
        print(f'예약 삭제 오류: {e}')
        return redirect(url_for('reservations_page', error='예약 삭제 실패'))

@app.route('/reservations/export-csv')
@jwt_required
def export_reservations_csv():
    conn = get_db_connection()
    cursor = conn.cursor()

    search_term = request.args.get('search_term', '')
    sort_by = request.args.get('sort_by', 'bookingDate')
    sort_order = request.args.get('sort_order', 'desc')
    status_filter = request.args.get('status', '')
    customer_id_filter = request.args.get('customer_id', '')
    schedule_id_filter = request.args.get('schedule_id', '')
    min_people = request.args.get('min_people', '')
    max_people = request.args.get('max_people', '')
    booking_date_start = request.args.get('booking_date_start', '')
    booking_date_end = request.args.get('booking_date_end', '')

    query = """
        SELECT
            r.id,
            r.customer_id,
            r.schedule_id,
            r.status,
            r.booking_date,
            r.number_of_people,
            r.total_price,
            r.notes,
            r.created_at,
            r.updated_at,
            c.name as customer_name,
            c.phone as customer_phone,
            c.email as customer_email,
            s.title as schedule_title,
            s.destination as schedule_destination,
            s.start_date as schedule_start_date,
            s.end_date as schedule_end_date
        FROM reservations r
        LEFT JOIN customers c ON r.customer_id = c.id
        LEFT JOIN schedules s ON r.schedule_id = s.id
        WHERE 1=1
    """
    params = []

    if search_term:
        query += ' AND (c.name LIKE ? OR s.title LIKE ? OR r.notes LIKE ?)'
        search_pattern = f'%{search_term}%'
        params.extend([search_pattern, search_pattern, search_pattern])

    if status_filter:
        query += ' AND r.status = ?'
        params.append(status_filter)

    if customer_id_filter:
        query += ' AND r.customer_id = ?'
        params.append(int(customer_id_filter))
    
    if schedule_id_filter:
        query += ' AND r.schedule_id = ?'
        params.append(int(schedule_id_filter))

    if min_people:
        query += ' AND r.number_of_people >= ?'
        params.append(int(min_people))
    if max_people:
        query += ' AND r.number_of_people <= ?'
        params.append(int(max_people))

    if booking_date_start:
        query += ' AND r.booking_date >= ?'
        params.append(booking_date_start)
    if booking_date_end:
        query += ' AND r.booking_date <= ?'
        params.append(booking_date_end)

    # 정렬
    if sort_by == 'bookingDate':
        query += ' ORDER BY r.booking_date'
    elif sort_by == 'customerName':
        query += ' ORDER BY c.name'
    elif sort_by == 'scheduleTitle':
        query += ' ORDER BY s.title'
    elif sort_by == 'totalPrice':
        query += ' ORDER BY r.total_price'
    elif sort_by == 'status':
        query += ' ORDER BY r.status'
    elif sort_by == 'created_at':
        query += ' ORDER BY r.created_at'

    if sort_order == 'desc':
        query += ' DESC'
    else:
        query += ' ASC'
    
    cursor.execute(query, params)
    all_reservations = cursor.fetchall()
    conn.close()

    # CSV 헤더 및 내용 생성
    headers = ['ID', '고객명', '일정명', '상태', '예약일', '인원수', '총 가격', '메모', '등록일']
    csv_rows = [headers]
    for res in all_reservations:
        csv_rows.append([
            res['id'],
            res['customer_name'] or '',
            res['schedule_title'] or '',
            res['status'] or '',
            res['booking_date'].split('T')[0] if res['booking_date'] else '',
            res['number_of_people'] or 0,
            res['total_price'] or 0,
            res['notes'] or '',
            res['created_at'].split('T')[0] if res['created_at'] else ''
        ])
    
    csv_content = "\n".join([','.join(map(str, row)) for row in csv_rows])

    response = make_response(csv_content)
    response.headers["Content-Disposition"] = "attachment; filename=reservations.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    return response

@app.route('/reservations/create', methods=['GET', 'POST'])
@jwt_required
def create_reservation_page():
    conn = get_db_connection()
    cursor = conn.cursor()
    customers = cursor.execute('SELECT id, name, phone FROM customers ORDER BY name ASC').fetchall()
    schedules = cursor.execute('SELECT id, title, start_date, end_date FROM schedules ORDER BY start_date DESC').fetchall()
    conn.close()

    errors = {}

    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        schedule_id = request.form.get('schedule_id')
        status = request.form.get('status', 'Pending')
        booking_date_str = request.form.get('booking_date')
        number_of_people = request.form.get('number_of_people', type=int)
        total_price = request.form.get('total_price', type=float)
        notes = request.form.get('notes', '')

        if not customer_id: errors['customer_id'] = '고객을 선택해주세요.'
        if not schedule_id: errors['schedule_id'] = '일정을 선택해주세요.'
        if not booking_date_str: errors['booking_date'] = '예약일을 입력해주세요.'
        if not number_of_people or number_of_people <= 0: errors['number_of_people'] = '유효한 인원수를 입력해주세요.'
        if total_price is None or total_price < 0: errors['total_price'] = '유효한 총 가격을 입력해주세요.'
        
        # 날짜 형식 검증
        booking_date = None
        if booking_date_str:
            try:
                # SQLite는 ISO8601 문자열을 지원합니다. Flask의 datetime-local은 YYYY-MM-DDTHH:MM 형식을 반환합니다.
                # 초와 마이크로초를 추가하여 ISO 형식에 맞춥니다.
                booking_date = datetime.fromisoformat(booking_date_str).isoformat(timespec='microseconds')
            except ValueError:
                errors['booking_date'] = '유효한 예약일 형식(YYYY-MM-DDTHH:MM)을 입력해주세요.'

        if errors:
            return render_template('create_reservation.html', customers=customers, schedules=schedules, errors=errors, request=request)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # 고객 존재 확인
            cursor.execute('SELECT id FROM customers WHERE id = ?', (customer_id,))
            customer_exists = cursor.fetchone()
            if not customer_exists:
                conn.close()
                errors['customer_id'] = '존재하지 않는 고객입니다.'
                return render_template('create_reservation.html', customers=customers, schedules=schedules, errors=errors, request=request)

            # 일정 존재 확인 및 최대 인원 확인
            cursor.execute('SELECT id, max_people FROM schedules WHERE id = ?', (schedule_id,))
            schedule_info = cursor.fetchone()
            if not schedule_info:
                conn.close()
                errors['schedule_id'] = '존재하지 않는 일정입니다.'
                return render_template('create_reservation.html', customers=customers, schedules=schedules, errors=errors, request=request)

            # 현재 일정의 예약 인원 합계 계산 (취소되지 않은 예약만)
            cursor.execute("""
                SELECT COALESCE(SUM(number_of_people), 0) FROM reservations
                WHERE schedule_id = ? AND status != 'Cancelled'
            """, (schedule_id,))
            current_booked_people = cursor.fetchone()[0]

            if current_booked_people + number_of_people > schedule_info['max_people']:
                conn.close()
                errors['number_of_people'] = f'예약 가능 인원({schedule_info['max_people']}명)을 초과했습니다. 현재 예약된 인원: {current_booked_people}명.'
                return render_template('create_reservation.html', customers=customers, schedules=schedules, errors=errors, request=request)

            current_time = datetime.now().isoformat(timespec='microseconds')
            cursor.execute("""
                INSERT INTO reservations (customer_id, schedule_id, status, booking_date, number_of_people, total_price, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                customer_id, schedule_id, status, booking_date, number_of_people, total_price, notes,
                current_time, current_time
            ))
            conn.commit()
            conn.close()
            return redirect(url_for('reservations_page', message='예약이 성공적으로 등록되었습니다.'))
        except Exception as e:
            conn.close()
            print(f'예약 등록 오류: {e}')
            return render_template('create_reservation.html', customers=customers, schedules=schedules, error='예약 등록에 실패했습니다. 다시 시도해주세요.', request=request)

    return render_template('create_reservation.html', customers=customers, schedules=schedules, errors={}, request=request)

@app.route('/reservations/edit/<int:reservation_id>', methods=['GET', 'POST'])
@jwt_required
def edit_reservation_page(reservation_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    reservation_query = """
        SELECT
            r.id, r.customer_id, r.schedule_id, r.status, r.booking_date,
            r.number_of_people, r.total_price, r.notes, r.created_at, r.updated_at,
            c.name as customer_name,
            s.title as schedule_title, s.start_date as schedule_start_date, s.end_date as schedule_end_date,
            s.max_people as schedule_max_people
        FROM reservations r
        LEFT JOIN customers c ON r.customer_id = c.id
        LEFT JOIN schedules s ON r.schedule_id = s.id
        WHERE r.id = ?
    """
    reservation = cursor.execute(reservation_query, (reservation_id,)).fetchone()

    if not reservation:
        conn.close()
        return render_template('edit_reservation.html', reservation=None, error='예약을 찾을 수 없습니다.')

    # CamelCase로 변환
    reservation_data = dict(reservation)
    reservation_data['customerId'] = reservation_data.pop('customer_id')
    reservation_data['scheduleId'] = reservation_data.pop('schedule_id')
    reservation_data['bookingDate'] = reservation_data.pop('booking_date')
    reservation_data['numberOfPeople'] = reservation_data.pop('number_of_people')
    reservation_data['totalPrice'] = reservation_data.pop('total_price')
    reservation_data['createdAt'] = reservation_data.pop('created_at')
    reservation_data['updatedAt'] = reservation_data.pop('updated_at')
    reservation_data['customerName'] = reservation_data.pop('customer_name')
    reservation_data['scheduleTitle'] = reservation_data.pop('schedule_title')
    reservation_data['scheduleStartDate'] = reservation_data.pop('schedule_start_date')
    reservation_data['scheduleEndDate'] = reservation_data.pop('schedule_end_date')
    reservation_data['scheduleMaxPeople'] = reservation_data.pop('schedule_max_people')

    customers = cursor.execute('SELECT id, name, phone FROM customers ORDER BY name ASC').fetchall()
    schedules = cursor.execute('SELECT id, title, start_date, end_date, max_people FROM schedules ORDER BY start_date DESC').fetchall()
    conn.close()

    errors = {}

    if request.method == 'POST':
        customer_id = request.form.get('customer_id', type=int)
        schedule_id = request.form.get('schedule_id', type=int)
        status = request.form.get('status', 'Pending')
        booking_date_str = request.form.get('booking_date')
        number_of_people = request.form.get('number_of_people', type=int)
        total_price = request.form.get('total_price', type=float)
        notes = request.form.get('notes', '')

        if not customer_id: errors['customer_id'] = '고객을 선택해주세요.'
        if not schedule_id: errors['schedule_id'] = '일정을 선택해주세요.'
        if not booking_date_str: errors['booking_date'] = '예약일을 입력해주세요.'
        if not number_of_people or number_of_people <= 0: errors['number_of_people'] = '유효한 인원수를 입력해주세요.'
        if total_price is None or total_price < 0: errors['total_price'] = '유효한 총 가격을 입력해주세요.'

        booking_date = None
        if booking_date_str:
            try:
                booking_date = datetime.fromisoformat(booking_date_str).isoformat(timespec='microseconds')
            except ValueError:
                errors['booking_date'] = '유효한 예약일 형식(YYYY-MM-DDTHH:MM)을 입력해주세요.'

        if errors:
            # 요청 폼 데이터로 reservation_data를 업데이트하여 오류 시 입력값을 유지
            reservation_data.update({
                'customerId': customer_id,
                'scheduleId': schedule_id,
                'status': status,
                'bookingDate': booking_date_str,
                'numberOfPeople': number_of_people,
                'totalPrice': total_price,
                'notes': notes
            })
            return render_template('edit_reservation.html', reservation=reservation_data, customers=customers, schedules=schedules, errors=errors, request=request)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # 고객 존재 확인 (다시 한 번)
            cursor.execute('SELECT id FROM customers WHERE id = ?', (customer_id,))
            customer_exists = cursor.fetchone()
            if not customer_exists:
                conn.close()
                errors['customer_id'] = '존재하지 않는 고객입니다.'
                return render_template('edit_reservation.html', reservation=reservation_data, customers=customers, schedules=schedules, errors=errors, request=request)

            # 일정 존재 확인 및 최대 인원 확인 (다시 한 번)
            cursor.execute('SELECT id, max_people FROM schedules WHERE id = ?', (schedule_id,))
            schedule_info = cursor.fetchone()
            if not schedule_info:
                conn.close()
                errors['schedule_id'] = '존재하지 않는 일정입니다.'
                return render_template('edit_reservation.html', reservation=reservation_data, customers=customers, schedules=schedules, errors=errors, request=request)
            
            # 현재 일정의 예약 인원 합계 계산 (취소되지 않은 예약, 현재 수정 중인 예약 제외)
            cursor.execute("""
                SELECT COALESCE(SUM(number_of_people), 0) FROM reservations
                WHERE schedule_id = ? AND status != 'Cancelled' AND id != ?
            """, (schedule_id, reservation_id))
            current_booked_people = cursor.fetchone()[0]

            if current_booked_people + number_of_people > schedule_info['max_people']:
                conn.close()
                errors['number_of_people'] = f'예약 가능 인원({schedule_info['max_people']}명)을 초과했습니다. 현재 예약된 인원: {current_booked_people}명.'
                return render_template('edit_reservation.html', reservation=reservation_data, customers=customers, schedules=schedules, errors=errors, request=request)

            current_time = datetime.now().isoformat(timespec='microseconds')
            cursor.execute("""
                UPDATE reservations
                SET customer_id = ?, schedule_id = ?, status = ?, booking_date = ?,
                    number_of_people = ?, total_price = ?, notes = ?, updated_at = ?
                WHERE id = ?
            """, (
                customer_id, schedule_id, status, booking_date, 
                number_of_people, total_price, notes, current_time, reservation_id
            ))
            conn.commit()

            if cursor.rowcount == 0:
                conn.close()
                return render_template('edit_reservation.html', reservation=reservation_data, customers=customers, schedules=schedules, error='예약을 찾을 수 없거나 변경된 내용이 없습니다.', request=request)
            
            # 업데이트된 예약 정보 다시 로드
            updated_reservation = cursor.execute(reservation_query, (reservation_id,)).fetchone()
            updated_reservation_data = dict(updated_reservation)
            updated_reservation_data['customerId'] = updated_reservation_data.pop('customer_id')
            updated_reservation_data['scheduleId'] = updated_reservation_data.pop('schedule_id')
            updated_reservation_data['bookingDate'] = updated_reservation_data.pop('booking_date')
            updated_reservation_data['numberOfPeople'] = updated_reservation_data.pop('number_of_people')
            updated_reservation_data['totalPrice'] = updated_reservation_data.pop('total_price')
            updated_reservation_data['createdAt'] = updated_reservation_data.pop('created_at')
            updated_reservation_data['updatedAt'] = updated_reservation_data.pop('updated_at')
            updated_reservation_data['customerName'] = updated_reservation_data.pop('customer_name')
            updated_reservation_data['scheduleTitle'] = updated_reservation_data.pop('schedule_title')
            updated_reservation_data['scheduleStartDate'] = updated_reservation_data.pop('schedule_start_date')
            updated_reservation_data['scheduleEndDate'] = updated_reservation_data.pop('schedule_end_date')
            updated_reservation_data['scheduleMaxPeople'] = updated_reservation_data.pop('schedule_max_people')

            conn.close()
            return render_template('edit_reservation.html', reservation=updated_reservation_data, customers=customers, schedules=schedules, message='예약 정보가 성공적으로 수정되었습니다.', request=request)
        except Exception as e:
            conn.close()
            print(f'예약 수정 오류: {e}')
            return render_template('edit_reservation.html', reservation=reservation_data, customers=customers, schedules=schedules, error='예약 정보 수정에 실패했습니다. 다시 시도해주세요.', request=request)

    return render_template('edit_reservation.html', reservation=reservation_data, customers=customers, schedules=schedules, errors={}, request=request)

if __name__ == '__main__':
    # 애플리케이션 실행 전 데이터베이스 초기화
    with app.app_context():
        initialize_database()
    app.run(debug=True) 