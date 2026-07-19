# core/config.py
import os
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, computed_field
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

    ⚠️ 규칙: 어떤 URL, org 이름, classroom_id 등도 이 파일 밖에서 직접 문자열로 선언하지 않습니다.
    새 값이 필요하면 이 클래스에 Field를 추가하고, 다른 코드는 반드시 `settings.xxx`로 가져다 씁니다.
    (팀원마다 자기 파일에 URL을 따로 선언하던 문제를 막기 위한 규칙입니다.)
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
    # 2. Elice 전용 설정 (SSOT)
    #    ⚠️ 아래 URL/org 값을 board_fixture.py, board_client.py 등
    #    다른 파일에 절대 복사해서 하드코딩하지 않습니다. 항상 settings.elice_env를 참조하세요.
    # ==========================================
    elice_dev_classroom_id: str = Field(
        default="22e01595-3c49-4605-8239-fe3473cd7e07", validation_alias="DEV_CLASSROOM_ID"
    )
    elice_dev_board_id: str = Field(default="1", validation_alias="DEV_BOARD_ID")
    elice_dev_others_article_id: str = Field(default="1", validation_alias="DEV_OTHERS_ARTICLE_ID")

    elice_prod_classroom_id: str = Field(
        default="a647c7c0-1e15-4196-97fd-d6e4dea84b2c", validation_alias="PROD_CLASSROOM_ID"
    )
    elice_prod_board_id: str = Field(default="10187", validation_alias="PROD_BOARD_ID")
    elice_prod_others_article_id: str = Field(default="78933", validation_alias="PROD_OTHERS_ARTICLE_ID")

    elice_api_timeout: float = Field(default=10.0, gt=0, validation_alias="ELICE_API_TIMEOUT")

    # ==========================================
    # 3. 동적/계산된 속성 (Computed Properties)
    # ==========================================

    @computed_field
    @property
    def elice_environments(self) -> dict:
        """
        Elice의 dev/prod 환경 설정 전체를 문자열 키("dev"/"prod")로 공개합니다.

        이게 Elice URL/org/classroom_id 등의 유일한 출처(SSOT)입니다.
        board_fixture.py, board_client.py 등 다른 어떤 파일에서도 이 값들을
        직접 문자열로 재선언하지 말고, 반드시 settings.elice_environments["dev"|"prod"]
        형태로 가져다 쓰세요.

        prod_learner/dev_learner/dev_educator처럼 현재 TEST_ENV와 무관하게
        특정 환경을 못 박아야 하는 픽스처가 있어서, test_env 하나로 자동 선택하는 대신
        dev/prod 두 세트를 통째로 반환합니다.

        Returns:
            dict: {"dev": {...}, "prod": {...}} — 각 값은
                REST_API_URL   — 게시판 REST API (BoardApiClient)
                AUTH_API_URL   — 로그인 (/login/pw)
                CLASSROOM_API_URL — 수업/일정 API (ScheduleAPI, ClassApi)
                ORG, CLASSROOM_ID, BOARD_ID, OTHERS_ARTICLE_ID
        """
        return {
            "dev": {
                "REST_API_URL": "https://dev-qatrack-api.dev.elicer.io",
                "AUTH_API_URL": "https://dev-qatrack-account-api.dev.elicer.io",
                "CLASSROOM_API_URL": "https://dev-qatrack-classroom-api.dev.elicer.io",
                "ORG": "academy",
                "CLASSROOM_ID": self.elice_dev_classroom_id,
                "BOARD_ID": self.elice_dev_board_id,
                "OTHERS_ARTICLE_ID": self.elice_dev_others_article_id,
            },
            "prod": {
                "REST_API_URL": "https://api-rest.elice.io",
                "AUTH_API_URL": "https://api-account.elice.io",
                "CLASSROOM_API_URL": "https://api-classroom.elice.io",
                "ORG": "qatrack",
                "CLASSROOM_ID": self.elice_prod_classroom_id,
                "BOARD_ID": self.elice_prod_board_id,
                "OTHERS_ARTICLE_ID": self.elice_prod_others_article_id,
            },
        }

    @computed_field
    @property
    def elice_env(self) -> dict:
        """
        현재 TARGET 환경변수(dev/prod, 기본 dev)에 대응하는 Elice 환경 설정 묶음.

        board_learner / board_educator처럼 "현재 지정된 환경 하나"만 있으면 되는
        픽스처를 위한 편의 프로퍼티입니다. 특정 환경을 못 박아야 하면
        elice_environments["dev"|"prod"]를 직접 쓰세요.
        """
        target = os.getenv("TARGET", "dev").lower()
        return self.elice_environments.get(target, self.elice_environments["dev"])

    @property
    def api_timeout(self) -> tuple[int, int]:
        """
        API 통신 시 적용할 (Connect Timeout, Read Timeout) 튜플을 반환합니다.

        Returns:
            tuple[int, int]: (Connect 타임아웃, Read 타임아웃)
        """
        return (5, self.api_timeout_sec)


# 전역에서 재사용할 단일 싱글톤 인스턴스 (앱 라이프사이클 내내 하나만 유지)
settings = Settings()