# utils/data_generator/password.py
import secrets
import string

# 비밀번호 정책 변경 시 쉽게 대응할 수 있도록 모듈 상수로 캡슐화
_PASSWORD_SPECIAL_CHARS = "!@#$%^&*"
_AMBIGUOUS_CHARS = "Il1O0"


def generate_secure_password(
    length: int = 12,
    require_special: bool = True,
    require_upper: bool = True,
    exclude_ambiguous: bool = True
) -> str:
    """
    회사 보안 정책에 맞는 무작위 비밀번호를 생성합니다. (secrets 모듈 사용)
    
    Args:
        length (int): 비밀번호 길이 (8 ~ 256)
        require_special (bool): 특수문자 포함 여부
        require_upper (bool): 대문자 포함 여부
        exclude_ambiguous (bool): 사람의 눈으로 구분이 어려운 문자(I, l, 1, O, 0) 제외 여부
    """
    if not (8 <= length <= 256):
        raise ValueError("[Error] 안전한 비밀번호는 8자리 이상, 256자리 이하이어야 합니다.")

    # 사용 가능한 문자 풀(Pool) 구성
    lowercase_pool = string.ascii_lowercase
    digit_pool = string.digits
    uppercase_pool = string.ascii_uppercase if require_upper else ""
    special_pool = _PASSWORD_SPECIAL_CHARS if require_special else ""

    # 가독성을 위해 모호한 문자 필터링
    if exclude_ambiguous:
        lowercase_pool = "".join(c for c in lowercase_pool if c not in _AMBIGUOUS_CHARS)
        digit_pool = "".join(c for c in digit_pool if c not in _AMBIGUOUS_CHARS)
        uppercase_pool = "".join(c for c in uppercase_pool if c not in _AMBIGUOUS_CHARS)

    password_chars = []
    
    # 조건별 필수 문자 1개씩 사전 확보
    password_chars.append(secrets.choice(lowercase_pool))
    password_chars.append(secrets.choice(digit_pool))
    if require_upper:
        password_chars.append(secrets.choice(uppercase_pool))
    if require_special:
        password_chars.append(secrets.choice(special_pool))

    # 남은 길이는 허용된 전체 풀에서 무작위 추출
    allowed_chars = lowercase_pool + digit_pool + uppercase_pool + special_pool
    if not allowed_chars:
        raise ValueError("허용된 문자 풀이 비어있습니다.")

    remaining_length = length - len(password_chars)
    password_chars += [secrets.choice(allowed_chars) for _ in range(remaining_length)]

    # 배열을 섞은 뒤 문자열로 반환
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)