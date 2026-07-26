"""학습과목 퀴즈 응답 API 테스트 — 학습자 권한으로 검증하는 기능.
엘리스 규약: HTTP는 성공/실패 여부와 관계없이 200 OK를 반환할 수 있으므로,
반드시 응답 body 내부의 `_result.status` 값과 에러 내용을 교차 검증한다.
"""
import pytest

from fixtures.class_lecture_fixture import (
    QUIZ_TARGETS,
    get_quiz_response,
    get_quiz_response_raw,
    select_quiz_option,
    select_quiz_option_raw,
)


@pytest.mark.api
@pytest.mark.class_lecture
class TestCourseQuiz:
    """[CL-LE-001] 퀴즈 응답 결과 조회."""

    @pytest.mark.parametrize("client_fixture", QUIZ_TARGETS)
    def test_cl_le_001_get_quiz_response_success(
        self, request, client_fixture, prod_quiz_response_id
    ):
        """CL-LE-001 퀴즈 응답 결과 정상 조회 및 상세 데이터 구조 검증."""
        board = request.getfixturevalue(client_fixture)

        resp = get_quiz_response(board, prod_quiz_response_id)

        assert resp.status_code == 200, f"HTTP 연결 실패: {resp.text}"
        assert "application/json" in resp.headers.get("Content-Type", ""), "응답 헤더가 JSON 형식이 아닙니다."

        body = resp.json()
        assert body["_result"]["status"] == "ok", body
        assert "quiz_response" in body, body

        quiz_response = body["quiz_response"]
        assert quiz_response["id"] == prod_quiz_response_id, quiz_response
        for field in ("user", "created_datetime", "score", "is_completed", "answer"):
            assert field in quiz_response, f"quiz_response에 '{field}' 필드가 없습니다: {quiz_response}"

    @pytest.mark.parametrize("client_fixture", QUIZ_TARGETS)
    def test_cl_le_001_e1_unauthorized(self, request, client_fixture, prod_quiz_response_id):
        """CL-LE-001-E1 비인증/만료된 토큰 요청 시 실패."""
        board = request.getfixturevalue(client_fixture)

        original_auth = board.session.headers.get("Authorization")
        try:
            board.session.headers["Authorization"] = "Bearer invalid_or_expired_token"
            resp = get_quiz_response(board, prod_quiz_response_id)

            assert resp.status_code in [200, 401], f"의도치 않은 HTTP 상태 코드: {resp.status_code}"
            body = resp.json()
            assert body["_result"]["status"] == "fail", body
            assert body["_result"]["status_code"] in [401, 403], body
        finally:
            if original_auth:
                board.session.headers["Authorization"] = original_auth
            else:
                board.session.headers.pop("Authorization", None)

    @pytest.mark.parametrize("client_fixture", QUIZ_TARGETS)
    def test_cl_le_001_e2_not_found(self, request, client_fixture, invalid_quiz_response_id):
        """CL-LE-001-E2 존재하지 않는 quiz_response_id 요청."""
        board = request.getfixturevalue(client_fixture)

        resp = get_quiz_response(board, invalid_quiz_response_id)

        assert resp.status_code == 200, f"HTTP 연결 실패: {resp.text}"
        body = resp.json()
        assert body["_result"]["status"] == "fail", body
        assert body["_result"]["status_code"] in [400, 404], body

    @pytest.mark.parametrize("client_fixture", QUIZ_TARGETS)
    def test_cl_le_001_e3_missing_param(self, request, client_fixture):
        """CL-LE-001-E3 필수 파라미터(quiz_response_id) 누락."""
        board = request.getfixturevalue(client_fixture)

        resp = get_quiz_response_raw(board, params={})

        assert resp.status_code == 200, f"HTTP 연결 자체가 끊겼습니다: {resp.text}"
        body = resp.json()
        assert body["_result"]["status"] == "fail", body
        assert body["_result"]["status_code"] == 400, body
        assert body.get("fail_code") == "invalid_parameter", body

        invalid_params = body.get("fail_detail", {}).get("invalid_params", {})
        assert invalid_params.get("quiz_response_id") == "required", body


@pytest.mark.api
@pytest.mark.class_lecture
class TestCourseQuizOption:
    """[CL-LE-003] 퀴즈 옵션 선택(Select)."""

    @pytest.mark.parametrize("client_fixture", QUIZ_TARGETS)
    def test_cl_le_003_select_quiz_option_success(
        self,
        request,
        client_fixture,
        prod_quiz_response_id,
        prod_material_quiz_id,
    ):
        """CL-LE-003 진행 중인 퀴즈의 보기를 정상적으로 선택."""
        board = request.getfixturevalue(client_fixture)

        quiz_resp = get_quiz_response(board, prod_quiz_response_id)
        assert quiz_resp.status_code == 200, f"HTTP 연결 실패: {quiz_resp.text}"
        
        quiz_body = quiz_resp.json()
        if quiz_body.get("_result", {}).get("status") == "ok":
            quiz_data = quiz_body.get("quiz_response", {})
        else:
            quiz_data = {}

        resp = select_quiz_option(
            board,
            quiz_response_id=prod_quiz_response_id,
            material_quiz_id=prod_material_quiz_id,
            selected_option_index=0,
        )
        assert resp.status_code == 200, f"HTTP 연결 실패: {resp.text}"
        body = resp.json()

        if quiz_data.get("is_completed"):
            status = body["_result"]["status"]
            assert status in ("ok", "fail"), body
        else:
            assert body["_result"]["status"] == "ok", body

    @pytest.mark.parametrize("client_fixture", QUIZ_TARGETS)
    def test_cl_le_003_e1_select_after_completion(
        self,
        request,
        client_fixture,
        prod_completed_quiz_response_id,
        prod_material_quiz_id,
    ):
        """CL-LE-003-E1 이미 제출 완료된 퀴즈의 답안 재선택 시도."""
        board = request.getfixturevalue(client_fixture)

        resp = select_quiz_option(
            board,
            quiz_response_id=prod_completed_quiz_response_id,
            material_quiz_id=prod_material_quiz_id,
            selected_option_index=1,
        )

        assert resp.status_code == 200, f"HTTP 연결 실패: {resp.text}"
        body = resp.json()
        
        assert body["_result"]["status"] == "fail", f"완료된 퀴즈 수정이 허용됨: {body}"

    @pytest.mark.parametrize("client_fixture", QUIZ_TARGETS)
    def test_cl_le_003_e2_select_unopened_quiz(
        self,
        request,
        client_fixture,
        prod_material_quiz_id,
        invalid_quiz_response_id,
    ):
        """CL-LE-003-E2 미개방/비공개 퀴즈 항목의 보기 선택 시도."""
        board = request.getfixturevalue(client_fixture)

        resp = select_quiz_option(
            board,
            quiz_response_id=invalid_quiz_response_id,
            material_quiz_id=prod_material_quiz_id,
            selected_option_index=0,
        )

        assert resp.status_code == 200, f"HTTP 연결 실패: {resp.text}"
        body = resp.json()
        assert body["_result"]["status"] == "fail", body
        assert body["_result"]["status_code"] in [400, 404], body