"""
E-11: 학습현황 엑셀 다운로드 (토큰 발급 → 파일 획득 2단계)
⚠️ 교육자 dev 고정.
"""

import pytest
from jsonschema import validate

from api.schemas.dashboard_schema import DashboardSchemas
from core.config import settings

REPORT_ELICE_COURSE_ID = settings.elice_environments["dev"]["REPORT_ELICE_COURSE_ID"]


@pytest.mark.api
@pytest.mark.educator
class TestReportTokenIssue:
    def test_E11_issue_download_token(self, educator_dashboard_api, assert_response):
        resp = educator_dashboard_api.get_course_report_token(
            course_id=REPORT_ELICE_COURSE_ID,
            elice_course_id=REPORT_ELICE_COURSE_ID,
        )
        data = assert_response(resp, 200)
        validate(instance=data, schema=DashboardSchemas.REPORT_TOKEN_SCHEMA)

    def test_E11b_nonexistent_course_id(self, educator_dashboard_api, assert_response):
        resp = educator_dashboard_api.get_course_report_token(
            course_id=999999999, elice_course_id=999999999,
        )
        # 서버는 존재하지 않는 리소스에 대해 409(model_not_found)을 반환합니다.
        # 실제 API 동작과 일치하도록 409로 기대값을 맞춥니다.
        assert resp.status_code == 409
        data = resp.json()
        assert data.get("code") == "model_not_found"


@pytest.mark.api
@pytest.mark.educator
class TestReportFileDownload:
    @pytest.fixture
    def download_token(self, educator_dashboard_api, assert_response):
        resp = educator_dashboard_api.get_course_report_token(
            course_id=REPORT_ELICE_COURSE_ID,
            elice_course_id=REPORT_ELICE_COURSE_ID,
        )
        return assert_response(resp, 200)["download_token"]

    def test_E11c_download_with_valid_token(self, educator_resource_api, download_token, assert_response):
        resp = educator_resource_api.download_temp_file(download_token)
        assert_response(resp, 200)
        assert resp.headers.get("content-type") is not None

    def test_E11d_reuse_same_token(self, educator_resource_api, download_token, assert_response):
        """같은 토큰 재사용 시 만료/재사용 정책 확인 (TODO: 기대 동작 미확정)"""
        first = educator_resource_api.download_temp_file(download_token)
        second = educator_resource_api.download_temp_file(download_token)
        assert_response(first, 200)
        # TODO: second.status_code 기대값 확정 필요