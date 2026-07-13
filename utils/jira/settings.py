# utils/jira/settings.py
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class JiraSettings(BaseSettings):
    """
    Jira API 통신에 필요한 환경 변수와 타임아웃 설정을 캡슐화한 클래스.
    
    어플리케이션(프레임워크)이 구동되거나 JiraClient가 인스턴스화되는 시점에
    필수 환경 변수들의 누락 및 타입 에러를 사전에 방어(Fail-fast)합니다.
    """
    
    base_url: str = Field(default="", validation_alias="JIRA_BASE_URL")
    user_email: str = Field(default="", validation_alias="JIRA_USER_EMAIL")
    
    # API 토큰은 로그나 터미널에 평문으로 노출되지 않도록 SecretStr로 엄격히 보호합니다.
    api_token: SecretStr = Field(default=SecretStr(""), validation_alias="JIRA_API_TOKEN")
    
    project_key: str = Field(default="QA", validation_alias="JIRA_PROJECT_KEY")
    issue_type: str = Field(default="Bug", validation_alias="JIRA_ISSUE_TYPE")
    
    # HTTP 타임아웃은 글로벌 설정에 의존하지 않고 각 연동 클라이언트(Jira, Slack 등)마다 
    # 독립적으로 설정하는 것이 실무 표준입니다.
    timeout: tuple[int, int] = Field(default=(5, 10), description="Connect, Read Timeout 튜플")

    @property
    def is_configured(self) -> bool:
        """
        Jira 연동에 필수적인 값들이 모두 정상적으로 세팅되었는지 확인합니다.
        
        Returns:
            bool: 필수 설정값(base_url, user_email, api_token, project_key)이 모두 존재하면 True
        """
        return bool(
            self.base_url 
            and self.user_email 
            and self.api_token.get_secret_value() 
            and self.project_key
        )