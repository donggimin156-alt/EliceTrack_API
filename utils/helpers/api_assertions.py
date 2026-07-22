# utils/helpers/api_assertions.py
import json
import logging
from functools import lru_cache
from typing import Any, Iterable

import jsonschema
from jsonschema import Draft202012Validator
from requests import Response

from .base import AssertionFailure, _fail, _format_json

logger = logging.getLogger(__name__)


@lru_cache(maxsize=256)
def _get_compiled_validator(schema_str: str) -> Draft202012Validator:
    """
    JSON 문자열 형태의 스키마를 파싱하여 검증기(Validator) 객체를 생성하고 캐싱합니다.
    (반복적인 스키마 파싱에 따른 오버헤드 방지)
    """
    schema = json.loads(schema_str)
    return Draft202012Validator(schema)


def assert_status_code(
    response: Response, 
    expected_codes: int | Iterable[int], 
    message: str | None = None
) -> None:
    """
    API 응답 상태 코드를 검증합니다.
    
    Args:
        response (Response): API 통신 결과 응답 객체
        expected_codes (int | Iterable[int]): 기대하는 단일 상태 코드 또는 상태 코드들의 집합(List, Set)
        message (str | None): 실패 시 출력할 커스텀 에러 메시지
        
    Raises:
        AssertionFailure: 상태 코드가 예상값과 다를 경우 발생
    """
    actual_code = response.status_code
    
    if isinstance(expected_codes, int):
        expected_codes = {expected_codes}
    else:
        expected_codes = set(expected_codes)
        
    if actual_code not in expected_codes:
        error_msg = message or (
            f"상태 코드 불일치! [Expected]: {expected_codes} 중 하나 | [Actual]: {actual_code}\n"
            f"[Method]: {response.request.method} | [URL]: {response.url}\n"
            f"[Elapsed]: {response.elapsed.total_seconds()}s\n"
            f"[Response Body]: {response.text[:500]}"
        )
        _fail(error_msg)
        
    logger.debug(f"상태 코드 {actual_code} 정상 확인")


def _assert_board_status(response: Response, expected: str) -> dict[str, Any]:
    """게시판 응답의 HTTP 200 + `_result.status` 를 검증하고 파싱된 body 를 반환합니다.

    게시판 API는 권한/파라미터 오류 같은 비즈니스 실패도 HTTP 200으로 응답하므로
    `_result.status` 까지 봐야 하고, 반대로 405 같은 HTTP 레벨 오류는 200이 아니므로
    status_code 검사도 필요합니다. 그래서 두 층을 함께 확인합니다.

    assert_board_ok / assert_board_fail 의 공통 부분이며, 기대값(expected)만 다릅니다.

    Args:
        response (Response): 게시판 API 응답 객체.
        expected (str): 기대하는 `_result.status` 값 ("ok" 또는 "fail").

    Returns:
        dict[str, Any]: 파싱된 응답 body.

    Raises:
        AssertionFailure: HTTP 200이 아니거나 `_result.status` 가 expected 와 다른 경우.
    """
    assert_status_code(response, 200)
    body = response.json()
    status = body.get("_result", {}).get("status")
    if status != expected:
        _fail(
            f"게시판 응답 _result.status 불일치! [Expected]: {expected} | [Actual]: {status}\n"
            f"[Method]: {response.request.method} | [URL]: {response.url}\n"
            f"[Response Body]:\n{_format_json(body)}"
        )
    return body


def assert_board_ok(response: Response) -> dict[str, Any]:
    """Elice 게시판 응답의 성공을 검증하고, 파싱된 body(dict)를 반환합니다.

    HTTP status_code == 200 과 body `_result.status` == "ok" 를 함께 확인합니다.

    Args:
        response (Response): 게시판 API 응답 객체

    Returns:
        dict[str, Any]: 파싱된 응답 body (후속 검증에서 재사용).

    Raises:
        AssertionFailure: HTTP 200이 아니거나 `_result.status`가 "ok"가 아닌 경우.
    """
    body = _assert_board_status(response, "ok")
    logger.debug("게시판 응답 _result.status == 'ok' 정상 확인")
    return body


def assert_board_fail(
    response: Response,
    fail_code: str | None = None,
    status_code: int | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Elice 게시판 응답의 실패(fail)를 검증하고, 파싱된 body(dict)를 반환합니다.

    HTTP는 200이지만 `_result.status`가 "fail"인 케이스(권한/파라미터/로직 오류 등)를
    검증합니다. fail_code / _result.status_code / _result.reason 을 선택적으로 대조합니다.

    Args:
        response (Response): 게시판 API 응답 객체.
        fail_code (str | None): 기대하는 최상위 fail_code (예: "invalid_parameter").
        status_code (int | None): 기대하는 _result.status_code (예: 400, 409).
        reason (str | None): 기대하는 _result.reason (예: "param", "logic").

    Returns:
        dict[str, Any]: 파싱된 응답 body.

    Raises:
        AssertionFailure: HTTP 200이 아니거나 fail 판정/대조값이 어긋난 경우.
    """
    body = _assert_board_status(response, "fail")
    result = body.get("_result", {})

    mismatches = []
    if fail_code is not None and body.get("fail_code") != fail_code:
        mismatches.append(f"fail_code [Expected]: {fail_code} | [Actual]: {body.get('fail_code')}")
    if status_code is not None and result.get("status_code") != status_code:
        mismatches.append(f"_result.status_code [Expected]: {status_code} | [Actual]: {result.get('status_code')}")
    if reason is not None and result.get("reason") != reason:
        mismatches.append(f"_result.reason [Expected]: {reason} | [Actual]: {result.get('reason')}")
    if mismatches:
        _fail("게시판 실패 응답 대조 불일치:\n - " + "\n - ".join(mismatches)
              + f"\n[Method]: {response.request.method} | [URL]: {response.url}"
              + f"\n[Response Body]:\n{_format_json(body)}")

    logger.debug("게시판 응답 실패(fail) 및 대조값 정상 확인")
    return body


def assert_200(response: Response) -> None:
    """HTTP 200 검증 헬퍼."""
    assert_status_code(response, 200)


def assert_valid_schema(response_json: dict[str, Any], schema: dict[str, Any]) -> None:
    """
    JSON Schema를 기반으로 API 응답의 전체적인 구조와 데이터 타입을 검증합니다.
    
    Args:
        response_json (dict[str, Any]): 검증할 API JSON 응답 페이로드
        schema (dict[str, Any]): 기준이 되는 JSON Schema 딕셔너리
        
    Raises:
        AssertionFailure: 응답 데이터가 스키마 구조와 일치하지 않는 경우
    """
    # 딕셔너리를 일관된 문자열로 직렬화하여 캐시 키로 사용
    schema_str = json.dumps(schema, sort_keys=True)
    
    try:
        validator = _get_compiled_validator(schema_str)
        # 여러 에러가 있을 경우 경로(path) 기준으로 정렬하여 파악하기 쉽게 만듦
        errors = sorted(validator.iter_errors(response_json), key=lambda e: str(e.path))
        
        if errors:
            error_details = []
            for error in errors:
                path = ".".join([str(p) for p in error.path]) if error.path else "root"
                error_details.append(f" - [{path}]: {error.message}")
            
            error_msg = f"JSON Schema 검증 실패 (총 {len(errors)}건):\n" + "\n".join(error_details)
            
            # 직접 로깅 후 raise하던 방식을 공통 헬퍼인 _fail()을 활용하도록 통합
            _fail(f"{error_msg}\n[Response Body]:\n{_format_json(response_json)}")
            
        logger.debug("JSON Schema 구조 및 타입 완벽 일치")
        
    except jsonschema.exceptions.SchemaError as e:
        _fail(f"JSON Schema 자체 문법(정의) 에러!\n[원인]: {e.message}")