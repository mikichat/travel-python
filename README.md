# Travel CRM (Python Flask)

이 프로젝트는 Flask 프레임워크를 기반으로 구축된 여행사 고객 관계 관리(CRM) 시스템입니다. 고객, 여행 일정 및 예약 정보를 효율적으로 관리할 수 있도록 설계되었습니다.

## 🚀 주요 기능

- **대시보드**: 실시간 통계, 최근 예약, 시스템 알림을 한눈에 확인
- **사용자 인증**: JWT(JSON Web Token) 기반의 안전한 사용자 등록 및 로그인 시스템
- **고객 관리**: 고객 정보 생성, 조회, 수정 및 삭제 기능, **여권 파일 첨부 및 정보 추출 기능 (OCR 기반)**
- **여행 일정 관리**: 여행 일정 생성, 조회, 수정 및 삭제 기능
- **예약 관리**: 여행 예약 생성, 조회, 수정 및 삭제 기능 (새로운 예약 코드 형식 및 QR코드 지원)
- **공개 예약 조회**: 예약 코드를 통해 로그인 없이 개별 예약 정보 조회 기능
- **발권 관리**: 항공 발권 정보 생성, 조회, 수정 및 삭제 기능 (항공사, 비행 유형, 진행 상태, 코드, 여권 첨부, 메모 포함)
- **데이터 내보내기**: 고객, 일정, 예약 데이터를 CSV 파일로 내보내는 기능
- **반응형 UI**: Tailwind CSS를 활용한 현대적이고 반응형 웹 인터페이스
- **모듈화된 구조**: Blueprint 기반의 깔끔한 코드 구조
- **실시간 통계**: 데이터베이스 기반 실시간 통계 및 성장률 분석
- **업체(렌드사) 관리**: 여행사와 협력하는 항공, 호텔, 교통, 식사, 가이드, 옵션투어, 보험, 비자 등 공급업체 정보 관리 (등록/수정/삭제/목록, 체크박스 취급항목)
- **예약코드 QR**: 예약수정 페이지에서 예약코드에 마우스를 올리면 해당 예약의 QR코드(예약조회 URL)가 팝업으로 표시됨 (모바일 터치 지원)

## 🛠 기술 스택

- **백엔드**: Python 3.8+, Flask 2.x
- **데이터베이스**: SQLite (SQLite3)
- **인증**: bcrypt, PyJWT
- **프론트엔드**: HTML, Jinja2, Tailwind CSS, Font Awesome
- **OCR**: pytesseract (Tesseract OCR 엔진 시스템 설치 필요)
- **아키텍처**: Blueprint 패턴, Application Factory 패턴
- **유틸리티**: 템플릿 필터, 오류 처리, 인증 데코레이터, QR코드 생성(qrcode)

## 📁 프로젝트 구조

```
travel-python/
├── app/                          # 메인 애플리케이션 패키지
│   ├── __init__.py              # Flask 앱 팩토리
│   ├── routes/                  # 라우트 모듈
│   │   ├── __init__.py          
│   │   ├── auth_routes.py       # 인증 관련 라우트
│   │   ├── customer_routes.py   # 고객 관리 라우트
│   │   ├── schedule_routes.py   # 일정 관리 라우트
│   │   ├── reservation_routes.py # 예약 관리 라우트
│   │   ├── ticketing_routes.py  # 발권 관리 라우트
│   │   ├── public_routes.py     # 공개 라우트 (예약 조회)
│   │   └── audit_routes.py      # 변경 로그 라우트
│   ├── models/                  # 데이터 모델 (향후 확장)
│   │   ├── __init__.py
│   │   └── ticketing_model.py   # 발권 모델
│   ├── utils/                   # 유틸리티 모듈
│   │   ├── __init__.py
│   │   ├── errors.py            # 오류 처리 및 APIError 클래스
│   │   ├── auth.py              # JWT 인증 데코레이터
│   │   ├── filters.py           # 템플릿 필터 함수들
│   │   └── ocr_utils.py         # 여권 정보 OCR 추출 유틸리티
│   ├── templates/               # HTML 템플릿
│   │   ├── base.html            # 기본 레이아웃
│   │   ├── public_base.html     # 공개 페이지 기본 레이아웃
│   │   ├── login.html           # 로그인 페이지
│   │   ├── register.html        # 회원가입 페이지
│   │   ├── dashboard.html       # 대시보드 페이지
│   │   ├── customers.html       # 고객 관리 페이지
│   │   ├── schedules.html       # 일정 관리 페이지
│   │   ├── reservations.html    # 예약 관리 페이지
│   │   ├── view_reservation.html # 예약 상세 조회 페이지
│   │   ├── ticketing.html       # 발권 목록 페이지
│   │   ├── create_ticketing.html # 새 발권 추가 페이지
│   │   ├── edit_ticketing.html  # 발권 정보 편집 페이지
│   │   └── components/          # 재사용 가능한 컴포넌트
│   └── static/                  # 정적 파일 (CSS, JS, 이미지)
│       ├── css/
│       ├── js/
│       └── uploads/             # 업로드된 여권 사진 등
├── config.py                    # 환경별 설정 관리
├── run.py                       # 애플리케이션 실행 진입점
├── database.py                  # 데이터베이스 연결 및 초기화
├── populate_db.py               # 샘플 데이터 생성 (선택사항)
├── populate_reservation_codes.py # 예약 코드 샘플 데이터 생성
├── requirements.txt             # Python 의존성 목록
└── README.md                    # 프로젝트 문서
```

## 🚀 시작하기

### 1. 저장소 클론

```bash
git clone <repository-url>
cd travel-python
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

qrcode 패키지가 QR코드 생성을 위해 필요합니다. requirements.txt에 포함되어 있습니다.

### 3. Tesseract OCR 설치 (Windows)

여권 사진에서 정보를 추출하려면 Tesseract OCR 엔진이 시스템에 설치되어 있어야 합니다.

1.  **Tesseract OCR 다운로드**: 다음 링크에서 Windows용 설치 프로그램을 다운로드합니다.
    *   [Tesseract OCR for Windows](https://tesseract-ocr.github.io/tessdoc/Downloads.html) (현재 권장 버전: `tesseract-ocr-w64-setup-5.5.0.20241111.exe`와 유사한 파일명)
    https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe
2.  **설치 진행**:
    *   다운로드한 `.exe` 파일을 실행하여 설치를 시작합니다.
    *   설치 과정 중 **"Add Tesseract to Path"** 옵션을 반드시 체크하여 시스템 환경 변수에 Tesseract 실행 파일 경로가 자동으로 추가되도록 합니다. (이 단계를 건너뛰었다면 수동으로 PATH를 설정해야 합니다.)
    *   한국어 등 추가 언어 팩이 필요하면 설치 시 선택합니다.
3.  **설치 확인**: 명령 프롬프트(CMD) 또는 PowerShell을 열고 다음 명령어를 입력하여 Tesseract가 올바르게 설치되었는지 확인합니다.
    ```bash
    tesseract --version
    ```
    버전 정보가 출력되면 성공적으로 설치된 것입니다.

### 4. 환경 변수 설정 (선택사항)

프로덕션 환경에서는 반드시 강력한 시크릿 키를 설정하는 것이 좋습니다.

**Windows (PowerShell):**
```powershell
$env:JWT_SECRET="your_jwt_secret_key"
$env:FLASK_SECRET_KEY="your_flask_secret_key"
$env:FLASK_ENV="development"
```

**Linux/macOS:**
```bash
export JWT_SECRET="your_jwt_secret_key"
export FLASK_SECRET_KEY="your_flask_secret_key"
export FLASK_ENV="development"
```

BASE_DOMAIN_URL: QR코드에 포함될 서비스 기본 도메인 URL (예: https://yourdomain.com)

### 5. 데이터베이스 초기화

```bash
python database.py
```

### 6. 샘플 데이터 생성 (선택사항)

```bash
python populate_db.py
```

### 7. 애플리케이션 실행

```bash
python run.py
```

애플리케이션은 `http://localhost:5000`에서 실행됩니다.

## 📖 사용법

### 기본 워크플로우

1.  **회원가입/로그인**: `/register` 또는 `/login`에서 계정 생성 또는 로그인
2.  **대시보드**: `/dashboard`에서 전체 시스템 개요 확인
    -   실시간 통계 (고객 수, 일정 수, 예약 수, 수익)
    -   최근 예약 현황
    -   시스템 알림
    -   빠른 액션 버튼
3.  **고객 관리**: `/customers`에서 고객 정보 관리
4.  **일정 관리**: `/schedules`에서 여행 일정 관리
5.  **예약 관리**: `/reservations`에서 예약 정보 관리
    -   **진행 단계**:
        1.  예약 요청 - 고객상담
        2.  진행 확인 - 담당자와 협의
        3.  대기 예약 - 입금 전
        4.  계약 확정 - 계약금만, 잔금 (미수)
        5.  완납 서비스 - 체크리스트
        6.  완료 도착
        7.  VIP 고객 - 재구매는 (V.V.IP 고객)
        8.  불만
        9.  처리완료
6.  **발권 관리**: `/ticketing`에서 항공 발권 정보 관리
    -   항공사 종류, 비행 유형 (편도, 왕복, 경유), 발권 진행 상태, 항공 발권 코드, 여권 첨부 및 메모 관리
-   **예약코드와 QR코드**: 예약수정 페이지에서 예약코드에 마우스를 올리면 해당 예약의 QR코드(예약조회 URL)가 팝업으로 표시됩니다. (모바일 터치 지원)

### 대시보드 기능

-   **통계 카드**: 실시간 데이터베이스 기반 통계
-   **성장률 표시**: 지난 달 대비 성장률 계산
-   **최근 예약**: 최근 5개 예약 현황
-   **빠른 액션**: 새 고객/일정/예약 생성 바로가기
-   **시스템 알림**: 동적 알림 시스템

## 🔧 개발 가이드

### 코드 구조

이 프로젝트는 Flask의 Blueprint 패턴을 사용하여 모듈화되어 있습니다:

-   **routes/**: 각 기능별 라우트를 별도 파일로 분리
-   **utils/**: 공통 유틸리티 함수 및 클래스
-   **models/**: 데이터 모델 (향후 ORM 도입 시 확장)
-   **templates/**: Jinja2 템플릿 파일
-   **static/**: CSS, JavaScript, 이미지 등 정적 파일

### 오류 처리

프로젝트는 표준화된 오류 처리 시스템을 사용합니다:

```python
from app.utils.errors import APIError

# 사용 예시
raise APIError('사용자를 찾을 수 없습니다.', 404)
```

### 인증 시스템

JWT 기반 인증 시스템이 구현되어 있습니다:

```python
from app.utils.auth import jwt_required

@app.route('/protected')
@jwt_required(current_app)
def protected_route():
    # 인증된 사용자만 접근 가능
    pass
```

### 템플릿 필터

템플릿에서 사용할 수 있는 필터 함수들이 구현되어 있습니다:

```python
# 상태별 색상
{{ reservation.status | get_status_color }}

# 상태별 텍스트
{{ reservation.status | get_status_text }}

# 통화 형식
{{ amount | format_currency }}

# 날짜 형식
{{ date | format_date }}
```

## 📊 API 엔드포인트

### 인증 API

-   `POST /api/auth/register` - 사용자 등록
-   `POST /api/auth/login` - 사용자 로그인
-   `GET /api/auth/me` - 현재 사용자 정보 조회

### 대시보드 API

-   `GET /dashboard/` - 대시보드 페이지 (통계 포함)

### 고객 API

-   `GET /api/customers` - 고객 목록 조회
-   `POST /api/customers` - 고객 생성
-   `GET /api/customers/<id>` - 특정 고객 조회
-   `PUT /api/customers/<id>` - 고객 정보 수정
-   `DELETE /api/customers/<id>` - 고객 삭제
-   `POST /api/customers/extract-passport-info` - 여권 사진에서 정보 추출
-   `GET /customers/export-csv` - 고객 데이터 CSV 내보내기

### 일정 API

-   `GET /api/schedules` - 일정 목록 조회
-   `POST /api/schedules` - 일정 생성
-   `GET /api/schedules/<id>` - 특정 일정 조회
-   `PUT /api/schedules/<id>` - 일정 정보 수정
-   `DELETE /api/schedules/<id>` - 일정 삭제
-   `GET /schedules/export-csv` - 일정 데이터 CSV 내보내기

### 예약 API

-   `GET /api/reservations` - 예약 목록 조회
-   `POST /api/reservations` - 예약 생성
-   `GET /api/reservations/<id>` - 특정 예약 조회
-   `PUT /api/reservations/<id>` - 예약 정보 수정
-   `DELETE /api/reservations/<id>` - 예약 삭제
-   `GET /reservations/export-csv` - 예약 데이터 CSV 내보내기

### 발권 API (New!)

-   `GET /ticketing/` - 발권 목록 페이지
-   `GET /ticketing/create` - 새 발권 추가 페이지
-   `POST /ticketing/create` - 새 발권 정보 생성
-   `GET /ticketing/edit/<id>` - 발권 정보 편집 페이지
-   `POST /ticketing/edit/<id>` - 발권 정보 업데이트
-   `POST /ticketing/delete/<id>` - 발권 정보 삭제

### 업체(렌드사) API (New!)

-   `GET /companies/` - 업체 목록 페이지
-   `GET /companies/create` - 새 업체 등록 페이지
-   `POST /companies/create` - 새 업체 정보 생성
-   `GET /companies/edit/<id>` - 업체 정보 수정 페이지
-   `POST /companies/edit/<id>` - 업체 정보 업데이트
-   `POST /companies/delete/<id>` - 업체 정보 삭제

## 🧪 테스트

현재 테스트 코드는 포함되어 있지 않지만, 향후 pytest를 사용한 테스트 추가를 계획하고 있습니다.

## 📝 최근 업데이트

### v2.3.0 - 업체(렌드사) 관리 기능 추가 (2024-06-19)

-   **신규 기능**: 업체(렌드사) 관리(등록/수정/삭제/목록, 취급항목 체크박스, UI 통일성)
-   **DB 스키마 업데이트**: `companies` 테이블 생성
-   **UI 개선**: 사이드바에 '업체 관리' 메뉴 추가, 예약/발권과 동일한 스타일 적용

### v2.2.0 - 발권 관리 기능 추가 및 UI/버그 개선 (2024-06-16)

-   **신규 기능**: 발권 정보 관리 기능 추가 (모델, 라우트, 템플릿 포함)
-   **데이터베이스 스키마 업데이트**: `ticketing` 테이블 생성
-   **UI 개선**: '예약 관리' 및 '변경 로그' 메뉴 UI를 '일정 관리'와 동일하게 개선
-   **UI 개선**: '새 발권 추가' 및 '발권 정보 편집' 페이지 UI를 기존의 '새 예약 생성' 및 '예약 수정' 페이지와 일관되게 디자인
-   **버그 수정**: 루트 URL (/) 접속 시 대시보드로 자동 리디렉션되도록 수정
-   **버그 수정**: 로그인 폼 `POST /login` 404 오류 수정
-   **버그 수정**: 대시보드 '최근 7일 예약' 표기 오류 진단 및 템플릿 수정

### v2.1.0 - 대시보드 기능 완전 구현 (2024-06-14)

-   **대시보드 완성**: 실시간 통계 및 알림 시스템 구현
-   **템플릿 필터**: 상태별 색상, 통화 형식, 날짜 형식 필터 추가
-   **오류 해결**: moment 함수 오류 해결 및 JavaScript 기반 날짜 표시
-   **데이터베이스 통계**: 실시간 통계 조회 및 성장률 계산
-   **동적 알림**: 시스템 상태에 따른 동적 알림 생성

### v2.0.0 - 구조 리팩토링 (2024-06-14)

-   **모듈화**: 단일 `app.py` 파일을 Blueprint 기반 모듈로 분리
-   **표준 구조**: Flask 표준 폴더 구조 적용
-   **오류 처리 개선**: 표준화된 APIError 클래스 및 오류 핸들러 추가
-   **설정 관리**: 환경별 설정 파일 분리
-   **코드 품질**: 가독성 및 유지보수성 향상

### v2.4.0 - 예약코드 QR 기능 및 UI 개선 (2024-06-XX)

-   **신규 기능**: 예약수정 페이지에서 예약코드에 마우스를 올리면 해당 예약의 QR코드(예약조회 URL)가 팝업으로 표시됨 (모바일 터치 지원)
-   **환경설정**: config.py에 BASE_DOMAIN_URL 추가, QR코드 URL 도메인 지정 가능
-   **의존성**: qrcode 패키지 추가
-   **UI 개선**: 예약코드+QR코드 UI 개선, 불필요한 QR 항상 노출 제거

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 연락처

프로젝트 링크: [https://github.com/yourusername/travel-python](https://github.com/yourusername/travel-python)

## 🙏 감사의 말

- Flask 커뮤니티
- Tailwind CSS 팀
- Font Awesome 팀


## 메모 ##
사용자(고객)
- 카카오톡 : 알림,계약금,잔금,일정안내,진행상태,계약승인 컴펌(Y/N)버튼(WEB URL)
- 전화문자 : 알림,계약금,잔금,일정안내,진행상태,계약승인 컴펌(Y/N)버튼(WEB URL)
- 통화안내 : 알림,계약금,잔금,일정안내,진행상태,계약승인
- 예약코드 : (로그인=예약코드+이메일발송코드) 사용자정보 업데이트,여권 업로드
여행사 - 여행일정(팩) : 항공,호텔,교통,식사,가이드,옵션투어,보험,비자
- 
렌드사(협력업체) - 여행일정(팩)상품을 여행사에공급 : 항공,호텔,교통,식사,가이드,옵션투어,보험,비자
Lend Service Provider
- 
## 예약단계
1.예약 요청-고객상담
2.진행 확인-담당자와협의
3.대기 예약-입금전
4.계약 확정-계약금만,잔금(미수)
5.완납 서비스-체크리스트
6.완료 도착
7.VIP고객-재구매(V.VIP고객)
8.불만
9.처리완료

## 코드생성 명령 ##

## FLASK_SECRET_KEY
import os
print(os.urandom(24).hex())

## JWT_SECRET_KEY
import secrets
print(secrets.token_hex(32)) # 32바이트 (64자)의 16진수 문자열

## ENCRYPTION_KEY
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
