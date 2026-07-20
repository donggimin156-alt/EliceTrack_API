# api/schemas/classhome_schema.py
from typing import Any, Final


class ClasshomeSchemas:
    """클래스 홈 API (GET /classroom) 응답 검증 스키마."""

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


class DashboardSchemas:
    """학습현황 API (GET /classroom/{id}, GET /student/{id}) 응답 검증 스키마."""

    # ── GET /classroom/{class_id} ─────────────────────────────────────────────
    # API가 소수점 값을 문자열로 반환하며("0.15"), 활동 없을 시 score는 null 가능.
    CLASSROOM_SUMMARY_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "learning_progress":  {"type": "string"},
            "practice_score":     {"type": ["string", "null"]},
            "test_score":         {"type": ["string", "null"]},
            "submit_cnt":         {"type": "integer"},
            "test_completed_cnt": {"type": "integer"},
        },
        "required": [
            "learning_progress",
            "practice_score",
            "test_score",
            "submit_cnt",
            "test_completed_cnt",
        ],
    }

    # ── GET /student/{account_id} ─────────────────────────────────────────────
    _ACCOUNT_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "id":       {"type": "integer"},
            "email":    {"type": "string"},
            "fullname": {"type": "string"},
        },
        "required": ["id", "email", "fullname"],
    }

    # API가 learning_progress를 문자열로 반환("87.81"), score 필드는 null 가능.
    STUDENT_LEARNING_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "learning_progress": {"type": "string"},
            "account":           _ACCOUNT_SCHEMA,
        },
        "required": ["learning_progress", "account"],
    }
