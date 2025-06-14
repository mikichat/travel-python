"""
변경 로그 조회 라우트
"""
from flask import Blueprint, render_template, request, jsonify, current_app
from app.utils.auth import jwt_required
from app.utils.audit import get_audit_logs, get_audit_logs_count
from app.utils.errors import APIError

audit_bp = Blueprint('audit', __name__, url_prefix='/audit')

@audit_bp.route('/')
@jwt_required(current_app)
def audit_logs_page():
    """변경 로그 페이지"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = 50
        offset = (page - 1) * limit
        
        table_name = request.args.get('table_name')
        record_id = request.args.get('record_id', type=int)
        
        logs = get_audit_logs(limit=limit, offset=offset, table_name=table_name, record_id=record_id)
        total_count = get_audit_logs_count(table_name=table_name, record_id=record_id)
        
        total_pages = (total_count + limit - 1) // limit
        
        return render_template('audit_logs.html', 
                             logs=logs, 
                             current_page=page, 
                             total_pages=total_pages,
                             table_name=table_name,
                             record_id=record_id)
    except Exception as e:
        print(f'변경 로그 조회 오류: {e}')
        return render_template('audit_logs.html', 
                             logs=[], 
                             current_page=1, 
                             total_pages=1,
                             table_name=None,
                             record_id=None,
                             error='변경 로그 조회 중 오류가 발생했습니다.')

@audit_bp.route('/api/logs')
@jwt_required(current_app)
def get_audit_logs_api():
    """변경 로그 API"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        offset = (page - 1) * limit
        
        table_name = request.args.get('table_name')
        record_id = request.args.get('record_id', type=int)
        
        logs = get_audit_logs(limit=limit, offset=offset, table_name=table_name, record_id=record_id)
        total_count = get_audit_logs_count(table_name=table_name, record_id=record_id)
        
        return jsonify({
            'logs': logs,
            'total_count': total_count,
            'current_page': page,
            'total_pages': (total_count + limit - 1) // limit
        })
    except Exception as e:
        print(f'변경 로그 API 오류: {e}')
        raise APIError('변경 로그 조회 중 오류가 발생했습니다.', 500) 