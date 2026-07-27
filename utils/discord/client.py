# utils/discord/client.py
import logging
import os
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.discord.embed_builder import DiscordEmbedBuilder
from utils.discord.models import DiscordColor, DiscordStatusIcon
from utils.discord.settings import DiscordSettings

logger = logging.getLogger(__name__)


class DiscordClient:
    """
    Discord 메시지 전송을 전담하는 엔터프라이즈 클라이언트.
    
    공유 세션(Connection Pool) 기반의 통신, 429(Rate Limit) 등 서버 에러에 대한 
    자동 재시도(Retry) 정책, 그리고 Webhook URL 보호를 위한 마스킹 로깅을 지원합니다.
    """
    
    _session: requests.Session | None = None

    def __init__(self, settings: DiscordSettings | None = None, session: requests.Session | None = None) -> None:
        """
        DiscordClient 인스턴스를 초기화합니다.
        
        의존성 주입(DI) 구조를 적용하여 Unit Test 시 Mocking이 용이하도록 설계했습니다.
        
        Args:
            settings (DiscordSettings | None): Discord 환경 설정 객체
            session (requests.Session | None): HTTP 통신 세션 객체
        """
        self.settings = settings or DiscordSettings()
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
            
            # Discord API 제약에 맞춘 재시도 정책 (주로 429 Too Many Requests 대응)
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
        보안을 위해 로깅 시 Webhook URL의 토큰 주소가 노출되지 않도록 마스킹 처리합니다.
        
        Args:
            payload (dict[str, Any]): 전송할 Discord API 규격의 JSON 딕셔너리
        """
        if not self.settings.is_configured:
            logger.info("디스코드 Webhook URL이 구성되지 않아 알림 전송을 생략합니다.")
            return

        webhook_url = self.settings.webhook_url.get_secret_value().strip()
        
        # 보안: Webhook 토큰 전체가 로깅되지 않도록 엔드포인트 앞부분만 추출
        domain = webhook_url.split('/api/webhooks/')[0] if '/api/webhooks/' in webhook_url else "Unknown Domain"

        try:
            response = self.session.post(webhook_url, json=payload, timeout=self.settings.timeout)
            logger.info(f"[디스코드 API] POST to {domain} | Status: {response.status_code} | Elapsed: {response.elapsed.total_seconds()}s")

            # Discord 웹훅은 정상 전송 시 HTTP 204 No Content를 반환합니다.
            response.raise_for_status()
            logger.debug("✅ 디스코드 알림 전송 완료")

        except requests.exceptions.Timeout as e:
            logger.error(f"[디스코드 Error] 요청 타임아웃: {e}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[디스코드 Error] 네트워크 연결 실패: {e}")
        except requests.exceptions.HTTPError as e:
            error_body = e.response.text if e.response is not None else "N/A"
            logger.error(f"[디스코드 Error] HTTP Error {e.response.status_code}: {error_body}")

    def _bullet_list(self, items: list[str]) -> str:
        """테스트 이름 목록을 불릿 문자열로 만들고 Discord Field 제약에 맞춰 잘라냅니다.

        Discord는 Field 하나의 value가 1024자를 넘으면 요청을 거부하므로,
        개수(max_failed_tests) 제한과 별개로 길이도 함께 방어합니다.

        Args:
            items (list[str]): 나열할 테스트 이름 목록

        Returns:
            str: Discord 마크다운 불릿 목록 문자열
        """
        max_show = self.settings.max_failed_tests
        lines = [f"• `{item}`" for item in items[:max_show]]

        # 지정된 개수(max_failed_tests)를 초과하면 줄임 표시를 추가합니다.
        if len(items) > max_show:
            lines.append(f"... and {len(items) - max_show} more")

        text = "\n".join(lines)
        if len(text) > self.settings.max_field_length:
            text = text[:self.settings.max_field_length - 15] + "\n... [TRUNCATED]"

        return text

    def send_summary_report(
        self,
        passed: int,
        failed: int,
        skipped: int,
        duration_sec: float,
        failed_tests: list[str] | None = None,
        xfailed: int = 0,
        xfail_reasons: list[str] | None = None,
        xpass_reasons: list[str] | None = None
    ) -> None:
        """
        테스트 세션 종료 후 결과를 취합하여 Discord에 요약 알림(Summary Report)을 전송합니다.

        Discord는 Slack과 달리 한눈에 들어오는 간략한 요약을 유지합니다.
        상세 내역(Skipped/xfail 개수, 알려진 버그 목록, XPASS 목록)은 Slack에서만 표시합니다.

        ⚠️ xfail_reasons / xpass_reasons 는 화면에 쓰지 않지만 파라미터는 반드시 남겨두세요.
           discord_hook 이 Slack 훅과 같은 요약 딕셔너리를 send_summary_report(**summary) 로
           통째로 넘기므로, 파라미터를 지우면 TypeError 가 나고 그 예외가 훅의 except 에
           삼켜져 Discord 알림이 아무 흔적 없이 사라집니다.

        Args:
            passed (int): 성공한 테스트 케이스 수
            failed (int): 실패한 테스트 케이스 수
            skipped (int): 건너뛴 테스트 케이스 수
            duration_sec (float): 전체 테스트 소요 시간(초)
            failed_tests (list[str] | None): 실패한 테스트 케이스의 이름 리스트 (선택 사항)
            xfailed (int): 알려진 버그로 xfail 처리된 테스트 수 (Total 계산에만 사용)
            xfail_reasons (list[str] | None): 미표시. 시그니처 호환용 (위 주의 참고)
            xpass_reasons (list[str] | None): 미표시. 시그니처 호환용 (위 주의 참고)
        """
        # 표시는 하지 않지만 xfailed 는 Total 에 반드시 더합니다.
        # (빠뜨리면 Discord Total 이 Slack/Allure Total 보다 적게 나옵니다)
        total = passed + failed + skipped + xfailed
        success_rate = (passed / total * 100) if total > 0 else 0
        is_success = failed == 0

        color = DiscordColor.SUCCESS if is_success else DiscordColor.FAIL
        icon = DiscordStatusIcon.SUCCESS if is_success else DiscordStatusIcon.FAIL
        env_name = os.getenv("TEST_ENV", "qa").upper()

        # Builder 패턴을 활용하여 Discord Embed 구성
        builder = DiscordEmbedBuilder(self.settings)
        builder.set_title(f"QA Automation Test Result ({env_name})", icon=icon.value)

        branch_name = os.getenv("CI_COMMIT_BRANCH", "local")
        trigger = os.getenv("CI_PIPELINE_SOURCE", "manual")

        # Discord Embed Field 양식에 맞게 다단 데이터 추가
        builder.add_field("Total Tests", f"{total}", inline=True)
        builder.add_field("Success Rate", f"{success_rate:.1f}%", inline=True)
        builder.add_field("Passed", f"{passed} 🟢", inline=True)
        builder.add_field("Failed", f"{failed} 🔴", inline=True)
        builder.add_field("Duration", f"{duration_sec:.1f} sec ⏱️", inline=True)
        builder.add_field("Branch", f"`{branch_name}` ({trigger})", inline=True)

        # 버튼 컴포넌트 대신 마크다운 하이퍼링크 필드로 전송 리크 연결
        job_url = os.getenv("CI_JOB_URL", "")
        if job_url.startswith("http"):
            builder.add_field("CI Pipeline", f"[View CI Pipeline 🔗]({job_url})", inline=False)

        if failed_tests:
            builder.add_field("🚨 Failed Tests", self._bullet_list(failed_tests), inline=False)

        builder.set_footer("TEAM2 CI/CD 자동화 시스템")

        payload = builder.build_payload(color)
        self._send(payload)