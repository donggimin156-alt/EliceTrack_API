# tests/api/classhome/classroom/test_classroom_info_common.py
"""클래스 홈 — 소속 클래스 목록 조회 공통 테스트 (CH-001~010).

대상 API:
  GET /classroom   소속 클래스 목록 조회 (학습자·교육자 공통)
"""
import pytest

from api.endpoints.classhome.classroom_api import ClassroomAPI
from api.schemas.classhome_schema import ClasshomeSchemas
from fixtures.classhome_fixture import CLASSROOM_CLIENTS
from utils.helpers.api_assertions import assert_200, assert_valid_schema

# ── 경계값 상수 ───────────────────────────────────────────────
VALID_SKIP = 0
VALID_COUNT = 10
LARGE_COUNT = 99999         # CH-006/007: 상한선 없음 확인 및 skip overflow용 큰 값


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
        assert_200(resp)
        data = resp.json()
        assert_valid_schema(data, ClasshomeSchemas.CLASSROOM_LIST_SCHEMA)
        for item in data:
            assert item["name"] != "", f"빈 name 항목 발견: {item}"
        ids = [item["id"] for item in data]
        assert len(ids) == len(set(ids)), f"중복 classroom ID 발견: {ids}"

    @pytest.mark.parametrize("client_fixture", CLASSROOM_CLIENTS)
    @pytest.mark.parametrize("params,expected_missing", [
        pytest.param({}, {"skip", "count"}, id="CH-002-both-missing"),
        pytest.param({"skip": VALID_SKIP}, {"count"}, id="CH-003-count-missing"),
    ])
    def test_ch_002_003_missing_params_returns_422(self, request, client_fixture, params, expected_missing):
        """[CH-002/003] 필수 파라미터 누락 시 422 반환 및 missing 필드 검증.

        기대값:
          - HTTP 422
          - detail 에 누락된 필드가 missing 타입으로 포함
        """
        api: ClassroomAPI = request.getfixturevalue(client_fixture)
        resp = api.get_classroom_list(**params)
        assert resp.status_code == 422, resp.text
        detail = resp.json().get("detail", [])
        missing_fields = {item["loc"][-1] for item in detail if item.get("type") == "missing" and item.get("loc")}
        for field in expected_missing:
            assert field in missing_fields, f"{field} missing 항목이 없음: {detail}"

    @pytest.mark.parametrize("client_fixture", CLASSROOM_CLIENTS)
    @pytest.mark.parametrize("bad_count,expected_error", [
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
        assert_200(resp)

    @pytest.mark.parametrize("client_fixture", CLASSROOM_CLIENTS)
    def test_ch_007_skip_exceeds_total_returns_empty(self, request, client_fixture):
        """[CH-007] 실제 소속 개수보다 큰 skip 값 사용 시 빈 배열을 반환해야 한다.

        기대값:
          - HTTP 200
          - 응답 배열 == []
        """
        api: ClassroomAPI = request.getfixturevalue(client_fixture)
        resp = api.get_classroom_list(skip=LARGE_COUNT, count=VALID_COUNT)
        assert_200(resp)
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
        assert_200(count_resp)
        total: int = count_resp.json()
        assert isinstance(total, int), count_resp.text

        list_resp = api.get_classroom_list(skip=0, count=max(total, 1))
        assert_200(list_resp)
        items = list_resp.json()
        assert len(items) == total, f"목록 길이({len(items)}) ≠ count API 값({total})"
        ids = [item["id"] for item in items]
        assert len(ids) == len(set(ids)), f"중복 classroom ID 발견: {ids}"
