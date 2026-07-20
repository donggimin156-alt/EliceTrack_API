# fixtures/elice_auth.py
"""Elice API 테스트 공통 인증 유틸.

토큰 해석, /login/pw, Bearer session 생성 등 board/schedule/class fixture가
공유하는 인증 로직의 SSOT(Single Source of Truth).
"""
import os

import requests

from core.config import settings
from fixtures.api_fixture import HttpClientFactory


def login(env_name: str, login_id: str, password: str) -> str:
    """POST /login/pw 로 access_token을 발급받는다."""
    auth_url = settings.elice_environments[env_name]["AUTH_API_URL"].rstrip("/")
    resp = requests.post(
        f"{auth_url}/login/pw",
        json={"login_id": login_id, "password": password},
        timeout=settings.elice_api_timeout,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def resolve_token(env_name: str, role: str) -> str | None:
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
        return login(env_name, login_id, password)
    return None


def get_env_config(env_name: str) -> dict:
    """dev/prod 환경 설정 묶음(ORG, CLASSROOM_ID, API URL 등)을 반환."""
    return settings.elice_environments[env_name]


def make_authenticated_session(env_name: str, role: str) -> requests.Session | None:
    """
    resolve_token으로 토큰을 구하고, Bearer + org 헤더가 세팅된 Session을 반환.

    토큰/계정 정보가 없으면 None.
    """
    token = resolve_token(env_name, role)
    if not token:
        return None

    env = get_env_config(env_name)
    session = HttpClientFactory.create_session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "x-elice-org-name-short": env["ORG"],
    })
    return session
