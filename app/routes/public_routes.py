from flask import Blueprint, render_template
from database import get_db_connection
import datetime

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