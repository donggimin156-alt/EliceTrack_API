"""
학습자 권한 UI — 신규 API 해피케이스 (2차 실증 반영)

⚠️ 디버그 테스트 결과로 확인된 중요 사실 3가지:

1) get_dashboard_course_stats_list 응답은 배열이 아니라
   {_result, users, user_count} 래퍼다. 각 항목은 lecture 단위가 아니라
   'user'(학습자) 단위 통계이며 필드는
   avg_exercise_score / eps / time_spent / completed_exercise_page_count 다.
   → 원래 이름(수업별 학습현황)과 달리 실제로는 학습자별 통계이므로,
     P2(lecture 목록)와의 개수 비교(P5-05)는 성립하지 않아 폐기한다.

2) get_dashboard_lecture / get_dashboard_lecture_user_list 는 학습자 계정으로
   호출 시 항상 409 insufficient_permission ("you should be TA or above")을
   반환한다 (실증됨). 즉 이 두 API는 학습자 권한에서는 거부되는 것이
   정상 동작이며, 이 파일(학습자 권한 UI 테스트) 스코프에서는 그 권한 경계만
   검증한다. 실제 응답 데이터 필드(완료 개수, 정렬, 자료별 점수)는 TA 이상
   계정을 사용하는 별도 테스트 파일에서 검증해야 한다.

3) get_dashboard_course 응답은 개별 학습자가 아니라 반(course_section) 전체
   집계 통계다. progress(%)나 개별 계정 식별 필드는 존재하지 않는다.
   필드: user_count, completed_student_count, running_count,
   normal_lecture_page_count, test_lecture_point, material_exercise_count,
   avg_normal_lecture_completed_page_count, avg_completed_exercise_page_count,
   avg_completed_exercise_n_quiz_page_count, avg_exercise_running_count,
   avg_eps, avg_time_spent.

기존 커버리지 (중복 작성하지 않음):
    - 과목 목록 조회/페이지네이션/진행률                 → test_class.py
    - 과목 추가→조회→삭제 풀 라이프사이클                → test_course_add_delete_happy_path.py
    - 학습현황 상세 (get_student_progress, course/cohort 지정) → test_student_dashboard.py
    - 학습현황 엑셀 리포트 토큰 발급/다운로드             → test_excel_report.py
    - 과목 단건 조회 스키마/목록↔상세 title 일치         → test_common_course_detail.py (교육자/학습자 파라미터라이즈)
"""

import os

import pytest

from core.config import settings

PROD_ENV = settings.elice_environments["prod"]
LEARNER_ACCOUNT_ID = os.getenv("PROD_LEARNER_ACCOUNT_ID") or PROD_ENV.get("LEARNER_ACCOUNT_ID")
CLASSROOM_ID = PROD_ENV["CLASSROOM_ID"]

pytestmark = pytest.mark.skipif(
    not LEARNER_ACCOUNT_ID,
    reason="PROD_LEARNER_ACCOUNT_ID not set; skipping learner-specific tests",
)


@pytest.fixture(scope="module")
def progress_course_section_id(class_api, assert_response):
    """PROGRESS_COURSE_ID 하위의 course_section id 하나를 동적으로 조회한다.

    ⚠️ 실증됨: 응답은 {_result, course_sections, course_section_count} 래퍼이며
    각 항목의 식별자 필드명은 'id'다 (course_section_id 아님).
    """
    resp = class_api.get_course_section_list(
        course_id=PROD_ENV["PROGRESS_COURSE_ID"], offset=0, count=20
    )
    data = assert_response(resp, 200)
    sections = data["course_sections"]
    if not sections:
        pytest.skip("PROGRESS_COURSE_ID에 course_section이 존재하지 않아 스킵합니다.")
    return sections[0]["id"]


# ============================================================
# 실제 코드 작성 가능 — ClassApi.get_course (진행률 정합성, P1-03)
# ============================================================
@pytest.mark.api
@pytest.mark.learner
class TestCourseDetailConsistency:
    def test_course_detail_omits_progress_data(self, class_api, course_data, assert_response):
        """TC-API-P1-03(수정): 단건 조회(get_course) 응답에는 목록과 달리
        classroom_course_progress_data 필드가 포함되지 않는다 (실증됨).
        """
        course_id = course_data[0]["course_id"]
        resp = class_api.get_course(course_id)
        detail = assert_response(resp, 200)
        assert "classroom_course_progress_data" not in detail, (
            "단건 조회 응답에 classroom_course_progress_data가 포함되었습니다. "
            "(이전에는 없는 것으로 실증되었으니, API 스펙이 변경되었을 수 있습니다)"
        )


# ============================================================
# 실제 코드 작성 가능 — DashboardAPI.get_classroom_summary
# ============================================================
@pytest.mark.api
@pytest.mark.learner
class TestClassroomSummary:
    def test_get_classroom_summary_returns_200(self, student_dashboard_api, assert_response):
        """TC-API-CS-01"""
        resp = student_dashboard_api.get_classroom_summary(CLASSROOM_ID)
        data = assert_response(resp, 200)
        assert isinstance(data, dict), f"Expected dict response but got {type(data)}"

    def test_get_classroom_summary_response_not_empty(self, student_dashboard_api, assert_response):
        """TC-API-CS-02"""
        resp = student_dashboard_api.get_classroom_summary(CLASSROOM_ID)
        data = assert_response(resp, 200)
        assert data, "반 전체 학습현황 응답이 비어있습니다."


# ============================================================
# 실제 코드 작성 가능 — DashboardAPI.get_student
# ============================================================
@pytest.mark.api
@pytest.mark.learner
class TestStudentOverview:
    def test_get_student_overview_returns_200(self, student_dashboard_api, assert_response):
        """TC-API-SO-01"""
        resp = student_dashboard_api.get_student(
            account_id=LEARNER_ACCOUNT_ID, classroom_id=CLASSROOM_ID
        )
        data = assert_response(resp, 200)
        assert isinstance(data, dict), f"Expected dict response but got {type(data)}"

    def test_get_student_overview_without_classroom_id_returns_422(
        self, student_dashboard_api, assert_response
    ):
        """TC-API-SO-02(수정): classroom_id는 필수 파라미터임이 실증됨."""
        resp = student_dashboard_api.get_student(account_id=LEARNER_ACCOUNT_ID)
        data = assert_response(resp, 422)
        assert data["detail"][0]["loc"] == ["query", "classroom_id"]
        assert data["detail"][0]["type"] == "missing"


# ============================================================
# P2: 과목 내 수업(강의) 목록 API
# ============================================================
@pytest.mark.api
@pytest.mark.learner
class TestP2LectureList:
    def test_tc_api_p2_01_lecture_list_returned_as_array(self, class_api, assert_response):
        """TC-API-P2-01"""
        resp = class_api.get_lecture_list(
            course_id=PROD_ENV["PROGRESS_COURSE_ID"], offset=0, count=20
        )
        data = assert_response(resp, 200)
        assert isinstance(data["lectures"], list), f"Expected list but got {type(data.get('lectures'))}"

    def test_tc_api_p2_02_pagination_offset_count(self, class_api, assert_response):
        """TC-API-P2-02"""
        resp = class_api.get_lecture_list(
            course_id=PROD_ENV["PROGRESS_COURSE_ID"], offset=0, count=40
        )
        data = assert_response(resp, 200)
        assert len(data["lectures"]) <= 40, f"Expected at most 40 items but got {len(data['lectures'])}"

    def test_tc_api_p2_03_filter_by_title(self, class_api, assert_response):
        """TC-API-P2-03"""
        all_resp = class_api.get_lecture_list(
            course_id=PROD_ENV["PROGRESS_COURSE_ID"], offset=0, count=1
        )
        all_data = assert_response(all_resp, 200)
        assert all_data["lectures"], "필터링 대상 강의가 없어 테스트를 진행할 수 없습니다."
        keyword = all_data["lectures"][0]["title"][:2]

        resp = class_api.get_lecture_list(
            course_id=PROD_ENV["PROGRESS_COURSE_ID"],
            offset=0,
            count=40,
            filter_conditions={"title": keyword},
        )
        data = assert_response(resp, 200)
        for item in data["lectures"]:
            assert keyword in item["title"], f"필터 키워드 {keyword!r}가 title {item['title']!r}에 없습니다."

    def test_tc_api_p2_06_no_duplicate_lecture_between_pages(self, class_api, assert_response):
        """TC-API-P2-06"""
        page1_resp = class_api.get_lecture_list(
            course_id=PROD_ENV["PROGRESS_COURSE_ID"], offset=0, count=20
        )
        page1 = assert_response(page1_resp, 200)
        page2_resp = class_api.get_lecture_list(
            course_id=PROD_ENV["PROGRESS_COURSE_ID"], offset=20, count=20
        )
        page2 = assert_response(page2_resp, 200)

        ids1 = {item["id"] for item in page1["lectures"]}
        ids2 = {item["id"] for item in page2["lectures"]}
        assert ids1.isdisjoint(ids2), f"페이지 간 중복 id: {ids1 & ids2}"


# ============================================================
# P3: 과목 소개 콘텐츠 API (get_course_info)
# ============================================================
@pytest.mark.api
@pytest.mark.learner
class TestP3CourseIntro:
    """⚠️ 현재 PROGRESS_COURSE_ID는 소개 콘텐츠가 전부 미등록 상태(빈 값)라,
    '값이 있을 때의 세부 스키마(제목/이미지 등 하위 필드)'까지는 실증하지
    못했다. 다만 비어있을 때 타입과 에러 여부는 확실히 실증되었으므로 그
    범위에서 채운다. 실제 소개 콘텐츠가 등록된 과목이 생기면 P3-02 하위
    스키마(title/description/image)를 보강해야 한다.
    """

    def test_tc_api_p3_01_description_fields_present(self, class_api, assert_response):
        """TC-API-P3-01: 응답에 description, short_description 필드가 문자열로 존재한다."""
        resp = class_api.get_course_info(course_id=PROD_ENV["PROGRESS_COURSE_ID"])
        data = assert_response(resp, 200)
        course = data["course"]
        assert isinstance(course["description"], str)
        assert isinstance(course["short_description"], str)

    def test_tc_api_p3_02_target_audience_is_array_max_3(self, class_api, assert_response):
        """TC-API-P3-02: target_audience는 배열이며 최대 3개 항목이다.
        ⚠️ 항목이 있을 때 title/description/image 하위 스키마는 미실증 - 데이터 확보 후 보강 필요.
        """
        resp = class_api.get_course_info(course_id=PROD_ENV["PROGRESS_COURSE_ID"])
        data = assert_response(resp, 200)
        target_audience = data["course"]["target_audience"]
        assert isinstance(target_audience, list)
        assert len(target_audience) <= 3
        for item in target_audience:
            assert "title" in item and "description" in item

    def test_tc_api_p3_03_objective_is_array_max_3_len_256(self, class_api, assert_response):
        """TC-API-P3-03: objective는 문자열 배열(각 항목 최대 256자, 최대 3개)이다."""
        resp = class_api.get_course_info(course_id=PROD_ENV["PROGRESS_COURSE_ID"])
        data = assert_response(resp, 200)
        objective = data["course"]["objective"]
        assert isinstance(objective, list)
        assert len(objective) <= 3
        for item in objective:
            assert isinstance(item, str)
            assert len(item) <= 256

    def test_tc_api_p3_04_faq_parsable_list(self, class_api, assert_response):
        """TC-API-P3-04: faq는 정상 파싱 가능한 배열 형태로 반환된다."""
        resp = class_api.get_course_info(course_id=PROD_ENV["PROGRESS_COURSE_ID"])
        data = assert_response(resp, 200)
        assert isinstance(data["course"]["faq"], list)

    def test_tc_api_p3_05_promote_video_url_none_or_https(self, class_api, assert_response):
        """TC-API-P3-05: promote_video_url은 None이거나 https 스킴 URL이다."""
        resp = class_api.get_course_info(course_id=PROD_ENV["PROGRESS_COURSE_ID"])
        data = assert_response(resp, 200)
        url = data["course"]["promote_video_url"]
        assert url is None or url.startswith("https://")

    def test_tc_api_p3_06_empty_intro_returns_null_not_error(self, class_api, assert_response):
        """TC-API-P3-06(실증됨): 소개 콘텐츠 미등록 과목은 관련 필드가
        null 또는 빈 배열/빈 문자열로 반환되고, 에러가 아니다."""
        resp = class_api.get_course_info(course_id=PROD_ENV["PROGRESS_COURSE_ID"])
        data = assert_response(resp, 200)
        course = data["course"]
        assert course["description"] == ""
        assert course["short_description"] == ""
        assert course["target_audience"] == []
        assert course["objective"] == []
        assert course["faq"] == []
        assert course["promote_video_url"] is None


# ============================================================
# P4: 과목(반) 단위 학습현황 집계 API (get_dashboard_course)
# ============================================================
@pytest.mark.api
@pytest.mark.learner
class TestP4CourseLearningStatusOverview:
    """⚠️ 실증됨: 이 API는 개별 학습자 진행률이 아니라 course_section 전체
    집계 통계를 반환한다. progress(%) 필드나 개별 계정 식별 필드는 없다.
    """

    def test_tc_api_p4_01_overview_returns_200(self, class_api, progress_course_section_id, assert_response):
        """TC-API-P4-01"""
        resp = class_api.get_dashboard_course(
            course_id=PROD_ENV["PROGRESS_COURSE_ID"],
            course_section_id=progress_course_section_id,
        )
        data = assert_response(resp, 200)
        assert isinstance(data["course"], dict), f"Expected dict but got {type(data.get('course'))}"

    def test_tc_api_p4_02_user_and_completed_counts_non_negative_and_consistent(
        self, class_api, progress_course_section_id, assert_response
    ):
        """TC-API-P4-02(수정): user_count/completed_student_count/running_count는
        0 이상이며, completed_student_count와 running_count는 user_count를
        초과할 수 없다."""
        resp = class_api.get_dashboard_course(
            course_id=PROD_ENV["PROGRESS_COURSE_ID"],
            course_section_id=progress_course_section_id,
        )
        data = assert_response(resp, 200)
        course = data["course"]
        assert course["user_count"] >= 0
        assert 0 <= course["completed_student_count"] <= course["user_count"]
        assert 0 <= course["running_count"] <= course["user_count"]

    def test_tc_api_p4_03_average_stat_fields_are_non_negative_numbers(
        self, class_api, progress_course_section_id, assert_response
    ):
        """TC-API-P4-03(수정): 평균 통계 필드(avg_normal_lecture_completed_page_count,
        avg_completed_exercise_page_count, avg_completed_exercise_n_quiz_page_count,
        avg_exercise_running_count, avg_eps, avg_time_spent)는 데이터가 없을 때
        null이 아니라 0으로 반환되며, 음수가 아니다."""
        resp = class_api.get_dashboard_course(
            course_id=PROD_ENV["PROGRESS_COURSE_ID"],
            course_section_id=progress_course_section_id,
        )
        data = assert_response(resp, 200)
        course = data["course"]
        avg_fields = [
            "avg_normal_lecture_completed_page_count",
            "avg_completed_exercise_page_count",
            "avg_completed_exercise_n_quiz_page_count",
            "avg_exercise_running_count",
            "avg_eps",
            "avg_time_spent",
        ]
        for field in avg_fields:
            assert isinstance(course[field], (int, float)), f"{field} 타입이 숫자가 아닙니다: {course[field]!r}"
            assert course[field] >= 0, f"{field}가 음수입니다: {course[field]}"

    def test_tc_api_p4_04_page_and_exercise_count_fields_are_non_negative_ints(
        self, class_api, progress_course_section_id, assert_response
    ):
        """TC-API-P4-04(수정): normal_lecture_page_count/test_lecture_point/
        material_exercise_count는 0 이상의 정수다."""
        resp = class_api.get_dashboard_course(
            course_id=PROD_ENV["PROGRESS_COURSE_ID"],
            course_section_id=progress_course_section_id,
        )
        data = assert_response(resp, 200)
        course = data["course"]
        for field in ("normal_lecture_page_count", "test_lecture_point", "material_exercise_count"):
            assert isinstance(course[field], int)
            assert course[field] >= 0

    def test_tc_api_p4_05_no_individual_account_identity_field(
        self, class_api, progress_course_section_id, assert_response
    ):
        """TC-API-P4-05(수정): 이 API는 반 전체 집계이므로 개별 계정 식별
        정보(account_id 등)를 포함하지 않는다 (실증됨 — 원래 TC 가정과 다름)."""
        resp = class_api.get_dashboard_course(
            course_id=PROD_ENV["PROGRESS_COURSE_ID"],
            course_section_id=progress_course_section_id,
        )
        data = assert_response(resp, 200)
        course = data["course"]
        assert "account_id" not in course
        assert "user" not in course


# ============================================================
# P5: 학습자별 학습현황 목록 API (get_dashboard_course_stats_list)
# ============================================================
@pytest.mark.api
@pytest.mark.learner
class TestP5UserWiseStatusTable:
    """⚠️ 실증됨: 응답은 배열이 아니라 {_result, users, user_count} 래퍼이고,
    각 항목은 lecture 단위가 아니라 학습자(user) 단위 통계다. 원래 문서의
    'lecture 개수와 P2 비교'(P5-05)는 데이터 모델이 달라 성립하지 않으므로
    폐기했다.
    """

    def test_tc_api_p5_01_users_returned_as_array(
        self, class_api, progress_course_section_id, assert_response
    ):
        """TC-API-P5-01(수정): 'users' 필드가 배열이다."""
        resp = class_api.get_dashboard_course_stats_list(
            course_id=PROD_ENV["PROGRESS_COURSE_ID"],
            course_section_id=progress_course_section_id,
            offset=0,
            count=500,
        )
        data = assert_response(resp, 200)
        assert isinstance(data["users"], list), f"Expected list but got {type(data.get('users'))}"

    def test_tc_api_p5_02_pagination_offset_count(
        self, class_api, progress_course_section_id, assert_response
    ):
        """TC-API-P5-02(수정): offset/count(최대 500) 페이지네이션이 정상 동작한다."""
        resp = class_api.get_dashboard_course_stats_list(
            course_id=PROD_ENV["PROGRESS_COURSE_ID"],
            course_section_id=progress_course_section_id,
            offset=0,
            count=500,
        )
        data = assert_response(resp, 200)
        assert len(data["users"]) <= 500, f"Expected at most 500 items but got {len(data['users'])}"

    def test_tc_api_p5_03_avg_exercise_score_and_eps_non_negative(
        self, class_api, progress_course_section_id, assert_response
    ):
        """TC-API-P5-03(수정): 각 학습자 항목의 avg_exercise_score, eps,
        time_spent, completed_exercise_page_count가 0 이상이다.
        ⚠️ avg_exercise_score의 상한(예: 100)은 아직 0이 아닌 실제 값으로
        실증되지 않아 상한 검증은 보류한다."""
        resp = class_api.get_dashboard_course_stats_list(
            course_id=PROD_ENV["PROGRESS_COURSE_ID"],
            course_section_id=progress_course_section_id,
            offset=0,
            count=500,
        )
        data = assert_response(resp, 200)
        for item in data["users"]:
            assert item["avg_exercise_score"] >= 0
            assert item["eps"] >= 0
            assert item["time_spent"] >= 0
            assert item["completed_exercise_page_count"] >= 0

    def test_tc_api_p5_04_user_count_matches_users_length_within_page(
        self, class_api, progress_course_section_id, assert_response
    ):
        """TC-API-P5-04(수정): 전체 조회(count=500) 시 user_count가 users
        배열 길이와 일치한다(정합성)."""
        resp = class_api.get_dashboard_course_stats_list(
            course_id=PROD_ENV["PROGRESS_COURSE_ID"],
            course_section_id=progress_course_section_id,
            offset=0,
            count=500,
        )
        data = assert_response(resp, 200)
        assert data["user_count"] == len(data["users"])

    # P5-05 (lecture 개수와 P2 비교)는 데이터 모델이 학습자 단위임이 실증되어 폐기.
    # 대신 반 전체 학습자 수(user_count)와 get_dashboard_course의 user_count가
    # 같은 course_section 기준으로 일치하는지는 별도 정합성 테스트로 분리 검토 필요.


# ============================================================
# P6: 개별 수업 학습현황 / 자료별 점수 API
# ============================================================
@pytest.mark.api
@pytest.mark.learner
class TestP6SingleLectureStatus:
    """⚠️ 실증됨: get_dashboard_lecture / get_dashboard_lecture_user_list는
    학습자 계정으로 호출 시 항상 409 insufficient_permission
    ("you should be TA or above")을 반환한다. 즉 이 두 API는 TA 이상
    권한이 필요하며, 학습자 권한에서는 거부되는 것이 정상 동작이다.
    실제 응답 데이터 스키마(완료 개수, 정렬, 자료별 점수)는 TA/교육자 계정을
    사용하는 별도 테스트 파일에서 검증해야 하며, 이 파일(학습자 권한 UI)
    스코프에서는 권한 경계만 검증한다.
    """

    @pytest.fixture
    def progress_lecture_id(self, class_api, assert_response):
        resp = class_api.get_lecture_list(
            course_id=PROD_ENV["PROGRESS_COURSE_ID"], offset=0, count=1
        )
        data = assert_response(resp, 200)
        lectures = data["lectures"]
        if not lectures:
            pytest.skip("PROGRESS_COURSE_ID에 lecture가 존재하지 않아 스킵합니다.")
        return lectures[0]["id"]

    def test_tc_api_p6_01_learner_denied_with_409(
        self, class_api, progress_lecture_id, progress_course_section_id, assert_response
    ):
        """TC-API-P6-01(수정): 학습자 권한으로 조회 시 거부된다.
        ⚠️ 실증됨: elice class API는 HTTP status를 항상 200으로 주고,
        실제 성공/실패는 바디 안 _result.status_code / fail_code에 담긴다.
        따라서 HTTP status가 아니라 바디 내용으로 검증해야 한다."""
        resp = class_api.get_dashboard_lecture(
            lecture_id=progress_lecture_id,
            course_section_id=progress_course_section_id,
        )
        data = assert_response(resp, 200)
        assert data["_result"]["status"] == "fail"
        assert data["_result"]["status_code"] == 409
        assert data["fail_code"] == "insufficient_permission"

    def test_tc_api_p6_03_material_score_list_learner_denied_with_409(
        self, class_api, progress_lecture_id, progress_course_section_id, assert_response
    ):
        """TC-API-P6-03(수정): 수업자료별 점수 목록도 학습자 권한으로는
        거부된다. HTTP status는 200이고 바디의 _result.status_code가 409다."""
        resp = class_api.get_dashboard_lecture_user_list(
            lecture_id=progress_lecture_id,
            course_section_id=progress_course_section_id,
            offset=0,
            count=20,
        )
        data = assert_response(resp, 200)
        assert data["_result"]["status"] == "fail"
        assert data["_result"]["status_code"] == 409
        assert data["fail_code"] == "insufficient_permission"

    # P6-02(완료/전체 개수), P6-04(정렬), P6-05(material_type별 sort_by 제한),
    # P6-06(자료별 점수 nullable)는 TA 이상 계정이 필요해 이 파일에서는
    # 검증 불가. TA 권한 테스트 파일(예: test_ta_dashboard.py)에서 다뤄야 한다.