# pages/base/waiter.py
import logging

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.base.locator import Locator, format_locator

logger = logging.getLogger(__name__)


class SmartWaiter:
    """
    DOM 대기(Synchronization) 로직만을 전담하는 컴포넌트.
    
    네트워크 지연이나 렌더링 속도 차이로 인한 Flaky 테스트(간헐적 실패)를 방지하기 위해,
    모든 UI 액션 이전에 명시적 대기(Explicit Wait)를 수행합니다.
    """

    def __init__(self, driver: WebDriver, default_timeout: int) -> None:
        """
        SmartWaiter 인스턴스를 초기화합니다.
        
        Args:
            driver (WebDriver): Selenium WebDriver 인스턴스
            default_timeout (int): 전역 기본 타임아웃(초) 설정
        """
        self.driver = driver
        self.timeout = default_timeout

    def get_wait(self, timeout: int | None = None, poll_frequency: float = 0.2) -> WebDriverWait:
        """
        조건 충족을 폴링(Polling)하며 대기하는 WebDriverWait 인스턴스를 생성합니다.
        
        Args:
            timeout (int | None): 대기할 최대 시간(초). None일 경우 전역 기본값을 사용합니다.
            poll_frequency (float): DOM 상태를 재확인하는 주기(초). (기본값: 0.2초)
            
        Returns:
            WebDriverWait: 대기 처리를 수행할 수 있는 Wait 객체
        """
        wait_time = self.timeout if timeout is None else timeout
        return WebDriverWait(self.driver, wait_time, poll_frequency=poll_frequency)

    def for_presence(self, locator: Locator, timeout: int | None = None) -> WebElement:
        """
        요소가 DOM 트리에 존재할 때까지 대기합니다. (화면 표시 여부와 무관)
        
        Args:
            locator (Locator): 대상 요소의 로케이터 튜플
            timeout (int | None): 최대 대기 시간
            
        Returns:
            WebElement: 대기가 완료된 DOM 요소 객체
            
        Raises:
            TimeoutException: 지정된 시간 내에 요소가 DOM에 나타나지 않은 경우
        """
        try:
            return self.get_wait(timeout).until(EC.presence_of_element_located(locator))
        except TimeoutException:
            logger.error(f"[Timeout] DOM 존재 대기 실패: {format_locator(locator)}")
            raise

    def for_visibility(self, locator: Locator, timeout: int | None = None) -> WebElement:
        """
        요소가 화면에 렌더링되어 사용자에게 보일 때까지 대기합니다.
        
        Args:
            locator (Locator): 대상 요소의 로케이터 튜플
            timeout (int | None): 최대 대기 시간
            
        Returns:
            WebElement: 화면에 표시된 요소 객체
            
        Raises:
            TimeoutException: 지정된 시간 내에 요소가 화면에 표시되지 않은 경우
        """
        try:
            return self.get_wait(timeout).until(EC.visibility_of_element_located(locator))
        except TimeoutException:
            logger.error(f"[Timeout] 화면 표시 대기 실패: {format_locator(locator)}")
            raise

    def for_clickable(self, locator: Locator, timeout: int | None = None) -> WebElement:
        """
        요소가 화면에 표시되고, 비활성화(disabled)되지 않아 클릭 가능한 상태일 때까지 대기합니다.
        
        Args:
            locator (Locator): 대상 요소의 로케이터 튜플
            timeout (int | None): 최대 대기 시간
            
        Returns:
            WebElement: 클릭 가능한 요소 객체
            
        Raises:
            TimeoutException: 지정된 시간 내에 요소가 클릭 가능해지지 않은 경우
        """
        try:
            return self.get_wait(timeout).until(EC.element_to_be_clickable(locator))
        except TimeoutException:
            logger.error(f"[Timeout] 클릭 가능 상태 대기 실패: {format_locator(locator)}")
            raise

    def for_invisibility(self, locator: Locator, timeout: int | None = None) -> bool:
        """
        로딩 스피너, 팝업 등 특정 요소가 화면에서 사라지거나 DOM에서 삭제될 때까지 대기합니다.
        
        Args:
            locator (Locator): 대상 요소의 로케이터 튜플
            timeout (int | None): 최대 대기 시간
            
        Returns:
            bool: 요소가 성공적으로 사라지면 True
            
        Raises:
            TimeoutException: 지정된 시간 내에 요소가 사라지지 않은 경우
        """
        try:
            return self.get_wait(timeout).until(EC.invisibility_of_element_located(locator))
        except TimeoutException:
            logger.error(f"[Timeout] 요소 사라짐 대기 실패: {format_locator(locator)}")
            raise

    def for_url_contains(self, url_fragment: str, timeout: int | None = None) -> bool:
        """
        현재 브라우저의 URL에 특정 문자열(Fragment)이 포함될 때까지 대기합니다.
        주로 페이지 이동/전환 검증 시 사용합니다.
        
        Args:
            url_fragment (str): 포함되어야 할 부분 URL 문자열
            timeout (int | None): 최대 대기 시간
            
        Returns:
            bool: 지정한 문자열이 URL에 포함되면 True
            
        Raises:
            TimeoutException: 지정된 시간 내에 해당 문자열이 URL에 나타나지 않은 경우
        """
        try:
            return self.get_wait(timeout).until(EC.url_contains(url_fragment))
        except TimeoutException:
            logger.error(f"[Timeout] URL '{url_fragment}' 포함 대기 실패")
            raise