# fixtures/dashboard_fixture.py
"""Dashboard/Resource API 전용 픽스처.

학습자 학습현황은 prod 고정, 교육자 리포트 토큰 발급은 dev 고정 —
role별로 elice_environments의 특정 환경을 못 박아 사용한다 (TARGET 환경변수와 무관).
"""

import pytest
import requests

from api.endpoints.classhome.dashboard_api import DashboardAPI
from api.endpoints.resource_api import ResourceApi
from api.utils.elice_auth import make_authenticated_session, get_env_config


@pytest.fixture(scope="session")
def dashboard_api_factory():
    def _create(
        *,
        env_name: str,
        role: str,
        session: requests.Session | None = None,
        skip_msg: str | None = None,
    ) -> DashboardAPI:
        if session is None:
            session = make_authenticated_session(env_name, role)
            if session is None:
                pytest.skip(
                    skip_msg or f"{env_name} 환경의 {role} 인증 정보가 없어 테스트를 건너뜁니다."
                )
        env = get_env_config(env_name)
        return DashboardAPI(session=session, org=env["ORG"], env=env_name)

    return _create


@pytest.fixture(scope="session")
def student_dashboard_api(dashboard_api_factory) -> DashboardAPI:
    """학습자 학습현황 조회용 — prod 고정 (학습자 테스트는 무조건 prod)."""
    return dashboard_api_factory(
        env_name="prod",
        role="LEARNER",
        skip_msg="prod 학습자 토큰 없음 (PROD_LEARNER_TOKEN)",
    )


@pytest.fixture(scope="session")
def educator_dashboard_api(dashboard_api_factory) -> DashboardAPI:
    """교육자 리포트 토큰 발급용 — dev 고정."""
    return dashboard_api_factory(
        env_name="dev",
        role="EDUCATOR",
        skip_msg="dev 교육자 토큰 없음 (DEV_EDUCATOR_TOKEN)",
    )


@pytest.fixture(scope="session")
def educator_resource_api(educator_dashboard_api) -> ResourceApi:
    """다운로드 토큰 소비(remote_file/temp/get)용 — 교육자 세션 재사용, dev 고정."""
    return ResourceApi(educator_dashboard_api.session, env_name="dev")