# fixtures/class_fixture_v2.py
"""Classroom Course API 전용 픽스처 — v2 리팩토링 버전."""

import pytest
import requests

from api.endpoints.class_api import ClassApi
from api.utils.elice_auth import get_env_config, make_authenticated_session

ENV_NAME = "prod"

# E5/E6 엣지 케이스용: 형식은 유효하지만 실존하지 않는 classroom_id / UUID 형식 자체가 아닌 값
NONEXISTENT_BUT_VALID_UUID = "00000000-0000-0000-0000-000000000000"
INVALID_UUID_FORMAT = "000000000-000000000000-000000-0-0000"


def _build_class_api(
    session: requests.Session,
    classroom_id: str | None = None,
    env_name: str = ENV_NAME,
) -> ClassApi:
    """세션과 환경 설정을 바탕으로 ClassApi 인스턴스를 생성한다."""
    env = get_env_config(env_name)
    resolved_classroom_id = classroom_id or env["CLASSROOM_ID"]
    return ClassApi(session, classroom_id=resolved_classroom_id, env_name=env_name)


@pytest.fixture(scope="session")
def assert_response():
    """응답 상태코드 검증과 JSON 파싱을 한 번에 처리하는 헬퍼."""

    def _assert_response(resp: requests.Response, expected_status: int):
        assert resp.status_code == expected_status, (
            f"status_code 불일치: expected={expected_status}, actual={resp.status_code}, "
            f"body={resp.text}"
        )
        try:
            return resp.json()
        except ValueError as exc:
            raise AssertionError(
                "응답 본문이 JSON 형식이 아닙니다. "
                f"status={resp.status_code}, content_type={resp.headers.get('content-type')}, "
                f"body={resp.text}"
            ) from exc

    return _assert_response


@pytest.fixture(scope="session")
def class_api_factory():
    """ClassApi 인스턴스를 생성하는 공통 팩토리 fixture."""

    def _create_class_api(
        *,
        classroom_id: str | None = None,
        session: requests.Session | None = None,
        env_name: str = ENV_NAME,
        role: str = "LEARNER",
        skip_msg: str | None = None,
    ) -> ClassApi:
        if session is None:
            session = make_authenticated_session(env_name, role)
            if session is None:
                pytest.skip(
                    skip_msg or f"{env_name} 환경의 {role} 인증 정보가 없어 테스트를 건너뜁니다."
                )

        return _build_class_api(session, classroom_id=classroom_id, env_name=env_name)

    return _create_class_api


@pytest.fixture(scope="session")
def class_api(class_api_factory) -> ClassApi:
    """prod 학습자용 기본 ClassApi fixture."""
    return class_api_factory(
        role="LEARNER",
        skip_msg="prod 학습자 토큰 없음 (PROD_LEARNER_TOKEN)",
    )


@pytest.fixture(scope="session")
def total_course_count(class_api, assert_response) -> int:
    """실제 등록된 과목 수를 동적으로 조회한다."""
    resp = class_api.get_course_list(skip=0, count=9999)
    data = assert_response(resp, 200)
    return len(data)


@pytest.fixture
def course_list(class_api, assert_response):
    """기본 과목 목록 응답을 한 번 생성해 재사용한다."""
    resp = class_api.get_course_list(skip=0, count=10)
    assert_response(resp, 200)
    return resp


@pytest.fixture
def full_course_list(class_api, total_course_count, assert_response):
    """전체 과목 수를 기준으로 전체 목록 응답을 생성한다."""
    resp = class_api.get_course_list(skip=0, count=total_course_count)
    assert_response(resp, 200)
    return resp


@pytest.fixture
def course_data(course_list):
    """course_list 응답을 파싱한 결과를 반환한다."""
    return course_list.json()


@pytest.fixture
def full_course_data(full_course_list):
    """full_course_list 응답을 파싱한 결과를 반환한다."""
    return full_course_list.json()


@pytest.fixture(scope="session")
def learner_session(class_api):
    """기본 인증 세션을 재사용한다."""
    return class_api.session


@pytest.fixture
def nonexistent_classroom_api(learner_session, class_api_factory):
    """실존하지 않는 classroom_id를 사용하는 클라이언트."""
    return class_api_factory(
        classroom_id=NONEXISTENT_BUT_VALID_UUID,
        session=learner_session,
    )


@pytest.fixture
def invalid_uuid_classroom_api(learner_session, class_api_factory):
    """UUID 형식이 아닌 classroom_id를 사용하는 클라이언트."""
    return class_api_factory(
        classroom_id=INVALID_UUID_FORMAT,
        session=learner_session,
    )


@pytest.fixture
def unauthenticated_class_api(class_api, class_api_factory):
    """Authorization 헤더 없이 요청하는 클라이언트."""
    plain_session = requests.Session()
    return class_api_factory(
        classroom_id=class_api.classroom_id,
        session=plain_session,
    )


@pytest.fixture
def tampered_token_class_api(class_api, class_api_factory):
    """변조된 토큰을 사용하는 클라이언트."""
    broken_session = requests.Session()
    broken_session.headers.update({"Authorization": "Bearer this-is-not-a-valid-token-xxx"})
    return class_api_factory(
        classroom_id=class_api.classroom_id,
        session=broken_session,
    )


@pytest.fixture
def other_account_class_api(class_api, class_api_factory):
    """다른 계정으로 접근하는 클라이언트."""
    return class_api_factory(
        classroom_id=class_api.classroom_id,
        role="LEARNER_OTHER_ACCOUNT",
        skip_msg="다른 계정 인증 정보(LEARNER_OTHER_ACCOUNT)가 준비되지 않아 스킵",
    )

@pytest.fixture(scope="session")
def educator_class_api(class_api_factory) -> ClassApi:
    """dev 교육자용 ClassApi — 과목 추가(bulk)/순서 변경 등 교육자 전용 액션에 사용."""
    return class_api_factory(
        env_name="dev",
        role="EDUCATOR",
        skip_msg="dev 교육자 토큰 없음 (DEV_EDUCATOR_TOKEN)",
    )


@pytest.fixture
def wait_for_task_completion(assert_response):
    """status가 terminal 상태(completed/failed)에 도달할 때까지 폴링.

    실증된 전이: queued -> assigned -> completed (완료 후 재조회해도 동일 응답, 멱등 확인됨)
    failed 상태는 아직 미실증 — 확인되면 이 주석과 E-12e 갱신 필요.
    """
    import time

    def _wait(class_api, task_id: str, timeout: float = 15.0, interval: float = 1.0):
        terminal_statuses = ("completed", "failed")
        deadline = time.monotonic() + timeout
        last_data = None
        while time.monotonic() < deadline:
            resp = class_api.get_task(task_id)
            last_data = assert_response(resp, 200)
            if last_data["status"] in terminal_statuses:
                return last_data
            time.sleep(interval)
        raise TimeoutError(
            f"task {task_id}가 {timeout}s 내에 완료 상태에 도달하지 못함. 마지막 응답: {last_data}"
        )

    return _wait