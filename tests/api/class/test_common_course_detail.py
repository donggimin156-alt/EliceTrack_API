"""
test_common_course_detail.py

get_course 단건 조회 — 교육자(dev)/학습자(prod) 공통 검증을 파라미터라이즈로 통합.

⚠️ course_data/course_list fixture는 class_api(prod 학습자)에 고정되어 있어
   educator 케이스에서 재사용하면 dev/prod 데이터가 섞인다. 따라서 이 파일은
   course_data를 재사용하지 않고, role별 client로 직접 get_course_list를
   호출해 목록을 가져온다.

⚠️ 기존 test_course_detail.py / test_student_ui.py 의 아래 두 테스트와 내용이
   겹쳐서 이 파일로 옮기고 원본에서는 제거한다:
   - 스키마 검증 (COURSE_DETAIL_SCHEMA)
   - 목록↔상세 course_id/title 일치 검증
"""
import os

import pytest

from api.schemas.class_schema import ClassSchemas
from core.config import settings
from utils.helpers.api_assertions import assert_valid_schema
from utils.helpers.class_helper import DEFAULT_PAGE_SIZE

PROD_ENV = settings.elice_environments["prod"]
LEARNER_ACCOUNT_ID = os.getenv("PROD_LEARNER_ACCOUNT_ID") or PROD_ENV.get("LEARNER_ACCOUNT_ID")


@pytest.fixture(
    params=[
        pytest.param("educator", marks=pytest.mark.educator, id="educator"),
        pytest.param("learner", marks=pytest.mark.learner, id="learner"),
    ]
)
def course_client_and_data(request, assert_response):
    """role에 따라 실제 API client를 선택하고, 그 client로 직접 목록을 조회해 반환."""
    role = request.param

    if role == "learner" and not LEARNER_ACCOUNT_ID:
        pytest.skip("PROD_LEARNER_ACCOUNT_ID not set; skipping learner case")

    client_fixture_name = "educator_class_api" if role == "educator" else "class_api"
    api = request.getfixturevalue(client_fixture_name)

    resp = api.get_course_list(skip=0, count=DEFAULT_PAGE_SIZE)
    course_data = assert_response(resp, 200)
    assert course_data, f"[{role}] 조회할 과목이 없습니다."

    return api, course_data


@pytest.mark.api
class TestCourseDetailCommon:
    """get_course 단건 조회 — 교육자/학습자 동일 동작 보장"""

    def test_course_detail_returns_valid_schema(
        self, course_client_and_data, assert_response
    ):
        api, course_data = course_client_and_data
        course_id = course_data[0]["course_id"]

        resp = api.get_course(course_id)
        data = assert_response(resp, 200)
        assert_valid_schema(data, ClassSchemas.COURSE_DETAIL_SCHEMA)

    def test_course_detail_matches_list_item(
        self, course_client_and_data, assert_response
    ):
        api, course_data = course_client_and_data
        list_item = course_data[0]
        course_id = list_item["course_id"]

        resp = api.get_course(course_id)
        detail = assert_response(resp, 200)

        assert detail["course_id"] == course_id, (
            f"Expected course_id={course_id} but got {detail['course_id']}"
        )
        assert detail.get("title") == list_item.get("title"), (
            f"목록 title={list_item.get('title')!r} 과 상세 title="
            f"{detail.get('title')!r} 이 일치해야 합니다."
        )