# fixtures/schedule_fixture.py
"""Elice 수업일정(Schedule) 전용 API 픽스처

로그인/토큰 발급 로직(_resolve_token)은 fixtures.elice_fixture의 기존 구현을 그대로 재사용
다만 수업일정 API는 게시판(board)/코스(course) API와 호스트 자체가 다르므로
(api-rest.elice.io → api-classroom.elice.io / dev-qatrack-classroom-api...),
EliceApiClient.url()(={base}/org/{org}/...) 조립 방식을 그대로 쓸 수 없어 수업일정 전용 클라이언트로 분리한다.
"""
import logging

import pytest
import requests

from fixtures.elice_fixture import _TIMEOUT, EliceApiClient, _resolve_token

logger = logging.getLogger(__name__)

# 수업일정은 별도 호스트(classroom-api)를 사용
_SCHEDULE_HOSTS = {
    "dev": "https://dev-qatrack-classroom-api.dev.elicer.io",
    "prod": "https://api-classroom.elice.io",
}


class ScheduleApiClient(EliceApiClient):
    """수업일정(Schedule) 도메인 API 전담 클라이언트.

    인증 세션(Authorization: Bearer + x-elice-org-name-short 헤더)은
    부모 클래스(EliceApiClient)의 __init__에서 이미 세팅되므로 그대로 물려받아 사용하고,
    이 클래스는 schedule 전용 호스트를 호출하는 메서드만 추가로 캡슐화한다.
    """

    def get_schedule(
        self,
        dt_start_ge: str,
        dt_start_le: str,
        classroom_id: str | None = None,
        count: int = 20,
        **kwargs,
    ) -> requests.Response:
        """[CS-001] 특정 기간 수업 일정 조회 (GET /schedule).

        Args:
            dt_start_ge (str): 조회 시작 기간 하한 (일정 데이터가 존재하는 유효한 값이어야 함)
            dt_start_le (str): 조회 시작 기간 상한
            classroom_id (str | None): 조회 대상 classroom ID. 미지정 시 환경 기본값(self.classroom_id) 사용
            count (int): 최대 조회 개수
            **kwargs: requests에 전달할 추가 옵션

        Returns:
            requests.Response: API 응답 객체
        """
        host = _SCHEDULE_HOSTS[self.env]
        params = {
            "classroom_id": classroom_id or self.classroom_id,
            "dt_start_ge": dt_start_ge,
            "dt_start_le": dt_start_le,
            "count": count,
        }
        return self.session.get(f"{host}/schedule", params=params, timeout=_TIMEOUT, **kwargs)


def _make_schedule_client(env_name: str, role: str, skip_msg: str) -> ScheduleApiClient:
    """인증 정보가 없으면 테스트를 skip 처리하고, 있으면 ScheduleApiClient를 생성한다."""
    token = _resolve_token(env_name, role)
    if not token:
        pytest.skip(skip_msg)
    return ScheduleApiClient(env_name, role, token)


# ──────────────────────────────────────────────
# 공개 픽스처 (elice_fixture의 prod_learner/dev_educator와 동일한 규칙)
#   prod: 학습자 (카카오 로그인 → PROD_LEARNER_TOKEN)
#   dev : 교육자 (/login/pw → EDUCATOR_LOGIN_ID/PASSWORD, 교육자는 dev에만 존재)
# ──────────────────────────────────────────────

@pytest.fixture(scope="session")
def schedule_prod_learner() -> ScheduleApiClient:
    """prod 학습자 수업일정 클라이언트."""
    return _make_schedule_client("prod", "LEARNER", "prod 학습자 토큰 없음 (PROD_LEARNER_TOKEN)")


@pytest.fixture(scope="session")
def schedule_dev_educator() -> ScheduleApiClient:
    """dev 교육자 수업일정 클라이언트."""
    return _make_schedule_client("dev", "EDUCATOR", "dev 교육자 인증 정보 없음 (EDUCATOR_LOGIN_ID/PASSWORD)")
