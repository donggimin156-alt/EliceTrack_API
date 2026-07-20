"""
학습과목 퀴즈 응답 API 테스트 — 학습자 권한으로 검증하는 기능.
명세 대조 기준: Notion "학습과목 API 명세".
엘리스 규약: HTTP는 성공/실패 여부와 관계없이 200 OK를 반환할 수 있으므로,
반드시 응답 body 내부의 `_result.status` 값과 에러 내용을 교차 검증한다.
"""
import pytest

# 퀴즈 테스트의 역할(target) 파라미터. id에 대응 TC 번호를 남겨 시트와 추적 가능하게 한다.
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

    @pytest.mark.parametrize("client_fixture", QUIZ_TARGETS)
    def test_get_quiz_response_success(self, request, client_fixture):
        """[Happy Case] 퀴즈 응답 결과 정상 조회 및 상세 데이터 구조 검증 (CL-001).

        기대값:
          - HTTP status_code == 200
          - _result.status == 'ok'
          - quiz_response 내부 필수 필드 존재 여부 확인
        """
        client = request.getfixturevalue(client_fixture)
        quiz_response_id = 34109086

        # 1. API 호출
        resp = client.get(
            "material_quiz/response/get/",
            params={"quiz_response_id": quiz_response_id},
        )

        # 응답 Header 검증
        assert resp.status_code == 200, f"HTTP 연결 실패: {resp.text}"
        assert "application/json" in resp.headers.get("Content-Type", ""), "응답 헤더가 JSON 형식이 아닙니다."

        # 응답 Body 검증
        body = resp.json()
        if "_result" in body:
            assert body["_result"]["status"] == "ok", f"API 비즈니스 로직 처리 실패: {body}"

        assert body["_result"]["status"] == "ok", body
        assert "quiz_response" in body, body

        quiz_response = body["quiz_response"]
        assert quiz_response["id"] == quiz_response_id
        assert "user" in quiz_response
        assert "created_datetime" in quiz_response
        assert "score" in quiz_response
        assert "is_completed" in quiz_response
        assert "answer" in quiz_response



    @pytest.mark.parametrize("client_fixture", QUIZ_TARGETS)
    def test_get_quiz_response_missing_param(self, request, client_fixture):
        """[Edge Case] 필수 파라미터(quiz_response_id) 누락 시 실패 상태 검증 (CL-001-E4).

        기대값:
          - HTTP status_code == 200 (연결 성공)
          - _result.status == 'fail'
          - fail_code == 'invalid_parameter'
        """
        client = request.getfixturevalue(client_fixture)

        # 1. 필수 파라미터를 누락시키고 API 호출
        resp = client.get("material_quiz/response/get/")

        # 연결 자체는 성공하므로 200 OK 확인
        assert resp.status_code == 200, f"HTTP 연결 자체가 끊겼습니다: {resp.text}"
        
        body = resp.json()

        # 내부 에러 필드 구조 꼼꼼하게 검증
        assert "_result" in body, "오류 발생 시 _result 필드가 누락되었습니다."
        assert body["_result"]["status"] == "fail", "파라미터 누락에도 status가 fail이 아닙니다."
        assert body["_result"]["status_code"] == 400, "내부 에러 status_code가 400이 아닙니다."
        assert body.get("fail_code") == "invalid_parameter", "오류 코드가 invalid_parameter가 아닙니다."
        
        invalid_params = body.get("fail_detail", {}).get("invalid_params", {})
        assert "quiz_response_id" in invalid_params, "오류 상세 정보에 quiz_response_id가 명시되지 않았습니다."
        assert invalid_params["quiz_response_id"] == "required", "오류 원인이 required가 아닙니다."



    @pytest.mark.parametrize("client_fixture", QUIZ_TARGETS)
    def test_get_quiz_response_unauthorized(self, request, client_fixture):
        """[Edge Case] 인증 정보가 없거나 올바르지 않을 때 실패 상태 검증 (CL-001-E1).

        기대값:
          - HTTP status_code in [200, 401]
          - _result.status == 'fail'
          - _result.status_code in [401, 403]
        """
        client = request.getfixturevalue(client_fixture)
        quiz_response_id = 34109086

        # 1. 덮어쓰기 전에 기존에 들어있던 정상 토큰을 임시 저장(백업)
        original_auth = client.session.headers.get("Authorization")

        try:
            # 2. 클라이언트 헤더의 토큰 값을 가짜(만료된 값)로 강제 변경
            client.session.headers["Authorization"] = "Bearer invalid_or_expired_token"

            # 3. 요청 전송 (안전한 공통 세션 사용)
            resp = client.get(
                "material_quiz/response/get/",
                params={"quiz_response_id": quiz_response_id},
            )

            # 4. HTTP 응답 코드 및 바디 내용 검증
            assert resp.status_code in [200, 401], f"의도치 않은 HTTP 상태 코드: {resp.status_code}"
            body = resp.json()
            
            assert "_result" in body, "오류 발생 시 _result 필드가 누락되었습니다."
            assert body["_result"]["status"] == "fail", "비인증 요청임에도 status가 fail이 아닙니다."
            assert body["_result"]["status_code"] in [401, 403], f"인증 실패 코드가 올바르지 않습니다: {body}"

        finally:
            # 5. [Teardown] 다른 테스트에 영향이 가지 않도록 원래 정상 토큰 복구
            if original_auth:
                client.session.headers["Authorization"] = original_auth
            else:
                client.session.headers.pop("Authorization", None)



    @pytest.mark.parametrize("client_fixture", QUIZ_TARGETS)
    def test_get_quiz_response_not_found(self, request, client_fixture):
        """[Edge Case] 시스템에 존재하지 않는 quiz_response_id 요청 시 실패 상태 검증 (CL-001-E2).

        기대값:
          - HTTP status_code == 200
          - _result.status == 'fail'
          - _result.status_code in [400, 404]
        """
        client = request.getfixturevalue(client_fixture)
        invalid_id = 99999999  # 존재하지 않는 임의의 ID

        resp = client.get(
            "material_quiz/response/get/",
            params={"quiz_response_id": invalid_id},
        )

        assert resp.status_code == 200, f"HTTP 연결 실패: {resp.text}"
        body = resp.json()
        
        # 내부 실패 규약 검증
        assert "_result" in body, "오류 발생 시 _result 필드가 누락되었습니다."
        assert body["_result"]["status"] == "fail", "존재하지 않는 ID 요청임에도 status가 fail이 아닙니다."
        assert body["_result"]["status_code"] in [400, 404], f"내부 에러 status_code가 잘못되었습니다: {body}"