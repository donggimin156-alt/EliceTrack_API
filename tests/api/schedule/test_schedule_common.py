# tests/api/schedule/test_schedule_common.py
"""수업일정(Schedule) 공통 API 테스트 — 학습자·교육자가 동일한 응답 구조를 검증하는 기능

공통 API는 검증 로직이 같고 역할(target)만 다르므로 역할별로 테스트를 따로 만들지 않고
하나의 테스트를 target으로 파라미터화
  - 학습자 → prod (본인 단일계정)
  - 교육자 → dev  (교육자 계정은 dev에만 존재)
"""
import pytest
from dataclasses import dataclass
from typing import Any, Literal

from api.endpoints import schedule_api as schedule # 수업일정 API 엔드포인트 및 헬퍼 함수
from api.schemas import schedule_schema as schedule_schemas # 수업일정 스키마 정의
from utils import assertions # 검증 도구

SCHEDULE_TARGETS = [    # 수업일정 API 테스트 대상 역할 픽스처 매칭용
    pytest.param(
        "schedule_prod_learner",
        marks=[
            pytest.mark.learner,
            pytest.mark.xfail(
                reason="[CS-001] prod 학습자 row 현재 실패(데이터·API). 고쳐지면 XPASS",
                strict=False,
            ),
        ],
        id="CS-001-learner-prod",
    ),
    pytest.param("schedule_dev_educator", marks=pytest.mark.educator, id="CS-001-educator-dev"),
]


@dataclass(frozen=True)
class AuthMissingCase:
    """CS-AUTH-01: API마다 토큰 누락 시 HTTP·JSON 기대값이 다르므로 row에 명시."""

    client_fixture: str
    api: Literal["classroom_schedule_get", "rest_course_get"]
    expected_http_status: int
    json_expectations: tuple[tuple[str, Any], ...]
    reject_schedule_list: bool = False
    course_id_fixture: str | None = None


# CS-AUTH-01 — 수업일정 관련 API 토큰 누락 (403+no_access_token vs REST 200+fail envelope 등 row별 상이)
AUTH_MISSING_CASES = [
    pytest.param(
        AuthMissingCase(
            client_fixture="schedule_prod_learner",
            api="classroom_schedule_get",
            expected_http_status=403,
            json_expectations=(("code", "no_access_token"),),
            reject_schedule_list=True,
        ),
        marks=pytest.mark.learner,
        id="CS-AUTH-01-schedule-learner-prod",
    ),
    pytest.param(
        AuthMissingCase(
            client_fixture="schedule_dev_educator",
            api="classroom_schedule_get",
            expected_http_status=403,
            json_expectations=(("code", "no_access_token"),),
            reject_schedule_list=True,
        ),
        marks=pytest.mark.educator,
        id="CS-AUTH-01-schedule-educator-dev",
    ),
    pytest.param(
        AuthMissingCase(
            client_fixture="schedule_prod_learner",
            api="rest_course_get",
            course_id_fixture="schedule_course_id",
            expected_http_status=200,
            json_expectations=(
                ("_result.status", "fail"),
                ("_result.status_code", 409),
                ("fail_code", "insufficient_permission"),
            ),
            reject_schedule_list=False,
        ),
        marks=pytest.mark.learner,
        id="CS-AUTH-01-course-get-learner-prod",
    ),
    pytest.param(
        AuthMissingCase(
            client_fixture="schedule_dev_educator",
            api="rest_course_get",
            course_id_fixture="schedule_dev_attached_course_id",
            expected_http_status=200,
            json_expectations=(
                ("_result.status", "fail"),
                ("_result.status_code", 409),
                ("fail_code", "insufficient_permission"),
            ),
            reject_schedule_list=False,
        ),
        marks=pytest.mark.educator,
        id="CS-AUTH-01-course-get-educator-dev",
    ),
]


@pytest.mark.api
@pytest.mark.schedule
class TestScheduleCommon:
    """공통 수업일정 API: 학습자·교육자 모두 동일하게 동작해야 하는 시나리오"""

    @pytest.mark.p0
    @pytest.mark.parametrize("client_fixture", SCHEDULE_TARGETS)
    def test_CS_001(
        self,
        request,
        client_fixture,
        schedule_query_params: schedule.ScheduleQueryParams,
    ):
        """[CS-001] 수업일정 조회 시 정상 응답 검증 학습자=prod(본인계정) 교육자=dev

        prod 학습자 row만 xfail(현재 실패 인지). dev 교육자 row는 일반 실행.
        기대값(명세서 'CS-001' 행 기준):
          - status_code == 200
          - JSON 배열 응답이며 1건 이상 ~ count 이하
          - 각 item이 스키마를 만족함
          - 모든 item의 tags.classroom_id가 요청 classroom_id와 일치
          - 모든 item의 활성 기간이 요청 기간과 겹침
        """
        # 이 이름의 픽스처 실행 후 client라는 변수에 담기 => 토큰, url, classroom_id 등 준비됨
        client = request.getfixturevalue(client_fixture)  
        
        classroom_id = client.classroom_id

        # 예시: “2026년 7월 1일 ~ 7월 31일, 최대 40건” (이번달 기준)이라는 조회 조건이 담긴 데이터
        query = schedule_query_params   

        # 수업 일정 API 호출 실행
        res = client.get_schedule(
            dt_start_ge=query.dt_start_ge,
            dt_start_le=query.dt_start_le,
            classroom_id=classroom_id,
            count=query.count,
        )

        assert res.status_code == 200, res.text
        body = res.json()

        assert isinstance(body, list), f"응답이 JSON 배열이 아님: {type(body)}"
        assert 1 <= len(body) <= query.count, (
            f"응답 개수({len(body)})가 1~{query.count} 범위를 벗어남"
        )
        
        # 수업 일정 스키마 검증
        assertions.assert_valid_schema(body, schedule_schemas.ScheduleSchemas.SCHEDULE_LIST_SCHEMA)

        # API한테 보냈었던 조회 기간 꼭다리 뗀 것
        query_start = query.query_start_date
        query_end = query.query_end_date

        # 응답 배열의 일정들마다 classroom_id 일치와 기간이 겹치는지 검증
        for item in body:  # body: API가 돌려준 일정 객체[] 하나씩
            tags = item.get("tags", {})  # item 안의 tags 객체 (없으면 빈 dict)
            item_classroom_id = tags.get("classroom_id")  # 이 일정이 속한 classroom UUID
            assert str(item_classroom_id) == str(classroom_id), (  # 요청한 classroom과 일치해야 함
                f"item의 tags.classroom_id({item_classroom_id})가 요청값({classroom_id})과 불일치"
            )

            # item의 활성 기간 [시작일, 종료일] (YYYY-MM-DD)
            item_start, item_end = schedule.item_active_date_range(item, query_end)  
            overlaps = item_start <= query_end and query_start <= item_end  # 요청 기간과 하루라도 겹치면 True
            assert overlaps, (  # 겹치지 않으면 FAIL (종료된 일정이 섞였을 때 등)
                f"'{item.get('summary')}' 일정의 활성 기간({item_start}~{item_end})이 "
                f"요청 기간({query_start}~{query_end})과 겹치지 않음 "
                f"(item id={item.get('id')})"
            )
    @pytest.mark.smoke
    @pytest.mark.parametrize("case", AUTH_MISSING_CASES)
    def test_CS_AUTH_01(
        self,
        request,
        case: AuthMissingCase,
        schedule_query_params: schedule.ScheduleQueryParams,
    ):
        """[CS-AUTH-01] 인증 토큰 누락 시 거부 검증 (수업일정 관련 API — row별 기대값 상이)

        사전조건: CS-001과 동일한 query/classroom_id 등 준비(호출 API에 따라 사용)
        절차: Authorization 헤더만 제거하고 해당 API 호출

        기대값(예):
          - classroom GET /schedule: status 403, code no_access_token
          - REST GET course/get (prod/dev REST 호스트·course_id row별): HTTP 200 + _result.status_code 409 fail envelope
        """
        client = request.getfixturevalue(case.client_fixture)
        query = schedule_query_params

        # Authorization 없이 호출 — case.api에 따라 classroom / REST 호스트 분기
        if case.api == "classroom_schedule_get":
            # classroom-api: org 헤더 + CS-001과 동일 query, Bearer만 제외
            resp = client.raw(
                "GET",
                schedule.ScheduleAPI.BASE_PATH,
                headers={"x-elice-org-name-short": client.org},
                params={
                    "classroom_id": client.classroom_id,
                    "dt_start_ge": query.dt_start_ge,
                    "dt_start_le": query.dt_start_le,
                    "count": query.count,
                },
            )
        elif case.api == "rest_course_get":
            if not case.course_id_fixture:
                raise ValueError("rest_course_get row must set course_id_fixture")
            course_id = request.getfixturevalue(case.course_id_fixture)
            # REST-api: env별 REST_API_URL·org + row별 course_id. raw()는 Bearer 미전송
            rest = schedule.ScheduleRestAPI.from_schedule_client(client)
            resp = rest.raw("GET", "course/get/", params={"course_id": course_id})
        else:
            raise ValueError(f"unknown api kind: {case.api}")

        assertions.assert_status_code(resp, case.expected_http_status)
        body = resp.json()
        for path, expected in case.json_expectations:
            assertions.assert_json_value(body, path, expected)
        if case.reject_schedule_list:
            assert not isinstance(body, list), "인증 없이 일정 배열이 반환되면 안 됨"
