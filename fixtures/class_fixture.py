# fixtures/class_fixture.py
"""Classroom Course API 전용 픽스처."""

import logging

import pytest
import requests

from api.endpoints.class_api import ClassApi
from api.schemas.class_schema import ClassSchemas
from core.config import settings
from api.utils.elice_auth import get_env_config, make_authenticated_session
from utils.helpers.api_assertions import assert_valid_schema
from utils.helpers.class_helper import (
    MAX_PAGE_SIZE,
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


def _fetch_course_ids(class_api: ClassApi, assert_response) -> set[int]:
    """현재 강의실에 배정된 course_id 전체 집합을 조회한다.

    count를 고정값(MAX_PAGE_SIZE)으로 두면 실제 과목 수가 그보다 많을 때 응답이
    잘려서(capped) diff가 항상 빈 값으로 나오는 문제가 있었다. 그래서 먼저
    /course/count로 전체 개수를 조회한 뒤, 그 값으로 목록을 요청해 전량을 받는다.
    (/course/count는 정수 하나를 그대로 반환한다.)
    """
    count_resp = class_api.get_course_count()
    total = assert_response(count_resp, 200)

    resp = class_api.get_course_list(skip=0, count=total)
    data = assert_response(resp, 200)
    return {course["course_id"] for course in data}


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
def track_bulk_added_courses(educator_class_api, assert_response):
    """bulk add로 강의실에 새로 생성된 course_id를 테스트 종료 후 자동 삭제(teardown)한다.

    ⚠️ 설계 노트:
    add_courses_bulk에 넘기는 original_course_ids(예: 17)는 "어떤 과목 템플릿을
    배정할지"를 가리키는 입력값일 뿐, 실제로 이 강의실에 생성되는 course_id
    (예: 288, 317...)와는 전혀 다른 값이다. 과거에 original_course_ids 자체를
    추적/삭제 대상으로 삼았다가, 존재 확인이 영원히 실패(409 model_not_found)하고
    진짜 생성된 리소스는 추적조차 안 돼 강의실에 orphan으로 계속 쌓이는 사고가
    있었다 (동일한 이름의 과목이 course_id만 다른 채 여러 개 누적됨).

    그래서 course_id 자체가 아니라 "bulk add 호출 직전의 course_id 스냅샷(set)"을
    등록받는다. teardown 시점에 현재 course_id 목록과 diff를 떠서 새로 생긴
    course_id들을 찾아내고, 그것들을 실제 삭제 대상으로 삼는다.
    """
    pre_add_snapshots: list[set[int]] = []
    yield pre_add_snapshots

    for before_ids in reversed(pre_add_snapshots):
        after_ids = _fetch_course_ids(educator_class_api, assert_response)
        new_course_ids = after_ids - before_ids
        for course_id in new_course_ids:
            cleanup_resource_if_exists(
                exists_check_fn=lambda cid=course_id: educator_class_api.get_course(cid).status_code == 200,
                delete_fn=lambda cid=course_id: educator_class_api.delete_course(cid),
                resource_label=f"course_id={course_id}",
            )


@pytest.fixture
def bulk_add_task_id(educator_class_api, assert_response, track_bulk_added_courses):
    """course_ids 리스트로 bulk add를 요청하고 task_id를 반환하는 팩토리 픽스처.

    호출 직전의 course_id 스냅샷을 track_bulk_added_courses에 등록해서, task 성공
    여부나 완료 시점과 무관하게 teardown에서 diff 기반으로 새로 생긴 리소스를
    정리할 수 있게 한다.

    사용: task_id = bulk_add_task_id([course_id, ...])
    """

    def _create(original_course_ids: list[int]) -> str:
        before_ids = _fetch_course_ids(educator_class_api, assert_response)

        resp = educator_class_api.add_courses_bulk(original_course_ids)
        data = assert_response(resp, 200)
        assert set(data.keys()) == {"task_id"}, f"Expected only 'task_id' key but got {data.keys()}"
        assert isinstance(data["task_id"], str) and data["task_id"], (
            f"Expected non-empty str task_id but got {data['task_id']!r}"
        )

        track_bulk_added_courses.append(before_ids)
        return data["task_id"]

    return _create


@pytest.fixture
def completed_bulk_add_task(educator_class_api, assert_response, bulk_add_task_id):
    """단일 과목 템플릿(BULK_ADD_COURSE_ID) bulk add 요청 후 completed 상태까지 대기하고,
    실제로 새로 생성된 course_id까지 diff로 찾아낸 (task_id, task 응답, added_course_id) 튜플.

    ⚠️ original_course_ids로 넘기는 값(BULK_ADD_COURSE_ID)과 실제 생성되는 course_id는
    다른 값이므로, 호출 직전 스냅샷과 완료 직후 스냅샷을 비교해 새로 생긴 course_id를
    특정한다. 이 fixture를 쓰는 테스트는 반환된 added_course_id를 사용해야 한다
    (BULK_ADD_COURSE_ID로 조회/검증하면 항상 실패한다).
    """
    before_ids = _fetch_course_ids(educator_class_api, assert_response)

    task_id = bulk_add_task_id([BULK_ADD_COURSE_ID])
    final = wait_until_task_completed(educator_class_api, task_id)
    assert_valid_schema(final, ClassSchemas.TASK_SCHEMA)
    assert_task_completed(final, expected_result=BULK_ADD_EXPECTED_RESULT)

    after_ids = _fetch_course_ids(educator_class_api, assert_response)
    new_course_ids = after_ids - before_ids
    assert len(new_course_ids) == 1, (
        f"Expected exactly 1 newly created course_id but found {new_course_ids} "
        f"(before={len(before_ids)}, after={len(after_ids)})"
    )
    added_course_id = new_course_ids.pop()

    return task_id, final, added_course_id