# tests/api/classhome/classroom/test_learning_status_common.py
"""클래스 홈 — 학습현황 테스트 (CH-019 ~ CH-028)

APIs (dashboard-api):
  GET /classroom/{class_id}      반 전체 학습현황 — CH-019 ~ CH-021  (dev 전용, 교육자 운영 로그인 불가)
  GET /student/{account_id}      개인 학습현황   — CH-022 ~ CH-028  (prod·dev 양쪽)
"""
import pytest

from api.endpoints.dashboard_api import DashboardAPI
from fixtures.classhome_fixture import (
    DASHBOARD_CLIENTS,
    DASHBOARD_LEARNER_CLIENTS,
    DASHBOARD_LEARNER_ACCOUNT_PAIRS,
)

NON_EXISTENT_CLASS_ID = "00000000-0000-0000-0000-000000000000"
NON_EXISTENT_ACCOUNT_ID = 999_999_999
EDUCATOR_ACCOUNT_ID = 111  # CH-028: Student 테이블에 없는 교육자 id


@pytest.mark.api
@pytest.mark.classroom
class TestClassroomSummary:
    """GET /classroom/{class_id} — 반 전체 학습현황 (CH-019 ~ CH-021)."""

    def test_ch_019_educator_200_and_fields(self, dev_educator_dashboard_api: DashboardAPI, dev_class_id: str):
        """[CH-019] 교육자 토큰으로 반 전체 학습현황 조회 시 200 및 집계 필드 반환."""
        resp = dev_educator_dashboard_api.get_classroom_summary(dev_class_id)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        for field in ("learning_progress", "practice_score", "test_score", "submit_cnt", "test_completed_cnt"):
            assert field in body, f"집계 필드 누락: {field}"

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

    def test_ch_021_nonexistent_class_id_returns_409(self, dev_educator_dashboard_api: DashboardAPI):
        """[CH-021] 존재하지 않는 class_id 조회 시 409(model_not_found) 반환."""
        resp = dev_educator_dashboard_api.get_classroom_summary(NON_EXISTENT_CLASS_ID)
        assert resp.status_code == 409, resp.text
        assert resp.json().get("code") == "model_not_found", resp.text


@pytest.mark.api
@pytest.mark.classroom
class TestStudentLearning:
    """GET /student/{account_id} — 개인 학습현황 (CH-022 ~ CH-028)."""

    @pytest.mark.parametrize("api_fixture,class_id_fixture,account_id_fixture", DASHBOARD_LEARNER_ACCOUNT_PAIRS)
    def test_ch_022_learner_own_account_returns_200(self, request, api_fixture, class_id_fixture, account_id_fixture):
        """[CH-022] 학습자 본인 account_id 조회 시 200 반환 — prod·dev 양쪽 검증."""
        api: DashboardAPI = request.getfixturevalue(api_fixture)
        class_id: str = request.getfixturevalue(class_id_fixture)
        account_id: int = request.getfixturevalue(account_id_fixture)
        resp = api.get_student(account_id, classroom_id=class_id)
        assert resp.status_code == 200, resp.text
        assert "learning_progress" in resp.json(), f"learning_progress 필드 누락: {resp.json()}"

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
            assert field in account, f"[IDOR] account.{field} 필드 노출 확인: {resp.json()}"

    @pytest.mark.parametrize("client_fixture", DASHBOARD_CLIENTS)
    def test_ch_024_invalid_account_id_type_returns_422(
        self, request, client_fixture, dev_class_id: str
    ):
        """[CH-024] account_id 타입 오류(abc) 시 422 및 int_parsing 에러 반환."""
        api: DashboardAPI = request.getfixturevalue(client_fixture)
        resp = api.get_student("abc", classroom_id=dev_class_id)
        assert resp.status_code == 422, resp.text
        error_types = {item.get("type") for item in resp.json().get("detail", [])}
        assert "int_parsing" in error_types, f"int_parsing 에러 없음: {resp.json()}"

    @pytest.mark.parametrize("client_fixture", DASHBOARD_CLIENTS)
    @pytest.mark.parametrize("bad_id", [0, -1], ids=["zero", "negative"])
    def test_ch_025_zero_or_negative_account_id_returns_409(
        self, request, client_fixture, bad_id, dev_class_id: str
    ):
        """[CH-025] account_id 0·음수 요청 시 409(model_not_found) 반환."""
        api: DashboardAPI = request.getfixturevalue(client_fixture)
        resp = api.get_student(bad_id, classroom_id=dev_class_id)
        assert resp.status_code == 409, resp.text
        assert resp.json().get("code") == "model_not_found", resp.text

    @pytest.mark.parametrize("client_fixture", DASHBOARD_CLIENTS)
    def test_ch_026_nonexistent_account_id_returns_409(
        self, request, client_fixture, dev_class_id: str
    ):
        """[CH-026] 존재하지 않는 account_id(999999999) 조회 시 409(model_not_found) 반환."""
        api: DashboardAPI = request.getfixturevalue(client_fixture)
        resp = api.get_student(NON_EXISTENT_ACCOUNT_ID, classroom_id=dev_class_id)
        assert resp.status_code == 409, resp.text
        assert resp.json().get("code") == "model_not_found", resp.text

    @pytest.mark.parametrize("client_fixture", DASHBOARD_CLIENTS)
    def test_ch_027_no_auth_returns_403(
        self, request, client_fixture
    ):
        """[CH-027] 인증 토큰 없이 요청 시 403(no_access_token) 반환."""
        api: DashboardAPI = request.getfixturevalue(client_fixture)
        resp = api.get_student(NON_EXISTENT_ACCOUNT_ID, auth=False)
        assert resp.status_code == 403, resp.text
        assert resp.json().get("code") == "no_access_token", resp.text

    def test_ch_028_educator_account_id_returns_409(
        self,
        dev_learner_dashboard_api: DashboardAPI,
        dev_class_id: str,
    ):
        """[CH-028] 교육자 account_id(111) 대입 시 409(model_not_found) 반환.

        Student 테이블에 없는 id이므로 학습자 token이어도 409.
        """
        resp = dev_learner_dashboard_api.get_student(EDUCATOR_ACCOUNT_ID, classroom_id=dev_class_id)
        assert resp.status_code == 409, resp.text
        assert resp.json().get("code") == "model_not_found", resp.text
