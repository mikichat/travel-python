import pytesseract
from PIL import Image
import re
import os
from datetime import datetime

# Tesseract 설치 경로를 지정해야 할 수도 있습니다.
# 예를 들어, Windows의 경우:
# pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
# 또는 macOS/Linux에서 brew로 설치한 경우:
# pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'


def extract_text_from_image(image_path):
    """
    이미지 파일에서 텍스트를 추출합니다.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='eng') # 영어로 OCR 수행
        return text
    except Exception as e:
        print(f"OCR 처리 중 오류 발생: {e}")
        return None

def extract_passport_info(text):
    """
    OCR로 추출된 텍스트에서 여권 정보를 추출합니다.
    """
    if not text:
        return {}

    info = {
        "passport_number": None,
        "last_name_eng": None,
        "first_name_eng": None,
        "expiry_date": None
    }

    # 여권 번호 (Passport No.) - 2자리 문자 + 7자리 숫자 (또는 다른 패턴)
    # 예: M1234567, P1234567
    passport_number_patterns = [
        re.compile(r'\b[A-Z]{1}[0-9]{8}\b'), # 1문자 8숫자 (새로운 여권)
        re.compile(r'\b[A-Z0-9<]{9}[0-9]{1}[A-Z]{3}[0-9]{7}[A-Z]{1}[0-9]{7}[A-Z0-9<]{15}[0-9]{2}\b') # MRZ line 2 (partial check)
    ]
    for pattern in passport_number_patterns:
        match = pattern.search(text)
        if match:
            # MRZ 라인에서 추출하는 경우 여권번호는 시작부터 9번째 문자까지
            if len(match.group(0)) > 9: # Likely MRZ line
                info["passport_number"] = match.group(0)[0:9].replace('<', '')
            else:
                info["passport_number"] = match.group(0)
            break

    # 영문 성 (Surname/Last Name)
    # "Surname", "Last Name", "Family Name" 뒤에 오는 대문자 문자열
    # MRZ (Machine Readable Zone)에서 추출: 이름<<성
    last_name_patterns = [
        re.compile(r'(?:Surname|Last Name|Family Name)\s*[:]*\s*([A-Z\s]+)'),
        re.compile(r'P<([A-Z<]+)<<([A-Z<]+)'), # MRZ line 1, Passport Type<Surname<<Firstname
        re.compile(r'([A-Z<]+)<<([A-Z<]+)') # General format, may need refinement
    ]
    for pattern in last_name_patterns:
        match = pattern.search(text)
        if match:
            if pattern.pattern.startswith('P<'): # MRZ line 1
                info["last_name_eng"] = match.group(2).replace('<', ' ').strip()
            else:
                info["last_name_eng"] = match.group(1).replace('<', ' ').strip()
            break

    # 영문 이름 (Given Names/First Name)
    # "Given Names", "First Name" 뒤에 오는 대문자 문자열
    first_name_patterns = [
        re.compile(r'(?:Given Names|First Name)\s*[:]*\s*([A-Z\s]+)'),
        re.compile(r'P<([A-Z<]+)<<([A-Z<]+)<<([A-Z<]+)') # MRZ line 1, Passport Type<Surname<<Firstname
    ]
    for pattern in first_name_patterns:
        match = pattern.search(text)
        if match:
            if pattern.pattern.startswith('P<'): # MRZ line 1
                info["first_name_eng"] = match.group(1).replace('<', ' ').strip()
            else:
                info["first_name_eng"] = match.group(1).replace('<', ' ').strip()
            break
            
    # 여권 만료일 (Date of Expiry/Expiry Date) - YYMMDD 형식 또는 DD MMM YYYY 형식
    # MRZ: YYMMDD
    expiry_date_patterns = [
        re.compile(r'(?:Date of Expiry|Expiry Date|Exp)\s*[:]*\s*(\d{2}\s*[A-Z]{3}\s*\d{4})'), # DD MMM YYYY
        re.compile(r'(\d{6})[MF<]') # MRZ line 2 (YYMMDD followed by gender)
    ]
    for pattern in expiry_date_patterns:
        match = pattern.search(text)
        if match:
            date_str = match.group(1)
            if re.match(r'\d{6}', date_str): # YYMMDD format from MRZ
                year = int(date_str[0:2])
                # 2000년 이전 출생자는 20YY, 이후 출생자는 19YY로 간주 (대략적인 추정)
                # 실제 여권은 만료일이 10년 단위로 찍히므로 YY+2000을 주로 사용.
                year = 2000 + year if year <= datetime.now().year % 100 + 10 else 1900 + year
                month = int(date_str[2:4])
                day = int(date_str[4:6])
                try:
                    info["expiry_date"] = datetime(year, month, day).strftime('%Y-%m-%d')
                except ValueError:
                    info["expiry_date"] = None # 유효하지 않은 날짜
            else: # DD MMM YYYY format
                try:
                    # 월 이름을 숫자로 변환 (예: JAN -> 01)
                    month_map = {
                        'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04', 'MAY': '05', 'JUN': '06',
                        'JUL': '07', 'AUG': '08', 'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
                    }
                    parts = date_str.split()
                    day = int(parts[0])
                    month = int(month_map.get(parts[1].upper()))
                    year = int(parts[2])
                    info["expiry_date"] = datetime(year, month, day).strftime('%Y-%m-%d')
                except Exception:
                    info["expiry_date"] = None # 파싱 오류
            break
    
    return info 