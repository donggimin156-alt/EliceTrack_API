'''
"""
P5: 수업별 학습현황 드릴다운 (수업 클릭 → 학생 목록 모달 → 개별 학생 학습현황)

스크린샷(수업별 학습 현황 목록 / 학생별 학습현황 모달 / 개별 학생 학습현황
모달)에서 확인된 흐름으로, 기존 PDF에는 없던 화면이라 대응 API가 아직
식별/실증되지 않았다. 함수 정의와 "검증해야 할 내용" + "확인되지 않은 부분"만
docstring으로 남겨둔다.
"""

import pytest


@pytest.mark.api
@pytest.mark.educator
class TestLectureLevelDashboardDrilldown:
    @pytest.mark.skip(reason="모달 진입 시 호출되는 API 미식별")
    def test_clicking_lecture_row_opens_student_list_for_that_lecture(self):
        """
        ["수업별 학습현황" 목록에서 임의 수업의 ">" 클릭]
        해당 수업 기준 학생별 학습현황(상단 "학습 완료 N/M명" 요약 + 학생별
        평균 실습자료 점수 목록)이 정상적으로 내려오는지 검증.

        ⚠️ 확인되지 않은 부분:
        - 실제 호출 엔드포인트 (dashboard/lecture/user/list 계열로 추정되나
          미확인)
        - "학습 완료 N/M명" 집계가 응답 필드로 내려오는지, 프론트에서
          계산하는지
        - 이 목록에 "평균 테스트 점수" 컬럼이 없는 이유(수업 단위에서는
          실습자료 점수만 노출되는 사양인지) 확인 필요
        """
        pass

    @pytest.mark.skip(reason="검색 파라미터가 상위 화면과 동일한지 미식별")
    def test_modal_student_search_by_name_or_email(self):
        """
        [수업별 학습현황 모달 내 "전체 학생" 검색]
        모달 내에서도 상위 학습현황 화면과 동일하게 이름/이메일 검색이
        되는지 검증.

        ⚠️ 확인되지 않은 부분: 상위 화면 검색(test_dashboard_course_status.py)과
        동일 파라미터를 쓰는지, lecture_id 필터가 추가로 필요한지
        """
        pass

    @pytest.mark.skip(reason="리포트 다운로드 대상 범위(전체 vs 수업 단위) 미확인")
    def test_modal_class_report_download_scoped_to_lecture(self):
        """
        [수업별 학습현황 모달 내 "클래스 리포트" 다운로드]
        전체 리포트(test_excel_report.py, E-11)와 달리, 해당 수업 기준으로
        범위가 좁혀진 리포트가 다운로드되는지 검증.

        ⚠️ 확인되지 않은 부분: 기존 get_course_report_token API에 lecture_id를
        추가 파라미터로 넘기는 구조인지, 완전히 별도 엔드포인트/토큰 발급
        플로우인지
        """
        pass


@pytest.mark.api
@pytest.mark.educator
class TestIndividualStudentDashboardFromModal:
    @pytest.mark.skip(reason="개별 학생 상세 진입 API 미식별")
    def test_clicking_student_in_modal_opens_individual_progress(self):
        """
        [수업별 학습현황 모달 → 학생 클릭]
        해당 학생의 개별 학습현황(수업자료별 점수 테이블: 수업 자료 / 점수
        컬럼)이 정상 노출되는지 검증.

        ⚠️ 확인되지 않은 부분:
        - test_student_dashboard.py의 GET /student/{account_id}와 동일 API인지,
          완전히 다른 lecture 단위 API인지
        - 수업자료별 점수 테이블의 실제 응답 필드 구조(material_type,
          material_id, score 등으로 추정되나 미확인)
        """
        pass

    @pytest.mark.skip(reason="빈 데이터 응답 형태 미확인")
    def test_individual_student_with_no_score_data_shows_empty_state(self):
        """
        [개별 학생 - 점수 데이터 없음]
        아직 아무 자료도 제출/응시하지 않은 학생의 경우, 에러가 아니라
        "데이터가 없습니다"에 대응하는 정상 응답(빈 배열 등)이 내려오는지
        검증. (스크린샷에서 "학습 완료 0/0개" + "데이터가 없습니다" 실제
        확인됨)

        ⚠️ 확인되지 않은 부분: 응답이 빈 배열인지, 각 필드가 null인 항목이
        채워져서 내려오는지
        """
        pass

    @pytest.mark.skip(reason="드롭다운 전환 시 호출 API 미확인")
    def test_switching_student_via_dropdown_updates_individual_progress(self):
        """
        [개별 학생 학습현황 모달 - 상단 드롭다운으로 다른 학생 전환]
        모달 상단의 학생 선택 드롭다운에서 다른 학생을 선택하면, 화면 전체를
        다시 열지 않고도 해당 학생 기준 데이터로 갱신되는지 검증.

        ⚠️ 확인되지 않은 부분: 드롭다운 전환이 새로운 API 호출을 유발하는지,
        이미 받아온 학생 목록 데이터 내에서 클라이언트 단 필터링만 하는지
        """
        pass

    @pytest.mark.skip(reason="모달 닫기 후 상태 복원 여부 미확인")
    def test_closing_individual_student_modal_returns_to_lecture_list(self):
        """
        [개별 학생 학습현황 모달 - "X" 닫기]
        "X" 클릭 시 모달이 닫히고 이전 화면(수업별 학생 목록)으로 정상
        복귀하는지, 그리고 이전 화면의 검색/페이지 상태가 유지되는지 검증.

        ⚠️ 확인되지 않은 부분: 이 동작이 API 재호출 없이 클라이언트 상태
        복원만으로 이뤄지는지 (API 자동화 관점에서는 검증 대상이 아닐 수 있음)
        """
        pass

'''