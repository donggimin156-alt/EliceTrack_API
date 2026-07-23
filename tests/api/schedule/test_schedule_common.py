# tests/api/schedule/test_schedule_common.py
"""수업일정(Schedule) 공통 API 테스트 — 학습자·교육자가 동일한 응답 구조를 검증하는 기능

공통 API는 검증 로직이 같고 역할(target)만 다르므로 역할별로 테스트를 따로 만들지 않고
하나의 테스트를 target으로 파라미터화
  - 학습자 → prod (본인 단일계정)
  - 교육자 → dev  (교육자 계정은 dev에만 존재)
"""
import pytest

from api.endpoints import schedule_api as schedule # 수업일정 API 엔드포인트 및 헬퍼 함수
from api.schemas import schedule_schema as schedule_schemas # 수업일정 스키마 정의
from utils import helpers # 검증 도구
from utils.helpers.class_helper import assert_detail_error

# CS-001 prod 학습자 xfail — GET /schedule 반복 일정 기간 필드 vs exdate 포함 기준 (GitLab #6)
CS001_PROD_SCHEDULE_ISSUE = (
    "https://kdt-gitlab.elice.io/qa_track/class_05/qa_project_02/team02/issue-report/-/issues/6"
)

SCHEDULE_TARGETS = [    # 수업일정 API 테스트 대상 역할 픽스처 매칭용
    pytest.param(
        "schedule_prod_learner",
        marks=[
            pytest.mark.learner,
            pytest.mark.xfail(
                reason=(
                    "[CS-001] prod 학습자: API가 exdate 기준으로 item을 내려주는 것으로 추정은 되지만 "
                    "dt_start/rrule.until만으로는 조회월과 겹침 검증 불가 → item_active_date_range assert FAIL. "
                    f"이슈: {CS001_PROD_SCHEDULE_ISSUE}"
                ),
                strict=False,
            ),
        ],
        id="CS-001-learner-prod",
    ),
    pytest.param("schedule_dev_educator", marks=pytest.mark.educator, id="CS-001-educator-dev"),
]

# CS-AUTH-01 — classroom GET /schedule, Bearer 없음 (prod learner / dev educator)
AUTH_01_SCHEDULE_TARGETS = [
    pytest.param("schedule_prod_learner", marks=pytest.mark.learner, id="CS-AUTH-01-schedule-learner-prod"),
    pytest.param("schedule_dev_educator", marks=pytest.mark.educator, id="CS-AUTH-01-schedule-educator-dev"),
]

# CS-AUTH-02 — REST GET course/get, Bearer 없음 (course_id만 env·픽스처별 상이)
AUTH_02_COURSE_GET_TARGETS = [
    pytest.param(
        "schedule_prod_learner",
        "schedule_course_id",
        marks=pytest.mark.learner,
        id="CS-AUTH-02-course-get-learner-prod",
    ),
    pytest.param(
        "schedule_dev_educator",
        "schedule_dev_attached_course_id",
        marks=pytest.mark.educator,
        id="CS-AUTH-02-course-get-educator-dev",
    ),
]

COURSE_GET_AUTH_JSON_EXPECTATIONS = (
    ("_result.status", "fail"),
    ("_result.status_code", 409),
    ("fail_code", "insufficient_permission"),
)

# CS-002 — REST GET course/get, Bearer 있음 (course_id row는 CS-AUTH-02와 동일)
CS_002_COURSE_GET_TARGETS = [
    pytest.param(
        "schedule_prod_learner",
        "schedule_course_id",
        marks=pytest.mark.learner,
        id="CS-002-course-get-learner-prod",
    ),
    pytest.param(
        "schedule_dev_educator",
        "schedule_dev_attached_course_id",
        marks=pytest.mark.educator,
        id="CS-002-course-get-educator-dev",
    ),
]

COURSE_GET_OK_JSON_EXPECTATIONS = (
    ("_result.status", "ok"),
    ("_result.status_code", 200),
)

# CS-PARAM-01~04 — GET /schedule 필수 query 1개씩 누락 (CS-001 query·Bearer O, prod/dev 각 2 row → 8 runs)
SCHEDULE_PARAM_OMIT_FIELDS = [
    pytest.param("classroom_id", id="CS-PARAM-01"),
    pytest.param("dt_start_ge", id="CS-PARAM-02"),
    pytest.param("dt_start_le", id="CS-PARAM-03"),
    pytest.param("count", id="CS-PARAM-04"),
]

SCHEDULE_PARAM_CLIENTS = [
    pytest.param("schedule_prod_learner", marks=pytest.mark.learner, id="learner-prod"),
    pytest.param("schedule_dev_educator", marks=pytest.mark.educator, id="educator-dev"),
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

        prod 학습자 row만 xfail — 반복 일정(QR·점심 등)이 API는 exdate로 조회월에 포함시키나
        item의 dt_start/rrule.until은 과거·5월 등이라 item_active_date_range overlap assert 실패.
        버그/개선: {issue}

        dev 교육자 row는 일반 실행.
        기대값(명세서 'CS-001' 행 기준):
          - status_code == 200
          - JSON 배열 응답이며 1건 이상 ~ count 이하
          - 각 item이 스키마를 만족함
          - 모든 item의 tags.classroom_id가 요청 classroom_id와 일치
          - 모든 item의 활성 기간이 요청 기간과 겹침
        """.format(issue=CS001_PROD_SCHEDULE_ISSUE)
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

        helpers.assert_status_code(res, 200)
        body = res.json()

        assert isinstance(body, list), f"응답이 JSON 배열이 아님: {type(body)}"
        assert 1 <= len(body) <= query.count, (
            f"응답 개수({len(body)})가 1~{query.count} 범위를 벗어남"
        )
        
        # 수업 일정 스키마 검증
        helpers.assert_valid_schema(body, schedule_schemas.ScheduleSchemas.SCHEDULE_LIST_SCHEMA)

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

    @pytest.mark.parametrize("client_fixture", SCHEDULE_PARAM_CLIENTS)
    @pytest.mark.parametrize("omit_field", SCHEDULE_PARAM_OMIT_FIELDS)
    def test_CS_PARAM_01_04(
        self,
        request,
        client_fixture: str,
        omit_field: str,
        schedule_query_params: schedule.ScheduleQueryParams,
    ):
        """[CS-PARAM-01~04] GET /schedule — 필수 query 1개 누락 시 422 및 detail 검증

        CS-001과 동일 Bearer·query 값에서 omit_field 키만 보내지 않음 (get_schedule 미사용).
        prod 학습자 / dev 교육자. 기대: 422, detail 1건, type missing, msg Field required,
        loc query + omit_field.
        """
        client = request.getfixturevalue(client_fixture)
        query = schedule_query_params
        params = {
            "classroom_id": client.classroom_id,
            "dt_start_ge": query.dt_start_ge,
            "dt_start_le": query.dt_start_le,
            "count": query.count,
        }
        del params[omit_field]

        resp = client.get(schedule.ScheduleAPI.BASE_PATH, params=params)

        helpers.assert_status_code(resp, 422)
        body = resp.json()
        assert not isinstance(body, list), "파라미터 누락 시 일정 JSON 배열이 반환되면 안 됨"
        helpers.assert_list_length(body["detail"], 1)
        assert_detail_error(body, "missing", ["query", omit_field])
        helpers.assert_json_value(body, "detail[0].msg", "Field required")

    @pytest.mark.parametrize("client_fixture", AUTH_01_SCHEDULE_TARGETS)
    def test_CS_AUTH_01(
        self,
        request,
        client_fixture: str,
        schedule_query_params: schedule.ScheduleQueryParams,
    ):
        """[CS-AUTH-01] classroom GET /schedule — Authorization 없이 호출 시 거부

        사전조건: CS-001과 동일 query·classroom_id
        기대값: HTTP 403, code no_access_token (일정 배열 미반환)
        """
        client = request.getfixturevalue(client_fixture)
        query = schedule_query_params

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

        helpers.assert_status_code(resp, 403)
        body = resp.json()
        helpers.assert_json_value(body, "code", "no_access_token")
        assert not isinstance(body, list), "인증 없이 일정 배열이 반환되면 안 됨"


    @pytest.mark.parametrize("client_fixture,course_id_fixture", AUTH_02_COURSE_GET_TARGETS)
    def test_CS_AUTH_02(
        self,
        request,
        client_fixture: str,
        course_id_fixture: str,
    ):
        """[CS-AUTH-02] REST GET course/get — Authorization 없이 호출 시 거부

        prod/dev REST 호스트·course_id는 row별 픽스처. JSON fail envelope는 동일.
        기대값: HTTP 200, _result.status_code 409, fail_code insufficient_permission
        """
        client = request.getfixturevalue(client_fixture)
        course_id = request.getfixturevalue(course_id_fixture)
        rest = schedule.ScheduleRestAPI.from_schedule_client(client)
        resp = rest.raw("GET", "course/get/", params={"course_id": course_id})

        helpers.assert_status_code(resp, 200)
        body = resp.json()
        for path, expected in COURSE_GET_AUTH_JSON_EXPECTATIONS:
            helpers.assert_json_value(body, path, expected)

    @pytest.mark.p0
    @pytest.mark.parametrize("client_fixture,course_id_fixture", CS_002_COURSE_GET_TARGETS)
    def test_CS_002(
        self,
        request,
        client_fixture: str,
        course_id_fixture: str,
    ):
        """[CS-002] REST GET course/get — Authorization 포함 시 코스 상세 정상 응답

        prod/dev REST 호스트·course_id는 row별 픽스처(CS-AUTH-02와 동일 row).
        기대값: HTTP 200, _result ok/200, course.id == 요청 course_id, 공통 골격 스키마.
        """
        client = request.getfixturevalue(client_fixture)
        course_id = request.getfixturevalue(course_id_fixture)
        rest = schedule.ScheduleRestAPI.from_schedule_client(client)
        resp = rest.get_course(course_id)

        helpers.assert_status_code(resp, 200)
        body = resp.json()
        for path, expected in COURSE_GET_OK_JSON_EXPECTATIONS:
            helpers.assert_json_value(body, path, expected)
        helpers.assert_json_value(body, "course.id", int(course_id))
        helpers.assert_valid_schema(body, schedule_schemas.ScheduleSchemas.COURSE_GET_RESPONSE_SCHEMA)
