"""
변경 로그 라우트
"""
from flask import Blueprint, render_template, request, current_app
from app.utils.auth import jwt_required
from app.utils.audit import get_audit_logs, get_audit_logs_count
from app.utils.filters import format_datetime

audit_bp = Blueprint('audit', __name__)

# 필터 등록
@audit_bp.app_template_filter('format_datetime')
def format_datetime_filter(datetime_str):
    return format_datetime(datetime_str)

@audit_bp.route('/')
@jwt_required(current_app)
def audit_logs_page():
    """변경 로그 페이지"""
    try:
        # 페이지네이션 파라미터
        page = request.args.get('page', 1, type=int)
        per_page = 50
        offset = (page - 1) * per_page
        
        # 필터 파라미터
        table_name = request.args.get('table_name', '').strip()
        action = request.args.get('action', '').strip()
        
        # 변경 로그 조회
        logs = get_audit_logs(limit=per_page, offset=offset, table_name=table_name if table_name else None)
        total_count = get_audit_logs_count(table_name=table_name if table_name else None)
        
        # 페이지네이션 계산
        total_pages = (total_count + per_page - 1) // per_page
        
        return render_template('audit_logs.html', 
                             logs=logs,
                             total_count=total_count,
                             current_page=page,
                             total_pages=total_pages,
                             per_page=per_page,
                             table_name=table_name,
                             action=action)
    except Exception as e:
        print(f'변경 로그 조회 오류: {e}')
        return render_template('audit_logs.html', error='변경 로그를 불러오는 중 오류가 발생했습니다.')

@audit_bp.route('/api/logs')
@jwt_required(current_app)
def get_audit_logs_api():
    """변경 로그 API"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        offset = (page - 1) * per_page
        
        table_name = request.args.get('table_name', '').strip()
        action = request.args.get('action', '').strip()
        
        logs = get_audit_logs(limit=per_page, offset=offset, table_name=table_name if table_name else None)
        total_count = get_audit_logs_count(table_name=table_name if table_name else None)
        
        return {
            'logs': logs,
            'total_count': total_count,
            'current_page': page,
            'total_pages': (total_count + per_page - 1) // per_page
        }
    except Exception as e:
        print(f'변경 로그 API 오류: {e}')
        return {'error': '변경 로그를 불러오는 중 오류가 발생했습니다.'}, 500 