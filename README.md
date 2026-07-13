# 🚀 Enterprise QA Automation Framework

본 프로젝트는 UI(Selenium WebDriver), API(Requests), Database(SQLAlchemy) 계층을 모두 아우르는 **엔드 투 엔드(E2E) 테스트 자동화 프레임워크**입니다. 

글로벌 실무 표준(Best Practices)과 객체 지향 설계 원칙(SOLID, DRY, 커넥션 풀링 등)을 엄격하게 적용하여 유지보수성, 확장성, 그리고 병렬 실행(xdist) 환경에서의 무결성을 극대화했습니다.

---

## 🛠️ Tech Stack

- **Language**: Python 3.11+
- **Test Runner**: Pytest (`pytest-xdist` 병렬 처리 지원)
- **UI Automation**: Selenium WebDriver 4.x (Page Object / Composition Pattern)
- **API Automation**: Requests (Session / Retry Strategy)
- **Database**: SQLAlchemy, PyMySQL (Connection Pooling)
- **Data Validation & Config**: Pydantic V2, JSON Schema, Faker
- **Reporting**: Allure Report
- **CI/CD & Infrastructure**: Docker, Docker Compose, GitLab CI/CD
- **Code Quality**: Ruff (Linter & Formatter), Mypy (Static Type Checker)

---

## 📁 Directory Structure

프레임워크는 철저한 **단일 책임 원칙(SRP)**과 **관심사 분리(SoC)**를 바탕으로 설계되었습니다.

```text
qa_automation_framework/
├── api/                    # API 클라이언트 및 DTO/Schema 데이터 모델
├── builders/               # API 요청 Payload 생성을 위한 Builder 패턴 객체
├── core/
│   ├── config.py           # Pydantic 기반 전역 환경 변수(SSOT) 관리
│   └── webdriver/          # 브라우저 팩토리 및 Options Builder (OCP 적용)
├── data/                   # 정적 테스트 데이터 (JSON, CSV)
├── fixtures/               # Pytest Fixtures (API Session, DB Client, WebDriver)
├── hooks/                  # Pytest Hooks (Allure 아티팩트, Slack, Jira 연동 제어)
├── pages/
│   ├── base/               # UI 컴포지션 컴포넌트 (Waiter, Interactor, Inspector)
│   └── ...                 # 비즈니스 도메인별 Page Object Model (POM) 클래스
├── services/               # 도메인별 API 비즈니스 워크플로우 추상화 (Service Layer)
├── tests/                  # 실제 Pytest 테스트 스크립트 (api, ui, e2e)
├── utils/                  # 공통 유틸리티 (Assertions, DB, Jira, Slack, DataGen)
├── docker-compose.yml      # Selenium Grid 및 테스트 실행 컨테이너 환경 정의
├── pytest.ini              # Pytest 실행 옵션 및 마커(Marker) 정의
└── requirements.txt        # 코어 패키지 의존성 명세
```

---

## ⚙️ Prerequisites & Installation

### 1. 로컬 환경 설정

Python 3.11 이상이 설치되어 있어야 합니다.

```bash
# 가상 환경 생성 및 활성화
python -m venv venv
source venv/Scripts/activate  # Windows
# source venv/bin/activate    # Mac/Linux

# 패키지 설치 (프로덕션 코어 + 로컬 개발/Lint용)
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. 환경 변수 (`.env`) 셋업

프로젝트 루트 디렉터리에 `.env` 파일을 생성하고 아래 양식에 맞게 값을 채워 넣습니다.
*(참고: 로컬 테스트 시 사용되며, CI/CD 환경에서는 파이프라인 Secret Variable로 오버라이딩 됩니다.)*

```env
TEST_ENV=qa
UI_TIMEOUT=15
API_TIMEOUT=10

# Database Configuration
DB_DRIVER=mysql+pymysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=qa_test_db

# Integrations
REQRES_API_KEY=your_api_key
SLACK_WEBHOOK_URL=[https://hooks.slack.com/services/YOUR/WEBHOOK/URL](https://hooks.slack.com/services/YOUR/WEBHOOK/URL)
JIRA_BASE_URL=[https://yourdomain.atlassian.net](https://yourdomain.atlassian.net)
JIRA_USER_EMAIL=your_email@example.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_PROJECT_KEY=QA
ENABLE_JIRA_AUTO_BUG=false
```

---

## ▶️ Running Tests

### 1. 로컬 환경 (CLI) 실행

Pytest CLI를 활용하여 원하는 테스트만 세밀하게 타겟팅하여 실행할 수 있습니다.

```bash
# 전체 테스트 병렬 실행 (가용 코어 자동 할당)
pytest tests/ -n auto --alluredir=reports/allure-results

# 특정 마커(Marker) 테스트만 실행
pytest -m "smoke"          # 스모크 테스트만 실행
pytest -m "api and p0"     # API 테스트 중 P0(Critical) 우선순위만 실행
pytest -m "ui" --headless  # UI 테스트를 화면 없이(Headless) 실행

# 브라우저 환경 및 Headless 옵션 제어 (기본값: chrome)
pytest tests/ui/ --browser=firefox --headless
```

### 2. 🐳 Docker & Selenium Grid 실행

로컬 PC 환경에 구애받지 않고 **완벽히 격리된 병렬 환경**에서 테스트를 실행하려면 Docker를 사용합니다.

```bash
# Selenium Grid 및 테스트 컨테이너 빌드 & 실행
docker-compose up --build

# 실행 중인 브라우저 테스트 화면 실시간 모니터링 (NoVNC)
# 웹 브라우저 접속: http://localhost:7900 (Password: secret)
```

---

## 📊 Reporting (Allure)

이 프레임워크는 강력한 시각화 도구인 **Allure Report**를 기본으로 지원합니다. 테스트 실패 시 **스크린샷, DOM HTML 원본, 브라우저 콘솔 로그**가 리포트에 자동으로 첨부되어 디버깅 시간을 단축합니다.

```bash
# 이전 결과 초기화 후 HTML 리포트 생성 및 로컬 웹 서버로 열기
allure serve reports/allure-results
```

---

## 🧩 Key Features & Architecture

### 1. Composition 패턴 기반 UI 테스트 (Fluent DSL)

수천 줄의 코드로 비대해지는 `BasePage`를 방지하기 위해 Wait, Action, State 객체로 책임을 분리했습니다.

```python
# 자연어(English-like)에 가까운 직관적인 UI 스크립트 작성 가능
self.action.input_text(self._USERNAME_INPUT, username)
self.action.click(self._LOGIN_BUTTON)
self.wait.for_visibility(self._INVENTORY_CONTAINER)
assert_true(self.state.is_visible(self._SHOPPING_CART))
```

### 2. API + Database E2E 교차 검증

단순 API 응답 검증을 넘어, DB 커넥션 풀을 활용하여 실제 데이터베이스 적재 정합성까지 검증합니다.

```python
@pytest.mark.e2e
def test_create_user_and_verify_db(user_service, db_client):
    # API 요청
    new_user = user_service.create_user(request_dto)
    
    # 실제 DB 데이터 검증
    db_record = db_client.fetch_one("SELECT * FROM users WHERE id = :id", {"id": new_user.id})
    assert_equal(db_record["status"], "ACTIVE")
```

### 3. Slack & Jira Automation

* **Slack**: 테스트 종료 시 총 통과/실패 비율, 소요 시간, 실패한 테스트 목록을 Block Kit UI로 전송합니다.
* **Jira**: CI 환경(`ENABLE_JIRA_AUTO_BUG=true`)에서 테스트 실패 시 자동으로 에러 트레이스와 함께 버그 티켓(Issue)을 생성하고 중복(Deduplication)을 방지합니다.

---

## 🧑‍💻 Code Quality (Linting & Typing)

협업 시 일관된 코드 컨벤션과 에러 방지를 위해 `Ruff`(정적 분석 도구)를 강제합니다. 커밋 전 반드시 린트 검사를 통과해야 합니다. 아래 명령어를 실행하세요.

```bash
# 코드 포맷팅 자동 맞춤
ruff format .

# Linter 경고 확인 및 자동 수정
ruff check . --fix

# 정적 타입(Type Hinting) 무결성 검사
mypy .
```
