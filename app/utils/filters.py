"""
템플릿 필터 함수들
"""

def get_status_color(status):
    """예약 상태에 따른 색상 반환"""
    status_colors = {
        'pending': 'bg-yellow-100 text-yellow-800',
        'confirmed': 'bg-green-100 text-green-800',
        'cancelled': 'bg-red-100 text-red-800',
        'completed': 'bg-blue-100 text-blue-800'
    }
    return status_colors.get(status, 'bg-gray-100 text-gray-800')

def get_status_text(status):
    """예약 상태에 따른 텍스트 반환"""
    status_texts = {
        'pending': '대기중',
        'confirmed': '확정',
        'cancelled': '취소',
        'completed': '완료'
    }
    return status_texts.get(status, status)

def format_currency(amount):
    """통화 형식으로 포맷팅"""
    if amount is None:
        return "₩0"
    return f"₩{amount:,}"

def format_date(date_str):
    """날짜 형식으로 포맷팅"""
    if not date_str:
        return ""
    try:
        from datetime import datetime
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date_obj.strftime('%Y-%m-%d')
    except:
        return date_str

def format_datetime(datetime_str):
    """날짜시간 형식으로 포맷팅"""
    if not datetime_str:
        return ""
    try:
        from datetime import datetime
        date_obj = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        return date_obj.strftime('%Y-%m-%d %H:%M')
    except:
        return datetime_str 