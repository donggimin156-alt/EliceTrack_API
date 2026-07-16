"""
Classroom Course API 전담 클라이언트.

BaseAPIClient(api/base_client.py)를 상속받아 UserAPI와 동일한 패턴을 따른다.
공통 로깅/재시도/헤더 병합 파이프라인(_send_request)은 부모가 처리하고,
여기서는 course 엔드포인트 비즈니스 메서드만 구현한다.

주의: course API(api-classroom.elice.io)는 BaseAPIClient가 기본으로 쓰는
settings.api_base_url과 호스트가 다르다. 그래서 super().__init__() 이후
self.base_url을 직접 오버라이드한다.
"""

import requests

from api.base_client import BaseAPIClient


class ClassApi(BaseAPIClient):
    # settings.api_base_url과 host가 다르므로 BASE_PATH(UserAPI)처럼 클래스 상수로 고정한다.
    BASE_URL = "https://api-classroom.elice.io"

    def __init__(self, session: requests.Session, classroom_id: str) -> None:
        super().__init__(session)
        self.base_url = self.BASE_URL
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