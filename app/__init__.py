from flask import Flask, redirect, url_for
import os
from app.utils.errors import register_error_handlers
from flask_jwt_extended import JWTManager
from database import initialize_database
from app.routes.auth_routes import auth_bp
from app.routes.customer_routes import customer_bp
from app.routes.schedule_routes import schedule_bp
from app.routes.reservation_routes import reservation_bp
from app.routes.dashboard_routes import dashboard_bp
from app.routes.audit_routes import audit_bp
from app.routes.ticketing_routes import ticketing_bp
from app.utils.filters import register_filters
import logging

def create_app():
    """
    Flask 애플리케이션 팩토리 함수
    """
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        handlers=[
            logging.FileHandler('app.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    app = Flask(__name__)
    
    # 기본 설정
    app.config['SECRET_KEY'] = os.environ.get('JWT_SECRET', 'your-secret-key')
    app.config['FLASK_SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))
    app.config['JWT_SECRET_KEY'] = 'jwt-secret-string'
    app.config['JWT_TOKEN_LOCATION'] = ['cookies']
    app.config['JWT_COOKIE_CSRF_PROTECT'] = False
    
    # JWT 초기화
    jwt = JWTManager(app)
    
    # 데이터베이스 초기화
    initialize_database()
    
    # 오류 핸들러 등록
    register_error_handlers(app)
    
    # Jinja2 사용자 정의 필터 등록
    @app.template_filter('get_emoji_for_rank')
    def get_emoji_for_rank(rank):
        if rank == 1: return '🥇'
        if rank == 2: return '🥈'
        if rank == 3: return '🥉'
        return '🏅'

    @app.template_filter('get_status_color')
    def get_status_color(status):
        if status == 'Confirmed': return 'bg-green-100 text-green-600'
        if status == 'Pending': return 'bg-yellow-100 text-yellow-600'
        if status == 'Cancelled': return 'bg-red-100 text-red-600'
        return 'bg-gray-100 text-gray-600'

    @app.template_filter('get_status_text')
    def get_status_text(status):
        if status == 'Confirmed': return '확정'
        if status == 'Pending': return '대기'
        if status == 'Cancelled': return '취소'
        return status
    
    # 필터 등록
    register_filters(app)
    
    # 블루프린트 등록
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(customer_bp, url_prefix='/customers')
    app.register_blueprint(schedule_bp, url_prefix='/schedules')
    app.register_blueprint(reservation_bp, url_prefix='/reservations')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(audit_bp, url_prefix='/audit')
    app.register_blueprint(ticketing_bp, url_prefix='/ticketing')
    
    @app.route('/')
    def index():
        return redirect(url_for('dashboard.dashboard'))
    
    return app 