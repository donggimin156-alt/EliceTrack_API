"""
helper.py

여러 테스트 모듈에서 공통으로 쓰는 헬퍼 함수 모음.

설계 원칙
- HTTP 통신/세션 관리는 담당하지 않는다. (그건 api/base_client.py, conftest.py의 몫)
- JSON Schema 검증처럼 이미 utils/assertions/ 쪽에 있는 공용 함수는 새로 만들지 않고
  그대로 재사용한다 (assert_valid_schema -> assert_schema로 alias만 노출).
- 여기서 새로 추가하는 함수(assert_detail_error, assert_model_not_found_error,
  wait_until 계열)는 utils/assertions/base.py의 `_fail()` / `_format_json()`을 그대로 활용해서
  실패 로깅 방식과 예외 타입(AssertionFailure)을 프로젝트 전체와 통일시킨다.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Iterable, final

from .api_assertions import assert_valid_schema
from .base import AssertionFailure, _fail, _format_json

logger = logging.getLogger(__name__)

# 리뷰 #2: validate(instance=..., schema=...)를 테스트 코드에서 반복 호출하지 않도록
# 기존 공용 함수를 도메인 친화적인 이름으로 재노출한다. (새로 만들지 않고 재사용)


# ==========================================
# 1. 상수 (리뷰 #3, #11: Magic Number 제거)
# ==========================================
DEFAULT_PAGE_SIZE = 10
# API의 실제 max count 제약에 맞춰서 조정할 것. 9999처럼 임의의 큰 값은 스펙이 바뀌면 깨진다.
MAX_PAGE_SIZE = 100
TASK_POLL_MAX_RETRY = 15
TASK_POLL_INTERVAL_SEC = 2.0

# teardown에서 "삭제하기 전에 실제로 존재하는지" 짧게 확인할 때 쓰는 기본값.
# 이미 완료를 확인한 리소스는 1차 시도에서 바로 통과하므로 추가 지연이 없다.
CLEANUP_EXISTENCE_CHECK_MAX_RETRY = 5
CLEANUP_EXISTENCE_CHECK_INTERVAL_SEC = 1.0


# ==========================================
# 2. Enum (리뷰 #8: 문자열 비교 대신 Enum 사용)
# ==========================================
class TaskStatus(str, Enum):
    """비동기 Task 상태값. str Enum이라 API가 내려주는 순수 문자열과 직접 비교/해시가 가능하다."""

    QUEUED = "queued"
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    FAILED = "failed"


_TASK_IN_PROGRESS_STATUSES = {TaskStatus.QUEUED, TaskStatus.ASSIGNED}


# ==========================================
# 3. datetime 파싱
# ==========================================
def parse_iso_datetime(value: str | None) -> datetime:
    """ISO 8601 문자열을 datetime으로 파싱한다. Z 접미사와 빈 값도 안전하게 처리한다."""
    if not value:
        _fail("datetime 값이 비어 있습니다.")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# ==========================================
# 4. detail / 공통 에러 바디 검증 (리뷰 #10: 메시지 포맷 통일)
# ==========================================
def assert_detail_error(
    data: dict[str, Any],
    expected_type: str,
    expected_loc: list[str],
    ctx_key: str | None = None,
    ctx_value: Any = None,
) -> None:
    """FastAPI 스타일 422 응답의 detail 배열 안에서
    조건에 맞는 에러 항목이 정확히 1개인지 검증한다."""
    detail = data.get("detail", [])
    matches = [
        d for d in detail
        if d.get("type") == expected_type and d.get("loc") == expected_loc
    ]
    if len(matches) != 1:
        _fail(
            f"Expected exactly 1 error matching type={expected_type!r}, "
            f"loc={expected_loc} but found {len(matches)}.\n"
            f"[detail]:\n{_format_json(detail)}"
        )

    match = matches[0]
    if ctx_key is not None:
        ctx = match.get("ctx", {})
        if ctx_key not in ctx:
            _fail(f"Expected ctx to contain key {ctx_key!r} but got {match}")
        if ctx[ctx_key] != ctx_value:
            _fail(f"Expected ctx[{ctx_key}]={ctx_value!r} but got {ctx[ctx_key]!r}")


def assert_model_not_found_error(data: dict[str, Any], model_name: str | None = None) -> None:
    """{code: model_not_found, detail: {...}} 형태로 내려오는 공통 에러 바디를 검증한다.
    (dev/prod 여러 엔드포인트에서 반복되는 409 model_not_found 패턴을 재사용하기 위함)
    """
    if data.get("code") != "model_not_found":
        _fail(
            f"Expected code='model_not_found' but got {data.get('code')!r}.\n"
            f"[body]:\n{_format_json(data)}"
        )
    if model_name is not None and model_name not in data.get("detail", {}):
        _fail(
            f"Expected detail to contain key {model_name!r} but got "
            f"{data.get('detail')!r}"
        )


# ==========================================
# 5. 범용 polling (리뷰 #6, #7, #13: private method 대신 재사용 가능한 헬퍼로 분리)
# ==========================================
def poll_until(
    condition_fn: Callable[[], Any],
    max_retry: int = TASK_POLL_MAX_RETRY,
    interval_sec: float = TASK_POLL_INTERVAL_SEC,
) -> Any:
    """condition_fn()이 truthy가 될 때까지 polling한다.

    wait_until()과 달리 "제한 시간 안에 충족되지 않는 것도 정상적인 결과일 수 있는"
    상황을 위한 함수다. 타임아웃 시 에러 로그를 남기거나 예외를 던지지 않고
    falsy 값을 그대로 반환한다. (예: 리소스가 아직 생성 안 됐을 수도 있는 존재 확인)
    """
    result = None
    for _ in range(max_retry):
        result = condition_fn()
        if result:
            return result
        time.sleep(interval_sec)
    return result


def wait_until(
    condition_fn: Callable[[], Any],
    max_retry: int = TASK_POLL_MAX_RETRY,
    interval_sec: float = TASK_POLL_INTERVAL_SEC,
    timeout_message: str = "조건이 제한 시간 내에 충족되지 않았습니다.",
) -> Any:
    """condition_fn()이 truthy 값을 반환할 때까지 polling한다.

    "제한 시간 안에 반드시 참이 돼야 하는" assertion 성격의 대기에 사용한다.
    (예: 제출한 task는 언젠가 반드시 completed/failed 상태가 돼야 한다)
    max_retry 안에 조건이 충족되지 않으면 AssertionFailure를 발생시킨다.
    "안 돼도 정상"인 상황(존재 확인 후 스킵 등)에는 poll_until()을 사용할 것.
    """
    result = poll_until(condition_fn, max_retry=max_retry, interval_sec=interval_sec)
    if not result:
        _fail(timeout_message)
    return result


def wait_until_task_completed(
    api_client: Any,
    task_id: str,
    max_retry: int = TASK_POLL_MAX_RETRY,
    interval_sec: float = TASK_POLL_INTERVAL_SEC,
) -> dict[str, Any]:
    """task_id의 상태가 QUEUED/ASSIGNED를 벗어날 때까지 polling한 뒤
    최종(completed/failed 등) task 응답을 반환한다."""

    def _poll() -> dict[str, Any] | None:
        resp = api_client.get_task(task_id)
        data = resp.json()
        if data.get("status") in _TASK_IN_PROGRESS_STATUSES:
            return None
        return data

    return wait_until(
        _poll,
        max_retry=max_retry,
        interval_sec=interval_sec,
        timeout_message=f"task_id={task_id}가 제한 시간 내에 완료 상태에 도달하지 못했습니다.",
    )


def assert_task_completed(
    task_data: dict[str, Any], expected_result: dict[str, Any] | None = None
) -> None:
    """Task 응답이 completed 상태인지 (그리고 필요 시 result까지) 검증한다.
    (assert만 하는 함수라 wait_until_task_completed와 이름/역할을 분리했다 — 리뷰 #5)
    """
    if task_data.get("status") != TaskStatus.COMPLETED:
        _fail(
            f"Expected task status={TaskStatus.COMPLETED!r} but got "
            f"{task_data.get('status')!r}.\n[task]:\n{_format_json(task_data)}"
        )
    if expected_result is not None and task_data.get("result") != expected_result:
        _fail(
            f"Expected task result={expected_result} but got {task_data.get('result')}"
        )
    logger.info("DEBUG final=%s", final)


def wait_until_item_in_list(
    fetch_list_fn: Callable[[], Iterable[dict[str, Any]]],
    match_key: str,
    match_value: Any,
    max_retry: int = TASK_POLL_MAX_RETRY,
    interval_sec: float = TASK_POLL_INTERVAL_SEC,
) -> list[dict[str, Any]]:
    """fetch_list_fn()이 반환하는 리스트 안에 match_key==match_value인 항목이
    나타날 때까지 polling한다. (예: bulk add 후 course_list 반영을 기다릴 때)
    다른 목록형 Task(예: UserAPI 쪽 bulk 작업)에도 그대로 재사용 가능하다.
    """

    def _poll() -> list[dict[str, Any]] | None:
        items = list(fetch_list_fn())
        if any(item.get(match_key) == match_value for item in items):
            return items
        return None

    return wait_until(
        _poll,
        max_retry=max_retry,
        interval_sec=interval_sec,
        timeout_message=(
            f"{match_key}={match_value}가 제한 시간 내에 목록에 반영되지 않았습니다."
        ),
    )

def wait_until_item_not_in_list(
    fetch_list_fn: Callable[[], Iterable[dict[str, Any]]],
    match_key: str,
    match_value: Any,
    max_retry: int = TASK_POLL_MAX_RETRY,
    interval_sec: float = TASK_POLL_INTERVAL_SEC,
) -> list[dict[str, Any]]:
    """fetch_list_fn()이 반환하는 리스트 안에서 match_key==match_value인 항목이
    사라질 때까지 polling한다. (예: 삭제 후 course_list에서 실제로 빠졌는지 확인할 때)
    wait_until_item_in_list와 대칭되는 함수 — 삭제 검증에도 재사용 가능하다.
    """

    def _poll() -> list[dict[str, Any]] | None:
        items = list(fetch_list_fn())
        if any(item.get(match_key) == match_value for item in items):
            return None
        return items

    return wait_until(
        _poll,
        max_retry=max_retry,
        interval_sec=interval_sec,
        timeout_message=(
            f"{match_key}={match_value}가 제한 시간 내에 목록에서 제거되지 않았습니다."
        ),
    )

# ==========================================
# 6. 비동기 생성 리소스에 대한 teardown 정리
# ==========================================
def cleanup_resource_if_exists(
    exists_check_fn: Callable[[], bool],
    delete_fn: Callable[[], Any],
    resource_label: str,
    max_retry: int = CLEANUP_EXISTENCE_CHECK_MAX_RETRY,
    interval_sec: float = CLEANUP_EXISTENCE_CHECK_INTERVAL_SEC,
) -> None:
    """..."""  # docstring 그대로
    exists = poll_until(
        exists_check_fn,
        max_retry=max_retry,
        interval_sec=interval_sec,
    )

    if not exists:
        logger.info(
            "%s가 정리 시점까지 반영되지 않아 삭제를 건너뜁니다 "
            "(비동기 작업 미완료 또는 실패로 애초에 생성되지 않았을 수 있음).",
            resource_label,
        )
        return

    try:
        delete_fn()
    except Exception as e:
        logger.warning("%s 정리 실패: %s", resource_label, e)


def assert_progress_in_range(progress) -> float:
    """learning_progress 값(문자열로 내려옴, 예: "5.26")이 0~100 범위의 숫자인지 검증하고
    float으로 변환한 값을 반환한다.
    """
    value = float(progress)
    assert 0 <= value <= 100, f"Expected 0<=progress<=100 but got {value}"
    return value

def extract_course_ids(courses: list[dict]) -> list[int]:
    """과목 목록 응답에서 course_id만 추출한다."""
    return [course["course_id"] for course in courses]