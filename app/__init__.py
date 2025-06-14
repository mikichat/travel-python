from flask import Flask
import os
from app.utils.errors import register_error_handlers

def create_app():
    """
    Flask 애플리케이션 팩토리 함수
    """
    app = Flask(__name__)
    
    # 기본 설정
    app.config['SECRET_KEY'] = os.environ.get('JWT_SECRET', 'your-secret-key')
    app.config['FLASK_SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))
    
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
    
    # 블루프린트 등록
    from app.routes import auth_routes, customer_routes, schedule_routes, reservation_routes
    from app.routes import dashboard_bp
    
    app.register_blueprint(auth_routes.auth_bp)
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(customer_routes.customer_bp, url_prefix='/customers')
    app.register_blueprint(schedule_routes.schedule_bp, url_prefix='/schedules')
    app.register_blueprint(reservation_routes.reservation_bp, url_prefix='/reservations')
    
    return app 