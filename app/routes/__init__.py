# Routes package 
from flask import Blueprint, render_template, current_app
from app.utils.auth import jwt_required

# 대시보드 블루프린트
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@jwt_required(current_app)
def dashboard():
    """메인 대시보드 페이지"""
    try:
        # 간단한 통계 데이터 (실제로는 데이터베이스에서 조회)
        stats = {
            'total_customers': 0,
            'total_schedules': 0,
            'total_reservations': 0,
            'recent_reservations': []
        }
        
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        print(f'대시보드 로드 오류: {e}')
        return render_template('dashboard.html', error='대시보드를 불러오는 중 오류가 발생했습니다.') 