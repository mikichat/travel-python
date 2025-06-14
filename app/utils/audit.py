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

def get_audit_logs(limit=100, offset=0, table_name=None, record_id=None):
    """
    변경 로그 조회
    
    Args:
        limit (int): 조회할 로그 개수
        offset (int): 시작 위치
        table_name (str, optional): 특정 테이블만 조회
        record_id (int, optional): 특정 레코드만 조회
    
    Returns:
        list: 변경 로그 목록
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT al.*, 
                   CASE 
                       WHEN al.table_name = 'customers' THEN c.name
                       WHEN al.table_name = 'schedules' THEN s.title
                       WHEN al.table_name = 'reservations' THEN CONCAT(c.name, ' - ', s.title)
                       ELSE 'Unknown'
                   END as record_name
            FROM audit_logs al
            LEFT JOIN customers c ON al.table_name = 'customers' AND al.record_id = c.id
            LEFT JOIN schedules s ON al.table_name = 'schedules' AND al.record_id = s.id
            LEFT JOIN reservations r ON al.table_name = 'reservations' AND al.record_id = r.id
            LEFT JOIN customers rc ON al.table_name = 'reservations' AND r.customer_id = rc.id
            LEFT JOIN schedules rs ON al.table_name = 'reservations' AND r.schedule_id = rs.id
        """
        
        conditions = []
        params = []
        
        if table_name:
            conditions.append("al.table_name = ?")
            params.append(table_name)
        
        if record_id:
            conditions.append("al.record_id = ?")
            params.append(record_id)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY al.changed_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        logs = cursor.fetchall()
        conn.close()
        
        return [dict(log) for log in logs]
    except Exception as e:
        print(f"변경 로그 조회 오류: {e}")
        return []

def get_audit_logs_count(table_name=None, record_id=None):
    """변경 로그 총 개수 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT COUNT(*) FROM audit_logs"
        conditions = []
        params = []
        
        if table_name:
            conditions.append("table_name = ?")
            params.append(table_name)
        
        if record_id:
            conditions.append("record_id = ?")
            params.append(record_id)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    except Exception as e:
        print(f"변경 로그 개수 조회 오류: {e}")
        return 0 