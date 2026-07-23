# api/endpoints/schedule_api.py
"""수업일정(Schedule) API 엔드포인트 및 테스트용 헬퍼 함수.

ScheduleAPI·ScheduleRestAPI는 BaseAPIClient를 상속해 공통 HTTP 파이프라인(로깅·헤더·타임아웃)을 재사용한다.
인증 세션·토큰 주입 등 사전 준비는 fixtures/schedule_fixture.py에서 담당한다.

Elice URL/org/classroom_id SSOT: core.config.settings.elice_environments
수업일정 메뉴는 호스트가 2종(classroom-api vs org REST)이라 클라이언트도 ScheduleAPI / ScheduleRestAPI
두 갈래만 생성 
API(엔드포인트)마다 클래스·config 항목을 새로 두는 구조는 아님
"""
import calendar
import os
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

import requests

from api.base_client import BaseAPIClient
from core.config import settings


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
    """수업일정(Schedule) — classroom 호스트 전용 클라이언트

    BaseAPIClient의 get/post 래퍼와 로깅 파이프라인을 그대로 활용한다
    env_name으로 settings.elice_environments[env_name]에서 base_url·ORG·CLASSROOM_ID를 읽는다

    Elice는 기능별로 서버가 나뉜다
      - CLASSROOM_API_URL → 일정 등 (예: GET /schedule) → 이 클래스
      - REST_API_URL      → /org/{org}/course/get/ 등 → ScheduleRestAPI (동일 파일)

    REST 경로는 ScheduleAPI로 호출할 수 없다. 호스트 종류만큼 base client를 나눈 것이지
    엔드포인트마다 config 줄이나 클라이언트 클래스를 반복 추가하는 설계가 아님
    """

    BASE_PATH = "/schedule"

    def __init__(
        self,
        session: requests.Session,
        *,
        env_name: str,
    ) -> None:
        env = settings.elice_environments[env_name]
        super().__init__(
            session,
            base_url=env["CLASSROOM_API_URL"].rstrip("/"),
        )
        self.env_name = env_name
        self.org = env["ORG"]
        self.classroom_id = env["CLASSROOM_ID"]

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

    def create_schedule(
        self,
        *,
        summary: str,
        dt_start: str,
        dt_end: str,
        classroom_id: str | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        """POST /schedule — 수업 일정 생성 (CS-003 등).

        org·Bearer는 fixtures/elice_auth.make_authenticated_session 이 session에 세팅 (get_schedule과 동일).
        """
        body = {
            "classroom_id": classroom_id or self.classroom_id,
            "summary": summary,
            "dt_start": dt_start,
            "dt_end": dt_end,
        }
        return self.post(self.BASE_PATH, json=body, **kwargs)

    def delete_schedule(
        self,
        schedule_id: str,
        *,
        classroom_id: str | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        """DELETE /schedule/{schedule_id} — 생성 TC teardown (CS-003). body에 classroom_id 필수."""
        path = f"{self.BASE_PATH}/{schedule_id.lstrip('/')}"
        if "json" not in kwargs and "data" not in kwargs:
            kwargs["json"] = {"classroom_id": classroom_id or self.classroom_id}
        return self.delete(path, **kwargs)

    def delete_classroom_course(self, course_id: int, **kwargs: Any) -> requests.Response:
        """ 과목 삭제 api 호출(teardown용)
        DELETE /classroom/{classroom_id}/course/{course_id} — classroom에서 과목 분리 (dev bulk teardown)

        명세: path course_id는 integer. org·Bearer는 authenticated session (get_schedule과 동일).
        """
        path = f"/classroom/{self.classroom_id}/course/{course_id}"
        return self.delete(path, **kwargs)

    def raw(
        self,
        method: str,
        endpoint: str,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        """세션 Bearer 없이 classroom 호스트만 호출 (CS-AUTH-01 등).

        org 헤더만 넘겨 classroom API 규약을 맞춘다.
        org-scoped REST API는 ScheduleRestAPI.raw 를 사용한다.
        """
        # self.get()은 session Bearer·로깅 파이프라인을 타므로, 토큰 없이 치는 CS-AUTH-01 등은 requests로 직접 호출
        # URL 호스트는 __init__에서 super로 넣은 self.base_url과 같다
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        return requests.request(method, url, headers=headers or {}, timeout=self.timeout, **kwargs)


class ScheduleRestAPI(BaseAPIClient):
    """수업일정 메뉴 org-scoped REST (REST_API_URL).

    classroom-api와 REST(api-rest)는 호스트·계약이 달라 ScheduleAPI와 클라이언트를 나눈다.
    env_name → settings.elice_environments[env_name]에서 REST_API_URL·ORG (SSOT).

    해피패스: self.get() 등 — 픽스처 session Bearer·로깅 파이프라인 사용.
    CS-AUTH 등: raw() — session/Bearer 없이 requests 직접 (ScheduleAPI.raw와 동일 패턴).
    """

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
        self.org = env["ORG"]

    def _scoped_endpoint(self, scoped_path: str) -> str:
        """base_url 아래 org-scoped 상대 경로"""
        return f"org/{self.org}/{scoped_path.lstrip('/')}"

    def get_course(self, course_id: int, **kwargs: Any) -> requests.Response:
        """GET org/{org}/course/get/ — session Bearer 사용 (해피패스·추후 CS TC)."""
        return self.get(
            self._scoped_endpoint("course/get/"),
            params={"course_id": course_id},
            **kwargs,
        )

    def raw(
        self,
        method: str,
        scoped_path: str,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        """scoped REST 경로를 Authorization·session 없이 호출 (CS-AUTH-01 등)"""
        # self.get()은 session Bearer를 붙이므로 토큰 누락 TC는 requests로 직접 호출
        url = f"{self.base_url.rstrip('/')}/{self._scoped_endpoint(scoped_path)}"
        return requests.request(method, url, headers=headers or {}, timeout=self.timeout, **kwargs)

    @classmethod
    def from_schedule_client(cls, client: ScheduleAPI) -> "ScheduleRestAPI":
        """동일 env·session으로 REST 호스트 클라이언트 연결 (classroom ScheduleAPI와 짝)"""
        return cls(client.session, env_name=client.env_name)


# ── dev schedule TC 전용:  bulk로 course_id 확보 ──

# dev CMS library/course id 1 = QA5기 학습과목 (이건 항상 존재함)
DEV_LIBRARY_ORIGINAL_COURSE_ID = 1

# classroom 과목 목록 GET count — 10이면 새 과목이 안 보일 수 있어 넉넉히
SCHEDULE_CLASSROOM_COURSE_LIST_COUNT = 9999


def _classroom_course_ids(client: ScheduleAPI, count: int = SCHEDULE_CLASSROOM_COURSE_LIST_COUNT) -> set[int]:
    """이 classroom에 붙은 과목들의 course_id(숫자)만 모은다

    bulk 전·후에 두 번 호출해서 차집합으로 이전과 비교했을 때 '방금 추가된 id'가 누구인지를 찾는 용도임
    """
    path = f"/classroom/{client.classroom_id}/course"
    resp = client.get(path, params={"skip": 0, "count": count})
    resp.raise_for_status()
    body = resp.json()
    if not isinstance(body, list):
        raise ValueError(f"course list must be array, got {type(body)}")
    return {int(row["course_id"]) for row in body}


def _bulk_attach_library_courses(client: ScheduleAPI, original_course_ids: list[int]) -> str:
    """
    과목을 생성하는 api 호출
    UI 과목 import와 동일 — library original id를 이 classroom에 bulk로 붙인다

    반환값은 task_id뿐 (course_id 없음) → 완료는 _wait_bulk_task, id는 목록 diff
    original_course_id 1 = dev library QA5기 학습과목
    """
    path = f"/v2/classroom/{client.classroom_id}/course/bulk"
    resp = client.post(path, json={"original_course_ids": original_course_ids})
    resp.raise_for_status()
    return resp.json()["task_id"]


def _wait_bulk_task(
    client: ScheduleAPI,
    task_id: str,
    *,
    timeout_sec: float = 60,
    poll_sec: float = 2,
) -> None:
    """ 얘는 과목 생성 api 호출 후 그 반환값을 넣어서 요청하면 completed를 주게 되는데 이것을 체크하는 함수
    bulk는 비동기 작업 — GET /task 로 붙이기가 끝날 때까지 폴링

    status completed + result.course_attached completed 이면 classroom 반영 완료
    task 응답에도 course_id는 없음
    """
    deadline = time.monotonic() + timeout_sec
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        resp = client.get(f"/task/{task_id}")
        resp.raise_for_status()
        last = resp.json()
        if last.get("status") == "completed":
            result = last.get("result") or {}
            if result.get("course_attached") == "completed":
                return
        time.sleep(poll_sec)
    raise TimeoutError(
        f"bulk task {task_id} timeout {timeout_sec}s last status={last.get('status')!r}"
    )


def resolve_dev_attached_course_id(
    client: ScheduleAPI,
    original_course_id: int = DEV_LIBRARY_ORIGINAL_COURSE_ID,
) -> int:
    """dev schedule/rest TC용 course_id 하나를 확보 (픽스처 schedule_dev_attached_course_id가 호출)

    before 목록 → bulk → task 대기 → after 목록 → after-before 가 1개면 그 course_id 반환
    client: dev 교육자 Session + ScheduleAPI (dev CLASSROOM_ID). prod와 무관
    """
    before = _classroom_course_ids(client)
    task_id = _bulk_attach_library_courses(client, [original_course_id])
    _wait_bulk_task(client, task_id)
    after = _classroom_course_ids(client)
    new_ids = after - before
    if len(new_ids) != 1:
        raise ValueError(
            f"expected 1 new course_id after bulk, got {sorted(new_ids)!r} "
            f"(before={len(before)} after={len(after)})"
        )
    return new_ids.pop()


def teardown_dev_attached_course(client: ScheduleAPI, course_id: int) -> None:
    """bulk로 붙인 dev classroom 과목 삭제 — pytest session teardown용 (HTTP 200, body {})."""
    resp = client.delete_classroom_course(course_id)
    if resp.status_code != 200:
        raise RuntimeError(
            f"DELETE /classroom/.../course/{course_id} failed: "
            f"status={resp.status_code}, body={resp.text!r}"
        )


def current_month_range() -> tuple[str, str]:
    """오늘 기준 이번 달 1일~말일을 ISO 8601 datetime(밀리초 + UTC "Z")로 반환."""
    today = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    start = f"{today.year:04d}-{today.month:02d}-01T00:00:00.000Z"
    end = f"{today.year:04d}-{today.month:02d}-{last_day:02d}T23:59:59.999Z"
    return start, end


def today_schedule_day_query() -> tuple[str, str, str]:
    """오늘 하루 일정 생성·조회용 (YYYY-MM-DD, dt_start_ge, dt_start_le).

    current_month_range()와 역할이 다름: CS-003은 POST 날짜(YYYY-MM-DD)와 GET 구간을 '오늘'로 좁히기 위함.
    이번 달 전체(current_month_range)로 GET해도 summary UUID로 찾는 건 가능하나, 조회 범위·노이즈가 커짐.
    """
    day = date.today().isoformat()
    return (
        day,
        f"{day}T00:00:00.000Z",
        f"{day}T23:59:59.999Z",
    )


def resolve_schedule_query_params() -> ScheduleQueryParams:
    """환경변수 또는 이번 달 기본값으로 Schedule 조회 파라미터를 구성한다."""
    default_start, default_end = current_month_range()
    return ScheduleQueryParams(
        dt_start_ge=os.getenv("SCHEDULE_DT_START_GE", default_start),
        dt_start_le=os.getenv("SCHEDULE_DT_START_LE", default_end),
        count=int(os.getenv("SCHEDULE_COUNT", "40")),
    )


def resolve_schedule_course_id() -> int:
    """코스 상세정보 조회 등 REST TC용 course_id (환경변수 SCHEDULE_COURSE_ID)."""
    return int(os.getenv("SCHEDULE_COURSE_ID", "770265"))


def extract_date(value: str) -> str:
    """ISO 날짜/datetime 문자열에서 앞 10자(YYYY-MM-DD)만 추출한다."""
    return value[:10]


def item_active_date_range(item: dict[str, Any], query_end_date: str) -> tuple[str, str]:
    """item의 dt_start·dt_end·rrule.until만으로 [시작일, 종료일] 구간을 잡는다 (CS-001 overlap 검증용)

    서버 GET /schedule은 exdate가 조회 구간에 걸리면 item을
    내려줄 수 있어서 이 함수 구간과 '왜 이번 달 목록에 있나'가 어긋날 수 있음 (prod CS-001 이슈 #6).

    - 반복 + until: [dt_start, until]
    - 반복 + until 없음: [dt_start, query_end_date]
    - 단발: [dt_start, dt_end]
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
