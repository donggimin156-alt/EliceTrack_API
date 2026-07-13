# fixtures/classroom_fixture.py
"""클래스 홈 API 전용 클라이언트 픽스처.

기존 EliceApiClient는 /org/{org}/ 경로 prefix를 붙이지만,
클래스 홈 API(api-classroom.elice.io)는 org prefix 없이 헤더로만 org를 전달하므로 별도 클라이언트 사용.
"""
import os

import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

_BASE = "https://api-classroom.elice.io"
_TIMEOUT = int(os.getenv("ELICE_API_TIMEOUT", "10"))


class ClassroomClient:
    """클래스 홈 API 클라이언트 (prod 학습자 전용).

    인증 헤더 + org 헤더가 미리 세팅된 requests.Session을 래핑합니다.
    get() / get_no_auth() 로 간결하게 호출 가능합니다.
    """

    def __init__(self, token: str) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "x-elice-org-name-short": "qatrack",  # prod 학습자 org
        })

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.session.get(f"{_BASE}/{path.lstrip('/')}", timeout=_TIMEOUT, **kwargs)

    def get_no_auth(self, path: str, **kwargs) -> requests.Response:
        """인증 헤더 없이 GET 요청 — 403 차단 검증 전용."""
        s = requests.Session()
        s.headers.update({"x-elice-org-name-short": "qatrack"})
        return s.get(f"{_BASE}/{path.lstrip('/')}", timeout=_TIMEOUT, **kwargs)


@pytest.fixture
def classroom_client() -> ClassroomClient:
    """prod 학습자 인증 클라이언트.

    PROD_LEARNER_TOKEN 또는 LEARNER_TOKEN 중 하나를 .env에 설정해야 합니다.
    토큰 미설정 시 해당 테스트는 skip 처리됩니다.
    """
    token = (
        os.getenv("PROD_LEARNER_TOKEN", "").strip()
        or os.getenv("LEARNER_TOKEN", "").strip()
    )
    if not token:
        pytest.skip("학습자 토큰 없음 — PROD_LEARNER_TOKEN 또는 LEARNER_TOKEN을 .env에 설정하세요")
    return ClassroomClient(token)
