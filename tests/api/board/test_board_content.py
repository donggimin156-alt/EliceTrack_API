# tests/api/board/test_board_content.py
"""게시글 본문 처리 API 테스트 (HTML 보존/XSS/공백/대용량/작성-조회 일관성).

게시판 규약: HTTP는 항상 200, 성공/실패는 body `_result.status`(ok/fail)로 판정.
역할(target)은 COMMON_TARGETS로 파라미터화(학습자→prod, 교육자→dev).
명세 대조 기준: Notion "dev_게시판 API 명세 (실측)".
"""
import pytest

from api.schemas.board_schema import BoardSchemas
from fixtures.board_fixture import COMMON_TARGETS
from utils.helpers.api_assertions import assert_valid_schema


@pytest.mark.api
@pytest.mark.board
class TestBoardContent:
    """게시글 본문 처리 API 테스트 (HTML 보존/XSS/공백/대용량/작성-조회 일관성)."""

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_057_html_content_preserved(self, board, make_article):
        """BRD-057 content 허용 HTML 태그 보존 검증 (공통).

        기대: 허용 태그(p, b, i 등)는 get/ 응답에 원문 그대로 보존.
        """
        content = "<p><b>굵게</b><i>기울임</i></p>"
        aid = make_article(board, title="HTML 태그 글", content=content)

        stored = board.get_article(aid).json()["board_article"]["content"]
        assert stored == content, stored

    @pytest.mark.bug
    @pytest.mark.security
    @pytest.mark.jira("EQA-12")
    @pytest.mark.xfail(reason="V7#4 저장형 XSS: content 미새니타이징. 고쳐지면 XPASS로 알림", strict=False)
    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_058_xss_content_sanitized(self, board, make_article):
        """BRD-058 [버그] content 위험 태그 미새니타이징 (저장형 XSS) (공통).

        보안 기대: 위험 태그/속성은 제거 또는 이스케이프되어 원문 그대로 저장되면 안 됨.
        실측(V7#4 버그): script/onerror/iframe 등이 원문 그대로 저장·반환됨 → 아래 assert 실패 → xfail.
        """
        payload = "<img src=x onerror=alert(1)><iframe src=//evil></iframe>"
        aid = make_article(board, title="XSS 글", content=payload)

        stored = board.get_article(aid).json()["board_article"]["content"]
        assert payload not in stored, f"위험 페이로드가 그대로 저장됨(XSS 버그): {stored}"

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_059_whitespace_content_allowed(self, board, track_articles, board_ok):
        """BRD-059 content 공백만 입력 처리 확인 (공통).

        기대: content=' '(공백)도 허용 → _result.status=='ok', board_article_id 반환.
        """
        resp = board.create_article("공백 content 글", " ", is_secret=False)
        body = board_ok(resp)
        aid = body.get("board_article_id")
        assert isinstance(aid, int), body
        track_articles.append((board, aid))

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_060_large_content(self, board, track_articles):
        """BRD-060 content 대용량(약 10만자) 처리 확인 (공통).

        기대: 정상 처리(ok) 또는 명시적 제한(fail) — 5xx/타임아웃 없어야 함(HTTP 200).
        """
        resp = board.create_article("대용량 content 글", "a" * 100000, is_secret=False)
        assert resp.status_code == 200, resp.text  # 5xx/타임아웃 없어야
        body = resp.json()
        assert body["_result"]["status"] in ("ok", "fail"), body
        aid = body.get("board_article_id")
        if isinstance(aid, int):
            track_articles.append((board, aid))

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_061_write_read_consistency(self, board, make_article):
        """BRD-061 작성 직후 반환 id 즉시 조회 (write-read 일관성) (공통).

        기대: 즉시 조회 성공, title/content 작성값과 일치.
        """
        title, content = "즉시조회 제목", "<p>즉시조회 내용</p>"

        aid = make_article(board, title, content, is_secret=False)

        art = board.get_article(aid).json()["board_article"]
        assert_valid_schema(art, BoardSchemas.BOARD_ARTICLE)
        assert art["id"] == aid, art
        assert art["title"] == title, art
        assert art["content"] == content, art
