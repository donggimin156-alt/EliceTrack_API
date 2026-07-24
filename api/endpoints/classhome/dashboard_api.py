# api/endpoints/dashboard_api.py
"""학습현황(Dashboard) API 전담 클라이언트.

prod: https://api-dashboard.elice.io
dev:  https://dev-qatrack-dashboard-api.dev.elicer.io

인증 세션은 elice_fixture의 prod_learner / dev_learner / dev_educator fixture에서 주입받는다.
"""
import requests

from api.endpoints.classhome.no_token import NoTokenClient
from core.config import settings


class DashboardAPI(NoTokenClient):
    def __init__(self, session: requests.Session, *, org: str, env: str = "dev") -> None:
        base_url = settings.elice_environments[env]["DASHBOARD_API_URL"]
        super().__init__(session, org=org, base_url=base_url)

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

    def get_student_progress(
        self,
        account_id: int,
        classroom_id: str,
        course_id: int,
        filter_cohort_id: str,
    ) -> requests.Response:
        """GET /student/{account_id} — 학습자 본인 학습현황 상세 (L-06~L-09)"""
        return self.get(
            f"/student/{account_id}",
            params={
                "classroom_id": classroom_id,
                "course_id": course_id,
                "filter_cohort_id": filter_cohort_id,
            },
        )

    def get_course_report_token(
        self,
        course_id: int,
        elice_course_id: int,
    ) -> requests.Response:
        """GET /course/{course_id}/report — 학습현황 엑셀 다운로드 토큰 발급 (E-11, 교육자)"""
        return self.get(
            f"/course/{course_id}/report",
            params={"elice_course_id": elice_course_id},
        )