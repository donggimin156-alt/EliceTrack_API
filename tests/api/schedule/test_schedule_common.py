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

SCHEDULE_TARGETS = [    # 수업일정 API 테스트 대상 역할 픽스처 매칭용
    pytest.param("schedule_prod_learner", marks=pytest.mark.learner, id="CS-001-learner-prod"),
    pytest.param("schedule_dev_educator", marks=pytest.mark.educator, id="CS-001-educator-dev"),
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
