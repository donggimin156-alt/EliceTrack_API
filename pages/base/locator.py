# pages/base/locator.py
from typing import TypeAlias

# 로케이터 타입 별칭: (By 전략, 선택자 문자열)
Locator: TypeAlias = tuple[str, str]

def format_locator(locator: Locator) -> str:
    """로케이터를 로깅하기 쉬운 문자열 포맷으로 변환합니다."""
    return f"{locator[0]}='{locator[1]}'"