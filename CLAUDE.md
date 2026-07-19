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
├── ├── endpoints/           
│   ├── schemas/ 
├── └── utils/                  
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

HTML 파일 2개(API 명세)는 꼭 전체를 다 알고 있을 것
PDF 파일 2개(학습자/교육자 권한 UI)를 숙지 하여
겹치는 api일 경우엔 학습자 교육자를 둘 다 알려주고
한쪽에서만 쓰일 경우엔 한쪽만 알려줌
test_class.py는 내 뼈대 코드임 이 스타일에 맞춰서 코딩할 것
또 폴더 구조에 맞게 코딩 할 것 (fixture, schemas 등등)
인증은 fixtures/elice_auth.py (SSOT), 도메인별 fixture는 board_fixture·class_fixture·schedule_fixture를 사용할 것