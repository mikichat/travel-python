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
        self.passport_attachment_path = passport_attachment_path
        self.memo = memo
        self.created_at = created_at
        self.updated_at = updated_at

    @staticmethod
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ticketing ORDER BY created_at DESC")
        ticketing_entries = [Ticketing(*row) for row in cursor.fetchall()]
        conn.close()
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
        if self.id:
            cursor.execute("""
                UPDATE ticketing
                SET airline_type = ?, flight_type = ?, ticketing_status = ?, ticket_code = ?, passport_attachment_path = ?, memo = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (self.airline_type, self.flight_type, self.ticketing_status, self.ticket_code, self.passport_attachment_path, self.memo, self.id))
        else:
            cursor.execute("""
                INSERT INTO ticketing (airline_type, flight_type, ticketing_status, ticket_code, passport_attachment_path, memo, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (self.airline_type, self.flight_type, self.ticketing_status, self.ticket_code, self.passport_attachment_path, self.memo))
            self.id = cursor.lastrowid
        conn.commit()
        conn.close()

    @staticmethod
    def delete(ticketing_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ticketing WHERE id = ?", (ticketing_id,))
        conn.commit()
        conn.close() 