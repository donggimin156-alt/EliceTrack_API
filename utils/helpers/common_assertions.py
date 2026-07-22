# utils/assertions/common_assertions.py
import logging
from typing import Any

from .base import _fail

logger = logging.getLogger(__name__)


def assert_equal(actual: Any, expected: Any, item_name: str = "항목") -> None:
    """
    두 값이 동등한지(Equal) 검증합니다.
    
    Args:
        actual (Any): 실제 반환된 결괏값
        expected (Any): 기대하는 상괏값
        item_name (str): 실패 메시지에 출력할 검증 항목의 이름 (기본값: "항목")
        
    Raises:
        AssertionFailure: 두 값이 다를 경우 발생
    """
    if actual != expected:
        _fail(f"{item_name} 불일치! \n[Expected]: '{expected}' (type: {type(expected).__name__})\n[Actual]: '{actual}' (type: {type(actual).__name__})")
        
    logger.debug(f"{item_name} 일치 확인: '{actual}'")


def assert_not_equal(actual: Any, expected: Any, item_name: str = "항목") -> None:
    """
    두 값이 다른지(Not Equal) 검증합니다.
    
    Args:
        actual (Any): 실제 반환된 결괏값
        expected (Any): 기대하지 않는(달라야 하는) 상괏값
        item_name (str): 실패 메시지에 출력할 검증 항목의 이름 (기본값: "항목")
        
    Raises:
        AssertionFailure: 두 값이 같을 경우 발생
    """
    if actual == expected:
        _fail(f"{item_name} 일치 에러 (달라야 함)! [Value]: '{actual}'")
        
    logger.debug(f"{item_name} 불일치(Not Equal) 정상 확인")


def assert_true(condition: bool, message: str) -> None:
    """
    주어진 조건식이 참(True)인지 검증합니다.
    
    Args:
        condition (bool): 검증할 조건식 또는 Bool 값
        message (str): 실패 시 출력할 에러 메시지 (어떤 조건이 실패했는지 명시)
        
    Raises:
        AssertionFailure: 조건이 거짓(False)일 경우 발생
    """
    if not condition:
        _fail(f"조건 불만족(False): {message}")
        
    logger.debug("조건(True) 충족 확인")


def assert_false(condition: bool, message: str) -> None:
    """
    주어진 조건식이 거짓(False)인지 검증합니다.
    
    Args:
        condition (bool): 검증할 조건식 또는 Bool 값
        message (str): 실패 시 출력할 에러 메시지
        
    Raises:
        AssertionFailure: 조건이 참(True)일 경우 발생
    """
    if condition:
        _fail(f"조건 불만족(True): {message}")
        
    logger.debug("조건(False) 충족 확인")


def assert_not_none(actual: Any, item_name: str = "항목") -> None:
    """
    값이 None이 아닌지 검증합니다. (주로 ID 발급 등 필수 데이터 존재 여부 확인용)
    
    Args:
        actual (Any): 검증할 데이터 값
        item_name (str): 실패 메시지에 출력할 검증 항목의 이름 (기본값: "항목")
        
    Raises:
        AssertionFailure: 값이 None일 경우 발생
    """
    if actual is None:
        _fail(f"{item_name}이(가) None입니다! (값이 존재해야 함)")
        
    logger.debug(f"{item_name} 정상 확인 (Not None)")


def assert_is_none(actual: Any, item_name: str = "항목") -> None:
    """
    값이 명확히 None인지 검증합니다.
    
    Args:
        actual (Any): 검증할 데이터 값
        item_name (str): 실패 메시지에 출력할 검증 항목의 이름 (기본값: "항목")
        
    Raises:
        AssertionFailure: 값이 None이 아닐 경우 발생
    """
    if actual is not None:
        _fail(f"{item_name}이(가) None이 아닙니다! [Actual]: '{actual}'")
        
    logger.debug(f"{item_name}이(가) None 임을 확인")