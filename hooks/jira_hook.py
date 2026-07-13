# hooks/jira_hook.py
import logging
import os
from typing import Generator

import pytest
from _pytest.reports import TestReport

logger = logging.getLogger(__name__)

# 중복 이슈 생성 억제를 위한 인메모리 캐시 셋 (Deduplication)
_reported_issues: set[str] = set()


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
        logger.info(f"🎫 Jira 자동 버그 티켓 생성 트리거됨: {item.name}")
        
        try:
            # Lazy Import: 모듈 순환 참조를 방지하고, Jira 기능이 꺼져있을 때 불필요한 패키지 로딩을 막습니다.
            from utils.jira import JiraClient
            
            jira = JiraClient()
            jira.create_bug_ticket(test_name=item.name, error_trace=error_trace)
        except Exception as e:
            logger.exception(f"[Jira Hook] 버그 티켓 자동 생성 중 시스템 오류 발생: {e}")