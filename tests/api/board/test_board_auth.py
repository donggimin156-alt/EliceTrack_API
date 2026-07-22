# tests/api/board/test_board_auth.py
"""게시판 인증·권한 API 테스트 (미인증/잘못된 토큰/org 헤더/게시판 권한/타인 비밀글 차단).

게시판 규약: HTTP는 항상 200, 성공/실패는 body `_result.status`(ok/fail)로 판정.
역할(target)은 COMMON_TARGETS로 파라미터화(학습자→prod, 교육자→dev).
명세 대조 기준: Notion "dev_게시판 API 명세 (실측)".
"""
import pytest

from fixtures.board_fixture import COMMON_TARGETS, CROSS_ACCOUNT_DEV


@pytest.mark.api
@pytest.mark.board
class TestBoardAuth:
    """게시판 인증·권한 API 테스트 (미인증/잘못된 토큰/org 헤더/게시판 권한/타인 비밀글 차단)."""

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_052_get_article_no_auth(self, board, own_article):
        """BRD-052 토큰 없이 게시글 조회 실패 (공통).

        Authorization 헤더 없이 GET → fail/403/auth/not_found_sessionkey.
        """

        resp = board.raw("GET", "board/article/get/",
                         headers={"x-elice-org-name-short": board.org},
                         params={"board_article_id": own_article})
        assert resp.status_code == 200, resp.text
        r = resp.json()["_result"]
        assert r["status"] == "fail", resp.text
        assert r["status_code"] == 403, resp.text
        assert r["reason"] == "auth", resp.text
        assert resp.json()["fail_code"] == "not_found_sessionkey", resp.text

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_053_get_article_bad_token(self, board, own_article):
        """BRD-053 잘못된 토큰으로 게시글 조회 실패 (공통).

        무효한 Bearer 토큰 → fail/403/auth/no_account_api_session.
        """

        resp = board.raw("GET", "board/article/get/",
                         headers={"Authorization": "Bearer invalid_token_123",
                                  "x-elice-org-name-short": board.org},
                         params={"board_article_id": own_article})
        assert resp.status_code == 200, resp.text
        r = resp.json()["_result"]
        assert r["status"] == "fail", resp.text
        assert r["status_code"] == 403, resp.text
        assert r["reason"] == "auth", resp.text
        assert resp.json()["fail_code"] == "no_account_api_session", resp.text

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_054_create_article_no_auth(self, board, board_fail):
        """BRD-054 토큰 없이 게시글 작성 실패 (공통).

        Authorization 없이 POST edit/ → fail/403/auth, 작성되지 않음(board_article_id 미반환).
        """
        resp = board.raw("POST", "board/article/edit/",
                         headers={"x-elice-org-name-short": board.org},
                         data={"title": "무단 작성", "content": "<p>x</p>",
                               "is_secret": "false", "classroom_id": board.classroom_id})
        body = board_fail(resp, status_code=403, reason="auth")
        assert body["fail_code"] == "not_found_sessionkey", body
        assert "board_article_id" not in body, body

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_055_get_article_no_org_header(self, board, own_article, board_ok):
        """BRD-055 x-elice-org-name-short 헤더 누락 (공통).

        실측: org 헤더가 없어도 URL 경로 /org/{org}/ 로 식별되어 조회 성공(ok).
        (TC의 'fail(org 식별 불가)' 기대와 다름 — 헤더는 이 엔드포인트에서 필수가 아님)
        """

        resp = board.raw("GET", "board/article/get/",
                         headers={"Authorization": f"Bearer {board.token}"},
                         params={"board_article_id": own_article})
        body = board_ok(resp)
        assert body["board_article"]["id"] == own_article, body

    @pytest.mark.bug
    @pytest.mark.security
    @pytest.mark.jira("EQA-11")
    @pytest.mark.xfail(reason="V7#3 비작성자가 타인 비밀글 조회 가능. 고쳐지면 XPASS로 알림", strict=False)
    @pytest.mark.parametrize("author_fixture,reader_fixture", CROSS_ACCOUNT_DEV)
    def test_brd_056_others_secret_article_blocked(self, request, author_fixture,
                                                   reader_fixture, make_article):
        """BRD-056 [버그] 타인 비밀글 조회 가능 (dev, cross-account).

        보안 기대: 비작성자는 is_secret=true 글 조회 차단(_result.status=='fail').
        실측(V7#3 버그): 비작성자도 status=ok로 content까지 조회됨 → 아래 assert 실패 → xfail.
        """
        author = request.getfixturevalue(author_fixture)
        reader = request.getfixturevalue(reader_fixture)
        aid = make_article(author,
                                     title="비밀글", content="<p>비밀 내용</p>", is_secret=True)

        body = reader.get_article(aid).json()
        assert body["_result"]["status"] == "fail", f"비작성자 비밀글 조회 차단 실패(버그): {body}"

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_066_board_create_no_permission(self, board, board_fail):
        """BRD-066 게시판 생성(board/edit) — 권한 없음 (공통).

        게시판(board) 자체 생성은 상위 관리자(HeadTA 이상) 전용 → 학습자·교육자 모두 실패.
        공통 판정: _result.status=='fail' (게시판 생성 안 됨).
        ※ fail_code는 역할/데이터에 따라 다름 — 교육자=insufficient_permission,
          학습자=resource_not_found(prod에 course_id=1 미존재).
        """
        resp = board.board_edit({
            "name": "[QA] 테스트 게시판",
            "course_id": 1,
            "viewable_course_role": 0,
            "postable_course_role": 0,
            "commentable_course_role": 0,
            "is_secret_default": "false",
            "is_secret_force": "false",
            "is_subscribed_default": "false",
        })
        body = board_fail(resp)
        assert body.get("fail_code") in ("insufficient_permission", "resource_not_found"), body
        assert "board_id" not in body, body  # 생성되지 않음

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_067_board_move_no_permission(self, board, board_fail):
        """BRD-067 게시판 순서 변경(board/move) — 권한 없음 (공통).

        순서 이동은 상위 관리자 전용 → 학습자·교육자 모두 실패.
        기대: _result.status=='fail', fail_code=='insufficient_permission'.
        """
        resp = board.board_move(board.board_id, 1)
        board_fail(resp, fail_code="insufficient_permission")
