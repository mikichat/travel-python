from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, jsonify
from app.models.ticketing_model import Ticketing
from app.utils.auth import jwt_required
from datetime import datetime
import os
import hashlib
import uuid

ticketing_bp = Blueprint('ticketing', __name__)

# 발권 목록 페이지
@ticketing_bp.route('/')
@jwt_required(current_app)
def ticketing_page():
    airline_type = request.args.get('airline_type', '')
    flight_type = request.args.get('flight_type', '')
    ticketing_status = request.args.get('ticketing_status', '')
    ticket_code = request.args.get('ticket_code', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    offset = (page - 1) * per_page

    ticketing_entries, total_count = Ticketing.search(
        airline_type=airline_type,
        flight_type=flight_type,
        ticketing_status=ticketing_status,
        ticket_code=ticket_code,
        offset=offset,
        limit=per_page,
        include_total_count=True,
        include_deleted=False
    )
    
    total_pages = (total_count + per_page - 1) // per_page
    if page < 1: page = 1
    if page > total_pages and total_pages > 0: page = total_pages

    return render_template('ticketing.html', 
                           ticketing_entries=ticketing_entries,
                           total_ticketing_count=total_count,
                           airline_type=airline_type,
                           flight_type=flight_type,
                           ticketing_status=ticketing_status,
                           ticket_code=ticket_code,
                           page=page,
                           per_page=per_page,
                           total_pages=total_pages)

@ticketing_bp.route('/api/ticketing/paginated', methods=['GET'])
@jwt_required(current_app)
def get_paginated_ticketing_api():
    try:
        offset = request.args.get('offset', type=int, default=0)
        limit = request.args.get('limit', type=int, default=10)
        airline_type = request.args.get('airline_type', '')
        flight_type = request.args.get('flight_type', '')
        ticketing_status = request.args.get('ticketing_status', '')
        ticket_code = request.args.get('ticket_code', '')

        ticketing_entries, total_count = Ticketing.search(
            airline_type=airline_type,
            flight_type=flight_type,
            ticketing_status=ticketing_status,
            ticket_code=ticket_code,
            offset=offset,
            limit=limit,
            include_total_count=True,
            include_deleted=False
        )

        # API 응답을 위해 객체를 딕셔너리로 변환
        entries_list = []
        for entry in ticketing_entries:
            entries_list.append({
                'id': entry.id,
                'airlineType': entry.airline_type,
                'flightType': entry.flight_type,
                'ticketingStatus': entry.ticketing_status,
                'ticketCode': entry.ticket_code,
                'passportAttachmentPaths': entry.passport_attachment_paths,
                'memo': entry.memo,
                'createdAt': entry.created_at,
                'updatedAt': entry.updated_at
            })
        return jsonify(entries_list=entries_list, total_count=total_count)
    except Exception as e:
        print(f'발권 페이지네이션 API 조회 실패: {e}')
        return jsonify({'error': '발권 목록을 불러오는 중 오류가 발생했습니다.'}), 500

# 발권 추가 페이지 (GET)
@ticketing_bp.route('/create', methods=['GET', 'POST'])
@jwt_required(current_app)
def create_ticketing():
    if request.method == 'POST':
        airline_type = request.form['airline_type']
        flight_type = request.form['flight_type']
        ticketing_status = request.form['ticketing_status']
        ticket_code = request.form['ticket_code']
        memo = request.form.get('memo', '')
        
        uploaded_passport_paths = []
        private_upload_folder = os.path.join(current_app.root_path, 'data', 'private_uploads')
        os.makedirs(private_upload_folder, exist_ok=True)

        for passport_file in request.files.getlist('passport_attachment'):
            if passport_file.filename != '':
                file_extension = os.path.splitext(passport_file.filename)[1]
                hashed_filename = hashlib.sha256(uuid.uuid4().bytes).hexdigest() + file_extension
                full_file_path = os.path.join(private_upload_folder, hashed_filename)
                passport_file.save(full_file_path)
                uploaded_passport_paths.append(hashed_filename)

        new_ticketing = Ticketing(id=None, airline_type=airline_type, flight_type=flight_type, 
                                  ticketing_status=ticketing_status, ticket_code=ticket_code,
                                  passport_attachment_path=','.join(uploaded_passport_paths), memo=memo,
                                  created_at=datetime.now().isoformat(), updated_at=datetime.now().isoformat())
        new_ticketing.save()
        flash('발권 정보가 성공적으로 추가되었습니다!', 'success')
        return redirect(url_for('ticketing.ticketing_page'))
    
    return render_template('create_ticketing.html')

# 발권 편집 페이지 (GET, POST)
@ticketing_bp.route('/edit/<int:ticketing_id>', methods=['GET', 'POST'])
@jwt_required(current_app)
def edit_ticketing(ticketing_id):
    ticketing = Ticketing.get_by_id(ticketing_id)
    if not ticketing:
        flash('발권 정보를 찾을 수 없습니다.', 'error')
        return redirect(url_for('ticketing.ticketing_page'))

    if ticketing.deleted_at is not None:
        flash('이미 삭제된 발권 정보입니다. 복원 후 수정해주세요.', 'error')
        return redirect(url_for('ticketing.ticketing_page'))

    if request.method == 'POST':
        ticketing.airline_type = request.form['airline_type']
        ticketing.flight_type = request.form['flight_type']
        ticketing.ticketing_status = request.form['ticketing_status']
        ticketing.ticket_code = request.form['ticket_code']
        ticketing.memo = request.form.get('memo', '')
        ticketing.updated_at = datetime.now().isoformat()

        private_upload_folder = os.path.join(current_app.root_path, 'data', 'private_uploads')
        os.makedirs(private_upload_folder, exist_ok=True)

        current_passport_paths = ticketing.passport_attachment_paths[:] # 현재 파일 목록 복사
        files_to_remove = request.form.getlist('remove_passport_attachment[]')

        # 삭제할 파일 처리
        for filename_to_remove in files_to_remove:
            if filename_to_remove in current_passport_paths:
                full_path_to_remove = os.path.join(private_upload_folder, filename_to_remove)
                if os.path.exists(full_path_to_remove):
                    os.remove(full_path_to_remove)
                current_passport_paths.remove(filename_to_remove)
        
        # 새 파일 업로드 처리
        for passport_file in request.files.getlist('passport_attachment'):
            if passport_file.filename != '':
                file_extension = os.path.splitext(passport_file.filename)[1]
                hashed_filename = hashlib.sha256(uuid.uuid4().bytes).hexdigest() + file_extension
                full_file_path = os.path.join(private_upload_folder, hashed_filename)
                passport_file.save(full_file_path)
                current_passport_paths.append(hashed_filename)

        ticketing.passport_attachment_paths = current_passport_paths # 업데이트된 경로 리스트 할당

        ticketing.save()
        flash('발권 정보가 성공적으로 업데이트되었습니다!', 'success')
        return redirect(url_for('ticketing.ticketing_page'))

    return render_template('edit_ticketing.html', ticketing=ticketing)

# 발권 삭제 (POST)
@ticketing_bp.route('/delete/<int:ticketing_id>', methods=['POST'])
@jwt_required(current_app)
def delete_ticketing(ticketing_id):
    files_to_delete = Ticketing.soft_delete(ticketing_id)
    
    private_upload_folder = os.path.join(current_app.root_path, 'data', 'private_uploads')
    for filename in files_to_delete:
        full_path = os.path.join(private_upload_folder, filename)
        if os.path.exists(full_path):
            os.remove(full_path)

    flash('발권 정보가 성공적으로 삭제되었습니다.', 'success')
    return redirect(url_for('ticketing.ticketing_page'))

@ticketing_bp.route('/restore/<int:ticketing_id>', methods=['POST'])
@jwt_required(current_app)
def restore_ticketing(ticketing_id):
    try:
        # 복원할 발권 정보가 존재하는지 확인 (논리적으로 삭제된 항목만)
        ticketing = Ticketing.get_by_id(ticketing_id, include_deleted=True)
        if not ticketing or ticketing.deleted_at is None:
            flash('발권 정보를 찾을 수 없거나 이미 활성 상태입니다.', 'error')
            return redirect(url_for('ticketing.ticketing_page'))

        # 발권 정보 복원
        Ticketing.restore(ticketing_id)

        # 감사 로그 기록
        # log_ticketing_change(ticketing_id, 'RESTORE', 'deleted_at', ticketing.deleted_at, None, 'admin')
        # 위 코드는 log_ticketing_change 함수에 맞게 수정 필요. 현재는 log_change 직접 호출.
        from app.utils.audit import log_ticketing_change
        log_ticketing_change(ticketing_id, 'RESTORE', 'deleted_at', ticketing.deleted_at, None, 'admin')

        flash('발권 정보가 성공적으로 복원되었습니다.', 'success')
        return redirect(url_for('ticketing.ticketing_page'))
    except Exception as e:
        print(f'발권 복원 오류: {e}')
        flash('발권 복원 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('ticketing.ticketing_page'))

# 안전한 여권 이미지 뷰어 라우트
@ticketing_bp.route('/passport/<int:ticketing_id>/<string:filename>')
@jwt_required(current_app)
def view_passport(ticketing_id, filename):
    ticketing = Ticketing.get_by_id(ticketing_id)
    if not ticketing or filename not in ticketing.passport_attachment_paths or ticketing.deleted_at is not None:
        flash('여권 이미지를 찾을 수 없거나 접근 권한이 없습니다.', 'danger')
        return redirect(url_for('ticketing.ticketing_page'))

    private_upload_folder = os.path.join(current_app.root_path, 'data', 'private_uploads')
    
    # 보안을 위해 파일 이름 유효성 검사 (폴더 구조 변경 시 필요)
    # os.path.basename을 사용하여 경로 조작을 방지
    safe_filename = os.path.basename(filename) # 이미 해시된 파일명이므로, 추가적인 보안 검사는 DB 조회로 충분
    
    return send_from_directory(private_upload_folder, safe_filename) 