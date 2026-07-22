"""
Classroom Course API 전담 클라이언트.

BaseAPIClient(api/base_client.py)를 상속받아 UserAPI와 동일한 패턴을 따른다.
공통 로깅/재시도/헤더 병합 파이프라인(_send_request)은 부모가 처리하고,
여기서는 course 엔드포인트 비즈니스 메서드만 구현한다.

호스트는 settings.elice_environments[env_name]["CLASSROOM_API_URL"] (SSOT)을 사용한다.
"""

import requests

from api.base_client import BaseAPIClient
from core.config import settings


class ClassApi(BaseAPIClient):
    def __init__(
        self,
        session: requests.Session,
        classroom_id: str,
        *,
        env_name: str = "prod",
    ) -> None:
        env = settings.elice_environments[env_name]
        super().__init__(
            session,
            base_url=env["CLASSROOM_API_URL"].rstrip("/"),
        )
        self.classroom_id = classroom_id

    @property
    def course_path(self) -> str:
        return f"/classroom/{self.classroom_id}/course"

    def get_course_list(self, skip: int, count: int) -> requests.Response:
        """GET /classroom/{classroom_id}/course"""
        return self.get(self.course_path, params={"skip": skip, "count": count})

    def get_course(self, course_id: str) -> requests.Response:
        """GET /classroom/{classroom_id}/course/{course_id}"""
        return self.get(f"{self.course_path}/{course_id}")

    def create_course(self, payload: dict) -> requests.Response:
        """POST /classroom/{classroom_id}/course"""
        return self.post(self.course_path, json=payload)

    def add_courses_bulk(self, original_course_ids: list[int]) -> requests.Response:
        """POST /v2/classroom/{classroom_id}/course/bulk — 비동기 과목 추가, task_id만 즉시 반환"""
        return self.post(
            f"/v2/classroom/{self.classroom_id}/course/bulk",
            json={"original_course_ids": original_course_ids},
        )

    def get_task(self, task_id: str) -> requests.Response:
        """GET /task/{task_id} — bulk 작업 상태 폴링 (classroom-api와 같은 호스트, /classroom 접두사 없음)"""
        return self.get(f"/task/{task_id}")