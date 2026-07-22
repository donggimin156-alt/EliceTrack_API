# fixtures/board_fixture.py
"""Elice 게시판(Board) API 전용 픽스처 — 인증·BoardApiClient·teardown 정리."""
import logging
import os

import pytest
from dotenv import load_dotenv

from api.endpoints.board_api import BoardApiClient
from api.utils.elice_auth import make_authenticated_session
from utils.helpers.api_assertions import assert_board_fail, assert_board_ok

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
def make_article(track_articles):
    """제목·내용을 지정해 본인 글을 생성하고 자동정리에 등록한 뒤 board_article_id를 반환하는 팩토리.

    사용: aid = make_article(board, "제목", "<p>내용</p>")
    생성 성공 검증(200 + _result.status=='ok')과 track_articles 등록까지 처리하므로
    테스트는 정리를 신경 쓸 필요가 없다(시그니처에 track_articles를 받지 않아도 됨).

    작성자를 바꿔 넘기면 cross-account 시나리오의 사전 준비로도 쓸 수 있다.
    (예: make_article(dev_educator, ...) 로 교육자 글을 만들고 학습자로 검증)
    """
    def _make(client, title="테스트 글", content="<p>내용</p>", is_secret=False):
        body = assert_board_ok(client.create_article(title, content, is_secret=is_secret))
        article_id = body.get("board_article_id")
        assert isinstance(article_id, int), f"setup 게시글 생성 실패: {body}"
        track_articles.append((client, article_id))
        return article_id

    return _make


@pytest.fixture
def own_article(board, make_article):
    """기본 내용의 본인 글 1개를 생성하고 board_article_id를 반환하는 setup 픽스처.

    class_fixture의 course_list처럼 "생성 시점에 성공 검증 + 데이터 반환"한다.
    제목·내용을 지정해야 하면 make_article 팩토리를 직접 사용한다.
    """
    return make_article(board)


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
