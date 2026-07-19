# services/user_service.py
import logging
from typing import Any, TypeVar

import allure
from pydantic import BaseModel
from requests import Response

from api.endpoints.user_api import UserAPI
from api.schemas.user_dto import CreateUserRequest, CreateUserResponse, GetUserResponse
from api.schemas.user_schema import UserSchemas
from utils.assertions import assert_equal, assert_status_code, assert_valid_schema

logger = logging.getLogger(__name__)

# 제네릭 타입 변수를 선언하여 _parse_and_validate_response의 반환 타입을 안전하게 추론합니다.
T = TypeVar('T', bound=BaseModel)


class UserService:
    """
    사용자(User) 도메인의 비즈니스 워크플로우를 캡슐화하는 Service 계층 클래스.
    
    순수한 비즈니스 API 호출과 데이터 변환(DTO)에 집중하며,
    테스트 케이스에서 중복해서 작성될 수 있는 공통 흐름을 추상화합니다.
    """

    def __init__(self, user_api: UserAPI) -> None:
        """
        UserService 인스턴스를 초기화합니다.

        Args:
            user_api (UserAPI): 엔드포인트 호출을 전담하는 API 클라이언트 객체
        """
        self.user_api = user_api

    def _parse_and_validate_response(
        self, 
        response: Response, 
        expected_status: int, 
        schema: dict[str, Any], 
        dto_class: type[T]
    ) -> T:
        """
        응답 객체에 대한 상태 코드, JSON Schema 검증 및 DTO 변환을 일괄 수행합니다.
        
        Args:
            response (Response): API 통신 결과 객체
            expected_status (int): 기대하는 HTTP 상태 코드
            schema (dict[str, Any]): 응답 구조를 검증할 JSON Schema 딕셔너리
            dto_class (type[T]): 역직렬화할 Pydantic DTO 클래스 타입
            
        Returns:
            T: 검증 및 역직렬화가 완료된 DTO 객체
            
        Raises:
            ValueError: 응답 본문을 JSON으로 파싱할 수 없는 경우
        """
        # 1. 상태 코드 검증
        assert_status_code(response, expected_status)
        
        # 2. 비정상적 응답 본문(HTML 에러 렌더링, 공백 등)에 대한 JSON 파싱 방어 로직
        try:
            response_data = response.json()
        except ValueError as e:
            error_msg = f"응답 본문을 JSON으로 파싱할 수 없습니다: {response.text[:100]} | 사유: {e}"
            logger.error(f"[JSONParseError] {error_msg}")
            raise ValueError(error_msg)
            
        # 3. JSON Schema 무결성 구조 검증
        assert_valid_schema(response_data, schema)
        
        # 4. Pydantic v2 표준 객체 역직렬화 및 검증법을 활용한 안전한 DTO 반환
        return dto_class.model_validate(response_data)

    @allure.step("사용자 생성 워크플로우")
    def create_user(self, request_dto: CreateUserRequest) -> CreateUserResponse:
        """
        신규 사용자 생성 비즈니스 로직을 수행하고 결과 DTO를 반환합니다.
        
        Service 계층의 독립성과 테스트 재사용성을 위해, 랜덤 데이터 생성 의존성을 제거하고 
        준비된 데이터 요청 DTO(CreateUserRequest)만을 매개변수로 주입받습니다.

        Args:
            request_dto (CreateUserRequest): 생성에 필요한 정보가 담긴 요청 DTO

        Returns:
            CreateUserResponse: 스키마 및 상태 검증이 완료된 사용자 생성 성공 DTO
        """
        logger.info("사용자 생성 워크플로우 시작")
        response = self.user_api.create_user(request_dto=request_dto)
        
        response_dto = self._parse_and_validate_response(
            response=response,
            expected_status=201,
            schema=UserSchemas.CREATE_USER_SCHEMA,
            dto_class=CreateUserResponse
        )
        
        # 데이터 정합성 비즈니스 검증 (Python 내장 assert 대신 공통 Assertion 유틸리티 사용)
        assert_equal(response_dto.name, request_dto.name, "생성된 사용자 이름")
        assert_equal(response_dto.job, request_dto.job, "생성된 사용자 직업")
        
        logger.debug(f"사용자 생성 완료: ID {response_dto.id}")
        return response_dto

    @allure.step("특정 사용자 상세 조회 워크플로우")
    def get_user(self, user_id: int | str) -> GetUserResponse:
        """
        특정 사용자를 조회하고 검증된 성공 응답 DTO를 반환합니다.
        
        Args:
            user_id (int | str): 조회할 사용자의 고유 ID
            
        Returns:
            GetUserResponse: 사용자 정보가 담긴 응답 DTO
        """
        logger.info(f"사용자(ID: {user_id}) 상세 조회 워크플로우 시작")
        response = self.user_api.get_user(user_id=user_id)
        
        response_dto = self._parse_and_validate_response(
            response=response,
            expected_status=200,
            schema=UserSchemas.GET_USER_SCHEMA,
            dto_class=GetUserResponse
        )
        
        # 요청한 ID와 조회된 데이터의 ID 정합성 확인
        assert_equal(str(response_dto.data.id), str(user_id), "조회된 사용자 ID 일치 여부")
        
        return response_dto
        
    @allure.step("존재하지 않는 사용자 상세 조회 (Negative 시나리오)")
    def get_user_expect_not_found(self, user_id: int | str) -> Response:
        """
        존재하지 않는 사용자 정보를 조회하는 예외 시나리오 동작을 수행합니다.
        
        Args:
            user_id (int | str): 조회할 (존재하지 않는) 사용자의 고유 ID
            
        Returns:
            Response: 404 상태 코드가 포함된 원본 API 응답 객체
        """
        logger.info(f"존재하지 않는 사용자(ID: {user_id}) 상세 조회 예외 워크플로우 시작")
        response = self.user_api.get_user(user_id=user_id)
        
        # 404 상태 코드 확인
        assert_status_code(response, 404)
        return response