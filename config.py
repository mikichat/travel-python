from datetime import timedelta
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Config:
    """기본 설정 클래스 - 모든 설정을 .env 파일에서 로드합니다."""
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex()) # 환경 변수 없으면 임시 생성
    
    # 기본 도메인 URL
    BASE_DOMAIN_URL = os.getenv('BASE_DOMAIN_URL', 'http://localhost:5000')
    
    # 데이터베이스 설정
    DATABASE_PATH = os.getenv('DATABASE_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'travel.db'))
    
    # JWT 설정
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY) # JWT 시크릿 키, 없으면 FLASK_SECRET_KEY 사용
    JWT_ACCESS_TOKEN_EXPIRES_HOURS = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 24))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=JWT_ACCESS_TOKEN_EXPIRES_HOURS)
    
    # 파일 업로드 설정
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)) # 16MB 기본값
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'static', 'uploads'))
    
    # 로깅 설정
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')
    LOG_FILE = os.getenv('LOG_FILE', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'app.log'))
    CONSOLE_DEBUG_MODE = os.getenv('CONSOLE_DEBUG_MODE', 'False').lower() in ('true', '1', 't')

    # 이메일 설정
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')

    # SMS 인증 설정
    SMS_VERIFICATION_ENABLED = os.getenv('SMS_VERIFICATION_ENABLED', 'True').lower() in ('true', '1', 't')
    SMS_API_KEY = os.getenv('SMS_API_KEY')
    SMS_API_SECRET = os.getenv('SMS_API_SECRET')
    SMS_SENDER_NUMBER = os.getenv('SMS_SENDER_NUMBER')

    # 페이지네이션 설정
    PER_PAGE = int(os.getenv('PER_PAGE', 10))

    # 디버그 모드
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    TESTING = os.getenv('FLASK_TESTING', 'False').lower() in ('true', '1', 't')


# 현재 환경에 따른 설정 클래스 반환 (환경 변수 'FLASK_ENV' 사용)
# FLASK_ENV가 설정되지 않으면 'development'로 간주
# 이 부분은 더 이상 필요 없으며, Config 클래스 자체가 환경 변수를 로드함.
# 이전 방식은 별도 클래스 상속을 통한 환경별 오버라이딩이었으나, 이제는 .env 파일이 주 설정 소스. 