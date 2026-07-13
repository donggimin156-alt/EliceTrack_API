# tests/ui/test_login.py
import logging

import allure
import pytest
from selenium.webdriver.remote.webdriver import WebDriver

from core.data_loader import DataLoader
from pages.login_page import LoginPage
from utils.assertions import assert_contains, assert_true

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def login_page(driver: WebDriver) -> LoginPage:
    """
    각 테스트 함수에서 독립적으로 사용할 LoginPage 객체를 주입하는 픽스처.
    """
    return LoginPage(driver)


@pytest.mark.ui
@allure.epic("Authentication")
@allure.feature("Login")
class TestLogin:
    """로그인 도메인과 관련된 UI 테스트 케이스 그룹"""

    @allure.title("[TC-UI-001] 유효한 계정으로 로그인 성공 및 페이지 전환 검증")
    @pytest.mark.smoke
    @pytest.mark.p0
    def test_valid_login_success(self, login_page: LoginPage) -> None:
        """
        유효한 자격 증명으로 로그인 시 메인(Inventory) 페이지로 정상 진입하는지 검증합니다.
        테스트 코드는 비즈니스 흐름과 검증(Assertion)에만 집중합니다.
        """
        with allure.step("1. [Given] 테스트용 계정 데이터 로드"):
            credentials = DataLoader.get_test_credentials("standard")
            logger.debug(f"테스트 계정 로드 완료: {credentials['username']}")

        with allure.step("2. [When] 로그인 페이지 접속"):
            login_page.open()

        with allure.step("3. [When] 로그인 워크플로우 수행 및 페이지 전환 대기"):
            # login_success 내부에서 인벤토리 페이지가 완전히 로드될 때까지 대기합니다.
            inventory_page = login_page.login_success(credentials["username"], credentials["password"])

        with allure.step("4. [Then] 인벤토리 페이지 전환 성공 검증"):
            # 파이썬 내장 assert 대신 공통 유틸리티를 사용하여 일관된 로깅과 명확한 실패 메시지를 확보합니다.
            assert_true(
                inventory_page.is_loaded(), 
                "로그인 성공 후 인벤토리 페이지가 정상적으로 로드되어야 합니다."
            )

    @allure.title("[TC-UI-002] 비정상 계정 로그인 시 에러 메시 노출 검증")
    @pytest.mark.p1
    @pytest.mark.parametrize("username, password, expected_error", [
        ("standard_user", "wrong_password", "Epic sadface: Username and password do not match"),
        ("locked_out_user", "secret_sauce", "Epic sadface: Sorry, this user has been locked out."),
        ("", "secret_sauce", "Epic sadface: Username is required")
    ])
    def test_invalid_login_shows_error(
        self, 
        login_page: LoginPage, 
        username: str, 
        password: str, 
        expected_error: str
    ) -> None:
        """
        다양한 비정상 조건에서 알맞은 에러 메시지가 노출되는지 데이터 주도(Data-Driven) 방식으로 검증합니다.
        """
        with allure.step("1. [Given] 로그인 페이지 접속"):
            login_page.open()
            
        with allure.step(f"2. [When] 비정상 데이터 입력 및 로그인 시도 (ID: '{username}')"):
            # login_fail 내부에서 에러 팝업이 렌더링될 때까지 안전하게 대기합니다.
            login_page.login_fail(username, password)
            
        with allure.step("3. [Then] 에러 메시지 노출 및 텍스트 검증"):
            assert_true(
                login_page.has_error(), 
                "에러 메시지 팝업이 화면에 노출되어야 합니다."
            )
            
            error_message = login_page.get_error_message()
            assert_contains(
                expected_error, 
                error_message, 
                "노출된 에러 메시지 텍스트"
            )
            logger.debug(f"에러 메시지 검증 통과: {error_message}")