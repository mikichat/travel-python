"""
템플릿 필터 함수들
"""

def get_status_color(status):
    """예약 상태에 따른 색상 반환"""
    status_colors = {
        'REQUESTED': 'bg-blue-100 text-blue-800', # 예약 요청 - 고객상담
        'IN_PROGRESS': 'bg-indigo-100 text-indigo-800', # 진행 확인 - 담당자와 협의
        'PENDING_DEPOSIT': 'bg-yellow-100 text-yellow-800', # 대기 예약 - 입금 전
        'CONTRACT_CONFIRMED': 'bg-purple-100 text-purple-800', # 계약 확정 - 계약금만, 잔금 (미수)
        'FULLY_PAID': 'bg-green-100 text-green-800', # 완납 서비스 - 체크리스트
        'COMPLETED': 'bg-teal-100 text-teal-800', # 완료 도착
        'VIP_CUSTOMER': 'bg-pink-100 text-pink-800', # VIP 고객 - 재구매는 (V.V.IP 고객)
        'COMPLAINT': 'bg-red-100 text-red-800', # 불만
        'PROCESSED': 'bg-gray-100 text-gray-800', # 처리완료
    }
    return status_colors.get(status, 'bg-gray-100 text-gray-800')

def get_status_text(status):
    """예약 상태에 따른 텍스트 반환"""
    status_texts = {
        'REQUESTED': '예약 요청 - 고객상담',
        'IN_PROGRESS': '진행 확인 - 담당자와 협의',
        'PENDING_DEPOSIT': '대기 예약 - 입금 전',
        'CONTRACT_CONFIRMED': '계약 확정 - 계약금만, 잔금 (미수)',
        'FULLY_PAID': '완납 서비스 - 체크리스트',
        'COMPLETED': '완료 도착',
        'VIP_CUSTOMER': 'VIP 고객 - 재구매는 (V.V.IP 고객)',
        'COMPLAINT': '불만',
        'PROCESSED': '처리완료',
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

def register_filters(app):
    """모든 필터를 Flask 앱에 등록"""
    app.template_filter('get_status_color')(get_status_color)
    app.template_filter('get_status_text')(get_status_text)
    app.template_filter('format_currency')(format_currency)
    app.template_filter('format_date')(format_date)
    app.template_filter('format_datetime')(format_datetime) 