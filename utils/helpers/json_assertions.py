# utils/helpers/json_assertions.py
import logging
from typing import Any

from .base import _MISSING, _fail, _get_nested_value

logger = logging.getLogger(__name__)


def assert_key_exists(data: dict[str, Any] | list[Any], path: str) -> None:
    """
    JSON 데이터 내에 특정 키 경로(Key Path)가 존재하는지 검증합니다.
    
    Args:
        data (dict[str, Any] | list[Any]): 탐색할 원본 JSON 데이터
        path (str): 점(.) 또는 대괄호([]) 표기법이 포함된 키 경로 (예: 'users[0].id')
        
    Raises:
        AssertionFailure: 키 경로가 JSON 데이터 내에 존재하지 않을 경우 발생
    """
    value = _get_nested_value(data, path)
    if value is _MISSING:
        _fail(f"JSON 키 누락! [Path]: '{path}'가 응답 데이터에 존재하지 않습니다.")
        
    logger.debug(f"JSON 키 존재 확인: '{path}'")


def assert_json_value(data: dict[str, Any] | list[Any], path: str, expected_value: Any) -> None:
    """
    JSON 데이터 내의 특정 키 경로의 값이 예상하는 값과 일치하는지 검증합니다.
    
    Args:
        data (dict[str, Any] | list[Any]): 탐색할 원본 JSON 데이터
        path (str): 점(.) 또는 대괄호([]) 표기법이 포함된 키 경로 (예: 'user.role')
        expected_value (Any): 기대하는 상괏값
        
    Raises:
        AssertionFailure: 키가 없거나, 실제 값이 예상 값과 다를 경우 발생
    """
    actual_value = _get_nested_value(data, path)
    
    # 1. 키 자체가 존재하는지 먼저 방어
    if actual_value is _MISSING:
        _fail(f"JSON 키 누락으로 값 비교 불가! [Path]: '{path}'가 존재하지 않습니다.")
        
    # 2. 값의 동등성 비교
    if actual_value != expected_value:
        _fail(
            f"JSON 값 불일치! [Path]: '{path}'\n"
            f"[Expected]: '{expected_value}' (type: {type(expected_value).__name__})\n"
            f"[Actual]: '{actual_value}' (type: {type(actual_value).__name__})"
        )
        
    logger.debug(f"JSON 값 일치 확인: '{path}' == '{expected_value}'")