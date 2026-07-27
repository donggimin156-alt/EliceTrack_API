# hooks/config_hook.py
import logging
import os

from _pytest.config import Config
from _pytest.config.argparsing import Parser

from core.config import PROJECT_ROOT

logger = logging.getLogger(__name__)


class DirectoryManager:
    """테스트 실행에 필요한 필수 디렉터리를 보장하는 유틸리티 관리자."""
    
    @staticmethod
    def ensure_directories() -> None:
        """
        리포트 등 프레임워크 실행에 필수적인 디렉터리를 생성합니다.
        이미 존재하는 경우 오류를 무시(exist_ok=True)합니다.
        """
        reports_dir = PROJECT_ROOT / "reports"

        os.makedirs(reports_dir, exist_ok=True)

        logger.debug(f"필수 디렉터리 보장 완료: {reports_dir}")


def pytest_addoption(parser: Parser) -> None:
    """
    테스트 실행 시 사용할 커스텀 CLI 옵션을 Pytest 파서에 추가합니다.
    
    Args:
        parser (Parser): Pytest 내장 인자 파서 객체
    """
    parser.addoption(
        "--browser", 
        action="store", 
        default="chrome", 
        choices=["chrome", "firefox", "edge"], 
        help="테스트를 실행할 브라우저를 지정합니다."
    )
    parser.addoption(
        "--env", 
        action="store", 
        default="qa", 
        choices=["dev", "qa", "stg", "prod"], 
        help="실행 대상 환경을 지정합니다."
    )
    parser.addoption(
        "--headless", 
        action="store_true", 
        default=False, 
        help="브라우저를 Headless(화면 숨김) 모드로 실행할지 여부를 지정합니다."
    )


def pytest_configure(config: Config) -> None:
    """
    Pytest 세션 초기화(Initialize) 시점에 실행되는 훅(Hook).
    
    파싱된 CLI 인자를 환경 변수로 주입하고, 프레임워크 구동에 필요한 사전 작업을 수행합니다.
    
    Args:
        config (Config): Pytest 설정 객체
    """
    test_env = config.getoption("--env")
    browser = config.getoption("--browser")
    is_headless = config.getoption("--headless")
    
    # Pydantic 설정(core.config.py)이 로드될 때 해당 환경 변수를 우선 참조하도록 강제 주입
    os.environ["TEST_ENV"] = test_env
    
    DirectoryManager.ensure_directories()
    
    # 파이프라인에서 실행 시 어떤 설정으로 시작되었는지 즉시 파악할 수 있도록 진입점 로깅
    logger.info(f"🚀 Pytest Configure 완료 | 환경: {test_env.upper()} | 브라우저: {browser.upper()} | Headless: {is_headless}")