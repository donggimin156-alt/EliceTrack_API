# utils/slack/client.py
import logging
import os
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.slack.block_builder import SlackBlockBuilder
from utils.slack.models import SlackColor, SlackStatusIcon
from utils.slack.settings import SlackSettings

logger = logging.getLogger(__name__)


class SlackClient:
    """
    Slack 메시지 전송을 전담하는 엔터프라이즈 클라이언트.
    
    공유 세션(Connection Pool) 기반의 통신, 429(Rate Limit) 등 서버 에러에 대한 
    자동 재시도(Retry) 정책, 그리고 Webhook URL 보호를 위한 마스킹 로깅을 지원합니다.
    """
    
    _session: requests.Session | None = None

    def __init__(self, settings: SlackSettings | None = None, session: requests.Session | None = None) -> None:
        """
        SlackClient 인스턴스를 초기화합니다.
        
        의존성 주입(DI) 구조를 적용하여 Unit Test 시 Mocking이 용이하도록 설계했습니다.
        
        Args:
            settings (SlackSettings | None): Slack 환경 설정 객체
            session (requests.Session | None): HTTP 통신 세션 객체
        """
        self.settings = settings or SlackSettings()
        self.session = session or self._get_shared_session()

    @classmethod
    def _get_shared_session(cls) -> requests.Session:
        """
        클래스 로딩 시점이 아닌, 첫 호출(Lazy) 시점에 세션을 생성하고 재시도 정책을 마운트합니다.
        
        Returns:
            requests.Session: 공통 헤더 및 Retry 설정이 완료된 공유 세션 객체
        """
        if cls._session is None:
            cls._session = requests.Session()
            cls._session.headers.update({
                "Content-Type": "application/json",
                "User-Agent": "QA-Automation-Framework/1.0"
            })
            
            # Slack API 제약에 맞춘 재시도 정책 (주로 429 Too Many Requests 대응)
            retries = Retry(
                total=3, 
                connect=3, 
                read=3, 
                status=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods={"POST"}
            )
            adapter = HTTPAdapter(max_retries=retries)
            cls._session.mount("http://", adapter)
            cls._session.mount("https://", adapter)
            
        return cls._session

    def _send(self, payload: dict[str, Any]) -> None:
        """
        실제 HTTP POST 요청을 수행하고 결과를 검증합니다.
        보안을 위해 로깅 시 Webhook URL의 전체 주소가 노출되지 않도록 마스킹 처리합니다.
        
        Args:
            payload (dict[str, Any]): 전송할 Slack API 규격의 JSON 딕셔너리
        """
        if not self.settings.is_configured:
            logger.info("Slack Webhook URL이 구성되지 않아 알림 전송을 생략합니다.")
            return

        webhook_url = self.settings.webhook_url.get_secret_value()
        
        # 보안: Webhook 전체가 로깅되지 않도록 도메인 앞부분만 추출
        domain = webhook_url.split('/services/')[0] if '/services/' in webhook_url else "Unknown Domain"

        try:
            response = self.session.post(webhook_url, json=payload, timeout=self.settings.timeout)
            logger.info(f"[Slack API] POST to {domain} | Status: {response.status_code} | Elapsed: {response.elapsed.total_seconds()}s")

            response.raise_for_status()

            # Slack API는 정상 전송 시 "ok" 문자열을 반환합니다. (개행 문자가 섞일 수 있어 strip 처리)
            if response.text.strip() != "ok":
                logger.warning(f"Slack 응답이 예상과 다릅니다. (전송은 성공했을 수 있음): {response.text}")
            else:
                logger.debug("✅ Slack 알림 전송 완료")

        except requests.exceptions.Timeout as e:
            logger.error(f"[Slack Error] 요청 타임아웃: {e}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[Slack Error] 네트워크 연결 실패: {e}")
        except requests.exceptions.HTTPError as e:
            error_body = e.response.text if e.response is not None else "N/A"
            logger.error(f"[Slack Error] HTTP Error {e.response.status_code}: {error_body}")

    def send_summary_report(
        self, 
        passed: int, 
        failed: int, 
        skipped: int, 
        duration_sec: float, 
        failed_tests: list[str] | None = None
    ) -> None:
        """
        테스트 세션 종료 후 결과를 취합하여 Slack에 요약 알림(Summary Report)을 전송합니다.
        
        Args:
            passed (int): 성공한 테스트 케이스 수
            failed (int): 실패한 테스트 케이스 수
            skipped (int): 건너뛴 테스트 케이스 수
            duration_sec (float): 전체 테스트 소요 시간(초)
            failed_tests (list[str] | None): 실패한 테스트 케이스의 이름 리스트 (선택 사항)
        """
        total = passed + failed + skipped
        success_rate = (passed / total * 100) if total > 0 else 0
        is_success = failed == 0

        color = SlackColor.SUCCESS if is_success else SlackColor.FAIL
        icon = SlackStatusIcon.SUCCESS if is_success else SlackStatusIcon.FAIL
        env_name = os.getenv("TEST_ENV", "qa").upper()

        # Builder 패턴을 활용하여 직관적으로 메시지 블록 구성
        builder = SlackBlockBuilder(self.settings)
        builder.add_header(f"QA Automation Test Result ({env_name})", icon=icon.value)

        branch_name = os.getenv("CI_COMMIT_BRANCH", "local")
        trigger = os.getenv("CI_PIPELINE_SOURCE", "manual")
        job_url = (os.getenv("CI_JOB_URL") or os.getenv("BUILD_URL") or "").strip()

        fields = [
            f"*Total Tests:*\n{total}",
            f"*Success Rate:*\n{success_rate:.1f}%",
            f"*Passed:*\n{passed} 🟢",
            f"*Failed:*\n{failed} 🔴",
            f"*Duration:*\n{duration_sec:.1f} sec ⏱️",
            f"*Branch:*\n`{branch_name}` ({trigger})"
        ]
        if job_url.startswith("http"):
            fields.append(f"*Jenkins:*\n<{job_url}|Open build #>")
        builder.add_section_fields(fields)

        if job_url.startswith("http"):
            builder.add_button("View Jenkins Build 🔗", job_url)

        if failed_tests:
            builder.add_divider()
            max_show = self.settings.max_failed_tests
            failed_list_str = "\n".join([f"• `{t}`" for t in failed_tests[:max_show]])
            
            # 지정된 개수(max_failed_tests)를 초과하면 줄임 표시를 추가합니다.
            if len(failed_tests) > max_show:
                failed_list_str += f"\n... and {len(failed_tests) - max_show} more"
            
            builder.add_text_section(f"*🚨 Failed Tests:*\n{failed_list_str}")

        payload = builder.build_payload(color)
        self._send(payload)