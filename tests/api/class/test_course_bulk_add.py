"""
E-12: 과목 추가 (POST /v2/classroom/{classroom_id}/course/bulk) — 비동기 task 패턴
⚠️ 교육자 dev 고정. 실증된 status 전이: queued -> assigned -> completed (완료 후 멱등)
   failed 케이스는 미실증 (E-12e, skip 처리).

⚠️ 주의: 이 테스트들은 dev 공용 강의실에 실제로 과목을 추가하는 파괴적(destructive) 테스트입니다.
   반복 실행 시 누적/중복 문제가 생길 수 있어 실행 전 팀과 정리 필요합니다 (하단 피드백 참고).
"""

import time

import pytest
from jsonschema import validate

from api.schemas.class_schema import ClassSchemas
from core.config import settings

BULK_ADD_COURSE_ID = settings.elice_environments["dev"]["BULK_ADD_COURSE_ID"]


@pytest.mark.api
@pytest.mark.educator
class TestCourseBulkAddTaskLifecycle:
    def _submit_bulk_add(self, educator_class_api, assert_response, course_ids):
        resp = educator_class_api.add_courses_bulk(course_ids)
        data = assert_response(resp, 200)
        assert set(data.keys()) == {"task_id"}
        assert isinstance(data["task_id"], str) and data["task_id"]
        return data["task_id"]

    def _assert_task_completed(self, educator_class_api, task_id, wait_for_task_completion):
        final = wait_for_task_completion(educator_class_api, task_id)
        validate(instance=final, schema=ClassSchemas.TASK_SCHEMA)
        assert final["status"] == "completed"
        assert final["result"] == {"course_attached": "completed"}
        return final

    def _wait_for_course_in_list(self, educator_class_api, assert_response, course_id):
        for _ in range(15):
            list_resp = educator_class_api.get_course_list(skip=0, count=9999)
            course_list = assert_response(list_resp, 200)
            if any(item["course_id"] == course_id for item in course_list):
                return course_list
            time.sleep(settings.api_timeout_sec)

        raise AssertionError(f"course_id={course_id}가 목록에 반영되지 않았습니다.")

    def test_E12_bulk_add_returns_task_id_only(self, educator_class_api, assert_response):
        task_id = self._submit_bulk_add(educator_class_api, assert_response, [BULK_ADD_COURSE_ID])
        assert isinstance(task_id, str)

    def test_E12a_task_reaches_completed_status(
        self, educator_class_api, assert_response, wait_for_task_completion
    ):
        task_id = self._submit_bulk_add(educator_class_api, assert_response, [BULK_ADD_COURSE_ID])
        self._assert_task_completed(educator_class_api, task_id, wait_for_task_completion)

    def test_E12a4_completed_task_is_idempotent_on_reread(
        self, educator_class_api, assert_response, wait_for_task_completion
    ):
        task_id = self._submit_bulk_add(educator_class_api, assert_response, [BULK_ADD_COURSE_ID])
        first_final = self._assert_task_completed(educator_class_api, task_id, wait_for_task_completion)

        resp_again = educator_class_api.get_task(task_id)
        assert assert_response(resp_again, 200) == first_final

    def test_E12c_nonexistent_task_id_returns_409(self, educator_class_api, assert_response):
        resp = educator_class_api.get_task("00000000-0000-0000-0000-000000000000")
        # 서버는 존재하지 않는 Task에 대해 409(model_not_found)을 반환합니다.
        # 저장소 관례에 맞춰 409 및 에러 코드를 확인합니다.
        assert resp.status_code == 409
        data = resp.json()
        assert data.get("code") == "model_not_found"

    def test_E12b_added_course_reflected_in_course_list(
        self, educator_class_api, assert_response, wait_for_task_completion
    ):
        task_id = self._submit_bulk_add(educator_class_api, assert_response, [BULK_ADD_COURSE_ID])
        final_task = self._assert_task_completed(educator_class_api, task_id, wait_for_task_completion)

        self._wait_for_course_in_list(educator_class_api, assert_response, BULK_ADD_COURSE_ID)
        assert final_task["status"] == "completed"
        assert final_task.get("result") == {"course_attached": "completed"}

    @pytest.mark.skip(reason="E-12e: 실패(failed) 케이스 미실증 — Postman 확인 후 unskip")
    def test_E12e_invalid_course_id_task_fails(
        self, educator_class_api, assert_response, wait_for_task_completion
    ):
        task_id = self._submit_bulk_add(educator_class_api, assert_response, [999999999])
        final = wait_for_task_completion(educator_class_api, task_id)
        assert final["status"] == "failed"

    def test_E12f_empty_course_ids_list(self, educator_class_api, assert_response):
        task_id = self._submit_bulk_add(educator_class_api, assert_response, [])
        assert isinstance(task_id, str)