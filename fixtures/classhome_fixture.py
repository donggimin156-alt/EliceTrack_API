# fixtures/classhome_fixture.py
"""클래스 홈 / 학습현황 API 픽스처.

인증은 api.utils.elice_auth.make_authenticated_session()으로 처리한다.
board_fixture의 prod_learner 등 공유 픽스처에 의존하지 않고 독립적으로 세션을 생성한다.
URL, org, classroom_id는 core.config.settings SSOT에서만 가져온다.
"""
import os

import pytest

from api.endpoints.classroom_api import ClassroomAPI
from api.endpoints.dashboard_api import DashboardAPI
from api.utils.elice_auth import get_env_config, make_authenticated_session

# ── classroom 테스트 공통 parametrize ──────────────────────────────────────────
CLASSROOM_CLIENTS = [
    pytest.param("prod_classroom_api",         marks=pytest.mark.learner,  id="prod-learner"),
    pytest.param("dev_educator_classroom_api", marks=pytest.mark.educator, id="dev-educator"),
]

# ── dashboard 테스트 공통 parametrize ─────────────────────────────────────────
# 학습자·교육자·운영·dev 전부 동일한 결과를 확인하는 sad-path 케이스용 (api_fixture, class_id_fixture)
DASHBOARD_CLIENTS = [
    pytest.param("prod_learner_dashboard_api", "prod_class_id", marks=pytest.mark.learner,  id="prod-learner"),
    pytest.param("dev_learner_dashboard_api",  "dev_class_id",  marks=pytest.mark.learner,  id="dev-learner"),
    pytest.param("dev_educator_dashboard_api", "dev_class_id",  marks=pytest.mark.educator, id="dev-educator"),
]

# 학습자 토큰으로 운영·dev 양쪽 실행하는 케이스용 (api_fixture, class_id_fixture)
DASHBOARD_LEARNER_CLIENTS = [
    pytest.param("prod_learner_dashboard_api", "prod_class_id", marks=pytest.mark.learner, id="prod-learner"),
    pytest.param("dev_learner_dashboard_api",  "dev_class_id",  marks=pytest.mark.learner, id="dev-learner"),
]

# 본인 account_id 조회 케이스용 (api_fixture, class_id_fixture, account_id_fixture)
DASHBOARD_LEARNER_ACCOUNT_PAIRS = [
    pytest.param("prod_learner_dashboard_api", "prod_class_id", "prod_learner_account_id", marks=pytest.mark.learner, id="prod-learner"),
    pytest.param("dev_learner_dashboard_api",  "dev_class_id",  "dev_learner_account_id",  marks=pytest.mark.learner, id="dev-learner"),
]


def _make_classroom_client(env_name: str, role: str, skip_msg: str) -> ClassroomAPI:
    session = make_authenticated_session(env_name, role)
    if session is None:
        pytest.skip(skip_msg)
    env = get_env_config(env_name)
    classroom_id = env.get("CLASSROOM_ID", "").strip()
    if not classroom_id:
        pytest.skip(f"{env_name.upper()} CLASSROOM_ID 미설정 — .env에 추가하세요")
    return ClassroomAPI(
        session=session,
        org=env["ORG"],
        classroom_id=classroom_id,
        env=env_name,
    )


def _make_dashboard_client(env_name: str, role: str, skip_msg: str) -> DashboardAPI:
    session = make_authenticated_session(env_name, role)
    if session is None:
        pytest.skip(skip_msg)
    env = get_env_config(env_name)
    return DashboardAPI(
        session=session,
        org=env["ORG"],
        env=env_name,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Classroom API 픽스처
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def prod_classroom_api() -> ClassroomAPI:
    return _make_classroom_client("prod", "LEARNER", "prod 학습자 토큰 없음 (PROD_LEARNER_TOKEN)")


@pytest.fixture(scope="session")
def dev_educator_classroom_api() -> ClassroomAPI:
    return _make_classroom_client("dev", "EDUCATOR", "dev 교육자 인증 정보 없음 (DEV_EDUCATOR_TOKEN)")


@pytest.fixture(scope="session")
def prod_class_id() -> str:
    val = get_env_config("prod").get("CLASSROOM_ID", "").strip()
    if not val:
        pytest.skip("PROD CLASSROOM_ID 미설정 — .env에 추가하세요")
    return val


@pytest.fixture(scope="session")
def dev_class_id() -> str:
    val = get_env_config("dev").get("CLASSROOM_ID", "").strip()
    if not val:
        pytest.skip("DEV CLASSROOM_ID 미설정 — .env에 추가하세요")
    return val


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard API 픽스처 (학습현황)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def prod_learner_dashboard_api() -> DashboardAPI:
    return _make_dashboard_client("prod", "LEARNER", "prod 학습자 토큰 없음 (PROD_LEARNER_TOKEN)")


@pytest.fixture(scope="session")
def dev_learner_dashboard_api() -> DashboardAPI:
    return _make_dashboard_client("dev", "LEARNER", "dev 학습자 인증 정보 없음 (DEV_LEARNER_TOKEN)")


@pytest.fixture(scope="session")
def dev_educator_dashboard_api() -> DashboardAPI:
    return _make_dashboard_client("dev", "EDUCATOR", "dev 교육자 인증 정보 없음 (DEV_EDUCATOR_TOKEN)")


# ── 학습현황 계정 ID 픽스처 ────────────────────────────────────────────────────

def _int_env(var: str, skip_msg: str) -> int:
    """환경변수를 int로 읽고, 없으면 skip."""
    val = os.getenv(var, "").strip()
    if not val:
        pytest.skip(skip_msg)
    return int(val)


@pytest.fixture(scope="session")
def prod_learner_account_id() -> int:
    """prod 학습자 account_id (PROD_LEARNER_ACCOUNT_ID 환경변수 — JWT의 _id 필드)."""
    return _int_env("PROD_LEARNER_ACCOUNT_ID", "PROD_LEARNER_ACCOUNT_ID 미설정 — .env에 추가하세요 (예: 8926240)")


@pytest.fixture(scope="session")
def dev_learner_account_id() -> int:
    """학습자 본인 account_id (DEV_LEARNER_ACCOUNT_ID 환경변수)."""
    return _int_env("DEV_LEARNER_ACCOUNT_ID", "DEV_LEARNER_ACCOUNT_ID 미설정 — .env에 추가하세요")


@pytest.fixture(scope="session")
def dev_educator_account_id() -> int:
    """교육자 account_id — Student 테이블에 없는 id (DEV_EDUCATOR_ACCOUNT_ID 환경변수).

    CH-028: 학습자 토큰으로 교육자 id 조회 시 409 확인용.
    """
    return _int_env("DEV_EDUCATOR_ACCOUNT_ID", "DEV_EDUCATOR_ACCOUNT_ID 미설정 — .env에 추가하세요")


@pytest.fixture(scope="session")
def prod_other_account_id() -> int:
    """prod 타인 학습자 account_id — IDOR 검증용 (PROD_OTHER_ACCOUNT_ID 환경변수).

    게시판 API author 필드 등 정상 경로로 확보한 값 사용 (브루트포스 아님).
    TC 실측값 예시: 8923361
    """
    return _int_env("PROD_OTHER_ACCOUNT_ID", "PROD_OTHER_ACCOUNT_ID 미설정 — .env에 추가하세요 (예: 8923361)")
