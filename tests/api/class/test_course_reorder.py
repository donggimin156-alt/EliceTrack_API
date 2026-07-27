"""
P2 / TC-3-1: 과목 순서 변경 (POST /classroom/{classroom_id}/course/reorder)

✅ 실증 완료(2026-07-27, dev):
   - 정상 요청 시 상태코드 200, 응답 바디는 빈 객체({}). 별도 응답 스키마
     검증 대상 없음 (happy path 테스트는 상태코드 + GET 재조회로 순서
     반영 여부만 검증).
   - **핵심 계약**: course_ids는 "현재 classroom에 존재하는 전체 course_id
     집합과 정확히 일치하는 순열(permutation)"이어야 한다. 하나라도 다르면
     (빈 배열/부분집합/존재하지 않는 id 포함 등 - 원인 무관) 전부 동일하게
     409 `{"code": "invalid_params", "detail": {"course_ids": ["mismatch"]}}`
     로 응답한다. 중복 id만 별도로 `["duplicate"]`로 구분된다.
     → 부분집합을 보내도 "나머지 과목이 사라지거나 밀리는" 위험은 애초에
       없다(서버가 아예 거부함). all_course_ids fixture로 항상 전체 목록을
       보내는 현재 설계가 계약과 정확히 일치한다.
   - 요청 전 course_ids 순서를 반드시 백업해두고, 테스트 후 원래 순서로
     복원해야 함(autouse fixture로 처리).
"""

import pytest

from utils.helpers.class_helper import (
    assert_detail_error,
    assert_model_not_found_error,
)

NONEXISTENT_COURSE_ID = 999999999


@pytest.fixture
def all_course_ids(educator_class_api, assert_response):
    """
    강의실에 있는 전체 과목의 course_id를 순서대로 반환한다.
    (course_data처럼 첫 페이지만 쓰지 않고, get_course_count로 구한 전체
    개수만큼 통째로 조회한다 — 이유는 모듈 docstring 참고)
    """
    count_resp = educator_class_api.get_course_count()
    total = assert_response(count_resp, 200)
    list_resp = educator_class_api.get_course_list(skip=0, count=total)
    data = assert_response(list_resp, 200)
    return [item["course_id"] for item in data]


@pytest.fixture(autouse=True)
def _restore_original_order(educator_class_api, all_course_ids, assert_response):
    """
    재정렬 테스트가 강의실의 실제 과목 순서를 변경하므로,
    각 테스트 종료 후 원래 순서(전체 목록 조회 시점의 순서)로 복원한다.
    """
    original_ids = all_course_ids
    yield
    restore_resp = educator_class_api.reorder_courses(original_ids)
    assert_response(restore_resp, 200)


@pytest.mark.api
@pytest.mark.educator
class TestCourseReorderHappyPath:
    """Happy Path: 정상적인 순서 변경 요청과 실제 반영 여부 확인"""

    def test_reorder_with_same_order_returns_200(
        self, educator_class_api, all_course_ids, assert_response
    ):
        resp = educator_class_api.reorder_courses(all_course_ids)
        assert_response(resp, 200)

    def test_reversed_order_is_reflected_in_list(
        self, educator_class_api, all_course_ids, assert_response
    ):
        """전체 순서를 뒤집어 요청한 뒤, 목록 재조회 시 실제로 뒤집힌 순서로 내려오는지 확인"""
        reversed_ids = list(reversed(all_course_ids))

        reorder_resp = educator_class_api.reorder_courses(reversed_ids)
        assert_response(reorder_resp, 200)

        list_resp = educator_class_api.get_course_list(
            skip=0, count=len(reversed_ids)
        )
        new_data = assert_response(list_resp, 200)
        new_ids = [item["course_id"] for item in new_data]

        assert new_ids == reversed_ids, (
            f"Expected order {reversed_ids} but got {new_ids}"
        )

    def test_single_course_moved_to_front(
        self, educator_class_api, all_course_ids, assert_response
    ):
        """마지막 과목 하나만 맨 앞으로 이동시키는 부분 재배치 시나리오"""
        assert len(all_course_ids) >= 2, "재배치를 검증하려면 과목이 2개 이상 필요합니다"

        moved_id = all_course_ids[-1]
        reordered_ids = [moved_id] + all_course_ids[:-1]

        reorder_resp = educator_class_api.reorder_courses(reordered_ids)
        assert_response(reorder_resp, 200)

        list_resp = educator_class_api.get_course_list(
            skip=0, count=len(reordered_ids)
        )
        new_data = assert_response(list_resp, 200)
        assert [item["course_id"] for item in new_data] == reordered_ids

    def test_reorder_is_idempotent_when_same_order_sent_twice(
        self, educator_class_api, all_course_ids, assert_response
    ):
        first_resp = educator_class_api.reorder_courses(all_course_ids)
        assert_response(first_resp, 200)
        second_resp = educator_class_api.reorder_courses(all_course_ids)
        assert_response(second_resp, 200)

        list_resp = educator_class_api.get_course_list(
            skip=0, count=len(all_course_ids)
        )
        data = assert_response(list_resp, 200)
        assert [item["course_id"] for item in data] == all_course_ids, (
            "동일 순서를 두 번 요청해도 최종 순서는 변하지 않아야 합니다"
        )


@pytest.mark.api
@pytest.mark.educator
class TestCourseReorderValidation:
    """Validation: 잘못된 course_ids 입력에 대한 422 검증"""

    def test_missing_course_ids_returns_422(self, educator_class_api, assert_response):
        resp = educator_class_api.post(
            f"{educator_class_api.course_path.rstrip('/')}/reorder", json={}
        )
        data = assert_response(resp, 422)
        assert_detail_error(
            data, expected_type="missing", expected_loc=["body", "course_ids"]
        )

    def test_non_list_course_ids_returns_422(self, educator_class_api, assert_response):
        resp = educator_class_api.reorder_courses("not-a-list")
        data = assert_response(resp, 422)
        assert_detail_error(
            data, expected_type="list_type", expected_loc=["body", "course_ids"]
        )

    def test_non_integer_items_return_422(self, educator_class_api, assert_response):
        resp = educator_class_api.reorder_courses(["abc", "def"])
        data = assert_response(resp, 422)
        assert_detail_error(
            data,
            expected_type="int_parsing",
            expected_loc=["body", "course_ids", 0],
        )

    def test_empty_course_ids_list_behavior(self, educator_class_api, assert_response):
        """
        실증: course_ids=[]는 "전체 집합과 불일치"로 취급되어 409(mismatch)를
        반환한다. 서버가 빈 배열을 특별 취급(예: 변경 없음으로 간주)하지
        않는다.
        """
        resp = educator_class_api.reorder_courses([])
        data = assert_response(resp, 409)
        assert data["code"] == "invalid_params", (
            f"Expected code='invalid_params' but got {data['code']!r}"
        )
        assert data["detail"]["course_ids"] == ["mismatch"]

    def test_duplicate_course_id_in_list_behavior(
        self, educator_class_api, all_course_ids, assert_response
    ):
        """
        실증: 같은 course_id를 두 번 포함하면, mismatch가 아니라 별도의
        "duplicate" 사유로 409를 반환한다 (서버가 중복 여부를 개수 불일치와
        별개로 명시적으로 구분해서 검사함).
        """
        duplicated_ids = all_course_ids + [all_course_ids[0]]
        resp = educator_class_api.reorder_courses(duplicated_ids)
        data = assert_response(resp, 409)
        assert data["code"] == "invalid_params", (
            f"Expected code='invalid_params' but got {data['code']!r}"
        )
        assert data["detail"]["course_ids"] == ["duplicate"]

    def test_nonexistent_course_id_included_returns_mismatch(
        self, educator_class_api, all_course_ids, assert_response
    ):
        """
        실증: 존재하지 않는 course_id를 섞어서 보내도, 다른 GET 계열
        엔드포인트들의 409(model_not_found/ClassroomCourse)가 아니라
        409(invalid_params, ["mismatch"])로 응답한다. reorder는 개별
        course_id의 존재 여부를 하나씩 조회하는 대신, "전체 집합이 정확히
        일치하는가"만 검사하는 것으로 보인다.
        """
        ids_with_nonexistent = all_course_ids + [NONEXISTENT_COURSE_ID]
        resp = educator_class_api.reorder_courses(ids_with_nonexistent)
        data = assert_response(resp, 409)
        assert data["code"] == "invalid_params", (
            f"Expected code='invalid_params' but got {data['code']!r}"
        )
        assert data["detail"]["course_ids"] == ["mismatch"]

    def test_partial_subset_of_course_ids_returns_mismatch(
        self, educator_class_api, all_course_ids, assert_response
    ):
        """
        실증: 전체 과목 중 일부만 포함한 course_ids로 요청해도 (전체 집합과
        개수/구성이 다르므로) 409(invalid_params, ["mismatch"])를 반환한다.
        즉 reorder는 부분 업데이트를 허용하지 않고, 항상 "현재 존재하는
        전체 course_id의 순열"만 허용한다 — "일부만 보내면 나머지가
        사라지거나 밀리지 않을까" 하는 우려가 애초에 성립하지 않음을
        확인했다(서버가 아예 거부함).
        """
        assert len(all_course_ids) >= 2, "부분집합 검증을 위해 과목이 2개 이상 필요합니다"
        half = max(1, len(all_course_ids) // 2)
        partial_ids = all_course_ids[:half]

        resp = educator_class_api.reorder_courses(partial_ids)
        data = assert_response(resp, 409)
        assert data["code"] == "invalid_params", (
            f"Expected code='invalid_params' but got {data['code']!r}"
        )
        assert data["detail"]["course_ids"] == ["mismatch"]


@pytest.mark.api
@pytest.mark.educator
class TestInvalidClassroomId:
    def test_nonexistent_classroom_id_returns_409(
        self, nonexistent_classroom_api, all_course_ids, assert_response
    ):
        resp = nonexistent_classroom_api.reorder_courses(all_course_ids)
        data = assert_response(resp, 409)
        assert_model_not_found_error(data, model_name="Classroom")

    def test_invalid_uuid_format_returns_422(
        self, invalid_uuid_classroom_api, all_course_ids, assert_response
    ):
        resp = invalid_uuid_classroom_api.reorder_courses(all_course_ids)
        data = assert_response(resp, 422)
        assert_detail_error(
            data, expected_type="uuid_parsing", expected_loc=["path", "classroom_id"]
        )


@pytest.mark.api
@pytest.mark.educator
class TestAuthAndPermission:
    def test_no_token_returns_403(
        self, unauthenticated_class_api, all_course_ids, assert_response
    ):
        resp = unauthenticated_class_api.reorder_courses(all_course_ids)
        data = assert_response(resp, 403)
        assert data["code"] == "no_access_token", (
            f"Expected code='no_access_token' but got {data['code']!r}"
        )

    def test_tampered_token_returns_409(
        self, tampered_token_class_api, all_course_ids, assert_response
    ):
        resp = tampered_token_class_api.reorder_courses(all_course_ids)
        data = assert_response(resp, 409)
        assert data["code"] == "elice_core_unexpected_result", (
            f"Expected code='elice_core_unexpected_result' but got {data['code']!r}"
        )
        assert data["detail"]["resp_json"]["fail_code"] == "no_account_api_session"