# utils/jira/client.py
import logging

import requests
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry

from utils.jira.models import JiraErrorMsg, JiraIssueResult
from utils.jira.payload_builder import JiraPayloadBuilder
from utils.jira.settings import JiraSettings

logger = logging.getLogger(__name__)


class JiraClient:
    """
    Jira API 통신을 전담하는 엔터프라이즈 클라이언트 클래스.
    
    공유 HTTP 세션(Connection Pool)을 사용하여 네트워크 오버헤드를 줄이고, 
    Jira 서버의 Rate Limit(429) 및 일시적 장애(5xx)에 대응하는 정교한 재시도 정책을 지원합니다.
    """
    
    # 인스턴스가 여러 개 생성되더라도 커넥션 풀을 공유하기 위한 클래스 레벨 세션 캐시
    _session: requests.Session | None = None

    def __init__(self, settings: JiraSettings | None = None, session: requests.Session | None = None) -> None:
        """
        JiraClient 인스턴스를 초기화합니다.
        
        의존성 주입(DI) 구조를 적용하여, Unit Test 시 Mocking 객체를 주입할 수 있도록 설계했습니다.
        
        Args:
            settings (JiraSettings | None): Jira 연동 설정 객체. 생략 시 기본 환경변수를 로드합니다.
            session (requests.Session | None): 커스텀 HTTP 세션. 생략 시 전역 공유 세션을 사용합니다.
        """
        self.settings = settings or JiraSettings()
        self.session = session or self._get_shared_session()
        self.payload_builder = JiraPayloadBuilder(
            project_key=self.settings.project_key,
            issue_type=self.settings.issue_type
        )

    @classmethod
    def _get_shared_session(cls) -> requests.Session:
        """
        Jira 전용 HTTP Session을 생성하고 전역 공통 헤더 및 Retry 정책을 설정합니다.
        
        Returns:
            requests.Session: 재시도 정책이 마운트된 공유 HTTP 세션 객체
        """
        if cls._session is None:
            cls._session = requests.Session()
            
            # 매 요청마다 반복되는 공통 헤더 주입
            cls._session.headers.update({
                "Accept": "application/json",
                "Content-Type": "application/json"
            })
            
            # 실무 기준에 맞춘 엄격한 Retry 정책 (429 Too Many Requests 대응 및 서버 부하 방지)
            retries = Retry(
                total=3,
                connect=3,
                read=3,
                status=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods={"POST"},
                respect_retry_after_header=True
            )
            adapter = HTTPAdapter(max_retries=retries)
            cls._session.mount("http://", adapter)
            cls._session.mount("https://", adapter)
            
        return cls._session

    def _build_api_url(self, path: str) -> str:
        """Base URL과 하위 경로(Path)를 결합하여 완벽한 API 엔드포인트 URL을 생성합니다."""
        return f"{self.settings.base_url.rstrip('/')}/{path.lstrip('/')}"

    def _build_issue_url(self, issue_key: str) -> str:
        """생성된 티켓의 브라우저 열람용(UI) URL을 생성합니다."""
        return f"{self.settings.base_url.rstrip('/')}/browse/{issue_key}"

    def _success(self, issue_key: str) -> JiraIssueResult:
        """
        성공 결과 반환을 위한 내부 헬퍼 메서드 (코드 중복 제거).
        """
        issue_url = self._build_issue_url(issue_key)
        logger.info(f"✅ Jira 버그 티켓 자동 생성 완료: {issue_key}")
        logger.debug(f"Jira Ticket URL: {issue_url}")
        
        return JiraIssueResult(success=True, issue_key=issue_key, issue_url=issue_url)

    def _failure(self, error_message: str) -> JiraIssueResult:
        """
        실패 결과 반환을 위한 내부 헬퍼 메서드 (코드 중복 제거).
        """
        logger.error(f"❌ Jira 티켓 생성 실패: {error_message}")
        
        return JiraIssueResult(success=False, issue_key=None, issue_url=None, error_message=error_message)

    def create_bug_ticket(self, test_name: str, error_trace: str) -> JiraIssueResult:
        """
        테스트 실패 내용을 기반으로 버그 티켓을 생성합니다.
        [검증 -> 페이로드 생성 -> API 요청 -> 응답 파싱 -> 결과 반환]의 5단계 구조로 안전하게 동작합니다.
        
        Args:
            test_name (str): 실패한 테스트 케이스의 이름
            error_trace (str): 실패 시 발생한 에러 스택 트레이스 문자열
            
        Returns:
            JiraIssueResult: 티켓 생성 성공 여부 및 URL이 담긴 데이터 모델 객체
        """
        # 1. 환경 설정 검증 (누락 시 API 요청 생략)
        if not self.settings.is_configured:
            return self._failure(JiraErrorMsg.CONFIG_MISSING.value)

        # 2. 페이로드 및 엔드포인트, 인증 객체 구성
        endpoint = self._build_api_url("rest/api/2/issue")
        auth = HTTPBasicAuth(self.settings.user_email, self.settings.api_token.get_secret_value())
        payload = self.payload_builder.build(test_name, error_trace)

        # 3. API 요청 및 세분화된 예외 처리
        try:
            response = self.session.post(endpoint, json=payload, auth=auth, timeout=self.settings.timeout)
            
            # API 호출 추적을 위한 상세 로깅
            logger.info(f"[Jira API] POST /issue | Status: {response.status_code} | Elapsed: {response.elapsed.total_seconds()}s")

            # 4. 상태 코드 우선 검증 및 JSON 파싱
            response.raise_for_status()
            
            try:
                body = response.json()
            except ValueError:
                content_type = response.headers.get("Content-Type", "N/A")
                body_snippet = response.text[:200]
                return self._failure(f"{JiraErrorMsg.JSON_PARSE_ERROR.value} | Content-Type: {content_type} | Body: {body_snippet}")

            # 5. 응답 결과 반환
            issue_key = body.get("key")
            if not issue_key:
                return self._failure(f"{JiraErrorMsg.MISSING_ISSUE_KEY.value} | Body: {body}")

            return self._success(issue_key)

        except requests.exceptions.Timeout as e:
            return self._failure(f"API Request Timeout: {e}")
        except requests.exceptions.ConnectionError as e:
            return self._failure(f"Network Connection Error: {e}")
        except requests.exceptions.HTTPError as e:
            error_body = e.response.text[:200] if e.response is not None else "N/A"
            return self._failure(f"HTTP Error {e.response.status_code}: {error_body}")