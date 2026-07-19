# hooks/debug_hook.py
import logging

import allure
import pytest
from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger(__name__)

# 거대한 SPA 페이지 소스코드로 인해 리포트 용량이 과도해지는 것을 방지 (5MB 리미트)
MAX_HTML_SIZE = 5 * 1024 * 1024


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """
    테스트 실행 결과를 가로채어, 실패한 UI 테스트에 한해 Allure 리포트에 디버깅 정보를 첨부합니다.
    
    Args:
        item (pytest.Item): 현재 실행 중인 테스트 아이템 객체
        call (pytest.CallInfo): 테스트 실행 단계(setup, call, teardown) 정보
    """
    outcome = yield
    rep = outcome.get_result()
    
    # [수정] rep.when == "call" 조건을 추가하여, setup/teardown 단계에서의 중복 캡처를 방지합니다.
    if rep.failed and rep.when == "call" and "driver" in item.funcargs:
        driver: WebDriver = item.funcargs["driver"]
        test_name = item.name
        
        logger.info(f"🐛 테스트 실패 감지됨: {test_name} | 디버깅 아티팩트 수집 시작")
        _attach_screenshot(driver, test_name)
        _attach_url(driver, test_name)
        _attach_html(driver, test_name)
        _attach_console_log(driver, test_name)


# ==========================================
# Allure Attachment Helpers
# 각 수집 과정은 독립적으로 실행되며, 하나가 실패해도 다른 수집에 영향을 주지 않습니다.
# ==========================================

def _attach_screenshot(driver: WebDriver, test_name: str) -> None:
    """화면 스크린샷을 캡처하여 PNG 형태로 첨부합니다."""
    try:
        allure.attach(
            driver.get_screenshot_as_png(), 
            name=f"Screenshot_{test_name}", 
            attachment_type=allure.attachment_type.PNG
        )
    except Exception as e:
        logger.debug(f"[{test_name}] 스크린샷 첨부 실패 (무시됨): {e}")


def _attach_url(driver: WebDriver, test_name: str) -> None:
    """실패 시점의 현재 브라우저 URL을 첨부합니다."""
    try:
        allure.attach(
            driver.current_url, 
            name=f"URL_{test_name}", 
            attachment_type=allure.attachment_type.TEXT
        )
    except Exception as e:
        logger.debug(f"[{test_name}] URL 첨부 실패 (무시됨): {e}")


def _attach_html(driver: WebDriver, test_name: str) -> None:
    """DOM 상태 분석을 위해 현재 페이지의 HTML 소스를 첨부하되 용량을 제한합니다."""
    try:
        page_source = driver.page_source
        if len(page_source.encode("utf-8")) > MAX_HTML_SIZE:
            page_source = page_source[:MAX_HTML_SIZE] + "\n... [TRUNCATED DUE TO SIZE]"
            
        allure.attach(
            page_source, 
            name=f"HTML_{test_name}", 
            attachment_type=allure.attachment_type.HTML
        )
    except Exception as e:
        logger.debug(f"[{test_name}] HTML 첨부 실패 (무시됨): {e}")


def _attach_console_log(driver: WebDriver, test_name: str) -> None:
    """브라우저 개발자 도구의 콘솔(Console) 로그를 추출하여 첨부합니다."""
    try:
        # 브라우저가 로그 기능을 지원하는지(Chrome, Edge 등) Capability 우선 검증
        if "browser" in driver.log_types:
            browser_logs = driver.get_log("browser")
            if browser_logs:
                log_str = "\n".join([f"{log['level']}: {log['message']}" for log in browser_logs])
                allure.attach(
                    log_str, 
                    name=f"Console_{test_name}", 
                    attachment_type=allure.attachment_type.TEXT
                )
    except Exception as e:
        logger.debug(f"[{test_name}] Console 로그 첨부 실패 (미지원 브라우저 등): {e}")