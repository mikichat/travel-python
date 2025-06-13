import sqlite3
import bcrypt
from datetime import datetime
from database import get_db_connection, initialize_database # database.py에서 함수 가져오기

def populate_sample_data():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 기존 데이터 삭제 (재실행 시 중복 방지)
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM customers")
    cursor.execute("DELETE FROM schedules")
    cursor.execute("DELETE FROM reservations")
    conn.commit()

    print("기존 데이터 삭제 완료.")

    # 1. 사용자 샘플 데이터 삽입
    hashed_password = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    now = datetime.now().isoformat()
    cursor.execute("INSERT INTO users (username, email, password, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                   ("admin", "admin@example.com", hashed_password, now, now))
    cursor.execute("INSERT INTO users (username, email, password, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                   ("testuser", "test@example.com", bcrypt.hashpw("testpass".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), now, now))
    print("사용자 샘플 데이터 삽입 완료.")

    # 2. 고객 샘플 데이터 삽입
    cursor.execute("INSERT INTO customers (name, phone, email, address, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ("김철수", "010-1234-5678", "chulsoo@example.com", "서울시 강남구", "VIP 고객", now, now))
    cursor.execute("INSERT INTO customers (name, phone, email, address, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ("이영희", "010-9876-5432", "younghee@example.com", "부산시 해운대구", "단체 여행 선호", now, now))
    conn.commit()
    print("고객 샘플 데이터 삽입 완료.")

    # 삽입된 고객 ID 가져오기
    cursor.execute("SELECT id FROM customers WHERE name = '김철수'")
    customer1_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM customers WHERE name = '이영희'")
    customer2_id = cursor.fetchone()[0]

    # 3. 일정 샘플 데이터 삽입
    cursor.execute("INSERT INTO schedules (title, description, start_date, end_date, destination, price, max_people, status, duration, region, meeting_date, meeting_time, meeting_place, manager, reservation_maker, reservation_maker_contact, important_docs, currency_info, other_items, memo, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   ("유럽 7박 9일 패키지", "파리, 로마, 런던 3개국 투어", "2025-07-01", "2025-07-09", "유럽", 3500.00, 20, "Active", "7박 9일", "유럽", "2025-06-25", "10:00", "인천공항 3층 A카운터", "박선우", "이동민", "010-1111-2222", "여권 사본, 비자", "EUR", "여행자 보험 포함", "단체 여행 일정", now, now))
    cursor.execute("INSERT INTO schedules (title, description, start_date, end_date, destination, price, max_people, status, duration, region, meeting_date, meeting_time, meeting_place, manager, reservation_maker, reservation_maker_contact, important_docs, currency_info, other_items, memo, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   ("제주도 2박 3일 힐링", "렌터카 포함 자유 일정", "2025-08-10", "2025-08-12", "제주도", 450.00, 10, "Active", "2박 3일", "국내", "2025-08-05", "14:00", "제주공항 렌터카 하우스", "최지영", "박영희", "010-3333-4444", "신분증", "KRW", "항공권 포함", "커플 여행 적합", now, now))
    conn.commit()
    print("일정 샘플 데이터 삽입 완료.")

    # 삽입된 일정 ID 가져오기
    cursor.execute("SELECT id FROM schedules WHERE title = '유럽 7박 9일 패키지'")
    schedule1_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM schedules WHERE title = '제주도 2박 3일 힐링'")
    schedule2_id = cursor.fetchone()[0]

    # 4. 예약 샘플 데이터 삽입
    cursor.execute("INSERT INTO reservations (customer_id, schedule_id, status, booking_date, number_of_people, total_price, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (customer1_id, schedule1_id, "Confirmed", now, 2, 7000.00, "김철수 고객의 유럽 여행 예약", now, now))
    cursor.execute("INSERT INTO reservations (customer_id, schedule_id, status, booking_date, number_of_people, total_price, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (customer2_id, schedule2_id, "Pending", now, 4, 1800.00, "이영희 고객의 제주도 여행 예약 (4인)", now, now))
    conn.commit()
    print("예약 샘플 데이터 삽입 완료.")

    conn.close()
    print("샘플 데이터 생성 완료.")

if __name__ == '__main__':
    # 데이터베이스 초기화 함수 호출 (테이블이 없으면 생성)
    initialize_database()
    populate_sample_data() 