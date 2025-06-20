import sqlite3
import os

DATABASE = './data/travel_crm.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    # users 테이블 생성 (비밀번호는 해시되어 저장)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # customers 테이블 생성
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            address TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT
        )
    """)
    cursor.execute("PRAGMA table_info(customers)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'deleted_at' not in columns:
        cursor.execute("""
            ALTER TABLE customers ADD COLUMN deleted_at TEXT
        """)

    # schedules 테이블 생성
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            destination TEXT NOT NULL,
            price REAL DEFAULT 0,
            max_people INTEGER DEFAULT 1,
            status TEXT DEFAULT 'Active',
            duration TEXT,
            region TEXT,
            meeting_date TEXT,
            meeting_time TEXT,
            meeting_place TEXT,
            manager TEXT,
            reservation_maker TEXT,
            reservation_maker_contact TEXT,
            important_docs TEXT,
            currency_info TEXT,
            other_items TEXT,
            memo TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT
        )
    """)
    cursor.execute("PRAGMA table_info(schedules)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'deleted_at' not in columns:
        cursor.execute("""
            ALTER TABLE schedules ADD COLUMN deleted_at TEXT
        """)

    # reservations 테이블 생성
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            schedule_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'REQUESTED',
            booking_date TEXT NOT NULL,
            number_of_people INTEGER NOT NULL,
            total_price REAL NOT NULL,
            notes TEXT,
            reservation_code TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
            FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("PRAGMA table_info(reservations)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'reservation_code' not in columns:
        cursor.execute("""
            ALTER TABLE reservations ADD COLUMN reservation_code TEXT
        """)
    if 'email_dispatch_code' not in columns:
        cursor.execute("""
            ALTER TABLE reservations ADD COLUMN email_dispatch_code TEXT
        """
        )
    if 'email_dispatch_code_expires_at' not in columns:
        cursor.execute("""
            ALTER TABLE reservations ADD COLUMN email_dispatch_code_expires_at TEXT
        """
        )

    # audit_logs 테이블 생성 (변경 로그)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            field_name TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            changed_at TEXT NOT NULL,
            changed_by TEXT NOT NULL,
            details TEXT,
            updated_at TEXT NOT NULL,
            deleted_at TEXT
        )
    """)

    # ticketing 테이블 생성
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ticketing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            airline_type TEXT NOT NULL,
            flight_type TEXT NOT NULL,
            ticketing_status TEXT NOT NULL,
            ticket_code TEXT NOT NULL,
            passport_attachment_path TEXT,
            memo TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT
        )
    """)
    cursor.execute("PRAGMA table_info(ticketing)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'deleted_at' not in columns:
        cursor.execute("""
            ALTER TABLE ticketing ADD COLUMN deleted_at TEXT
        """)

    # passport_info 테이블 생성 (고객 연동)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS passport_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            passport_number TEXT,
            last_name_eng TEXT,
            first_name_eng TEXT,
            expiry_date TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
        )
    """)

    # companies 테이블 생성
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT,
            notes TEXT,
            items TEXT,  -- 항공,호텔,교통,식사,가이드,옵션투어,보험,비자 (콤마구분)
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT
        )
    """)
    cursor.execute("PRAGMA table_info(companies)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'deleted_at' not in columns:
        cursor.execute("""
            ALTER TABLE companies ADD COLUMN deleted_at TEXT
        """)

    conn.commit()
    conn.close() 