# core/webdriver/factory.py
import logging
import os

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

from core.config import PROJECT_ROOT, settings
from core.webdriver.enums import BrowserType
from core.webdriver.options_builder import (
    ChromeOptionsBuilder,
    EdgeOptionsBuilder,
    FirefoxOptionsBuilder,
)

logger = logging.getLogger(__name__)


class DriverFactory:
    """
    개방-폐쇄 원칙(OCP)이 적용된 WebDriver 생성 팩토리 클래스.
    
    새로운 브라우저가 추가되더라도 _REGISTRY 매핑만 추가하면 기존 코드는 수정되지 않습니다.
    """

    # 브라우저별 (WebDriver 클래스, Option 빌더 객체) 매핑 레지스트리
    _REGISTRY = {
        BrowserType.CHROME: (webdriver.Chrome, ChromeOptionsBuilder()),
        BrowserType.FIREFOX: (webdriver.Firefox, FirefoxOptionsBuilder()),
        BrowserType.EDGE: (webdriver.Edge, EdgeOptionsBuilder()),
    }

    @classmethod
    def get_driver(cls, browser_name: str = "chrome", is_headless: bool = True) -> WebDriver:
        """
        요청된 브라우저 타입에 맞는 WebDriver 인스턴스를 생성하여 반환합니다.
        
        Args:
            browser_name (str): 실행할 브라우저 이름 (기본값: "chrome")
            is_headless (bool): Headless 모드 실행 여부 (기본값: True)
            
        Returns:
            WebDriver: 설정이 완료된 Selenium WebDriver 인스턴스
            
        Raises:
            ValueError: 지원하지 않는 브라우저 이름이 입력된 경우
        """
        try:
            browser_type = BrowserType(browser_name.lower())
        except ValueError:
            raise ValueError(f"[Error] 지원하지 않는 브라우저입니다: {browser_name}")

        grid_url = os.getenv("GRID_URL")
        download_dir = cls._setup_download_directory()

        # 레지스트리에서 드라이버 클래스와 옵션 빌더를 동적으로 가져옵니다.
        driver_class, options_builder = cls._REGISTRY[browser_type]
        options = options_builder.build(is_headless, download_dir)

        # 1. 원격 Grid 환경 실행
        if grid_url:
            logger.info(f"[GRID] {browser_type.name} 실행 | URL: {grid_url}")
            options.set_capability("se:name", f"QA-Auto-{browser_type.name}")
            driver = webdriver.Remote(command_executor=grid_url, options=options)
            try:
                driver.maximize_window()
            except WebDriverException as e:
                # pass 대신 debug로 흔적을 남겨 완전히 묻히는 것을 방지
                logger.debug(f"원격 브라우저 창 최대화 실패 (무시됨): {e}")
                
        # 2. 로컬 환경 실행
        else:
            logger.info(f"[LOCAL] {browser_type.name} 실행 | Headless: {is_headless}")
            driver = driver_class(options=options)
            # Headless가 아닐 때만 화면을 최대화하여 불필요한 연산을 줄임
            if not is_headless:
                try:
                    driver.maximize_window()
                except WebDriverException as e:
                    logger.debug(f"로컬 브라우저 창 최대화 실패 (무시됨): {e}")

        cls._apply_global_timeouts(driver)
        return driver

    @staticmethod
    def _setup_download_directory() -> str:
        """
        병렬 테스트(xdist) 환경에서 워커별로 충돌 없는 격리된 다운로드 경로를 생성합니다.
        
        Returns:
            str: 생성된 워커 전용 다운로드 디렉터리의 절대 경로
        """
        worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
        download_dir = str(PROJECT_ROOT / "downloads" / worker_id)
        os.makedirs(download_dir, exist_ok=True)
        return download_dir

    @staticmethod
    def _apply_global_timeouts(driver: WebDriver) -> None:
        """
        전역 Config 정책에 맞춰 브라우저 글로벌 타임아웃을 강제합니다.
        
        Args:
            driver (WebDriver): 타임아웃을 적용할 WebDriver 인스턴스
        """
        driver.set_page_load_timeout(settings.page_load_timeout)
        driver.set_script_timeout(settings.script_timeout)
        
        # [중요] 암묵적 대기(Implicit Wait)는 SmartWaiter의 명시적 대기(Explicit Wait)와 
        # 혼용될 경우 예상치 못한 지연(Timeout 충돌)을 유발하므로 반드시 0으로 설정합니다.
        driver.implicitly_wait(0)