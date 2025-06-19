# Utils package 
from .errors import APIError, ValidationError, PermissionDenied
import random
import string
import datetime

def generate_reservation_code():
    """
    6자리 예약코드 생성 (예: Ab-XyZ)
    오늘 날짜의 년도 2자리+랜덤 대소문자2자+(주차수를 알파벳 대소문자에서 짝수주는대문자,홀수는소문자) 로써 예) 25Xza
    """
    now = datetime.datetime.now()
    year_two_digits = str(now.year)[-2:]

    random_chars = ''.join(random.choices(string.ascii_letters, k=2))

    week_number = now.isocalendar()[1]
    
    # 주차수를 알파벳으로 변환 (짝수 주차는 대문자, 홀수 주차는 소문자)
    char_code = (week_number - 1) % 26
    if week_number % 2 == 0:  # 짝수 주차, 대문자
        week_char = chr(ord('A') + char_code)
    else:  # 홀수 주차, 소문자
        week_char = chr(ord('a') + char_code)
        
    return f"{year_two_digits}{random_chars}{week_char}"

__all__ = [
    'APIError',
    'ValidationError',
    'PermissionDenied',
    'generate_reservation_code',
] 