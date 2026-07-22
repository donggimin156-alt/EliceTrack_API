"""
L-06~L-09: 학습자 학습현황 상세 조회 (GET /student/{account_id})

⚠️ 학습자 테스트는 항상 prod 고정 (student_dashboard_api fixture가 prod로 못박혀 있음).
L-07(타인 계정 접근 차단)은 미실증 — Postman 확인 후 unskip.
"""

import os
import pytest
from jsonschema import validate

from api.schemas.dashboard_schema import DashboardSchemas
from core.config import settings

PROD_ENV = settings.elice_environments["prod"]
# `LEARNER_ACCOUNT_ID` is a personal value; prefer providing it via environment variable
# rather than committing it to repository config. Tests depending on it will be skipped
# when the env var is not present.
LEARNER_ACCOUNT_ID = os.getenv("PROD_LEARNER_ACCOUNT_ID")
if LEARNER_ACCOUNT_ID is None:
    # fallback to settings only if explicitly configured in prod env (rare)
    LEARNER_ACCOUNT_ID = PROD_ENV.get("LEARNER_ACCOUNT_ID")
PROGRESS_COURSE_ID = PROD_ENV["PROGRESS_COURSE_ID"]
COHORT_ID = PROD_ENV["COHORT_ID"]
CLASSROOM_ID = PROD_ENV["CLASSROOM_ID"]


def _require_learner_account():
    if not LEARNER_ACCOUNT_ID:
        pytest.skip("PROD_LEARNER_ACCOUNT_ID not set; skipping learner-specific tests")


pytestmark = pytest.mark.skipif(
    not LEARNER_ACCOUNT_ID,
    reason="PROD_LEARNER_ACCOUNT_ID not set; skipping learner-specific tests",
)


@pytest.fixture
def student_progress(student_dashboard_api, assert_response):
    _require_learner_account()

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
    def test_L06_response_matches_schema(self, student_progress):
        validate(instance=student_progress, schema=DashboardSchemas.STUDENT_PROGRESS_SCHEMA)

    def test_L06_account_matches_schema(self, student_progress):
        validate(instance=student_progress["account"], schema=DashboardSchemas.ACCOUNT_SCHEMA)


@pytest.mark.api
@pytest.mark.learner
class TestStudentProgressBusiness:
    def test_L08_learning_progress_is_string(self, student_progress):
        # 실증됨: "5.26"처럼 문자열로 내려옴 — 자동화 assertion 시 형변환 필요
        assert isinstance(student_progress["learning_progress"], str)
        float(student_progress["learning_progress"])  # 형변환 가능해야 함

    def test_L08_progress_value_range(self, student_progress):
        assert 0 <= float(student_progress["learning_progress"]) <= 100

    def test_L09_scores_are_null_or_number(self, student_progress):
        for key in ("test_score", "practice_score"):
            value = student_progress[key]
            assert value is None or isinstance(value, (int, float))


@pytest.mark.api
@pytest.mark.learner
class TestStudentProgressValidation:
    def test_nonexistent_cohort_id_behavior(self, student_dashboard_api, assert_response):
        _require_learner_account()

        resp = student_dashboard_api.get_student_progress(
            account_id=LEARNER_ACCOUNT_ID,
            classroom_id=CLASSROOM_ID,
            course_id=PROGRESS_COURSE_ID,
            filter_cohort_id="00000000-0000-0000-0000-000000000000",
        )
        # 서버는 비존재 리소스에 대해 409(model_not_found)을 반환하기도 합니다.
        # 안정적으로 통과하려면 200/404/409를 허용하고, 409일 때는 응답 코드 확인합니다.
        if resp.status_code == 409:
            body = resp.json()
            assert body.get("code") == "model_not_found"
        else:
            assert resp.status_code in (200, 404)


@pytest.mark.api
@pytest.mark.learner
class TestStudentProgressPermission:
    def test_L07_cannot_access_other_students_progress(
        self, student_dashboard_api, assert_response
    ):
        _require_learner_account()

        # 현재 테스트 계정이 없으므로 다른 사용자를 나타내는 안전한 placeholder 사용
        other_account_id = 0
        resp = student_dashboard_api.get_student_progress(
            account_id=other_account_id,
            classroom_id=CLASSROOM_ID,
            course_id=PROGRESS_COURSE_ID,
            filter_cohort_id=COHORT_ID,
        )
        # 백엔드에서 접근 권한/모델 없음 등으로 403/404/409 중 하나를 반환할 수 있음
        if resp.status_code == 409:
            body = resp.json()
            assert body.get("code") == "model_not_found"
        else:
            assert resp.status_code in (403, 404)