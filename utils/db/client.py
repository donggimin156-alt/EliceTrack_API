# utils/db/client.py
import logging
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from utils.db.settings import DatabaseSettings

logger = logging.getLogger(__name__)


class DatabaseClient:
    """
    엔터프라이즈 환경을 위한 데이터베이스 클라이언트.
    
    커넥션 풀링(Connection Pooling)을 적용하여 다중 병렬 워커(xdist) 환경에서도 
    DB 과부하 없이 안정적으로 쿼리를 실행합니다.
    """
    
    _engine = None
    _SessionLocal = None

    def __init__(self, settings: DatabaseSettings | None = None) -> None:
        """
        DatabaseClient 인스턴스를 초기화하고 커넥션 풀을 보장합니다.
        
        Args:
            settings (DatabaseSettings | None): DB 연결 설정 객체. None일 경우 기본 환경변수를 로드합니다.
        """
        self.settings = settings or DatabaseSettings()
        self._initialize_pool(self.settings)

    @classmethod
    def _initialize_pool(cls, settings: DatabaseSettings) -> None:
        """
        클래스 로드 시 최초 1회만 커넥션 풀(Engine 및 SessionMaker)을 초기화합니다.
        
        Args:
            settings (DatabaseSettings): 데이터베이스 연결 설정 객체
        """
        if cls._engine is None:
            # 실무 트래픽을 고려한 풀링 옵션 (병렬 테스트 최적화)
            cls._engine = create_engine(
                settings.database_url,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=1800,  # 30분 이상 유휴된 커넥션 갱신
            )
            cls._SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls._engine)
            logger.info(f"🗄️ Database Connection Pool 초기화 완료: {settings.db_host}")

    def fetch_all(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        SELECT 쿼리를 실행하고 다중 결과를 딕셔너리 리스트로 반환합니다.
        
        Args:
            query (str): 실행할 SQL 쿼리 문자열
            params (dict[str, Any] | None): 쿼리에 바인딩할 파라미터 딕셔너리
            
        Returns:
            list[dict[str, Any]]: 조회된 데이터 딕셔너리의 리스트
            
        Raises:
            SQLAlchemyError: 쿼리 실행 중 예외가 발생한 경우
        """
        with self._SessionLocal() as session:
            try:
                result = session.execute(text(query), params or {})
                # SQLAlchemy 2.0 권장 방식: mappings()를 호출하여 안전하게 Dict 형태로 변환
                return [dict(row) for row in result.mappings()]
            except SQLAlchemyError as e:
                logger.error(f"[DB Error] Fetch All 실패: {e}\nQuery: {query}\nParams: {params}")
                raise

    def fetch_one(self, query: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """
        SELECT 쿼리를 실행하고 단일 결과만 딕셔너리 형태로 반환합니다.
        
        Args:
            query (str): 실행할 SQL 쿼리 문자열
            params (dict[str, Any] | None): 쿼리에 바인딩할 파라미터 딕셔너리
            
        Returns:
            dict[str, Any] | None: 조회된 단일 행 데이터. 결과가 없으면 None 반환.
        """
        result = self.fetch_all(query, params)
        return result[0] if result else None

    def execute_update(self, query: str, params: dict[str, Any] | None = None) -> int:
        """
        INSERT, UPDATE, DELETE 쿼리를 실행합니다.
        성공 시 Commit, 실패 시 안전하게 Rollback을 보장합니다.
        
        Args:
            query (str): 실행할 DML 쿼리 문자열
            params (dict[str, Any] | None): 쿼리에 바인딩할 파라미터 딕셔너리
            
        Returns:
            int: 쿼리 실행으로 영향을 받은 행(Affected Rows)의 개수
            
        Raises:
            SQLAlchemyError: 쿼리 실행 실패로 인해 롤백이 발생한 경우
        """
        with self._SessionLocal() as session:
            try:
                result = session.execute(text(query), params or {})
                session.commit()
                logger.debug(f"DB Update 완료 (영향받은 행: {result.rowcount}건)")
                return result.rowcount
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"[DB Error] Update 실패 (Rollback 실행됨): {e}\nQuery: {query}\nParams: {params}")
                raise

    def dispose(self) -> None:
        """
        테스트 세션이 모두 종료될 때 커넥션 풀을 안전하게 정리(Dispose)합니다.
        """
        if self._engine:
            self._engine.dispose()
            logger.info("🗄️ Database Connection Pool 자원 반환 (Dispose) 완료")