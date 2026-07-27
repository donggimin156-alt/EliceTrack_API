"""
P1-01 / TC-1-2: 개별 과목 단건 조회 (GET /classroom/{classroom_id}/course/{course_id})

목록 조회(test_class.py)와 별개로, 단건 조회 자체의 스키마/비즈니스 규칙/
에러 케이스를 전담 검증한다. COURSE_DETAIL_SCHEMA는
test_course_add_delete_happy_path.py에서 이미 실증된 스키마를 재사용한다.
"""

import pytest

from api.schemas.class_schema import ClassSchemas
from core.config import settings
from utils.helpers.api_assertions import assert_valid_schema
from utils.helpers.class_helper import (
    assert_detail_error,
    assert_model_not_found_error,
)

NONEXISTENT_COURSE_ID = 999999999

# course_data[0](목록 첫 항목)을 그대로 쓰면, 다른 테스트 파일이 만들고 지우는
# 임시 과목("과목 추가 테스트용 과목" 등)을 집을 위험이 있다.
# 실제로 pytest 실행 시 course_id=362(임시 생성 후 다른 테스트에서 이미 삭제된
# 과목)가 걸려서 409(model_not_found)로 4개 테스트가 실패한 사례가 있었다.
# test_excel_report.py(E-11)와 동일하게, 삭제되지 않도록 명명된 고정 과목
# (REPORT_ELICE_COURSE_ID, dev 기준 course_id=43, "(1팀 삭제 XX) QA5기 학습과목")
# 을 사용해 이 문제를 피한다.
STABLE_COURSE_ID = settings.elice_environments["dev"]["REPORT_ELICE_COURSE_ID"]


@pytest.fixture
def existing_course_id():
    """다른 테스트의 부수효과로 삭제될 위험이 없는, 고정된 실존 course_id."""
    return STABLE_COURSE_ID


@pytest.mark.api
@pytest.mark.educator
class TestCourseDetailSchema:
    def test_response_matches_detail_schema(
        self, educator_class_api, existing_course_id, assert_response
    ):
        resp = educator_class_api.get_course(existing_course_id)
        data = assert_response(resp, 200)
        assert_valid_schema(data, ClassSchemas.COURSE_DETAIL_SCHEMA)

    def test_course_id_matches_requested_id(
        self, educator_class_api, existing_course_id, assert_response
    ):
        resp = educator_class_api.get_course(existing_course_id)
        data = assert_response(resp, 200)
        assert data["course_id"] == existing_course_id, (
            f"Expected course_id={existing_course_id} but got {data['course_id']}"
        )


@pytest.mark.api
@pytest.mark.educator
class TestCourseDetailBusiness:
    """
    실증 결과(2026-07-27, dev, course_id=362): 단건 조회 응답에는
    목록 조회에만 존재하는 classroom_course_status / classroom_course_progress_data
    / pass_info 필드가 내려오지 않는다. 따라서 progress/completed_material_cnt
    관련 비즈니스 검증은 이 파일이 아니라 목록 조회(test_class.py)에서만
    성립한다. 이 사실 자체를 회귀 테스트로 고정해둔다.
    """

    def test_progress_data_not_present_in_detail_response(
        self, educator_class_api, existing_course_id, assert_response
    ):
        """
        단건 조회 응답에는 classroom_course_progress_data가 없다는 것을
        고정(lock-in)한다. 추후 API가 이 필드를 단건 응답에도 포함하도록
        바뀌면 이 테스트가 실패하며 변경을 알려준다 - 그때 progress 관련
        비즈니스 검증을 이 클래스에 다시 추가할 것.
        """
        resp = educator_class_api.get_course(existing_course_id)
        data = assert_response(resp, 200)
        assert "classroom_course_progress_data" not in data, (
            "단건 조회 응답에 classroom_course_progress_data가 추가된 것으로 "
            "보입니다. progress 관련 비즈니스 검증 테스트를 복원하세요."
        )
        assert "classroom_course_status" not in data
        assert "pass_info" not in data

    def test_detail_matches_corresponding_list_item(
        self, educator_class_api, existing_course_id, assert_response
    ):
        """
        단건 조회 결과가 목록 조회 결과와 title 기준으로 일치하는지 (데이터 정합성).

        실증 결과: course_data fixture(첫 페이지, DEFAULT_PAGE_SIZE 제한)만으로
        찾으면 StopIteration이 발생할 수 있었다 — 다른 bulk add 테스트들이
        계속 새 과목을 만들어내면서 전체 목록이 커지는 중이라, STABLE_COURSE_ID가
        항상 첫 페이지 안에 있으리라는 보장이 없다. 그래서 이 테스트는
        course_data를 쓰지 않고, get_course_count로 전체 개수를 구해 목록
        전체를 한 번에 조회한 뒤 찾는다 (test_course_add_delete_happy_path.py의
        _fetch_course_list와 동일한 패턴).
        """
        resp = educator_class_api.get_course(existing_course_id)
        detail = assert_response(resp, 200)

        count_resp = educator_class_api.get_course_count()
        total = assert_response(count_resp, 200)
        list_resp = educator_class_api.get_course_list(skip=0, count=total)
        full_list = assert_response(list_resp, 200)

        list_item = next(
            (item for item in full_list if item["course_id"] == existing_course_id),
            None,
        )
        assert list_item is not None, (
            f"목록 전체({total}건)에서 course_id={existing_course_id}를 "
            "찾지 못했습니다. STABLE_COURSE_ID 설정이 유효한지 확인하세요."
        )
        assert detail["title"] == list_item["title"], (
            f"목록의 title({list_item['title']!r})과 단건 조회 title"
            f"({detail['title']!r})이 다릅니다"
        )


@pytest.mark.api
@pytest.mark.educator
class TestCourseDetailValidation:
    def test_nonexistent_course_id_returns_409(
        self, educator_class_api, assert_response
    ):
        """
        실증(2026-07-27, dev): detail 키가 "Classroom"이 아니라
        "ClassroomCourse"로 내려온다. classroom_id 자체가 아니라
        classroom 내부의 course를 못 찾은 것이므로 모델명이 다르다.
        """
        resp = educator_class_api.get_course(NONEXISTENT_COURSE_ID)
        data = assert_response(resp, 409)
        assert_model_not_found_error(data, model_name="ClassroomCourse")

    def test_non_integer_course_id_returns_422(
        self, educator_class_api, assert_response
    ):
        resp = educator_class_api.get(
            f"{educator_class_api.course_path.rstrip('/')}/abc"
        )
        data = assert_response(resp, 422)
        assert_detail_error(
            data, expected_type="int_parsing", expected_loc=["path", "course_id"]
        )


@pytest.mark.api
@pytest.mark.educator
class TestInvalidClassroomId:
    def test_nonexistent_classroom_id_returns_409(
        self, nonexistent_classroom_api, existing_course_id, assert_response
    ):
        resp = nonexistent_classroom_api.get_course(existing_course_id)
        data = assert_response(resp, 409)
        assert_model_not_found_error(data, model_name="Classroom")

    def test_invalid_uuid_format_returns_422(
        self, invalid_uuid_classroom_api, existing_course_id, assert_response
    ):
        resp = invalid_uuid_classroom_api.get_course(existing_course_id)
        data = assert_response(resp, 422)
        assert_detail_error(
            data, expected_type="uuid_parsing", expected_loc=["path", "classroom_id"]
        )


@pytest.mark.api
@pytest.mark.educator
class TestAuthAndPermission:
    def test_no_token_returns_403(
        self, unauthenticated_class_api, existing_course_id, assert_response
    ):
        resp = unauthenticated_class_api.get_course(existing_course_id)
        data = assert_response(resp, 403)
        assert data["code"] == "no_access_token", (
            f"Expected code='no_access_token' but got {data['code']!r}"
        )

    def test_tampered_token_returns_409(
        self, tampered_token_class_api, existing_course_id, assert_response
    ):
        resp = tampered_token_class_api.get_course(existing_course_id)
        data = assert_response(resp, 409)
        assert data["code"] == "elice_core_unexpected_result", (
            f"Expected code='elice_core_unexpected_result' but got {data['code']!r}"
        )
        assert data["detail"]["resp_json"]["fail_code"] == "no_account_api_session"

