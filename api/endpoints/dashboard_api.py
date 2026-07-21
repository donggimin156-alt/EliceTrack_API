# api/endpoints/dashboard_api.py
"""학습현황(Dashboard) API 전담 클라이언트.

prod: https://api-dashboard.elice.io
dev:  https://dev-qatrack-dashboard-api.dev.elicer.io

인증 세션은 elice_fixture의 prod_learner / dev_learner / dev_educator fixture에서 주입받는다.
"""
import requests

from api.base_client import BaseAPIClient
from core.config import settings


class DashboardAPI(BaseAPIClient):
    PROD_BASE = "https://api-dashboard.elice.io"
    DEV_BASE = "https://dev-qatrack-dashboard-api.dev.elicer.io"

    def __init__(self, session: requests.Session, *, org: str, env: str = "dev") -> None:
        base_url = self.PROD_BASE if env == "prod" else self.DEV_BASE
        super().__init__(session, base_url=base_url)
        self.org = org

    def get_classroom_summary(self, class_id: str, auth: bool = True) -> requests.Response:
        """GET /classroom/{class_id} — 반 전체 학습현황."""
        if not auth:
            return self._no_auth_get(f"/classroom/{class_id}")
        return self.get(f"/classroom/{class_id}")

    def get_student(
        self,
        account_id: int | str,
        classroom_id: str | None = None,
        auth: bool = True,
    ) -> requests.Response:
        """GET /student/{account_id} — 개인 학습현황."""
        params = {}
        if classroom_id is not None:
            params["classroom_id"] = classroom_id
        if not auth:
            return self._no_auth_get(f"/student/{account_id}", params=params)
        return self.get(f"/student/{account_id}", params=params)

    def _no_auth_get(self, endpoint: str, **kwargs) -> requests.Response:
        """Authorization 헤더 없이 GET — 403 차단 검증 전용."""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        return requests.get(
            url,
            headers={"x-elice-org-name-short": self.org},
            timeout=settings.api_timeout,
            **kwargs,
        )
