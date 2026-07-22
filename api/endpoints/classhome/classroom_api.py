# api/endpoints/classroom_api.py
"""클래스 홈(Classroom) API 전담 클라이언트.

classroom-api는 EliceApiClient 기본 host(api-rest.elice.io)와 달라
별도 base_url을 오버라이드한다.
인증 세션은 elice_fixture의 prod_learner / dev_educator fixture에서 주입받는다.
"""
import requests

from api.endpoints.classhome.no_token import NoTokenClient
from core.config import settings


class ClassroomAPI(NoTokenClient):
    def __init__(
        self,
        session: requests.Session,
        *,
        org: str,
        classroom_id: str,
        env: str,
    ) -> None:
        base_url = settings.elice_environments[env]["CLASSROOM_API_URL"]
        super().__init__(session, org=org, base_url=base_url)
        self.classroom_id = classroom_id

    def get_classroom_list(self, skip=None, count=None, auth: bool = True) -> requests.Response:
        """GET /classroom — skip/count를 None으로 두면 파라미터에서 제외."""
        params = {k: v for k, v in {"skip": skip, "count": count}.items() if v is not None}
        if not auth:
            return self._no_auth_get("/classroom", params=params)
        return self.get("/classroom", params=params)

    def get_classroom_count(self, auth: bool = True) -> requests.Response:
        """GET /classroom/count"""
        if not auth:
            return self._no_auth_get("/classroom/count")
        return self.get("/classroom/count")

