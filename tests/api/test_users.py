# tests/api/test_users.py
import logging

import allure
import pytest
import requests

from api.endpoints.user_api import UserAPI
from builders.user_builder import UserBuilder
from services.user_service import UserService
from utils.assertions import assert_empty, assert_not_none

# 타입 힌팅을 위해 DB 클라이언트 임포트
from utils.db import DatabaseClient

logger = logging.getLogger(__name__)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture(scope="session")
def user_api(api_session: requests.Session) -> UserAPI:
    """
    UserAPI 통신 객체. 
    상태를 가지지 않는 API 클라이언트이므로 매번 생성하지 않고 session 스코프로 재사용합니다.
    """
    return UserAPI(session=api_session)


@pytest.fixture(scope="session")
def user_service(user_api: UserAPI) -> UserService:
    """
    API 클라이언트를 주입받아 비즈니스 워크플로우를 처리하는 Service 계층 객체.
    마찬가지로 session 스코프로 생성하여 메모리와 초기화 비용을 절약합니다.
    """
    return UserService(user_api=user_api)


# ==========================================
# Test Cases
# ==========================================

@pytest.mark.api
@pytest.mark.regression
@allure.epic("User Management")
@allure.feature("User Creation")
class TestCreateUser:
    """사용자 생성(POST) 도메인에 집중하는 테스트 클래스"""

    @allure.title("[TC-API-001] 사용자 생성 성공 시나리오")
    @pytest.mark.smoke
    @pytest.mark.p0
    def test_create_user_successfully(self, user_service: UserService) -> None:
        """
        유효한 데이터로 사용자를 생성하는 시나리오 테스트.
        
        세부적인 상태 코드, 스키마, 데이터 무결성 검증은 Service 계층(UserService)에서 이미 처리하므로,
        여기서는 비즈니스 흐름과 최종 식별자(ID) 발급 여부만 검증하여 책임을 명확히 분리합니다.
        """
        with allure.step("1. [Given] 테스트용 사용자 생성 데이터(DTO) 준비"):
            request_dto = UserBuilder.build_create_request()
            logger.debug(f"테스트 데이터 준비 완료: {request_dto.name}")
            
        with allure.step("2. [When] 사용자 생성 워크플로우 실행"):
            new_user = user_service.create_user(request_dto=request_dto)
            
        with allure.step("3. [Then] 최종 비즈니스 상태 검증"):
            assert_not_none(new_user.id, "발급된 사용자 ID")
            assert_not_none(new_user.createdAt, "사용자 생성 시각")

    @allure.title("[TC-API-E2E-001] 사용자 생성 후 DB 정합성 교차 검증")
    @pytest.mark.db
    @pytest.mark.e2e
    def test_create_user_and_verify_db(self, user_service: UserService, db_client: DatabaseClient) -> None:
        """
        API로 사용자를 생성하고, DB에 실제 해당 데이터가 적재되었는지 교차 검증합니다.
        (주의: ReqRes API는 가짜(Mock) API이므로 실제 연동할 사내 DB가 있어야 완벽히 통과합니다.)
        """
        # test_email = "qa_automation@example.test"
        
        with allure.step("1. [When] API를 통해 사용자 생성"):
            request_dto = UserBuilder.build_create_request()
            request_dto.name = "QA Tester"
            new_user = user_service.create_user(request_dto=request_dto)
            assert_not_none(new_user.id)

        with allure.step("2. [Then] 직접 DB를 조회하여 데이터 정합성 검증"):
            # SQL Injection을 방어하기 위해 바인딩 변수(:email)를 사용 (실제 환경 적용 시 활성화)
            # query = "SELECT id, name, status FROM users WHERE email = :email"
            # db_record = db_client.fetch_one(query, {"email": test_email})
            
            # assert_not_none(db_record, "DB에 유저 데이터가 존재해야 함")
            # assert_equal(str(db_record["id"]), str(new_user.id), "API 유저 ID와 DB 유저 ID")
            logger.info("DB 정합성 검증 로직은 실제 사내 DB 환경 구성 후 활성화해야 합니다.")
            
        with allure.step("3. [Teardown] 테스트 데이터 클렌징"):
            # delete_query = "DELETE FROM users WHERE email = :email"
            # db_client.execute_update(delete_query, {"email": test_email})
            pass


@pytest.mark.api
@pytest.mark.regression
@allure.epic("User Management")
@allure.feature("User Retrieval")
class TestGetUser:
    """사용자 조회(GET) 도메인에 집중하는 테스트 클래스"""

    @allure.title("[TC-API-002] 다수 사용자 상세 정보 조회 성공")
    @pytest.mark.p1
    @pytest.mark.parametrize(
        "target_id", 
        [1, 2, 3], 
        ids=["User_ID_1", "User_ID_2", "User_ID_3"]  # CI/CD 리포트에서 실패 대상을 식별하기 쉽게 ids 부여
    )
    def test_get_existing_user(self, user_service: UserService, target_id: int) -> None:
        """
        존재하는 사용자의 상세 정보를 정상적으로 조회하는지 검증합니다.
        데이터 정합성(요청 ID == 응답 ID)은 Service 계층에서 이미 Assert 처리됩니다.
        """
        with allure.step(f"1. [When] 사용자(ID: {target_id}) 조회 워크플로우 실행"):
            user_service.get_user(user_id=target_id)

    @allure.title("[TC-API-003] 존재하지 않는 사용자 조회 시 404 방어 검증")
    @pytest.mark.p1
    def test_get_invalid_user_returns_404(self, user_service: UserService) -> None:
        """
        존재하지 않는 사용자 조회 시 시스템이 404 Not Found 에러와 함께 
        안전하게 방어하는지(빈 페이로드 반환) 검증합니다. (Negative Scenario)
        """
        # 의도가 명확한 음수값(시스템에 존재할 수 없는 ID)을 사용하여 가독성 향상
        invalid_user_id = -1 
        
        with allure.step(f"1. [When] 존재하지 않는 사용자(ID: {invalid_user_id}) 조회 시도"):
            response = user_service.get_user_expect_not_found(user_id=invalid_user_id)
            
        with allure.step("2. [Then] 응답 페이로드가 비어있는지 검증"):
            assert_empty(response.json(), "404 에러 시 응답 페이로드")