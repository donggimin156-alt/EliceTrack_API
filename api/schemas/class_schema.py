from typing import Any, Final

# 상수(Schema) 네임스페이스 역할만 수행하는 모듈이므로 logger는 선언하지 않습니다.


class ClassSchemas:
    """
    Classroom Course API 응답 검증을 위한 JSON Schema 정의 클래스.

    user_schema.py(UserSchemas)와 동일한 컨벤션을 따른다.
    각 property는 값이 null이어도 통과해야 하므로 type을 지정하지 않고,
    "required"로 키 존재 여부만 강제한다.
    (classroom_course_progress_data 내부 구조는 별도로 PROGRESS_DATA_SCHEMA에서 검증한다.)
    """

    COURSE_TOP_LEVEL_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "id": {},
            "course_id": {},
            "title": {},
            "short_description": {},
            "description": {},
            "course_type": {},
            "logo_file_url": {},
            "image_file_url": {},
            "status": {},
            "categories": {},
            "programming_languages": {},
            "level": {},
            "classroom_course_status": {},
            "classroom_course_progress_data": {"type": "object"},
            "created": {},
            "modified": {},
            "pass_info": {},
        },
        "required": [
            "id", "course_id", "title", "short_description", "description",
            "course_type", "logo_file_url", "image_file_url", "status",
            "categories", "programming_languages", "level",
            "classroom_course_status", "classroom_course_progress_data",
            "created", "modified", "pass_info",
        ],
    }

    PROGRESS_DATA_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "progress": {},
            "total_material_cnt": {},
            "completed_material_cnt": {},
        },
        "required": ["progress", "total_material_cnt", "completed_material_cnt"],
    }

    TASK_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "status": {"type": "string"},
            "result": {},
        },
        "required": ["id", "status", "result"],
    }