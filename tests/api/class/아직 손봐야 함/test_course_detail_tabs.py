"""
P3: 개별 과목 상세 화면 - 상단 탭 전환
    (수업 목록 / 학습 현황 / 학습맵 / 과목 소개 / 과목 편집 / 과목 설정)

⚠️ 아래 테스트들은 각 탭 클릭 시 실제로 어떤 API가 호출되는지, 응답 스키마가
   무엇인지 Postman/DevTools로 아직 확인되지 않았다. 그래서 함수 정의와
   "무엇을 검증해야 하는지" + "무엇이 확인되지 않았는지"만 docstring으로
   남겨두고, pytest.mark.skip으로 CI에서는 스킵되도록 처리했다.
   실제 응답을 확인한 뒤 skip 마커를 제거하고 본문을 구현할 것.
"""

import pytest


@pytest.mark.api
@pytest.mark.educator
class TestCourseLectureListTab:
    @pytest.mark.skip(reason="실제 호출 엔드포인트/응답 스키마 미실증")
    def test_lecture_list_returns_expected_lectures(self):
        """
        [수업 목록 탭]
        과목 상세 화면에서 "수업 목록" 탭 클릭 시 호출되는 API의 응답에
        수업(lecture) 목록이 순서/개수와 함께 정상적으로 내려오는지 검증해야 함.

        ⚠️ 확인되지 않은 부분:
        - 어떤 엔드포인트가 실제로 호출되는지 (org/lecture_page/list 계열로
          추정되나, classroom 쪽 course_id와 org 쪽 course_id의 매핑 관계가
          아직 확인되지 않음)
        - 응답 스키마(필드명, nested 구조)
        - "수업 4개 · 수업자료 25개" 같은 집계값이 이 응답에 포함되는지,
          별도 API로 내려오는지
        """
        pass

    @pytest.mark.skip(reason="실제 호출 엔드포인트/응답 스키마 미실증")
    def test_lecture_material_count_matches_summary(self):
        """
        [수업 목록 탭 - 집계 숫자]
        상단에 노출되는 "수업 N개 · 수업자료 N개" 숫자가 실제 lecture/material
        개수와 일치하는지 검증해야 함.

        ⚠️ 확인되지 않은 부분: 집계값을 내려주는 API, material 집계 범위
        (note/video/pdf/exercise/quiz 등 전체 material_type 포함 여부)
        """
        pass


@pytest.mark.api
@pytest.mark.educator
class TestCourseLearningMapTab:
    @pytest.mark.skip(reason="학습맵 전용 API 존재 여부 자체가 미확인")
    def test_learning_map_returns_expected_structure(self):
        """
        [학습맵 탭]
        학습맵 탭 클릭 시 노출되는 구조(수업 간 선후관계/트리 등)를 검증해야 함.

        ⚠️ 확인되지 않은 부분: 현재 API 스펙 문서(강의실/LXP 스펙)에서
        "학습맵"에 대응하는 엔드포인트가 명시적으로 식별되지 않음.
        브라우저 네트워크 탭 캡처가 선행되어야 함.
        """
        pass


@pytest.mark.api
@pytest.mark.educator
class TestCourseIntroTab:
    @pytest.mark.skip(reason="과목 소개 전용 응답 필드 범위 미확인")
    def test_course_intro_returns_expected_fields(self):
        """
        [과목 소개 탭]
        과목 소개(제목/설명/커리큘럼 등)가 정상 노출되는지 검증해야 함.

        ⚠️ 확인되지 않은 부분: test_course_detail.py의 get_course 단건 조회
        응답에 포함된 필드만으로 충분한지, 별도 조회(org/course/get 등)가
        필요한지 확인되지 않음
        """
        pass


@pytest.mark.api
@pytest.mark.educator
class TestCourseEditEntry:
    @pytest.mark.skip(reason="요청 페이로드/프리필 방식 미확인")
    def test_course_edit_toggle_navigates_to_edit_screen(self):
        """
        [과목 편집 진입]
        "과목 편집" 토글 클릭 시 편집 화면으로 이동하고, 기존 값이 프리필되어
        내려오는지 검증해야 함 (org/course/edit 계열로 추정).

        ⚠️ 확인되지 않은 부분:
        - org/course/edit이 스펙상 POST 전용으로 보이는데, 프리필용 별도 GET이
          존재하는지 확인 필요
        - 필수 필드가 매우 많음(leaderboard_info, completion_info, target_audience 등)
          해피패스 하나 구성하려면 실제 요청 페이로드를 먼저 캡처해야 함
        """
        pass


@pytest.mark.api
@pytest.mark.educator
class TestCourseSettingsEntry:
    @pytest.mark.skip(reason="과목 편집과의 API 구분 여부 미확인")
    def test_course_settings_entry_returns_expected_options(self):
        """
        [과목 설정 진입]
        "과목 설정" 클릭 시 노출되는 설정 항목(공개 여부, 수강 정책 등)이
        실제 과목 데이터와 일치하는지 검증해야 함.

        ⚠️ 확인되지 않은 부분: "과목 편집"과 "과목 설정"이 동일 화면/API인지
        별개인지 UI상 구분이 명확하지 않아, 실제 클릭 후 네트워크 캡처가
        선행되어야 함
        """
        pass