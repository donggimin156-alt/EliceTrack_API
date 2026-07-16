import pytest

from api.endpoints.class_api import ClassApi


@pytest.fixture(scope="session")
def class_api(prod_learner) -> ClassApi:
    """
    원래 테스트의 CLASSROOM_ID가 PROD_CLASSROOM_ID와 일치하므로,
    TARGET 환경변수를 따라가는 elice_learner 대신
    prod로 고정된 prod_learner를 사용한다.

    base_url은 ClassApi.BASE_URL 클래스 상수로 고정되어 있으므로 여기서 넘기지 않는다.
    """
    return ClassApi(
        session=prod_learner.session,
        classroom_id=prod_learner.classroom_id,
    )


@pytest.fixture(scope="session")
def total_course_count(class_api) -> int:
    """
    매직넘버(TOTAL_COURSE_COUNT = 20) 대신, 세션 시작 시
    실제 전체 과목 수를 한 번 조회해서 동적으로 계산한다.
    """
    resp = class_api.get_course_list(skip=0, count=9999)
    assert resp.status_code == 200, "전체 과목 수를 조회하기 위한 사전 요청이 실패했습니다."
    return len(resp.json())


@pytest.fixture
def course_list(class_api):
    """
    skip=0, count=10 기본 목록 응답 (여러 테스트가 공유).

    응답을 만드는 시점에 바로 200 여부를 검증한다.
    (autouse + teardown 시점 검사 방식은 pytest의 LIFO teardown 순서 때문에
    "fixture가 이미 정리됨" 에러가 나서, 생성 시점 검증으로 바꿨다.)
    """
    resp = class_api.get_course_list(skip=0, count=10)
    assert resp.status_code == 200, f"course_list 응답 상태 코드 이상: {resp.status_code}"
    return resp


@pytest.fixture
def full_course_list(class_api, total_course_count):
    """전체 과목 수만큼 조회한 응답 (Business 검증용). 생성 시점에 200 검증."""
    resp = class_api.get_course_list(skip=0, count=total_course_count)
    assert resp.status_code == 200, f"full_course_list 응답 상태 코드 이상: {resp.status_code}"
    return resp


@pytest.fixture
def course_data(course_list):
    """course_list.json() 반복 호출 제거용. 테스트에서는 이 fixture만 받아서 쓴다."""
    return course_list.json()


@pytest.fixture
def full_course_data(full_course_list):
    """full_course_list.json() 반복 호출 제거용."""
    return full_course_list.json()