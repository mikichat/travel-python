from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app
import bcrypt
import jwt
from datetime import datetime
from database import get_db_connection
from app.utils.errors import APIError
from app.utils.auth import jwt_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login_page():
    """로그인 페이지"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return render_template('login.html', error='사용자명과 비밀번호를 입력해주세요.', username=username)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['logged_in'] = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('auth.dashboard'))
        else:
            return render_template('login.html', error='사용자명 또는 비밀번호가 올바르지 않습니다.', username=username)
    
    return render_template('login.html')

@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """API 로그인 엔드포인트"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            raise APIError('사용자명과 비밀번호를 입력해주세요.', 400)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, password, created_at, updated_at FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            raise APIError('사용자명 또는 비밀번호가 올바르지 않습니다.', 401)

        token = jwt.encode(
            {'userId': user['id'], 'username': user['username']},
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )

        user_data = dict(user)
        user_data.pop('password')
        user_data['createdAt'] = user['created_at']
        user_data['updatedAt'] = user['updated_at']

        return jsonify({
            'success': True,
            'user': user_data,
            'token': token
        }), 200
    except APIError:
        raise
    except Exception as e:
        print(f'로그인 오류: {e}')
        raise APIError('로그인 처리 중 오류가 발생했습니다.', 500)

@auth_bp.route('/api/auth/me', methods=['GET'])
@jwt_required(current_app)
def me():
    """현재 사용자 정보 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, created_at, updated_at FROM users WHERE id = ?', (request.user_id,))
        user = cursor.fetchone()
        conn.close()

        if not user:
            raise APIError('사용자를 찾을 수 없습니다.', 404)

        user_data = dict(user)
        user_data['createdAt'] = user['created_at']
        user_data['updatedAt'] = user['updated_at']

        return jsonify({'success': True, 'user': user_data})
    except APIError:
        raise
    except Exception as e:
        print(f'사용자 정보 조회 오류: {e}')
        raise APIError('사용자 정보 조회 중 오류가 발생했습니다.', 500)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register_page():
    """회원가입 페이지"""
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
            return redirect(url_for('auth.login_page'))
        except Exception as e:
            conn.close()
            print(f'회원가입 오류: {e}')
            error = '회원가입 처리 중 오류가 발생했습니다. 다시 시도해주세요.'
            return render_template('register.html', error=error, username=username, email=email)

    return render_template('register.html')

@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    """API 회원가입 엔드포인트"""
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not username or not email or not password:
            raise APIError('모든 필드를 입력해주세요.', 400)

        conn = get_db_connection()
        cursor = conn.cursor()

        # 사용자명 중복 확인
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        existing_user = cursor.fetchone()
        if existing_user:
            conn.close()
            raise APIError('이미 사용 중인 사용자명입니다.', 400)

        # 이메일 중복 확인
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        existing_email = cursor.fetchone()
        if existing_email:
            conn.close()
            raise APIError('이미 사용 중인 이메일입니다.', 400)

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
            raise APIError('사용자 등록 후 정보를 찾을 수 없습니다.', 500)

        # JWT 토큰 생성
        token = jwt.encode(
            {'userId': new_user['id'], 'username': new_user['username']},
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )

        new_user_data = dict(new_user)
        new_user_data['createdAt'] = new_user['created_at']
        new_user_data['updatedAt'] = new_user['updated_at']

        return jsonify({
            'success': True,
            'user': new_user_data,
            'token': token
        }), 201

    except APIError:
        raise
    except Exception as e:
        print(f'회원가입 오류: {e}')
        raise APIError('회원가입 처리 중 오류가 발생했습니다.', 500)

@auth_bp.route('/logout')
def logout():
    """로그아웃"""
    session.pop('logged_in', None)
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('auth.login_page'))

@auth_bp.route('/dashboard')
@jwt_required(current_app)
def dashboard():
    """대시보드 페이지"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 통계 데이터 조회
        cursor.execute('SELECT COUNT(*) FROM customers')
        customer_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM schedules')
        schedule_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM reservations')
        reservation_count = cursor.fetchone()[0]
        
        # 최근 예약 조회
        cursor.execute("""
            SELECT r.id, r.booking_date, r.status, r.number_of_people, r.total_price,
                   c.name as customer_name, s.title as schedule_title
            FROM reservations r
            LEFT JOIN customers c ON r.customer_id = c.id
            LEFT JOIN schedules s ON r.schedule_id = s.id
            ORDER BY r.booking_date DESC
            LIMIT 5
        """)
        recent_reservations = cursor.fetchall()
        
        conn.close()
        
        return render_template('dashboard.html', 
                             customer_count=customer_count,
                             schedule_count=schedule_count,
                             reservation_count=reservation_count,
                             recent_reservations=recent_reservations)
    except Exception as e:
        print(f'대시보드 오류: {e}')
        return render_template('dashboard.html', error='데이터를 불러오는 중 오류가 발생했습니다.') 