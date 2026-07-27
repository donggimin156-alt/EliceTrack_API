# utils/discord/settings.py
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class DiscordSettings(BaseSettings):
    """
    Discord 연동에 필요한 환경 변수와 타임아웃, 제한(Limit) 설정을 캡슐화한 클래스.
    
    Webhook URL과 같은 민감한 정보는 SecretStr로 보호하여 
    로깅이나 디버깅 과정에서 평문으로 노출되는 것을 원천적으로 차단합니다.
    """
    
    webhook_url: SecretStr = Field(
        default=SecretStr(""), validation_alias="DISCORD_WEBHOOK_URL")
    
    # HTTP 타임아웃은 글로벌 설정에 의존하지 않고 각 클라이언트 목적에 맞게 독립적으로 관리합니다.
    # Discord API 권장 타임아웃 (Connect 5초, Read 10초)
    timeout: tuple[int, int] = Field(default=(5, 10), description="Connect, Read Timeout 튜플")
    
    # Discord API의 Payload 크기 제한 초과 방지를 위한 매직 넘버 상수화
    max_failed_tests: int = Field(default=10, description="디스코드 노출할 최대 실패 테스트 개수")
    max_fields: int = Field(default=25, description="디스코드 Embed 최대 허용 필드(Fields) 개수")
    max_field_length: int = Field(default=1024, description="디스코드 Embed 필드 하나의 최대 글자 수")

    @property
    def is_configured(self) -> bool:
        """
        Discord Webhook URL이 정상적으로 세팅되어 알림 전송이 가능한 상태인지 검증합니다.
        
        Returns:
            bool: Webhook URL 값이 존재하면 True, 비어있으면 False
        """
        return bool(self.webhook_url.get_secret_value())