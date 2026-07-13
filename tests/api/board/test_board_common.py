# tests/api/board/test_board_common.py
"""게시판 공통 API 테스트 — 학습자·교육자가 동일하게 사용하는 기능.

공통 API는 로직이 같고 역할(target)만 다르므로, 역할별로 테스트를 따로 만들지 않고
하나의 테스트를 target으로 파라미터화한다.
  - 학습자 → prod (본인 단일계정)
  - 교육자 → dev  (교육자 계정은 dev에만 존재)

명세 대조 기준: Notion "dev_게시판 API 명세 (실측)" (게시판은 Swagger/openapi 미노출).
게시판 규약: HTTP는 항상 200, 성공/실패는 body `_result.status`(ok/fail)로 판정.
"""
import pytest


# 공통 테스트의 역할(target) 파라미터. id에 대응 TC 번호를 남겨 시트와 추적 가능하게 한다.
COMMON_TARGETS = [
    pytest.param("prod_learner", marks=pytest.mark.learner, id="TC-BRD-001-learner-prod"),
    pytest.param("dev_educator", marks=pytest.mark.educator, id="TC-BRD-062-educator-dev"),
]


@pytest.mark.api
@pytest.mark.board
class TestBoardCommon:
    """공통 게시판 API: 학습자·교육자 모두 동일하게 동작해야 하는 시나리오."""

    @pytest.mark.parametrize("client_fixture", COMMON_TARGETS)
    def test_create_article(self, request, client_fixture, track_articles):
        """게시글 작성 성공 (공통). 학습자=prod(TC-BRD-001), 교육자=dev(TC-BRD-062).

        기대값(명세서 '게시글 작성' 행):
          - HTTP status_code == 200
          - _result.status == 'ok'
          - board_article_id: int 반환
        """
        client = request.getfixturevalue(client_fixture)
        resp = client.create_article(
            title="자동화 게시글",
            content="<p>내용</p>",
            is_secret=False,
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()

        # 정리 예약: ok 판정 전에 등록해 후속 assert 실패 시에도 삭제되도록
        article_id = body.get("board_article_id")
        if isinstance(article_id, int):
            track_articles.append((client, article_id))

        assert body["_result"]["status"] == "ok", body
        assert isinstance(article_id, int), body
