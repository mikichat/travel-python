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
        per_page = request.args.get('per_page', 10, type=int) # 페이지당 항목 수, 기본값 30
        offset = (page - 1) * per_page
        limit = per_page
        
        table_name = request.args.get('table_name', '')
        record_id = request.args.get('record_id', type=int)
        search_term = request.args.get('search_term', '').strip()

        logs = get_audit_logs(limit=limit, offset=offset, table_name=table_name, record_id=record_id, search_term=search_term)
        total_count = get_audit_logs_count(table_name=table_name, record_id=record_id, search_term=search_term)
        
        total_pages = (total_count + per_page - 1) // per_page
        
        return render_template('audit_logs.html', 
                             logs=logs, 
                             total_audit_logs_count=total_count,
                             table_name=table_name,
                             record_id=record_id,
                             search_term=search_term,
                             page=page,
                             per_page=per_page,
                             total_pages=total_pages)
    except Exception as e:
        print(f'변경 로그 조회 오류: {e}')
        # 오류 발생 시에도 템플릿에 필요한 모든 변수를 전달
        return render_template('audit_logs.html', 
                             logs=[], 
                             total_audit_logs_count=0,
                             table_name=table_name,
                             record_id=record_id,
                             search_term=search_term,
                             page=request.args.get('page', 1, type=int), # 현재 페이지 값을 유지하거나 기본값 1
                             per_page=request.args.get('per_page', 30, type=int), # 현재 페이지당 항목 수를 유지하거나 기본값 30
                             total_pages=0, # 오류 발생 시 총 페이지 수는 0으로 설정
                             error='변경 로그 조회 중 오류가 발생했습니다.')

@audit_bp.route('/api/logs/paginated')
@jwt_required(current_app)
def get_paginated_audit_logs_api():
    """페이지네이션 및 검색을 지원하는 변경 로그 API"""
    try:
        offset = request.args.get('offset', type=int, default=0)
        limit = request.args.get('limit', type=int, default=10)
        
        table_name = request.args.get('table_name', '')
        record_id = request.args.get('record_id', type=int)
        search_term = request.args.get('search_term', '').strip()

        logs = get_audit_logs(limit=limit, offset=offset, table_name=table_name, record_id=record_id, search_term=search_term)
        total_count = get_audit_logs_count(table_name=table_name, record_id=record_id, search_term=search_term)
        
        return jsonify({
            'logs': logs,
            'total_count': total_count,
            'offset': offset,
            'limit': limit
        })
    except Exception as e:
        print(f'변경 로그 API 오류: {e}')
        raise APIError('변경 로그 조회 중 오류가 발생했습니다.', 500) 