# hooks/jira_hook.py
import logging
import os
from typing import Generator

import pytest
from _pytest.reports import TestReport

logger = logging.getLogger(__name__)

# 중복 이슈 생성 억제를 위한 인메모리 캐시 셋 (Deduplication)
_reported_issues: set[str] = set()
# 동일 XPASS(버그 수정 추정) 알림을 세션당 1회만 남기기 위한 캐시
_xpass_notified: set[str] = set()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> Generator[None, None, None]:
    """
    테스트 실패 시 CI/CD 등 특정 환경에서 Jira 버그 티켓을 자동 생성합니다.
    
    Args:
        item (pytest.Item): 현재 실행 중인 테스트 아이템 객체
        call (pytest.CallInfo): 테스트 실행 단계(setup, call, teardown) 정보
    """
    outcome = yield
    rep: TestReport = outcome.get_result()

    is_jira_enabled = os.getenv("ENABLE_JIRA_AUTO_BUG", "false").lower() == "true"

    if rep.failed and is_jira_enabled:
        # 중복 방어: 동일한 NodeID(테스트)가 여러 단계(setup/call/teardown)에서 실패로 보고되더라도 1회만 처리합니다.
        if item.nodeid in _reported_issues:
            return
        _reported_issues.add(item.nodeid)

        error_trace = rep.longreprtext if rep.longreprtext else "No Traceback"

        # @pytest.mark.jira("EQA-5") 로 이 테스트가 추적하는 이슈 키를 읽는다.
        jira_marker = item.get_closest_marker("jira")
        issue_key = jira_marker.args[0] if (jira_marker and jira_marker.args) else None

        try:
            # Lazy Import: 모듈 순환 참조를 방지하고, Jira 기능이 꺼져있을 때 불필요한 패키지 로딩을 막습니다.
            from utils.jira import JiraClient

            jira = JiraClient()
            if issue_key:
                # 추적 대상 이슈가 있으면 새 티켓 대신 기존 이슈에 실패 이력을 댓글로 남긴다(중복 티켓 방지).
                logger.info(f"🎫 Jira 이슈 {issue_key} 에 실패 코멘트 추가: {item.name}")
                jira.add_comment(issue_key=issue_key, test_name=item.name, error_trace=error_trace)
            else:
                # 추적 이슈가 없으면 기존처럼 새 버그 티켓을 생성한다.
                logger.info(f"🎫 Jira 자동 버그 티켓 생성 트리거됨: {item.name}")
                jira.create_bug_ticket(test_name=item.name, error_trace=error_trace)
        except Exception as e:
            logger.exception(f"[Jira Hook] Jira 연동 중 시스템 오류 발생: {e}")

    # XPASS 감지: xfail(알려진 버그)로 표시된 테스트가 예상외로 통과하면 버그가 고쳐졌을 가능성이 높다.
    # 추적 이슈(@pytest.mark.jira)가 있으면 "수정된 듯" 알림 댓글을 남겨 사람이 확인 후 이슈를 닫도록 한다.
    is_xpass = rep.when == "call" and rep.passed and getattr(rep, "wasxfail", None) is not None

    if is_xpass and is_jira_enabled:
        jira_marker = item.get_closest_marker("jira")
        issue_key = jira_marker.args[0] if (jira_marker and jira_marker.args) else None
        if not issue_key or item.nodeid in _xpass_notified:
            return
        _xpass_notified.add(item.nodeid)

        try:
            from utils.jira import JiraClient

            note = (
                f"✅ *XPASS 감지 — 버그가 수정되었을 가능성이 높습니다.*\n\n"
                f"* 테스트: {item.name}\n"
                f"* 이 테스트는 이 이슈의 버그를 재현(xfail)하도록 표시돼 있었으나, 이번 실행에서 통과했습니다.\n"
                f"* 수정 여부를 확인한 뒤 이슈를 닫고, 테스트의 xfail 표시를 제거해 회귀 테스트로 전환하세요."
            )
            logger.info(f"✅ Jira 이슈 {issue_key} 에 XPASS(수정 추정) 알림: {item.name}")
            JiraClient().add_note(issue_key=issue_key, note=note)
        except Exception as e:
            logger.exception(f"[Jira Hook] XPASS 알림 중 시스템 오류 발생: {e}")
