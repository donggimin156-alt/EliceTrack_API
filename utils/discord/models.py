# utils/discord/models.py
from enum import Enum


class DiscordColor(int, Enum):
    """
    Discord Embed의 사이드바 테마 색상을 정의하는 Enum 클래스.
    
    테스트 결과(성공, 실패, 경고)에 따라 알림 메시지 좌측에 표시될 
    직관적인 시각적 색상 코드를 제공합니다.
    주의: Discord API 명세에 맞춰 16진수(Hex)가 아닌 10진수(Integer) 값을 사용합니다.
    """
    SUCCESS = 3581519   # Hex #36a64f -> Decimal 3581519 (초록색)
    FAIL = 16711680     # Hex #ff0000 -> Decimal 16711680 (빨간색)
    WARNING = 16763904  # Hex #ffcc00 -> Decimal 16763904 (노란색)


class DiscordStatusIcon(str, Enum):
    """
    테스트 결과 상태를 직관적으로 나타내는 이모지(Emoji)를 정의하는 Enum 클래스.
    
    메시지 헤더나 본문에 텍스트와 함께 배치되어 
    알림 수신자가 결과를 빠르게 파악할 수 있도록 돕습니다.
    """
    SUCCESS = "✅"
    FAIL = "🚨"
    WARNING = "⚠️"