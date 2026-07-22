# tests/api/board/test_board_attachment.py
"""게시판 첨부파일 API 테스트 (업로드/파라미터 검증/글 첨부).

게시판 규약: HTTP는 항상 200, 성공/실패는 body `_result.status`(ok/fail)로 판정.
역할(target)은 COMMON_TARGETS로 파라미터화(학습자→prod, 교육자→dev).
명세 대조 기준: Notion "dev_게시판 API 명세 (실측)".
"""
import pytest

from fixtures.board_fixture import COMMON_TARGETS, PNG_1x1


@pytest.mark.api
@pytest.mark.board
class TestBoardAttachment:
    """게시판 첨부파일 API 테스트 (업로드/파라미터 검증/글 첨부)."""

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_062_attachment_upload(self, board, board_ok):
        """BRD-062 첨부파일 업로드 성공 (공통).

        기대: _result.status=='ok', 업로드된 파일 URL 반환.
        (※ 명세 필드 attachment_files → 실제 attachment_file, 응답은 {_result, url})
        """
        resp = board.attachment_upload("test.png", PNG_1x1, "image/png")

        body = board_ok(resp)
        assert isinstance(body.get("url"), str) and body["url"], body

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_063_attachment_upload_no_file(self, board, board_fail):
        """BRD-063 첨부파일 필드 없이 업로드 실패 (공통).

        기대: _result.status=='fail', fail_code=='invalid_parameter' (attachment_file 누락).
        """
        resp = board.attachment_upload_raw(files={"dummy": ("", "")})

        board_fail(resp, fail_code="invalid_parameter")

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_064_attachment_upload_wrong_method(self, board):
        """BRD-064 첨부 업로드 잘못된 메서드(GET) 거부 (공통).

        업로드는 POST 전용 → GET은 HTTP 405.
        (board API는 보통 HTTP 200+_result지만, 메서드 불일치는 HTTP 레벨 405 — _result 없이 상태코드로 판단)
        """
        resp = board.attachment_upload_raw(method="GET")
        assert resp.status_code == 405, resp.text

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_065_attach_file_to_article(self, board, track_articles, board_ok):
        """BRD-065 업로드한 첨부를 게시글에 연결 (공통).

        웹 UI 실측: 별도 upload/ 없이 board/article/edit/ 의 attachment_files 필드에 파일을
        직접 실어(multipart) 작성+첨부를 한 번에 처리한다.
        기대:
          - _result.status=='ok', board_article_id 반환
          - 단건조회 article_attachments 배열에 파일 포함(filename 일치)
          - 목록의 article_attachment_count 증가
        """
        resp = board.create_article_with_attachment(
            "첨부 연결 글", "<p>첨부 테스트</p>", "qa_test.png", PNG_1x1, content_type="image/png")

        body = board_ok(resp)
        aid = body.get("board_article_id")
        assert isinstance(aid, int), body
        track_articles.append((board, aid))

        # 단건조회: article_attachments 에 파일 연결됨
        art = board.get_article(aid).json()["board_article"]
        atts = art["article_attachments"]
        assert isinstance(atts, list) and len(atts) >= 1, art
        assert atts[0]["attachment"]["filename"] == "qa_test.png", atts

        # 목록: article_attachment_count 증가
        listed = board.list_articles(count=20).json()["board_articles"]
        me = next((a for a in listed if a["id"] == aid), None)
        assert me is not None and me["article_attachment_count"] >= 1, me
