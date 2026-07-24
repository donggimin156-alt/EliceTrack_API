# fixtures/class_lecture_fixture.py
"""
학습과목 퀴즈(material_quiz) 관련 테스트 공통 픽스처.
"""

import os
import pytest
from core.config import settings

# settings 인스턴스에 elice_api_timeout이 없으면, api_timeout_sec 값으로 보정.
if not hasattr(settings, "elice_api_timeout"):
    object.__setattr__(settings, "elice_api_timeout", settings.api_timeout_sec)

# 퀴즈 테스트 공통 parametrize. board_fixture의 prod_learner를 그대로 사용.
QUIZ_TARGETS = [
    pytest.param("prod_learner", marks=pytest.mark.learner, id="prod-learner"),
]

# 팀 공통 기본 테스트 ID (필요시 실제 유효한 ID 값으로 수정)
DEFAULT_QUIZ_RESPONSE_ID = 34109086
DEFAULT_MATERIAL_QUIZ_ID = 614


def _int_env(var: str, default: int) -> int:
    """환경변수를 int로 읽고, 설정되어 있지 않으면 기본값(default)을 사용"""
    val = os.getenv(var, "").strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        return default

@pytest.fixture(scope="session")
def prod_quiz_response_id() -> int:
    """prod_learner 계정이 실제로 소유한, 진행 중/완료 상태를 오갈 수 있는 quiz_response_id.

    PROD_QUIZ_RESPONSE_ID 미설정 시 기본값(DEFAULT_QUIZ_RESPONSE_ID) 사용.
    """
    return _int_env("PROD_QUIZ_RESPONSE_ID", default=DEFAULT_QUIZ_RESPONSE_ID)


@pytest.fixture(scope="session")
def prod_completed_quiz_response_id(prod_quiz_response_id) -> int:
    """제출 완료(is_completed=true) 상태인 quiz_response_id.

    PROD_COMPLETED_QUIZ_RESPONSE_ID가 별도로 없으면 prod_quiz_response_id를 그대로 사용한다.
    """
    val = os.getenv("PROD_COMPLETED_QUIZ_RESPONSE_ID", "").strip()
    return int(val) if val else prod_quiz_response_id


@pytest.fixture(scope="session")
def prod_material_quiz_id(prod_quiz_response_id, prod_learner) -> int:
    """PROD_MATERIAL_QUIZ_ID가 없으면 quiz_response_id 조회를 통해 실제 material_quiz_id를 자동으로 가져와 사용한다."""
    env_val = os.getenv("PROD_MATERIAL_QUIZ_ID", "").strip()
    if env_val:
        return int(env_val)
    
    # .env에 없으면 actual quiz_response 조회 응답에서 material_quiz_id 추출
    resp = get_quiz_response(prod_learner, prod_quiz_response_id)
    if resp.status_code == 200:
        data = resp.json()
        quiz_resp = data.get("quiz_response", {})
        # 응답 구조에 맞게 material_quiz_id 또는 quiz.id 반환
        if "material_quiz_id" in quiz_resp:
            return quiz_resp["material_quiz_id"]
        elif "material_quiz" in quiz_resp and "id" in quiz_resp["material_quiz"]:
            return quiz_resp["material_quiz"]["id"]
            
    # 자동 추출 실패 시 fallback 기본값 사용
    return DEFAULT_MATERIAL_QUIZ_ID


@pytest.fixture(scope="function")
def invalid_quiz_response_id() -> int:
    """존재하지 않는 퀴즈 응답 ID (404/400 예외 케이스용)."""
    return 99999999


# ==========================================================================
# 퀴즈 API 호출 헬퍼
# ==========================================================================

def get_quiz_response(board, quiz_response_id: int):
    """퀴즈 응답 결과 단건조회 (material_quiz/response/get)."""
    return board.get("material_quiz/response/get/", params={"quiz_response_id": quiz_response_id})


def get_quiz_response_raw(board, params: dict | None = None):
    """퀴즈 응답 결과 조회 원본 호출 (필수 파라미터 누락 등 음성 테스트용)."""
    return board.get("material_quiz/response/get/", params=params or {})


def select_quiz_option(board, quiz_response_id: int, material_quiz_id: int, selected_option_index: int):
    """퀴즈 보기 선택 (material_quiz/options_set/select)."""
    return board.post("material_quiz/options_set/select/", data={
        "quiz_response_id": quiz_response_id,
        "material_quiz_id": material_quiz_id,
        "selected_option_index": selected_option_index,
    })


def select_quiz_option_raw(board, data: dict):
    """퀴즈 보기 선택 원본 호출 (음성/경계 테스트용 임의 payload)."""
    return board.post("material_quiz/options_set/select/", data=data)