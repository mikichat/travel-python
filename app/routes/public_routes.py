from flask import Blueprint, render_template, request, jsonify, url_for, current_app, redirect
from database import get_db_connection
import datetime
import random
from app.utils.mail import send_email

public_bp = Blueprint('public', __name__)

@public_bp.route('/my-trip/<string:reservation_code>', methods=['GET', 'POST'], defaults={'phone_digits': None})
@public_bp.route('/my-trip/<string:reservation_code>/<string:phone_digits>', methods=['GET'])
def my_trip_page(reservation_code, phone_digits):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 예약 정보 확인
        cursor.execute("SELECT r.*, c.phone FROM reservations r JOIN customers c ON r.customer_id = c.id WHERE r.reservation_code = ? AND r.deleted_at IS NULL", (reservation_code,))
        reservation_data = cursor.fetchone()

        if not reservation_data:
            return render_template('errors/404.html', message="예약 정보를 찾을 수 없습니다."), 404

        def render_trip_details():
            # 전체 정보 다시 조회 (JOIN 포함)
            cursor.execute("""
                SELECT
                    r.*,
                    c.id as customer_id, c.name as customer_name, c.phone, c.email,
                    s.title as schedule_title, s.start_date as travel_start_date, s.end_date as travel_end_date,
                    p.id as passport_info_id, p.passport_number, p.last_name_eng, p.first_name_eng, p.expiry_date, p.passport_photo_path
                FROM reservations r
                JOIN customers c ON r.customer_id = c.id
                LEFT JOIN schedules s ON r.schedule_id = s.id
                LEFT JOIN passport_info p ON c.passport_info_id = p.id
                WHERE r.reservation_code = ? AND r.deleted_at IS NULL
            """, (reservation_code,))
            data = cursor.fetchone()

            reservation_data_dict = {k: data[k] for k in data.keys() if k in ['id', 'customer_id', 'schedule_id', 'status', 'booking_date', 'number_of_people', 'total_price', 'notes', 'reservation_code', 'customer_name', 'schedule_title', 'travel_start_date', 'travel_end_date']}
            customer_data_dict = {k: data[k] for k in data.keys() if k in ['customer_id', 'name', 'phone', 'email']}
            customer_data_dict['name'] = data['customer_name']
            passport_data = {k: data[k] for k in data.keys() if k in ['passport_info_id', 'passport_number', 'last_name_eng', 'first_name_eng', 'expiry_date', 'passport_photo_path']} if data['passport_info_id'] else None

            return render_template('my_trip.html',
                                   reservation=reservation_data_dict,
                                   customer=customer_data_dict,
                                   passport_info=passport_data)

        if current_app.config.get('SMS_VERIFICATION_ENABLED'):
            if request.method == 'POST':
                action = request.form.get('action')
                if action == 'send_sms':
                    sms_code = str(random.randint(100000, 999999))
                    expires_at = datetime.datetime.now() + datetime.timedelta(minutes=10)
                    
                    cursor.execute("UPDATE reservations SET sms_dispatch_code = ?, sms_dispatch_code_expires_at = ? WHERE id = ?",
                                   (sms_code, expires_at.isoformat(), reservation_data['id']))
                    conn.commit()
                    
                    current_app.logger.info(f"SMS Code for {reservation_code}: {sms_code}")
                    return render_template('verify_sms.html', reservation_code=reservation_code, message="인증번호가 발송되었습니다.")
                
                elif action == 'verify_sms':
                    submitted_code = request.form.get('sms_code')
                    stored_code = reservation_data['sms_dispatch_code']
                    expires_at_str = reservation_data['sms_dispatch_code_expires_at']

                    if not stored_code or stored_code != submitted_code:
                        return render_template('verify_sms.html', reservation_code=reservation_code, error="인증번호가 일치하지 않습니다.")

                    if expires_at_str:
                        expires_at = datetime.datetime.fromisoformat(expires_at_str)
                        if datetime.datetime.now() > expires_at:
                            return render_template('verify_sms.html', reservation_code=reservation_code, error="인증번호가 만료되었습니다.")
                    
                    return render_trip_details()
            
            return render_template('verify_sms.html', reservation_code=reservation_code)

        else: # Phone digit verification
            if request.method == 'POST':
                phone_digits_form = request.form.get('phone_digits')
                if phone_digits_form:
                    return redirect(url_for('public.my_trip_page', reservation_code=reservation_code, phone_digits=phone_digits_form))
                else:
                    return render_template('verify_phone.html', reservation_code=reservation_code, error="전화번호 끝 4자리를 입력해주세요.")

            if phone_digits is None:
                return render_template('verify_phone.html', reservation_code=reservation_code)

            customer_phone = reservation_data['phone']
            if not customer_phone or len(customer_phone) < 4 or customer_phone[-4:] != phone_digits:
                return render_template('verify_phone.html', reservation_code=reservation_code, error="전화번호가 일치하지 않습니다."), 403
            
            return render_trip_details()

    except Exception as e:
        current_app.logger.error(f"Error fetching my trip page data: {e}")
        return render_template('errors/500.html'), 500
    finally:
        if conn:
            conn.close()

import os
import uuid
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@public_bp.route('/api/public/update-my-info/<string:reservation_code>', methods=['POST'])
def update_my_info(reservation_code):
    email_dispatch_code = request.form.get('email_dispatch_code')

    if not email_dispatch_code:
        return jsonify({'success': False, 'error': '이메일 인증 코드가 필요합니다.'}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. 인증 코드 확인
        cursor.execute("""
            SELECT r.id, r.customer_id, r.email_dispatch_code, r.email_dispatch_code_expires_at, c.passport_info_id
            FROM reservations r
            JOIN customers c ON r.customer_id = c.id
            WHERE r.reservation_code = ? AND r.deleted_at IS NULL
        """, (reservation_code,))
        reservation = cursor.fetchone()

        if not reservation:
            return jsonify({'success': False, 'error': '유효하지 않은 예약 코드입니다.'}), 404

        if not reservation['email_dispatch_code'] or reservation['email_dispatch_code'] != email_dispatch_code:
            return jsonify({'success': False, 'error': '인증 코드가 일치하지 않습니다.'}), 401

        if reservation['email_dispatch_code_expires_at']:
            expires_at = datetime.datetime.fromisoformat(reservation['email_dispatch_code_expires_at'])
            if datetime.datetime.now() > expires_at:
                return jsonify({'success': False, 'error': '인증 코드가 만료되었습니다.'}), 401

        # 2. 폼 데이터 가져오기
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        passport_number = request.form.get('passport_number')
        last_name_eng = request.form.get('last_name_eng')
        first_name_eng = request.form.get('first_name_eng')
        expiry_date = request.form.get('expiry_date')
        delete_passport_photo = request.form.get('delete_passport_photo') == 'true'
        passport_photo_file = request.files.get('passport_photo')

        current_time = datetime.datetime.now().isoformat()
        customer_id = reservation['customer_id']

        # 3. 고객 정보 업데이트
        cursor.execute("""
            UPDATE customers SET name = ?, phone = ?, email = ?, updated_at = ? WHERE id = ?
        """, (name, phone, email, current_time, customer_id))

        # 4. 여권 사진 처리
        passport_info_id = reservation['passport_info_id']
        updated_passport_photo_filename = None

        if passport_info_id:
            cursor.execute("SELECT passport_photo_path FROM passport_info WHERE id = ?", (passport_info_id,))
            existing_photo = cursor.fetchone()
            if existing_photo:
                updated_passport_photo_filename = existing_photo['passport_photo_path']

        if delete_passport_photo and updated_passport_photo_filename:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], updated_passport_photo_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            updated_passport_photo_filename = None

        if passport_photo_file and allowed_file(passport_photo_file.filename):
            filename = secure_filename(passport_photo_file.filename)
            unique_filename = str(uuid.uuid4()) + os.path.splitext(filename)[1]
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            passport_photo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            passport_photo_file.save(passport_photo_path)
            updated_passport_photo_filename = unique_filename

        # 5. 여권 정보 업데이트 또는 생성
        if passport_info_id:
            cursor.execute("""
                UPDATE passport_info
                SET passport_number = ?, last_name_eng = ?, first_name_eng = ?, expiry_date = ?, passport_photo_path = ?, updated_at = ?
                WHERE id = ?
            """, (passport_number, last_name_eng, first_name_eng, expiry_date, updated_passport_photo_filename, current_time, passport_info_id))
        else:
            cursor.execute("""
                INSERT INTO passport_info (customer_id, passport_number, last_name_eng, first_name_eng, expiry_date, passport_photo_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (customer_id, passport_number, last_name_eng, first_name_eng, expiry_date, updated_passport_photo_filename, current_time, current_time))
            new_passport_info_id = cursor.lastrowid
            cursor.execute("UPDATE customers SET passport_info_id = ? WHERE id = ?", (new_passport_info_id, customer_id))

        conn.commit()

        return jsonify({'success': True, 'message': '정보가 성공적으로 업데이트되었습니다.', 'new_photo_path': updated_passport_photo_filename})

    except Exception as e:
        if conn:
            conn.rollback()
        current_app.logger.error(f"Error updating my info: {e}")
        return jsonify({'success': False, 'error': '서버 오류가 발생했습니다.'}), 500
    finally:
        if conn:
            conn.close()

@public_bp.route('/api/public/send_login_code', methods=['POST'])
def send_reservation_login_code():
    data = request.get_json()
    reservation_code = data.get('reservation_code')
    customer_email = data.get('customer_email')

    if not reservation_code or not customer_email:
        return jsonify({'error': 'Reservation code and customer email are required'}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch reservation and customer information
        cursor.execute("""
            SELECT r.id, c.email
            FROM reservations r
            JOIN customers c ON r.customer_id = c.id
            WHERE r.reservation_code = ? AND c.email = ? AND r.deleted_at IS NULL
        """, (reservation_code, customer_email))
        reservation = cursor.fetchone()

        if not reservation:
            return jsonify({'error': 'Reservation not found or email does not match'}), 404

        # Generate a 6-digit dispatch code
        email_dispatch_code = str(random.randint(100000, 999999))
        # Set expiration time (e.g., 15 minutes from now)
        expires_at = datetime.datetime.now() + datetime.timedelta(minutes=15)

        # Update reservation with dispatch code and expiry
        cursor.execute("""
            UPDATE reservations
            SET email_dispatch_code = ?,
                email_dispatch_code_expires_at = ?,
                updated_at = ?
            WHERE id = ?
        """, (email_dispatch_code, expires_at.isoformat(), datetime.datetime.now().isoformat(), reservation['id']))
        conn.commit()

        # Prepare email content
        login_url = url_for('public.login_with_reservation_code', _external=True, reservation_code=reservation_code)
        email_body = render_template(
            'emails/login_code.html',
            reservation_code=reservation_code,
            email_dispatch_code=email_dispatch_code,
            login_url=login_url
        )

        # Send email
        send_email(
            to=customer_email,
            subject=f'[Travel CRM] 예약 로그인 코드: {reservation_code}',
            template=email_body
        )

        return jsonify({'message': 'Login code sent successfully', 'email_dispatch_code': email_dispatch_code}), 200

    except Exception as e:
        current_app.logger.error(f"Error sending login code: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        if conn:
            conn.close()

@public_bp.route('/public/login')
def public_login_page():
    # This route will render a simple page where users can input reservation code and email dispatch code
    return render_template('public_login.html')

@public_bp.route('/public/login/authenticate', methods=['POST'])
def login_with_reservation_code():
    reservation_code = request.form.get('reservation_code')
    email_dispatch_code = request.form.get('email_dispatch_code')

    if not reservation_code or not email_dispatch_code:
        return render_template('errors/api_error.html', message='예약 코드와 인증 코드를 모두 입력해주세요.'), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT r.id, r.email_dispatch_code, r.email_dispatch_code_expires_at, c.email
            FROM reservations r
            JOIN customers c ON r.customer_id = c.id
            WHERE r.reservation_code = ? AND r.deleted_at IS NULL
        """, (reservation_code,))
        reservation = cursor.fetchone()

        if not reservation:
            return render_template('errors/api_error.html', message='유효하지 않은 예약 코드입니다.'), 404

        # Check if dispatch code matches and is not expired
        stored_dispatch_code = reservation['email_dispatch_code']
        expires_at_str = reservation['email_dispatch_code_expires_at']
        customer_email_from_db = reservation['email']

        if not stored_dispatch_code or stored_dispatch_code != email_dispatch_code:
            return render_template('errors/api_error.html', message='인증 코드가 일치하지 않습니다.'), 401

        if expires_at_str:
            expires_at = datetime.datetime.fromisoformat(expires_at_str)
            if datetime.datetime.now() > expires_at:
                return render_template('errors/api_error.html', message='인증 코드가 만료되었습니다. 다시 요청해주세요.'), 401

        # If everything is valid, proceed with login logic
        # For now, let's redirect to a success page or a page where they can update info
        # In a real application, you might set a session or a temporary token here
        current_app.logger.info(f"Public login successful for reservation: {reservation_code}, email: {customer_email_from_db}")
        return redirect(url_for('public.my_trip_page', reservation_code=reservation_code)) # Redirect to the new trip page

    except Exception as e:
        current_app.logger.error(f"Error during public login: {e}")
        return render_template('errors/api_error.html', message='로그인 중 오류가 발생했습니다.'), 500
    finally:
        if conn:
            conn.close() 