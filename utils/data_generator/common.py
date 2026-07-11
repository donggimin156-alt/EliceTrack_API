# utils/data_generator/common.py
import uuid

from utils.data_generator.faker_manager import get_faker


def generate_random_string(min_chars: int = 1, max_chars: int = 50, locale: str = "en_US") -> str:
    """
    UI 입력 폼 검증 등에 사용할 무작위 텍스트를 생성합니다.
    특수 공백이나 줄바꿈을 제외한 안전한 문자열(pystr)만을 생성합니다.
    """
    fake = get_faker(locale)
    return fake.pystr(min_chars=min_chars, max_chars=max_chars)


def generate_uuid() -> str:
    """
    API 멱등성 키나 고유 식별자로 자주 사용되는 UUID4 표준 문자열 포맷을 반환합니다.
    (예: 550e8400-e29b-41d4-a716-446655440000)
    """
    return str(uuid.uuid4())