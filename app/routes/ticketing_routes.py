from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
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
    airline_type = request.args.get('airline_type')
    flight_type = request.args.get('flight_type')
    ticketing_status = request.args.get('ticketing_status')
    ticket_code = request.args.get('ticket_code')

    ticketing_entries = Ticketing.search(airline_type, flight_type, ticketing_status, ticket_code)
    
    return render_template('ticketing.html', 
                           ticketing_entries=ticketing_entries,
                           airline_type=airline_type,
                           flight_type=flight_type,
                           ticketing_status=ticketing_status,
                           ticket_code=ticket_code)

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
        
        passport_attachment_path = None
        if 'passport_attachment' in request.files:
            passport_file = request.files['passport_attachment']
            if passport_file.filename != '':
                # 파일 저장 로직: 'data/private_uploads' 폴더에 저장
                private_upload_folder = os.path.join(current_app.root_path, 'data', 'private_uploads')
                os.makedirs(private_upload_folder, exist_ok=True)
                
                # 파일명 해시화
                file_extension = os.path.splitext(passport_file.filename)[1]
                hashed_filename = hashlib.sha256(uuid.uuid4().bytes).hexdigest() + file_extension
                
                full_file_path = os.path.join(private_upload_folder, hashed_filename)
                passport_file.save(full_file_path)
                
                # 데이터베이스에는 해시된 파일명만 저장
                passport_attachment_path = hashed_filename

        new_ticketing = Ticketing(id=None, airline_type=airline_type, flight_type=flight_type, 
                                  ticketing_status=ticketing_status, ticket_code=ticket_code,
                                  passport_attachment_path=passport_attachment_path, memo=memo,
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
        flash('발권 정보를 찾을 수 없습니다.', 'danger')
        return redirect(url_for('ticketing.ticketing_page'))

    if request.method == 'POST':
        ticketing.airline_type = request.form['airline_type']
        ticketing.flight_type = request.form['flight_type']
        ticketing.ticketing_status = request.form['ticketing_status']
        ticketing.ticket_code = request.form['ticket_code']
        ticketing.memo = request.form.get('memo', '')
        ticketing.updated_at = datetime.now().isoformat()

        if 'passport_attachment' in request.files:
            passport_file = request.files['passport_attachment']
            if passport_file.filename != '':
                private_upload_folder = os.path.join(current_app.root_path, 'data', 'private_uploads')
                os.makedirs(private_upload_folder, exist_ok=True)

                # 기존 파일 삭제
                if ticketing.passport_attachment_path and \
                   os.path.exists(os.path.join(private_upload_folder, ticketing.passport_attachment_path)):
                    os.remove(os.path.join(private_upload_folder, ticketing.passport_attachment_path))
                
                # 새 파일 저장 로직 (파일명 해시화)
                file_extension = os.path.splitext(passport_file.filename)[1]
                hashed_filename = hashlib.sha256(uuid.uuid4().bytes).hexdigest() + file_extension
                full_file_path = os.path.join(private_upload_folder, hashed_filename)
                passport_file.save(full_file_path)
                ticketing.passport_attachment_path = hashed_filename
            elif request.form.get('clear_passport_attachment') == '1':
                # 파일 지우기 요청이 있었고 기존 파일이 있다면 삭제
                private_upload_folder = os.path.join(current_app.root_path, 'data', 'private_uploads')
                if ticketing.passport_attachment_path and \
                   os.path.exists(os.path.join(private_upload_folder, ticketing.passport_attachment_path)):
                    os.remove(os.path.join(private_upload_folder, ticketing.passport_attachment_path))
                ticketing.passport_attachment_path = None

        ticketing.save()
        flash('발권 정보가 성공적으로 업데이트되었습니다!', 'success')
        return redirect(url_for('ticketing.ticketing_page'))

    return render_template('edit_ticketing.html', ticketing=ticketing)

# 발권 삭제 (POST)
@ticketing_bp.route('/delete/<int:ticketing_id>', methods=['POST'])
@jwt_required(current_app)
def delete_ticketing(ticketing_id):
    ticketing = Ticketing.get_by_id(ticketing_id)
    if not ticketing:
        flash('발권 정보를 찾을 수 없습니다.', 'danger')
    else:
        # 파일이 있다면 삭제
        private_upload_folder = os.path.join(current_app.root_path, 'data', 'private_uploads')
        if ticketing.passport_attachment_path and \
           os.path.exists(os.path.join(private_upload_folder, ticketing.passport_attachment_path)):
            os.remove(os.path.join(private_upload_folder, ticketing.passport_attachment_path))
        Ticketing.delete(ticketing_id)
        flash('발권 정보가 성공적으로 삭제되었습니다.', 'success')
    return redirect(url_for('ticketing.ticketing_page'))

# 안전한 여권 이미지 뷰어 라우트
@ticketing_bp.route('/passport/<int:ticketing_id>')
@jwt_required(current_app)
def view_passport(ticketing_id):
    ticketing = Ticketing.get_by_id(ticketing_id)
    if not ticketing or not ticketing.passport_attachment_path:
        flash('여권 이미지를 찾을 수 없습니다.', 'danger')
        return redirect(url_for('ticketing.ticketing_page'))

    private_upload_folder = os.path.join(current_app.root_path, 'data', 'private_uploads')
    
    # 보안을 위해 파일 이름 유효성 검사 (폴더 구조 변경 시 필요)
    # os.path.basename을 사용하여 경로 조작을 방지
    filename = os.path.basename(ticketing.passport_attachment_path)
    
    return send_from_directory(private_upload_folder, filename) 