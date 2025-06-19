from database import get_db_connection
from datetime import datetime

class Company:
    def __init__(self, id, name, phone, email, address, notes, items, created_at, updated_at, deleted_at=None):
        self.id = id
        self.name = name
        self.phone = phone
        self.email = email
        self.address = address
        self.notes = notes
        if isinstance(items, str):
            self.items = items.split(',') if items else []
        elif isinstance(items, list):
            self.items = items
        else:
            self.items = []
        self.created_at = created_at
        self.updated_at = updated_at
        self.deleted_at = deleted_at

    @staticmethod
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM companies WHERE deleted_at IS NULL ORDER BY created_at DESC")
        companies = [Company(*row) for row in cursor.fetchall()]
        conn.close()
        return companies

    @staticmethod
    def get_by_id(company_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM companies WHERE id = ? AND deleted_at IS NULL", (company_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return Company(*row)
        return None

    def save(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().isoformat()
        items_str = ','.join(self.items) if isinstance(self.items, list) else self.items
        if self.id:
            self.updated_at = current_time
            cursor.execute("""
                UPDATE companies SET name=?, phone=?, email=?, address=?, notes=?, items=?, updated_at=?, deleted_at=? WHERE id=?
            """, (self.name, self.phone, self.email, self.address, self.notes, items_str, self.updated_at, self.deleted_at, self.id))
        else:
            self.created_at = current_time
            self.updated_at = current_time
            cursor.execute("""
                INSERT INTO companies (name, phone, email, address, notes, items, created_at, updated_at, deleted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.name, self.phone, self.email, self.address, self.notes, items_str, self.created_at, self.updated_at, self.deleted_at))
            self.id = cursor.lastrowid
        conn.commit()
        conn.close()

    @staticmethod
    def soft_delete(company_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().isoformat()
        cursor.execute("UPDATE companies SET deleted_at = ?, updated_at = ? WHERE id = ?", (current_time, current_time, company_id))
        conn.commit()
        conn.close()

    @staticmethod
    def restore(company_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().isoformat()
        cursor.execute("UPDATE companies SET deleted_at = NULL, updated_at = ? WHERE id = ?", (current_time, company_id))
        conn.commit()
        conn.close() 