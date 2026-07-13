# core/data_loader.py
import json
import logging
from functools import lru_cache
from typing import Any

from core.config import PROJECT_ROOT

logger = logging.getLogger(__name__)


class DataLoader:
    """
    테스트 데이터를 파일(JSON, CSV 등)에서 읽어오는 공통 유틸리티 클래스.
    
    상태를 가지지 않는 네임스페이스(Namespace) 역할을 하며,
    파일 I/O 병목을 제거하기 위해 lru_cache를 활용하여 한 번 읽은 데이터는 메모리에 캐싱합니다.
    """

    @staticmethod
    @lru_cache(maxsize=32)
    def load_json_data(file_name: str) -> dict[str, Any]:
        """
        data/ 디렉터리에 위치한 JSON 파일을 읽어 파이썬 딕셔너리로 반환합니다.
        
        Args:
            file_name (str): 읽어올 JSON 파일의 이름 (예: 'users.json')
            
        Returns:
            dict[str, Any]: JSON 파싱이 완료된 딕셔너리 데이터
            
        Raises:
            FileNotFoundError: 지정한 테스트 데이터 파일을 찾을 수 없는 경우
            ValueError: JSON 파일 형식이 올바르지 않아 파싱에 실패한 경우
        """
        file_path = PROJECT_ROOT / "data" / file_name
        
        if not file_path.exists():
            error_msg = f"테스트 데이터 파일을 찾을 수 없습니다: {file_path}"
            logger.error(f"[FileNotFoundError] {error_msg}")
            raise FileNotFoundError(error_msg)
        
        with open(file_path, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
                logger.debug(f"테스트 데이터 파일 로드 및 캐싱 완료: {file_name}")
                return data
            except json.JSONDecodeError as e:
                error_msg = f"JSON 파일 형식이 올바르지 않습니다 ({file_name}): {e}"
                logger.error(f"[JSONDecodeError] {error_msg}")
                raise ValueError(error_msg)
    
    @staticmethod
    def get_test_credentials(role: str = "standard") -> dict[str, str]:
        """
        테스트에 자주 사용되는 계정 정보를 쉽게 조회하기 위한 래퍼(Wrapper) 메서드입니다.
        
        Args:
            role (str): 사용자 권한 타입 (예: 'standard', 'locked_out'). 기본값은 'standard'.
            
        Returns:
            dict[str, str]: 해당 계정의 자격 증명 정보 (username, password 등)
            
        Raises:
            KeyError: 매칭되는 권한 데이터(role)가 JSON 파일에 없을 경우
        """
        users_data = DataLoader.load_json_data("users.json")
        
        user = users_data.get(role)
        if not user:
            error_msg = f"[{role}] 권한에 해당하는 사용자 데이터가 users.json에 없습니다."
            logger.error(f"[KeyError] {error_msg}")
            raise KeyError(error_msg)
        
        return user