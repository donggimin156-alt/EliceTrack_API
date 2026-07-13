# api/utils/api_logger.py
import json
import logging
from typing import Any

import requests

from api.utils.http_utils import extract_request_id, generate_curl, mask_sensitive_headers

logger = logging.getLogger(__name__)


class APILogger:
    """
    API 요청 및 응답 로깅을 전담하여 BaseAPIClient의 비대화를 방지하는 유틸리티 클래스.
    """
    
    def __init__(self, client_name: str = "APIClient") -> None:
        """
        APILogger 인스턴스를 초기화합니다.
        
        Args:
            client_name (str): 호출한 클라이언트의 이름 (로깅 컨텍스트용, 기본값 "APIClient")
        """
        self.client_name = client_name

    def log_request(
        self, 
        method: str, 
        url: str, 
        headers: dict[str, Any], 
        timeout: float | tuple[int, int], 
        kwargs: dict[str, Any]
    ) -> None:
        """
        API 요청 정보를 마스킹 처리하여 안전하게 로깅합니다.
        
        Args:
            method (str): HTTP 메서드 (GET, POST 등)
            url (str): 요청 대상 URL
            headers (dict[str, Any]): 요청 헤더 딕셔너리
            timeout (float | tuple[int, int]): 타임아웃 설정값
            kwargs (dict[str, Any]): 부가적인 요청 파라미터 (json, params, data 등)
        """
        masked_headers = mask_sensitive_headers(headers)
        logger.info(f"[{self.client_name}] [{method}] Request URL: {url}")
        logger.debug(f"Request Headers: {masked_headers}")
        logger.debug(f"Request Timeout: {timeout}s")
        
        if "cookies" in kwargs:
            logger.debug(f"Request Cookies: {kwargs['cookies']}")
        if "json" in kwargs:
            logger.debug(f"Request JSON:\n{json.dumps(kwargs['json'], indent=2, ensure_ascii=False)}")
        if "data" in kwargs:
            logger.debug(f"Request Data: {kwargs['data']}")
        if "params" in kwargs:
            logger.debug(f"Request Params: {kwargs['params']}")
        if "files" in kwargs:
            logger.debug(f"Request Files: {kwargs['files']}")

    def log_response(self, method: str, endpoint: str, response: requests.Response) -> None:
        """
        API 응답 결과, 소요 시간, 상태 코드를 로깅하고 메트릭을 요약합니다.
        
        Args:
            method (str): HTTP 메서드
            endpoint (str): API 엔드포인트 경로
            response (requests.Response): HTTP 응답 객체
        """
        elapsed_sec = response.elapsed.total_seconds()
        req_id = extract_request_id(dict(response.headers))
        status = response.status_code
        
        # Prometheus나 Grafana 연동을 고려한 한 줄 요약 메트릭 로그
        status_text = "PASS" if response.ok else "FAIL"
        logger.info(f"[{self.client_name}] [{method} {endpoint}] {elapsed_sec * 1000:.0f}ms {status_text} ({status}) | ReqID: {req_id}")
        
        # SLA 검증
        if elapsed_sec > 3.0:
            logger.warning(f"[{method}] SLA 지연 초과 ({elapsed_sec}s) | URL: {response.url}")
            
        content_type = response.headers.get("Content-Type", "").lower()
        binary_types = ["application/octet-stream", "image/", "zip", "pdf", "audio/", "video/"]
        
        if any(t in content_type for t in binary_types):
            logger.debug(f"Response Body: [BINARY DATA - {content_type}]")
            return

        body_text = response.text
        if "application/json" in content_type and body_text:
            try:
                body_text = json.dumps(response.json(), indent=2, ensure_ascii=False)
            except ValueError:
                pass  # JSON 파싱 실패 시 원본 text를 유지
        
        # 응답이 너무 길어 CI 로그 시스템에 과부하를 주는 것을 방지
        if len(body_text) > 3000:
            body_text = body_text[:3000] + "\n... [TRUNCATED]"
            
        if body_text:
            logger.debug(f"Response Body:\n{body_text}")

    def log_error(self, e: requests.exceptions.RequestException) -> None:
        """
        세분화된 예외 로깅 및 재현(Curl) 커맨드 출력을 수행합니다.
        
        Args:
            e (requests.exceptions.RequestException): 발생한 HTTP 요청 예외
        """
        if isinstance(e, requests.exceptions.Timeout):
            logger.error(f"[TimeoutError] API 요청 시간 초과: {e}")
        elif isinstance(e, requests.exceptions.ConnectionError):
            logger.error(f"[ConnectionError] API 서버 연결 실패 (DNS 등): {e}")
        else:
            logger.error(f"[RequestException] API 요청 중 오류 발생: {e}")
            
        if getattr(e, "request", None):
            logger.error(f"Reproduce with:\n{generate_curl(e.request)}")