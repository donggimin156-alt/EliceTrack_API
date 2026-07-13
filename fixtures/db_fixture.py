# fixtures/db_fixture.py
import logging
from typing import Generator

import pytest

from utils.db import DatabaseClient

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def db_client() -> Generator[DatabaseClient, None, None]:
    """
    모든 테스트에서 공유하는 단일 DB 클라이언트 인스턴스를 제공하는 픽스처.
    
    세션 스코프(Session Scope)로 생성되어 전체 테스트 실행 내내 1회만 커넥션 풀을 초기화하며,
    테스트가 모두 종료되면 안전하게 DB 커넥션을 반환(dispose)하여 리소스 누수를 방지합니다.
    
    Yields:
        DatabaseClient: 초기화된 데이터베이스 클라이언트 객체
    """
    client = None
    try:
        logger.info("🗄️ 테스트용 데이터베이스 클라이언트(Connection Pool) 초기화 시작")
        client = DatabaseClient()
        yield client
        
    except Exception as e:
        logger.exception(f"[Fixture Error] DB Client 초기화 중 예외 발생: {e}")
        raise
        
    finally:
        if client:
            logger.info("🛑 테스트용 데이터베이스 클라이언트 종료 및 커넥션 풀 자원 반환")
            client.dispose()