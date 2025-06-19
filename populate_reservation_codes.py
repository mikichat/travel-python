import sqlite3
from app.utils import generate_reservation_code

DB_PATH = './data/travel_crm.db'

def update_reservation_codes():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # reservation_code가 없거나 NULL인 예약만 선택
    cursor.execute("SELECT id FROM reservations WHERE reservation_code IS NULL OR reservation_code = ''")
    rows = cursor.fetchall()

    for row in rows:
        code = generate_reservation_code()
        cursor.execute(
            "UPDATE reservations SET reservation_code = ? WHERE id = ?",
            (code, row['id'])
        )
        print(f"예약 ID {row['id']} → 코드 {code} 추가")

    conn.commit()
    conn.close()
    print("모든 예약에 코드가 추가되었습니다.")

if __name__ == '__main__':
    update_reservation_codes() 