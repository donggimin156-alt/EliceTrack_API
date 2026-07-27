# tests/api/board/test_board_security.py
"""게시판 개인정보 노출·권한 버그(xfail) 테스트 — 타인/크로스계정 조회 시 email 노출, 타인 글 삭제 버그.

게시판 규약: HTTP는 항상 200, 성공/실패는 body `_result.status`(ok/fail)로 판정.
역할(target)은 COMMON_TARGETS로 파라미터화(학습자→prod, 교육자→dev).
명세 대조 기준: Notion "dev_게시판 API 명세 (실측)".
"""
import pytest

from fixtures.board_fixture import CROSS_ACCOUNT_DEV


@pytest.mark.api
@pytest.mark.board
class TestBoardSecurity:
    """게시판 개인정보 노출·권한 버그(xfail) 테스트 — 타인/크로스계정 조회 시 email 노출, 타인 글 삭제 버그."""

    @pytest.mark.bug
    @pytest.mark.security
    @pytest.mark.jira("EQA-10")
    @pytest.mark.xfail(reason="V7#2 타인 게시글 조회 시 작성자 email 노출(버그). 고쳐지면 XPASS로 알림",
                       strict=False)
    def test_brd_013_others_article_email_exposed(self, dev_learner, dev_educator, board_ok, make_article):
        """BRD-013 [버그] 타인 게시글 조회 시 작성자 개인정보(email) 노출 (dev, 단일 시나리오).

        비작성자(교육자)가 타인(학습자) 글을 조회 → 작성자 email 노출.
        보안 기대: board_article.user에 email/display_email 비노출 → 현재 실패(버그) → xfail.
        prod은 타 계정 글 생성 불가로 dev에서만.
        """
        # 학습자 생성 → 비작성자(교육자) 조회
        aid = make_article(dev_learner, "타인조회 대상 글", "<p>내용</p>", is_secret=False)

        body = board_ok(dev_educator.get_article(aid))
        user = body["board_article"]["user"]
        assert "email" not in user, f"작성자 email 노출(V7#2 버그): {user.get('email')}"
        assert "display_email" not in user, f"작성자 display_email 노출(V7#2 버그): {user.get('display_email')}"

    @pytest.mark.bug
    @pytest.mark.security
    @pytest.mark.jira("EQA-10")
    @pytest.mark.xfail(reason="V7#2 크로스계정 조회 시 작성자 email 노출(버그). 고쳐지면 XPASS로 알림",
                       strict=False)
    @pytest.mark.parametrize("author_fixture,reader_fixture", CROSS_ACCOUNT_DEV)
    def test_brd_014_cross_account_email_exposed(self, request, author_fixture,
                                                 reader_fixture, board_ok, make_article):
        """BRD-014 [버그] 크로스계정 조회 시 작성자 개인정보(email) 노출 (dev, 2방향).

        학습자↔교육자 양방향으로 비작성자 조회 시 email·display_email 노출.
        보안 기대: 비노출 → 현재 실패(버그) → xfail. prod은 타 계정 글 생성 불가로 dev에서만.
        """
        author = request.getfixturevalue(author_fixture)
        reader = request.getfixturevalue(reader_fixture)

        aid = make_article(author, "크로스계정 조회 대상", "<p>내용</p>", is_secret=False)

        body = board_ok(reader.get_article(aid))
        user = body["board_article"]["user"]
        assert "email" not in user, f"작성자 email 노출(V7#2 버그): {user.get('email')}"
        assert "display_email" not in user, f"작성자 display_email 노출(V7#2 버그): {user.get('display_email')}"

    @pytest.mark.bug
    @pytest.mark.security
    @pytest.mark.jira("EQA-9")
    @pytest.mark.xfail(
        reason="V7#1 권한 미검사 버그: 비작성자(학습자)가 타인(교육자) 게시글 삭제 가능. 고쳐지면 XPASS로 알림",
        strict=False,
    )
    def test_brd_019_delete_others_article_bug(self, dev_learner, dev_educator, track_articles):
        """BRD-019 [버그] 타인 게시글 삭제 가능 (권한 미검사) (dev).

        비작성자(학습자)가 타인(교육자) 글 삭제 시도 → 권한 없어 차단돼야 하는데 삭제됨.
        보안 기대: _result.status=='fail' → 현재 'ok'(삭제 성공)이라 실패 → xfail(버그 문서화).
        prod은 타 계정 글 생성 불가로 dev에서만.
        """
        created = dev_educator.create_article("삭제대상(교육자 작성)", "<p>내용</p>", is_secret=False)
        assert created.status_code == 200, created.text
        aid = created.json().get("board_article_id")
        assert isinstance(aid, int), f"setup 게시글 생성 실패: {created.text}"
        track_articles.append((dev_educator, aid))  # 안전망(차단되면 교육자가 정리)

        # 학습자가 타인(교육자) 글 삭제 시도 → 거부돼야 정상(현재는 버그로 ok → xfail)
        resp = dev_learner.delete_article(aid)
        assert resp.status_code == 200, resp.text
        assert resp.json()["_result"]["status"] == "fail", resp.text
