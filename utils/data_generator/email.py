# utils/data_generator/email.py
import time

from utils.data_generator.faker_manager import get_faker


def generate_qa_email(domain: str = "example.test") -> str:
    """
    테스트 데이터를 실운영 데이터와 명확히 구분하고 중복(충돌)을 완벽히 방지하는 이메일 생성.
    실무에서 스팸/외부 발송 이슈를 막기 위해 'example.test' 같은 고정 도메인을 사용합니다.
    """
    # 병렬 테스트 시 동일한 이메일이 생성되지 않도록 타임스탬프와 난수 조합
    timestamp = int(time.time() * 1000)
    
    # pystr()를 이용해 소문자 랜덤 문자열 생성
    fake = get_faker("en_US")
    random_str = fake.pystr(min_chars=5, max_chars=5).lower()
    
    return f"qa_{timestamp}_{random_str}@{domain}"