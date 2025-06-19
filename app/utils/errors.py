from flask import jsonify, render_template, flash, redirect, url_for, request
import logging

class APIError(Exception):
    """API 오류를 위한 사용자 정의 예외 클래스"""
    def __init__(self, message, status_code=500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class ValidationError(Exception):
    """입력값 검증 오류"""
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class PermissionDenied(Exception):
    """권한 부족 오류"""
    def __init__(self, message="권한이 없습니다.", status_code=403):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

def register_error_handlers(app):
    """Flask 애플리케이션에 오류 핸들러를 등록합니다."""
    logger = logging.getLogger(__name__)

    @app.errorhandler(APIError)
    def handle_api_error(error):
        logger.error(f"APIError: {error.message}")
        flash(error.message, 'error')
        return render_template('errors/api_error.html', error=error), error.status_code

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        logger.warning(f"ValidationError: {error.message}")
        flash(error.message, 'error')
        return render_template('errors/validation_error.html', error=error), error.status_code

    @app.errorhandler(PermissionDenied)
    def handle_permission_denied(error):
        logger.warning(f"PermissionDenied: {error.message}")
        flash(error.message, 'error')
        return render_template('errors/permission_denied.html', error=error), error.status_code

    @app.errorhandler(404)
    def not_found_error(error):
        logger.info(f"404 Not Found: {request.path}")
        flash("요청한 페이지를 찾을 수 없습니다.", 'error')
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"500 Internal Server Error: {error}")
        flash("서버 내부 오류가 발생했습니다.", 'error')
        return render_template('errors/500.html'), 500

    @app.errorhandler(400)
    def bad_request_error(error):
        logger.warning(f"400 Bad Request: {error}")
        flash("잘못된 요청입니다.", 'error')
        return render_template('errors/400.html'), 400 