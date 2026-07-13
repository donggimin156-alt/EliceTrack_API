# utils/jira/models.py
from dataclasses import dataclass
from enum import Enum


class JiraErrorMsg(str, Enum):
    """
    실무 환경에서 모니터링 및 로깅의 일관성을 유지하기 위해 
    Jira 연동 시 발생하는 에러 메시지를 상수로 관리하는 Enum 클래스.
    """
    CONFIG_MISSING = "Jira configuration is missing or incomplete."
    JSON_PARSE_ERROR = "Failed to parse Jira API response as JSON."
    MISSING_ISSUE_KEY = "Jira ticket was successfully created, but the response is missing the 'key'."


@dataclass
class JiraIssueResult:
    """
    Jira 티켓 생성 요청에 대한 최종 처리 결과를 명확하게 캡슐화하는 데이터 클래스(DTO).
    
    Attributes:
        success (bool): 티켓 생성 성공 여부
        issue_key (str | None): 생성된 티켓의 고유 키 (예: 'QA-123')
        issue_url (str | None): 브라우저에서 티켓을 바로 열람할 수 있는 전체 접속 URL
        error_message (str | None): 실패 시 원인을 파악할 수 있는 상세 에러 메시지 (기본값: None)
    """
    success: bool
    issue_key: str | None
    issue_url: str | None
    error_message: str | None = None