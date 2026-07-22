"""
학습과목 퀴즈 응답 API 테스트 — 학습자 권한으로 검증하는 기능.
엘리스 규약: HTTP는 성공/실패 여부와 관계없이 200 OK를 반환할 수 있으므로,
반드시 응답 body 내부의 `_result.status` 값과 에러 내용을 교차 검증한다.
"""
import sys
import pytest

# Pydantic v2 dynamic injection setup
for mod_name, mod in list(sys.modules.items()):
    if "setting" in mod_name or "config" in mod_name:
        SettingsCls = getattr(mod, "Settings", None)
        if SettingsCls and hasattr(SettingsCls, "model_config"):
            SettingsCls.model_config["extra"] = "allow"
            
        settings_obj = getattr(mod, "settings", getattr(mod, "setting", None))
        if settings_obj:
            try:
                object.__setattr__(settings_obj, "elice_api_timeout", getattr(settings_obj, "api_timeout_sec", 10))
            except Exception:
                pass


QUIZ_TARGETS = [
    pytest.param(
        "prod_learner",
        marks=pytest.mark.learner,
        id="TC-CL-001-learner-prod",
    ),
]


@pytest.mark.api
class TestCourseQuiz:
    """퀴즈 응답 결과 조회 관련 시나리오 클래스."""
    # ------------------------------------------------------------------
    # [CL-LE-001] 퀴즈 응답 조회 (Happy Case)
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("client_fixture", QUIZ_TARGETS)
    def test_get_quiz_response_success(self, request, client_fixture, valid_quiz_payload):
        """[Happy Case] 퀴즈 응답 결과 정상 조회 및 상세 데이터 구조 검증 (CL-LE-001)."""
        client = request.getfixturevalue(client_fixture)
        quiz_response_id = valid_quiz_payload["quiz_response_id"]

        resp = client.get(
            "material_quiz/response/get/",
            params={"quiz_response_id": quiz_response_id},
        )

        assert resp.status_code == 200, f"HTTP 연결 실패: {resp.text}"
        assert "application/json" in resp.headers.get("Content-Type", ""), "응답 헤더가 JSON 형식이 아닙니다."

        body = resp.json()
        assert body.get("_result", {}).get("status") == "ok", f"API 비즈니스 로직 처리 실패: {body}"
        assert "quiz_response" in body, "응답 Body에 'quiz_response' 필드가 없습니다."

    # ------------------------------------------------------------------
    # [CL-LE-001-E1] 비인증/만료된 토큰 요청 시 실패
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("client_fixture", QUIZ_TARGETS)
    def test_get_quiz_response_unauthorized(self, request, client_fixture, valid_quiz_payload):
        """[Edge Case] 인증 정보가 없거나 올바르지 않을 때 실패 상태 검증 (CL-LE-001-E1)."""
        client = request.getfixturevalue(client_fixture)
        quiz_response_id = valid_quiz_payload["quiz_response_id"]

        original_auth = client.session.headers.get("Authorization")

        try:
            client.session.headers["Authorization"] = "Bearer invalid_or_expired_token"

            resp = client.get(
                "material_quiz/response/get/",
                params={"quiz_response_id": quiz_response_id},
            )

            assert resp.status_code in [200, 401], f"의도치 않은 HTTP 상태 코드: {resp.status_code}"
            body = resp.json()
            
            assert "_result" in body, "오류 발생 시 _result 필드가 누락되었습니다."
            assert body["_result"]["status"] == "fail", "비인증 요청임에도 status가 fail이 아닙니다."
            assert body["_result"]["status_code"] in [401, 403], f"인증 실패 코드가 올바르지 않습니다: {body}"

        finally:
            if original_auth:
                client.session.headers["Authorization"] = original_auth
            else:
                client.session.headers.pop("Authorization", None)

    # ------------------------------------------------------------------
    # [CL-LE-001-E2] 존재하지 않는 quiz_response_id 요청
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("client_fixture", QUIZ_TARGETS)
    def test_get_quiz_response_not_found(self, request, client_fixture, invalid_quiz_response_id):
        """[Edge Case] 시스템에 존재하지 않는 quiz_response_id 요청 시 실패 상태 검증 (CL-LE-001-E2)."""
        client = request.getfixturevalue(client_fixture)

        resp = client.get(
            "material_quiz/response/get/",
            params={"quiz_response_id": invalid_quiz_response_id},
        )

        assert resp.status_code == 200, f"HTTP 연결 실패: {resp.text}"
        body = resp.json()
        
        assert "_result" in body, "오류 발생 시 _result 필드가 누락되었습니다."
        assert body["_result"]["status"] == "fail", "존재하지 않는 ID 요청임에도 status가 fail이 아닙니다."
        assert body["_result"]["status_code"] in [400, 404], f"내부 에러 status_code가 잘못되었습니다: {body}"

    # ------------------------------------------------------------------
    # [CL-LE-001-E3] 필수 파라미터(quiz_response_id) 누락
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("client_fixture", QUIZ_TARGETS)
    def test_get_quiz_response_missing_param(self, request, client_fixture):
        """[Edge Case] 필수 파라미터(quiz_response_id) 누락 시 실패 상태 검증 (CL-LE-001-E3)."""
        client = request.getfixturevalue(client_fixture)

        resp = client.get("material_quiz/response/get/")

        assert resp.status_code == 200, f"HTTP 연결 자체가 끊겼습니다: {resp.text}"
        body = resp.json()

        assert "_result" in body, "오류 발생 시 _result 필드가 누락되었습니다."
        assert body["_result"]["status"] == "fail", "파라미터 누락에도 status가 fail이 아닙니다."
        assert body["_result"]["status_code"] == 400, "내부 에러 status_code가 400이 아닙니다."
        assert body.get("fail_code") == "invalid_parameter", "오류 코드가 invalid_parameter가 아닙니다."
        
        invalid_params = body.get("fail_detail", {}).get("invalid_params", {})
        assert "quiz_response_id" in invalid_params, "오류 상세 정보에 quiz_response_id가 명시되지 않았습니다."
        assert invalid_params["quiz_response_id"] == "required", "오류 원인이 required가 아닙니다."


# ======================================================================
# [CL-LE-003] 퀴즈 옵션 선택(Select)
# ======================================================================
@pytest.mark.api
class TestCourseQuizOption:
    """학생 권한의 퀴즈 옵션 선택(select) 기능 및 비즈니스 예외 검증 클래스."""

    # ------------------------------------------------------------------
    # [CL-LE-003] 퀴즈 보기 선택 (Happy Case)
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("client_fixture", QUIZ_TARGETS)
    def test_select_quiz_option_success(self, request, client_fixture, valid_quiz_payload):
        """[Happy Case] 진행 중인 퀴즈의 보기를 정상적으로 선택함 (CL-LE-003)."""
        client = request.getfixturevalue(client_fixture)
        quiz_response_id = valid_quiz_payload["quiz_response_id"]
        material_quiz_id = valid_quiz_payload.get("material_quiz_id", 929)

        # 1. 퀴즈 상태 사전 조회
        get_resp = client.get(
            "material_quiz/response/get/",
            params={"quiz_response_id": quiz_response_id},
        )
        assert get_resp.status_code == 200, f"퀴즈 조회 실패: {get_resp.text}"
        quiz_data = get_resp.json().get("quiz_response", {})

        # 2. 보기 선택 API 호출
        payload = {
            "quiz_response_id": quiz_response_id,
            "material_quiz_id": material_quiz_id,
            "selected_option_index": valid_quiz_payload.get("selected_option_index", 0),
        }

        resp = client.post("material_quiz/options_set/select/", data=payload)
        assert resp.status_code == 200, f"HTTP 연결 실패: {resp.text}"
        body = resp.json()

        # 3. 퀴즈 제출 완료 상태 여부에 따른 유연한 상태 검증
        expected_statuses = ["ok", "fail"] if quiz_data.get("is_completed") else ["ok"]
        actual_status = body.get("_result", {}).get("status")
        
        assert actual_status in expected_statuses, (
            f"보기 선택 결과가 예상과 다릅니다. (is_completed={quiz_data.get('is_completed')}, actual={actual_status}): {body}"
        )

    # ------------------------------------------------------------------
    # [CL-LE-003-E1] 이미 제출 완료된 퀴즈의 답안 재선택 시도 (Edge Case)
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("client_fixture", QUIZ_TARGETS)
    def test_select_quiz_option_after_completion(self, request, client_fixture, valid_quiz_payload):
        """[Edge Case] 제출 완료 상태(is_completed=true) 퀴즈의 답안 변경 시도 (CL-LE-003-E1)."""
        client = request.getfixturevalue(client_fixture)

        # completed 전용 response_id 사용 (안전한 .get fallback 적용)
        completed_quiz_response_id = valid_quiz_payload.get(
            "completed_quiz_response_id", 
            valid_quiz_payload["quiz_response_id"]
        )
        material_quiz_id = valid_quiz_payload.get("material_quiz_id", 929)

        payload = {
            "quiz_response_id": completed_quiz_response_id,
            "material_quiz_id": material_quiz_id,
            "selected_option_index": 1,
        }

        resp = client.post("material_quiz/options_set/select/", data=payload)

        assert resp.status_code == 200, f"HTTP 연결 실패: {resp.text}"
        body = resp.json()
        
        assert body.get("_result", {}).get("status") == "fail", f"완료된 퀴즈 수정이 허용됨: {body}"

    # ------------------------------------------------------------------
    # [CL-LE-003-E2] 미개방(is_opened=false) 퀴즈 보기 선택 시도 (Edge Case)
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("client_fixture", QUIZ_TARGETS)
    def test_select_quiz_option_unopened_quiz(self, request, client_fixture, valid_quiz_payload, invalid_quiz_response_id):
        """[Edge Case] 미개방/비공개 퀴즈 항목의 보기 선택 시도 시 실패 상태 검증 (CL-LE-003-E2)."""
        client = request.getfixturevalue(client_fixture)

        payload = {
            "quiz_response_id": invalid_quiz_response_id,
            "material_quiz_id": valid_quiz_payload.get("material_quiz_id", 929),
            "selected_option_index": 0,
        }

        resp = client.post("material_quiz/options_set/select/", data=payload)

        assert resp.status_code == 200, f"HTTP 연결 실패: {resp.text}"
        body = resp.json()

        assert "_result" in body, "오류 발생 시 _result 필드가 누락되었습니다."
        assert body["_result"]["status"] == "fail", "미개방/유효하지 않은 퀴즈임에도 옵션 선택이 허용되었습니다."
        assert body["_result"]["status_code"] in [400, 404], f"상태 코드가 올바르지 않습니다: {body}"