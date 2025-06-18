"""
변경 로그 유틸리티 함수들
"""
from datetime import datetime
from database import get_db_connection

def log_change(table_name, record_id, action, field_name, old_value, new_value, changed_by, details=None):
    """
    변경 로그를 데이터베이스에 기록
    
    Args:
        table_name (str): 테이블 이름 (customers, schedules, reservations)
        record_id (int): 레코드 ID
        action (str): 액션 (CREATE, UPDATE, DELETE)
        field_name (str): 변경된 필드 이름
        old_value (str): 변경 전 값
        new_value (str): 변경 후 값
        changed_by (str): 변경자 이름
        details (str, optional): 추가 세부사항
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        current_time = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO audit_logs (table_name, record_id, action, field_name, old_value, new_value, changed_at, changed_by, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (table_name, record_id, action, field_name, old_value, new_value, current_time, changed_by, details))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"변경 로그 기록 오류: {e}")

def log_customer_change(customer_id, action, field_name, old_value, new_value, changed_by, details=None):
    """고객 변경 로그 기록"""
    log_change('customers', customer_id, action, field_name, old_value, new_value, changed_by, details)

def log_schedule_change(schedule_id, action, field_name, old_value, new_value, changed_by, details=None):
    """일정 변경 로그 기록"""
    log_change('schedules', schedule_id, action, field_name, old_value, new_value, changed_by, details)

def log_reservation_change(reservation_id, action, field_name, old_value, new_value, changed_by, details=None):
    """예약 변경 로그 기록"""
    log_change('reservations', reservation_id, action, field_name, old_value, new_value, changed_by, details)

def get_audit_logs(limit, offset, table_name=None, record_id=None, search_term=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []

    if table_name:
        query += " AND table_name = ?"
        params.append(table_name)
    if record_id is not None:
        query += " AND record_id = ?"
        params.append(record_id)
    if search_term:
        search_term_like = f"%{search_term}%"
        query += " AND (action LIKE ? OR field_name LIKE ? OR changed_by LIKE ? OR details LIKE ?)"
        params.extend([search_term_like, search_term_like, search_term_like, search_term_like])

    query += " ORDER BY changed_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    logs = cursor.fetchall()
    conn.close()
    return logs

def get_audit_logs_count(table_name=None, record_id=None, search_term=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT COUNT(*) FROM audit_logs WHERE 1=1"
    params = []

    if table_name:
        query += " AND table_name = ?"
        params.append(table_name)
    if record_id is not None:
        query += " AND record_id = ?"
        params.append(record_id)
    if search_term:
        search_term_like = f"%{search_term}%"
        query += " AND (action LIKE ? OR field_name LIKE ? OR changed_by LIKE ? OR details LIKE ?)"
        params.extend([search_term_like, search_term_like, search_term_like, search_term_like])

    cursor.execute(query, params)
    total_count = cursor.fetchone()[0]
    conn.close()
    return total_count 