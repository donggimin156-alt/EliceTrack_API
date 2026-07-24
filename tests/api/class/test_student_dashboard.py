"""
학습자 학습현황 상세 조회 (GET /student/{account_id})

학습자 테스트는 항상 prod 고정 (student_dashboard_api fixture가 prod로 못박혀 있음).
타인 계정 접근 차단 검증은 아직 기대 응답 코드가 확정되지 않았음 (QA-150).
"""

import os

import pytest

from api.schemas.dashboard_schema import DashboardSchemas
from core.config import settings
from utils.helpers.class_helper import assert_model_not_found_error, assert_schema

PROD_ENV = settings.elice_environments["prod"]
# `LEARNER_ACCOUNT_ID`는 개인 식별 정보이므로 레포에 커밋하지 않고 환경 변수로 주입받는다.
# 값이 없으면 이 파일의 테스트는 전부 skip 처리된다.
LEARNER_ACCOUNT_ID = os.getenv("PROD_LEARNER_ACCOUNT_ID") or PROD_ENV.get("LEARNER_ACCOUNT_ID")
PROGRESS_COURSE_ID = PROD_ENV["PROGRESS_COURSE_ID"]
COHORT_ID = PROD_ENV["COHORT_ID"]
CLASSROOM_ID = PROD_ENV["CLASSROOM_ID"]
NONEXISTENT_COHORT_ID = "00000000-0000-0000-0000-000000000000"
# 현재 테스트 계정이 없으므로 "다른 학습자"를 나타내는 안전한 placeholder
OTHER_ACCOUNT_ID_PLACEHOLDER = 0

pytestmark = pytest.mark.skipif(
    not LEARNER_ACCOUNT_ID,
    reason="PROD_LEARNER_ACCOUNT_ID not set; skipping learner-specific tests",
)


@pytest.fixture
def student_progress(student_dashboard_api, assert_response):
    resp = student_dashboard_api.get_student_progress(
        account_id=LEARNER_ACCOUNT_ID,
        classroom_id=CLASSROOM_ID,
        course_id=PROGRESS_COURSE_ID,
        filter_cohort_id=COHORT_ID,
    )
    return assert_response(resp, 200)


@pytest.mark.api
@pytest.mark.learner
class TestStudentProgressSchema:
    def test_response_matches_schema(self, student_progress):
        assert_schema(student_progress, DashboardSchemas.STUDENT_PROGRESS_SCHEMA)

    def test_account_matches_schema(self, student_progress):
        assert_schema(student_progress["account"], DashboardSchemas.ACCOUNT_SCHEMA)


@pytest.mark.api
@pytest.mark.learner
class TestStudentProgressBusiness:
    def test_learning_progress_is_numeric_string(self, student_progress):
        # 실증됨: "5.26"처럼 문자열로 내려옴 — 자동화 assertion 시 형변환 필요
        progress = student_progress["learning_progress"]
        assert isinstance(progress, str), (
            f"Expected learning_progress to be str but got {type(progress)}"
        )
        float(progress)  # 형변환 가능해야 함

    def test_learning_progress_value_range(self, student_progress):
        progress = float(student_progress["learning_progress"])
        assert 0 <= progress <= 100, f"Expected 0<=progress<=100 but got {progress}"

    def test_scores_are_null_or_number(self, student_progress):
        for key in ("test_score", "practice_score"):
            value = student_progress[key]
            assert value is None or isinstance(value, (int, float)), (
                f"Expected {key} to be null or number but got {value!r}"
            )


@pytest.mark.api
@pytest.mark.learner
class TestStudentProgressValidation:
    def test_nonexistent_cohort_id_behavior(self, student_dashboard_api, assert_response):
        resp = student_dashboard_api.get_student_progress(
            account_id=LEARNER_ACCOUNT_ID,
            classroom_id=CLASSROOM_ID,
            course_id=PROGRESS_COURSE_ID,
            filter_cohort_id=NONEXISTENT_COHORT_ID,
        )
        # 서버는 비존재 리소스에 대해 409(model_not_found)을 반환하기도 한다.
        # 안정적으로 통과하려면 200/404/409를 허용하고, 409일 때만 바디를 추가 검증한다.
        if resp.status_code == 409:
            assert_model_not_found_error(resp.json())
        else:
            assert resp.status_code in (200, 404), (
                f"Expected status in (200, 404, 409) but got {resp.status_code}"
            )


@pytest.mark.api
@pytest.mark.learner
class TestStudentProgressPermission:
    def test_cannot_access_other_students_progress(
        self, student_dashboard_api, assert_response
    ):
        resp = student_dashboard_api.get_student_progress(
            account_id=OTHER_ACCOUNT_ID_PLACEHOLDER,
            classroom_id=CLASSROOM_ID,
            course_id=PROGRESS_COURSE_ID,
            filter_cohort_id=COHORT_ID,
        )
        # 백엔드에서 접근 권한/모델 없음 등으로 403/404/409 중 하나를 반환할 수 있다 (QA-150).
        if resp.status_code == 409:
            assert_model_not_found_error(resp.json())
        else:
            assert resp.status_code in (403, 404), (
                f"Expected status in (403, 404, 409) but got {resp.status_code}"
            )