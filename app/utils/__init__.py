# Utils package 
from .errors import APIError, ValidationError, PermissionDenied
import random
import string

def generate_reservation_code():
    """
    6자리 예약코드 생성 (예: Ab-XyZ)
    """
    chars = string.ascii_letters
    part1 = ''.join(random.choices(chars, k=2))
    part2 = ''.join(random.choices(chars, k=3))
    return f"{part1}-{part2}"

__all__ = [
    'APIError',
    'ValidationError',
    'PermissionDenied',
    'generate_reservation_code',
] 