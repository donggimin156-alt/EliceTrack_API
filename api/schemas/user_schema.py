# api/schemas/user_schema.py
from typing import Any, Final

# 상수(Schema) 네임스페이스 역할만 수행하는 모듈이므로 logger는 선언하지 않습니다.


class UserSchemas:
    """
    User API 응답 검증을 위한 JSON Schema 정의 클래스.
    
    DTO(Pydantic)로 역직렬화하기 전에 API 응답 페이로드의 전체적인 구조와 필수 키, 
    데이터 타입을 빠르고 엄격하게 1차 검증(Contract Testing)하는 역할을 수행합니다.
    해당 클래스는 인스턴스화하지 않고 상수 네임스페이스(Namespace) 용도로만 사용됩니다.
    """

    # Final 타입 힌트를 사용하여 런타임에 수정되지 않는 상수임을 명확히 합니다.
    CREATE_USER_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "job": {"type": "string"},
            "id": {"type": "string"},
            "createdAt": {"type": "string", "format": "date-time"}
        },
        "required": ["name", "job", "id", "createdAt"]
    }

    GET_USER_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "email": {"type": "string", "format": "email"},
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "avatar": {"type": "string", "format": "uri"}
                },
                "required": ["id", "email", "first_name", "last_name", "avatar"]
            },
            "support": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "format": "uri"},
                    "text": {"type": "string"}
                },
                "required": ["url", "text"]
            }
        },
        "required": ["data", "support"]
    }