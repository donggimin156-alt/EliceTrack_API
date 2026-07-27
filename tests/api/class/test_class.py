"""
TC-1-1 v2: 학습 과목 목록 조회 (GET /classroom/{classroom_id}/course)
"""

import pytest

from api.schemas.class_schema import ClassSchemas
from utils.helpers.api_assertions import assert_valid_schema
from utils.helpers.class_helper import (
    DEFAULT_PAGE_SIZE,
    assert_detail_error,
    assert_model_not_found_error,
    parse_iso_datetime,
)


class TestClassroomCourseListSchema:
    """Response Schema Validation: 최상위 응답 형태 + 필드 존재 여부만 검사"""

    def test_response_is_array(self, course_data):
        """응답 데이터가 리스트(Array) 형태인지 검증한다."""
        assert isinstance(course_data, list)

    def test_response_within_count_bound(self, course_data):
        """응답 개수가 설정된 페이지 크기(DEFAULT_PAGE_SIZE) 범위 내인지 검증한다."""
        assert 0 <= len(course_data) <= DEFAULT_PAGE_SIZE

    def test_each_item_matches_top_level_schema(self, course_data):
        """응답 리스트의 각 아이템이 최상위 스키마 규격을 만족하는지 검증한다."""
        for item in course_data:
            assert_valid_schema(item, ClassSchemas.COURSE_TOP_LEVEL_SCHEMA)


class TestClassroomCourseListNestedSchema:
    """Nested Schema Validation: classroom_course_progress_data 내부만 검사"""

    def test_progress_data_matches_schema(self, course_data):
        """중첩된 진척도 데이터가 지정된 세부 스키마 규격을 만족하는지 검증한다."""
        for item in course_data:
            progress_data = item["classroom_course_progress_data"]
            assert_valid_schema(progress_data, ClassSchemas.PROGRESS_DATA_SCHEMA)


class TestClassroomCourseListBusiness:
    """Business Validation: 스키마가 아닌 비즈니스 규칙 검사"""

    def test_at_least_one_course_exists(self, course_data):
        """최소 1개 이상의 과목이 존재하는지 비즈니스 규칙을 검증한다."""
        assert len(course_data) > 0, "Expected at least 1 course but got 0"

    def test_progress_value_range(self, full_course_data):
        """진척도(progress) 값이 0에서 100 사이의 유효한 퍼센트 범위 내에 있는지 검증한다."""
        for item in full_course_data:
            progress = item["classroom_course_progress_data"]["progress"]
            assert 0 <= progress <= 100, f"Expected 0<=progress<=100 but got {progress}"

    def test_completed_not_exceed_total_material(self, full_course_data):
        """완료된 학습 자료 수가 전체 학습 자료 수를 초과하지 않는지 검증한다."""
        for item in full_course_data:
            pd = item["classroom_course_progress_data"]
            completed, total = pd["completed_material_cnt"], pd["total_material_cnt"]
            assert completed <= total, (
                f"completed_material_cnt({completed}) > total_material_cnt({total}) "
                f"course_id={item.get('course_id')}"
            )

    def test_created_not_after_modified(self, full_course_data):
        """생성일이 수정일보다 이후가 아닌지 datetime 객체로 변환하여 비교 검증한다."""
        for item in full_course_data:
            created = parse_iso_datetime(item["created"])
            modified = parse_iso_datetime(item["modified"])
            assert created <= modified, (
                f"Expected created<=modified but got created={created}, "
                f"modified={modified} (course_id={item.get('course_id')})"
            )

    def test_course_id_is_unique(self, full_course_data):
        """과목 ID(course_id)가 중복 없이 고유한 값인지 검증한다."""
        course_ids = [item["course_id"] for item in full_course_data]
        duplicates = {cid for cid in course_ids if course_ids.count(cid) > 1}
        assert not duplicates, f"Expected unique course_id but found duplicates: {duplicates}"

    def test_required_business_fields_exist(self, full_course_data):
        """필수 비즈니스 필드들이 누락되지 않고 유효하게 존재하는지 검증한다."""
        for item in full_course_data:
            for field in ("title", "created", "modified"):
                assert item.get(field), (
                    f"Expected non-empty '{field}' but got {item.get(field)!r} "
                    f"(course_id={item.get('course_id')})"
                )


class TestPagination:
    """페이지네이션 관련 동작 검증 (skip/count 조합 별 실제 응답)"""

    def test_no_duplicate_between_pages(self, course_data, class_api, assert_response):
        """
        skip=0과 DEFAULT_PAGE_SIZE 페이지 간 course_id 중복이 없는지 확인한다.
        page1은 이미 조회된 course_data 픽스처를 재사용하고, page2만 새로 요청하여 교집합을 검증한다.
        """
        page2_resp = class_api.get_course_list(skip=DEFAULT_PAGE_SIZE, count=DEFAULT_PAGE_SIZE)
        page2 = assert_response(page2_resp, 200)
        ids_page1 = {item["course_id"] for item in course_data}
        ids_page2 = {item["course_id"] for item in page2}
        assert ids_page1.isdisjoint(ids_page2), (
            f"Expected no overlapping course_id between pages but found "
            f"{ids_page1 & ids_page2}"
        )

    def test_count_larger_than_total_returns_actual_count_only(
        self, class_api, total_course_count, assert_response
    ):
        """count를 실제 총 개수보다 훨씬 크게 요청해도 실제 등록된 개수만큼만 반환되는지 검증한다."""
        resp = class_api.get_course_list(skip=0, count=total_course_count + 100)
        data = assert_response(resp, 200)
        assert len(data) == total_course_count, (
            f"Expected {total_course_count} items but got {len(data)}"
        )

    @pytest.mark.parametrize(
        "skip_offset",
        [0, 80],
        ids=["skip_equal_to_total", "skip_far_exceeds_total"],
    )
    def test_skip_beyond_total_returns_empty_array(
        self, class_api, total_course_count, assert_response, skip_offset
    ):
        """skip 값이 전체 데이터 개수를 초과할 경우 빈 배열([])이 반환되는지 검증한다."""
        skip_value = total_course_count + skip_offset
        resp = class_api.get_course_list(skip=skip_value, count=DEFAULT_PAGE_SIZE)
        data = assert_response(resp, 200)
        assert data == [], f"Expected empty array for skip={skip_value} but got {data}"


class TestValidationErrors:
    def test_count_zero_returns_422(self, class_api, assert_response):
        """count 파라미터가 0일 때 422 에러와 함께 올바른 제약 조건 오류 메시지가 반환되는지 검증한다."""
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
        """skip이나 count에 음수 값을 전달했을 때 422 에러가 발생하는지 검증한다."""
        resp = class_api.get_course_list(skip=skip, count=count)
        data = assert_response(resp, 422)
        assert len(data["detail"]) == len(expected_errors), (
            f"Expected {len(expected_errors)} error(s) but got "
            f"{len(data['detail'])}: {data['detail']}"
        )
        for expected_loc, expected_ge in expected_errors:
            assert_detail_error(
                data, "greater_than_equal", expected_loc, "ge", expected_ge
            )

    def test_non_integer_skip_and_count_returns_422(self, class_api, assert_response):
        """skip과 count에 정수가 아닌 문자열 값을 전달했을 때 422 타입 파싱 에러가 발생하는지 검증한다."""
        resp = class_api.get_course_list(skip="abc", count="xyz")
        data = assert_response(resp, 422)
        assert len(data["detail"]) == 2, f"Expected 2 errors but got {data['detail']}"
        assert_detail_error(data, "int_parsing", ["query", "skip"])
        assert_detail_error(data, "int_parsing", ["query", "count"])
        for d in data["detail"]:
            assert "ctx" not in d, f"Expected no 'ctx' key but found one in {d}"

    def test_missing_skip_and_count_returns_422(self, class_api, assert_response):
        """필수 쿼리 파라미터인 skip과 count가 누락되었을 때 422 필수값 누락 에러가 발생하는지 검증한다."""
        resp = class_api.get(class_api.course_path)
        data = assert_response(resp, 422)
        assert len(data["detail"]) == 2, f"Expected 2 errors but got {data['detail']}"
        assert_detail_error(data, "missing", ["query", "skip"])
        assert_detail_error(data, "missing", ["query", "count"])


class TestInvalidClassroomId:
    def test_nonexistent_classroom_id_returns_409(
        self, nonexistent_classroom_api, assert_response
    ):
        """존재하지 않는 classroom_id로 조회 요청 시 409 Conflict 에러와 모델 미발견 메시지가 반환되는지 검증한다."""
        resp = nonexistent_classroom_api.get_course_list(skip=0, count=DEFAULT_PAGE_SIZE)
        data = assert_response(resp, 409)
        assert_model_not_found_error(data, model_name="Classroom")
        assert "id" in data["detail"]["Classroom"], (
            f"Expected detail.Classroom to contain 'id' but got {data['detail']['Classroom']}"
        )

    def test_invalid_uuid_format_returns_422(
        self, invalid_uuid_classroom_api, assert_response
    ):
        """잘못된 UUID 형식의 classroom_id로 요청 시 422 UUID 파싱 에러가 발생하는지 검증한다."""
        resp = invalid_uuid_classroom_api.get_course_list(skip=0, count=DEFAULT_PAGE_SIZE)
        data = assert_response(resp, 422)
        assert_detail_error(
            data, expected_type="uuid_parsing", expected_loc=["path", "classroom_id"]
        )


class TestAuthAndPermission:
    def test_no_token_returns_403(self, unauthenticated_class_api, assert_response):
        """인증 토큰이 없는 상태로 요청 시 403 Forbidden 및 no_access_token 코드가 반환되는지 검증한다."""
        resp = unauthenticated_class_api.get_course_list(skip=0, count=DEFAULT_PAGE_SIZE)
        data = assert_response(resp, 403)
        assert data["code"] == "no_access_token", (
            f"Expected code='no_access_token' but got {data['code']!r}"
        )

    def test_tampered_token_returns_409(self, tampered_token_class_api, assert_response):
        """변조된 인증 토큰으로 요청 시 409 에러와 관련 세션 에러 코드가 반환되는지 검증한다."""
        resp = tampered_token_class_api.get_course_list(skip=0, count=DEFAULT_PAGE_SIZE)
        data = assert_response(resp, 409)
        assert data["code"] == "elice_core_unexpected_result", (
            f"Expected code='elice_core_unexpected_result' but got {data['code']!r}"
        )
        assert data["detail"]["resp_json"]["fail_code"] == "no_account_api_session"

