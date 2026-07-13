# api/base_client.py
import logging
import uuid
from typing import Any, Literal

import requests

from api.utils.api_logger import APILogger
from api.utils.http_utils import extract_request_id
from core.config import settings

logger = logging.getLogger(__name__)


class BaseAPIClient:
    """
    엔터프라이즈 환경을 위한 공통 API 클라이언트 클래스.
    
    관심사 분리(SoC)를 통해 HTTP 통신 제어(헤더 병합, 타임아웃, 예외 처리 등)에만 집중하며,
    비즈니스 로직은 상속받는 하위 도메인 API 클래스(예: UserAPI)로 위임합니다.
    """

    def __init__(self, session: requests.Session, raise_for_status: bool = False) -> None:
        """
        BaseAPIClient 인스턴스를 초기화합니다.
        
        Args:
            session (requests.Session): 연결 풀링(Connection Pooling) 및 재시도를 위한 공유 HTTP 세션
            raise_for_status (bool): True일 경우 4xx, 5xx 에러 응답 시 자동으로 예외를 발생시킵니다.
        """
        self.session: requests.Session = session
        self.base_url: str = settings.api_base_url
        self.timeout: tuple[int, int] = settings.api_timeout
        self.raise_for_status: bool = raise_for_status
        
        # 통신 로깅을 전담하는 유틸리티 객체 (하위 클래스의 이름을 로깅 컨텍스트로 전달)
        self.api_logger = APILogger(client_name=self.__class__.__name__)

        # 공통 헤더 세팅
        self.default_headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if settings.api_key:
            self.default_headers["x-api-key"] = settings.api_key

    def _send_request(
        self, 
        method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"], 
        endpoint: str, 
        **kwargs: Any
    ) -> requests.Response:
        """
        모든 HTTP 요청을 중앙 제어하고 파이프라인(로깅 -> 통신 -> 예외 처리)을 실행합니다.
        
        Args:
            method (Literal): HTTP 메서드
            endpoint (str): API 엔드포인트 경로
            **kwargs: requests.request에 전달될 추가 옵션들 (json, data, params 등)
            
        Returns:
            requests.Response: API 응답 객체
            
        Raises:
            requests.exceptions.RequestException: 통신 중 발생하는 네트워크/타임아웃 예외
        """
        # 1. URL 및 타임아웃 조합
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        request_timeout = kwargs.pop("timeout", self.timeout)
        
        # 2. 헤더 병합 및 추적 ID(X-Request-ID) 주입
        request_headers = {**self.default_headers, **kwargs.pop("headers", {})}
        
        if extract_request_id(request_headers) == "N/A":
            request_headers["X-Request-ID"] = str(uuid.uuid4())
        kwargs["headers"] = request_headers

        # 3. 요청 로깅
        self.api_logger.log_request(method, url, request_headers, request_timeout, kwargs)

        try:
            # 4. HTTP 요청 수행
            response = self.session.request(method, url, timeout=request_timeout, **kwargs)
            
            # 5. 응답 로깅 및 SLA 검증
            self.api_logger.log_response(method, endpoint, response)
            
            # 6. 상태 코드 에러 처리 (옵션)
            if self.raise_for_status:
                response.raise_for_status()
                
            return response

        except requests.exceptions.RequestException as e:
            # 7. 예외 로깅 (cURL 포함)
            self.api_logger.log_error(e)
            # 프레임워크 레벨의 시스템 에러 추적을 위해 최상위 모듈 로거에도 흔적을 남깁니다.
            logger.debug(f"API HTTP Request 파이프라인 중 예외 발생: {e}")
            raise

    # ==========================================
    # HTTP Methods Wrappers
    # ==========================================

    def request(self, method: str, endpoint: str, **kwargs: Any) -> requests.Response:
        return self._send_request(method, endpoint, **kwargs)  # type: ignore

    def get(self, endpoint: str, **kwargs: Any) -> requests.Response:
        return self._send_request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs: Any) -> requests.Response:
        return self._send_request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs: Any) -> requests.Response:
        return self._send_request("PUT", endpoint, **kwargs)

    def patch(self, endpoint: str, **kwargs: Any) -> requests.Response:
        return self._send_request("PATCH", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs: Any) -> requests.Response:
        return self._send_request("DELETE", endpoint, **kwargs)
        
    def options(self, endpoint: str, **kwargs: Any) -> requests.Response:
        return self._send_request("OPTIONS", endpoint, **kwargs)
        
    def head(self, endpoint: str, **kwargs: Any) -> requests.Response:
        return self._send_request("HEAD", endpoint, **kwargs)