# Travel CRM (Python Flask)

이 프로젝트는 Flask 프레임워크를 기반으로 구축된 여행사 고객 관계 관리(CRM) 시스템입니다. 고객, 여행 일정 및 예약 정보를 효율적으로 관리할 수 있도록 설계되었습니다.

## 🚀 주요 기능

- **대시보드**: 실시간 통계, 최근 예약, 시스템 알림을 한눈에 확인
- **사용자 인증**: JWT(JSON Web Token) 기반의 안전한 사용자 등록 및 로그인 시스템
- **고객 관리**: 고객 정보 생성, 조회, 수정 및 삭제 기능
- **여행 일정 관리**: 여행 일정 생성, 조회, 수정 및 삭제 기능
- **예약 관리**: 여행 예약 생성, 조회, 수정 및 삭제 기능
- **데이터 내보내기**: 고객, 일정, 예약 데이터를 CSV 파일로 내보내는 기능
- **반응형 UI**: Tailwind CSS를 활용한 현대적이고 반응형 웹 인터페이스
- **모듈화된 구조**: Blueprint 기반의 깔끔한 코드 구조
- **실시간 통계**: 데이터베이스 기반 실시간 통계 및 성장률 분석

## 🛠 기술 스택

- **백엔드**: Python 3.8+, Flask 2.x
- **데이터베이스**: SQLite (SQLite3)
- **인증**: bcrypt, PyJWT
- **프론트엔드**: HTML, Jinja2, Tailwind CSS, Font Awesome
- **아키텍처**: Blueprint 패턴, Application Factory 패턴
- **유틸리티**: 템플릿 필터, 오류 처리, 인증 데코레이터

## 📁 프로젝트 구조

```
travel-python/
├── app/                          # 메인 애플리케이션 패키지
│   ├── __init__.py              # Flask 앱 팩토리
│   ├── routes/                  # 라우트 모듈
│   │   ├── __init__.py          # 대시보드 라우트 및 필터
│   │   ├── auth_routes.py       # 인증 관련 라우트
│   │   ├── customer_routes.py   # 고객 관리 라우트
│   │   ├── schedule_routes.py   # 일정 관리 라우트
│   │   └── reservation_routes.py # 예약 관리 라우트
│   ├── models/                  # 데이터 모델 (향후 확장)
│   │   └── __init__.py
│   ├── utils/                   # 유틸리티 모듈
│   │   ├── __init__.py
│   │   ├── errors.py            # 오류 처리 및 APIError 클래스
│   │   ├── auth.py              # JWT 인증 데코레이터
│   │   └── filters.py           # 템플릿 필터 함수들
│   ├── templates/               # HTML 템플릿
│   │   ├── base.html            # 기본 레이아웃
│   │   ├── login.html           # 로그인 페이지
│   │   ├── register.html        # 회원가입 페이지
│   │   ├── dashboard.html       # 대시보드 페이지
│   │   ├── customers.html       # 고객 관리 페이지
│   │   ├── schedules.html       # 일정 관리 페이지
│   │   ├── reservations.html    # 예약 관리 페이지
│   │   └── components/          # 재사용 가능한 컴포넌트
│   └── static/                  # 정적 파일 (CSS, JS, 이미지)
│       ├── css/
│       └── js/
├── config.py                    # 환경별 설정 관리
├── run.py                       # 애플리케이션 실행 진입점
├── database.py                  # 데이터베이스 연결 및 초기화
├── populate_db.py               # 샘플 데이터 생성 (선택사항)
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

### 3. 환경 변수 설정 (선택사항)

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

### 4. 데이터베이스 초기화

```bash
python database.py
```

### 5. 샘플 데이터 생성 (선택사항)

```bash
python populate_db.py
```

### 6. 애플리케이션 실행

```bash
python run.py
```

애플리케이션은 `http://localhost:5000`에서 실행됩니다.

## 📖 사용법

### 기본 워크플로우

1. **회원가입/로그인**: `/register` 또는 `/login`에서 계정 생성 또는 로그인
2. **대시보드**: `/dashboard`에서 전체 시스템 개요 확인
   - 실시간 통계 (고객 수, 일정 수, 예약 수, 수익)
   - 최근 예약 현황
   - 시스템 알림
   - 빠른 액션 버튼
3. **고객 관리**: `/customers`에서 고객 정보 관리
4. **일정 관리**: `/schedules`에서 여행 일정 관리
5. **예약 관리**: `/reservations`에서 예약 정보 관리

### 대시보드 기능

- **통계 카드**: 실시간 데이터베이스 기반 통계
- **성장률 표시**: 지난 달 대비 성장률 계산
- **최근 예약**: 최근 5개 예약 현황
- **빠른 액션**: 새 고객/일정/예약 생성 바로가기
- **시스템 알림**: 동적 알림 시스템

## 🔧 개발 가이드

### 코드 구조

이 프로젝트는 Flask의 Blueprint 패턴을 사용하여 모듈화되어 있습니다:

- **routes/**: 각 기능별 라우트를 별도 파일로 분리
- **utils/**: 공통 유틸리티 함수 및 클래스
- **models/**: 데이터 모델 (향후 ORM 도입 시 확장)
- **templates/**: Jinja2 템플릿 파일
- **static/**: CSS, JavaScript, 이미지 등 정적 파일

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
- `POST /api/auth/register` - 사용자 등록
- `POST /api/auth/login` - 사용자 로그인
- `GET /api/auth/me` - 현재 사용자 정보 조회

### 대시보드 API
- `GET /dashboard/` - 대시보드 페이지 (통계 포함)

### 고객 API
- `GET /api/customers` - 고객 목록 조회
- `POST /api/customers` - 고객 생성
- `GET /api/customers/<id>` - 특정 고객 조회
- `PUT /api/customers/<id>` - 고객 정보 수정
- `DELETE /api/customers/<id>` - 고객 삭제
- `GET /customers/export-csv` - 고객 데이터 CSV 내보내기

### 일정 API
- `GET /api/schedules` - 일정 목록 조회
- `POST /api/schedules` - 일정 생성
- `GET /api/schedules/<id>` - 특정 일정 조회
- `PUT /api/schedules/<id>` - 일정 정보 수정
- `DELETE /api/schedules/<id>` - 일정 삭제
- `GET /schedules/export-csv` - 일정 데이터 CSV 내보내기

### 예약 API
- `GET /api/reservations` - 예약 목록 조회
- `POST /api/reservations` - 예약 생성
- `GET /api/reservations/<id>` - 특정 예약 조회
- `PUT /api/reservations/<id>` - 예약 정보 수정
- `DELETE /api/reservations/<id>` - 예약 삭제
- `GET /reservations/export-csv` - 예약 데이터 CSV 내보내기

## 🧪 테스트

현재 테스트 코드는 포함되어 있지 않지만, 향후 pytest를 사용한 테스트 추가를 계획하고 있습니다.

## 📝 최근 업데이트

### v2.1.0 - 대시보드 기능 완전 구현 (2024-06-14)

- **대시보드 완성**: 실시간 통계 및 알림 시스템 구현
- **템플릿 필터**: 상태별 색상, 통화 형식, 날짜 형식 필터 추가
- **오류 해결**: moment 함수 오류 해결 및 JavaScript 기반 날짜 표시
- **데이터베이스 통계**: 실시간 통계 조회 및 성장률 계산
- **동적 알림**: 시스템 상태에 따른 동적 알림 생성

### v2.0.0 - 구조 리팩토링 (2024-06-14)

- **모듈화**: 단일 `app.py` 파일을 Blueprint 기반 모듈로 분리
- **표준 구조**: Flask 표준 폴더 구조 적용
- **오류 처리 개선**: 표준화된 APIError 클래스 및 오류 핸들러 추가
- **설정 관리**: 환경별 설정 파일 분리
- **코드 품질**: 가독성 및 유지보수성 향상

### 주요 변경사항

1. **파일 구조 개선**
   - `app/` 디렉토리 생성 및 모듈화
   - `routes/`, `utils/`, `models/` 디렉토리 분리
   - `config.py` 및 `run.py` 추가

2. **Blueprint 패턴 도입**
   - `dashboard_bp`: 대시보드 라우트
   - `auth_bp`: 인증 관련 라우트
   - `customer_bp`: 고객 관리 라우트
   - `schedule_bp`: 일정 관리 라우트
   - `reservation_bp`: 예약 관리 라우트

3. **유틸리티 모듈**
   - `errors.py`: 표준화된 오류 처리
   - `auth.py`: JWT 인증 데코레이터
   - `filters.py`: 템플릿 필터 함수들

4. **대시보드 기능**
   - 실시간 데이터베이스 통계
   - 성장률 계산
   - 최근 예약 표시
   - 동적 알림 시스템
   - 빠른 액션 버튼

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
