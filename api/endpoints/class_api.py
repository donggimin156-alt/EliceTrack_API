"""
Classroom Course API 전담 클라이언트.

BaseAPIClient(api/base_client.py)를 상속받아 UserAPI와 동일한 패턴을 따른다.
공통 로깅/재시도/헤더 병합 파이프라인(_send_request)은 부모가 처리하고,
여기서는 course 엔드포인트 비즈니스 메서드만 구현한다.

호스트는 settings.elice_environments[env_name]["CLASSROOM_API_URL"] (SSOT)을 사용한다.

⚠️ org-scoped 메서드(get_lecture_list, get_dashboard_* 등)는 CLASSROOM_API_URL이 아니라
   REST_API_URL 위에서 서빙된다 (실증: GET https://dev-qatrack-api.dev.elicer.io/org/academy/course/get/?course_id=43).
   BaseAPIClient의 base_url은 하나로 고정되므로, 이 메서드들은 self.session을 직접 써서
   별도 호스트(_rest_api_base_url)로 요청을 보낸다.
"""

import requests

from api.base_client import BaseAPIClient
from core.config import settings
from utils.helpers.class_helper import build_json_query_params


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
        # org-scoped (lecture/dashboard) 엔드포인트 전용 — 위 docstring 참고
        self._rest_api_base_url = env["REST_API_URL"].rstrip("/")
        self.org = env["ORG"]

    @property
    def course_path(self) -> str:
        return f"/classroom/{self.classroom_id}/course"

    # ==========================================
    # classroom-scoped 메서드 (CLASSROOM_API_URL)
    # ==========================================

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

    def delete_course(self, course_id: int | str) -> requests.Response:
        """DELETE /classroom/{classroom_id}/course/{course_id}"""
        return self.delete(f"{self.course_path}/{course_id}")

    def get_course_count(self) -> requests.Response:
        """GET /classroom/{classroom_id}/course/count"""
        return self.get(f"{self.course_path}/count")

    def reorder_courses(self, course_ids: list[int]) -> requests.Response:
        """POST /classroom/{classroom_id}/course/reorder"""
        return self.post(f"{self.course_path}/reorder", json={"course_ids": course_ids})

    # ==========================================
    # org-scoped 메서드 (REST_API_URL, /org/{org}/... )
    # ==========================================

    def _org_get(self, path: str, **kwargs) -> requests.Response:
        """REST_API_URL + org/{org}/... 로 GET 요청 (classroom-api와 다른 호스트)."""
        url = f"{self._rest_api_base_url}/org/{self.org}/{path.lstrip('/')}"
        return self.session.get(url, timeout=self.timeout, **kwargs)

    def get_lecture_list(
        self,
        course_id: int,
        offset: int,
        count: int,
        *,
        filter_conditions: dict | None = None,
        filter_contain_recommand_lecture_page: bool | None = None,
    ) -> requests.Response:
        """GET /org/{org}/lecture/list/ — 과목 내 수업(강의) 목록 (P2)

        ⚠️ 확인되지 않은 부분: filter_conditions 직렬화 방식(JSON 문자열 가정),
        parent_lecture_id 최상위 필터링 시 null 처리 여부. 실제 호출로 검증 필요.
        """
        params = build_json_query_params(
            course_id=course_id,
            offset=offset,
            count=count,
            filter_conditions=filter_conditions,
            filter_contain_recommand_lecture_page=filter_contain_recommand_lecture_page,
        )
        return self._org_get("lecture/list/", params=params)

    def get_course_info(self, course_id: int) -> requests.Response:
        """GET /org/{org}/course/get/ — 과목 소개 콘텐츠 포함 여부 확인용 (P3)

        ⚠️ 확인되지 않은 부분: description/short_description/target_audience/objective/faq/
        promote_video_url이 실제로 이 응답에 포함되는지. org/course/edit/의 쓰기 파라미터로만
        존재를 추정했고, 읽기 응답 스키마는 스펙 문서에 없어 실제 호출로 확인 필요.
        """
        return self._org_get("course/get/", params={"course_id": course_id})

    def get_dashboard_course(self, course_id: int, course_section_id: int) -> requests.Response:
        """GET /org/{org}/dashboard/course/get/ — 과목 단위 학습현황 오버뷰 (P4)

        ⚠️ 확인되지 않은 부분: 응답 필드(progress/avg_practice_score/avg_test_score 등)
        구체적인 이름과 null 처리 방식. 스펙 문서에 응답 스키마 없음.
        """
        return self._org_get(
            "dashboard/course/get/",
            params={"course_id": course_id, "course_section_id": course_section_id},
        )

    def get_dashboard_course_stats_list(
        self, course_id: int, course_section_id: int, offset: int, count: int
    ) -> requests.Response:
        """GET /org/{org}/dashboard/course/stats/list/ — 수업별 학습현황 목록 (P5)"""
        return self._org_get(
            "dashboard/course/stats/list/",
            params={
                "course_id": course_id,
                "course_section_id": course_section_id,
                "offset": offset,
                "count": count,
            },
        )

    def get_dashboard_lecture(self, lecture_id: int, course_section_id: int) -> requests.Response:
        """GET /org/{org}/dashboard/lecture/get/ — 개별 수업 학습현황 요약 (P6)"""
        return self._org_get(
            "dashboard/lecture/get/",
            params={"lecture_id": lecture_id, "course_section_id": course_section_id},
        )

    def get_dashboard_lecture_user_list(
        self,
        lecture_id: int,
        course_section_id: int,
        offset: int,
        count: int,
        *,
        filter_conditions: dict | None = None,
        sort_by: dict | None = None,
    ) -> requests.Response:
        """GET /org/{org}/dashboard/lecture/user/list/ — 수업자료별 점수 목록 (P6)

        ⚠️ 확인되지 않은 부분: sort_by가 JSON object({"key":..., "order":...}) 문자열로
        직렬화되는지 실제 호출로 검증 필요 (스펙상 oneOf 구조 기반 추정).
        """
        params = build_json_query_params(
            lecture_id=lecture_id,
            course_section_id=course_section_id,
            offset=offset,
            count=count,
            filter_conditions=filter_conditions,
            sort_by=sort_by,
        )
        return self._org_get("dashboard/lecture/user/list/", params=params)

    def get_course_section_list(
        self, course_id: int, offset: int = 0, count: int = 20
    ) -> requests.Response:
        """GET /org/{org}/course/section/list/ — 과목 하위 course_section 목록.

        ⚠️ 확인되지 않은 부분: 응답에 course_section_id 필드명이 정확히 이 이름인지,
        최소 1개 이상 항상 존재하는지(과목 생성 시 기본 section 자동 생성 여부).
        """
        return self._org_get(
            "course/section/list/",
            params={"course_id": course_id, "offset": offset, "count": count},
        )