# builders/user_builder.py
from api.schemas.user_dto import CreateUserRequest
from utils.data_generator import get_faker

# 본 모듈은 순수하게 테스트용 DTO 객체를 조립(Build)하는 역할만 수행하므로,
# 부작용(Side Effect) 방지 및 단일 책임 원칙(SRP)에 따라 logger를 선언하지 않습니다.


class UserBuilder:
    """
    API 요청에 사용되는 DTO(Data Transfer Object)를 조립(Build)하는 전담 클래스.
    
    순수 데이터 생성 유틸리티(Faker 등)와 비즈니스 도메인 DTO 생성을 분리하여 
    코드 응집도를 높이고 테스트 데이터 생성 코드의 중복을 방지합니다.
    """

    @staticmethod
    def build_create_request(locale: str = "en_US") -> CreateUserRequest:
        """
        랜덤 데이터를 활용하여 사용자 생성(POST) 요청용 DTO를 생성하여 반환합니다.
        
        Args:
            locale (str): 생성할 랜덤 데이터의 국가/언어 코드 (기본값: "en_US")
            
        Returns:
            CreateUserRequest: 랜덤한 이름(name)과 직업(job)이 채워진 DTO 객체
        """
        fake = get_faker(locale)
        
        return CreateUserRequest(
            name=fake.name(),
            job=fake.job()
        )