<<<<<<< HEAD
# travel-python
=======
# Travel CRM (Python Flask)

이 프로젝트는 Flask 프레임워크를 기반으로 구축된 여행사 고객 관계 관리(CRM) 시스템입니다. 고객, 여행 일정 및 예약 정보를 효율적으로 관리할 수 있도록 설계되었습니다.

## 주요 기능

*   **사용자 인증**: JWT(JSON Web Token) 기반의 안전한 사용자 등록 및 로그인 시스템.
*   **고객 관리**: 고객 정보 생성, 조회, 수정 및 삭제 기능.
*   **여행 일정 관리**: 여행 일정 생성, 조회, 수정 및 삭제 기능.
*   **예약 관리**: 여행 예약 생성, 조회, 수정 및 삭제 기능.
*   **데이터 내보내기**: 고객, 일정, 예약 데이터를 CSV 파일로 내보내는 기능.
*   **반응형 UI**: Tailwind CSS를 활용한 현대적이고 반응형 웹 인터페이스.

## 기술 스택

*   **백엔드**: Python, Flask
*   **데이터베이스**: SQLite (SQLite3)
*   **인증**: bcrypt, PyJWT
*   **프론트엔드**: HTML, Jinja2, Tailwind CSS

## 시작하기

프로젝트를 로컬에서 설정하고 실행하는 방법에 대한 지침입니다.

### 1. 의존성 설치

`requirements.txt` 파일에 명시된 모든 Python 의존성을 설치합니다.

```bash
pip install -r requirements.txt
```

### 2. 데이터베이스 초기화 (선택 사항)

애플리케이션을 처음 실행하거나 데이터베이스를 초기화해야 하는 경우, `database.py` 파일의 `initialize_database()` 함수를 실행해야 합니다. 이 함수는 애플리케이션 시작 시 `app.py`에서 호출됩니다.

### 3. 환경 변수 설정

Flask와 JWT를 위한 시크릿 키를 설정해야 합니다. `app.py`에서는 환경 변수가 설정되지 않은 경우 기본값을 사용하지만, 프로덕션 환경에서는 반드시 강력한 시크릿 키를 설정하는 것이 좋습니다.

**Windows (명령 프롬프트):**
```bash
set FLASK_APP=app.py
set JWT_SECRET=your_jwt_secret_key
set FLASK_SECRET_KEY=your_flask_secret_key
```

**Windows (PowerShell):**
```bash
$env:FLASK_APP="app.py"
$env:JWT_SECRET="your_jwt_secret_key"
$env:FLASK_SECRET_KEY="your_flask_secret_key"
```

**Linux/macOS:**
```bash
export FLASK_APP=app.py
export JWT_SECRET=your_jwt_secret_key
export FLASK_SECRET_KEY=your_flask_secret_key
```

### 4. 애플리케이션 실행

환경 변수를 설정한 후, Flask 개발 서버를 실행합니다.

```bash
flask run
```

또는 `python app.py`를 직접 실행할 수도 있습니다.

```bash
python app.py
```

애플리케이션은 일반적으로 `http://127.0.0.1:5000`에서 실행됩니다. 웹 브라우저를 통해 접속할 수 있습니다.

## 사용법

*   **로그인/회원가입**: `/login` 또는 `/register` 경로를 통해 사용자 계정을 생성하거나 로그인할 수 있습니다.
*   **대시보드**: 로그인 후 `/dashboard`에서 관리 페이지로 이동할 수 있습니다.
*   **고객, 일정, 예약 관리**: 대시보드에서 각 섹션으로 이동하여 데이터를 관리할 수 있습니다.

--- 
>>>>>>> 6a2e4bc (Initial commit)
