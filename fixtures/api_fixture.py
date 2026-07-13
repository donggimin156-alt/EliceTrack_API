# fixtures/api_fixture.py
import logging
import os
from typing import Generator

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class HttpClientFactory:
    """
    HTTP 세션 생성의 복잡성을 캡슐화하는 Factory 클래스.
    
    안전한 재시도(Retry) 정책과 커넥션 풀(Connection Pool) 크기를 구성하여
    엔터프라이즈 환경의 대규모 API 테스트에서도 안정적인 통신을 보장합니다.
    """

    @staticmethod
    def create_session() -> requests.Session:
        """
        재시도 정책과 커넥션 풀이 적용된 requests.Session 객체를 생성합니다.
        
        Returns:
            requests.Session: 설정이 완료된 HTTP 세션 인스턴스
        """
        session = requests.Session()
        
        # POST, PUT, DELETE 등 멱등성이 보장되지 않는 메서드는 
        # 데이터 중복 생성/삭제의 위험이 있으므로 재시도(Retry) 풀에서 엄격히 제외합니다.
        retries = Retry(
            total=3, 
            connect=3, 
            read=3, 
            status=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods={"GET", "HEAD", "OPTIONS"}, 
            respect_retry_after_header=True
        )
        
        # 병렬 워커(xdist) 환경을 고려하여 Connection Pool 사이즈를 넉넉하게 확보합니다.
        pool_size = int(os.getenv("HTTP_POOL_SIZE", "50"))
        adapter = HTTPAdapter(
            max_retries=retries, 
            pool_connections=pool_size, 
            pool_maxsize=pool_size
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        logger.debug(f"Global HTTP Session 생성 완료 (Pool Size: {pool_size})")
        return session


@pytest.fixture(scope="session")
def api_session() -> Generator[requests.Session, None, None]:
    """
    모든 API 테스트가 공유하는 단일 HTTP 세션 픽스처(Fixture).
    
    Session 스코프로 선언되어 테스트 시작 시 1회만 생성되며, 
    모든 테스트가 종료된 후 안전하게 자원을 반환(teardown)합니다.
    
    Yields:
        requests.Session: 공유 HTTP 세션 객체
    """
    logger.info("🚀 API 테스트용 공유 HTTP Session 초기화 시작")
    session = HttpClientFactory.create_session()
    
    yield session
    
    # Teardown: 테스트 세션 종료 시 리소스 누수(Memory/Connection Leak)를 막기 위해 명시적으로 닫습니다.
    logger.info("🛑 API 테스트용 공유 HTTP Session 종료 및 자원 반환")
    session.close()