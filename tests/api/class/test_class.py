"""
TC-1-1 v2: 학습 과목 목록 조회 (GET /classroom/{classroom_id}/course)

이 파일은 현재 리팩토링된 테스트 구조를 별도 v2 구현으로 보관한 버전입니다.
기존 test_class.py와 동일한 검증 의미를 유지하면서, 구조를 분리해 두었습니다.
"""

from datetime import datetime

import pytest
from jsonschema import validate

from api.schemas.class_schema import ClassSchemas


def parse_iso_datetime(value: str | None) -> datetime:
    """ISO 8601 문자열을 datetime으로 파싱한다. Z 접미사와 빈 값도 안전하게 처리한다."""
    if not value:
        raise AssertionError("datetime 값이 비어 있습니다.")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def assert_detail_error(data, expected_type, expected_loc, ctx_key=None, ctx_value=None):
    """detail 배열 안에서 조건에 맞는 에러 항목이 하나인지 검증한다."""
    detail = data.get("detail", [])
    matches = [
        d for d in detail
        if d.get("type") == expected_type and d.get("loc") == expected_loc
    ]
    assert len(matches) == 1, (
        f"조건에 맞는 에러 항목이 1개가 아님: type={expected_type}, "
        f"loc={expected_loc}, detail={detail}"
    )

    match = matches[0]
    if ctx_key is not None:
        ctx = match.get("ctx", {})
        assert ctx_key in ctx, f"ctx에 {ctx_key}가 없음: {match}"
        assert ctx[ctx_key] == ctx_value, (
            f"ctx[{ctx_key}] 불일치: expected={ctx_value}, actual={ctx[ctx_key]}"
        )


# ===========================================================================
# 1. Happy Path
# ===========================================================================
class TestClassroomCourseListSchema:
    """1. Response Schema Validation: 최상위 응답 형태 + 필드 존재 여부만 검사"""

    def test_response_is_array(self, course_data):
        assert isinstance(course_data, list)

    def test_response_within_count_bound(self, course_data):
        assert 0 <= len(course_data) <= 10

    def test_each_item_matches_top_level_schema(self, course_data):
        for item in course_data:
            validate(instance=item, schema=ClassSchemas.COURSE_TOP_LEVEL_SCHEMA)


class TestClassroomCourseListNestedSchema:
    """2. Nested Schema Validation: classroom_course_progress_data 내부만 검사"""

    def test_progress_data_matches_schema(self, course_data):
        for item in course_data:
            progress_data = item["classroom_course_progress_data"]
            validate(instance=progress_data, schema=ClassSchemas.PROGRESS_DATA_SCHEMA)


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
            created = parse_iso_datetime(item["created"])
            modified = parse_iso_datetime(item["modified"])
            assert created <= modified, (
                f"created가 modified보다 이후임: course_id={item.get('course_id')}"
            )

    def test_course_id_is_unique(self, full_course_data):
        course_ids = [item["course_id"] for item in full_course_data]
        assert len(course_ids) == len(set(course_ids)), "course_id 중복 발생"

    def test_required_business_fields_exist(self, full_course_data):
        for item in full_course_data:
            assert item.get("title"), f"title이 비어 있음: course_id={item.get('course_id')}"
            assert item.get("created"), f"created가 비어 있음: course_id={item.get('course_id')}"
            assert item.get("modified"), f"modified가 비어 있음: course_id={item.get('course_id')}"

    def test_pagination_no_duplicate_between_pages(
        self, course_data, class_api, assert_response
    ):
        """
        skip=0/10 두 페이지 간 course_id 중복이 없는지 확인.
        page1은 이미 skip=0, count=10으로 조회해둔 course_data 픽스처를 재사용하고,
        page2만 새로 요청한다.
        """
        page2_resp = class_api.get_course_list(skip=10, count=10)
        page2 = assert_response(page2_resp, 200)
        ids_page1 = {item["course_id"] for item in course_data}
        ids_page2 = {item["course_id"] for item in page2}
        assert ids_page1.isdisjoint(ids_page2), "페이지 간 course_id 중복 발생"

    def test_count_larger_than_total_returns_actual_count_only(
        self, class_api, total_course_count, assert_response
    ):
        """count를 실제 개수보다 훨씬 크게 요청해도 실제 등록된 개수만큼만 반환"""
        resp = class_api.get_course_list(skip=0, count=total_course_count + 100)
        data = assert_response(resp, 200)
        assert len(data) == total_course_count


class TestPaginationAndEdgeBehavior:
    """skip이 전체 과목 수와 같거나 초과하는 경우"""

    @pytest.mark.parametrize(
        "skip_offset",
        [0, 80],
        ids=["skip_equal_to_total", "skip_far_exceeds_total"],
    )
    def test_returns_200_with_empty_array(
        self, class_api, total_course_count, assert_response, skip_offset
    ):
        skip_value = total_course_count + skip_offset
        resp = class_api.get_course_list(skip=skip_value, count=10)
        data = assert_response(resp, 200)
        assert data == [], f"skip={skip_value} 요청 시 빈 배열이 아님: {data}"


# ===========================================================================
# 2. Edge Cases (E2~E11)
# ===========================================================================
class TestValidationErrors:
    def test_count_zero_returns_422(self, class_api, assert_response):
        resp = class_api.get_course_list(skip=0, count=0)
        data = assert_response(resp, 422)
        assert_detail_error(
            data,
            expected_type="greater_than_equal",
            expected_loc=["query", "count"],
            ctx_key="ge",
            ctx_value=1,
        )

    @pytest.mark.parametrize(
        "skip, count, expected_errors",
        [
            pytest.param(-1, 10, [(["query", "skip"], 0)], id="skip_negative"),
            pytest.param(0, -5, [(["query", "count"], 1)], id="count_negative"),
            pytest.param(
                -1,
                -5,
                [(["query", "skip"], 0), (["query", "count"], 1)],
                id="both_negative",
            ),
        ],
    )
    def test_negative_values_return_422(
        self, class_api, assert_response, skip, count, expected_errors
    ):
        resp = class_api.get_course_list(skip=skip, count=count)
        data = assert_response(resp, 422)
        assert len(data["detail"]) == len(expected_errors)
        for expected_loc, expected_ge in expected_errors:
            assert_detail_error(
                data, "greater_than_equal", expected_loc, "ge", expected_ge
            )

    def test_non_integer_skip_and_count_returns_422(self, class_api, assert_response):
        resp = class_api.get_course_list(skip="abc", count="xyz")
        data = assert_response(resp, 422)
        assert len(data["detail"]) == 2
        assert_detail_error(data, "int_parsing", ["query", "skip"])
        assert_detail_error(data, "int_parsing", ["query", "count"])
        for d in data["detail"]:
            assert "ctx" not in d

    def test_missing_skip_and_count_returns_422(self, class_api, assert_response):
        resp = class_api.get(class_api.course_path)
        data = assert_response(resp, 422)
        assert len(data["detail"]) == 2
        assert_detail_error(data, "missing", ["query", "skip"])
        assert_detail_error(data, "missing", ["query", "count"])


class TestInvalidClassroomId:
    def test_nonexistent_classroom_id_returns_409(
        self, nonexistent_classroom_api, assert_response
    ):
        resp = nonexistent_classroom_api.get_course_list(skip=0, count=10)
        data = assert_response(resp, 409)
        assert data["code"] == "model_not_found"
        assert "Classroom" in data["detail"]
        assert "id" in data["detail"]["Classroom"]

    def test_invalid_uuid_format_returns_422(
        self, invalid_uuid_classroom_api, assert_response
    ):
        resp = invalid_uuid_classroom_api.get_course_list(skip=0, count=10)
        data = assert_response(resp, 422)
        assert_detail_error(
            data, expected_type="uuid_parsing", expected_loc=["path", "classroom_id"]
        )


class TestAuthAndPermission:
    def test_no_token_returns_403(self, unauthenticated_class_api, assert_response):
        resp = unauthenticated_class_api.get_course_list(skip=0, count=10)
        data = assert_response(resp, 403)
        assert data["code"] == "no_access_token"

    def test_tampered_token_returns_409(self, tampered_token_class_api, assert_response):
        resp = tampered_token_class_api.get_course_list(skip=0, count=10)
        data = assert_response(resp, 409)
        assert data["code"] == "elice_core_unexpected_result"
        assert data["detail"]["resp_json"]["fail_code"] == "no_account_api_session"

    def test_other_authorized_account_returns_200(
        self, other_account_class_api, assert_response
    ):
        """같은 classroom에 접근 권한이 있는 다른 계정 토큰으로도 정상 조회되는지 (sanity check)"""
        resp = other_account_class_api.get_course_list(skip=0, count=10)
        data = assert_response(resp, 200)
        assert isinstance(data, list)
