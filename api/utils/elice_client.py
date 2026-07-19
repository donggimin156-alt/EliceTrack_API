# api/elice_client.py
"""Elice QA 프로젝트 전용 API 클라이언트.

BaseAPIClient(통신 엔진: 로깅, cURL 재현, SLA 체크, Request-ID 추적)를 상속하고,
그 위에 Elice 특유의 인증(Bearer token) / 조직(org) 헤더 / 게시판 도메인 메서드를 얹습니다.

기존에는 elice_fixture.py 안에 EliceApiClient가 requests.Session을 직접 감싸며
독자적인 통신 로직을 갖고 있었지만, 이제 통신 로직은 전부 BaseAPIClient에 위임합니다.
"""
import requests

from api.base_client import BaseAPIClient
from core.config import settings


class EliceApiClient(BaseAPIClient):
    """Elice API 통신 클라이언트.

    인증 헤더 + org 헤더가 미리 세팅된 세션을 사용하며,
    org-scoped 경로(`org/{org}/...`)를 자동으로 붙여줍니다.

    URL/org/classroom_id 등은 이 클래스가 직접 선언하지 않고,
    항상 core.config.settings.elice_environments(SSOT)에서 가져옵니다.
    """

    def __init__(self, env_name: str, role: str, token: str):
        env_config = settings.elice_environments[env_name]
        super().__init__(
            session=requests.Session(),
            raise_for_status=False,
            base_url=env_config["REST_API_URL"].rstrip("/"),
            timeout=(5, int(settings.elice_api_timeout)),
            client_name=f"Elice-{env_name}-{role}",
        )
        self.env_name = env_name
        self.role = role
        self.org = env_config["ORG"]
        self.auth_url = env_config["AUTH_API_URL"].rstrip("/")
        self.classroom_id = env_config["CLASSROOM_ID"]
        self.board_id = env_config["BOARD_ID"]
        self.others_article_id = env_config["OTHERS_ARTICLE_ID"]

        # requests.Session.headers는 session을 공유하는 다른 BaseAPIClient에도
        # Authorization/org 헤더가 자동 병합되므로, fixture에서 session에 심어두면
        # ClassApi·ScheduleAPI 등이 같은 인증을 재사용할 수 있다.
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "x-elice-org-name-short": self.org,
        })

    def _scoped(self, path: str) -> str:
        return f"org/{self.org}/{path.lstrip('/')}"

    # ── BaseAPIClient의 get/post를 org-scoped 경로로 감싸기 ──
    def get(self, path: str, **kwargs) -> requests.Response:
        return super().get(self._scoped(path), **kwargs)

    def post(self, path: str, data: dict | None = None, json: dict | None = None, **kwargs) -> requests.Response:
        return super().post(self._scoped(path), data=data, json=json, **kwargs)
