# tests/api/classhome/test_learning_status_educator.py
"""학습현황 — 교육자 전용 테스트 (CH-019, CH-021)

대상 API (dashboard-api):
  GET /classroom/{class_id}   반 전체 학습현황 — 교육자만 접근 가능
  (교육자 계정은 운영 로그인 불가 → dev 전용)
"""
import pytest

from api.endpoints.dashboard_api import DashboardAPI
from api.schemas.classhome_schema import DashboardSchemas
from utils.assertions.api_assertions import assert_valid_schema

NON_EXISTENT_CLASS_ID = "00000000-0000-0000-0000-000000000000"


@pytest.mark.api
@pytest.mark.classhome
@pytest.mark.educator
class TestClassroomSummaryEducator:
    """GET /classroom/{class_id} — 교육자 전용 (CH-019, CH-021)."""

    def test_ch_019_educator_200_and_fields(self, dev_educator_dashboard_api: DashboardAPI, dev_class_id: str):
        """[CH-019] 교육자 토큰으로 반 전체 학습현황 조회 시 200 및 집계 필드 반환."""
        resp = dev_educator_dashboard_api.get_classroom_summary(dev_class_id)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert_valid_schema(body, DashboardSchemas.CLASSROOM_SUMMARY_SCHEMA)
        # Business: 카운트 필드는 음수 불가
        assert body["submit_cnt"] >= 0, f"submit_cnt 음수: {body}"
        assert body["test_completed_cnt"] >= 0, f"test_completed_cnt 음수: {body}"
        # Business: learning_progress는 수치로 파싱 가능한 문자열
        # API가 learning_progress(평균)를 숫자가 아닌 문자열로 반환 -> float으로 변환될수있는지 확인
        try:
            float(body["learning_progress"])
        except (ValueError, TypeError):
            pytest.fail(f"learning_progress 파싱 불가: {body['learning_progress']}")

    def test_ch_021_nonexistent_class_id_returns_409(self, dev_educator_dashboard_api: DashboardAPI):
        """[CH-021] 존재하지 않는 class_id 조회 시 409(model_not_found) 반환."""
        resp = dev_educator_dashboard_api.get_classroom_summary(NON_EXISTENT_CLASS_ID)
        assert resp.status_code == 409, resp.text
        assert resp.json().get("code") == "model_not_found", resp.text
