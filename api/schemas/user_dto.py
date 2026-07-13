# api/schemas/user_dto.py
from pydantic import BaseModel, EmailStr, Field

# 데이터의 구조(Schema/DTO)만 정의하는 모듈이므로 logger는 선언하지 않습니다.


class CreateUserRequest(BaseModel):
    """
    사용자 생성(POST) 요청 시 사용되는 페이로드 데이터 전송 객체(DTO).
    
    데이터의 유효성 검증(Validation)과 IDE 자동 완성을 지원합니다.
    """
    name: str = Field(..., description="생성할 사용자 이름", min_length=1)
    job: str = Field(..., description="생성할 사용자 직업", min_length=1)


class UpdateUserRequest(BaseModel):
    """
    사용자 수정(PUT/PATCH) 요청 페이로드 모델.
    
    부분 수정(PATCH)을 지원하기 위해 모든 필드를 선택적(Optional)으로 처리합니다.
    """
    # Python 3.10+ 컨벤션에 맞춰 Optional[str] 대신 str | None 을 사용합니다.
    name: str | None = Field(default=None, description="수정할 사용자 이름")
    job: str | None = Field(default=None, description="수정할 사용자 직업")


class CreateUserResponse(BaseModel):
    """
    사용자 생성(POST) 성공 시 반환되는 응답 페이로드 모델.
    
    API 응답 딕셔너리를 해당 클래스로 매핑하여 속성(Attribute) 방식으로 안전하게 접근할 수 있도록 돕습니다.
    """
    name: str = Field(..., description="생성된 사용자 이름")
    job: str = Field(..., description="생성된 사용자 직업")
    id: str = Field(..., description="발급된 고유 식별자 ID")
    createdAt: str = Field(..., description="생성된 시간(ISO 8601 포맷)")


class UserData(BaseModel):
    """단일 사용자 상세 정보(Data 객체) 모델."""
    id: int = Field(..., description="사용자 고유 ID")
    email: EmailStr = Field(..., description="사용자 이메일 주소")
    first_name: str = Field(..., description="사용자 이름")
    last_name: str = Field(..., description="사용자 성")
    avatar: str = Field(..., description="아바타 이미지 URL")


class SupportData(BaseModel):
    """API 지원 정보 모델."""
    url: str = Field(..., description="지원 페이지 URL")
    text: str = Field(..., description="지원 안내 텍스트")


class GetUserResponse(BaseModel):
    """단일 사용자 조회(GET) 성공 응답 전체 구조 모델."""
    data: UserData = Field(..., description="사용자 상세 데이터")
    support: SupportData = Field(..., description="API 지원 정보")