# utils/assertions/api_assertions.py
import json
import logging
from functools import lru_cache
from typing import Any, Iterable

import jsonschema
from jsonschema import Draft202012Validator
from requests import Response

from utils.assertions.base import AssertionFailure, _fail, _format_json

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