# tests/api/class_lecture/conftest.py
import pytest

@pytest.fixture(scope="function")
def valid_quiz_payload():
    """정상적인 퀴즈 조회/제출 테스트를 위해 사용할 공통 페이로드 데이터"""
    return {
        "quiz_response_id": 12345,  # 테스트용 기본 ID
        "lecture_id": 99,
        "course_id": 10
    }

@pytest.fixture(scope="function")
def invalid_quiz_response_id():
    """존재하지 않는 퀴즈 응답 ID (404 예외 케이스용)"""
    return 99999999  # 존재할 수 없는 극단적인 큰 수
