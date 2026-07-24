"""
E-11: 학습현황 엑셀 다운로드 (토큰 발급 → 파일 획득 2단계)
교육자 dev 고정.
"""

import pytest

from api.schemas.dashboard_schema import DashboardSchemas
from core.config import settings
from utils.helpers.class_helper import assert_model_not_found_error
from utils.helpers.api_assertions import assert_valid_schema

REPORT_ELICE_COURSE_ID = settings.elice_environments["dev"]["REPORT_ELICE_COURSE_ID"]
NONEXISTENT_COURSE_ID = 999999999


@pytest.mark.api
@pytest.mark.educator
class TestReportTokenIssue:
    def test_issue_download_token(self, educator_dashboard_api, assert_response):
        resp = educator_dashboard_api.get_course_report_token(
            course_id=REPORT_ELICE_COURSE_ID,
            elice_course_id=REPORT_ELICE_COURSE_ID,
        )
        data = assert_response(resp, 200)
        assert_valid_schema(data, DashboardSchemas.REPORT_TOKEN_SCHEMA)

    def test_nonexistent_course_id_returns_409(self, educator_dashboard_api, assert_response):
        resp = educator_dashboard_api.get_course_report_token(
            course_id=NONEXISTENT_COURSE_ID, elice_course_id=NONEXISTENT_COURSE_ID,
        )
        data = assert_response(resp, 409)
        assert_model_not_found_error(data)


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

    def test_download_with_valid_token(
        self, educator_resource_api, download_token, assert_response
    ):
        resp = educator_resource_api.download_temp_file(download_token)
        assert_response(resp, 200)
        assert resp.headers.get("content-type") is not None

    def test_reuse_same_token(self, educator_resource_api, download_token, assert_response):
        """같은 토큰 재사용 시 만료/재사용 정책 확인 (QA-149: 기대 동작 미확정)"""
        first = educator_resource_api.download_temp_file(download_token)
        second = educator_resource_api.download_temp_file(download_token)
        assert_response(first, 200)