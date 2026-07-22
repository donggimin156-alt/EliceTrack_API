"""
E-12: 과목 추가 (POST /v2/classroom/{classroom_id}/course/bulk) — 비동기 task 패턴
실증된 status 전이: queued -> assigned -> completed (완료 후 멱등)
failed 케이스는 미실증 (QA-148 — Postman 확인 후 unskip).

⚠️ 주의: 이 테스트들은 dev 공용 강의실에 실제로 과목을 추가하는 파괴적(destructive) 테스트입니다.
   반복 실행 시 누적/중복 문제가 생길 수 있어 실행 전 팀과 정리 필요합니다.

픽스처(bulk_add_task_id, completed_bulk_add_task)는
fixtures/course_bulk_add_fixture.py에 정의되어 있고, conftest의 pytest_plugins를 통해
자동으로 주입된다. (예: pytest_plugins = ["fixtures.course_bulk_add_fixture", ...])
"""

import pytest

from fixtures.class_fixture import BULK_ADD_COURSE_ID, BULK_ADD_EXPECTED_RESULT
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
    def test_bulk_add_returns_task_id_only(self, bulk_add_task_id):
        task_id = bulk_add_task_id([BULK_ADD_COURSE_ID])
        assert isinstance(task_id, str)

    def test_task_reaches_completed_status(self, completed_bulk_add_task):
        _task_id, final = completed_bulk_add_task
        assert_task_completed(final, expected_result=BULK_ADD_EXPECTED_RESULT)

    def test_completed_task_is_idempotent_on_reread(
        self, educator_class_api, assert_response, completed_bulk_add_task
    ):
        task_id, first_final = completed_bulk_add_task
        resp_again = educator_class_api.get_task(task_id)
        assert assert_response(resp_again, 200) == first_final

    def test_nonexistent_task_id_returns_409(self, educator_class_api, assert_response):
        resp = educator_class_api.get_task("00000000-0000-0000-0000-000000000000")
        data = assert_response(resp, 409)
        assert_model_not_found_error(data)

    def test_added_course_reflected_in_course_list(
        self, educator_class_api, assert_response, completed_bulk_add_task
    ):
        _task_id, _final = completed_bulk_add_task

        def _fetch_course_list():
            resp = educator_class_api.get_course_list(skip=0, count=MAX_PAGE_SIZE)
            return assert_response(resp, 200)

        wait_until_item_in_list(
            _fetch_course_list,
            match_key="course_id",
            match_value=BULK_ADD_COURSE_ID,
        )

    @pytest.mark.skip(reason="QA-148: 실패(failed) 케이스 미실증 — Postman 확인 후 unskip")
    def test_invalid_course_id_task_fails(self, educator_class_api, bulk_add_task_id):
        task_id = bulk_add_task_id([999999999])
        final = wait_until_task_completed(educator_class_api, task_id)
        assert final["status"] == TaskStatus.FAILED, (
            f"Expected status={TaskStatus.FAILED!r} but got {final['status']!r}"
        )

    def test_empty_course_ids_list(self, bulk_add_task_id):
        task_id = bulk_add_task_id([])
        assert isinstance(task_id, str)