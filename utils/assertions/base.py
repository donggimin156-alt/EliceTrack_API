# utils/assertions/base.py
import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# 키 누락(Missing)과 실제 값(None)을 엄격히 구분하기 위한 Sentinel 객체
_MISSING = object()


class AssertionFailure(AssertionError):
    """
    엔터프라이즈 환경에서 Assertion 실패 시 상세한 Context를 담기 위한 커스텀 예외 클래스.
    기본 AssertionError 대신 이 클래스를 발생시켜 프레임워크 레벨의 예외 처리와 구분합니다.
    """
    pass


def _fail(message: str) -> None:
    """
    공통 실패 처리 헬퍼 함수.
    
    실패 메시지를 에러 로그로 먼저 남긴 후, AssertionFailure를 발생시켜 
    중복 로깅을 제거하고 일관된 실패 흐름을 보장합니다.
    
    Args:
        message (str): 출력하고 발생시킬 에러 메시지
        
    Raises:
        AssertionFailure: 항상 발생함
    """
    logger.error(message)
    raise AssertionFailure(message)


def _format_json(data: dict[str, Any] | list[Any]) -> str:
    """
    JSON 데이터를 보기 좋게 포맷팅(Pretty Print)합니다.
    
    에러 발생 시 로그에 원본 데이터를 출력할 때 가독성을 높이기 위해 사용됩니다.
    
    Args:
        data (dict[str, Any] | list[Any]): 포맷팅할 JSON 객체 또는 배열
        
    Returns:
        str: 들여쓰기(indent=2)가 적용된 JSON 문자열
    """
    return json.dumps(data, indent=2, ensure_ascii=False)


def _get_nested_value(data: dict[str, Any] | list[Any], path: str) -> Any:
    """
    'data.user.id' 또는 'data.users[0].name' 형태의 경로를 파싱하여 
    중첩된 JSON 값을 안전하게 반환합니다.
    
    Args:
        data (dict[str, Any] | list[Any]): 탐색할 원본 JSON 데이터
        path (str): 점(.) 또는 대괄호([]) 표기법이 포함된 키 경로
        
    Returns:
        Any: 경로에 해당하는 값. 키가 존재하지 않으면 _MISSING 객체를 반환합니다.
    """
    # 'users[0]' 같은 배열 인덱스를 'users.0' 형태로 정규화하여 딕셔너리와 리스트 탐색 로직을 통일합니다.
    normalized_path = re.sub(r'\[(\d+)\]', r'.\1', path)
    keys = normalized_path.split('.')
    
    val: Any = data
    for key in keys:
        if not key:
            continue
            
        if isinstance(val, dict):
            if key in val:
                val = val[key]
            else:
                return _MISSING
                
        elif isinstance(val, list) and key.isdigit():
            idx = int(key)
            if 0 <= idx < len(val):
                val = val[idx]
            else:
                return _MISSING
                
        else:
            # 딕셔너리나 리스트가 아닌데 더 깊이 탐색하려고 하는 경우
            return _MISSING
            
    return val