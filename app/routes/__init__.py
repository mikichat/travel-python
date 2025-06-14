# Routes package 
from flask import Blueprint, render_template, current_app
from app.utils.auth import jwt_required
from app.utils.filters import get_status_color, get_status_text, format_currency, format_date, format_datetime
import sqlite3
from datetime import datetime, timedelta

# 대시보드 블루프린트
dashboard_bp = Blueprint('dashboard', __name__)

# 필터 등록
@dashboard_bp.app_template_filter('get_status_color')
def get_status_color_filter(status):
    return get_status_color(status)

@dashboard_bp.app_template_filter('get_status_text')
def get_status_text_filter(status):
    return get_status_text(status)

@dashboard_bp.app_template_filter('format_currency')
def format_currency_filter(amount):
    return format_currency(amount)

@dashboard_bp.app_template_filter('format_date')
def format_date_filter(date_str):
    return format_date(date_str)

@dashboard_bp.app_template_filter('format_datetime')
def format_datetime_filter(datetime_str):
    return format_datetime(datetime_str)

def get_database_stats():
    """데이터베이스에서 통계 데이터 조회"""
    try:
        conn = sqlite3.connect('travel_crm.db')
        cursor = conn.cursor()
        
        # 기본 통계
        cursor.execute("SELECT COUNT(*) FROM customers")
        total_customers = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM schedules")
        total_schedules = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM reservations")
        total_reservations = cursor.fetchone()[0]
        
        # 이번 달 예약 수
        current_month = datetime.now().replace(day=1)
        cursor.execute("""
            SELECT COUNT(*) FROM reservations 
            WHERE created_at >= ?
        """, (current_month.isoformat(),))
        monthly_reservations = cursor.fetchone()[0]
        
        # 이번 달 수익 (예약 가격 합계)
        cursor.execute("""
            SELECT COALESCE(SUM(price), 0) FROM reservations 
            WHERE created_at >= ? AND status != 'cancelled'
        """, (current_month.isoformat(),))
        monthly_revenue = cursor.fetchone()[0] or 0
        
        # 지난 달 수익 (비교용)
        last_month = (current_month - timedelta(days=1)).replace(day=1)
        cursor.execute("""
            SELECT COALESCE(SUM(price), 0) FROM reservations 
            WHERE created_at >= ? AND created_at < ? AND status != 'cancelled'
        """, (last_month.isoformat(), current_month.isoformat()))
        last_month_revenue = cursor.fetchone()[0] or 0
        
        # 성장률 계산
        def calculate_growth(current, previous):
            if previous == 0:
                return 100 if current > 0 else 0
            return round(((current - previous) / previous) * 100, 1)
        
        # 최근 예약 조회
        cursor.execute("""
            SELECT r.id, r.status, r.created_at, c.name as customer_name, s.title as schedule_title
            FROM reservations r
            JOIN customers c ON r.customer_id = c.id
            JOIN schedules s ON r.schedule_id = s.id
            ORDER BY r.created_at DESC
            LIMIT 5
        """)
        recent_reservations = []
        for row in cursor.fetchall():
            recent_reservations.append({
                'id': row[0],
                'status': row[1],
                'created_at': row[2],
                'customer_name': row[3],
                'schedule_title': row[4]
            })
        
        # 알림 생성
        notifications = [
            {
                'title': '시스템 업데이트',
                'message': 'Travel CRM v2.0이 성공적으로 업데이트되었습니다.',
                'time': '2시간 전',
                'icon': 'fas fa-info-circle',
                'icon_color': 'text-blue-600',
                'icon_bg': 'bg-blue-100'
            },
            {
                'title': '데이터베이스 백업',
                'message': '일일 데이터베이스 백업이 완료되었습니다.',
                'time': '1일 전',
                'icon': 'fas fa-check-circle',
                'icon_color': 'text-green-600',
                'icon_bg': 'bg-green-100'
            }
        ]
        
        # 예약 상태별 통계 추가
        if total_reservations > 0:
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM reservations
                GROUP BY status
            """)
            status_stats = dict(cursor.fetchall())
            
            # 대기중인 예약이 있으면 알림 추가
            if status_stats.get('pending', 0) > 0:
                notifications.insert(0, {
                    'title': '대기중인 예약',
                    'message': f'{status_stats["pending"]}개의 예약이 승인 대기 중입니다.',
                    'time': '방금 전',
                    'icon': 'fas fa-clock',
                    'icon_color': 'text-yellow-600',
                    'icon_bg': 'bg-yellow-100'
                })
        
        conn.close()
        
        return {
            'total_customers': total_customers,
            'total_schedules': total_schedules,
            'total_reservations': total_reservations,
            'monthly_revenue': monthly_revenue,
            'customer_growth': calculate_growth(total_customers, max(0, total_customers - 5)),  # 임시 데이터
            'schedule_growth': calculate_growth(total_schedules, max(0, total_schedules - 3)),  # 임시 데이터
            'reservation_growth': calculate_growth(monthly_reservations, max(0, monthly_reservations - 2)),  # 임시 데이터
            'revenue_growth': calculate_growth(monthly_revenue, last_month_revenue),
            'recent_reservations': recent_reservations,
            'notifications': notifications
        }
        
    except Exception as e:
        print(f"데이터베이스 통계 조회 오류: {e}")
        return {
            'total_customers': 0,
            'total_schedules': 0,
            'total_reservations': 0,
            'monthly_revenue': 0,
            'customer_growth': 0,
            'schedule_growth': 0,
            'reservation_growth': 0,
            'revenue_growth': 0,
            'recent_reservations': [],
            'notifications': [
                {
                    'title': '데이터베이스 오류',
                    'message': '통계 데이터를 불러오는 중 오류가 발생했습니다.',
                    'time': '방금 전',
                    'icon': 'fas fa-exclamation-triangle',
                    'icon_color': 'text-red-600',
                    'icon_bg': 'bg-red-100'
                }
            ]
        }

@dashboard_bp.route('/')
@jwt_required(current_app)
def dashboard():
    """메인 대시보드 페이지"""
    try:
        # 실제 데이터베이스에서 통계 데이터 조회
        stats = get_database_stats()
        
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        print(f'대시보드 로드 오류: {e}')
        # 오류 발생 시 기본 통계로 렌더링
        error_stats = {
            'total_customers': 0,
            'total_schedules': 0,
            'total_reservations': 0,
            'monthly_revenue': 0,
            'customer_growth': 0,
            'schedule_growth': 0,
            'reservation_growth': 0,
            'revenue_growth': 0,
            'recent_reservations': [],
            'notifications': [
                {
                    'title': '시스템 오류',
                    'message': '대시보드를 불러오는 중 오류가 발생했습니다.',
                    'time': '방금 전',
                    'icon': 'fas fa-exclamation-triangle',
                    'icon_color': 'text-red-600',
                    'icon_bg': 'bg-red-100'
                }
            ]
        }
        return render_template('dashboard.html', stats=error_stats, error='대시보드를 불러오는 중 오류가 발생했습니다.') 