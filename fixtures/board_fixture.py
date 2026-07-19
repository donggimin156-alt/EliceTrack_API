# fixtures/board_fixture.py
"""Elice 게시판(Board) API 전용 픽스처 — 인증·BoardApiClient·teardown 정리."""
import logging
import os

import pytest
from dotenv import load_dotenv

from api.utils.board_client import BoardApiClient
from fixtures.elice_auth import make_authenticated_session

load_dotenv()

logger = logging.getLogger(__name__)

TARGET = os.getenv("TARGET", "dev").lower()


def _make_board_client(env_name: str, role: str, skip_msg: str) -> BoardApiClient:
    """인증 정보가 없으면 skip, 있으면 Bearer 세션이 세팅된 BoardApiClient를 생성한다."""
    session = make_authenticated_session(env_name, role)
    if session is None:
        pytest.skip(skip_msg)

    return BoardApiClient(session, env_name=env_name, role=role)


# ── TARGET 기준 (현재 지정 환경) ──


@pytest.fixture(scope="session")
def board_learner() -> BoardApiClient:
    """현재 TARGET 환경의 학습자 게시판 클라이언트."""
    return _make_board_client(TARGET, "LEARNER", f"[{TARGET}] 학습자 인증 정보 없음 (LEARNER_LOGIN_ID/PASSWORD)")


@pytest.fixture(scope="session")
def board_educator() -> BoardApiClient:
    """현재 TARGET 환경의 교육자(기관 관리자) 게시판 클라이언트."""
    return _make_board_client(TARGET, "EDUCATOR", f"[{TARGET}] 교육자 인증 정보 없음 (EDUCATOR_LOGIN_ID/PASSWORD)")


# ── 환경 고정 (TC 시트 서버 지정 — prod: 학습자 토큰 / dev: 로그인) ──


@pytest.fixture(scope="session")
def prod_learner() -> BoardApiClient:
    """prod 학습자 (카카오 로그인 → PROD_LEARNER_TOKEN)."""
    return _make_board_client("prod", "LEARNER", "prod 학습자 토큰 없음 (PROD_LEARNER_TOKEN)")


@pytest.fixture(scope="session")
def dev_learner() -> BoardApiClient:
    """dev 학습자 (/login/pw → LEARNER_LOGIN_ID/PASSWORD)."""
    return _make_board_client("dev", "LEARNER", "dev 학습자 인증 정보 없음 (LEARNER_LOGIN_ID/PASSWORD)")


@pytest.fixture(scope="session")
def dev_educator() -> BoardApiClient:
    """dev 교육자(기관 관리자). 교육자는 dev에만 존재."""
    return _make_board_client("dev", "EDUCATOR", "dev 교육자 인증 정보 없음 (EDUCATOR_LOGIN_ID/PASSWORD)")


@pytest.fixture
def track_articles():
    """생성한 게시글을 테스트 종료 후 자동 삭제.

    테스트에서 (client, board_article_id) 튜플을 append 하면 teardown에서 역순으로 삭제.
    """
    created: list[tuple[BoardApiClient, int]] = []
    yield created
    for client, article_id in reversed(created):
        try:
            client.delete_article(article_id)
        except Exception as e:
            logger.warning("track_articles 정리 실패 (id=%s): %s", article_id, e)
