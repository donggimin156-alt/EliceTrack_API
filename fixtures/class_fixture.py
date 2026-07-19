# fixtures/class_fixture.py
"""Classroom Course API 전용 픽스처 — 인증·ClassApi·과목 목록 응답 준비."""
import pytest

from api.endpoints.class_api import ClassApi
from fixtures.elice_auth import get_env_config, make_authenticated_session


def _make_class_client(env_name: str, role: str, skip_msg: str) -> ClassApi:
    """인증 정보가 없으면 skip, 있으면 Bearer 세션이 세팅된 ClassApi를 생성한다."""
    session = make_authenticated_session(env_name, role)
    if session is None:
        pytest.skip(skip_msg)

    env = get_env_config(env_name)
    return ClassApi(
        session,
        classroom_id=env["CLASSROOM_ID"],
        env_name=env_name,
    )


@pytest.fixture(scope="session")
def class_api() -> ClassApi:
    """
    prod 학습자 ClassApi.

    CLASSROOM_ID·CLASSROOM_API_URL은 settings.elice_environments["prod"] (SSOT).
    인증은 fixtures/elice_auth.py (SSOT)를 사용하며 board fixture에 의존하지 않는다.
    """
    return _make_class_client("prod", "LEARNER", "prod 학습자 토큰 없음 (PROD_LEARNER_TOKEN)")


@pytest.fixture(scope="session")
def total_course_count(class_api) -> int:
    """
    매직넘버(TOTAL_COURSE_COUNT = 20) 대신, 세션 시작 시
    실제 전체 과목 수를 한 번 조회해서 동적으로 계산한다.
    """
    resp = class_api.get_course_list(skip=0, count=9999)
    assert resp.status_code == 200, "전체 과목 수를 조회하기 위한 사전 요청이 실패했습니다."
    return len(resp.json())


@pytest.fixture
def course_list(class_api):
    """
    skip=0, count=10 기본 목록 응답 (여러 테스트가 공유).

    응답을 만드는 시점에 바로 200 여부를 검증한다.
    (autouse + teardown 시점 검사 방식은 pytest의 LIFO teardown 순서 때문에
    "fixture가 이미 정리됨" 에러가 나서, 생성 시점 검증으로 바꿨다.)
    """
    resp = class_api.get_course_list(skip=0, count=10)
    assert resp.status_code == 200, f"course_list 응답 상태 코드 이상: {resp.status_code}"
    return resp


@pytest.fixture
def full_course_list(class_api, total_course_count):
    """전체 과목 수만큼 조회한 응답 (Business 검증용). 생성 시점에 200 검증."""
    resp = class_api.get_course_list(skip=0, count=total_course_count)
    assert resp.status_code == 200, f"full_course_list 응답 상태 코드 이상: {resp.status_code}"
    return resp


@pytest.fixture
def course_data(course_list):
    """course_list.json() 반복 호출 제거용. 테스트에서는 이 fixture만 받아서 쓴다."""
    return course_list.json()


@pytest.fixture
def full_course_data(full_course_list):
    """full_course_list.json() 반복 호출 제거용."""
    return full_course_list.json()
