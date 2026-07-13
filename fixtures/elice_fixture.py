# fixtures/elice_fixture.py
"""Elice QA 프로젝트 전용 API 픽스처.

학습자(Learner) / 교육자(Educator) 두 역할의 인증된 API 클라이언트를 제공합니다.
인증 방식: POST /login/pw → Bearer token
"""
import os
import logging

import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_TIMEOUT = float(os.getenv("ELICE_API_TIMEOUT", "10"))

_ENVS = {
    "dev": {
        "BASE_URL": "https://dev-qatrack-api.dev.elicer.io",
        "AUTH_URL": "https://dev-qatrack-account-api.dev.elicer.io",
        "ORG": "academy",
        "CLASSROOM_ID": os.getenv("DEV_CLASSROOM_ID", "22e01595-3c49-4605-8239-fe3473cd7e07"),
        "BOARD_ID": os.getenv("DEV_BOARD_ID", "1"),
        "OTHERS_ARTICLE_ID": os.getenv("DEV_OTHERS_ARTICLE_ID", "1"),
    },
    "prod": {
        "BASE_URL": "https://api-rest.elice.io",
        "AUTH_URL": "https://api-account.elice.io",
        "ORG": "qatrack",
        "CLASSROOM_ID": os.getenv("PROD_CLASSROOM_ID", "a647c7c0-1e15-4196-97fd-d6e4dea84b2c"),
        "BOARD_ID": os.getenv("PROD_BOARD_ID", "10187"),
        "OTHERS_ARTICLE_ID": os.getenv("PROD_OTHERS_ARTICLE_ID", "78933"),
    },
}


class EliceApiClient:
    """Elice API 통신 클라이언트.

    인증 헤더 + org 헤더가 미리 세팅된 requests.Session을 래핑합니다.
    url() / get() / post() 로 간결하게 호출 가능합니다.
    """

    def __init__(self, env_name: str, role: str, token: str):
        e = _ENVS[env_name]
        self.env = env_name
        self.role = role
        self.base = e["BASE_URL"].rstrip("/")
        self.auth_url = e["AUTH_URL"].rstrip("/")
        self.org = e["ORG"]
        self.classroom_id = e["CLASSROOM_ID"]
        self.board_id = e["BOARD_ID"]
        self.others_article_id = e["OTHERS_ARTICLE_ID"]

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "x-elice-org-name-short": self.org,
        })

    def url(self, path: str) -> str:
        return f"{self.base}/org/{self.org}/{path.lstrip('/')}"

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.session.get(self.url(path), timeout=_TIMEOUT, **kwargs)

    def post(self, path: str, data: dict | None = None, json: dict | None = None, **kwargs) -> requests.Response:
        return self.session.post(self.url(path), data=data, json=json, timeout=_TIMEOUT, **kwargs)

    # ── 게시판 게시글 (board/article) ──
    def create_article(self, title: str, content: str, is_secret: bool = False,
                       classroom_id: str | None = None) -> requests.Response:
        """게시글 작성. board_article_id 없이 POST → 신규 작성 (명세: 게시글 작성)."""
        data = {
            "title": title,
            "content": content,
            "is_secret": "true" if is_secret else "false",
            "classroom_id": classroom_id or self.classroom_id,
        }
        return self.post("board/article/edit/", data=data)

    def delete_article(self, board_article_id: int) -> requests.Response:
        """게시글 삭제 (명세: 게시글 삭제). 정리(teardown)용으로도 사용."""
        return self.post("board/article/delete/", data={"board_article_id": board_article_id})


def _login(env_name: str, login_id: str, password: str) -> str:
    auth_url = _ENVS[env_name]["AUTH_URL"].rstrip("/")
    resp = requests.post(
        f"{auth_url}/login/pw",
        json={"login_id": login_id, "password": password},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _resolve_token(env_name: str, role: str) -> str | None:
    """환경변수에서 토큰 또는 로그인 정보를 가져와 access_token을 반환."""
    prefix = f"{env_name.upper()}_{role}"
    token = os.getenv(f"{prefix}_TOKEN", "").strip()
    if token:
        return token
    # prod는 카카오 로그인이라 /login/pw 불가 → 토큰만 허용.
    # 접두사 없는 LEARNER_LOGIN_ID 등(=dev 계정)이 prod 로그인에 잘못 쓰이지 않도록 dev로 제한.
    if env_name == "dev":
        login_id = os.getenv(f"{prefix}_LOGIN_ID") or os.getenv(f"{role}_LOGIN_ID")
        password = os.getenv(f"{prefix}_PASSWORD") or os.getenv(f"{role}_PASSWORD")
    else:
        login_id = os.getenv(f"{prefix}_LOGIN_ID")
        password = os.getenv(f"{prefix}_PASSWORD")
    if login_id and password:
        return _login(env_name, login_id, password)
    return None


def _make_client(env_name: str, role: str, skip_msg: str) -> EliceApiClient:
    token = _resolve_token(env_name, role)
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
