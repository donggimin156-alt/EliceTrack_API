# api/endpoints/schedule_api.py
"""수업일정(Schedule) API 엔드포인트 및 테스트용 헬퍼 함수.

UserAPI와 동일하게 BaseAPIClient를 상속해 공통 HTTP 파이프라인(로깅·헤더·타임아웃)을 재사용한다.
인증 세션·토큰 주입 등 사전 준비는 fixtures/schedule_fixture.py에서 담당한다.
"""
import calendar
import logging
import os
from dataclasses import dataclass
from datetime import date
from typing import Any

import requests

from api.base_client import BaseAPIClient

logger = logging.getLogger(__name__)

_SCHEDULE_HOSTS = {
    "dev": "https://dev-qatrack-classroom-api.dev.elicer.io",
    "prod": "https://api-classroom.elice.io",
}


@dataclass(frozen=True)
class ScheduleQueryParams:
    """GET /schedule 조회에 사용하는 기간·개수 파라미터."""

    dt_start_ge: str
    dt_start_le: str
    count: int

    @property
    def query_start_date(self) -> str:
        return extract_date(self.dt_start_ge)

    @property
    def query_end_date(self) -> str:
        return extract_date(self.dt_start_le)


class ScheduleAPI(BaseAPIClient):
    """수업일정(Schedule) 도메인 API 전담 엔드포인트 클래스.

    BaseAPIClient의 get/post 래퍼와 로깅 파이프라인을 그대로 활용하고,
    수업일정 전용 호스트(classroom-api)와 엔드포인트만 캡슐화한다.
    """

    BASE_PATH = "/schedule"

    def __init__(
        self,
        session: requests.Session,
        *,
        env_name: str,
        role: str,
        org: str,
        classroom_id: str,
    ) -> None:
        super().__init__(session)
        self.env = env_name
        self.role = role
        self.org = org
        self.classroom_id = classroom_id
        self.base_url = _SCHEDULE_HOSTS[env_name].rstrip("/")

    def get_schedule(
        self,
        dt_start_ge: str,
        dt_start_le: str,
        classroom_id: str | None = None,
        count: int = 20,
        **kwargs: Any,
    ) -> requests.Response:
        """[CS-001] 특정 기간 수업 일정 조회 (GET /schedule)."""
        params = {
            "classroom_id": classroom_id or self.classroom_id,
            "dt_start_ge": dt_start_ge,
            "dt_start_le": dt_start_le,
            "count": count,
        }
        return self.get(self.BASE_PATH, params=params, **kwargs)


def current_month_range() -> tuple[str, str]:
    """오늘 기준 이번 달 1일~말일을 ISO 8601 datetime(밀리초 + UTC "Z")로 반환."""
    today = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    start = f"{today.year:04d}-{today.month:02d}-01T00:00:00.000Z"
    end = f"{today.year:04d}-{today.month:02d}-{last_day:02d}T23:59:59.999Z"
    return start, end


def resolve_schedule_query_params() -> ScheduleQueryParams:
    """환경변수 또는 이번 달 기본값으로 Schedule 조회 파라미터를 구성한다."""
    default_start, default_end = current_month_range()
    return ScheduleQueryParams(
        dt_start_ge=os.getenv("SCHEDULE_DT_START_GE", default_start),
        dt_start_le=os.getenv("SCHEDULE_DT_START_LE", default_end),
        count=int(os.getenv("SCHEDULE_COUNT", "40")),
    )


def extract_date(value: str) -> str:
    """ISO 날짜/datetime 문자열에서 앞 10자(YYYY-MM-DD)만 추출한다."""
    return value[:10]


def item_active_date_range(item: dict[str, Any], query_end_date: str) -> tuple[str, str]:
    """item이 실제로 존재(활성)하는 기간을 [시작일, 종료일](YYYY-MM-DD)로 계산한다.

    - 반복일정(rrule) + until 있음: [dt_start, until]
    - 반복일정 + until 없음: [dt_start, query_end_date]
    - 단발성 일정: [dt_start, dt_end]
    """
    start = extract_date(item["dt_start"])
    rrule = item.get("rrule")
    if rrule and rrule.get("until"):
        end = extract_date(rrule["until"])
    elif rrule:
        end = query_end_date
    else:
        end = extract_date(item["dt_end"])
    return start, end
