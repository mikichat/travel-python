"""
엑셀 파일 처리 유틸리티
"""
import pandas as pd
import io
from datetime import datetime
from database import get_db_connection
import logging

logger = logging.getLogger(__name__)

def export_customers_to_excel():
    """고객 데이터를 엑셀 파일로 내보내기"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 고객 데이터 조회
        cursor.execute("""
            SELECT id, name, email, phone, address, created_at, updated_at
            FROM customers
            ORDER BY created_at DESC
        """)
        
        customers = cursor.fetchall()
        conn.close()
        
        # DataFrame 생성
        df = pd.DataFrame(customers, columns=[
            'ID', '이름', '이메일', '전화번호', '주소', '생성일', '수정일'
        ])
        
        # 엑셀 파일 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='고객목록', index=False)
        
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"고객 데이터 내보내기 오류: {e}")
        raise

def import_customers_from_excel(file_content):
    """엑셀 파일에서 고객 데이터 가져오기"""
    try:
        # 엑셀 파일 읽기
        df = pd.read_excel(io.BytesIO(file_content))
        
        # 필수 컬럼 확인
        required_columns = ['이름', '이메일', '전화번호']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"필수 컬럼이 누락되었습니다: {missing_columns}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        success_count = 0
        error_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # 데이터 검증
                if pd.isna(row['이름']) or pd.isna(row['이메일']):
                    errors.append(f"행 {index + 2}: 이름과 이메일은 필수입니다.")
                    error_count += 1
                    continue
                
                # 중복 이메일 확인
                cursor.execute('SELECT id FROM customers WHERE email = ?', (row['이메일'],))
                if cursor.fetchone():
                    errors.append(f"행 {index + 2}: 이미 존재하는 이메일입니다 - {row['이메일']}")
                    error_count += 1
                    continue
                
                # 고객 추가
                cursor.execute("""
                    INSERT INTO customers (name, email, phone, address, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    row['이름'],
                    row['이메일'],
                    row.get('전화번호', ''),
                    row.get('주소', ''),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                
                success_count += 1
                
            except Exception as e:
                errors.append(f"행 {index + 2}: {str(e)}")
                error_count += 1
        
        conn.commit()
        conn.close()
        
        return {
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"고객 데이터 가져오기 오류: {e}")
        raise

def export_schedules_to_excel():
    """일정 데이터를 엑셀 파일로 내보내기"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 일정 데이터 조회
        cursor.execute("""
            SELECT id, title, description, destination, start_date, end_date, 
                   price, capacity, status, created_at, updated_at
            FROM schedules
            ORDER BY start_date DESC
        """)
        
        schedules = cursor.fetchall()
        conn.close()
        
        # DataFrame 생성
        df = pd.DataFrame(schedules, columns=[
            'ID', '제목', '설명', '목적지', '출발일', '도착일', 
            '가격', '수용인원', '상태', '생성일', '수정일'
        ])
        
        # 엑셀 파일 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='일정목록', index=False)
        
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"일정 데이터 내보내기 오류: {e}")
        raise

def import_schedules_from_excel(file_content):
    """엑셀 파일에서 일정 데이터 가져오기"""
    try:
        # 엑셀 파일 읽기
        df = pd.read_excel(io.BytesIO(file_content))
        
        # 필수 컬럼 확인
        required_columns = ['제목', '목적지', '출발일', '도착일']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"필수 컬럼이 누락되었습니다: {missing_columns}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        success_count = 0
        error_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # 데이터 검증
                if pd.isna(row['제목']) or pd.isna(row['목적지']):
                    errors.append(f"행 {index + 2}: 제목과 목적지는 필수입니다.")
                    error_count += 1
                    continue
                
                # 날짜 형식 변환
                start_date = pd.to_datetime(row['출발일']).strftime('%Y-%m-%d')
                end_date = pd.to_datetime(row['도착일']).strftime('%Y-%m-%d')
                
                # 일정 추가
                cursor.execute("""
                    INSERT INTO schedules (title, description, destination, start_date, end_date, 
                                         price, capacity, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['제목'],
                    row.get('설명', ''),
                    row['목적지'],
                    start_date,
                    end_date,
                    row.get('가격', 0),
                    row.get('수용인원', 0),
                    row.get('상태', 'Active'),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                
                success_count += 1
                
            except Exception as e:
                errors.append(f"행 {index + 2}: {str(e)}")
                error_count += 1
        
        conn.commit()
        conn.close()
        
        return {
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"일정 데이터 가져오기 오류: {e}")
        raise

def export_reservations_to_excel():
    """예약 데이터를 엑셀 파일로 내보내기"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 예약 데이터 조회 (고객명과 일정명 포함)
        cursor.execute("""
            SELECT r.id, c.name as customer_name, s.title as schedule_title,
                   r.number_of_people, r.total_price, r.status, r.notes,
                   r.created_at, r.updated_at
            FROM reservations r
            LEFT JOIN customers c ON r.customer_id = c.id
            LEFT JOIN schedules s ON r.schedule_id = s.id
            ORDER BY r.created_at DESC
        """)
        
        reservations = cursor.fetchall()
        conn.close()
        
        # DataFrame 생성
        df = pd.DataFrame(reservations, columns=[
            'ID', '고객명', '일정명', '인원수', '총가격', '상태', '비고', '생성일', '수정일'
        ])
        
        # 엑셀 파일 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='예약목록', index=False)
        
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"예약 데이터 내보내기 오류: {e}")
        raise

def import_reservations_from_excel(file_content):
    """엑셀 파일에서 예약 데이터 가져오기"""
    try:
        # 엑셀 파일 읽기
        df = pd.read_excel(io.BytesIO(file_content))
        
        # 필수 컬럼 확인
        required_columns = ['고객명', '일정명', '인원수']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"필수 컬럼이 누락되었습니다: {missing_columns}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        success_count = 0
        error_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # 데이터 검증
                if pd.isna(row['고객명']) or pd.isna(row['일정명']) or pd.isna(row['인원수']):
                    errors.append(f"행 {index + 2}: 고객명, 일정명, 인원수는 필수입니다.")
                    error_count += 1
                    continue
                
                # 고객 ID 조회
                cursor.execute('SELECT id FROM customers WHERE name = ?', (row['고객명'],))
                customer_result = cursor.fetchone()
                if not customer_result:
                    errors.append(f"행 {index + 2}: 존재하지 않는 고객명입니다 - {row['고객명']}")
                    error_count += 1
                    continue
                
                # 일정 ID 조회
                cursor.execute('SELECT id FROM schedules WHERE title = ?', (row['일정명'],))
                schedule_result = cursor.fetchone()
                if not schedule_result:
                    errors.append(f"행 {index + 2}: 존재하지 않는 일정명입니다 - {row['일정명']}")
                    error_count += 1
                    continue
                
                # 예약 추가
                cursor.execute("""
                    INSERT INTO reservations (customer_id, schedule_id, number_of_people, 
                                            total_price, status, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    customer_result[0],
                    schedule_result[0],
                    int(row['인원수']),
                    row.get('총가격', 0),
                    row.get('상태', 'Pending'),
                    row.get('비고', ''),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                
                success_count += 1
                
            except Exception as e:
                errors.append(f"행 {index + 2}: {str(e)}")
                error_count += 1
        
        conn.commit()
        conn.close()
        
        return {
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"예약 데이터 가져오기 오류: {e}")
        raise 