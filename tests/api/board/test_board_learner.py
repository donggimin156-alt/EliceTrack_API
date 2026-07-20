# tests/api/test_board_learner.py
"""게시판 학습자 전용 API 테스트 — 학습자 계정에서만 허용·제한되는 기능."""
import pytest


@pytest.mark.api
@pytest.mark.board
@pytest.mark.learner
class TestBoardLearner:
    """학습자 전용 게시판 API: 학습자만 접근 가능한 시나리오."""
    pass
