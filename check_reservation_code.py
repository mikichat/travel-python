import sqlite3

DB_PATH = './data/travel_crm.db'

def check_reservation_code(code):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reservations WHERE reservation_code = ?", (code,))
    row = cursor.fetchone()
    conn.close()
    if row:
        print("예약 정보:")
        for key in row.keys():
            print(f"{key}: {row[key]}")
    else:
        print("해당 예약코드로 예약을 찾을 수 없습니다.")

if __name__ == '__main__':
    code = input('조회할 예약코드를 입력하세요: ').strip()
    check_reservation_code(code) 