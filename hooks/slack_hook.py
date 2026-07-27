# hooks/slack_hook.py
import logging
import time
from typing import Any

from _pytest.config import Config
from _pytest.terminal import TerminalReporter

logger = logging.getLogger(__name__)


class ReportSummaryBuilder:
    """
    Pytest의 복잡한 TerminalReporter 객체를 파싱하여
    알림 시스템에 최적화된 Dictionary 형태로 변환하는 빌더 클래스.
    """
    
    @staticmethod
    def build(terminalreporter: TerminalReporter) -> dict[str, Any]:
        """
        테스트 실행 통계를 추출하여 요약 딕셔너리를 생성합니다.

        Pytest는 결과를 passed/failed/skipped 외에 error(setup·teardown 실패),
        xfailed(알려진 버그), xpassed(버그 수정 추정) 버킷에도 나눠 담습니다.
        앞의 셋만 세면 나머지가 통째로 빠져 Total이 실제 실행 건수보다 적게 나오므로
        (Allure 리포트와 숫자가 어긋남), 아래 기준으로 세 버킷에 흡수시킵니다.

          - error   → failed  : 조치가 필요한 실패이므로 실패로 집계하고 목록에도 노출
          - xfailed → skipped : 검증을 넘어간 알려진 버그 (Allure의 분류와 동일)
          - xpassed → passed  : 버그가 고쳐졌을 가능성 (별도 알림은 jira_hook이 담당)

        Args:
            terminalreporter (TerminalReporter): Pytest의 터미널 결과 리포터 객체

        Returns:
            dict[str, Any]: 통과, 실패, 스킵 개수 및 소요 시간, 실패한 테스트 목록이 포함된 딕셔너리
        """
        stats = terminalreporter.stats
        failed_reports = stats.get("failed", [])

        # 한 테스트가 call 실패 후 teardown에서도 에러가 나면 두 버킷에 모두 잡히므로 중복을 제거합니다.
        failed_nodeids = {report.nodeid for report in failed_reports}
        error_reports = [r for r in stats.get("error", []) if r.nodeid not in failed_nodeids]

        passed = len(stats.get("passed", [])) + len(stats.get("xpassed", []))
        failed = len(failed_reports) + len(error_reports)
        skipped = len(stats.get("skipped", [])) + len(stats.get("xfailed", []))

        # setup/teardown 에러는 테스트 본문 실패와 원인이 다르므로 목록에서 구분해 표시합니다.
        failed_tests = [report.nodeid.split("::")[-1] for report in failed_reports]
        failed_tests += [f"{report.nodeid.split('::')[-1]} (error)" for report in error_reports]

        # 단순 time.time() 차이보다 Pytest 내부 세션 시작 시간을 사용하는 것이 정합성에 더 유리합니다.
        start_time = getattr(terminalreporter, "_sessionstarttime", time.time())
        duration_sec = time.time() - start_time

        return {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration_sec": duration_sec,
            "failed_tests": failed_tests
        }


def pytest_terminal_summary(terminalreporter: TerminalReporter, exitstatus: int, config: Config) -> None:
    """
    테스트 세션이 완전히 종료된 후 최종 결과를 취합하여 Slack으로 전송합니다.
    
    Args:
        terminalreporter (TerminalReporter): 터미널 리포터 객체
        exitstatus (int): Pytest 종료 상태 코드
        config (Config): Pytest 설정 객체
    """
    summary = ReportSummaryBuilder.build(terminalreporter)

    try:
        # Lazy Import: 모듈 순환 참조를 방지하고, 초기 로딩 속도를 최적화합니다.
        # 또한, 향후 TeamsClient 등 다른 메신저로 확장이 용이하도록 호출부를 분리했습니다.
        from utils.slack import SlackClient
        
        # 향후 NotificationManager 등으로 추상화할 수 있는 확장 지점
        notifier = SlackClient()
        notifier.send_summary_report(**summary)
        
    except Exception as e:
        # 알림 전송 실패가 테스트 자체의 성공/실패 여부에 영향을 주지 않도록 예외를 삼킵니다.
        logger.exception(f"[Slack Hook] 최종 요약 리포트 전송 중 시스템 오류 발생: {e}")