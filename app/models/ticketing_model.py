from database import get_db_connection

class Ticketing:
    """
    발권 정보를 관리하는 모델
    """
    def __init__(self, id, airline_type, flight_type, ticketing_status, ticket_code, passport_attachment_path, memo, created_at, updated_at):
        self.id = id
        self.airline_type = airline_type
        self.flight_type = flight_type
        self.ticketing_status = ticketing_status
        self.ticket_code = ticket_code
        self.memo = memo
        self.created_at = created_at
        self.updated_at = updated_at
        # 콤마로 구분된 문자열을 리스트로 변환
        self._passport_attachment_paths = passport_attachment_path.split(',') if passport_attachment_path else []

    @property
    def passport_attachment_paths(self):
        return self._passport_attachment_paths

    @passport_attachment_paths.setter
    def passport_attachment_paths(self, paths):
        if isinstance(paths, list):
            self._passport_attachment_paths = paths
        elif isinstance(paths, str):
            self._passport_attachment_paths = paths.split(',') if paths else []
        else:
            self._passport_attachment_paths = []

    @staticmethod
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ticketing ORDER BY created_at DESC")
        ticketing_entries = [Ticketing(*row) for row in cursor.fetchall()]
        conn.close()
        return ticketing_entries

    @staticmethod
    def search(airline_type=None, flight_type=None, ticketing_status=None, ticket_code=None, offset=0, limit=None, include_total_count=False):
        conn = get_db_connection()
        cursor = conn.cursor()

        base_query = "SELECT * FROM ticketing WHERE 1=1"
        count_query = "SELECT COUNT(*) FROM ticketing WHERE 1=1"

        conditions = []
        params = []

        if airline_type:
            conditions.append("airline_type LIKE ?")
            params.append(f'%{airline_type}%')
        if flight_type:
            conditions.append("flight_type LIKE ?")
            params.append(f'%{flight_type}%')
        if ticketing_status:
            conditions.append("ticketing_status = ?")
            params.append(ticketing_status)
        if ticket_code:
            conditions.append("ticket_code LIKE ?")
            params.append(f'%{ticket_code}%')

        if conditions:
            base_query += " AND " + " AND ".join(conditions)
            count_query += " AND " + " AND ".join(conditions)

        total_count = 0
        if include_total_count:
            cursor.execute(count_query, tuple(params))
            total_count = cursor.fetchone()[0]

        base_query += " ORDER BY created_at DESC"

        if limit is not None:
            base_query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        cursor.execute(base_query, tuple(params))
        ticketing_entries = [Ticketing(*row) for row in cursor.fetchall()]
        conn.close()

        if include_total_count:
            return ticketing_entries, total_count
        return ticketing_entries

    @staticmethod
    def get_by_id(ticketing_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ticketing WHERE id = ?", (ticketing_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return Ticketing(*row)
        return None

    def save(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        # 리스트를 콤마로 구분된 문자열로 변환하여 DB에 저장
        db_passport_paths = ','.join(self.passport_attachment_paths)

        if self.id:
            cursor.execute("""
                UPDATE ticketing
                SET airline_type = ?, flight_type = ?, ticketing_status = ?, ticket_code = ?, passport_attachment_path = ?, memo = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (self.airline_type, self.flight_type, self.ticketing_status, self.ticket_code, db_passport_paths, self.memo, self.id))
        else:
            cursor.execute("""
                INSERT INTO ticketing (airline_type, flight_type, ticketing_status, ticket_code, passport_attachment_path, memo, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (self.airline_type, self.flight_type, self.ticketing_status, self.ticket_code, db_passport_paths, self.memo))
            self.id = cursor.lastrowid
        conn.commit()
        conn.close()

    @staticmethod
    def delete(ticketing_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        # 파일 삭제를 위해 기존 경로를 먼저 조회
        cursor.execute("SELECT passport_attachment_path FROM ticketing WHERE id = ?", (ticketing_id,))
        row = cursor.fetchone()
        
        conn.execute("DELETE FROM ticketing WHERE id = ?", (ticketing_id,))
        conn.commit()
        conn.close()
        
        # 삭제할 파일 경로 리스트 반환
        return row[0].split(',') if row and row[0] else [] 