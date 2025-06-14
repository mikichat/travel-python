import os
from app import create_app
from database import initialize_database

# 환경 변수 설정
os.environ.setdefault('FLASK_ENV', 'development')

# 애플리케이션 생성
app = create_app()

# 데이터베이스 초기화
with app.app_context():
    initialize_database()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 