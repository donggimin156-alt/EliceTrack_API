# pages/login_page.py
import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from core.config import settings
from pages.base_page import BasePage
from pages.inventory_page import InventoryPage

logger = logging.getLogger(__name__)


class LoginPage(BasePage):
    """
    로그인 페이지의 UI 요소와 비즈니스/시나리오 상호작용을 정의하는 클래스.
    
    BasePage를 상속받아 공통 동작(wait, action, state)을 사용하며,
    로그인 성공/실패와 같은 페이지 단위의 시나리오 흐름을 캡슐화합니다.
    """

    PAGE_URL = "/"

    # Locators (클래스 내부에서만 사용하는 캡슐화를 위해 '_' 접두사 사용)
    _USERNAME_INPUT = (By.ID, "user-name")
    _PASSWORD_INPUT = (By.ID, "password")
    _LOGIN_BUTTON = (By.ID, "login-button")
    _ERROR_MESSAGE = (By.CSS_SELECTOR, "h3[data-test='error']")

    def __init__(self, driver: WebDriver) -> None:
        """
        LoginPage 인스턴스를 초기화합니다.
        
        Args:
            driver (WebDriver): Selenium WebDriver 인스턴스
        """
        super().__init__(driver)

    # ==========================================
    # Page Navigation & Validation
    # ==========================================
    
    def open(self) -> "LoginPage":
        """
        로그인 페이지로 이동 후 폼이 표시될 때까지 대기합니다.
        
        상수화된 URL과 Config Base URL을 조합하여 확장성을 높입니다.
        
        Returns:
            LoginPage: Method Chaining을 위한 자기 자신 인스턴스
        """
        url = f"{settings.base_url.rstrip('/')}{self.PAGE_URL}"
        self.driver.get(url)
        self.wait.for_visibility(self._LOGIN_BUTTON)
        
        logger.debug(f"[{self.__class__.__name__}] 접속 완료: {url}")
        return self

    def has_error(self, timeout: int = 3) -> bool:
        """
        에러 메시지 요소가 화면에 표시되었는지 확인합니다.
        
        Args:
            timeout (int): 최대 대기 시간(초). 기본값 3초.
            
        Returns:
            bool: 에러 메시지가 화면에 노출되었으면 True, 아니면 False
        """
        return self.state.is_visible(self._ERROR_MESSAGE, timeout=timeout)

    def get_error_message(self) -> str:
        """
        노출된 에러 메시지 텍스트를 추출합니다.
        
        Returns:
            str: 추출된 에러 메시지 문자열 (좌우 여백 제거)
        """
        return self.state.get_text(self._ERROR_MESSAGE)

    # ==========================================
    # Business Actions
    # ==========================================
    
    def fill_login_form(self, username: str, password: str) -> "LoginPage":
        """
        아이디와 비밀번호를 폼에 입력합니다.
        
        Args:
            username (str): 입력할 사용자 ID
            password (str): 입력할 비밀번호
            
        Returns:
            LoginPage: Method Chaining을 위한 자기 자신 인스턴스
        """
        self.action.input_text(self._USERNAME_INPUT, username)
        self.action.input_text(self._PASSWORD_INPUT, password)
        return self

    def click_login_button(self) -> "LoginPage":
        """
        로그인 버튼을 클릭합니다.
        
        Returns:
            LoginPage: Method Chaining을 위한 자기 자신 인스턴스
        """
        self.action.click(self._LOGIN_BUTTON)
        return self

    # ==========================================
    # Scenarios
    # ==========================================
    
    def login_success(self, username: str, password: str) -> InventoryPage:
        """
        정상 자격증명으로 로그인을 수행하고 메인 페이지로 이동합니다.
        
        단순히 객체를 반환하는 것에 그치지 않고, 다음 페이지(InventoryPage)가 
        완전히 로딩될 때까지 내부적으로 대기하여 E2E 테스트의 안정성을 보장합니다.
        
        Args:
            username (str): 올바른 사용자 ID
            password (str): 올바른 비밀번호
            
        Returns:
            InventoryPage: 로딩이 완료된 인벤토리 페이지 인스턴스
        """
        self.fill_login_form(username, password)
        self.click_login_button()
        
        inventory_page = InventoryPage(self.driver)
        inventory_page.wait_until_loaded()
        
        logger.info(f"[{self.__class__.__name__}] 로그인 액션 완료 및 인벤토리 진입 성공")
        return inventory_page

    def login_fail(self, username: str, password: str) -> "LoginPage":
        """
        비정상 자격증명으로 로그인을 시도하고 에러 메시지를 기다립니다.
        
        실패 후 에러 메시지가 화면에 노출되는 시점까지 명시적으로 대기하여 
        다음 검증(Assertion) 단계에서의 타임아웃을 방지합니다.
        
        Args:
            username (str): 잘못된 사용자 ID 또는 올바른 ID
            password (str): 잘못된 비밀번호
            
        Returns:
            LoginPage: 검증을 이어나가기 위한 자기 자신 인스턴스
        """
        self.fill_login_form(username, password)
        self.click_login_button()
        
        self.wait.for_visibility(self._ERROR_MESSAGE)
        logger.info(f"[{self.__class__.__name__}] 로그인 실패 시나리오 완료 (에러 메시지 렌더링 확인됨)")
        return self