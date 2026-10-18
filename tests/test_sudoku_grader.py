"""
tests/test_sudoku_grader.py — Tests for the technique-based Sudoku grader (F-SUDOKU-GRADING).
"""
import pytest
from sudoku_grader import grade, grade_for_difficulty, Technique, TECHNIQUE_NAMES, GradeResult


# A well-known puzzle solvable with naked and hidden singles only.
EASY_PUZZLE = "530070000600195000098000060800060003400803001700020006060000280000419005000080079"

# A puzzle that requires naked pairs (constructed to need pair elimination).
# This is a medium-difficulty puzzle.
MEDIUM_PUZZLE = "000000012000035000000600070700000300060000010008000006090007000000580000310000000"


class TestGradeBasics:
    def test_easy_puzzle_solved_with_singles(self):
        result = grade(EASY_PUZZLE)
        assert result.solved is True
        assert result.hardest_technique is not None
        assert result.hardest_technique <= Technique.HIDDEN_SINGLE
        assert result.difficulty == "easy"

    def test_solved_puzzle_returns_complete_board(self):
        result = grade(EASY_PUZZLE)
        assert result.solved is True
        # All techniques used should be valid
        for t in result.techniques_used:
            assert t in TECHNIQUE_NAMES

    def test_invalid_givens_length(self):
        with pytest.raises(ValueError, match="81 digits"):
            grade("123")

    def test_invalid_givens_chars(self):
        with pytest.raises(ValueError, match="81 digits"):
            grade("a" * 81)

    def test_empty_board_is_unsolvable_by_logic(self):
        result = grade("0" * 81)
        # An empty board cannot be solved by logic alone (needs guessing)
        assert result.solved is False

    def test_solved_board_returns_no_techniques(self):
        # A fully filled valid board
        solved = "534678912672195348198342567859761423426853791713924856961537284287419635345286179"
        result = grade(solved)
        assert result.solved is True
        assert result.hardest_technique is None
        assert len(result.techniques_used) == 0


class TestGradeForDifficulty:
    def test_easy_puzzle_grades_as_easy(self):
        assert grade_for_difficulty(EASY_PUZZLE, "easy") is True

    def test_easy_puzzle_not_medium(self):
        # An easy puzzle should not grade as medium (it doesn't NEED pairs)
        assert grade_for_difficulty(EASY_PUZZLE, "medium") is False

    def test_invalid_difficulty_returns_false(self):
        assert grade_for_difficulty(EASY_PUZZLE, "impossible") is False

    def test_daily_maps_to_medium(self):
        # Daily uses the same range as medium
        result = grade(EASY_PUZZLE)
        if result.difficulty == "easy":
            assert grade_for_difficulty(EASY_PUZZLE, "daily") is False


class TestTechniqueNames:
    def test_all_techniques_have_names(self):
        for t in Technique:
            assert t in TECHNIQUE_NAMES
            assert isinstance(TECHNIQUE_NAMES[t], str)
            assert len(TECHNIQUE_NAMES[t]) > 0

    def test_grade_result_is_named_tuple(self):
        result = grade(EASY_PUZZLE)
        assert isinstance(result, GradeResult)
        assert hasattr(result, "solved")
        assert hasattr(result, "hardest_technique")
        assert hasattr(result, "difficulty")
        assert hasattr(result, "techniques_used")
