# tests/api/board/test_board_like.py
"""게시글 좋아요 API 테스트 (추가/삭제/멱등/목록/카운트 정합).

게시판 규약: HTTP는 항상 200, 성공/실패는 body `_result.status`(ok/fail)로 판정.
역할(target)은 COMMON_TARGETS로 파라미터화(학습자→prod, 교육자→dev).
명세 대조 기준: Notion "dev_게시판 API 명세 (실측)".
"""
import pytest

from fixtures.board_fixture import COMMON_TARGETS


@pytest.mark.api
@pytest.mark.board
class TestBoardLike:
    """게시글 좋아요 API 테스트 (추가/삭제/멱등/목록/카운트 정합)."""

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_022_like_add(self, board, board_ok, make_article):
        """BRD-022 게시글 좋아요 추가 성공 (공통, 본인 글).

        기대(명세서 '게시글 좋아요 추가'):
          - like/add _result.status == 'ok'
          - 이후 조회 시 is_liked == True, board_article_like_count 증가(+1)
        """
        aid = make_article(board, "좋아요 추가 대상", "<p>내용</p>", is_secret=False)

        before = board.get_article(aid).json()["board_article"]
        resp = board.like_add(aid)
        board_ok(resp)

        after = board.get_article(aid).json()["board_article"]
        assert after["is_liked"] is True, after
        assert after["board_article_like_count"] == before["board_article_like_count"] + 1, after

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_023_like_count_reflected(self, board, board_ok, make_article):
        """BRD-023 좋아요 추가 후 like_count·is_liked 반영 검증 (공통, 본인 글).

        절차: 좋아요 전 get(N) → like/add → 다시 get.
        기대: board_article_like_count == N + 1, is_liked == True.
        """
        aid = make_article(board, "좋아요 카운트 검증", "<p>내용</p>", is_secret=False)

        # 좋아요 전 N 기록
        n = board.get_article(aid).json()["board_article"]["board_article_like_count"]

        # 좋아요
        board_ok(board.like_add(aid))

        # 좋아요 후 N+1, is_liked=True
        after = board.get_article(aid).json()["board_article"]
        assert after["board_article_like_count"] == n + 1, after
        assert after["is_liked"] is True, after

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_024_self_like_allowed(self, board, board_ok, make_article):
        """BRD-024 본인 게시글 좋아요(self-like) 허용 (공통).

        기대: 본인 글에 like/add → _result.status == 'ok' (self-like 허용).
        """
        aid = make_article(board, "self-like 대상", "<p>내용</p>", is_secret=False)

        resp = board.like_add(aid)
        board_ok(resp)

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_025_like_idempotent(self, board, board_ok, make_article):
        """BRD-025 이미 좋아요한 글 재추가 (멱등성) (공통, 본인 글).

        절차: like/add 1회 → 재호출.
        기대: 재호출도 _result.status == 'ok', board_article_like_count 중복 증가 없음.
        """
        aid = make_article(board, "멱등 좋아요 대상", "<p>내용</p>", is_secret=False)

        # 1회 좋아요
        board_ok(board.like_add(aid))
        count1 = board.get_article(aid).json()["board_article"]["board_article_like_count"]

        # 재추가(멱등) → status ok, count 그대로
        resp = board.like_add(aid)
        board_ok(resp)
        count2 = board.get_article(aid).json()["board_article"]["board_article_like_count"]
        assert count2 == count1, f"멱등이어야 하는데 count 증가: {count1} -> {count2}"

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_026_like_delete(self, board, own_article, board_ok):
        """BRD-026 게시글 좋아요 삭제 성공 (공통, 본인 글).

        절차: 좋아요 추가 → 삭제.
        기대: like/delete _result.status=='ok', 이후 is_liked==False, like_count 감소.
        """

        board.like_add(own_article)
        before = board.get_article(own_article).json()["board_article"]["board_article_like_count"]

        resp = board.like_delete(own_article)
        board_ok(resp)

        after = board.get_article(own_article).json()["board_article"]
        assert after["is_liked"] is False, after
        assert after["board_article_like_count"] == before - 1, after

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_027_like_delete_idempotent(self, board, own_article, board_ok):
        """BRD-027 좋아요하지 않은 글 좋아요 삭제 (멱등) (공통, 본인 글).

        기대: 좋아요 안 한 상태에서 like/delete → _result.status=='ok' (멱등 처리).
        """

        resp = board.like_delete(own_article)  # 좋아요 안 한 상태
        board_ok(resp)

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_028_like_list(self, board, own_article, board_ok):
        """BRD-028 게시글 좋아요 목록 조회 성공 (공통, 본인 글).

        기대: _result.status=='ok', board_article_like_users 가 배열(list)로 반환.
        (※ 명세 표기 like_users → 실제 board_article_like_users, item.user_id → item.id)
        """
        board.like_add(own_article)

        resp = board.like_list(own_article)
        body = board_ok(resp)
        assert isinstance(body["board_article_like_users"], list), body

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_029_like_list_contains_self(self, board, own_article):
        """BRD-029 좋아요 추가 후 목록에 본인 id 포함 (공통, 본인 글).

        기대: like/add 후 board_article_like_users 에 본인 user id 포함.
        """
        my_uid = board.get_article(own_article).json()["board_article"]["user"]["id"]

        board.like_add(own_article)
        users = board.like_list(own_article).json()["board_article_like_users"]
        assert my_uid in [u["id"] for u in users], users

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_030_like_list_removes_self(self, board, own_article):
        """BRD-030 좋아요 삭제 후 목록에서 본인 id 제거 (공통, 본인 글).

        기대: like/add → like/delete 후 board_article_like_users 에 본인 user id 없음.
        """
        my_uid = board.get_article(own_article).json()["board_article"]["user"]["id"]

        board.like_add(own_article)
        board.like_delete(own_article)
        users = board.like_list(own_article).json()["board_article_like_users"]
        assert my_uid not in [u["id"] for u in users], users

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_031_like_list_empty(self, board, own_article, board_ok):
        """BRD-031 좋아요 0건 게시글 목록 빈 배열 (공통, 본인 글).

        기대: 좋아요 없는 새 글 → _result.status=='ok', board_article_like_users == [].
        """

        resp = board.like_list(own_article)
        body = board_ok(resp)
        assert body["board_article_like_users"] == [], body
