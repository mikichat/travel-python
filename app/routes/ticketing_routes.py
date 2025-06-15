from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app.models.ticketing_model import Ticketing
from app.utils.auth import jwt_required
from datetime import datetime
import os

ticketing_bp = Blueprint('ticketing', __name__)

# 발권 목록 페이지
@ticketing_bp.route('/')
@jwt_required(current_app)
def ticketing_page():
    ticketing_entries = Ticketing.get_all()
    return render_template('ticketing.html', ticketing_entries=ticketing_entries)

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
                # 파일 저장 로직 (예: static/uploads 폴더)
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                filename = f"passport_{datetime.now().strftime('%Y%m%d%H%M%S')}_{passport_file.filename}"
                passport_attachment_path = os.path.join(upload_folder, filename)
                passport_file.save(passport_attachment_path)
                # 데이터베이스에는 상대 경로 또는 URL 저장
                passport_attachment_path = os.path.join('static', 'uploads', filename)

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
                # 기존 파일 삭제 (선택 사항)
                if ticketing.passport_attachment_path and os.path.exists(os.path.join(current_app.root_path, ticketing.passport_attachment_path)):
                    os.remove(os.path.join(current_app.root_path, ticketing.passport_attachment_path))
                
                # 새 파일 저장 로직
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                filename = f"passport_{datetime.now().strftime('%Y%m%d%H%M%S')}_{passport_file.filename}"
                passport_attachment_path = os.path.join(upload_folder, filename)
                passport_file.save(passport_attachment_path)
                ticketing.passport_attachment_path = os.path.join('static', 'uploads', filename)
            elif request.form.get('clear_passport_attachment') == '1':
                # 파일 지우기 요청이 있었고 기존 파일이 있다면 삭제
                if ticketing.passport_attachment_path and os.path.exists(os.path.join(current_app.root_path, ticketing.passport_attachment_path)):
                    os.remove(os.path.join(current_app.root_path, ticketing.passport_attachment_path))
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
        if ticketing.passport_attachment_path and os.path.exists(os.path.join(current_app.root_path, ticketing.passport_attachment_path)):
            os.remove(os.path.join(current_app.root_path, ticketing.passport_attachment_path))
        Ticketing.delete(ticketing_id)
        flash('발권 정보가 성공적으로 삭제되었습니다.', 'success')
    return redirect(url_for('ticketing.ticketing_page')) 