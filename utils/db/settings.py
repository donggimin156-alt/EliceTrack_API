# utils/db/settings.py
from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """
    데이터베이스 연결에 필요한 환경 변수를 관리하는 Pydantic 설정 클래스.
    
    .env 파일이나 시스템 환경 변수로부터 DB 관련 설정을 안전하게 로드하고 타입을 검증합니다.
    비밀번호와 같은 민감 정보는 SecretStr로 처리하여 메모리 덤프나 로그 노출을 방지합니다.
    """
    
    # 지원 드라이버 예시: MySQL ('mysql+pymysql'), PostgreSQL ('postgresql+psycopg2') 등
    db_driver: str = Field(default="mysql+pymysql", validation_alias="DB_DRIVER")
    db_host: str = Field(default="localhost", validation_alias="DB_HOST")
    db_port: int = Field(default=3306, validation_alias="DB_PORT")
    db_user: str = Field(default="qa_admin", validation_alias="DB_USER")
    
    # 비밀번호는 SecretStr로 선언하여 무심코 print()를 찍어도 마스킹(***) 처리되도록 보호합니다.
    db_password: SecretStr = Field(default=SecretStr(""), validation_alias="DB_PASSWORD")
    db_name: str = Field(default="qa_test_db", validation_alias="DB_NAME")

    @computed_field
    @property
    def database_url(self) -> str:
        """
        주어진 설정값들을 조합하여 SQLAlchemy 엔진 생성용 완전한 Database URL을 반환합니다.
        
        Returns:
            str: 조합된 데이터베이스 연결 문자열 (예: mysql+pymysql://user:pass@localhost:3306/dbname)
        """
        pwd = self.db_password.get_secret_value()
        
        # 비밀번호가 비어있는 로컬/개발 환경 등을 고려하여 auth 문자열을 동적으로 생성합니다.
        auth = f"{self.db_user}:{pwd}@" if pwd else f"{self.db_user}@"
        
        return f"{self.db_driver}://{auth}{self.db_host}:{self.db_port}/{self.db_name}"