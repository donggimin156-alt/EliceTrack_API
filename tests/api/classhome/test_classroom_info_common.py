# tests/api/classhome/classroom/test_classroom_info_common.py
"""클래스 홈 — 소속 클래스 목록 조회 공통 테스트 (CH-001~010).

대상 API:
  GET /classroom   소속 클래스 목록 조회 (학습자·교육자 공통)
"""
import pytest

from api.endpoints.classroom_api import ClassroomAPI
from api.schemas.classhome_schema import ClasshomeSchemas
from fixtures.classhome_fixture import CLASSROOM_CLIENTS
from utils.assertions.api_assertions import assert_valid_schema

# ── 경계값 상수 ───────────────────────────────────────────────
VALID_SKIP = 0
VALID_COUNT = 10
LARGE_COUNT = 99999         # CH-006: 상한선 없음 확인용 큰 count 값
OVERFLOW_SKIP_BUFFER = 100  # CH-007: 전체 개수에 더해 skip overflow 유발


@pytest.mark.api
@pytest.mark.classhome
class TestClassroomList:
    """목록 API 공통 케이스."""

    @pytest.mark.parametrize("client_fixture", CLASSROOM_CLIENTS)
    def test_ch_001_list_response(self, request, client_fixture):
        """[CH-001] skip=0, count=10 정상 요청 응답 검증.

        기대값:
          - HTTP 200
          - 응답이 JSON 배열이며 각 항목에 id(str)·name(str) 존재
          - 모든 항목의 name != ""
        """
        api: ClassroomAPI = request.getfixturevalue(client_fixture)
        resp = api.get_classroom_list(skip=VALID_SKIP, count=VALID_COUNT)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert_valid_schema(data, ClasshomeSchemas.CLASSROOM_LIST_SCHEMA)
        # Business: 이름 비어있지 않음
        for item in data:
            assert item["name"] != "", f"빈 name 항목 발견: {item}"
        # Business: 중복 ID 없음
        ids = [item["id"] for item in data]
        assert len(ids) == len(set(ids)), f"중복 classroom ID 발견: {ids}"

    @pytest.mark.parametrize("client_fixture", CLASSROOM_CLIENTS)
    def test_ch_002_missing_all_params(self, request, client_fixture):
        """[CH-002] skip·count 모두 생략 시 422 반환 및 두 필드 모두 missing 검증.

        기대값:
          - HTTP 422
          - detail 에 skip, count 모두 missing 타입으로 포함
        """
        api: ClassroomAPI = request.getfixturevalue(client_fixture)
        resp = api.get_classroom_list()
        assert resp.status_code == 422, resp.text
        detail = resp.json().get("detail", [])
        # detail 목록 중에서, type이 missing인 것들만 골라서, 그 필드 이름(skip, count 등)만 모아놓은 집합
        missing_fields = {item["loc"][-1] for item in detail if item.get("type") == "missing" and item.get("loc")}
        assert "skip" in missing_fields, f"skip missing 항목이 없음: {detail}"
        assert "count" in missing_fields, f"count missing 항목이 없음: {detail}"

    @pytest.mark.parametrize("client_fixture", CLASSROOM_CLIENTS)
    def test_ch_003_missing_count(self, request, client_fixture):
        """[CH-003] count만 생략 시 422 반환 및 count missing 검증.

        기대값:
          - HTTP 422
          - detail 에 count missing 타입으로 포함
        """
        api: ClassroomAPI = request.getfixturevalue(client_fixture)
        resp = api.get_classroom_list(skip=VALID_SKIP)
        assert resp.status_code == 422, resp.text
        detail = resp.json().get("detail", [])
        missing_fields = {item["loc"][-1] for item in detail if item.get("type") == "missing" and item.get("loc")}
        assert "count" in missing_fields, f"count missing 항목이 없음: {detail}"

    # client_fixture — 2가지(prod, dev) * 3가지 = 6번실행
    @pytest.mark.parametrize("client_fixture", CLASSROOM_CLIENTS)
    @pytest.mark.parametrize("bad_count,expected_error", [
        # (bad_count, expected_error)
        pytest.param(0,     "greater_than_equal", id="count=0"),
        pytest.param(-1,    "greater_than_equal", id="count=-1"),
        pytest.param("abc", "int_parsing",        id="count=string"),
    ])
    def test_ch_004_005_008_invalid_count(self, request, client_fixture, bad_count, expected_error):
        """[CH-004/005/008] 유효하지 않은 count 값 전달 시 422 반환 및 에러 타입 검증.

        기대값:
          - HTTP 422
          - count=0 또는 음수: detail 에 greater_than_equal 타입 포함
          - count=문자열:      detail 에 int_parsing 타입 포함
        """
        api: ClassroomAPI = request.getfixturevalue(client_fixture)
        resp = api.get_classroom_list(skip=VALID_SKIP, count=bad_count)
        assert resp.status_code == 422, resp.text
        error_types = {item.get("type") for item in resp.json().get("detail", [])}
        assert expected_error in error_types, f"{expected_error} 에러 없음: {resp.json()}"

    @pytest.mark.parametrize("client_fixture", CLASSROOM_CLIENTS)
    def test_ch_006_large_count_returns_200(self, request, client_fixture):
        """[CH-006] count=99999처럼 매우 큰 값도 422 없이 200을 반환해야 한다.

        기대값:
          - HTTP 200 (상한선 오류 없음)
        """
        api: ClassroomAPI = request.getfixturevalue(client_fixture)
        resp = api.get_classroom_list(skip=VALID_SKIP, count=LARGE_COUNT)
        assert resp.status_code == 200, resp.text

    @pytest.mark.parametrize("client_fixture", CLASSROOM_CLIENTS)
    def test_ch_007_skip_exceeds_total_returns_empty(self, request, client_fixture):
        """[CH-007] 실제 소속 개수보다 큰 skip 값 사용 시 빈 배열을 반환해야 한다.

        기대값:
          - HTTP 200
          - 응답 배열 == []
        """
        api: ClassroomAPI = request.getfixturevalue(client_fixture)
        # 소속확인
        count_resp = api.get_classroom_count()
        assert count_resp.status_code == 200, count_resp.text
        total = count_resp.json()
        assert isinstance(total, int), count_resp.text
        # 실제 개수 + 100(overflow)
        overflow_skip = total + OVERFLOW_SKIP_BUFFER

        resp = api.get_classroom_list(skip=overflow_skip, count=VALID_COUNT)
        assert resp.status_code == 200, resp.text
        assert resp.json() == [], f"빈 배열이어야 하지만 데이터가 반환됨: {resp.json()}"

    @pytest.mark.parametrize("client_fixture", CLASSROOM_CLIENTS)
    def test_ch_009_no_auth_returns_403(self, request, client_fixture):
        """[CH-009] Authorization 헤더 없이(로그인x) 목록 API 호출 시 403을 반환해야 한다.

        기대값:
          - HTTP 403
          - code: no_access_token
        """
        api: ClassroomAPI = request.getfixturevalue(client_fixture)
        resp = api.get_classroom_list(skip=VALID_SKIP, count=VALID_COUNT, auth=False)
        assert resp.status_code == 403, resp.text
        assert resp.json().get("code") == "no_access_token", resp.text

    @pytest.mark.parametrize("client_fixture", CLASSROOM_CLIENTS)
    def test_ch_010_list_count_consistency(self, request, client_fixture):
        """[CH-010] 목록 API 배열 길이가 count API 값과 일치하는 숫자를 확인한다.

        기대값:
          - 두 API 모두 HTTP 200
          - len(목록 응답) == count API 응답값
        """
        api: ClassroomAPI = request.getfixturevalue(client_fixture)
        count_resp = api.get_classroom_count()
        assert count_resp.status_code == 200, count_resp.text
        total: int = count_resp.json()
        assert isinstance(total, int), count_resp.text

        # count는 >=1 범위여야하니까
        list_resp = api.get_classroom_list(skip=0, count=max(total, 1))
        assert list_resp.status_code == 200, list_resp.text
        items = list_resp.json()
        assert len(items) == total, f"목록 길이({len(items)}) ≠ count API 값({total})"
        # Business: 중복 classroom ID 없음
        ids = [item["id"] for item in items]
        assert len(ids) == len(set(ids)), f"중복 classroom ID 발견: {ids}"
