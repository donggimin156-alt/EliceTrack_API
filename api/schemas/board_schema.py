# api/schemas/board_schema.py
from typing import Any, Final

# 상수(Schema) 네임스페이스 역할만 수행하는 모듈이므로 logger는 선언하지 않습니다.


class BoardSchemas:
    """게시판(Board) API 응답 검증을 위한 JSON Schema 정의 클래스.

    게시판은 Swagger/OpenAPI가 없어 스키마를 노출하지 않으므로, 아래 스키마는
    dev/prod 실측 응답(docs/brd_실측_responses*.json)을 기준으로 작성했다.

    설계 방침
      - null이 관측된 필드(modified_datetime, read_datetime, course_id, profile_url 등)는
        ["<type>", "null"] 로 nullable 허용한다.
      - 역할(학습자/교육자)·상태에 따라 있을 수도 없을 수도 있는 부가 필드가 있어,
        처음에는 additionalProperties를 열어둔다(예상 밖 필드가 섞여도 통과).
        엄격 검증이 필요해지면 각 스키마에 "additionalProperties": False 를 추가한다.
      - required는 모든 실측 샘플에서 항상 존재가 확인된 핵심 필드만 잡는다.

    게시판 규약: HTTP는 항상 200, 성공/실패는 body `_result.status`(ok/fail)로 판정.

    해당 클래스는 인스턴스화하지 않고 상수 네임스페이스(Namespace) 용도로만 사용.
    """

    # 모든 게시판 응답 공통 래퍼(_result)
    RESULT: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["ok", "fail"]},
            "status_code": {"type": "integer"},
            "reason": {"type": ["string", "null"]},
        },
        "required": ["status"],
    }

    # 게시글/댓글 작성자(user) 객체.
    # ※ 실측상 email/display_email이 그대로 노출됨(= BRD-013/014의 이메일 노출 이슈).
    #    스키마는 "구조"만 검증하므로 통과되며, 노출 여부 판정은 별도 보안 테스트가 담당한다.
    _USER: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "fullname": {"type": "string"},
            "firstname": {"type": "string"},
            "lastname": {"type": "string"},
            "profile_url": {"type": ["string", "null"]},
            "course_role": {"type": "integer"},
            "email": {"type": "string"},
            "display_email": {"type": "string"},
        },
        "required": ["id", "fullname", "course_role"],
    }

    # 게시글 단건조회(board/article/get) 응답의 board_article 객체
    BOARD_ARTICLE: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "title": {"type": "string"},
            "content": {"type": "string"},
            "classroom_id": {"type": "string"},
            "course_id": {"type": ["integer", "null"]},
            "user": _USER,
            "created_datetime": {"type": "integer"},
            "modified_datetime": {"type": ["integer", "null"]},
            "is_secret": {"type": "boolean"},
            "is_liked": {"type": "boolean"},
            "board_article_like_count": {"type": "integer"},
            "read_datetime": {"type": ["integer", "null"]},
            "article_comment_count": {"type": "integer"},
            "article_read_users_count": {"type": "integer"},
            "article_attachments": {"type": "array"},
        },
        "required": [
            "id", "title", "content", "classroom_id",
            "user", "created_datetime", "is_secret",
        ],
    }

    # 게시글 목록(board/article/list) 응답의 board_articles[] item.
    # 목록 item에는 user 객체와 함께 fullname/firstname/... 플랫 필드도 함께 온다(실측).
    _BOARD_ARTICLE_LIST_ITEM: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "title": {"type": "string"},
            "user": {"type": "object"},
            "content_short": {"type": "string"},
            "created_datetime": {"type": "integer"},
            "modified_datetime": {"type": ["integer", "null"]},
            "updated_datetime": {"type": ["integer", "null"]},
            "is_updated": {"type": "boolean"},
            "is_secret": {"type": "boolean"},
            "is_liked": {"type": "boolean"},
            "board_article_like_count": {"type": "integer"},
            "read_datetime": {"type": ["integer", "null"]},
            "article_comment_count": {"type": "integer"},
            "article_read_users_count": {"type": "integer"},
            "article_attachment_count": {"type": "integer"},
            "course_role": {"type": "integer"},
            "fullname": {"type": "string"},
            "firstname": {"type": "string"},
            "lastname": {"type": "string"},
            "profile_url": {"type": ["string", "null"]},
        },
        "required": ["id", "title", "created_datetime", "is_secret"],
    }

    BOARD_ARTICLE_LIST: Final[dict[str, Any]] = {
        "type": "array",
        "items": _BOARD_ARTICLE_LIST_ITEM,
    }

    # 댓글 단건조회(board/article/comment/get) 응답의 article_comment 객체
    ARTICLE_COMMENT: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "content": {"type": "string"},
            "user": _USER,
            "board_article_id": {"type": "integer"},
            "created_datetime": {"type": "integer"},
            "modified_datetime": {"type": ["integer", "null"]},
            "is_liked": {"type": "boolean"},
            "comment_like_count": {"type": "integer"},
        },
        "required": ["id", "content", "user", "board_article_id", "created_datetime"],
    }
