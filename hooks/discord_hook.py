# hooks/discord_hook.py
import logging

from _pytest.config import Config
from _pytest.terminal import TerminalReporter

# 팀 컨벤션: 기존 Slack 훅에 구현된 빌더 로직을 그대로 재사용하여 중복 코드를 제거합니다.
from hooks.slack_hook import ReportSummaryBuilder

logger = logging.getLogger(__name__)


def pytest_terminal_summary(terminalreporter: TerminalReporter, exitstatus: int, config: Config) -> None:
    """
    테스트 세션이 완전히 종료된 후 최종 결과를 취합하여 Discord로 전송합니다.
    
    Args:
        terminalreporter (TerminalReporter): 터미널 리포터 객체
        exitstatus (int): Pytest 종료 상태 코드
        config (Config): Pytest 설정 객체
    """
    # 공용 통계 빌더를 통해 정제된 데이터 수집
    summary = ReportSummaryBuilder.build(terminalreporter)

    try:
        # Lazy Import: 모듈 순환 참조 방지 및 프레임워크 초기 로딩 속도 최적화
        from utils.discord import DiscordClient
        
        # Discord 클라이언트를 인스턴스화하여 요약 리포트 발송
        notifier = DiscordClient()
        notifier.send_summary_report(**summary)
        
    except Exception as e:
        # 알림 전송 실패가 전체 테스트 세션 결과에 영향을 주지 않도록 예외 격리
        logger.exception(f"[Discord Hook] 최종 요약 리포트 전송 중 시스템 오류 발생: {e}")