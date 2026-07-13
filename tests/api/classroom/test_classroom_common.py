# tests/api/classroom/test_classroom_common.py
"""클래스 홈 — classroom 엔드포인트 테스트 (CH-001~010, CH-012~018).

대상 API: GET https://api-classroom.elice.io/classroom
환경: prod 학습자 계정 (qatrack org)
명세 대조 기준: Notion "4차 클래스홈 TC (최종)"
"""
import pytest

from fixtures.classroom_fixture import ClassroomClient


@pytest.mark.api
@pytest.mark.classroom
@pytest.mark.learner
class TestClassroomCommon:
    """classroom 목록 API: 학습자 계정 기준 정상·예외 시나리오."""

    def test_ch001_normal_list(self, classroom_client: ClassroomClient) -> None:
        """CH-001: 필수 파라미터 포함 시 정상 목록 조회.

        기대값(실측 완료):
          - HTTP 200
          - 응답이 배열([]) 형태
          - 배열 내 각 항목에 id(class_id), name(title) 필드 존재
        """
        resp = classroom_client.get("classroom", params={"skip": 0, "count": 10})

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list), resp.text
        for item in data:
            assert "class_id" in item or "id" in item, f"class_id/id 필드 없음: {item}"
            assert "name" in item or "title" in item, f"name/title 필드 없음: {item}"

    def test_ch002_missing_params(self, classroom_client: ClassroomClient) -> None:
        """CH-002: skip/count 파라미터 누락 시 422.

        기대값(실측 완료):
          - HTTP 422 Unprocessable Entity
          - detail에 skip, count 두 항목이 missing으로 포함
        """
        resp = classroom_client.get("classroom")

        assert resp.status_code == 422, resp.text
