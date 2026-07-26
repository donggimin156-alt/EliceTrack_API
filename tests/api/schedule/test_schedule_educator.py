# tests/api/schedule/test_schedule_educator.py
"""수업일정(Schedule) 교육자 전용 API — dev 교육자 계정·classroom 호스트."""
import logging
import uuid

import pytest

from api.endpoints import schedule_api as schedule
from utils import helpers
from utils.helpers.class_helper import assert_detail_error

logger = logging.getLogger(__name__)


@pytest.mark.api
@pytest.mark.schedule
@pytest.mark.educator
class TestScheduleEducator:
    """교육자만 가능한 수업일정 API (dev)."""

    @pytest.mark.p0
    def test_CS_003(
        self,
        schedule_dev_educator: schedule.ScheduleAPI,
    ):
        """[CS-003] POST /schedule — 필수 필드만으로 일정 생성 후 GET으로 검증, DELETE teardown


        Required body: classroom_id, summary, dt_start, dt_end (오늘 날짜).
        summary는 UUID 접두로 유일. 기대: POST 200 {}, GET 1건 일치, DELETE 200.
        """
        client = schedule_dev_educator
        day, dt_start_ge, dt_start_le = schedule.today_schedule_day_query()

        # 예: "QA-CS-003-a1b2c3d4e5f6789012345678abcdef01" (매 실행마다 hex 32자리가 달라짐)
        summary = f"QA-CS-003-{uuid.uuid4().hex}"

        create_resp = client.create_schedule( # 일정 생성
            summary=summary,
            dt_start=day,
            dt_end=day,
        )
        helpers.assert_status_code(create_resp, 200)
        assert create_resp.json() == {}, f"POST body expected {{}}, got {create_resp.text!r}"

        schedule_id: str | None = None
        try:
            get_resp = client.get_schedule( # 제대로 만들었는지 확인을 위해 조회
                dt_start_ge=dt_start_ge,
                dt_start_le=dt_start_le,
                count=schedule.SCHEDULE_COUNT_MAX,
            )
            helpers.assert_status_code(get_resp, 200)
            body = get_resp.json()
            assert isinstance(body, list), f"GET /schedule must return array, got {type(body)}"

            matches = [item for item in body if item.get("summary") == summary]
            assert len(matches) == 1, ( # 1건만 조회되어야 함(uuid 중복 방지)
                f"summary={summary!r} 일정 1건 기대, 실제 {len(matches)}건 "
                f"(조회 구간 {day}, 전체 {len(body)}건)"
            )
            item = matches[0]
            schedule_id = str(item["id"])

            assert schedule.extract_date(item["dt_start"]) == day
            assert schedule.extract_date(item["dt_end"]) == day
            tags = item.get("tags") or {}
            assert str(tags.get("classroom_id")) == str(client.classroom_id), (
                f"tags.classroom_id {tags.get('classroom_id')!r} != {client.classroom_id!r}"
            )
        finally:
            if schedule_id:
                del_resp = client.delete_schedule(schedule_id) # 일정 삭제
                if del_resp.status_code != 200:
                    logger.warning(
                        "CS-003 teardown DELETE /schedule/%s failed: %s %s",
                        schedule_id,
                        del_resp.status_code,
                        del_resp.text,
                    )
                else:
                    helpers.assert_status_code(del_resp, 200)

    @pytest.mark.p0
    def test_CS_004(
        self,
        schedule_dev_educator: schedule.ScheduleAPI,
    ):
        """[CS-004] DELETE /schedule — 삭제 후 GET으로 미존재 검증 (State Transition)

        Setup: CS-003과 동일 POST(UUID summary, 오늘). dev 교육자
        본 TC: DELETE 200 → GET 동일 summary 0건. teardown 불필요
        """
        client = schedule_dev_educator
        day, dt_start_ge, dt_start_le = schedule.today_schedule_day_query()
        summary = f"QA-CS-004-{uuid.uuid4().hex}"

        create_resp = client.create_schedule(
            summary=summary,
            dt_start=day,
            dt_end=day,
        )
        helpers.assert_status_code(create_resp, 200)
        assert create_resp.json() == {}, f"POST body expected {{}}, got {create_resp.text!r}"

        get_before = client.get_schedule(
            dt_start_ge=dt_start_ge,
            dt_start_le=dt_start_le,
            count=schedule.SCHEDULE_COUNT_MAX,
        )
        helpers.assert_status_code(get_before, 200)
        body_before = get_before.json()
        assert isinstance(body_before, list), f"GET /schedule must return array, got {type(body_before)}"

        matches_before = [item for item in body_before if item.get("summary") == summary]
        assert len(matches_before) == 1, (
            f"삭제 전 summary={summary!r} 일정 1건 기대, 실제 {len(matches_before)}건"
        )
        schedule_id = str(matches_before[0]["id"])

        del_resp = client.delete_schedule(schedule_id)
        helpers.assert_status_code(del_resp, 200)

        get_after = client.get_schedule(
            dt_start_ge=dt_start_ge,
            dt_start_le=dt_start_le,
            count=schedule.SCHEDULE_COUNT_MAX,
        )
        helpers.assert_status_code(get_after, 200)
        body_after = get_after.json()
        assert isinstance(body_after, list), f"GET /schedule must return array, got {type(body_after)}"

        matches_after = [item for item in body_after if item.get("summary") == summary]
        assert len(matches_after) == 0, (
            f"DELETE 후 summary={summary!r} 일정 0건 기대, 실제 {len(matches_after)}건 "
            f"(schedule_id={schedule_id}, 조회 구간 {day})"
        )

    @pytest.mark.learner
    def test_CS_AUTH_03(
        self,
        schedule_dev_learner: schedule.ScheduleAPI,
    ):
        """[CS-AUTH-03] POST /schedule — dev 학습자 토큰으로 교육자 전용 생성 API 호출 시 거부

        CS-003과 동일 body(UUID summary, 오늘 dt_start/dt_end). Bearer는 dev 학습자.
        기대: POST 403, code has_no_permission, message You have no permission,
        GET 동일 summary·오늘 구간 0건(미생성). teardown 불필요.
        """
        client = schedule_dev_learner
        day, dt_start_ge, dt_start_le = schedule.today_schedule_day_query()
        summary = f"QA-CS-AUTH-03-{uuid.uuid4().hex}"

        create_resp = client.create_schedule(
            summary=summary,
            dt_start=day,
            dt_end=day,
        )
        helpers.assert_status_code(create_resp, 403)
        body = create_resp.json()
        assert isinstance(body, dict), f"403 응답은 JSON 객체여야 함: {type(body)}"
        assert not isinstance(body, list), "권한 거부 시 일정 JSON 배열이 반환되면 안 됨"
        helpers.assert_json_value(body, "code", "has_no_permission")
        helpers.assert_json_value(body, "message", "You have no permission")

        get_resp = client.get_schedule(
            dt_start_ge=dt_start_ge,
            dt_start_le=dt_start_le,
            count=schedule.SCHEDULE_COUNT_MAX,
        )
        helpers.assert_status_code(get_resp, 200)
        schedule_body = get_resp.json()
        assert isinstance(schedule_body, list), f"GET /schedule must return array, got {type(schedule_body)}"

        matches = [item for item in schedule_body if item.get("summary") == summary]
        assert len(matches) == 0, (
            f"POST 거부 후 summary={summary!r} 일정이 {len(matches)}건 조회됨 — 생성되면 안 됨 "
            f"(조회 구간 {day}, 전체 {len(schedule_body)}건)"
        )

    def test_CS_PARAM_05(
        self,
        schedule_dev_educator: schedule.ScheduleAPI,
    ):
        """[CS-PARAM-05] POST /schedule — body none(미전송) 시 422

        CS-PARAM-01~04(GET query 누락)의 POST 대칭. dev 교육자 only.
        기대: 422, detail 1건, type missing, loc body, msg Field required.
        """
        client = schedule_dev_educator

        resp = client.post(schedule.ScheduleAPI.BASE_PATH)

        helpers.assert_status_code(resp, 422)
        body = resp.json()
        assert not isinstance(body, list), "body 누락 시 일정 배열이 반환되면 안 됨"
        helpers.assert_list_length(body["detail"], 1)
        assert_detail_error(body, "missing", ["body"])
        helpers.assert_json_value(body, "detail[0].msg", "Field required")
