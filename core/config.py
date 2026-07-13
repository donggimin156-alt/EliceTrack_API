# core/config.py
import os
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 환경 변수와 설정을 관리하는 순수 데이터(Configuration) 모듈이므로 logger를 선언하지 않습니다.

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 시스템 환경 변수로 전역 등록 (하위 프로세스 및 호환성 유지)
load_dotenv(PROJECT_ROOT / ".env")


class EnvType(str, Enum):
    """실무 운영 환경을 명확히 제한하는 Enum 클래스."""
    DEV = "dev"
    QA = "qa"
    STG = "stg"
    PROD = "prod"


class Settings(BaseSettings):
    """
    프레임워크 전역 설정 관리 클래스 (Pydantic V2 기반).
    
    기존 env_config.py와 config.py를 통합하여 단일 진실 공급원(SSOT, Single Source of Truth)을 제공합니다.
    """
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # ==========================================
    # 1. 실행 환경 및 타임아웃
    # ==========================================
    test_env: EnvType = Field(default=EnvType.QA, validation_alias="TEST_ENV")

    ui_timeout: int = Field(default=15, gt=0, le=300, validation_alias="UI_TIMEOUT")
    api_timeout_sec: int = Field(default=10, gt=0, le=120, validation_alias="API_TIMEOUT")
    page_load_timeout: int = Field(default=30, gt=0, le=300, validation_alias="PAGE_LOAD_TIMEOUT")
    script_timeout: int = Field(default=30, gt=0, le=120, validation_alias="SCRIPT_TIMEOUT")

    # ==========================================
    # 2. 보안 데이터 (인증, API 키)
    # ==========================================
    global_admin_user: str = Field(default="", validation_alias="GLOBAL_ADMIN_USER")
    global_admin_pass: SecretStr = Field(default=SecretStr(""), validation_alias="GLOBAL_ADMIN_PASS")
    reqres_api_key: SecretStr | None = Field(default=None, validation_alias="REQRES_API_KEY")

    # ==========================================
    # 3. 동적/계산된 속성 (Computed Properties)
    # ==========================================
    
    @computed_field
    @property
    def base_url(self) -> str:
        """현재 실행 환경(test_env)에 맞는 UI Base URL을 반환합니다."""
        urls = {
            EnvType.DEV: "https://dev.saucedemo.com",
            EnvType.QA: "https://www.saucedemo.com",
            EnvType.STG: "https://stg.saucedemo.com",
            EnvType.PROD: "https://www.saucedemo.com"
        }
        return urls[self.test_env]

    @computed_field
    @property
    def api_base_url(self) -> str:
        """현재 실행 환경에 맞는 API Base URL을 반환합니다."""
        urls = {
            EnvType.DEV: "https://api-dev.saucedemo.com",
            EnvType.QA: "https://reqres.in",
            EnvType.STG: "https://api-stg.saucedemo.com",
            EnvType.PROD: "https://api.saucedemo.com"
        }
        return urls[self.test_env]

    @property
    def api_timeout(self) -> tuple[int, int]:
        """
        API 통신 시 적용할 (Connect Timeout, Read Timeout) 튜플을 반환합니다.
        
        Returns:
            tuple[int, int]: (Connect 타임아웃, Read 타임아웃)
        """
        return (5, self.api_timeout_sec)

    @property
    def api_key(self) -> str | None:
        """SecretStr로 보호된 API 키 값을 안전하게 추출하여 반환합니다."""
        if not self.reqres_api_key:
            return None
        val = self.reqres_api_key.get_secret_value()
        return val if val else None

    @property
    def admin_password(self) -> str:
        """SecretStr로 보호된 어드민 비밀번호를 반환합니다."""
        return self.global_admin_pass.get_secret_value()


# 전역에서 재사용할 단일 싱글톤 인스턴스 (앱 라이프사이클 내내 하나만 유지)
settings = Settings()