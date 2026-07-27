# tests/api/board/test_board_comment.py
"""댓글 및 댓글 좋아요 API 테스트 (작성/수정/삭제/조회/목록/좋아요).

게시판 규약: HTTP는 항상 200, 성공/실패는 body `_result.status`(ok/fail)로 판정.
역할(target)은 COMMON_TARGETS로 파라미터화(학습자→prod, 교육자→dev).
명세 대조 기준: Notion "dev_게시판 API 명세 (실측)".
"""
import pytest

from api.schemas.board_schema import BoardSchemas
from fixtures.board_fixture import COMMON_TARGETS, CROSS_ACCOUNT_DEV
from utils.helpers.api_assertions import assert_valid_schema


@pytest.mark.api
@pytest.mark.board
class TestBoardComment:
    """댓글 및 댓글 좋아요 API 테스트 (작성/수정/삭제/조회/목록/좋아요)."""

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_032_create_comment(self, board, own_article, board_ok):
        """BRD-032 댓글 작성 성공 (공통, 본인 글).

        기대: _result.status=='ok', article_comment_id 정수 반환, article_comment_count +1.
        """
        before = board.get_article(own_article).json()["board_article"]["article_comment_count"]

        resp = board.create_comment(own_article, "첫 댓글")
        body = board_ok(resp)
        assert isinstance(body.get("article_comment_id"), int), body

        after = board.get_article(own_article).json()["board_article"]["article_comment_count"]
        assert after == before + 1, (before, after)

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_033_update_own_comment(self, board, own_article, board_ok):
        """BRD-033 본인 댓글 수정 성공 (공통).

        기대: _result.status=='ok', 반환 article_comment_id == 요청 article_comment_id.
        """
        cid = board.create_comment(own_article, "원본 댓글").json()["article_comment_id"]

        resp = board.update_comment(cid, own_article, "수정된 댓글")
        body = board_ok(resp)
        assert body.get("article_comment_id") == cid, body

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_034_comment_modified_datetime(self, board, own_article):
        """BRD-034 댓글 수정 시 modified_datetime 갱신 (공통).

        기대: 최초 modified_datetime==None, 수정 후 modified_datetime!=None(값으로 갱신).
        """
        cid = board.create_comment(own_article, "원본 댓글").json()["article_comment_id"]

        before = board.get_comment(cid).json()["article_comment"]
        assert_valid_schema(before, BoardSchemas.ARTICLE_COMMENT)
        assert before["modified_datetime"] is None, before

        board.update_comment(cid, own_article, "수정된 댓글")
        after = board.get_comment(cid).json()["article_comment"]
        assert after["modified_datetime"] is not None, after

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_035_create_comment_fail_missing_content(self, board, own_article, board_fail):
        """BRD-035 댓글 작성 실패 (content 누락) (공통).

        기대: _result.status=='fail', fail_code=='invalid_parameter'.
        """

        resp = board.comment_edit_raw({"board_article_id": own_article})  # content 누락
        body = board_fail(resp, fail_code="invalid_parameter")
        assert "fail_message" in body and "fail_detail" in body, body

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_036_create_comment_fail_missing_board_article_id(self, board, board_fail):
        """BRD-036 댓글 작성 실패 (board_article_id 누락) (공통).

        기대: _result.status=='fail', fail_code=='invalid_parameter'.
        """
        resp = board.comment_edit_raw({"content": "내용만 있음"})  # board_article_id 누락
        body = board_fail(resp, fail_code="invalid_parameter")
        assert "fail_message" in body and "fail_detail" in body, body

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_037_comment_on_nonexistent_article(self, board, board_fail):
        """BRD-037 존재하지 않는 게시글에 댓글 작성 실패 (공통).

        기대: _result.status=='fail', fail_code=='resource_not_found'.
        """
        resp = board.comment_edit_raw({"board_article_id": 99999999, "content": "내용"})
        board_fail(resp, fail_code="resource_not_found")

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_038_comment_count_increases(self, board, own_article):
        """BRD-038 댓글 작성 후 article_comment_count 증가 (공통).

        기대: 댓글 작성 후 article_comment_count == N + 1.
        """
        n = board.get_article(own_article).json()["board_article"]["article_comment_count"]

        board.create_comment(own_article, "댓글")
        after = board.get_article(own_article).json()["board_article"]["article_comment_count"]
        assert after == n + 1, (n, after)

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_039_list_comments(self, board, own_article, board_ok):
        """BRD-039 댓글 목록 조회 성공 (공통).

        기대: _result.status=='ok', article_comments 배열, article_comment_count 정수.
        """
        board.create_comment(own_article, "댓글1")

        resp = board.list_comments(own_article, count=5)
        body = board_ok(resp)
        assert isinstance(body["article_comments"], list), body
        assert isinstance(body["article_comment_count"], int), body
        assert_valid_schema(body["article_comments"], BoardSchemas.ARTICLE_COMMENT_LIST)

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_040_comment_list_count_param(self, board, own_article):
        """BRD-040 댓글 목록 count 파라미터 동작 (공통).

        댓글 3개 작성 후 count=2로 조회 → 반환 개수 <= count.
        """
        for i in range(3):
            board.create_comment(own_article, f"댓글{i}")

        resp = board.list_comments(own_article, count=2)
        assert resp.status_code == 200, resp.text
        comments = resp.json()["article_comments"]
        assert len(comments) <= 2, comments

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_041_comment_list_empty(self, board, own_article, board_ok):
        """BRD-041 댓글 없는 게시글 목록 빈 배열·count 0 (공통).

        기대: _result.status=='ok', article_comments==[], article_comment_count==0.
        """

        resp = board.list_comments(own_article, count=5)
        body = board_ok(resp)
        assert body["article_comments"] == [], body
        assert body["article_comment_count"] == 0, body

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_042_comment_list_count_boundary(self, board, own_article):
        """BRD-042 댓글 목록 count 경계값(0/음수/초과) (공통).

        실측: count=0, -1, 100000 모두 fail/invalid_parameter.
        (TC의 '초과는 상한 범위 내 반환'과 달리, 초과값도 거부됨)
        """

        for bad_count in (0, -1, 100000):
            body = board.list_comments(own_article, count=bad_count).json()
            assert body["_result"]["status"] == "fail", (bad_count, body)
            assert body["fail_code"] == "invalid_parameter", (bad_count, body)

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_043_get_comment(self, board, own_article, board_ok):
        """BRD-043 댓글 단건 조회 성공 (공통).

        기대: _result.status=='ok', article_comment.id == 요청 id, 스키마 필드 존재.
        """
        cid = board.create_comment(own_article, "댓글 내용").json()["article_comment_id"]

        resp = board.get_comment(cid)
        body = board_ok(resp)
        art = body["article_comment"]
        assert art["id"] == cid, art
        for f in ("id", "content", "user", "created_datetime", "modified_datetime",
                  "is_liked", "comment_like_count"):
            assert f in art, (f, art)

    @pytest.mark.parametrize("author_fixture,actor_fixture", CROSS_ACCOUNT_DEV)
    def test_brd_044_edit_others_comment_blocked(self, request, author_fixture,
                                                 actor_fixture, board_fail, make_article):
        """BRD-044 타인 댓글 수정 시도 → 권한 차단 (dev, cross-account).

        수정은 정상 차단. 기대: _result.status=='fail', fail_code=='resource_not_found'.
        """
        author = request.getfixturevalue(author_fixture)
        actor = request.getfixturevalue(actor_fixture)
        aid = make_article(author)
        cid = author.create_comment(aid, "원본 댓글").json()["article_comment_id"]

        resp = actor.update_comment(cid, aid, "몰래 수정")
        board_fail(resp, fail_code="resource_not_found")

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_045_delete_own_comment(self, board, own_article, board_ok):
        """BRD-045 본인 댓글 삭제 성공 (공통).

        기대: _result.status=='ok', 이후 article_comment_count 감소.
        """
        cid = board.create_comment(own_article, "삭제할 댓글").json()["article_comment_id"]
        n = board.get_article(own_article).json()["board_article"]["article_comment_count"]

        resp = board.delete_comment(cid)
        board_ok(resp)

        after = board.get_article(own_article).json()["board_article"]["article_comment_count"]
        assert after == n - 1, (n, after)

    @pytest.mark.parametrize("author_fixture,actor_fixture", CROSS_ACCOUNT_DEV)
    def test_brd_046_delete_others_comment_blocked(self, request, author_fixture,
                                                   actor_fixture, board_fail, make_article):
        """BRD-046 타인 댓글 삭제 시도 → 권한 차단 (dev, cross-account).

        댓글 삭제는 정상 차단(게시글 삭제 버그와 대조).
        기대: _result.status=='fail', fail_code=='insufficient_permission'.
        """
        author = request.getfixturevalue(author_fixture)
        actor = request.getfixturevalue(actor_fixture)
        aid = make_article(author)
        cid = author.create_comment(aid, "원본 댓글").json()["article_comment_id"]

        resp = actor.delete_comment(cid)
        board_fail(resp, fail_code="insufficient_permission")

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_047_comment_like_add(self, board, own_article, board_ok):
        """BRD-047 댓글 좋아요 추가 성공 (공통, 본인 댓글).

        기대: _result.status=='ok', 이후 is_liked==True, comment_like_count 증가.
        """
        cid = board.create_comment(own_article, "댓글").json()["article_comment_id"]
        before = board.get_comment(cid).json()["article_comment"]["comment_like_count"]

        resp = board.comment_like_add(cid)
        board_ok(resp)

        after = board.get_comment(cid).json()["article_comment"]
        assert after["is_liked"] is True, after
        assert after["comment_like_count"] == before + 1, after

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_048_self_comment_like_allowed(self, board, own_article, board_ok):
        """BRD-048 본인 댓글 좋아요(self-like) 허용 (공통).

        기대: 본인 댓글에 comment/like/add → _result.status=='ok'.
        """
        cid = board.create_comment(own_article, "본인 댓글").json()["article_comment_id"]

        resp = board.comment_like_add(cid)
        board_ok(resp)

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_049_comment_like_delete(self, board, own_article, board_ok):
        """BRD-049 댓글 좋아요 삭제 성공 (공통, 본인 댓글).

        기대: _result.status=='ok', 이후 is_liked==False, comment_like_count 감소.
        """
        cid = board.create_comment(own_article, "댓글").json()["article_comment_id"]
        board.comment_like_add(cid)
        before = board.get_comment(cid).json()["article_comment"]["comment_like_count"]

        resp = board.comment_like_delete(cid)
        board_ok(resp)

        after = board.get_comment(cid).json()["article_comment"]
        assert after["is_liked"] is False, after
        assert after["comment_like_count"] == before - 1, after

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_050_comment_like_list(self, board, own_article, board_ok):
        """BRD-050 댓글 좋아요 목록 조회 성공 (공통).

        기대: _result.status=='ok', 좋아요 유저 목록이 배열로 반환.
        (※ 명세 표기 like_users → 실제 article_comment_like_users, item.user_id → item.id)
        """
        cid = board.create_comment(own_article, "댓글").json()["article_comment_id"]
        board.comment_like_add(cid)

        resp = board.comment_like_list(cid)
        body = board_ok(resp)
        assert isinstance(body["article_comment_like_users"], list), body

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_051_comment_like_count_integrity(self, board, own_article):
        """BRD-051 댓글 좋아요 count 정합성 (공통).

        기대: 좋아요 추가 후 comment_like_count==N+1, 삭제 후 ==N.
        """
        cid = board.create_comment(own_article, "댓글").json()["article_comment_id"]

        n = board.get_comment(cid).json()["article_comment"]["comment_like_count"]
        board.comment_like_add(cid)
        assert board.get_comment(cid).json()["article_comment"]["comment_like_count"] == n + 1
        board.comment_like_delete(cid)
        assert board.get_comment(cid).json()["article_comment"]["comment_like_count"] == n
