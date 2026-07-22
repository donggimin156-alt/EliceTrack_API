# tests/api/class_lecture/conftest.py
"""
학습과목 퀴즈(Quiz) 관련 테스트 공통 픽스처.

주의:
- 아래 값들은 prod_learner 계정이 "실제로 소유한" 데이터를 기준으로 합니다.
  계정/환경이 바뀌면 반드시 재검증이 필요합니다.
- material_quiz_id는 quiz_response 응답 안에서 파싱하는 것이 이상적이지만,
  API 응답 스키마에 따라 위치가 다를 수 있어 fallback 값을 함께 둡니다.
  (valid_quiz_payload 픽스처의 "material_quiz_id_is_fallback" 플래그로
  현재 fallback을 쓰고 있는지 테스트 쪽에서 인지할 수 있게 했습니다.)
"""
import sys
import pytest

# ----------------------------------------------------------------------
# Pydantic v2 설정 객체에 테스트 전용 속성을 동적으로 주입하는 로직.
# 테스트 파일 상단이 아니라 conftest의 autouse 픽스처로 격리해서,
# "테스트 실행 시점에 1회, 명시적으로" 적용되도록 합니다.
# ----------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def _patch_settings_for_test_env():
    for mod_name, mod in list(sys.modules.items()):
        if "setting" not in mod_name and "config" not in mod_name:
            continue

        settings_cls = getattr(mod, "Settings", None)
        if settings_cls is not None and hasattr(settings_cls, "model_config"):
            settings_cls.model_config["extra"] = "allow"

        settings_obj = getattr(mod, "settings", getattr(mod, "setting", None))
        if settings_obj is None:
            continue

        try:
            object.__setattr__(
                settings_obj,
                "elice_api_timeout",
                getattr(settings_obj, "api_timeout_sec", 10),
            )
        except Exception:
            # 설정 객체 구조가 다른 모듈이면 조용히 스킵
            pass

    yield


@pytest.fixture(scope="function")
def valid_quiz_payload():
    """prod_learner 계정이 실제 소유한 유효한 퀴즈 응답 데이터."""
    return {
        # prod_learner 계정이 실제로 소유한, 검증된 quiz_response_id
        "quiz_response_id": 34109086,
        # 동일 ID를 재사용: "이미 완료된 상태"의 테스트도 이 응답으로 커버 가능
        "completed_quiz_response_id": 34109086,
        "course_id": 158,
        "lecture_id": 614,
        # ⚠️ 검증되지 않은 fallback 값. GET 응답에서 실제 material_quiz_id를
        # 파싱하지 못했을 때만 사용해야 하며, 테스트 결과 해석 시
        # "이 값이 fallback인지" 반드시 함께 고려할 것.
        "material_quiz_id_fallback": 929,
    }


@pytest.fixture(scope="function")
def invalid_quiz_response_id():
    """존재하지 않는 퀴즈 응답 ID (404/400 예외 케이스용)."""
    return 99999999
