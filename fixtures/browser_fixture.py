# fixtures/browser_fixture.py
import logging
from typing import Generator

import pytest
from selenium.webdriver.remote.webdriver import WebDriver

from core.webdriver import DriverFactory

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def driver(request: pytest.FixtureRequest) -> Generator[WebDriver, None, None]:
    """
    테스트 함수(Function) 단위로 독립적인 WebDriver 세션을 생성하고 반환합니다.
    
    테스트 실행 시 전달된 CLI 옵션(--browser, --headless)을 기반으로 
    DriverFactory를 통해 브라우저를 동적으로 띄우고, 테스트 종료 후 안전하게 종료(quit)합니다.
    
    Args:
        request (pytest.FixtureRequest): pytest 내장 픽스처 (CLI 옵션 접근용)
        
    Yields:
        WebDriver: 초기화 및 설정이 완료된 브라우저 인스턴스
    """
    browser_name = request.config.getoption("--browser")
    is_headless = request.config.getoption("--headless")
    
    driver_instance = None
    try:
        logger.info(f"🌐 UI 테스트용 WebDriver 초기화 시작 ({browser_name.upper()}, Headless: {is_headless})")
        driver_instance = DriverFactory.get_driver(browser_name=browser_name, is_headless=is_headless)
        
        # 테스트 함수에 WebDriver 인스턴스 전달
        yield driver_instance
        
    except Exception as e:
        logger.exception(f"[Driver Error] {browser_name.upper()} 브라우저 세션 생성 중 예외 발생: {e}")
        raise
        
    finally:
        if driver_instance:
            try:
                logger.info(f"🛑 UI 테스트 종료 및 {browser_name.upper()} 브라우저 세션 반환 (Teardown)")
                driver_instance.quit()
            except Exception as e:
                # 브라우저 종료 실패(이미 닫혀있는 등)는 치명적 에러가 아니므로 Exception 대신 Debug 처리하여 무시합니다.
                logger.debug(f"[Teardown] 브라우저 세션 정상 종료 실패 (무시 가능): {e}")