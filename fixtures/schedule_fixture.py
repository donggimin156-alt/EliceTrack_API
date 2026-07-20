# fixtures/schedule_fixture.py
"""Elice 수업일정(Schedule) 전용 API 픽스처 — 사전 준비(인증·세션·클라이언트·조회 파라미터)만 담당."""
import logging

import pytest

from api.endpoints import schedule_api as schedule
from api.utils.elice_auth import get_env_config, make_authenticated_session

logger = logging.getLogger(__name__)


def _make_schedule_client(env_name: str, role: str, skip_msg: str) -> schedule.ScheduleAPI:
    """인증 정보가 없으면 skip, 있으면 Bearer 세션이 세팅된 ScheduleAPI를 생성한다."""
    session = make_authenticated_session(env_name, role)
    if session is None:
        pytest.skip(skip_msg)

    env = get_env_config(env_name)
    return schedule.ScheduleAPI(
        session,
        env_name=env_name,
        role=role,
        org=env["ORG"],
        classroom_id=env["CLASSROOM_ID"],
    )


@pytest.fixture(scope="session")
def schedule_prod_learner() -> schedule.ScheduleAPI:
    """prod 학습자 수업일정 클라이언트."""
    return _make_schedule_client("prod", "LEARNER", "prod 학습자 토큰 없음 (PROD_LEARNER_TOKEN)")


@pytest.fixture(scope="session")
def schedule_dev_educator() -> schedule.ScheduleAPI:
    """dev 교육자 수업일정 클라이언트."""
    return _make_schedule_client("dev", "EDUCATOR", "dev 교육자 인증 정보 없음 (EDUCATOR_LOGIN_ID/PASSWORD)")


@pytest.fixture(scope="function")
def schedule_query_params() -> schedule.ScheduleQueryParams:
    """CS-001 등 기간 조회 TC에 사용할 dt_start_ge/le, count 파라미터."""
    return schedule.resolve_schedule_query_params()
