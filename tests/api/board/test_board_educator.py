# tests/api/test_board_educator.py
"""게시판 교육자(기관 관리자) 전용 API 테스트 — 교육자 계정에서만 허용·제한되는 기능."""
import pytest

from fixtures.elice_fixture import EliceApiClient


@pytest.mark.api
@pytest.mark.board
@pytest.mark.educator
class TestBoardEducator:
    """교육자 전용 게시판 API: 교육자(기관 관리자)만 접근 가능한 시나리오."""
    pass
