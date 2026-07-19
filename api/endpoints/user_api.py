# api/endpoints/user_api.py
import logging
from typing import Any

import requests

from api.base_client import BaseAPIClient
from api.schemas.user_dto import CreateUserRequest, UpdateUserRequest

logger = logging.getLogger(__name__)


class UserAPI(BaseAPIClient):
    """
    사용자(User) 도메인과 관련된 API 통신을 전담하는 엔드포인트 클래스.
    
    BaseAPIClient를 상속받아 공통 설정(헤더 주입, 로깅, 재시도)을 그대로 활용하며,
    비즈니스 엔드포인트 로직에만 집중합니다.
    """

    BASE_PATH = "/api/users"

    def __init__(self, session: requests.Session) -> None:
        """
        UserAPI 인스턴스를 초기화합니다.
        
        부모 클래스인 BaseAPIClient에서 공통 헤더(API 키 등) 주입 및 설정을 
        이미 담당하고 있으므로, 하위 클래스에서는 세션만 넘겨줍니다.
        
        Args:
            session (requests.Session): HTTP 통신을 위한 공유 세션 객체
        """
        super().__init__(session)

    def _resource(self, user_id: int | str) -> str:
        """
        단일 사용자 리소스에 접근하기 위한 URL 경로를 생성합니다.
        
        Args:
            user_id (int | str): 사용자 고유 식별자 ID
            
        Returns:
            str: 조합된 리소스 URL 경로 (예: /api/users/1)
        """
        return f"{self.BASE_PATH}/{user_id}"

    # ==========================================
    # Business API Methods
    # ==========================================

    def create_user(self, request_dto: CreateUserRequest, **kwargs: Any) -> requests.Response:
        """
        새로운 사용자를 생성합니다 (POST).
        
        Args:
            request_dto (CreateUserRequest): 생성할 사용자 데이터 DTO 객체
            **kwargs: 추가 HTTP 요청 파라미터 (헤더, 타임아웃 등)
            
        Returns:
            requests.Response: API 응답 객체
        """
        # exclude_none=True 옵션을 통해 값이 없는 필드는 JSON 페이로드에서 제외시킵니다.
        payload = request_dto.model_dump(exclude_none=True)
        return self.post(self.BASE_PATH, json=payload, **kwargs)

    def get_user(self, user_id: int | str, params: dict[str, Any] | None = None, **kwargs: Any) -> requests.Response:
        """
        특정 사용자의 상세 정보를 조회합니다 (GET).
        
        Args:
            user_id (int | str): 조회할 사용자의 고유 ID
            params (dict[str, Any] | None): 쿼리 파라미터
            **kwargs: 추가 HTTP 요청 파라미터
            
        Returns:
            requests.Response: API 응답 객체
        """
        return self.get(self._resource(user_id), params=params, **kwargs)

    def list_users(self, params: dict[str, Any] | None = None, **kwargs: Any) -> requests.Response:
        """
        사용자 목록을 페이징하여 조회합니다 (GET).
        
        Args:
            params (dict[str, Any] | None): 페이징 및 검색 쿼리 파라미터
            **kwargs: 추가 HTTP 요청 파라미터
            
        Returns:
            requests.Response: API 응답 객체
        """
        return self.get(self.BASE_PATH, params=params, **kwargs)

    def update_user(self, user_id: int | str, request_dto: UpdateUserRequest, **kwargs: Any) -> requests.Response:
        """
        기존 사용자 정보를 전체 수정합니다 (PUT).
        
        Args:
            user_id (int | str): 수정할 사용자의 고유 ID
            request_dto (UpdateUserRequest): 수정할 데이터가 담긴 DTO
            **kwargs: 추가 HTTP 요청 파라미터
            
        Returns:
            requests.Response: API 응답 객체
        """
        payload = request_dto.model_dump(exclude_none=True)
        return self.put(self._resource(user_id), json=payload, **kwargs)

    def partial_update_user(self, user_id: int | str, request_dto: UpdateUserRequest, **kwargs: Any) -> requests.Response:
        """
        기존 사용자 정보를 부분 수정합니다 (PATCH).
        
        Args:
            user_id (int | str): 수정할 사용자의 고유 ID
            request_dto (UpdateUserRequest): 부분 수정할 데이터가 담긴 DTO
            **kwargs: 추가 HTTP 요청 파라미터
            
        Returns:
            requests.Response: API 응답 객체
        """
        payload = request_dto.model_dump(exclude_none=True)
        return self.patch(self._resource(user_id), json=payload, **kwargs)

    def delete_user(self, user_id: int | str, **kwargs: Any) -> requests.Response:
        """
        특정 사용자를 삭제합니다 (DELETE).
        
        Args:
            user_id (int | str): 삭제할 사용자의 고유 ID
            **kwargs: 추가 HTTP 요청 파라미터
            
        Returns:
            requests.Response: API 응답 객체
        """
        return self.delete(self._resource(user_id), **kwargs)