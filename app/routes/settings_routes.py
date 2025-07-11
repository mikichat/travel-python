from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from database import get_db_connection
from datetime import datetime

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings_page():
    """설정 페이지를 렌더링하고 설정을 업데이트합니다."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        try:
            language = request.form.get('language')
            timezone = request.form.get('timezone')
            items_per_page = request.form.get('items_per_page', 25)
            
            # items_per_page를 int로 변환 시도
            try:
                items_per_page = int(items_per_page)
            except ValueError:
                flash('페이지당 항목 수는 유효한 숫자여야 합니다.', 'error')
                return redirect(url_for('settings.settings_page'))

            cursor.execute("""
                INSERT INTO user_settings (user_id, language, timezone, items_per_page, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    language = excluded.language,
                    timezone = excluded.timezone,
                    items_per_page = excluded.items_per_page,
                    updated_at = excluded.updated_at
            """, (current_user.id, language, timezone, items_per_page, datetime.now().isoformat(), datetime.now().isoformat()))
            
            conn.commit()
            flash('설정이 성공적으로 저장되었습니다.', 'success')
            
        except Exception as e:
            conn.rollback() # 오류 발생 시 롤백
            flash(f'설정 저장 중 오류가 발생했습니다: {e}', 'error')
            # 에러 로깅 (선택 사항)
            # app.logger.error(f"Error saving settings for user {current_user.id}: {e}")
        finally:
            conn.close()
        
        return redirect(url_for('settings.settings_page'))

    cursor.execute('SELECT * FROM user_settings WHERE user_id = ?', (current_user.id,))
    settings = cursor.fetchone()
    conn.close()

    if not settings:
        # 기본값 설정
        settings = {'language': 'ko', 'timezone': 'Asia/Seoul'}

    return render_template('settings.html', settings=settings)
