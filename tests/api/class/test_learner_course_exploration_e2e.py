"""
E2E: 학습자 단일 시점 해피패스 — 과목 탐색 → 상세 조회 → 내 학습현황 확인

test_course_add_delete_happy_path.py가 교육자 시점에서 "추가 → 조회 → 삭제"를
하나의 라이프사이클로 묶은 것처럼, 이 파일은 학습자 시점에서
"과목 목록 탐색 → 과목 상세 조회 → 내 학습현황 조회"를 하나의 여정으로 묶는다.

⚠️ 학습자/교육자 API는 서버 자체가 dev/prod로 분리되어 있어 병행 테스트를 하지
   않는다. 이 파일은 순수하게 학습자(prod) 시점만 다룬다.

⚠️ PROGRESS_COURSE_ID(기본값 776040, 설정 키 PROD_PROGRESS_COURSE_ID)가 실제로
   class_api의 과목 목록(get_course_list) 응답에도 노출되는 과목인지는 아직
   실행으로 확인되지 않았다. 노출되지 않는 별도 관리 course_id일 가능성을
   감안해 방어적으로 skip 처리하지 않고, 실패 시 "어떤 course_id를 찾았는데
   목록에 없어서 실패했는지"를 그대로 assert 메시지에 남기도록 작성했다.

⚠️ 반 전체 학습현황(get_classroom_summary)은 학습자 권한으로는 조회가 되지
   않을 것으로 추정되어 이 해피패스에 포함하지 않았다.
"""

import os

import pytest

from core.config import settings
from utils.helpers.class_helper import DEFAULT_PAGE_SIZE, assert_progress_in_range

PROD_ENV = settings.elice_environments["prod"]
LEARNER_ACCOUNT_ID = os.getenv("PROD_LEARNER_ACCOUNT_ID") or PROD_ENV.get("LEARNER_ACCOUNT_ID")
CLASSROOM_ID = PROD_ENV["CLASSROOM_ID"]
COHORT_ID = PROD_ENV["COHORT_ID"]
PROGRESS_COURSE_ID = PROD_ENV["PROGRESS_COURSE_ID"]

pytestmark = pytest.mark.skipif(
    not LEARNER_ACCOUNT_ID,
    reason="PROD_LEARNER_ACCOUNT_ID not set; skipping learner-specific tests",
)


@pytest.mark.api
@pytest.mark.learner
class TestLearnerCourseExplorationHappyPath:
    def test_browse_course_list_view_detail_and_check_my_progress(
        self, class_api, student_dashboard_api, assert_response
    ):
        # --- 1단계 (E2E-L-01): 과목 개수 조회 ---
        count_resp = class_api.get_course_count()
        total_count = assert_response(count_resp, 200)
        assert isinstance(total_count, int), (
            f"Expected int course count but got {type(total_count)}: {total_count!r}"
        )

        # --- 2단계 (E2E-L-02): 개수 기준 목록 조회 ---
        list_resp = class_api.get_course_list(
            skip=0, count=max(total_count, DEFAULT_PAGE_SIZE)
        )
        course_list = assert_response(list_resp, 200)
        assert len(course_list) <= total_count, (
            f"Expected at most {total_count} items but got {len(course_list)}"
        )

        # --- 3단계 (E2E-L-03): 목록 안에 PROGRESS_COURSE_ID가 존재하는지 확인 ---
        matched = next(
            (item for item in course_list if item["course_id"] == PROGRESS_COURSE_ID),
            None,
        )
        assert matched is not None, (
            f"PROGRESS_COURSE_ID={PROGRESS_COURSE_ID} 가 과목 목록에서 발견되지 "
            f"않았습니다 (id가 일치하지 않아 실패). 목록에 존재하는 course_id들: "
            f"{[item['course_id'] for item in course_list]}"
        )

        # --- 4단계 (E2E-L-04): 해당 과목 단건 조회 후 목록 데이터와 일치 확인 ---
        detail_resp = class_api.get_course(PROGRESS_COURSE_ID)
        detail = assert_response(detail_resp, 200)
        assert detail["course_id"] == PROGRESS_COURSE_ID, (
            f"Expected course_id={PROGRESS_COURSE_ID} but got {detail['course_id']}"
        )
        assert detail.get("title") == matched.get("title"), (
            f"목록 title={matched.get('title')!r} 과 상세 title="
            f"{detail.get('title')!r} 이 일치해야 합니다."
        )

        # --- 5단계 (E2E-L-05): 해당 과목에 대한 내 학습현황 조회 ---
        progress_resp = student_dashboard_api.get_student_progress(
            account_id=LEARNER_ACCOUNT_ID,
            classroom_id=CLASSROOM_ID,
            course_id=PROGRESS_COURSE_ID,
            filter_cohort_id=COHORT_ID,
        )
        progress = assert_response(progress_resp, 200)
        assert_progress_in_range(progress["learning_progress"])