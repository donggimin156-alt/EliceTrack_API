# api/utils/http_utils.py
import shlex
from typing import Any

import requests

# 본 모듈은 상태를 가지지 않는 순수 함수(Pure Functions)들의 모음이므로 
# 독립성과 재사용성을 위해 logger를 선언하지 않고 입력값에 따른 출력만 책임집니다.


def mask_sensitive_headers(headers: dict[str, Any]) -> dict[str, Any]:
    """
    로그 출력 전 인증 토큰, 비밀번호 등 민감한 정보가 포함된 헤더 값을 마스킹합니다.
    
    Args:
        headers (dict[str, Any]): 원본 HTTP 헤더 딕셔너리
        
    Returns:
        dict[str, Any]: 민감한 값이 '********'로 마스킹 처리된 새로운 헤더 딕셔너리
    """
    sensitive_keys = {
        "authorization", "proxy-authorization", "x-api-key", "api-key",
        "token", "access-token", "refresh-token", "cookie", "set-cookie",
        "password", "secret", "client-secret", "client-id"
    }
    
    # 딕셔너리 컴프리헨션을 사용하여 불필요한 copy() 및 반복을 줄이고 성능을 개선했습니다.
    return {
        k: ("********" if k.lower() in sensitive_keys else v)
        for k, v in headers.items()
    }


def generate_curl(req: requests.PreparedRequest) -> str:
    """
    API 요청 실패 시 터미널에서 즉시 재현해 볼 수 있는 Curl 명령어를 생성합니다.
    
    Args:
        req (requests.PreparedRequest): 준비된 HTTP 요청 객체
        
    Returns:
        str: 터미널에서 실행 가능한 cURL 커맨드 문자열
    """
    command = f"curl -X {req.method} '{req.url}'"
    
    if req.headers:
        masked_headers = mask_sensitive_headers(dict(req.headers))
        for k, v in masked_headers.items():
            command += f" -H '{k}: {v}'"
            
    if req.body:
        body_str = req.body.decode("utf-8") if isinstance(req.body, bytes) else str(req.body)
        command += f" -d {shlex.quote(body_str)}"
        
    return command


def extract_request_id(headers: dict[str, Any]) -> str:
    """
    헤더에서 분산 추적(Trace)을 위한 Request ID를 추출합니다.
    
    Args:
        headers (dict[str, Any]): HTTP 응답 또는 요청 헤더
        
    Returns:
        str: 추출된 Request ID (없을 경우 "N/A" 반환)
    """
    trace_keys = ["x-request-id", "x-correlation-id", "trace-id", "traceparent", "request-id"]
    
    # 이중 루프(O(N*M))로 인한 비효율을 제거하기 위해 헤더 키를 소문자로 정규화한 딕셔너리를 먼저 생성(O(N))합니다.
    lower_headers = {k.lower(): str(v) for k, v in headers.items()}
    
    for key in trace_keys:
        if key in lower_headers:
            return lower_headers[key]
            
    return "N/A"