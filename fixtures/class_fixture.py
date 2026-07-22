# fixtures/class_fixture_v2.py
"""Classroom Course API 전용 픽스처 — v2 리팩토링 버전."""

import logging

import pytest
import requests

from api.endpoints.class_api import ClassApi
from api.schemas.class_schema import ClassSchemas
from core.config import settings
from api.utils.elice_auth import get_env_config, make_authenticated_session
from utils.helpers.api_assertions import assert_valid_schema
from utils.helpers.class_helper import (
    assert_task_completed,
    cleanup_resource_if_exists,
    wait_until_task_completed,
)

logger = logging.getLogger(__name__)

ENV_NAME = "prod"
BULK_ADD_COURSE_ID = settings.elice_environments["dev"]["BULK_ADD_COURSE_ID"]
BULK_ADD_EXPECTED_RESULT = {"course_attached": "completed"}

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

@pytest.fixture
def track_bulk_added_courses(educator_class_api):
    """bulk add로 강의실에 추가된 course_id를 테스트 종료 후 자동 삭제(teardown)한다.
 
    board_fixture.py의 track_articles와 동일한 패턴(등록 -> yield -> 역순 정리)에
    "삭제 전 존재 확인"만 helper.cleanup_resource_if_exists로 추가한 버전이다.
    """
    added: list[int] = []
    yield added
    for course_id in reversed(added):
        cleanup_resource_if_exists(
            exists_check_fn=lambda cid=course_id: educator_class_api.get_course(cid).status_code == 200,
            delete_fn=lambda cid=course_id: educator_class_api.delete_course(cid),
            resource_label=f"course_id={course_id}",
        )
 
 
@pytest.fixture
def bulk_add_task_id(educator_class_api, assert_response, track_bulk_added_courses):
    """course_ids 리스트로 bulk add를 요청하고 task_id를 반환하는 팩토리 픽스처.
 
    요청에 사용한 course_id들은 (task 성공 여부와 무관하게) track_bulk_added_courses에
    등록된다. 실제 정리 시점에는 존재 여부를 확인한 뒤에만 삭제하므로, task가 아직
    끝나지 않은 상태로 테스트가 종료돼도 안전하다.
 
    사용: task_id = bulk_add_task_id([course_id, ...])
    """
 
    def _create(course_ids: list[int]) -> str:
        resp = educator_class_api.add_courses_bulk(course_ids)
        data = assert_response(resp, 200)
        assert set(data.keys()) == {"task_id"}, f"Expected only 'task_id' key but got {data.keys()}"
        assert isinstance(data["task_id"], str) and data["task_id"], (
            f"Expected non-empty str task_id but got {data['task_id']!r}"
        )
        track_bulk_added_courses.extend(course_ids)
        return data["task_id"]
 
    return _create
 
 
@pytest.fixture
def completed_bulk_add_task(educator_class_api, bulk_add_task_id):
    """단일 과목(BULK_ADD_COURSE_ID) bulk add 요청 후 completed 상태까지 대기한
    (task_id, 최종 task 응답) 튜플.
 
    여러 테스트에서 반복되는 '제출 -> 완료 대기 -> schema/status 검증' 흐름을
    한 곳에 캡슐화한다. 이 픽스처를 쓰는 테스트는 완료를 이미 확인했으므로
    teardown에서 존재 확인이 즉시 통과해 추가 대기 없이 바로 정리된다.
    """
    task_id = bulk_add_task_id([BULK_ADD_COURSE_ID])
    final = wait_until_task_completed(educator_class_api, task_id)
    assert_valid_schema(final, ClassSchemas.TASK_SCHEMA)
    assert_task_completed(final, expected_result=BULK_ADD_EXPECTED_RESULT)
    return task_id, final
 