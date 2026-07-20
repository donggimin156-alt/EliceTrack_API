# tests/api/classhome/test_learning_status_learner.py
"""학습현황 — 학습자 전용 테스트 (CH-020, CH-022, CH-023, CH-028)

대상 API (dashboard-api):
  GET /classroom/{class_id}   학습자 토큰 접근 검증 (BFLA)
  GET /student/{account_id}   개인 학습현황 — 본인 조회, IDOR, 교육자 ID 조회
"""
import pytest

from api.endpoints.dashboard_api import DashboardAPI
from api.schemas.classhome_schema import DashboardSchemas
from fixtures.classhome_fixture import DASHBOARD_LEARNER_CLIENTS, DASHBOARD_LEARNER_ACCOUNT_PAIRS
from utils.assertions.api_assertions import assert_valid_schema


@pytest.mark.api
@pytest.mark.classroom
@pytest.mark.learner
class TestClassroomSummaryLearner:
    """GET /classroom/{class_id} — 학습자 토큰 접근 검증 (CH-020)."""

    @pytest.mark.bug
    @pytest.mark.parametrize("api_fixture,class_id_fixture", DASHBOARD_LEARNER_CLIENTS)
    def test_ch_020_learner_bfla_returns_200(self, request, api_fixture, class_id_fixture):
        """[CH-020][버그 확정] 학습자 토큰으로 교육자 전용 API 접근 시 200 반환 — BFLA 버그 (기대값: 403).

        prod·dev 양쪽에서 재현 확인. 반 전체 집계 데이터가 그대로 노출됨.
        """
        api: DashboardAPI = request.getfixturevalue(api_fixture)
        class_id: str = request.getfixturevalue(class_id_fixture)
        resp = api.get_classroom_summary(class_id)
        assert resp.status_code == 200, resp.text


@pytest.mark.api
@pytest.mark.classroom
@pytest.mark.learner
class TestStudentLearningLearner:
    """GET /student/{account_id} — 학습자 전용 (CH-022, CH-023, CH-028)."""

    @pytest.mark.parametrize("api_fixture,class_id_fixture,account_id_fixture", DASHBOARD_LEARNER_ACCOUNT_PAIRS)
    def test_ch_022_learner_own_account_returns_200(self, request, api_fixture, class_id_fixture, account_id_fixture):
        """[CH-022] 학습자 본인 account_id 조회 시 200 반환 — prod·dev 양쪽 검증."""
        api: DashboardAPI = request.getfixturevalue(api_fixture)
        class_id: str = request.getfixturevalue(class_id_fixture)
        account_id: int = request.getfixturevalue(account_id_fixture)
        resp = api.get_student(account_id, classroom_id=class_id)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert_valid_schema(body, DashboardSchemas.STUDENT_LEARNING_SCHEMA)
        # Business: 반환된 account.id가 요청한 account_id와 일치
        assert body["account"]["id"] == account_id, (
            f"반환 account.id({body['account']['id']}) ≠ 요청 account_id({account_id})"
        )

    @pytest.mark.bug
    @pytest.mark.security
    def test_ch_023_learner_idor_returns_200(
        self,
        prod_learner_dashboard_api: DashboardAPI,
        prod_class_id: str,
        prod_other_account_id: int,
    ):
        """[CH-023][버그 확정] 학습자 타인 account_id 조회 시 200 반환 — IDOR 버그 (기대값: 403).

        운영에서 실측 확인 (게시판 author 필드로 확보한 account_id 사용).
        타인의 email, fullname, 학습 데이터가 그대로 노출됨.
        """
        resp = prod_learner_dashboard_api.get_student(prod_other_account_id, classroom_id=prod_class_id)
        assert resp.status_code == 200, resp.text
        account = resp.json().get("account", {})
        for field in ("email", "fullname"):
            assert field in account, f"[IDOR] account.{field} 필드가 응답에 없음 — 버그 수정 여부 확인 필요: {resp.json()}"

    def test_ch_028_educator_account_id_returns_409(
        self,
        dev_learner_dashboard_api: DashboardAPI,
        dev_class_id: str,
        dev_educator_account_id: int,
    ):
        """[CH-028] 교육자 account_id 대입 시 409(model_not_found) 반환.

        Student 테이블에 없는 id이므로 학습자 token이어도 409.
        """
        resp = dev_learner_dashboard_api.get_student(dev_educator_account_id, classroom_id=dev_class_id)
        assert resp.status_code == 409, resp.text
        assert resp.json().get("code") == "model_not_found", resp.text
