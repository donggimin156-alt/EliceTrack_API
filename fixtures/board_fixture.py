# fixtures/board_fixture.py
"""Elice 게시판(Board) API 전용 픽스처 — 인증·BoardApiClient·teardown 정리."""
import logging
import os

import pytest
from dotenv import load_dotenv

from api.utils.board_api import BoardApiClient
from api.utils.elice_auth import make_authenticated_session
from utils.assertions.api_assertions import assert_board_fail, assert_board_ok

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
def board(request) -> BoardApiClient:
    """공통 테스트용 board 클라이언트 (COMMON_TARGETS로 indirect 파라미터화).

    request.param(픽스처 이름, 예: "prod_learner"/"dev_educator")을 해석해
    해당 board 클라이언트를 반환한다.
    사용: @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    """
    return request.getfixturevalue(request.param)


# ── 검증 헬퍼 주입 (로직은 utils/assertions, class_fixture처럼 픽스처로 받아 사용) ──


@pytest.fixture
def board_ok():
    """게시판 성공 판정 헬퍼 주입: assert_board_ok(resp) → (200 + _result.status=='ok') 검증 후 body 반환."""
    return assert_board_ok


@pytest.fixture
def board_fail():
    """게시판 실패 판정 헬퍼 주입: assert_board_fail(resp, fail_code=, status_code=, reason=)."""
    return assert_board_fail


@pytest.fixture
def own_article(board, track_articles):
    """본인 글 1개 생성(200 확인) + 자동정리 등록 후 board_article_id 반환.

    class_fixture의 course_list처럼 "생성 시점에 성공 검증 + 데이터 반환"하는 setup 픽스처.
    수정/삭제/댓글/좋아요 등 "기존 글에 대해" 검증하는 테스트의 사전 준비용.
    """
    resp = board.create_article("테스트 글", "<p>내용</p>", is_secret=False)
    body = assert_board_ok(resp)
    article_id = body["board_article_id"]
    track_articles.append((board, article_id))
    return article_id


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
