# api/schemas/schedule_schema.py
from typing import Any, Final

# 상수(Schema) 네임스페이스 역할만 수행하는 모듈이므로 logger는 선언하지 않습니다


class ScheduleSchemas:
    """수업일정(Schedule) API 응답 검증을 위한 JSON Schema 정의 클래스

    학습자/교육자 응답을 실제로 비교한 결과, 필드 차이는 "역할"이 아니라
    "일정 종류"(코스 강의 / 자유 일정 등)에 따라 생기는 걸로 확인됐다
    (예: cohort_id/course_id/lecture_id/lectureroom_id/educator_member_id는
     학습자·교육자 모두에게서 있는 응답과 없는 응답이 섞여 있었음)

    그래서 레벨별로 엄격도를 다르게 뒀다
      - item 최상위: 모든 샘플에서 항상 존재가 확인된 필드만 required로 엄격하게 잡고,
        additionalProperties=False로 예상 밖 필드 유입을 잡아낸다
        (다만 역할에 따라 있을 수도 없을 수도 있는 cohort_id/cohort_name은
         properties에 정의만 해두고 required에서는 빼서 둘 다 통과되게 한다)
      - tags 내부: course_id/lecture_id 등 일정 종류에 따라 들쭉날쭉한 필드가 많아
        모든 샘플에서 공통으로 확인된 classroom_id/organization_id만 required로 두고
        additionalProperties는 열어둬 다른 부가 필드가 섞여도 통과시킨다
      - rrule: null(단발성 일정) 또는 반복 규칙 object 둘 다 허용하고, object인 경우엔
        내부 필드(freq/until/count/interval/bymonth/byday/bymonthday/exdate)까지 검증한다
        (jsonschema는 instance 타입이 object가 아니면 properties/required를 검사하지
         않으므로 null일 때는 자동으로 통과된다)

    해당 클래스는 인스턴스화하지 않고 상수 네임스페이스(Namespace) 용도로만 사용
    """

    _RRULE_SCHEMA: Final[dict[str, Any]] = {
        "type": ["object", "null"],
        "properties": {
            "freq": {"type": "string"},
            "until": {"type": ["string", "null"]},
            "count": {"type": ["integer", "null"]},
            "interval": {"type": ["integer", "null"]},
            "bymonth": {"type": ["array", "null"]},
            "byday": {"type": ["array", "null"]},
            "bymonthday": {"type": ["array", "null"]},
            "exdate": {"type": ["array", "null"]},
        },
        "required": [
            "freq", "until", "count", "interval",
            "bymonth", "byday", "bymonthday", "exdate",
        ],
        "additionalProperties": False,
    }

    _TAGS_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "classroom_id": {"type": "string"},
            "organization_id": {"type": "integer"},
        },
        # course_id/lecture_id/lectureroom_id/educator_member_id/cohort_id/classroom_time_zone 등은
        # 일정 종류·역할에 따라 있을 수도 없을 수도 있어 required·additionalProperties로 막지 않는다
        "required": ["classroom_id", "organization_id"],
    }

    SCHEDULE_ITEM_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "uid": {"type": "string"},
            "recurrence_id": {"type": ["string", "null"]},
            "summary": {"type": "string"},
            "lecture_title": {"type": ["string", "null"]},
            "description": {"type": ["string", "null"]},
            "dt_start": {"type": "string"},
            "dt_end": {"type": "string"},
            "rrule": _RRULE_SCHEMA,
            "tags": _TAGS_SCHEMA,
            # 학습자 응답에서만 확인된 최상위 필드. 있어도 통과시키기 위해 properties에는 정의하되
            # 교육자 응답엔 없어도 실패하지 않도록 required에는 넣지 않는다
            "cohort_id": {"type": "string"},
            "cohort_name": {"type": "string"},
        },
        "required": [
            "id", "uid", "recurrence_id", "summary", "lecture_title",
            "description", "dt_start", "dt_end", "rrule", "tags",
        ],
        "additionalProperties": False,
    }

    # /schedule 응답은 item 배열이므로, 배열 전체를 한 번에 검증할 수 있는 스키마도 같이 제공한다
    SCHEDULE_LIST_SCHEMA: Final[dict[str, Any]] = {
        "type": "array",
        "items": SCHEDULE_ITEM_SCHEMA,
    }

    # REST GET course/get — prod·dev 실측 기준 공통 골격만 검증 (preference/menus 깊이·lectures 개수는 환경별로 다름)
    _COURSE_GET_RESULT: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "status_code": {"type": "integer"},
            "reason": {"type": ["string", "null"]},
        },
        "required": ["status", "status_code"],
    }

    _COURSE_GET_LECTURE_ITEM: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "title": {"type": "string"},
        },
        "required": ["id", "title"],
    }

    _COURSE_GET_COURSE: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "organization_id": {"type": "integer"},
            "title": {"type": "string"},
            "lectures": {
                "type": "array",
                "minItems": 0,
                "items": _COURSE_GET_LECTURE_ITEM,
            },
            "preference": {"type": "object"},
            "menus": {"type": "object"},
            "instructors": {"type": "array"},
        },
        "required": ["id", "organization_id", "title", "lectures"],
    }

    _COURSE_GET_SECTION: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "is_joined": {"type": "boolean"},
        },
        "required": ["id", "name", "is_joined"],
    }

    COURSE_GET_RESPONSE_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "_result": _COURSE_GET_RESULT,
            "course": _COURSE_GET_COURSE,
            "course_sections": {
                "type": "array",
                "items": _COURSE_GET_SECTION,
            },
            "course_role": {"type": "integer"},
            "has_past_course_role": {"type": "boolean"},
        },
        "required": ["_result", "course"],
    }
