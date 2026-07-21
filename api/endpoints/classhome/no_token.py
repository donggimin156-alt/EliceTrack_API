# api/endpoints/classhome/no_token.py
"""토큰 없는 요청 공통 기반 — classroom-api·dashboard-api 403 차단 검증 공유."""
import requests

from api.base_client import BaseAPIClient
from core.config import settings


class NoTokenClient(BaseAPIClient):
    """토큰 없이 GET 요청을 보내는 공통 기반 — _no_auth_get 중복 제거."""

    def __init__(self, session: requests.Session, *, org: str, **kwargs) -> None:
        super().__init__(session, **kwargs)
        self.org = org

    def _no_auth_get(self, endpoint: str, **kwargs) -> requests.Response:
        """Authorization 헤더 없이 GET — 403 차단 검증 전용."""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        return requests.get(
            url,
            headers={"x-elice-org-name-short": self.org},
            timeout=settings.api_timeout,
            **kwargs,
        )
