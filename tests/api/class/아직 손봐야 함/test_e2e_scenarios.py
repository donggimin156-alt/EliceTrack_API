"""
E2E 시나리오 통합

- E2E-1: 과목 추가 → 순서 변경 → 클래스에서 제거
- E2E-2~5: UI 단독 동작이거나, 의존 API 미실증으로 스텁 정의 유지
"""

import pytest
from fixtures.class_fixture import BULK_ADD_EXPECTED_RESULT
from utils.helpers.class_helper import (
    extract_course_ids,
    wait_until_item_in_list,
    wait_until_item_not_in_list,
)


@pytest.mark.api
@pytest.mark.educator
@pytest.mark.e2e
class TestE2ECourseManagement:
    """E2E-1: 과목 추가 → 순서 변경 → 클래스에서 제거"""

    def test_add_reorder_delete_full_cycle(
        self,
        educator_class_api,
        assert_response,
        completed_bulk_add_task,
        fetch_course_list,
    ):
        # 1. 과목 추가 (fixture에서 bulk add 완료 및 검증까지 수행)
        _, _, added_course_id = completed_bulk_add_task

        # 2. 추가된 과목이 목록에 나타날 때까지 대기
        courses = wait_until_item_in_list(
            fetch_course_list,
            match_key="course_id",
            match_value=added_course_id,
        )

        # 3. 추가된 과목을 첫 번째로 이동하도록 순서 구성
        current_order = [course["course_id"] for course in courses]
        expected_order = [
            added_course_id,
            *[cid for cid in current_order if cid != added_course_id],
        ]

        # 4. 순서 변경
        reorder_resp = educator_class_api.reorder_courses(expected_order)
        assert_response(reorder_resp, 200)

        # 5. 재조회하여 순서가 실제 반영되었는지 검증
        verify_resp = educator_class_api.get_course_list(
            skip=0,
            count=len(expected_order),
        )
        reordered_courses = assert_response(verify_resp, 200)

        actual_order = [
            course["course_id"]
            for course in reordered_courses
        ]

        assert actual_order == expected_order, (
            "순서 변경 결과가 재조회 시 그대로 반영되어야 합니다."
        )

        # 6. 과목 삭제
        delete_resp = educator_class_api.delete_course(added_course_id)
        assert_response(delete_resp, 200)

        # 7. 삭제 완료될 때까지 대기 후 목록에서 제거되었는지 확인
        wait_until_item_not_in_list(
            fetch_course_list,
            match_key="course_id",
            match_value=added_course_id,
        )


@pytest.mark.api
@pytest.mark.educator
@pytest.mark.e2e
class TestE2ECourseDetailTabTraversal:
    @pytest.mark.skip(reason="P3 각 탭 대응 API 미실증")
    def test_traverse_all_tabs_from_course_list(self):
        """[E2E-3] 과목 목록 → 과목 클릭 → 탭 전환 검증"""
        pass


@pytest.mark.api
@pytest.mark.educator
@pytest.mark.e2e
class TestE2EDashboardMainFlow:
    @pytest.mark.skip(reason="P4/P5 대시보드 API 미실증")
    def test_dashboard_summary_search_and_report(self):
        """[E2E-4] 과목 상세 → 학습현황 메인 플로우"""
        pass


@pytest.mark.api
@pytest.mark.educator
@pytest.mark.e2e
class TestE2ELectureDrilldownFlow:
    @pytest.mark.skip(reason="수업별 학습현황 드릴다운 API 미실증")
    def test_lecture_drilldown_to_individual_student(self):
        """[E2E-5] 학습현황 화면 → 수업별 학습현황 드릴다운"""
        pass