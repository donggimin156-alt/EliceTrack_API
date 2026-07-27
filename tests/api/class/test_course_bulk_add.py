"""
E-12: 과목 추가 (POST /v2/classroom/{classroom_id}/course/bulk) — 비동기 task 패턴
  - queued -> assigned -> completed (완료 후 멱등)
  - queued -> assigned -> failed (존재하지 않는 course template id인 경우, result=null)

⚠️ original_course_ids로 넘기는 값(예: BULK_ADD_COURSE_ID=17)은 과목 "템플릿" id이며,
   실제로 이 강의실에 생성되는 course_id와는 다른 값이다. completed_bulk_add_task가
   diff로 실제 added_course_id를 찾아 (task_id, final, added_course_id) 3-튜플로
   반환하니, 목록/단건 조회 검증에는 반드시 added_course_id를 사용할 것
   (BULK_ADD_COURSE_ID로 조회하면 항상 실패한다 — 409 model_not_found).
"""

import pytest

from api.schemas.class_schema import ClassSchemas
from fixtures.class_fixture import BULK_ADD_COURSE_ID, BULK_ADD_EXPECTED_RESULT
from utils.helpers.api_assertions import assert_valid_schema
from utils.helpers.class_helper import (
    MAX_PAGE_SIZE,
    TaskStatus,
    assert_model_not_found_error,
    assert_task_completed,
    wait_until_item_in_list,
    wait_until_task_completed,
)


@pytest.mark.api
@pytest.mark.educator
class TestCourseBulkAddTaskLifecycle:
    def test_bulk_add_returns_task_id_only(
        self, educator_class_api, bulk_add_task_id
    ):
        task_id = bulk_add_task_id([BULK_ADD_COURSE_ID])
        assert isinstance(task_id, str)
        final = wait_until_task_completed(educator_class_api, task_id)
        assert_task_completed(final, expected_result=BULK_ADD_EXPECTED_RESULT)

    def test_task_reaches_completed_status(self, completed_bulk_add_task):
        _task_id, final, _added_course_id = completed_bulk_add_task
        assert_task_completed(final, expected_result=BULK_ADD_EXPECTED_RESULT)

    def test_completed_task_is_idempotent_on_reread(
        self, educator_class_api, assert_response, completed_bulk_add_task
    ):
        task_id, first_final, _added_course_id = completed_bulk_add_task
        resp_again = educator_class_api.get_task(task_id)
        assert assert_response(resp_again, 200) == first_final

    def test_nonexistent_task_id_returns_409(self, educator_class_api, assert_response):
        resp = educator_class_api.get_task("00000000-0000-0000-0000-000000000000")
        data = assert_response(resp, 409)
        assert_model_not_found_error(data)

    def test_added_course_reflected_in_course_list(
        self, completed_bulk_add_task, fetch_course_list
    ):
        _, _, added_course_id = completed_bulk_add_task

        items = wait_until_item_in_list(
            fetch_course_list,
            match_key="course_id",
            match_value=added_course_id,
        )
        item = next(i for i in items if i["course_id"] == added_course_id)
        assert_valid_schema(item, ClassSchemas.COURSE_LIST_ITEM_SCHEMA)


    def test_invalid_course_id_task_fails(self, educator_class_api, bulk_add_task_id):
        task_id = bulk_add_task_id([999999999])
        final = wait_until_task_completed(educator_class_api, task_id)
        assert final["status"] == TaskStatus.FAILED, (
            f"Expected status={TaskStatus.FAILED!r} but got {final['status']!r}"
        )
        assert final["result"] is None, (
            f"Expected result=None but got {final['result']!r}"
        )

    def test_empty_course_ids_list(self, bulk_add_task_id):
        task_id = bulk_add_task_id([])
        assert isinstance(task_id, str)