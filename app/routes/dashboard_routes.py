"""
대시보드 라우트
"""
from flask import Blueprint, render_template, current_app
from app.utils.auth import jwt_required
from database import get_db_connection
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@jwt_required(current_app)
def dashboard():
    """대시보드 메인 페이지"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 전체 통계
        cursor.execute('SELECT COUNT(*) FROM customers')
        total_customers = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM schedules')
        total_schedules = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM reservations')
        total_reservations = cursor.fetchone()[0]
        
        # 활성 일정 수
        cursor.execute('SELECT COUNT(*) FROM schedules WHERE status = "Active"')
        active_schedules = cursor.fetchone()[0]
        
        # 최근 예약 (최근 7일)
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute('SELECT COUNT(*) FROM reservations WHERE created_at >= ?', (seven_days_ago,))
        recent_reservations = cursor.fetchone()[0]
        
        # 최근 예약 목록 (최근 5개)
        cursor.execute("""
            SELECT r.*, c.name as customer_name, s.title as schedule_title
            FROM reservations r
            LEFT JOIN customers c ON r.customer_id = c.id
            LEFT JOIN schedules s ON r.schedule_id = s.id
            ORDER BY r.created_at DESC
            LIMIT 5
        """)
        recent_reservations_list = cursor.fetchall()
        
        # 시스템 알림 (최근 10개)
        cursor.execute("""
            SELECT * FROM audit_logs
            ORDER BY changed_at DESC
            LIMIT 10
        """)
        system_notifications = cursor.fetchall()
        
        conn.close()
        
        return render_template('dashboard.html',
                             total_customers=total_customers,
                             total_schedules=total_schedules,
                             total_reservations=total_reservations,
                             active_schedules=active_schedules,
                             recent_reservations=recent_reservations,
                             recent_reservations_list=recent_reservations_list,
                             system_notifications=system_notifications)
    except Exception as e:
        print(f'대시보드 로드 오류: {e}')
        return render_template('dashboard.html', error='대시보드를 불러오는 중 오류가 발생했습니다.')

@dashboard_bp.route('/api/stats')
@jwt_required(current_app)
def get_stats():
    """대시보드 통계 API"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 기본 통계
        cursor.execute('SELECT COUNT(*) FROM customers')
        total_customers = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM schedules')
        total_schedules = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM reservations')
        total_reservations = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM schedules WHERE status = "Active"')
        active_schedules = cursor.fetchone()[0]
        
        # 최근 예약
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute('SELECT COUNT(*) FROM reservations WHERE created_at >= ?', (seven_days_ago,))
        recent_reservations = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_customers': total_customers,
            'total_schedules': total_schedules,
            'total_reservations': total_reservations,
            'active_schedules': active_schedules,
            'recent_reservations': recent_reservations
        }
    except Exception as e:
        print(f'통계 조회 오류: {e}')
        return {'error': '통계를 불러오는 중 오류가 발생했습니다.'}, 500 