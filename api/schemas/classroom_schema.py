# api/schemas/classroom_schema.py
from typing import Any, Final


class ClassroomSchemas:
    """클래스 홈(Classroom) API 응답 검증을 위한 JSON Schema 정의 클래스."""

    _CLASSROOM_ITEM_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "id":   {"type": "string"},
            "name": {"type": "string"},
        },
        "required": ["id", "name"],
    }

    CLASSROOM_LIST_SCHEMA: Final[dict[str, Any]] = {
        "type": "array",
        "items": _CLASSROOM_ITEM_SCHEMA,
    }
