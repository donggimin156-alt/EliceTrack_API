# tests/api/schedule/test_schedule_educator.py
"""수업일정(Schedule) 교육자 전용 API — dev 교육자 계정·classroom 호스트."""
import logging
import uuid

import pytest

from api.endpoints import schedule_api as schedule
from utils import helpers

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
                count=40,
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
