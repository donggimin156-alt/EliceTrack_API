# pages/base/interactor.py
import logging
import sys
import time

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver

from pages.base.locator import Locator, format_locator
from pages.base.waiter import SmartWaiter

logger = logging.getLogger(__name__)


class UIInteractor:
    """
    클릭, 텍스트 입력, 스크롤 등 UI 액션을 전담하는 컴포넌트.
    
    메서드 체이닝(Method Chaining)을 지원하여 Fluent DSL 형태로 테스트 코드를 작성할 수 있도록
    대부분의 액션 메서드가 자기 자신(self)을 반환합니다.
    """

    def __init__(self, driver: WebDriver, waiter: SmartWaiter) -> None:
        """
        UIInteractor 인스턴스를 초기화합니다.
        
        Args:
            driver (WebDriver): Selenium WebDriver 인스턴스
            waiter (SmartWaiter): 동기화 대기를 처리하는 SmartWaiter 객체
        """
        self.driver = driver
        self.waiter = waiter

    def click(self, locator: Locator, retries: int = 3) -> "UIInteractor":
        """
        주어진 요소가 클릭 가능해질 때까지 대기한 후 클릭합니다.
        
        화면 렌더링 지연(Stale)이나 다른 요소에 가려짐(Intercept) 오류를 방어하기 위해 
        지수 백오프(Exponential Backoff) 기반의 재시도를 수행합니다.
        
        Args:
            locator (Locator): 클릭할 대상 요소의 로케이터 튜플
            retries (int): 실패 시 최대 재시도 횟수 (기본값: 3)
            
        Returns:
            UIInteractor: Method Chaining을 위한 자기 자신 인스턴스
            
        Raises:
            Exception: 최대 재시도 횟수를 초과하여 클릭에 실패한 경우
        """
        fmt_locator = format_locator(locator)
        for attempt in range(1, retries + 1):
            try:
                element = self.waiter.for_clickable(locator)
                element.click()
                logger.debug(f"클릭 성공: {fmt_locator}")
                return self
            except (
                StaleElementReferenceException, 
                ElementClickInterceptedException, 
                ElementNotInteractableException, 
                TimeoutException
            ) as e:
                if attempt == retries:
                    logger.error(f"[Retry Failed] {retries}회 실패: {fmt_locator} | 사유: {e.__class__.__name__}")
                    raise
                
                sleep_time = 0.2 * (2 ** (attempt - 1))
                logger.warning(f"클릭 재시도 ({attempt}/{retries}) 대기 {sleep_time}s: {fmt_locator}")
                time.sleep(sleep_time)
        return self

    def js_click(self, locator: Locator) -> "UIInteractor":
        """
        일반적인 클릭이 불가능한 요소(팝업에 가려짐 등)를 JavaScript를 이용해 강제로 클릭합니다.
        
        Args:
            locator (Locator): 클릭할 대상 요소의 로케이터 튜플
            
        Returns:
            UIInteractor: Method Chaining을 위한 자기 자신 인스턴스
        """
        element = self.waiter.for_presence(locator)
        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", element)
        time.sleep(0.1)
        self.driver.execute_script("arguments[0].click();", element)
        
        logger.debug(f"JS 클릭 완료: {format_locator(locator)}")
        return self

    def clear(self, locator: Locator) -> "UIInteractor":
        """
        입력 필드의 텍스트를 초기화합니다.
        단순 `.clear()`가 동작하지 않는 SPA(React, Vue 등) 환경을 완벽히 방어하기 위해 
        키보드 단축키 전체 선택 삭제 및 JS 값 초기화까지 병행합니다.
        
        Args:
            locator (Locator): 초기화할 입력 필드의 로케이터 튜플
            
        Returns:
            UIInteractor: Method Chaining을 위한 자기 자신 인스턴스
        """
        element = self.waiter.for_visibility(locator)
        element.clear()
        
        # 1차 방어: SPA 폼 상태 동기화 강제 초기화 (Ctrl+A / Cmd+A -> Backspace)
        if element.get_attribute("value"):
            ctrl_cmd = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL
            element.send_keys(ctrl_cmd + "a")
            element.send_keys(Keys.BACKSPACE)
            
        # 2차 방어: 최후의 수단으로 JS 속성 강제 빈 값 처리
        if element.get_attribute("value"):
            self.driver.execute_script("arguments[0].value = '';", element)
            
        logger.debug(f"입력 필드 초기화 완료: {format_locator(locator)}")
        return self

    def input_text(self, locator: Locator, text: str) -> "UIInteractor":
        """
        입력 필드를 깨끗이 초기화한 후 지정한 텍스트를 안전하게 입력합니다.
        
        Args:
            locator (Locator): 텍스트를 입력할 대상 요소의 로케이터 튜플
            text (str): 입력할 텍스트 문자열
            
        Returns:
            UIInteractor: Method Chaining을 위한 자기 자신 인스턴스
        """
        self.clear(locator)
        element = self.waiter.for_visibility(locator)
        element.send_keys(text)
        
        # 보안을 위해 입력한 text 자체를 남기기보다는 대상 요소만 로깅합니다.
        logger.debug(f"텍스트 입력 완료: {format_locator(locator)}")
        return self

    def scroll_to(self, locator: Locator) -> "UIInteractor":
        """
        특정 요소가 화면 중앙에 오도록 부드럽게 스크롤합니다.
        
        Args:
            locator (Locator): 스크롤하여 화면에 표시할 요소의 로케이터 튜플
            
        Returns:
            UIInteractor: Method Chaining을 위한 자기 자신 인스턴스
        """
        element = self.waiter.for_presence(locator)
        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        
        logger.debug(f"요소로 스크롤 완료: {format_locator(locator)}")
        return self

    def hover(self, locator: Locator) -> "UIInteractor":
        """
        특정 요소 위에 마우스 커서를 올립니다(Hover).
        
        Args:
            locator (Locator): Hover할 대상 요소의 로케이터 튜플
            
        Returns:
            UIInteractor: Method Chaining을 위한 자기 자신 인스턴스
        """
        element = self.waiter.for_visibility(locator)
        ActionChains(self.driver).move_to_element(element).perform()
        
        logger.debug(f"마우스 Hover 완료: {format_locator(locator)}")
        return self