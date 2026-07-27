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
    def _summarize_xfail_reasons(reports: list[Any]) -> list[str]:
        """xfail/xpass 리포트에서 마커의 reason을 뽑아 같은 사유끼리 묶습니다.

        파라미터화된 테스트는 같은 사유로 여러 건이 잡히므로 `(×N)`으로 합쳐
        알림이 같은 문장으로 도배되는 것을 막습니다.
        reason 없이 xfail만 걸어둔 경우에는 테스트 이름으로 대체합니다.

        Args:
            reports (list[Any]): stats["xfailed"] 또는 stats["xpassed"]의 리포트 목록

        Returns:
            list[str]: 중복이 합쳐진 사유 문자열 목록
        """
        counts: dict[str, int] = {}
        for report in reports:
            reason = (getattr(report, "wasxfail", "") or "").strip()
            if not reason:
                reason = report.nodeid.split("::")[-1]
            counts[reason] = counts.get(reason, 0) + 1

        return [f"{reason} (×{n})" if n > 1 else reason for reason, n in counts.items()]

    @staticmethod
    def build(terminalreporter: TerminalReporter) -> dict[str, Any]:
        """
        테스트 실행 통계를 추출하여 요약 딕셔너리를 생성합니다.

        Pytest는 결과를 passed/failed/skipped 외에 error(setup·teardown 실패),
        xfailed(알려진 버그), xpassed(버그 수정 추정) 버킷에도 나눠 담습니다.
        이 버킷들을 빠뜨리면 Total이 실제 실행 건수보다 적게 나오므로(Allure와 불일치)
        아래 기준으로 집계합니다.

          - error   → failed  : 조치가 필요한 실패이므로 실패로 집계하고 목록에도 노출
          - xpassed → passed  : 버그가 고쳐졌을 가능성 (Jira 알림은 jira_hook이 담당)
          - xfailed → 별도 집계: 미실행(skip)과 성격이 달라 섞지 않고 따로 반환

        ⚠️ xfailed를 skipped에서 분리했으므로, 수신 측(Slack/Discord)의 Total은
           passed + failed + skipped + xfailed 로 계산해야 합니다.

        Args:
            terminalreporter (TerminalReporter): Pytest의 터미널 결과 리포터 객체

        Returns:
            dict[str, Any]: 결과별 개수와 소요 시간, 실패 테스트 목록,
                그리고 xfail/xpass의 사유 목록이 포함된 딕셔너리
        """
        stats = terminalreporter.stats
        failed_reports = stats.get("failed", [])
        xfailed_reports = stats.get("xfailed", [])
        xpassed_reports = stats.get("xpassed", [])

        # 한 테스트가 call 실패 후 teardown에서도 에러가 나면 두 버킷에 모두 잡히므로 중복을 제거합니다.
        failed_nodeids = {report.nodeid for report in failed_reports}
        error_reports = [r for r in stats.get("error", []) if r.nodeid not in failed_nodeids]

        passed = len(stats.get("passed", [])) + len(xpassed_reports)
        failed = len(failed_reports) + len(error_reports)
        skipped = len(stats.get("skipped", []))
        xfailed = len(xfailed_reports)

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
            "xfailed": xfailed,
            "duration_sec": duration_sec,
            "failed_tests": failed_tests,
            "xfail_reasons": ReportSummaryBuilder._summarize_xfail_reasons(xfailed_reports),
            "xpass_reasons": ReportSummaryBuilder._summarize_xfail_reasons(xpassed_reports),
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