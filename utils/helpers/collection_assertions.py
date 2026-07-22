# utils/helpers/collection_assertions.py
import logging
from typing import Any, Iterable, Sized

from utils.helpers.base import _fail

logger = logging.getLogger(__name__)


def assert_empty(collection: Sized, item_name: str = "컬렉션") -> None:
    """
    컬렉션(리스트, 딕셔너리, 세트, 문자열 등)이 비어있는지 검증합니다.
    
    Args:
        collection (Sized): 길이를 측정할 수 있는 데이터 컬렉션
        item_name (str): 실패 메시지에 출력할 항목의 이름 (기본값: "컬렉션")
        
    Raises:
        AssertionFailure: 컬렉션의 길이가 0보다 클 경우 발생
    """
    if len(collection) > 0:
        _fail(f"{item_name}이(가) 비어있지 않습니다! [Actual Size]: {len(collection)}")
        
    logger.debug(f"{item_name}이(가) 정상적으로 비어있음 확인")


def assert_list_length(actual_list: Sized, expected_length: int, list_name: str = "리스트") -> None:
    """
    리스트를 비롯한 크기 측정이 가능한 객체(Sized)의 길이가 예상과 일치하는지 검증합니다.
    
    Args:
        actual_list (Sized): 길이를 측정할 대상 데이터 (리스트, 튜플 등)
        expected_length (int): 기대하는 정확한 길이 값
        list_name (str): 실패 메시지에 출력할 데이터의 이름 (기본값: "리스트")
        
    Raises:
        AssertionFailure: 실제 길이가 기대하는 길이와 다를 경우 발생
    """
    actual_length = len(actual_list)
    if actual_length != expected_length:
        _fail(f"{list_name} 길이 불일치! [Expected]: {expected_length} | [Actual]: {actual_length}")
        
    logger.debug(f"{list_name} 길이({expected_length}) 일치 확인")


def assert_contains(substring_or_item: Any, target: Iterable | Sized, item_name: str = "항목") -> None:
    """
    문자열이나 컬렉션 내에 특정 값(Substring 또는 Item)이 포함되어 있는지 검증합니다.
    
    Args:
        substring_or_item (Any): 대상 내에 존재하는지 찾을 특정 값
        target (Iterable | Sized): 검색의 대상이 되는 전체 문자열 또는 컬렉션 객체
        item_name (str): 실패 메시지에 출력할 항목의 이름 (기본값: "항목")
        
    Raises:
        AssertionFailure: 대상 객체 내에 찾는 값이 존재하지 않을 경우 발생
    """
    # in 연산자를 지원하는(Iterable) 객체인지 확인하고 값을 찾습니다. (Type Checker 경고 무시 처리)
    if substring_or_item not in target:  # type: ignore
        target_repr = repr(target)
        
        # 로그나 에러 메시지가 너무 길어 콘솔에 도배되는 것을 방지하기 위해 Truncate 처리
        if len(target_repr) > 300:
            target_repr = target_repr[:300] + " ... [TRUNCATED]"
            
        _fail(f"{item_name} 포함 실패! 찾는 값: '{substring_or_item}' | 대상: '{target_repr}'")
        
    logger.debug(f"대상 내 '{substring_or_item}' 포함 확인")