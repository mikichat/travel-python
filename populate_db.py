import sqlite3
import bcrypt
from datetime import datetime
from database import get_db_connection, initialize_database # database.py에서 함수 가져오기

def log_change(cursor, table_name, record_id, action, field_name, old_value, new_value, changed_by, details=None):
    """변경 로그를 데이터베이스에 기록"""
    current_time = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO audit_logs (table_name, record_id, action, field_name, old_value, new_value, changed_at, changed_by, details, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (table_name, record_id, action, field_name, old_value, new_value, current_time, changed_by, details, current_time))

def populate_sample_data():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 기존 데이터 삭제 (재실행 시 중복 방지)
    cursor.execute("DELETE FROM audit_logs")  # 변경 로그도 삭제
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM customers")
    cursor.execute("DELETE FROM schedules")
    cursor.execute("DELETE FROM reservations")
    cursor.execute("DELETE FROM companies")
    conn.commit()

    print("기존 데이터 삭제 완료.")

    # 1. 사용자 샘플 데이터 삽입
    hashed_password = bcrypt.hashpw("admin".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    now = datetime.now().isoformat()
    cursor.execute("INSERT INTO users (username, email, password, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                   ("admin", "admin@example.com", hashed_password, now, now))
    admin_id = cursor.lastrowid
    log_change(cursor, 'users', admin_id, 'CREATE', 'all', None, '관리자 계정 생성', 'system', '샘플 데이터 생성')
    
    cursor.execute("INSERT INTO users (username, email, password, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                   ("testuser", "test@example.com", bcrypt.hashpw("testpass".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), now, now))
    testuser_id = cursor.lastrowid
    log_change(cursor, 'users', testuser_id, 'CREATE', 'all', None, '테스트 사용자 계정 생성', 'system', '샘플 데이터 생성')
    
    conn.commit()
    print("사용자 샘플 데이터 삽입 완료.")

    # 2. 고객 샘플 데이터 삽입
    cursor.execute("INSERT INTO customers (name, phone, email, address, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ("김철수", "010-1234-5678", "chulsoo@example.com", "서울시 강남구", "VIP 고객", now, now))
    customer1_id = cursor.lastrowid
    log_change(cursor, 'customers', customer1_id, 'CREATE', 'all', None, '고객 생성: 김철수', 'system', '샘플 데이터 생성')
    
    cursor.execute("INSERT INTO customers (name, phone, email, address, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ("이영희", "010-9876-5432", "younghee@example.com", "부산시 해운대구", "단체 여행 선호", now, now))
    customer2_id = cursor.lastrowid
    log_change(cursor, 'customers', customer2_id, 'CREATE', 'all', None, '고객 생성: 이영희', 'system', '샘플 데이터 생성')
    
    conn.commit()
    print("고객 샘플 데이터 삽입 완료.")

    # 3. 일정 샘플 데이터 삽입
    cursor.execute("INSERT INTO schedules (title, description, start_date, end_date, destination, price, max_people, status, duration, region, meeting_date, meeting_time, meeting_place, manager, reservation_maker, reservation_maker_contact, important_docs, currency_info, other_items, memo, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   ("유럽 7박 9일 패키지", "파리, 로마, 런던 3개국 투어", "2025-07-01", "2025-07-09", "유럽", 3500.00, 20, "Active", "7박 9일", "유럽", "2025-06-25", "10:00", "인천공항 3층 A카운터", "박선우", "이동민", "010-1111-2222", "여권 사본, 비자", "EUR", "여행자 보험 포함", "단체 여행 일정", now, now))
    schedule1_id = cursor.lastrowid
    log_change(cursor, 'schedules', schedule1_id, 'CREATE', 'all', None, '일정 생성: 유럽 7박 9일 패키지', 'system', '샘플 데이터 생성')
    
    cursor.execute("INSERT INTO schedules (title, description, start_date, end_date, destination, price, max_people, status, duration, region, meeting_date, meeting_time, meeting_place, manager, reservation_maker, reservation_maker_contact, important_docs, currency_info, other_items, memo, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   ("제주도 2박 3일 힐링", "렌터카 포함 자유 일정", "2025-08-10", "2025-08-12", "제주도", 450.00, 10, "Active", "2박 3일", "국내", "2025-08-05", "14:00", "제주공항 렌터카 하우스", "최지영", "박영희", "010-3333-4444", "신분증", "KRW", "항공권 포함", "커플 여행 적합", now, now))
    schedule2_id = cursor.lastrowid
    log_change(cursor, 'schedules', schedule2_id, 'CREATE', 'all', None, '일정 생성: 제주도 2박 3일 힐링', 'system', '샘플 데이터 생성')
    
    conn.commit()
    print("일정 샘플 데이터 삽입 완료.")

    # 4. 예약 샘플 데이터 삽입
    cursor.execute("INSERT INTO reservations (customer_id, schedule_id, status, booking_date, number_of_people, total_price, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (customer1_id, schedule1_id, "Confirmed", now, 2, 7000.00, "김철수 고객의 유럽 여행 예약", now, now))
    reservation1_id = cursor.lastrowid
    log_change(cursor, 'reservations', reservation1_id, 'CREATE', 'all', None, f'예약 생성: 고객ID {customer1_id}, 일정ID {schedule1_id}', 'system', '샘플 데이터 생성')
    
    cursor.execute("INSERT INTO reservations (customer_id, schedule_id, status, booking_date, number_of_people, total_price, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (customer2_id, schedule2_id, "Pending", now, 4, 1800.00, "이영희 고객의 제주도 여행 예약 (4인)", now, now))
    reservation2_id = cursor.lastrowid
    log_change(cursor, 'reservations', reservation2_id, 'CREATE', 'all', None, f'예약 생성: 고객ID {customer2_id}, 일정ID {schedule2_id}', 'system', '샘플 데이터 생성')
    
    conn.commit()
    print("예약 샘플 데이터 삽입 완료.")

    # 5. 업체(렌드사) 샘플 데이터 삽입
    companies_samples = [
        ("코리아항공", "02-123-4567", "air@koreaair.com", "서울 강서구 공항대로 123", "국내외 항공 전문", "항공,호텔", now, now),
        ("월드호텔네트워크", "02-234-5678", "info@worldhotel.com", "서울 중구 남대문로 456", "글로벌 호텔 체인", "호텔,식사,가이드", now, now),
        ("제주렌트카", "064-789-1234", "rent@jejurent.com", "제주 제주시 공항로 789", "제주도 교통/렌트 전문", "교통,보험", now, now),
        ("투어가이드코리아", "02-345-6789", "guide@tourkorea.com", "서울 종로구 인사동 101", "전문 가이드 및 옵션투어", "가이드,옵션투어,비자", now, now),
        ("글로벌여행보험", "02-456-7890", "insure@globalins.com", "서울 영등포구 국제금융로 202", "여행자 보험 전문", "보험,비자", now, now),
    ]
    for name, phone, email, address, notes, items, created_at, updated_at in companies_samples:
        cursor.execute("INSERT INTO companies (name, phone, email, address, notes, items, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (name, phone, email, address, notes, items, created_at, updated_at))
        company_id = cursor.lastrowid
        log_change(cursor, 'companies', company_id, 'CREATE', 'all', None, f'업체 생성: {name}', 'system', '샘플 데이터 생성')
    conn.commit()
    print("업체(렌드사) 샘플 데이터 삽입 완료.")

    conn.close()
    print("샘플 데이터 생성 완료.")
    print("변경 로그도 함께 기록되었습니다.")

if __name__ == '__main__':
    # 데이터베이스 초기화 함수 호출 (테이블이 없으면 생성)
    initialize_database()
    populate_sample_data() 