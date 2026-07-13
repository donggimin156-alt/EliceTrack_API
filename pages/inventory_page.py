# pages/inventory_page.py
import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from pages.base_page import BasePage

logger = logging.getLogger(__name__)


class InventoryPage(BasePage):
    """
    로그인 성공 후 이동하는 인벤토리(메인) 페이지 모델.
    
    해당 페이지 내의 기능(상품 정렬, 필터, 장바구니 추가 등)을 캡슐화합니다.
    BasePage를 상속받아 공통 UI 액션(wait, action, state)을 그대로 활용합니다.
    """
    
    PAGE_URL = "/inventory.html"
    
    # Locators (클래스 내부에서만 사용하는 캡슐화를 위해 '_' 접두사 사용)
    _INVENTORY_CONTAINER = (By.ID, "inventory_container")
    _SHOPPING_CART = (By.CLASS_NAME, "shopping_cart_link")

    def __init__(self, driver: WebDriver) -> None:
        """
        InventoryPage 인스턴스를 초기화합니다.
        
        Args:
            driver (WebDriver): Selenium WebDriver 인스턴스
        """
        super().__init__(driver)

    def is_loaded(self) -> bool:
        """
        페이지가 정상적으로 로드되었는지 검증합니다.
        
        단순 URL 확인을 넘어, 핵심 컴포넌트(인벤토리 컨테이너)가 
        화면에 정상적으로 렌더링되었는지 종합적으로 검증합니다.
        
        Returns:
            bool: 지정된 URL에 위치하고 주요 컨테이너가 화면에 표시되면 True
        """
        is_url_correct = self.PAGE_URL in self.driver.current_url
        is_container_visible = self.state.is_visible(self._INVENTORY_CONTAINER)
        
        return is_url_correct and is_container_visible

    def wait_until_loaded(self) -> "InventoryPage":
        """
        페이지 전환 시 핵심 UI 요소가 모두 표시될 때까지 명시적으로 대기합니다.
        
        Returns:
            InventoryPage: Method Chaining을 위한 자기 자신 인스턴스
        """
        self.wait.for_url_contains(self.PAGE_URL)
        self.wait.for_visibility(self._INVENTORY_CONTAINER)
        
        # BasePage에서 self.logger 의존성을 제거했으므로, 모듈 로거를 사용하여 기록합니다.
        logger.debug(f"[{self.__class__.__name__}] 주요 요소 렌더링 완료")
        
        return self