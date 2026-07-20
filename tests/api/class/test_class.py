"""
TC-1-1: 학습 과목 목록 조회 (GET /classroom/{classroom_id}/course)

검증을 3개 레이어로 분리했다. (HTTP 200 체크는 assert_status_ok 오토유즈 픽스처가
course_list/full_course_list를 사용하는 모든 테스트에서 자동으로 수행하므로
별도 Status 테스트 클래스는 없앴다.)

    1. Schema Validation       : 응답의 최상위 필드 존재 여부만 검사 (jsonschema)
    2. Nested Schema Validation: classroom_course_progress_data 내부 필드만 검사
    3. Business Validation     : 스키마가 아닌 비즈니스 규칙(값의 의미) 검사
"""

from datetime import datetime

import pytest
from jsonschema import validate
from jsonschema.exceptions import ValidationError

from api.schemas.class_schema import ClassSchemas


def _parse_iso_datetime(value: str) -> datetime:
    """ISO 8601 문자열을 datetime으로 파싱한다 (Z 서픽스 대응)."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class TestClassroomCourseListSchema:
    """1. Response Schema Validation: 최상위 응답 형태 + 필드 존재 여부만 검사"""

    def test_response_is_array(self, course_data):
        assert isinstance(course_data, list)

    def test_response_within_count_bound(self, course_data):
        assert 0 <= len(course_data) <= 10

    def test_each_item_matches_top_level_schema(self, course_data):
        for item in course_data:
            try:
                validate(instance=item, schema=ClassSchemas.COURSE_TOP_LEVEL_SCHEMA)
            except ValidationError as e:
                pytest.fail(
                    f"스키마 검증 실패 (course_id={item.get('course_id')}): {e.message}"
                )


class TestClassroomCourseListNestedSchema:
    """2. Nested Schema Validation: classroom_course_progress_data 내부만 검사"""

    def test_progress_data_matches_schema(self, course_data):
        for item in course_data:
            progress_data = item["classroom_course_progress_data"]
            try:
                validate(instance=progress_data, schema=ClassSchemas.PROGRESS_DATA_SCHEMA)
            except ValidationError as e:
                pytest.fail(
                    f"progress 데이터 스키마 검증 실패 (course_id={item.get('course_id')}): {e.message}"
                )


class TestClassroomCourseListBusiness:
    """3. Business Validation: 스키마가 아닌 비즈니스 규칙 검사"""

    def test_at_least_one_course_exists(self, course_data):
        assert len(course_data) > 0, "검증을 위해 최소 1개 이상의 과목이 필요합니다."

    def test_progress_value_range(self, full_course_data):
        for item in full_course_data:
            progress = item["classroom_course_progress_data"]["progress"]
            assert 0 <= progress <= 100, f"progress 범위 초과: {progress}"

    def test_completed_not_exceed_total_material(self, full_course_data):
        for item in full_course_data:
            pd = item["classroom_course_progress_data"]
            assert pd["completed_material_cnt"] <= pd["total_material_cnt"], (
                f"완료 자료 수가 전체 자료 수를 초과함: course_id={item.get('course_id')}"
            )

    def test_created_not_after_modified(self, full_course_data):
        """created/modified를 문자열이 아닌 실제 datetime으로 비교한다."""
        for item in full_course_data:
            created = _parse_iso_datetime(item["created"])
            modified = _parse_iso_datetime(item["modified"])
            assert created <= modified, (
                f"created가 modified보다 이후임: course_id={item.get('course_id')}"
            )

    def test_pagination_no_duplicate_between_pages(self, class_api):
        """skip=0/10 두 페이지 간 course_id 중복이 없는지 확인"""
        page1 = class_api.get_course_list(skip=0, count=10).json()
        page2 = class_api.get_course_list(skip=10, count=10).json()
        ids_page1 = {item["course_id"] for item in page1}
        ids_page2 = {item["course_id"] for item in page2}
        assert ids_page1.isdisjoint(ids_page2), "페이지 간 course_id 중복 발생"

    def test_count_larger_than_total_returns_actual_count_only(
        self, class_api, total_course_count
    ):
        """count를 실제 개수보다 훨씬 크게 요청해도 실제 등록된 개수만큼만 반환"""
        resp = class_api.get_course_list(skip=0, count=total_course_count + 100)
        data = resp.json()
        assert resp.status_code == 200
        assert len(data) == total_course_count


class TestClassroomCourseListSkipExceedsTotal:
    """TC-1-1-E1: skip이 전체 과목 수와 같거나 초과하는 경우"""

    @pytest.mark.parametrize(
        "skip_offset",
        [0, 80],
        ids=["skip_equal_to_total", "skip_far_exceeds_total"],
    )
    def test_returns_200_with_empty_array(
        self, class_api, total_course_count, skip_offset
    ):
        skip_value = total_course_count + skip_offset
        resp = class_api.get_course_list(skip=skip_value, count=10)
        assert resp.status_code == 200
        data = resp.json()
        assert data == [], f"skip={skip_value} 요청 시 빈 배열이 아님: {data}"