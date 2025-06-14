from functools import wraps
from flask import request, jsonify, session, redirect, url_for, current_app
import jwt
from app.utils.errors import APIError

def jwt_required(app):
    """JWT 인증이 필요한 라우트를 위한 데코레이터 팩토리"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 웹 페이지 요청인 경우 Flask 세션을 먼저 확인
            if not request.path.startswith('/api/') and session.get('logged_in'):
                request.user_id = session.get('user_id')
                return f(*args, **kwargs)

            # API 호출이거나 Flask 세션에 로그인 정보가 없는 경우 JWT 확인
            auth_header = request.headers.get('Authorization')

            if not auth_header or not auth_header.startswith('Bearer '):
                if request.path.startswith('/api/') or request.path.startswith('/auth/'):
                    raise APIError('인증 토큰이 필요합니다.', 401)
                else:
                    session.pop('logged_in', None)
                    session.pop('user_id', None)
                    session.pop('username', None)
                    return redirect(url_for('auth.login_page', error='세션이 만료되었거나 인증 토큰이 없습니다. 다시 로그인해주세요.'))

            token = auth_header.split(' ')[1]

            try:
                decoded_token = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                request.user_id = decoded_token['userId']
            except jwt.ExpiredSignatureError:
                if request.path.startswith('/api/'):
                    raise APIError('인증 토큰이 만료되었습니다.', 401)
                else:
                    session.pop('logged_in', None)
                    session.pop('user_id', None)
                    session.pop('username', None)
                    return redirect(url_for('auth.login_page', error='세션이 만료되었습니다. 다시 로그인해주세요.'))
            except jwt.InvalidTokenError:
                if request.path.startswith('/api/'):
                    raise APIError('유효하지 않은 인증 토큰입니다.', 401)
                else:
                    session.pop('logged_in', None)
                    session.pop('user_id', None)
                    session.pop('username', None)
                    return redirect(url_for('auth.login_page', error='유효하지 않은 세션입니다. 다시 로그인해주세요.'))
            except Exception as e:
                print(f'JWT 인증 오류: {e}')
                if request.path.startswith('/api/'):
                    raise APIError('인증 확인 중 오류가 발생했습니다.', 500)
                else:
                    session.pop('logged_in', None)
                    session.pop('user_id', None)
                    session.pop('username', None)
                    return redirect(url_for('auth.login_page', error='인증 확인 중 오류가 발생했습니다.'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator 