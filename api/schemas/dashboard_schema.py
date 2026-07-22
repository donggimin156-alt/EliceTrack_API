from typing import Any, Final


class DashboardSchemas:
    """Dashboard API(학습현황/리포트) 응답 검증용 JSON Schema. ClassSchemas와 동일 컨벤션."""

    ACCOUNT_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "email": {"type": "string"},
            "fullname": {"type": "string"},
            "profile_url": {},
        },
        "required": ["id", "email", "fullname", "profile_url"],
    }

    STUDENT_PROGRESS_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "account": {"type": "object"},
            "learning_progress": {},
            "test_score": {},
            "practice_score": {},
            "submit_cnt": {},
            "test_completed_cnt": {},
            "learning_completed": {},
        },
        "required": [
            "account", "learning_progress", "test_score",
            "practice_score", "submit_cnt",
            "test_completed_cnt", "learning_completed",
        ],
    }

    REPORT_TOKEN_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {"download_token": {"type": "string"}},
        "required": ["download_token"],
    }