from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app.models.company_model import Company
from app.utils.auth import jwt_required
from app.utils.errors import APIError
from app.utils import ValidationError
from datetime import datetime

company_bp = Blueprint('company', __name__)

@company_bp.route('/')
@jwt_required(current_app)
def companies_page():
    companies = Company.get_all()
    return render_template('companies.html', companies=companies)

@company_bp.route('/create', methods=['GET', 'POST'])
@jwt_required(current_app)
def create_company_page():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        notes = request.form.get('notes', '').strip()
        items = request.form.getlist('items')
        if not name:
            flash('회사명은 필수입니다.', 'error')
            return render_template('create_company.html')
        company = Company(None, name, phone, email, address, notes, items, None, None)
        company.save()
        flash('업체가 성공적으로 등록되었습니다.', 'success')
        return redirect(url_for('company.companies_page'))
    return render_template('create_company.html')

@company_bp.route('/edit/<int:company_id>', methods=['GET', 'POST'])
@jwt_required(current_app)
def edit_company_page(company_id):
    company = Company.get_by_id(company_id)
    if not company:
        flash('업체를 찾을 수 없습니다.', 'error')
        return redirect(url_for('company.companies_page'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        notes = request.form.get('notes', '').strip()
        items = request.form.getlist('items')
        if not name:
            flash('회사명은 필수입니다.', 'error')
            return render_template('edit_company.html', company=company)
        company.name = name
        company.phone = phone
        company.email = email
        company.address = address
        company.notes = notes
        company.items = items
        company.save()
        flash('업체 정보가 수정되었습니다.', 'success')
        return redirect(url_for('company.companies_page'))
    return render_template('edit_company.html', company=company)

@company_bp.route('/delete/<int:company_id>', methods=['POST'])
@jwt_required(current_app)
def delete_company_page(company_id):
    company = Company.get_by_id(company_id)
    if not company:
        flash('업체를 찾을 수 없습니다.', 'error')
        return redirect(url_for('company.companies_page'))
    Company.soft_delete(company_id)
    flash('업체가 삭제되었습니다.', 'success')
    return redirect(url_for('company.companies_page')) 