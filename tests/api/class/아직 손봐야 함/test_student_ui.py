"""
학습자 권한 UI — 신규 API 해피케이스

⚠️ class_api.py / dashboard_api.py를 확인한 결과를 반영해 TC를 다시 짬.

기존 커버리지 (중복 작성하지 않음):
    - 과목 목록 조회/페이지네이션/진행률                 → test_class.py
    - 과목 추가→조회→삭제 풀 라이프사이클                → test_course_add_delete_happy_path.py
    - 학습현황 상세 (get_student_progress, course/cohort 지정) → test_student_dashboard.py
    - 학습현황 엑셀 리포트 토큰 발급/다운로드             → test_excel_report.py

이번에 실제 코드로 추가한 것 (client에 메서드가 존재함을 확인):
    - ClassApi.get_course               → 목록↔단건 조회 정합성 (P1)
    - DashboardAPI.get_classroom_summary → 반 전체 학습현황 (어떤 파일에서도 호출된 적 없음)
    - DashboardAPI.get_student          → 개인 학습현황 (course_id/cohort 없는 버전.
      get_student_progress와 같은 경로(/student/{account_id})지만 파라미터가 달라
      별도 오버로드로 취급, 역시 호출된 적 없음)

코드화하지 못한 것 (client에 대응 메서드 자체가 없음, 확인 완료):
    - 과목 내 수업(강의) 목록 조회
    - 과목 소개 콘텐츠 조회
    - 수업별 학습현황 표(과목 하위 lecture 단위 통계) 조회
    - 개별 수업 학습현황 + 수업자료별 점수 조회
    - 학습맵(트리 구조) 조회
  → class_api.py / dashboard_api.py 어디에도 위 기능에 대응하는 메서드가 없어,
    엔드포인트가 실제로 구현/노출되어 있는지 여부 자체가 확인 안 된 상태.
    스텁 함수로 남기고 사유를 명시함.
"""

import os

import pytest

from api.schemas.class_schema import ClassSchemas
from core.config import settings
from utils.helpers.api_assertions import assert_valid_schema

PROD_ENV = settings.elice_environments["prod"]
LEARNER_ACCOUNT_ID = os.getenv("PROD_LEARNER_ACCOUNT_ID") or PROD_ENV.get("LEARNER_ACCOUNT_ID")
CLASSROOM_ID = PROD_ENV["CLASSROOM_ID"]

pytestmark = pytest.mark.skipif(
    not LEARNER_ACCOUNT_ID,
    reason="PROD_LEARNER_ACCOUNT_ID not set; skipping learner-specific tests",
)


# ============================================================
# 실제 코드 작성 가능 — ClassApi.get_course (목록 ↔ 단건 조회 정합성)
# ============================================================
@pytest.mark.api
@pytest.mark.learner
class TestCourseDetailConsistency:
    """목록에서 본 과목을 단건 조회했을 때 데이터가 일치하는지 (P1 상세 진입 대응)"""

    def test_course_detail_progress_data_consistent_with_list(
        self, class_api, course_data, assert_response
    ):
        """TC-API-P1-03: 과목 단건 조회 결과의 진행률 정보(classroom_course_progress_data)가 목록 조회 시 반환된 진행률 정보와 일치하는지 검증한다."""
        list_item = course_data[0]
        course_id = list_item["course_id"]

        resp = class_api.get_course(course_id)
        detail = assert_response(resp, 200)

        list_progress = list_item.get("classroom_course_progress_data", {})
        detail_progress = detail.get("classroom_course_progress_data", {})
        assert list_progress == detail_progress, (
            f"목록의 진행률 데이터={list_progress} 와 상세 조회 진행률 데이터="
            f"{detail_progress} 가 일치해야 합니다."
        )


# ============================================================
# 실제 코드 작성 가능 — DashboardAPI.get_classroom_summary (신규)
# ============================================================
@pytest.mark.api
@pytest.mark.learner
class TestClassroomSummary:
    """반 전체 학습현황 (GET /classroom/{class_id}) — 이번에 처음 커버.

    ⚠️ 응답 스키마가 DashboardSchemas에 별도 정의되어 있지 않아, 구조 검증은
    최소한(200 응답 + dict 형태)으로만 수행한다. 필드 단위(예: 클래스 평균
    점수, 반 전체 진행률 등) 세부 검증은 스키마가 정의되면 보강이 필요하다.
    """

    def test_get_classroom_summary_returns_200(
        self, student_dashboard_api, assert_response
    ):
        """TC-API-CS-01: 반 전체 학습현황 API 요청 시 HTTP 200 OK와 함께 딕셔너리(dict) 형태의 응답을 반환하는지 검증한다."""
        resp = student_dashboard_api.get_classroom_summary(CLASSROOM_ID)
        data = assert_response(resp, 200)
        assert isinstance(data, dict), f"Expected dict response but got {type(data)}"

    def test_get_classroom_summary_response_not_empty(
        self, student_dashboard_api, assert_response
    ):
        """TC-API-CS-02: 반 전체 학습현황 API가 빈 응답이 아닌 유효한 데이터를 포함하여 반환하는지 검증한다."""
        resp = student_dashboard_api.get_classroom_summary(CLASSROOM_ID)
        data = assert_response(resp, 200)
        assert data, "반 전체 학습현황 응답이 비어있습니다."


# ============================================================
# 실제 코드 작성 가능 — DashboardAPI.get_student (course_id/cohort 없는 버전, 신규)
# ============================================================
@pytest.mark.api
@pytest.mark.learner
class TestStudentOverview:
    """개인 학습현황 개요 (GET /student/{account_id}, classroom_id만 지정)

    get_student_progress(course_id/cohort 필수)와는 다른 오버로드이며
    test_student_dashboard.py에서 다루지 않은 경로다.

    ⚠️ 이 호출 역시 대응 스키마가 DashboardSchemas에 없어 구조 검증만 수행.
    """

    def test_get_student_overview_returns_200(
        self, student_dashboard_api, assert_response
    ):
        """TC-API-SO-01: 특정 반(classroom_id)에 속한 학습자의 개인 학습현황 개요 조회 시 HTTP 200 OK 및 dict 형태 응답을 반환하는지 검증한다."""
        resp = student_dashboard_api.get_student(
            account_id=LEARNER_ACCOUNT_ID, classroom_id=CLASSROOM_ID
        )
        data = assert_response(resp, 200)
        assert isinstance(data, dict), f"Expected dict response but got {type(data)}"

    def test_get_student_overview_without_classroom_id_returns_200(
        self, student_dashboard_api, assert_response
    ):
        """TC-API-SO-02: 선택 파라미터인 classroom_id를 생략하고 학습자 계정 ID만으로 학습현황 개요를 조회할 때도 HTTP 200 OK를 반환하는지 검증한다."""
        resp = student_dashboard_api.get_student(account_id=LEARNER_ACCOUNT_ID)
        data = assert_response(resp, 200)
        assert isinstance(data, dict), f"Expected dict response but got {type(data)}"


# ============================================================
# 스텁 — P2: 과목 내 수업(강의) 목록 API
# ============================================================
# 공통 사유: class_api.py / dashboard_api.py 어디에도 과목 하위 수업(강의)
# 목록을 조회하는 메서드가 존재하지 않는다. 엔드포인트가 백엔드에 구현/노출
# 되어 있는지, API 클라이언트에 메서드가 추가될 예정인지 확인이 선행되어야
# 아래 TC들의 실제 코드 작성이 가능하다.
@pytest.mark.api
@pytest.mark.learner
class TestP2LectureListStub:
    @pytest.mark.skip(reason="검증 불가 - class_api.py에 lecture list 조회 메서드 없음")
    def test_tc_api_p2_01_lecture_list_returned_as_array(self):
        """TC-API-P2-01: 응답이 배열이며 각 항목이 강의(lecture) 스키마를 준수한다."""

    @pytest.mark.skip(reason="검증 불가 - class_api.py에 lecture list 조회 메서드 없음")
    def test_tc_api_p2_02_pagination_offset_count(self):
        """TC-API-P2-02: offset/count(최대 40) 페이지네이션이 정상 동작하고, count 초과 요청 시 실제 개수만 반환한다."""

    @pytest.mark.skip(reason="검증 불가 - class_api.py에 lecture list 조회 메서드 없음")
    def test_tc_api_p2_03_filter_by_title(self):
        """TC-API-P2-03: filter_conditions.title로 필터링 시 제목에 검색어를 포함한 강의만 반환된다."""

    @pytest.mark.skip(reason="검증 불가 - class_api.py에 lecture list 조회 메서드 없음")
    def test_tc_api_p2_04_filter_by_parent_lecture_id(self):
        """TC-API-P2-04: filter_conditions.parent_lecture_id로 필터링 시 해당 상위 강의의 하위 강의만 반환된다(최상위 강의는 parent_lecture_id null)."""

    @pytest.mark.skip(reason="검증 불가 - class_api.py에 lecture list 조회 메서드 없음")
    def test_tc_api_p2_05_recommended_lecture_page_toggle(self):
        """TC-API-P2-05: filter_contain_recommand_lecture_page 옵션에 따라 추천 강의 페이지 포함/제외가 정상 반영된다."""

    @pytest.mark.skip(reason="검증 불가 - class_api.py에 lecture list 조회 메서드 없음")
    def test_tc_api_p2_06_no_duplicate_lecture_between_pages(self):
        """TC-API-P2-06: 페이지 간(skip 이동) 강의 lecture_id 중복이 없다."""


# ============================================================
# 스텁 — P3: 과목 소개 데이터 API
# ============================================================
# 공통 사유: class_api.py / dashboard_api.py 어디에도 과목 소개 콘텐츠를
# 조회하는 메서드가 존재하지 않는다. get_course 응답(COURSE_DETAIL_SCHEMA)에
# 소개 콘텐츠 필드가 포함되는지 여부도 스키마 정의상 확인되지 않는다.
@pytest.mark.api
@pytest.mark.learner
class TestP3CourseIntroStub:
    @pytest.mark.skip(reason="검증 불가 - 과목 소개 조회 메서드/스키마 확인 안 됨")
    def test_tc_api_p3_01_description_fields_present(self):
        """TC-API-P3-01: 응답에 description, short_description 필드가 정상 존재한다."""

    @pytest.mark.skip(reason="검증 불가 - 과목 소개 조회 메서드/스키마 확인 안 됨")
    def test_tc_api_p3_02_target_audience_schema(self):
        """TC-API-P3-02: target_audience가 등록된 경우 title/description/image 하위 필드를 포함한 배열(최대 3개) 스키마를 준수한다."""

    @pytest.mark.skip(reason="검증 불가 - 과목 소개 조회 메서드/스키마 확인 안 됨")
    def test_tc_api_p3_03_objective_schema(self):
        """TC-API-P3-03: objective가 등록된 경우 문자열 배열(각 항목 최대 256자, 최대 3개) 스키마를 준수한다."""

    @pytest.mark.skip(reason="검증 불가 - 과목 소개 조회 메서드/스키마 확인 안 됨")
    def test_tc_api_p3_04_faq_parsable(self):
        """TC-API-P3-04: faq가 등록된 경우 정상 파싱 가능한 형태로 반환된다."""

    @pytest.mark.skip(reason="검증 불가 - 과목 소개 조회 메서드/스키마 확인 안 됨")
    def test_tc_api_p3_05_promote_video_url_valid(self):
        """TC-API-P3-05: promote_video_url이 등록된 경우 유효한 URL 형식(https 스킴)으로 반환된다."""

    @pytest.mark.skip(reason="검증 불가 - 과목 소개 조회 메서드/스키마 확인 안 됨")
    def test_tc_api_p3_06_empty_intro_returns_null_not_error(self):
        """TC-API-P3-06: 소개 콘텐츠 미등록 과목은 관련 필드가 null/빈 값으로 반환된다(에러 아님)."""


# ============================================================
# 스텁 — P4: 과목 단위 학습현황 오버뷰 API
# ============================================================
# 공통 사유: dashboard_api.py에는 get_student / get_student_progress
# (계정 단위) 와 get_classroom_summary(반 단위) 만 있고, '과목 단위 학습현황
# 오버뷰'를 명시적으로 반환하는 메서드는 없다. get_classroom_summary 응답에
# 이 데이터가 포함될 가능성이 있으나 스키마가 확인되지 않아 단정할 수 없다.
@pytest.mark.api
@pytest.mark.learner
class TestP4CourseLearningStatusOverviewStub:
    @pytest.mark.skip(reason="검증 불가 - 과목 단위 학습현황 오버뷰 조회 메서드/스키마 확인 안 됨")
    def test_tc_api_p4_01_overview_returns_200_and_schema(self):
        """TC-API-P4-01: 200 응답 및 학습현황 오버뷰 스키마를 준수한다."""

    @pytest.mark.skip(reason="검증 불가 - 과목 단위 학습현황 오버뷰 조회 메서드/스키마 확인 안 됨")
    def test_tc_api_p4_02_progress_rate_in_range(self):
        """TC-API-P4-02: 학습 진행률이 0~100 범위 내 값으로 반환된다."""

    @pytest.mark.skip(reason="검증 불가 - 과목 단위 학습현황 오버뷰 조회 메서드/스키마 확인 안 됨")
    def test_tc_api_p4_03_average_practice_score_nullable(self):
        """TC-API-P4-03: 평균 실습 자료 점수가 null 또는 숫자로 반환된다(데이터 없을 시 null)."""

    @pytest.mark.skip(reason="검증 불가 - 과목 단위 학습현황 오버뷰 조회 메서드/스키마 확인 안 됨")
    def test_tc_api_p4_04_average_test_score_nullable(self):
        """TC-API-P4-04: 평균 테스트 점수가 null 또는 숫자로 반환된다."""

    @pytest.mark.skip(reason="검증 불가 - 과목 단위 학습현황 오버뷰 조회 메서드/스키마 확인 안 됨")
    def test_tc_api_p4_05_account_identity_included(self):
        """TC-API-P4-05: 응답에 학습자(계정) 식별 정보가 정상 포함된다."""


# ============================================================
# 스텁 — P5: 수업별 학습현황 목록 API
# ============================================================
# 공통 사유: '과목 하위 수업(lecture)별 학습현황 목록'을 반환하는 메서드가
# class_api.py / dashboard_api.py 어디에도 없다.
@pytest.mark.api
@pytest.mark.learner
class TestP5LectureWiseStatusTableStub:
    @pytest.mark.skip(reason="검증 불가 - 수업별 학습현황 목록 조회 메서드 없음")
    def test_tc_api_p5_01_returned_as_array_with_valid_schema(self):
        """TC-API-P5-01: 응답이 배열이며 각 항목이 수업(lecture) 단위 통계 스키마를 준수한다."""

    @pytest.mark.skip(reason="검증 불가 - 수업별 학습현황 목록 조회 메서드 없음")
    def test_tc_api_p5_02_pagination_offset_count(self):
        """TC-API-P5-02: offset/count(최대 500) 페이지네이션이 정상 동작한다."""

    @pytest.mark.skip(reason="검증 불가 - 수업별 학습현황 목록 조회 메서드 없음")
    def test_tc_api_p5_03_average_progress_in_range(self):
        """TC-API-P5-03: 각 항목의 평균 학습 진행률이 0~100 범위 내다."""

    @pytest.mark.skip(reason="검증 불가 - 수업별 학습현황 목록 조회 메서드 없음")
    def test_tc_api_p5_04_average_scores_nullable(self):
        """TC-API-P5-04: 각 항목의 평균 실습자료점수/테스트점수가 null 또는 숫자로 반환된다."""

    @pytest.mark.skip(reason="검증 불가 - 수업별 학습현황 목록 조회 메서드 없음")
    def test_tc_api_p5_05_lecture_count_matches_lecture_list(self):
        """TC-API-P5-05: 목록에 표시된 수업 개수가 P2(수업 목록 API)에서 조회한 수업 개수와 일치한다(데이터 정합성). P2 자체가 코드화 불가라 이 TC도 함께 보류된다."""


# ============================================================
# 스텁 — P6: 개별 수업 학습현황 / 자료별 점수 API
# ============================================================
# 공통 사유: 개별 수업(lecture) 단위 학습현황이나 수업자료별 점수를 반환하는
# 메서드가 class_api.py / dashboard_api.py 어디에도 없다.
@pytest.mark.api
@pytest.mark.learner
class TestP6SingleLectureStatusStub:
    @pytest.mark.skip(reason="검증 불가 - 개별 수업 학습현황 조회 메서드 없음")
    def test_tc_api_p6_01_returns_200_and_schema(self):
        """TC-API-P6-01: 200 응답 및 스키마를 준수한다(lecture_id + course_section_id 기준)."""

    @pytest.mark.skip(reason="검증 불가 - 개별 수업 학습현황 조회 메서드 없음")
    def test_tc_api_p6_02_completion_count_le_total(self):
        """TC-API-P6-02: 응답에 학습 완료 개수/전체 개수(예: 0/22)가 정상 포함되고 완료 ≤ 전체다."""

    @pytest.mark.skip(reason="검증 불가 - 개별 수업 학습현황 조회 메서드 없음")
    def test_tc_api_p6_03_material_score_pagination(self):
        """TC-API-P6-03: 수업자료별 점수 목록의 offset/count(최대 20) 페이지네이션이 정상 동작한다."""

    @pytest.mark.skip(reason="검증 불가 - 개별 수업 학습현황 조회 메서드 없음")
    def test_tc_api_p6_04_sort_by_material_type_key(self):
        """TC-API-P6-04: sort_by 옵션(exercise_score, quiz_score, assignment_score, is_completed 등 material_type별) 지정 시 해당 기준으로 정렬되어 반환된다."""

    @pytest.mark.skip(reason="검증 불가 - 개별 수업 학습현황 조회 메서드 없음")
    def test_tc_api_p6_05_sort_by_key_restricted_per_material_type(self):
        """TC-API-P6-05: material_type별로 유효한 key만 sort_by에 허용된다(예: quiz는 quiz_score만 가능). 해피케이스라기보다 밸리데이션 케이스에 가까워 별도 분리 고려 필요."""

    @pytest.mark.skip(reason="검증 불가 - 개별 수업 학습현황 조회 메서드 없음")
    def test_tc_api_p6_06_material_scores_nullable(self):
        """TC-API-P6-06: 자료별 점수(exercise_score/quiz_score/assignment_score/external_score/runbox_score)가 null 또는 숫자로 반환된다."""