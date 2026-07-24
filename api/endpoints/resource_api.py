"""
Global Resource API (임시 파일 다운로드) 전담 클라이언트.

호스트는 settings.elice_environments[env_name]["REST_API_URL"] (SSOT)을 사용한다.
캡처 확인 결과 download_token 소비 엔드포인트는 classroom-api/dashboard-api가 아니라
REST_API_URL 호스트에 있다 (global/remote_file/temp/get/).
"""

import requests

from api.base_client import BaseAPIClient
from core.config import settings


class ResourceApi(BaseAPIClient):
    def __init__(
        self,
        session: requests.Session,
        *,
        env_name: str,
    ) -> None:
        env = settings.elice_environments[env_name]
        super().__init__(
            session,
            base_url=env["REST_API_URL"].rstrip("/"),
        )
        self.env_name = env_name

    def download_temp_file(self, download_token: str) -> requests.Response:
        """GET /global/remote_file/temp/get/ — 발급받은 토큰으로 실제 파일 획득 (E-11c)"""
        return self.get(
            "/global/remote_file/temp/get/",
            params={"download_token": download_token},
        )