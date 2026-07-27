"""
E-13: 과목 추가 → 조회 → 삭제 해피패스 (풀 라이프사이클 시나리오)

E-12(test_course_bulk_add.py)가 task 상태 전이 자체에 집중한다면, 이 파일은
"사용자가 실제로 겪는 흐름"을 e2e로 검증한다:

    추가 요청 → 완료 대기 → 목록 반영 확인 → 단건 조회로 재확인
    → 삭제 실행 → 삭제 응답 검증 → 단건 조회 404(또는 그에 준하는 코드) 확인
    → 목록에서도 사라졌는지 확인

⚠️ 이 파일이 생기기 전까지 "삭제"는 teardown(track_bulk_added_courses)의 부수 효과로만
   존재했고, 삭제 자체를 검증하는 assertion이 없었다. 그 결과 delete_course 미구현이나
   잘못된 course_id 추적이 있어도 어떤 테스트도 실패하지 않고 강의실에 과목이 계속
   누적되는 사고로 이어졌다. 이 파일의 목적은 "삭제가 실제로 동작한다"를 1급 시민으로
   검증하는 것.

⚠️ completed_bulk_add_task가 반환하는 course_id는 add_courses_bulk에 넘긴
   original_course_ids(BULK_ADD_COURSE_ID)가 아니라, diff로 찾아낸 "실제로 이
   강의실에 새로 생성된 course_id"다. (fixtures/class_fixture.py 참고)
"""

import pytest

from api.schemas.class_schema import ClassSchemas
from fixtures.class_fixture import BULK_ADD_EXPECTED_RESULT
from utils.helpers.api_assertions import assert_valid_schema
from utils.helpers.class_helper import (
    MAX_PAGE_SIZE,
    assert_task_completed,
    wait_until_item_in_list,
    wait_until_item_not_in_list,
)


@pytest.mark.api
@pytest.mark.educator
class TestCourseAddDeleteHappyPath:
    def test_add_view_delete_full_cycle(
        self, educator_class_api, assert_response, completed_bulk_add_task, fetch_course_list
    ):
        _, final, course_id = completed_bulk_add_task
        assert_task_completed(final, expected_result=BULK_ADD_EXPECTED_RESULT)

        wait_until_item_in_list(
            fetch_course_list, match_key="course_id", match_value=course_id
    )
        # --- 4단계: 단건 조회로도 확인 (기존에 teardown 존재확인 용도로만 쓰이던 걸
        #            정식 assertion으로 승격) ---
        get_resp = educator_class_api.get_course(course_id)
        get_data = assert_response(get_resp, 200)
        assert_valid_schema(get_data, ClassSchemas.COURSE_DETAIL_SCHEMA)
        assert get_data["course_id"] == course_id

        # --- 5단계: 삭제 실행 + 응답 자체를 검증 ---
        delete_resp = educator_class_api.delete_course(course_id)
        assert_response(delete_resp, 200)

        # --- 6단계: 삭제 후 단건 조회는 더 이상 200이 아니어야 함 ---
        after_delete_resp = educator_class_api.get_course(course_id)
        assert after_delete_resp.status_code != 200, (
            f"삭제 후에도 course_id={course_id} 단건 조회가 200을 반환합니다. "
            f"실제 삭제 여부를 확인하세요. body={after_delete_resp.text}"
        )

        # --- 7단계: 목록에서도 사라졌는지 확인 ---
        wait_until_item_not_in_list(
            fetch_course_list,
            match_key="course_id",
            match_value=course_id,
        )