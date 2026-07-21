# tests/api/classhome/test_learning_status_common.py
"""학습현황 — 공통 테스트 (CH-024~027)

학습자·교육자 양쪽 모두 동일한 결과를 내는 케이스.
대상 API (dashboard-api):
  GET /student/{account_id}   타입 오류, 경계값, 인증 없음
"""
import pytest

from api.endpoints.dashboard_api import DashboardAPI
from fixtures.classhome_fixture import DASHBOARD_CLIENTS

NON_EXISTENT_ACCOUNT_ID = 999_999_999


@pytest.mark.api
@pytest.mark.classhome
class TestStudentLearningCommon:
    """GET /student/{account_id} — 학습자·교육자 공통 (CH-024~027)."""

    @pytest.mark.parametrize("client_fixture,class_id_fixture", DASHBOARD_CLIENTS)
    def test_ch_024_invalid_account_id_type_returns_422(self, request, client_fixture, class_id_fixture):
        """[CH-024] account_id 타입 오류(abc) 시 422 및 int_parsing 에러 반환."""
        api: DashboardAPI = request.getfixturevalue(client_fixture)
        class_id: str = request.getfixturevalue(class_id_fixture)
        resp = api.get_student("abc", classroom_id=class_id)
        assert resp.status_code == 422, resp.text
        error_types = {item.get("type") for item in resp.json().get("detail", [])}
        assert "int_parsing" in error_types, f"int_parsing 에러 없음: {resp.json()}"

    @pytest.mark.parametrize("client_fixture,class_id_fixture", DASHBOARD_CLIENTS)
    @pytest.mark.parametrize("bad_id", [0, -1], ids=["zero", "negative"])
    def test_ch_025_zero_or_negative_account_id_returns_409(
        self, request, client_fixture, class_id_fixture, bad_id
    ):
        """[CH-025] account_id 0·음수 요청 시 409(model_not_found) 반환."""
        api: DashboardAPI = request.getfixturevalue(client_fixture)
        class_id: str = request.getfixturevalue(class_id_fixture)
        resp = api.get_student(bad_id, classroom_id=class_id)
        assert resp.status_code == 409, resp.text
        assert resp.json().get("code") == "model_not_found", resp.text

    @pytest.mark.parametrize("client_fixture,class_id_fixture", DASHBOARD_CLIENTS)
    def test_ch_026_nonexistent_account_id_returns_409(self, request, client_fixture, class_id_fixture):
        """[CH-026] 존재하지 않는 account_id(999999999) 조회 시 409(model_not_found) 반환."""
        api: DashboardAPI = request.getfixturevalue(client_fixture)
        class_id: str = request.getfixturevalue(class_id_fixture)
        resp = api.get_student(NON_EXISTENT_ACCOUNT_ID, classroom_id=class_id)
        assert resp.status_code == 409, resp.text
        assert resp.json().get("code") == "model_not_found", resp.text

    @pytest.mark.parametrize("client_fixture,class_id_fixture", DASHBOARD_CLIENTS)
    def test_ch_027_no_auth_returns_403(self, request, client_fixture, class_id_fixture):
        """[CH-027] 인증 토큰 없이 요청 시 403(no_access_token) 반환."""
        api: DashboardAPI = request.getfixturevalue(client_fixture)
        class_id: str = request.getfixturevalue(class_id_fixture)
        resp = api.get_student(NON_EXISTENT_ACCOUNT_ID, classroom_id=class_id, auth=False)
        assert resp.status_code == 403, resp.text
        assert resp.json().get("code") == "no_access_token", resp.text
