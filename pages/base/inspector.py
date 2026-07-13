# pages/base/inspector.py
import logging

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC

from pages.base.locator import Locator
from pages.base.waiter import SmartWaiter

logger = logging.getLogger(__name__)


class UIInspector:
    """
    DOM 상태 확인(is_visible) 및 데이터 추출(get_text)을 전담하는 컴포넌트.
    
    요소와 상호작용하기 전에 요소가 화면에 존재하는지, 특정 텍스트를 포함하고 있는지 
    확인하는 상태 검증(Inspection) 역할을 수행합니다.
    """

    def __init__(self, driver: WebDriver, waiter: SmartWaiter) -> None:
        """
        UIInspector 인스턴스를 초기화합니다.
        
        Args:
            driver (WebDriver): Selenium WebDriver 인스턴스
            waiter (SmartWaiter): 동기화 대기를 처리하는 SmartWaiter 객체
        """
        self.driver = driver
        self.waiter = waiter

    def get_text(self, locator: Locator) -> str:
        """
        주어진 로케이터 요소의 텍스트를 추출합니다.
        일반 텍스트뿐만 아니라 Input, Textarea의 입력값(value) 추출도 대응합니다.
        
        Args:
            locator (Locator): 추출할 대상 요소의 로케이터 튜플
            
        Returns:
            str: 추출된 텍스트 문자열 (좌우 여백이 제거됨)
        """
        element = self.waiter.for_visibility(locator)
        text = element.text
        
        if not text:
            # Input, Textarea 등 일반적인 text 속성으로 잡히지 않는 경우 Fallback 처리
            text = element.get_attribute("value") or element.get_attribute("textContent") or ""
            
        return text.strip()

    def find_elements(self, locator: Locator, timeout: int | None = None) -> list[WebElement]:
        """
        조건에 맞는 모든 DOM 요소를 리스트 형태로 반환합니다.
        
        Args:
            locator (Locator): 찾을 요소들의 로케이터 튜플
            timeout (int | None): 최대 대기 시간(초). 기본값은 글로벌 타임아웃
            
        Returns:
            list[WebElement]: 찾은 요소 객체 리스트. (발견하지 못하면 빈 리스트 반환)
        """
        try:
            return self.waiter.get_wait(timeout).until(EC.presence_of_all_elements_located(locator))
        except TimeoutException:
            logger.debug(f"요소를 찾을 수 없어 빈 리스트를 반환합니다: {locator}")
            return []

    def is_visible(self, locator: Locator, timeout: int = 3) -> bool:
        """
        요소가 화면에 렌더링되어 표시(Visible)되는지 빠르게 확인 후 Bool을 반환합니다.
        에러 팝업 노출 여부 등 분기 처리가 필요할 때 유용하게 쓰입니다.
        
        Args:
            locator (Locator): 확인할 요소의 로케이터 튜플
            timeout (int): 최대 대기 시간(초). (기본값: 3초 - 빠른 상태 확인용)
            
        Returns:
            bool: 요소가 화면에 표시되면 True, 아니면 False
        """
        try:
            self.waiter.get_wait(timeout).until(EC.visibility_of_element_located(locator))
            return True
        except TimeoutException:
            return False

    def exists(self, locator: Locator, timeout: int = 0) -> bool:
        """
        요소가 DOM 트리에 존재하는지 확인합니다. (화면 표시 여부와 무관)
        화면 밖의 요소(스크롤 필요)나 hidden 상태인 요소를 확인할 때 사용합니다.
        
        Args:
            locator (Locator): 확인할 요소의 로케이터 튜플
            timeout (int): 최대 대기 시간(초). (기본값: 0초 - 즉시 확인)
            
        Returns:
            bool: 요소가 DOM에 존재하면 True, 아니면 False
        """
        try:
            self.waiter.get_wait(timeout).until(EC.presence_of_element_located(locator))
            return True
        except TimeoutException:
            return False