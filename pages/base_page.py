# pages/base_page.py
import logging
from datetime import datetime

from selenium.webdriver.remote.webdriver import WebDriver

from core.config import settings
from pages.base.inspector import UIInspector
from pages.base.interactor import UIInteractor
from pages.base.waiter import SmartWaiter

logger = logging.getLogger(__name__)


class BasePage:
    """
    컴포지션(Composition) 패턴이 적용된 최상위 UI 페이지 객체.
    
    모든 Page Object 클래스는 이 클래스를 상속받아 직관적인 
    DSL(wait, action, state) API를 기본적으로 제공받습니다.
    """

    def __init__(self, driver: WebDriver) -> None:
        """
        BasePage 인스턴스를 초기화하고 핵심 UI 컴포넌트를 조립합니다.
        
        Args:
            driver (WebDriver): Selenium WebDriver 인스턴스
        """
        self.driver = driver
        
        # 타임아웃 전역 설정 로드
        timeout = settings.ui_timeout
        
        # 관심사가 분리된 핵심 컴포넌트(동기화, 액션, 상태검증) 조립
        self.wait = SmartWaiter(self.driver, timeout)
        self.action = UIInteractor(self.driver, self.wait)
        self.state = UIInspector(self.driver, self.wait)

    def take_screenshot(self, filename_prefix: str = "screenshot") -> str:
        """
        현재 브라우저 화면의 스크린샷을 캡처하여 파일로 저장합니다.
        
        Args:
            filename_prefix (str): 저장할 파일명의 접두사 (기본값: "screenshot")
            
        Returns:
            str: 저장된 스크린샷 파일의 전체 이름
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.png"
        
        self.driver.save_screenshot(filename)
        
        # 로깅 시 self.__class__.__name__을 명시하여 어떤 하위 페이지 객체에서 캡처했는지 추적성을 유지합니다.
        logger.info(f"[{self.__class__.__name__}] 스크린샷 저장 완료: {filename}")
        
        return filename