from flask import Blueprint, render_template, request, jsonify, url_for, current_app, redirect
from database import get_db_connection
import datetime
import random
from app.utils.mail import send_email

public_bp = Blueprint('public', __name__)

@public_bp.route('/<string:reservation_code>')
def view_reservation_by_code(reservation_code):
    # 5자리, 앞 2자리 숫자, 뒤 3자리 영문 대소문자인 예약코드만 허용
    if len(reservation_code) == 5 and \
       reservation_code[:2].isdigit() and \
       reservation_code[2:].isalpha():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, c.name as customer_name, s.title as schedule_title,
                   s.start_date as travel_start_date, s.end_date as travel_end_date
            FROM reservations r
            LEFT JOIN customers c ON r.customer_id = c.id
            LEFT JOIN schedules s ON r.schedule_id = s.id
            WHERE r.reservation_code = ? AND r.deleted_at IS NULL
        """, (reservation_code,))
        reservation = cursor.fetchone()
        conn.close()
        if reservation:
            reservation_dict = dict(reservation)
            # booking_date를 YYYY-MM-DD 형식으로 변환
            if reservation_dict.get('booking_date'):
                try:
                    # ISO 8601 형식 (마이크로초 포함, 'T' 구분자)
                    booking_datetime = datetime.datetime.strptime(reservation_dict['booking_date'], '%Y-%m-%dT%H:%M:%S.%f')
                except ValueError:
                    try:
                        # ISO 8601 형식 (마이크로초 없음, 'T' 구분자)
                        booking_datetime = datetime.datetime.strptime(reservation_dict['booking_date'], '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        try:
                            # 기존 형식 (마이크로초 포함, 공백 구분자)
                            booking_datetime = datetime.datetime.strptime(reservation_dict['booking_date'], '%Y-%m-%d %H:%M:%S.%f')
                        except ValueError:
                            try:
                                # 기존 형식 (마이크로초 없음, 공백 구분자)
                                booking_datetime = datetime.datetime.strptime(reservation_dict['booking_date'], '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                booking_datetime = None

                if booking_datetime:
                    reservation_dict['booking_date'] = booking_datetime.strftime('%Y-%m-%d')
                else:
                    reservation_dict['booking_date'] = reservation_dict['booking_date'] # 실패 시 원본 유지

            reservation_dict['customer_name'] = reservation_dict.get('customer_name', '알 수 없음')
            reservation_dict['schedule_title'] = reservation_dict.get('schedule_title', '알 수 없음')
            reservation_dict['travel_start_date'] = reservation_dict.get('travel_start_date', '')
            reservation_dict['travel_end_date'] = reservation_dict.get('travel_end_date', '')
            return render_template('view_reservation.html', reservation=reservation_dict)
    return render_template('errors/404.html'), 404

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
        return redirect(url_for('public.view_reservation_by_code', reservation_code=reservation_code)) # Redirect to view reservation page or a dedicated update page

    except Exception as e:
        current_app.logger.error(f"Error during public login: {e}")
        return render_template('errors/api_error.html', message='로그인 중 오류가 발생했습니다.'), 500
    finally:
        if conn:
            conn.close() 