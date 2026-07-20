# tests/api/board/test_board_common.py
"""게시판 공통 API 테스트 — 학습자·교육자가 동일하게 사용하는 기능.

공통 API는 로직이 같고 역할(target)만 다르므로, 역할별로 테스트를 따로 만들지 않고
하나의 테스트를 target으로 파라미터화한다. (학습자→prod, 교육자→dev)
번호는 파라미터화된 테스트 1개당 하나(BRD-xxx); 역할은 param(learner-prod/educator-dev)으로 구분.

명세 대조 기준: Notion "dev_게시판 API 명세 (실측)" (게시판은 Swagger/openapi 미노출).
게시판 규약: HTTP는 항상 200, 성공/실패는 body `_result.status`(ok/fail)로 판정.
"""
import base64

import pytest

from api.schemas.board_schema import BoardSchemas
from utils.assertions.api_assertions import assert_valid_schema

# 첨부 업로드 테스트용 1x1 PNG (67바이트)
_PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNk+P+/HgAFhAJ/wlseKgAAAABJRU5ErkJggg=="
)


# 공통 테스트의 역할(target) 파라미터. board_fixture의 board 클라이언트 픽스처 이름.
COMMON_TARGETS = [
    pytest.param("prod_learner", marks=pytest.mark.learner, id="learner-prod"),
    pytest.param("dev_educator", marks=pytest.mark.educator, id="educator-dev"),
]

# 2계정 cross-account 파라미터 (작성자, 행위자). prod은 타 계정 글 생성 불가 → dev 전용 2방향.
CROSS_ACCOUNT_DEV = [
    pytest.param("dev_learner", "dev_educator", id="learner_write-educator_act"),
    pytest.param("dev_educator", "dev_learner", id="educator_write-learner_act"),
]


@pytest.mark.api
@pytest.mark.board
class TestBoardCommon:
    """공통 게시판 API: 학습자·교육자 모두 동일하게 동작해야 하는 시나리오."""

    @staticmethod
    def _make_own_article(board, track_articles, title="테스트 글", content="<p>내용</p>", is_secret=False):
        """본인 글 생성 헬퍼: 생성 성공 확인 + track_articles 등록 후 board_article_id 반환."""
        created = board.create_article(title, content, is_secret=is_secret)
        assert created.status_code == 200, created.text
        aid = created.json().get("board_article_id")
        assert isinstance(aid, int), f"setup 게시글 생성 실패: {created.text}"
        track_articles.append((board, aid))
        return aid

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_001_create_article(self, board, track_articles):
        """BRD-001 본인 게시글 작성 성공 (공통).

        기대(명세서 '게시글 작성'):
          - HTTP status_code == 200
          - _result.status == 'ok'
          - board_article_id: int 반환
        """
        resp = board.create_article("자동화 게시글", "<p>내용</p>", is_secret=False)

        assert resp.status_code == 200, resp.text
        body = resp.json()

        # 정리 예약: ok 판정 전에 등록해 후속 assert 실패 시에도 삭제되도록
        article_id = body.get("board_article_id")
        if isinstance(article_id, int):
            track_articles.append((board, article_id))

        assert body["_result"]["status"] == "ok", body
        assert isinstance(article_id, int), body

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_002_edit_own_article(self, board, track_articles, board_ok):
        """BRD-002 본인 게시글 수정 성공 (공통).

        절차: (setup) 본인 글 생성 → 수정 호출 → 재조회.
        기대(명세서 '게시글 수정'):
          - HTTP status_code == 200
          - _result.status == 'ok'
          - 반환 board_article_id == 요청 board_article_id
          - 재조회 시 modified_datetime 이 null → 값으로 갱신
        """

        # setup: 수정할 본인 글 생성 (생성 실패 시 원인이 드러나도록 방어)
        aid = self._make_own_article(board, track_articles, "수정 전 제목", "<p>수정 전</p>", is_secret=False)

        # 생성 직후 modified_datetime 은 null
        before = board.get_article(aid).json()["board_article"]
        assert before["modified_datetime"] is None, before

        # 수정 호출
        resp = board.update_article(aid, "수정된 제목", "<p>수정된 내용</p>", is_secret=False)

        body = board_ok(resp)
        assert body.get("board_article_id") == aid, body

        # 재조회: modified_datetime 갱신 + 수정 내용 반영
        after = board.get_article(aid).json()["board_article"]
        assert after["modified_datetime"] is not None, after
        assert after["title"] == "수정된 제목", after

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_003_create_secret_article(self, board, track_articles):
        """BRD-003 비밀글(is_secret=true) 작성 성공 (공통).

        기대(명세서 '게시글 작성'):
          - HTTP status_code == 200
          - _result.status == 'ok'
          - board_article_id: int 반환
          - (추가) 재조회 시 is_secret == True 로 저장됨
        """
        resp = board.create_article("비밀 게시글", "<p>비밀 내용</p>", is_secret=True)

        assert resp.status_code == 200, resp.text
        body = resp.json()

        article_id = body.get("board_article_id")
        if isinstance(article_id, int):
            track_articles.append((board, article_id))

        assert body["_result"]["status"] == "ok", body
        assert isinstance(article_id, int), body

        # 비밀글로 저장됐는지 재조회 확인
        after = board.get_article(article_id).json()["board_article"]
        assert after["is_secret"] is True, after

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_004_create_fail_missing_title(self, board, board_fail):
        """BRD-004 게시글 작성 실패 (title 누락) (공통).

        title을 의도적으로 빼고 요청 → 검증 실패.
        기대(명세서 '게시글 작성' fail):
          - HTTP status_code == 200 (게시판은 실패해도 항상 200)
          - _result.status == 'fail', _result.status_code == 400, _result.reason == 'param'
          - fail_code == 'invalid_parameter'
          - 스키마: fail_code, fail_message, fail_detail 존재
        """
        # title 제외, content/is_secret/classroom_id 만 지정
        resp = board.create_article_raw({
            "content": "<p>내용</p>",
            "is_secret": "false",
            "classroom_id": board.classroom_id,
        })

        body = board_fail(resp, fail_code="invalid_parameter", status_code=400, reason="param")
        assert "fail_message" in body and "fail_detail" in body, body

        # 생성되면 안 됨(실패 케이스라 board_article_id 없음)
        assert "board_article_id" not in body, body

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_005_create_fail_missing_content(self, board, board_fail):
        """BRD-005 게시글 작성 실패 (content 누락) (공통).

        content를 의도적으로 빼고 요청 → 검증 실패.
        (참고: content=""(빈 문자열)은 허용되지만, 필드 자체 누락은 required 오류)
        기대(명세서 '게시글 작성' fail):
          - HTTP status_code == 200
          - _result.status == 'fail', _result.status_code == 400, _result.reason == 'param'
          - fail_code == 'invalid_parameter'
          - 스키마: fail_code, fail_message, fail_detail 존재
        """
        # content 제외, title/is_secret/classroom_id 만 지정
        resp = board.create_article_raw({
            "title": "제목만 있음",
            "is_secret": "false",
            "classroom_id": board.classroom_id,
        })

        body = board_fail(resp, fail_code="invalid_parameter", status_code=400, reason="param")
        assert "fail_message" in body and "fail_detail" in body, body

        # 생성되면 안 됨(실패 케이스라 board_article_id 없음)
        assert "board_article_id" not in body, body

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_006_create_fail_missing_is_secret(self, board, board_fail):
        """BRD-006 게시글 작성 실패 (is_secret 누락) (공통).

        is_secret을 의도적으로 빼고 요청 → 검증 실패.
        기대(명세서 '게시글 작성' fail):
          - HTTP status_code == 200
          - _result.status == 'fail', _result.status_code == 400, _result.reason == 'param'
          - fail_code == 'invalid_parameter'
          - 스키마: fail_code, fail_message, fail_detail 존재
        """
        # is_secret 제외, title/content/classroom_id 만 지정
        resp = board.create_article_raw({
            "title": "제목",
            "content": "<p>내용</p>",
            "classroom_id": board.classroom_id,
        })

        body = board_fail(resp, fail_code="invalid_parameter", status_code=400, reason="param")
        assert "fail_message" in body and "fail_detail" in body, body

        # 생성되면 안 됨(실패 케이스라 board_article_id 없음)
        assert "board_article_id" not in body, body

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_007_create_fail_missing_classroom_and_board_id(self, board, board_fail):
        """BRD-007 게시글 작성 실패 (classroom_id·board_id 모두 누락) (공통).

        board_id/classroom_id는 각각 optional이나 최소 하나 필수 → 둘 다 빼면 실패.
        기대(명세서 fail):
          - HTTP status_code == 200
          - _result.status == 'fail'
          - fail_code == 'no_board_id_or_classroom_id'
          - 스키마: fail_code, fail_message, fail_detail 존재
        ※ 실측: 필수필드 누락(400/param)과 다른 에러 계열 — _result.status_code=409, reason='logic'.
        """
        # classroom_id·board_id 모두 제외 (title/content/is_secret 만)
        resp = board.create_article_raw({
            "title": "제목",
            "content": "<p>내용</p>",
            "is_secret": "false",
        })

        # 실측 상세: 필수필드 누락(400/param)과 다른 에러 계열(409/logic)까지 대조
        body = board_fail(
            resp, fail_code="no_board_id_or_classroom_id", status_code=409, reason="logic"
        )
        assert "fail_message" in body and "fail_detail" in body, body

        # 생성되면 안 됨(실패 케이스라 board_article_id 없음)
        assert "board_article_id" not in body, body

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_008_create_title_128_boundary(self, board, track_articles):
        """BRD-008 제목 128자(한글) 작성 성공 — 경계 상한 (공통).

        스펙: title 허용 길이 1~128자 → 128자는 허용(성공). (129자 이상은 별도 실패 TC)
        기대(명세서 '게시글 작성'):
          - HTTP status_code == 200
          - _result.status == 'ok'
          - board_article_id: int 반환
          - (추가) 재조회 시 저장된 title 길이 == 128
        """
        title = "가" * 128  # 한글 128자 경계 상한

        resp = board.create_article(title, "<p>내용</p>", is_secret=False)

        assert resp.status_code == 200, resp.text
        body = resp.json()

        article_id = body.get("board_article_id")
        if isinstance(article_id, int):
            track_articles.append((board, article_id))

        assert body["_result"]["status"] == "ok", body
        assert isinstance(article_id, int), body

        # 128자가 잘려나가지 않고 그대로 저장됐는지 재조회 확인
        after = board.get_article(article_id).json()["board_article"]
        assert len(after["title"]) == 128, len(after["title"])

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_009_create_fail_title_129(self, board, board_fail):
        """BRD-009 제목 129자(한글) 작성 실패 — 경계 초과 (공통).

        스펙: title 최대 128자 → 129자는 초과, 검증 실패.
        기대(명세서 '게시글 작성' fail):
          - HTTP status_code == 200
          - _result.status == 'fail', _result.status_code == 400, _result.reason == 'param'
          - fail_code == 'invalid_parameter'
          - 스키마: fail_code, fail_message, fail_detail 존재
        """
        title = "가" * 129  # 한글 129자 (경계 초과)

        # classroom_id 등 다른 필드는 정상, title만 초과
        resp = board.create_article(title, "<p>내용</p>", is_secret=False)

        body = board_fail(resp, fail_code="invalid_parameter", status_code=400, reason="param")
        assert "fail_message" in body and "fail_detail" in body, body

        # 생성되면 안 됨(실패 케이스라 board_article_id 없음)
        assert "board_article_id" not in body, body

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_010_create_fail_empty_title(self, board, board_fail):
        """BRD-010 제목 빈 문자열 작성 실패 (공통).

        스펙: title 최소 1자 → 빈 문자열("")은 실패.
        기대(명세서 '게시글 작성' fail):
          - HTTP status_code == 200
          - _result.status == 'fail', _result.status_code == 400, _result.reason == 'param'
          - fail_code == 'invalid_parameter'
          - 스키마: fail_code, fail_message, fail_detail 존재
        (실측: fail_detail.invalid_params.title = "should be between 1 and 128 letters/elements")
        """
        resp = board.create_article_raw({
            "title": "",
            "content": "<p>내용</p>",
            "is_secret": "false",
            "classroom_id": board.classroom_id,
        })

        body = board_fail(resp, fail_code="invalid_parameter", status_code=400, reason="param")
        assert "fail_message" in body and "fail_detail" in body, body
        assert "board_article_id" not in body, body

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_011_create_fail_non_boolean_is_secret(self, board, board_fail):
        """BRD-011 is_secret 비boolean 값 작성 실패 (공통).

        is_secret은 boolean('true'/'false')만 유효 → 'abc' 같은 값은 실패.
        기대(명세서 '게시글 작성' fail):
          - HTTP status_code == 200
          - _result.status == 'fail'
          - fail_code == 'invalid_parameter'
          - 스키마: fail_code, fail_message, fail_detail 존재
        ※ 실측 뉘앙스: 서버는 비boolean 값을 enum 오류가 아니라 '누락'처럼 처리
          → fail_detail.invalid_params.is_secret = "required" (TC의 'enum 위반' 설명과는 다름).
          핵심 판정(fail + invalid_parameter)은 TC와 동일하므로 그 기준으로 검증.
        """
        resp = board.create_article_raw({
            "title": "제목",
            "content": "<p>내용</p>",
            "is_secret": "abc",  # boolean이 아닌 값
            "classroom_id": board.classroom_id,
        })

        body = board_fail(resp, fail_code="invalid_parameter", status_code=400, reason="param")
        assert "fail_message" in body and "fail_detail" in body, body
        # is_secret이 문제 필드로 지목됐는지(메시지 문구는 서버 구현에 의존하므로 키만 확인)
        assert "is_secret" in body["fail_detail"].get("invalid_params", {}), body
        assert "board_article_id" not in body, body

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_012_get_own_article(self, board, track_articles, board_ok):
        """BRD-012 본인 게시글 단건 조회 성공 (공통).

        절차: (setup) 본인 글 생성 → GET 단건조회 → board_article 필드·값 검증.
        기대(명세서 '게시글 단건조회'):
          - _result.status == 'ok'
          - board_article.id == 요청 id, title/content 일치(원문 보존)
          - board_article 스키마 전 필드 존재(user 하위 필드 포함)
        (명세 DB에 없던 read_datetime·article_read_users_count도 실측상 포함됨)
        """
        title, content = "단건조회 테스트 제목", "<p>단건조회 내용</p>"

        # setup: 본인 글 생성
        aid = self._make_own_article(board, track_articles, title, content, is_secret=False)

        # 단건조회
        resp = board.get_article(aid)
        body = board_ok(resp)

        art = body["board_article"]
        assert_valid_schema(art, BoardSchemas.BOARD_ARTICLE)
        assert art["id"] == aid, art
        assert art["title"] == title, art
        assert art["content"] == content, art  # content 원문 보존

        # 스키마: 명세 실측 전 필드 존재
        spec_fields = {
            "id", "title", "content", "classroom_id", "course_id", "user",
            "created_datetime", "modified_datetime", "is_secret", "is_liked",
            "board_article_like_count", "read_datetime", "article_comment_count",
            "article_read_users_count", "article_attachments",
        }
        assert not (spec_fields - art.keys()), f"board_article 누락 필드: {spec_fields - art.keys()}"

        user_fields = {"id", "fullname", "firstname", "lastname",
                       "profile_url", "course_role", "email", "display_email"}
        assert not (user_fields - art["user"].keys()), f"user 누락 필드: {user_fields - art['user'].keys()}"

    @pytest.mark.bug
    @pytest.mark.security
    @pytest.mark.xfail(reason="V7#2 타인 게시글 조회 시 작성자 email 노출(버그). 고쳐지면 XPASS로 알림",
                       strict=False)
    def test_brd_013_others_article_email_exposed(self, dev_learner, dev_educator, track_articles, board_ok):
        """BRD-013 [버그] 타인 게시글 조회 시 작성자 개인정보(email) 노출 (dev, 단일 시나리오).

        비작성자(교육자)가 타인(학습자) 글을 조회 → 작성자 email 노출.
        보안 기대: board_article.user에 email/display_email 비노출 → 현재 실패(버그) → xfail.
        prod은 타 계정 글 생성 불가로 dev에서만.
        """
        # 학습자 생성 → 비작성자(교육자) 조회
        aid = self._make_own_article(dev_learner, track_articles, "타인조회 대상 글", "<p>내용</p>", is_secret=False)

        body = board_ok(dev_educator.get_article(aid))
        user = body["board_article"]["user"]
        assert "email" not in user, f"작성자 email 노출(V7#2 버그): {user.get('email')}"
        assert "display_email" not in user, f"작성자 display_email 노출(V7#2 버그): {user.get('display_email')}"

    @pytest.mark.bug
    @pytest.mark.security
    @pytest.mark.xfail(reason="V7#2 크로스계정 조회 시 작성자 email 노출(버그). 고쳐지면 XPASS로 알림",
                       strict=False)
    @pytest.mark.parametrize("author_fixture,reader_fixture", CROSS_ACCOUNT_DEV)
    def test_brd_014_cross_account_email_exposed(self, request, author_fixture,
                                                 reader_fixture, track_articles, board_ok):
        """BRD-014 [버그] 크로스계정 조회 시 작성자 개인정보(email) 노출 (dev, 2방향).

        학습자↔교육자 양방향으로 비작성자 조회 시 email·display_email 노출.
        보안 기대: 비노출 → 현재 실패(버그) → xfail. prod은 타 계정 글 생성 불가로 dev에서만.
        """
        author = request.getfixturevalue(author_fixture)
        reader = request.getfixturevalue(reader_fixture)

        aid = self._make_own_article(author, track_articles, "크로스계정 조회 대상", "<p>내용</p>", is_secret=False)

        body = board_ok(reader.get_article(aid))
        user = body["board_article"]["user"]
        assert "email" not in user, f"작성자 email 노출(V7#2 버그): {user.get('email')}"
        assert "display_email" not in user, f"작성자 display_email 노출(V7#2 버그): {user.get('display_email')}"

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_015_get_fail_string_id(self, board, board_fail):
        """BRD-015 board_article_id 문자열 값 조회 실패 (공통).

        board_article_id는 int converter → 'abc' 같은 문자열은 실패.
        기대(명세서 '게시글 단건조회' fail):
          - HTTP status_code == 200
          - _result.status == 'fail', _result.status_code == 400, _result.reason == 'param'
          - fail_code == 'invalid_parameter'
          - 스키마: fail_code, fail_message, fail_detail 존재
        (실측: 문자열은 int 변환 실패 → fail_detail.invalid_params.board_article_id = "required")
        """
        resp = board.get_article("abc")

        body = board_fail(resp, fail_code="invalid_parameter", status_code=400, reason="param")
        assert "fail_message" in body and "fail_detail" in body, body

    @pytest.mark.parametrize("bad_id", [0, -1])
    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_016_get_fail_nonpositive_id(self, board, bad_id, board_fail):
        """BRD-016 board_article_id 0/음수 조회 실패 (공통).

        존재하지 않는 id(0, -1) 단건조회 → 실패.
        기대(명세서 '게시글 단건조회' fail):
          - HTTP status_code == 200
          - _result.status == 'fail'
          - fail_code == 'resource_not_found'
          - 스키마: _result, fail_code (실측상 fail_message/fail_detail도 포함)
        (실측: fail_detail = {"resource_type":"board_article_model","resource_ident":[<id>]})
        """
        resp = board.get_article(bad_id)

        body = board_fail(resp, fail_code="resource_not_found", status_code=400, reason="param")
        assert "fail_message" in body and "fail_detail" in body, body

    @pytest.mark.parametrize("author_fixture,actor_fixture", CROSS_ACCOUNT_DEV)
    def test_brd_017_edit_others_article_blocked(self, request, author_fixture,
                                                 actor_fixture, track_articles, board_fail):
        """BRD-017 타인 게시글 수정 시도 → 권한 차단 (dev, cross-account).

        수정은 정상 차단(삭제와 달리 버그 아님). 학습자·교육자 모두 타인 글 수정 불가(동일).
        기대(명세서 '게시글 수정' fail):
          - HTTP status_code == 200
          - _result.status == 'fail'
          - fail_code == 'resource_not_found'
          - (행위 검증) 원본 글이 실제로 변경되지 않음
        prod은 타 계정 글 생성이 불가하여 dev에서만(2방향).
        """
        author = request.getfixturevalue(author_fixture)
        actor = request.getfixturevalue(actor_fixture)

        # 작성자가 글 생성
        original_title = "수정차단 대상 글"
        aid = self._make_own_article(author, track_articles, original_title, "<p>원본</p>", is_secret=False)

        # 비작성자가 수정 시도 → 차단되어야 함
        resp = actor.update_article(aid, "몰래 수정", "<p>변경 시도</p>", is_secret=False)
        board_fail(resp, fail_code="resource_not_found")

        # 원본이 실제로 바뀌지 않았는지 작성자로 재조회
        after = author.get_article(aid).json()["board_article"]
        assert after["title"] == original_title, after

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_018_delete_own_article(self, board, track_articles, board_ok):
        """BRD-018 본인 게시글 삭제 성공 (공통).

        절차: (setup) 본인 글 생성 → 삭제 → 재조회로 삭제 확인.
        기대(명세서 '게시글 삭제'):
          - 삭제 응답 _result.status == 'ok'
          - 이후 단건조회 시 _result.status == 'fail', fail_code == 'resource_not_found'
        """

        # setup: 본인 글 생성
        created = board.create_article("삭제 대상 글", "<p>내용</p>", is_secret=False)
        assert created.status_code == 200, created.text
        aid = created.json().get("board_article_id")
        assert isinstance(aid, int), f"setup 게시글 생성 실패: {created.text}"
        track_articles.append((board, aid))  # 안전망: 테스트가 지우지만 실패 대비(이미 삭제면 무시됨)

        # 삭제
        resp = board.delete_article(aid)
        board_ok(resp)

        # 재조회로 삭제 확인
        after = board.get_article(aid).json()
        assert after["_result"]["status"] == "fail", after
        assert after["fail_code"] == "resource_not_found", after

    @pytest.mark.bug
    @pytest.mark.security
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

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_020_delete_nonexistent_article(self, board, board_fail):
        """BRD-020 존재하지 않는 게시글 삭제 실패 (공통).

        기대(명세서 '게시글 삭제' fail):
          - HTTP status_code == 200
          - _result.status == 'fail'
          - fail_code == 'resource_not_found'
        """
        resp = board.delete_article(99999999)

        board_fail(resp, fail_code="resource_not_found")

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_021_list_articles(self, board, board_ok):
        """BRD-021 게시글 목록 조회 (공통).

        기대(명세서 '게시글 목록'):
          - HTTP status_code == 200
          - _result.status == 'ok'
          - board_articles: 배열(list) 반환 (단건조회보다 평면적: content_short 등)
          - board_article_count: 정수(전체 건수)
        """
        resp = board.list_articles(offset=0, count=20)

        body = board_ok(resp)
        assert isinstance(body["board_articles"], list), body
        assert isinstance(body["board_article_count"], int), body

        # 목록 전체를 스키마로 검증 (필드 존재 + 타입 + nullable 규칙)
        assert_valid_schema(body["board_articles"], BoardSchemas.BOARD_ARTICLE_LIST)

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_022_like_add(self, board, track_articles, board_ok):
        """BRD-022 게시글 좋아요 추가 성공 (공통, 본인 글).

        기대(명세서 '게시글 좋아요 추가'):
          - like/add _result.status == 'ok'
          - 이후 조회 시 is_liked == True, board_article_like_count 증가(+1)
        """
        aid = self._make_own_article(board, track_articles, "좋아요 추가 대상", "<p>내용</p>", is_secret=False)

        before = board.get_article(aid).json()["board_article"]
        resp = board.like_add(aid)
        board_ok(resp)

        after = board.get_article(aid).json()["board_article"]
        assert after["is_liked"] is True, after
        assert after["board_article_like_count"] == before["board_article_like_count"] + 1, after

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_023_like_count_reflected(self, board, track_articles, board_ok):
        """BRD-023 좋아요 추가 후 like_count·is_liked 반영 검증 (공통, 본인 글).

        절차: 좋아요 전 get(N) → like/add → 다시 get.
        기대: board_article_like_count == N + 1, is_liked == True.
        """
        aid = self._make_own_article(board, track_articles, "좋아요 카운트 검증", "<p>내용</p>", is_secret=False)

        # 좋아요 전 N 기록
        n = board.get_article(aid).json()["board_article"]["board_article_like_count"]

        # 좋아요
        board_ok(board.like_add(aid))

        # 좋아요 후 N+1, is_liked=True
        after = board.get_article(aid).json()["board_article"]
        assert after["board_article_like_count"] == n + 1, after
        assert after["is_liked"] is True, after

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_024_self_like_allowed(self, board, track_articles, board_ok):
        """BRD-024 본인 게시글 좋아요(self-like) 허용 (공통).

        기대: 본인 글에 like/add → _result.status == 'ok' (self-like 허용).
        """
        aid = self._make_own_article(board, track_articles, "self-like 대상", "<p>내용</p>", is_secret=False)

        resp = board.like_add(aid)
        board_ok(resp)

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_025_like_idempotent(self, board, track_articles, board_ok):
        """BRD-025 이미 좋아요한 글 재추가 (멱등성) (공통, 본인 글).

        절차: like/add 1회 → 재호출.
        기대: 재호출도 _result.status == 'ok', board_article_like_count 중복 증가 없음.
        """
        aid = self._make_own_article(board, track_articles, "멱등 좋아요 대상", "<p>내용</p>", is_secret=False)

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

    # ══════════════ 댓글 (comment) ══════════════

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
                                                 actor_fixture, track_articles, board_fail):
        """BRD-044 타인 댓글 수정 시도 → 권한 차단 (dev, cross-account).

        수정은 정상 차단. 기대: _result.status=='fail', fail_code=='resource_not_found'.
        """
        author = request.getfixturevalue(author_fixture)
        actor = request.getfixturevalue(actor_fixture)
        aid = self._make_own_article(author, track_articles)
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
                                                   actor_fixture, track_articles, board_fail):
        """BRD-046 타인 댓글 삭제 시도 → 권한 차단 (dev, cross-account).

        댓글 삭제는 정상 차단(게시글 삭제 버그와 대조).
        기대: _result.status=='fail', fail_code=='insufficient_permission'.
        """
        author = request.getfixturevalue(author_fixture)
        actor = request.getfixturevalue(actor_fixture)
        aid = self._make_own_article(author, track_articles)
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

    # ══════════════ 인증/인가 (auth) ══════════════

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

    # ══════════════ 비밀글/XSS/content ══════════════

    @pytest.mark.bug
    @pytest.mark.security
    @pytest.mark.xfail(reason="V7#3 비작성자가 타인 비밀글 조회 가능. 고쳐지면 XPASS로 알림", strict=False)
    @pytest.mark.parametrize("author_fixture,reader_fixture", CROSS_ACCOUNT_DEV)
    def test_brd_056_others_secret_article_blocked(self, request, author_fixture,
                                                   reader_fixture, track_articles):
        """BRD-056 [버그] 타인 비밀글 조회 가능 (dev, cross-account).

        보안 기대: 비작성자는 is_secret=true 글 조회 차단(_result.status=='fail').
        실측(V7#3 버그): 비작성자도 status=ok로 content까지 조회됨 → 아래 assert 실패 → xfail.
        """
        author = request.getfixturevalue(author_fixture)
        reader = request.getfixturevalue(reader_fixture)
        aid = self._make_own_article(author, track_articles,
                                     title="비밀글", content="<p>비밀 내용</p>", is_secret=True)

        body = reader.get_article(aid).json()
        assert body["_result"]["status"] == "fail", f"비작성자 비밀글 조회 차단 실패(버그): {body}"

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_057_html_content_preserved(self, board, track_articles):
        """BRD-057 content 허용 HTML 태그 보존 검증 (공통).

        기대: 허용 태그(p, b, i 등)는 get/ 응답에 원문 그대로 보존.
        """
        content = "<p><b>굵게</b><i>기울임</i></p>"
        aid = self._make_own_article(board, track_articles, title="HTML 태그 글", content=content)

        stored = board.get_article(aid).json()["board_article"]["content"]
        assert stored == content, stored

    @pytest.mark.bug
    @pytest.mark.security
    @pytest.mark.xfail(reason="V7#4 저장형 XSS: content 미새니타이징. 고쳐지면 XPASS로 알림", strict=False)
    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_058_xss_content_sanitized(self, board, track_articles):
        """BRD-058 [버그] content 위험 태그 미새니타이징 (저장형 XSS) (공통).

        보안 기대: 위험 태그/속성은 제거 또는 이스케이프되어 원문 그대로 저장되면 안 됨.
        실측(V7#4 버그): script/onerror/iframe 등이 원문 그대로 저장·반환됨 → 아래 assert 실패 → xfail.
        """
        payload = "<img src=x onerror=alert(1)><iframe src=//evil></iframe>"
        aid = self._make_own_article(board, track_articles, title="XSS 글", content=payload)

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
    def test_brd_061_write_read_consistency(self, board, track_articles):
        """BRD-061 작성 직후 반환 id 즉시 조회 (write-read 일관성) (공통).

        기대: 즉시 조회 성공, title/content 작성값과 일치.
        """
        title, content = "즉시조회 제목", "<p>즉시조회 내용</p>"

        aid = self._make_own_article(board, track_articles, title, content, is_secret=False)

        art = board.get_article(aid).json()["board_article"]
        assert_valid_schema(art, BoardSchemas.BOARD_ARTICLE)
        assert art["id"] == aid, art
        assert art["title"] == title, art
        assert art["content"] == content, art

    # ══════════════ 첨부파일 (attachment) ══════════════

    @pytest.mark.parametrize("board", COMMON_TARGETS, indirect=True)
    def test_brd_062_attachment_upload(self, board, board_ok):
        """BRD-062 첨부파일 업로드 성공 (공통).

        기대: _result.status=='ok', 업로드된 파일 URL 반환.
        (※ 명세 필드 attachment_files → 실제 attachment_file, 응답은 {_result, url})
        """
        resp = board.attachment_upload("test.png", _PNG_1x1, "image/png")

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
            "첨부 연결 글", "<p>첨부 테스트</p>", "qa_test.png", _PNG_1x1, content_type="image/png")

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

    # ══════════════ 게시판(board) 관리 — 학습자·교육자 모두 권한 없음 ══════════════

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
