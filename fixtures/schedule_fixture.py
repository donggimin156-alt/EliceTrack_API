# fixtures/schedule_fixture.py
"""Elice 수업일정(Schedule) 전용 API 픽스처 — 사전 준비(인증·세션·클라이언트·조회 파라미터)만 담당"""
import logging

import pytest

from api.endpoints import schedule_api as schedule
from api.utils.elice_auth import make_authenticated_session

logger = logging.getLogger(__name__)


def _make_schedule_client(env_name: str, role: str, skip_msg: str) -> schedule.ScheduleAPI:
    """인증 정보가 없으면 skip, 있으면 Bearer 세션이 세팅된 ScheduleAPI를 생성한다"""
    session = make_authenticated_session(env_name, role)
    if session is None:
        pytest.skip(skip_msg)

    return schedule.ScheduleAPI(session, env_name=env_name)


@pytest.fixture(scope="session")
def schedule_prod_learner() -> schedule.ScheduleAPI:
    """prod 학습자 수업일정 클라이언트"""
    return _make_schedule_client("prod", "LEARNER", "prod 학습자 토큰 없음 (PROD_LEARNER_TOKEN)")


@pytest.fixture(scope="session")
def schedule_dev_educator() -> schedule.ScheduleAPI:
    """dev 교육자 수업일정 클라이언트"""
    return _make_schedule_client("dev", "EDUCATOR", "dev 교육자 인증 정보 없음 (EDUCATOR_LOGIN_ID/PASSWORD)")


@pytest.fixture(scope="session")
def schedule_dev_learner() -> schedule.ScheduleAPI:
    """dev 학습자 수업일정 클라이언트 (CS-AUTH-03 등)"""
    return _make_schedule_client(
        "dev",
        "LEARNER",
        "dev 학습자 인증 정보 없음 (LEARNER_LOGIN_ID/PASSWORD 또는 DEV_LEARNER_TOKEN)",
    )


@pytest.fixture(scope="function")
def schedule_query_params() -> schedule.ScheduleQueryParams:
    """CS-001 등 기간 조회 TC에 사용할 dt_start_ge/le, count 파라미터"""
    return schedule.resolve_schedule_query_params()


@pytest.fixture(scope="session")
def schedule_course_id() -> int:
    """prod REST course/get — env SCHEDULE_COURSE_ID (기본 770265). dev bulk 템플릿·course_id와 별개."""
    return schedule.resolve_schedule_course_id()


@pytest.fixture(scope="session")
def schedule_dev_attached_course_id(schedule_dev_educator: schedule.ScheduleAPI) -> int:
    """dev REST course/get용 course_id — bulk attach로 확보, session 종료 시 DELETE teardown.

    setup: DEV_BULK_ADD_COURSE_ID(341, 「2팀 테스트 과목」) 템플릿 bulk → diff로 실제 course_id 추출.
    사용 TC: CS-AUTH-02·CS-002 dev 교육자 row (CS-002 test_CS_002 포함).
    teardown: DELETE /classroom/{id}/course/{course_id}, 기대 HTTP 200.
    """
    try:
        course_id = schedule.resolve_dev_attached_course_id(schedule_dev_educator)
    except (TimeoutError, ValueError) as e:
        pytest.fail(f"dev schedule용 course_id 확보 실패: {e}")

    yield course_id

    try:
        schedule.teardown_dev_attached_course(schedule_dev_educator, course_id)
    except Exception as e:
        logger.warning(
            "schedule_dev_attached_course_id teardown 실패 (course_id=%s): %s",
            course_id,
            e,
        )
