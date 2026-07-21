# utils/jira/payload_builder.py
import os
from typing import Any


class JiraPayloadBuilder:
    """
    Jira API 요청에 사용할 JSON 페이로드 조립을 전담하는 Builder 클래스.
    
    Jira 서버의 텍스트 길이 제한(Limit) 정책으로 인해 API 호출이 거부되는 것을 
    방지하기 위해, Summary와 Description의 최대 길이를 안전하게 제어합니다.
    (순수 데이터 조립을 목적으로 하므로 로깅은 Client 계층에 위임합니다.)
    """

    # Jira API 거부 방어를 위한 매직 넘버 상수화
    MAX_SUMMARY_LENGTH = 200
    # 스택 트레이스 + 캡처된 HTTP 요청/응답 로그까지 담으므로 넉넉히 잡는다(Jira description 한도 내).
    MAX_TRACE_LENGTH = 20000

    def __init__(self, project_key: str, issue_type: str) -> None:
        """
        JiraPayloadBuilder 인스턴스를 초기화합니다.
        
        Args:
            project_key (str): 이슈를 생성할 대상 프로젝트의 키 (예: 'QA')
            issue_type (str): 생성할 이슈의 타입 (예: 'Bug')
        """
        self.project_key = project_key
        self.issue_type = issue_type

    def _build_summary(self, test_name: str) -> str:
        """
        버그 티켓의 제목(Summary)을 생성하고 최대 길이를 제한합니다.
        
        Args:
            test_name (str): 실패한 테스트 케이스의 이름
            
        Returns:
            str: 길이 제한이 적용된 안전한 제목 문자열
        """
        summary = f"[Auto-Bug] 테스트 자동화 실패: {test_name}"
        return summary[:self.MAX_SUMMARY_LENGTH]

    def _build_description(self, test_name: str, error_trace: str) -> str:
        """
        버그 티켓의 본문(Description)을 포맷팅하고 최대 길이를 제한합니다.
        
        CI/CD 파이프라인에서 실행된 경우 해당 Job의 URL을 포함시켜 추적성을 높입니다.
        
        Args:
            test_name (str): 실패한 테스트 케이스의 이름
            error_trace (str): 오류 발생 시의 스택 트레이스 원문
            
        Returns:
            str: Jira 마크다운 규격이 적용된 안전한 본문 문자열
        """
        safe_trace = error_trace[:self.MAX_TRACE_LENGTH]
        job_url = os.getenv("CI_JOB_URL", "로컬 실행 환경")
        env_name = os.getenv("TEST_ENV", "qa").upper()

        return (
            f"*자동화 파이프라인에서 테스트 실패가 감지되었습니다.*\n\n"
            f"* 📌 테스트명: {test_name}\n"
            f"* 🌍 실행 환경: {env_name}\n"
            f"* 🔗 CI/CD 링크: {job_url}\n\n"
            f"* 🚨 상세 로그 (스택 트레이스 + HTTP 요청/응답·payload):*\n"
            f"{{code}}\n{safe_trace}\n{{code}}"
        )

    def build(self, test_name: str, error_trace: str) -> dict[str, Any]:
        """
        Jira API 전송에 즉시 사용할 수 있는 최종 페이로드 딕셔너리를 생성합니다.
        
        Args:
            test_name (str): 실패한 테스트 케이스의 이름
            error_trace (str): 오류 발생 시의 스택 트레이스 원문
            
        Returns:
            dict[str, Any]: 조립이 완료된 페이로드 데이터 전송 객체
        """
        # (아래는 이슈 생성 payload — build_comment 는 클래스 하단에 별도 정의)
        # issue_type이 숫자로만 이뤄지면 ID(예: "10080"), 아니면 이름(예: "버그"/"Bug")으로 취급.
        # ID는 이름이 현지화/변경돼도 안 바뀌므로 더 안전하다.
        issuetype = (
            {"id": self.issue_type}
            if self.issue_type.isdigit()
            else {"name": self.issue_type}
        )

        return {
            "fields": {
                "project": {"key": self.project_key},
                "summary": self._build_summary(test_name),
                "description": self._build_description(test_name, error_trace),
                "issuetype": issuetype,
                "labels": ["automation", "pytest", "nightly"]
            }
        }

    def build_comment(self, test_name: str, error_trace: str) -> str:
        """기존 이슈에 남길 실패 이력 댓글 본문을 생성합니다(생성 payload의 description과 동일 포맷 재사용).

        Args:
            test_name (str): 실패한 테스트 케이스 이름.
            error_trace (str): 실패 시 스택 트레이스.

        Returns:
            str: Jira 마크다운 규격이 적용된 댓글 본문 문자열.
        """
        return self._build_description(test_name, error_trace)
