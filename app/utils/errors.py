from flask import jsonify

class APIError(Exception):
    """API 오류를 위한 사용자 정의 예외 클래스"""
    def __init__(self, message, status_code=500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

def register_error_handlers(app):
    """Flask 애플리케이션에 오류 핸들러를 등록합니다."""
    
    @app.errorhandler(APIError)
    def handle_api_error(error):
        """APIError 예외를 처리합니다."""
        response = jsonify({"success": False, "error": error.message})
        response.status_code = error.status_code
        return response
    
    @app.errorhandler(404)
    def not_found_error(error):
        """404 오류를 처리합니다."""
        return jsonify({"success": False, "error": "요청한 리소스를 찾을 수 없습니다."}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """500 오류를 처리합니다."""
        return jsonify({"success": False, "error": "서버 내부 오류가 발생했습니다."}), 500
    
    @app.errorhandler(400)
    def bad_request_error(error):
        """400 오류를 처리합니다."""
        return jsonify({"success": False, "error": "잘못된 요청입니다."}), 400 