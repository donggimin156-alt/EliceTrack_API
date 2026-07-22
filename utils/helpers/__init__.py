# utils/helpers/__init__.py
import warnings

# 하위 모듈들의 함수들을 __init__.py 레벨로 끌어올려 외부에서 간편하게 import 하도록 지원합니다.
# 권장 사용 예: from utils.helpers import assert_equal, assert_status_code
from utils.helpers.api_assertions import assert_status_code, assert_valid_schema
from utils.helpers.collection_assertions import assert_contains, assert_empty, assert_list_length
from utils.helpers.common_assertions import assert_equal, assert_false, assert_not_none, assert_true
from utils.helpers.json_assertions import assert_json_value, assert_key_exists

__all__ = [
    "assert_status_code",
    "assert_valid_schema",
    "assert_contains",
    "assert_empty",
    "assert_list_length",
    "assert_equal",
    "assert_false",
    "assert_not_none",
    "assert_true",
    "assert_json_value",
    "assert_key_exists",
]

# ==============================================================================
# 기존에 `Assertions.assert_equal()` 형태로 사용하던 테스트 코드들이 
# 단번에 깨지지 않도록 지원하는 래퍼 클래스 (점진적 마이그레이션 용도)
# ==============================================================================
class Assertions:
    """
    [Deprecation Warning]
    기존 객체 지향 방식(Assertions.assert_...)의 호환성을 유지하기 위한 래퍼 클래스입니다.
    새로 작성되는 테스트 코드는 해당 클래스를 사용하지 말고 함수를 직접 import 하여 사용해 주세요.
    추후 모든 테스트 코드가 함수형 호출로 변경되면 이 클래스는 삭제 가능합니다.
    """
    
    def __init__(self) -> None:
        warnings.warn(
            "Assertions 클래스는 곧 Deprecated(제거) 될 예정입니다. "
            "개별 assert 함수(예: assert_equal)를 직접 import 해서 사용해 주세요.",
            DeprecationWarning,
            stacklevel=2
        )

    assert_status_code = staticmethod(assert_status_code)
    assert_valid_schema = staticmethod(assert_valid_schema)
    assert_json_value = staticmethod(assert_json_value)
    assert_key_exists = staticmethod(assert_key_exists)
    assert_equal = staticmethod(assert_equal)
    assert_not_none = staticmethod(assert_not_none)
    assert_true = staticmethod(assert_true)
    assert_false = staticmethod(assert_false)
    assert_empty = staticmethod(assert_empty)
    assert_list_length = staticmethod(assert_list_length)
    assert_contains = staticmethod(assert_contains)