# api/utils/board_client.py
"""Elice 게시판(Board) REST API 클라이언트.

BaseAPIClient(통신 엔진)를 상속하고, org-scoped 경로와 게시판 도메인 메서드를 제공한다.
인증(Bearer + org 헤더)은 fixtures/elice_auth.make_authenticated_session에서 session에 세팅한다.
"""
import requests

from api.base_client import BaseAPIClient
from core.config import settings


class BoardApiClient(BaseAPIClient):
    """게시판 REST API 클라이언트.

    org-scoped 경로(`org/{org}/...`)를 자동으로 붙여준다.
    URL/org/classroom_id 등은 core.config.settings.elice_environments(SSOT)에서 가져온다.
    """

    def __init__(
        self,
        session: requests.Session,
        *,
        env_name: str,
        role: str,
    ) -> None:
        env_config = settings.elice_environments[env_name]
        super().__init__(
            session,
            raise_for_status=False,
            base_url=env_config["REST_API_URL"].rstrip("/"),
            timeout=(5, int(settings.elice_api_timeout)),
            client_name=f"Board-{env_name}-{role}",
        )
        self.env_name = env_name
        self.role = role
        self.org = env_config["ORG"]
        self.classroom_id = env_config["CLASSROOM_ID"]
        self.board_id = env_config["BOARD_ID"]
        self.others_article_id = env_config["OTHERS_ARTICLE_ID"]

    def _scoped(self, path: str) -> str:
        return f"org/{self.org}/{path.lstrip('/')}"

    def get(self, path: str, **kwargs) -> requests.Response:
        return super().get(self._scoped(path), **kwargs)

    def post(
        self,
        path: str,
        data: dict | None = None,
        json: dict | None = None,
        **kwargs,
    ) -> requests.Response:
        return super().post(self._scoped(path), data=data, json=json, **kwargs)

    def create_article(
        self,
        title: str,
        content: str,
        is_secret: bool = False,
        classroom_id: str | None = None,
    ) -> requests.Response:
        """게시글 작성. board_article_id 없이 POST → 신규 작성."""
        data = {
            "title": title,
            "content": content,
            "is_secret": "true" if is_secret else "false",
            "classroom_id": classroom_id or self.classroom_id,
        }
        return self.post("board/article/edit/", data=data)

    def delete_article(self, board_article_id: int) -> requests.Response:
        """게시글 삭제. track_articles teardown 정리용."""
        return self.post("board/article/delete/", data={"board_article_id": board_article_id})
