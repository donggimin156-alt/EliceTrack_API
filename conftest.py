# conftest.py
"""
QA 자동화 프레임워크의 최상위 Pytest 진입점(Entry Point) 설정 파일입니다.

[단일 책임 원칙(SRP) 준수]
이 파일 내부에 직접 Fixture나 Hook 로직을 구현하여 비대해지는 것을 방지합니다.
대신 `pytest_plugins` 리스트를 통해 하위 모듈들을 동적으로 지연 로딩(Lazy Loading)하여 
프레임워크의 유지보수성과 가독성을 극대화합니다.
"""

# Pytest가 실행될 때 자동으로 탐색하고 로드할 커스텀 플러그인 경로 목록
pytest_plugins = [
    # 1. Hooks (초기화, 디버깅, 알림 연동 생명주기 제어)
    "hooks.config_hook",
    "hooks.debug_hook",
    "hooks.jira_hook",
    "hooks.slack_hook",
    "hooks.discord_hook", 
    
    # 2. Fixtures (테스트 실행 전/후 의존성 주입 객체)
    "fixtures.api_fixture",
    "fixtures.board_fixture",
    "fixtures.class_fixture",
    "fixtures.schedule_fixture",
    "fixtures.class_lecture_fixture",
]