# api/utils/board_api.py
"""Elice 게시판(Board) REST API 클라이언트.

BaseAPIClient(통신 엔진: 로깅/재시도/추적/Request-ID)를 상속하고, org-scoped 경로와
게시판 도메인 메서드(게시글·댓글·좋아요·첨부·게시판 관리)를 제공한다.
인증(Bearer + org 헤더)은 fixtures/elice_auth.make_authenticated_session에서 session에 세팅한다.

게시판 규약: HTTP는 항상 200, 성공/실패는 body `_result.status`(ok/fail)로 판정.
게시글 목록 count는 1~20만 허용(초과 시 invalid_parameter).
URL/org/classroom_id 등은 core.config.settings.elice_environments(SSOT)에서 가져온다.
"""
import requests

from api.base_client import BaseAPIClient
from core.config import settings


class BoardApiClient(BaseAPIClient):
    """게시판 REST API 클라이언트.

    org-scoped 경로(`org/{org}/...`)를 자동으로 붙여준다.
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
            timeout=settings.api_timeout,
            client_name=f"Board-{env_name}-{role}",
        )
        # 게시판은 form(x-www-form-urlencoded) / multipart 바디를 쓴다.
        # BaseAPIClient가 강제하는 Content-Type: application/json 을 제거해
        # requests가 data=/files=/json= 에 맞춰 Content-Type을 자동 설정하도록 위임한다.
        # (강제 json이면 폼 바디가 json으로 잘못 파싱되어 invalid_parameter로 실패)
        self.default_headers.pop("Content-Type", None)

        self.env_name = env_name
        self.role = role
        self.org = env_config["ORG"]
        self.classroom_id = env_config["CLASSROOM_ID"]
        self.board_id = env_config["BOARD_ID"]
        self.others_article_id = env_config["OTHERS_ARTICLE_ID"]
        # 인증/헤더 음성 테스트에서 헤더를 직접 조립할 때 쓰도록 원본 토큰을 노출한다.
        self.token = session.headers.get("Authorization", "").removeprefix("Bearer ").strip()

    # ── 경로 스코프 / URL ──
    def _scoped(self, path: str) -> str:
        return f"org/{self.org}/{path.lstrip('/')}"

    def _abs(self, path: str) -> str:
        """org-scoped 절대 URL (session 직접 호출 / raw 음성 테스트용)."""
        return f"{self.base_url}/{self._scoped(path)}"

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

    def raw(self, method: str, path: str, headers: dict | None = None, **kwargs) -> requests.Response:
        """세션 기본 헤더(인증/org)를 쓰지 않고 주어진 headers만으로 요청.

        인증/헤더 음성 테스트(토큰 없음·오류, org 헤더 누락)용.
        """
        return requests.request(method, self._abs(path), headers=headers or {}, timeout=self.timeout, **kwargs)

    # ── 게시글 (board/article) ──
    def create_article(
        self,
        title: str,
        content: str,
        is_secret: bool = False,
        classroom_id: str | None = None,
    ) -> requests.Response:
        """게시글 작성. board_article_id 없이 POST → 신규 작성."""
        return self.post("board/article/edit/", data={
            "title": title,
            "content": content,
            "is_secret": "true" if is_secret else "false",
            "classroom_id": classroom_id or self.classroom_id,
        })

    def create_article_raw(self, data: dict) -> requests.Response:
        """게시글 작성 원본 폼 호출 (음성/경계 테스트용 — 필수 필드 누락 등 임의 payload)."""
        return self.post("board/article/edit/", data=data)

    def update_article(
        self,
        board_article_id: int,
        title: str,
        content: str,
        is_secret: bool = False,
        classroom_id: str | None = None,
    ) -> requests.Response:
        """게시글 수정. board_article_id 포함 → 기존 글 수정 (본인만)."""
        return self.post("board/article/edit/", data={
            "board_article_id": board_article_id,
            "title": title,
            "content": content,
            "is_secret": "true" if is_secret else "false",
            "classroom_id": classroom_id or self.classroom_id,
        })

    def get_article(self, board_article_id: int) -> requests.Response:
        """게시글 단건조회."""
        return self.get("board/article/get/", params={"board_article_id": board_article_id})

    def delete_article(self, board_article_id: int) -> requests.Response:
        """게시글 삭제. track_articles teardown 정리용으로도 사용."""
        return self.post("board/article/delete/", data={"board_article_id": board_article_id})

    def list_articles(
        self,
        offset: int = 0,
        count: int = 20,
        board_id: int | str | None = None,
    ) -> requests.Response:
        """게시글 목록. count는 1~20."""
        return self.get("board/article/list/", params={
            "board_id": board_id or self.board_id,
            "offset": offset,
            "count": count,
        })

    # ── 게시글 좋아요 (board/article/like) ──
    def like_add(self, board_article_id: int) -> requests.Response:
        return self.post("board/article/like/add/", data={"board_article_id": board_article_id})

    def like_delete(self, board_article_id: int) -> requests.Response:
        return self.post("board/article/like/delete/", data={"board_article_id": board_article_id})

    def like_list(self, board_article_id: int) -> requests.Response:
        return self.get("board/article/like/list/", params={"board_article_id": board_article_id})

    # ── 댓글 (board/article/comment) ──
    def create_comment(self, board_article_id: int, content: str) -> requests.Response:
        """댓글 작성 (article_comment_id 없이 → 신규)."""
        return self.post("board/article/comment/edit/", data={
            "board_article_id": board_article_id,
            "content": content,
        })

    def update_comment(self, article_comment_id: int, board_article_id: int, content: str) -> requests.Response:
        """댓글 수정 (article_comment_id 포함 → 기존 댓글, 본인만)."""
        return self.post("board/article/comment/edit/", data={
            "article_comment_id": article_comment_id,
            "board_article_id": board_article_id,
            "content": content,
        })

    def comment_edit_raw(self, data: dict) -> requests.Response:
        """댓글 작성/수정 원본 폼 호출 (음성 테스트용 임의 payload)."""
        return self.post("board/article/comment/edit/", data=data)

    def get_comment(self, article_comment_id: int) -> requests.Response:
        """댓글 단건조회."""
        return self.get("board/article/comment/get/", params={"article_comment_id": article_comment_id})

    def list_comments(self, board_article_id: int, count: int = 20, offset: int = 0) -> requests.Response:
        """댓글 목록 (count는 1 이상 필수)."""
        return self.get("board/article/comment/list/", params={
            "board_article_id": board_article_id,
            "count": count,
            "offset": offset,
        })

    def delete_comment(self, article_comment_id: int) -> requests.Response:
        """댓글 삭제 (권한검사 O — 타인 댓글은 insufficient_permission)."""
        return self.post("board/article/comment/delete/", data={"article_comment_id": article_comment_id})

    # ── 댓글 좋아요 (board/article/comment/like) ──
    def comment_like_add(self, article_comment_id: int) -> requests.Response:
        return self.post("board/article/comment/like/add/", data={"article_comment_id": article_comment_id})

    def comment_like_delete(self, article_comment_id: int) -> requests.Response:
        return self.post("board/article/comment/like/delete/", data={"article_comment_id": article_comment_id})

    def comment_like_list(self, article_comment_id: int) -> requests.Response:
        return self.get("board/article/comment/like/list/", params={"article_comment_id": article_comment_id})

    # ── 첨부파일 (global/remote_file, org 경로 아님 → session 직접 호출) ──
    @property
    def _attachment_url(self) -> str:
        return f"{self.base_url}/global/remote_file/attachment/upload/"

    def attachment_upload(
        self,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> requests.Response:
        """첨부파일 업로드 (multipart, 필드명 attachment_file). 성공 시 응답에 url 반환."""
        return self.session.post(
            self._attachment_url,
            files={"attachment_file": (filename, content, content_type)},
            timeout=30,
        )

    def attachment_upload_raw(self, *, files: dict | None = None, method: str = "POST") -> requests.Response:
        """첨부 업로드 원본(음성 테스트용: 파일 없음/다른 메서드)."""
        return self.session.request(method, self._attachment_url, files=files, timeout=30)

    def create_article_with_attachment(
        self,
        title: str,
        content: str,
        filename: str,
        file_content: bytes,
        is_secret: bool = False,
        classroom_id: str | None = None,
        content_type: str = "application/octet-stream",
    ) -> requests.Response:
        """게시글 작성 + 첨부 (multipart). 웹 UI처럼 board/article/edit/ 의 attachment_files 필드에
        파일 바이너리를 직접 실어 작성+첨부를 한 번에 처리 (별도 upload/ 미사용)."""
        data = {
            "title": title,
            "content": content,
            "is_secret": "true" if is_secret else "false",
            "classroom_id": classroom_id or self.classroom_id,
        }
        files = {"attachment_files": (filename, file_content, content_type)}
        return self.session.post(self._abs("board/article/edit/"), data=data, files=files, timeout=30)

    # ── 게시판(board) 관리 (관리자 전용 동작) ──
    def board_edit(self, data: dict) -> requests.Response:
        """게시판 생성/수정 (board/edit)."""
        return self.post("board/edit/", data=data)

    def board_move(self, board_id: int, order_no: int) -> requests.Response:
        """게시판 순서 변경 (board/move)."""
        return self.post("board/move/", data={"board_id": board_id, "order_no": order_no})
