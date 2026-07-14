# tests/api/schedule/test_schedule_common.py
"""수업일정(Schedule) 공통 API 테스트 — 학습자·교육자가 동일한 응답 구조를 검증하는 기능

공통 API는 검증 로직이 같고 역할(target)만 다르므로 역할별로 테스트를 따로 만들지 않고
하나의 테스트를 target으로 파라미터화한다 (tests/api/board/test_board_common.py와 동일한 패턴)
  - 학습자 → prod (본인 단일계정)
  - 교육자 → dev  (교육자 계정은 dev에만 존재)

역할별로 달라지는 건 호출 엔드포인트(호스트)와 인증 토큰뿐이고 응답에 대한 검증 로직은 동일하다

명세 대조 기준: Notion "수업 일정" 시트 CS-001 (특정 기간 수업 일정 조회)
"""
import calendar
import os
from datetime import date

import pytest

from api.schemas.schedule_schema import ScheduleSchemas
from utils.assertions import assert_valid_schema


def _current_month_range() -> tuple[str, str]:
    """오늘 기준 이번 달 1일부터 말일까지를 ISO 8601 datetime(밀리초 + UTC "Z") 형식으로 반환

    조회 기간을 고정값으로 박아두면 시간이 지날수록 실제 존재하는 일정 데이터와 어긋나
    테스트가 항상 성공하거나 항상 실패하는 상태로 굳어버린다
    그래서 실행 시점의 "이번 달"을 매번 새로 계산해 조회 기간으로 사용한다
    """
    today = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    start = f"{today.year:04d}-{today.month:02d}-01T00:00:00.000Z"
    end = f"{today.year:04d}-{today.month:02d}-{last_day:02d}T23:59:59.999Z"
    return start, end


_DEFAULT_DT_START_GE, _DEFAULT_DT_START_LE = _current_month_range()

# TC 사전조건("dt_start_ge, dt_start_le에 일정이 존재하는 유효한 기간")을 만족하는 값
# 날짜가 아닌 ISO 8601 datetime(밀리초 + UTC "Z") 형식이어야 한다
# 기본값은 실행 시점 기준 이번 달 1일~말일이며 SCHEDULE_DT_START_GE/LE 환경변수로 덮어쓸 수 있다
_DT_START_GE = os.getenv("SCHEDULE_DT_START_GE", _DEFAULT_DT_START_GE)
_DT_START_LE = os.getenv("SCHEDULE_DT_START_LE", _DEFAULT_DT_START_LE)
_COUNT = int(os.getenv("SCHEDULE_COUNT", "3"))

# 공통 테스트의 역할(target) 파라미터
# id에 대응 TC 번호를 남겨 시트와 추적 가능하게 한다
SCHEDULE_TARGETS = [
    pytest.param("schedule_prod_learner", marks=pytest.mark.learner, id="CS-001-learner-prod"),
    pytest.param("schedule_dev_educator", marks=pytest.mark.educator, id="CS-001-educator-dev"),
]


def _extract_date(value: str) -> str:
    """ISO 날짜/datetime 문자열에서 앞 10자(YYYY-MM-DD)만 추출한다

    dt_start/dt_end/rrule.until은 item에 따라 "2026-03-23"(날짜만) 또는
    "2026-03-23T03:00:00.000Z"(전체 datetime 등)가 섞여 있다
    타임존 변환의 복잡도를 피하고 일(day) 단위로만 겹침을 비교하기 위해 앞 10자만 사용한다
    """
    return value[:10]


_QUERY_START_DATE = _extract_date(_DT_START_GE)
_QUERY_END_DATE = _extract_date(_DT_START_LE)


def _item_active_date_range(item: dict) -> tuple[str, str]:
    """item이 실제로 존재(활성)하는 기간을 [시작일, 종료일](YYYY-MM-DD)로 계산한다

    - 반복일정(rrule 존재)이고 종료 조건(until)이 있으면: [dt_start, until]
      (실측 결과 dt_start는 "시리즈가 최초 시작한 날짜"이고 until이 시리즈의 실제 종료일이다
       회차(byday)/예외일(exdate)까지 정확히 펼쳐 계산하는 건 하지 않고 시리즈 활성 구간
       자체가 요청 기간과 겹치는지까지만 검증한다)
    - 반복일정인데 until이 없으면(무한 반복 등): 종료일을 알 수 없으므로 요청 종료일로 간주해
      "시작일이 요청 종료일 이전이면 겹침"으로 판단되게 한다
    - 반복이 아닌 단발성 일정이면: [dt_start, dt_end]
    """
    start = _extract_date(item["dt_start"])
    rrule = item.get("rrule")
    if rrule and rrule.get("until"):
        end = _extract_date(rrule["until"])
    elif rrule:
        end = _QUERY_END_DATE
    else:
        end = _extract_date(item["dt_end"])
    return start, end


@pytest.mark.api
@pytest.mark.schedule
class TestScheduleCommon:
    """공통 수업일정 API: 학습자·교육자 모두 동일하게 동작해야 하는 시나리오"""

    @pytest.mark.p0
    @pytest.mark.parametrize("client_fixture", SCHEDULE_TARGETS)
    def test_CS_001(self, request, client_fixture):
        """[CS-001] 수업일정 조회 시 정상 응답 검증 학습자=prod(본인계정) 교육자=dev

        기대값(명세서 'CS-001' 행 기준):
          - 두 응답 모두 status_code == 200
          - JSON 배열 응답이며 1건 이상 ~ count 이하
          - 각 item이 스키마(ScheduleSchemas.SCHEDULE_LIST_SCHEMA)를 만족함
            (필수 필드 존재 + 타입 + 예상 밖 필드 유입 여부까지 한 번에 검증)
          - 모든 item의 tags.classroom_id가 요청한 classroom_id와 일치
          - 모든 item의 활성 기간(_item_active_date_range)이 요청 기간과 겹쳐야 함

        [조회 기간(dt_start_ge~dt_start_le)을 이번 달로 매번 새로 계산하는 이유]
        조회 기간을 고정값으로 두면 시간이 지날수록 실제 일정 데이터와 어긋나
        테스트가 항상 성공하거나 항상 실패하는 상태로 고정되어 버린다
        그래서 _current_month_range()로 실행 시점 기준 이번 달 1일~말일을 매번 계산해 사용한다

        [일정 기간 검증 방식에 대한 설계 노트]
        item.dt_start는 "반복일정 시리즈가 최초 시작한 날짜"이지 요청 기간에 실제로 걸리는
        회차의 날짜가 아니다 그래서 item.dt_start가 요청 범위 안에 있는지를 그대로 비교하면
        정상 데이터인데도 항상 실패하는 경우가 생긴다 (예: 시리즈는 몇 달 전에 시작했지만
        지금도 계속 진행 중인 반복일정)

        대신 아래처럼 item이 "활성 상태로 존재하는 기간"과 요청 기간이 겹치는지(overlap)를
        비교한다: 반복일정은 [dt_start, rrule.until]을 단발성 일정은 [dt_start, dt_end]를
        활성 구간으로 보고 요청 구간과 하루라도 겹치면 통과시킨다
        (주의: byday/exdate까지 반영해 실제 회차를 정확히 펼쳐 계산하진 않으므로
         "시리즈가 이 기간에 존재했었는지"까지만 검증하는 다소 느슨한 검증이다)

        이미 종료된 반복일정(활성 기간이 이번 달보다 먼저 끝난 경우)이 조회 결과에 섞여 나오면
        이 겹침 검증에서 FAIL 하는 게 정상
        """
        client = request.getfixturevalue(client_fixture)
        classroom_id = client.classroom_id

        res = client.get_schedule(
            dt_start_ge=_DT_START_GE,
            dt_start_le=_DT_START_LE,
            classroom_id=classroom_id,
            count=_COUNT,
        )

        assert res.status_code == 200, res.text
        body = res.json()

        assert isinstance(body, list), f"응답이 JSON 배열이 아님: {type(body)}"
        assert 1 <= len(body) <= _COUNT, f"응답 개수({len(body)})가 1~{_COUNT} 범위를 벗어남"

        # 구조(shape) 검증: 필수 필드 존재 + 타입 + 예상 밖 필드 유입 여부를 jsonschema로 한 번에 검증
        assert_valid_schema(body, ScheduleSchemas.SCHEDULE_LIST_SCHEMA)

        for item in body:
            tags = item.get("tags", {})
            item_classroom_id = tags.get("classroom_id")
            assert str(item_classroom_id) == str(classroom_id), (
                f"item의 tags.classroom_id({item_classroom_id})가 요청값({classroom_id})과 불일치"
            )

            item_start, item_end = _item_active_date_range(item)
            overlaps = item_start <= _QUERY_END_DATE and _QUERY_START_DATE <= item_end
            assert overlaps, (
                f"'{item.get('summary')}' 일정의 활성 기간({item_start}~{item_end})이 "
                f"요청 기간({_QUERY_START_DATE}~{_QUERY_END_DATE})과 겹치지 않음 "
                f"(item id={item.get('id')})"
            )
