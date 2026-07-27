# tests/api/board/test_board_article.py
"""게시글 CRUD·조회·목록·경계 API 테스트 (작성/수정/조회/삭제/목록/비밀글 생성·경계값).

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
class TestBoardArticle:
    """게시글 CRUD·조회·목록·경계 API 테스트 (작성/수정/조회/삭제/목록/비밀글 생성·경계값)."""

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
    def test_brd_002_edit_own_article(self, board, board_ok, make_article):
        """BRD-002 본인 게시글 수정 성공 (공통).

        절차: (setup) 본인 글 생성 → 수정 호출 → 재조회.
        기대(명세서 '게시글 수정'):
          - HTTP status_code == 200
          - _result.status == 'ok'
          - 반환 board_article_id == 요청 board_article_id
          - 재조회 시 modified_datetime 이 null → 값으로 갱신
        """
        # setup: 수정할 본인 글 생성 (생성 실패 시 원인이 드러나도록 방어)
        aid = make_article(board, "수정 전 제목", "<p>수정 전</p>", is_secret=False)

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
        # raw 폼: title을 의도적으로 누락(타입 헬퍼로는 표현 불가한 음성 케이스)
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
        # raw 폼: content를 의도적으로 누락(타입 헬퍼로는 표현 불가한 음성 케이스)
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
        # raw 폼: is_secret을 의도적으로 누락(타입 헬퍼로는 표현 불가한 음성 케이스)
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
        # raw 폼: classroom_id·board_id 둘 다 의도적으로 누락(타입 헬퍼로는 표현 불가한 음성 케이스)
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
        # raw 폼: title을 빈 문자열("")로 — 타입 헬퍼가 막지 못하는 경계값을 의도적으로 전송
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
        # raw 폼: is_secret에 비boolean 값을 의도적으로 전송(타입 헬퍼로는 표현 불가)
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
    def test_brd_012_get_own_article(self, board, board_ok, make_article):
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
        aid = make_article(board, title, content, is_secret=False)

        # 단건조회
        resp = board.get_article(aid)
        body = board_ok(resp)

        art = body["board_article"]
        assert_valid_schema(art, BoardSchemas.BOARD_ARTICLE)
        assert art["id"] == aid, art
        assert art["title"] == title, art
        assert art["content"] == content, art  # content 원문 보존

        # 실측 필드 스냅샷 (위 assert_valid_schema 와 역할이 다르므로 중복이 아님)
        #  - board_schema: 안정적 구조 계약(타입·nullable·중첩)만 검증
        #  - 아래 수동 검사: "현재 실제로 오는 필드" 기록. user의 email/display_email은
        #    타인 글 이메일 노출 버그(BRD-013/014, xfail)의 증거라서, 노출이 사라지면
        #    여기서도 실패해 변화를 알리는 것이 목적이다.
        #    => 이메일 노출을 "필수 계약"으로 못 박게 되므로 스키마 required로 옮기지 않는다.
        #    (게시글 user에는 email이 있지만 댓글 user에는 없어, 공용 _USER 스키마로도 표현 불가)
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
                                                 actor_fixture, board_fail, make_article):
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
        aid = make_article(author, original_title, "<p>원본</p>", is_secret=False)

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
    def test_brd_068_create_article_without_cohort(self, board, board_ok, track_articles):
        """BRD-068 cohort_id 없이도 게시글 작성은 성공한다 (공통).

        create_article은 코호트 환경(prod)에서 cohort_id를 자동으로 실어 보내므로,
        cohort_id가 빠진 경로는 create_article_raw로 직접 만들어 검증한다.

        기대(명세서 '게시글 작성'):
          - HTTP status_code == 200
          - _result.status == 'ok'  (cohort_id는 선택 항목)
          - board_article_id: int 반환

        주의: 이렇게 만든 글은 cohort가 null이라 웹 UI 게시판 목록
        (/classroom/{id}/article?filter_cohort_id=...)에는 노출되지 않는다.
        API로는 조회되지만 화면에서는 보이지 않는 상태이므로, 실제 시나리오
        테스트는 cohort_id를 함께 보내는 create_article을 사용한다.
        """
        resp = board.create_article_raw({
            "title": "cohort 없는 게시글",
            "content": "<p>내용</p>",
            "is_secret": "false",
            "classroom_id": board.classroom_id,
        })

        body = board_ok(resp)
        article_id = body.get("board_article_id")
        if isinstance(article_id, int):
            track_articles.append((board, article_id))

        assert isinstance(article_id, int), body
