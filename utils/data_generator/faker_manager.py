# utils/data_generator/faker_manager.py
from functools import lru_cache

from faker import Faker

# 향후 core/config.py에 Config.locale() 설정이 추가되었다고 가정하고 사용할 수 있습니다.
# from core.config import Config


@lru_cache(maxsize=16)
def get_faker(locale: str = "en_US") -> Faker:
    """
    요청된 Locale의 Faker 인스턴스를 반환합니다.
    @lru_cache를 통한 Lazy Loading으로, 사용하지 않는 언어의 초기화 리소스를 아끼고
    동일한 언어의 Faker 인스턴스를 전역에서 캐싱하여 재사용합니다.
    """
    # 실무 적용 예시: locale = locale or Config.locale()
    return Faker(locale)


def set_seed(seed: int) -> None:
    """
    간헐적 실패 디버깅 시 재현 가능한 테스트를 위해 Faker 시드를 고정합니다.
    Faker 클래스 메서드를 직접 호출하여 생성된 모든 인스턴스에 적용되도록 합니다.
    """
    Faker.seed(seed)