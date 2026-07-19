# fixtures/elice_fixture.py
"""Elice QA 프로젝트 게시판(Board) API 픽스처.

학습자(Learner) / 교육자(Educator) 두 역할의 인증된 Board API 클라이언트를 제공합니다.

통신 로직(로깅/cURL 재현/SLA 체크)은 BaseAPIClient가 담당하고,
인증 토큰 해석은 fixtures/elice_auth.py (SSOT)를 사용합니다.
"""
import os
import logging

import pytest
from dotenv import load_dotenv

from api.utils.elice_client import EliceApiClient
from fixtures.elice_auth import resolve_token

load_dotenv()

logger = logging.getLogger(__name__)


def _make_client(env_name: str, role: str, skip_msg: str) -> EliceApiClient:
    token = resolve_token(env_name, role)
    if not token:
        pytest.skip(skip_msg)
    return EliceApiClient(env_name, role, token)


TARGET = os.getenv("TARGET", "dev").lower()


# ──────────────────────────────────────────────
# 공개 픽스처 (테스트 파일에서 직접 사용)
# ──────────────────────────────────────────────

@pytest.fixture(scope="session")
def elice_learner() -> EliceApiClient:
    """현재 TARGET 환경의 학습자 계정 클라이언트."""
    return _make_client(TARGET, "LEARNER", f"[{TARGET}] 학습자 인증 정보 없음 (LEARNER_LOGIN_ID/PASSWORD)")


@pytest.fixture(scope="session")
def elice_educator() -> EliceApiClient:
    """현재 TARGET 환경의 교육자(기관 관리자) 계정 클라이언트."""
    return _make_client(TARGET, "EDUCATOR", f"[{TARGET}] 교육자 인증 정보 없음 (EDUCATOR_LOGIN_ID/PASSWORD)")


# ──────────────────────────────────────────────
# 환경 고정 픽스처 (TARGET 무관 — TC 시트의 서버 지정에 맞춤)
#   prod: 단일 계정(학습자 토큰) / dev: 2계정(로그인)
# ──────────────────────────────────────────────

@pytest.fixture(scope="session")
def prod_learner() -> EliceApiClient:
    """prod 학습자 (카카오 로그인 → PROD_LEARNER_TOKEN)."""
    return _make_client("prod", "LEARNER", "prod 학습자 토큰 없음 (PROD_LEARNER_TOKEN)")


@pytest.fixture(scope="session")
def dev_learner() -> EliceApiClient:
    """dev 학습자 (/login/pw → LEARNER_LOGIN_ID/PASSWORD)."""
    return _make_client("dev", "LEARNER", "dev 학습자 인증 정보 없음 (LEARNER_LOGIN_ID/PASSWORD)")


@pytest.fixture(scope="session")
def dev_educator() -> EliceApiClient:
    """dev 교육자(기관 관리자) (/login/pw → EDUCATOR_LOGIN_ID/PASSWORD). 교육자는 dev에만 존재."""
    return _make_client("dev", "EDUCATOR", "dev 교육자 인증 정보 없음 (EDUCATOR_LOGIN_ID/PASSWORD)")


@pytest.fixture
def track_articles():
    """생성한 게시글을 테스트 종료 후 자동 삭제.

    테스트에서 (client, board_article_id) 튜플을 append 하면 teardown에서 역순으로 삭제.
    """
    created: list[tuple[EliceApiClient, int]] = []
    yield created
    for client, article_id in reversed(created):
        try:
            client.delete_article(article_id)
        except Exception as e:  # 정리 실패가 테스트 결과에 영향을 주지 않도록 흡수
            logger.warning("track_articles 정리 실패 (id=%s): %s", article_id, e)
