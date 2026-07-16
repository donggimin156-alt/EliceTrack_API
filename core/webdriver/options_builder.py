# core/webdriver/options_builder.py
from abc import ABC, abstractmethod

from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions

# 본 모듈은 WebDriver 옵션 객체를 단순 조립(Build)하여 반환하는 팩토리 성격의 클래스입니다.
# 부작용(Side Effect)이 없고 상태를 변경하지 않으므로 logger를 선언하지 않습니다.


class BrowserOptionsBuilder(ABC):
    """
    브라우저별 옵션 생성을 위한 추상 빌더 인터페이스.
    
    새로운 브라우저 지원이 필요할 경우, 이 인터페이스를 상속받아 구현합니다.
    """
    
    @abstractmethod
    def build(self, is_headless: bool, download_dir: str) -> ChromeOptions | FirefoxOptions | EdgeOptions:
        """
        브라우저 실행에 필요한 옵션(Options) 객체를 생성합니다.
        
        Args:
            is_headless (bool): 화면 없이 백그라운드에서 실행할지 여부
            download_dir (str): 파일 다운로드가 저장될 절대 경로
            
        Returns:
            브라우저별 전용 Options 객체
        """
        pass


class ChromeOptionsBuilder(BrowserOptionsBuilder):
    """Chrome 브라우저 전용 성능 최적화 및 안정성 옵션 빌더."""
    
    def build(self, is_headless: bool, download_dir: str) -> ChromeOptions:
        options = ChromeOptions()
        # DOM Tree가 구성되면 리소스(이미지 등) 로딩을 기다리지 않고 즉시 제어권을 반환받아 테스트 속도를 높입니다.
        options.page_load_strategy = "eager"
        
        if is_headless:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")

        # CI/CD 및 Docker 환경(Linux)에서의 메모리 크래시 및 권한 문제를 방지하는 필수 엔터프라이즈 옵션
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument("--ignore-certificate-errors")
        
        # 봇 탐지(Bot Detection)를 우회하기 위한 자동화 식별자 제거 옵션
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--lang=en-US")

        # 다운로드 경로 지정 및 브라우저 알림(Notification) 차단 설정
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "safebrowsing.enabled": True,
            "profile.default_content_setting_values.notifications": 2
        }
        options.add_experimental_option("prefs", prefs)
        return options


class FirefoxOptionsBuilder(BrowserOptionsBuilder):
    """Firefox 브라우저 전용 옵션 및 프로필 셋업 빌더."""
    
    def build(self, is_headless: bool, download_dir: str) -> FirefoxOptions:
        options = FirefoxOptions()
        options.page_load_strategy = "eager"
        
        if is_headless:
            options.add_argument("--headless")
            
        options.add_argument("--width=1920")
        options.add_argument("--height=1080")
        
        # Firefox 전용 파일 다운로드 자동화 프로필 설정 (OS 팝업 방지)
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.dir", download_dir)
        options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf, text/csv, application/zip")
        options.set_preference("dom.webnotifications.enabled", False)
        
        return options


class EdgeOptionsBuilder(BrowserOptionsBuilder):
    """Edge 브라우저 전용 옵션 빌더."""
    
    def build(self, is_headless: bool, download_dir: str) -> EdgeOptions:
        options = EdgeOptions()
        options.page_load_strategy = "eager"
        
        if is_headless:
            options.add_argument("--headless=new")
            
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Chromium 기반인 Edge의 다운로드 및 알림 차단 프로필 설정
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "profile.default_content_setting_values.notifications": 2
        }
        options.add_experimental_option("prefs", prefs)
        return options