"""
tests/test_sudoku_generator.py — Tests for the server-side puzzle generator (F-SUDOKU-GRADING).
"""
import random

import pytest
from sudoku_generator import generate_puzzle, generate_daily_puzzle, GIVENS_RANGE
from sudoku_grader import grade, Technique


class TestGeneratePuzzle:
    def test_easy_puzzle_generation(self):
        rng = random.Random(42)
        result = generate_puzzle("easy", rng)
        assert result is not None
        assert len(result.givens) == 81
        assert len(result.solution) == 81
        assert result.grade_result.solved is True
        assert result.grade_result.difficulty == "easy"
        given_count = sum(1 for c in result.givens if c != "0")
        lo, hi = GIVENS_RANGE["easy"]
        assert lo <= given_count <= hi

    def test_medium_puzzle_generation(self):
        rng = random.Random(123)
        result = generate_puzzle("medium", rng)
        assert result is not None
        assert result.grade_result.solved is True
        assert result.grade_result.difficulty == "medium"

    def test_puzzle_has_valid_hash(self):
        import hashlib
        rng = random.Random(42)
        result = generate_puzzle("easy", rng)
        assert result is not None
        expected = hashlib.sha256(result.givens.encode()).hexdigest()
        assert result.board_hash == expected

    def test_solution_is_valid(self):
        rng = random.Random(42)
        result = generate_puzzle("easy", rng)
        assert result is not None
        sol = [int(c) for c in result.solution]
        # Check each row has 1-9
        for r in range(9):
            assert set(sol[r*9:(r+1)*9]) == set(range(1, 10))
        # Check each column has 1-9
        for c in range(9):
            assert set(sol[r*9+c] for r in range(9)) == set(range(1, 10))
        # Check each box has 1-9
        for br in range(3):
            for bc in range(3):
                vals = set()
                for dr in range(3):
                    for dc in range(3):
                        vals.add(sol[(br*3+dr)*9 + bc*3+dc])
                assert vals == set(range(1, 10))

    def test_givens_match_solution(self):
        rng = random.Random(42)
        result = generate_puzzle("easy", rng)
        assert result is not None
        for i in range(81):
            if result.givens[i] != "0":
                assert result.givens[i] == result.solution[i]

    def test_invalid_difficulty_raises(self):
        with pytest.raises(ValueError, match="Invalid difficulty"):
            generate_puzzle("nightmare")

    def test_deterministic_with_same_seed(self):
        r1 = generate_puzzle("easy", random.Random(999))
        r2 = generate_puzzle("easy", random.Random(999))
        assert r1 is not None and r2 is not None
        assert r1.givens == r2.givens
        assert r1.solution == r2.solution


class TestGenerateDaily:
    def test_daily_puzzle_deterministic(self):
        r1 = generate_daily_puzzle("2026-10-20")
        r2 = generate_daily_puzzle("2026-10-20")
        assert r1 is not None and r2 is not None
        assert r1.givens == r2.givens

    def test_different_dates_produce_different_puzzles(self):
        r1 = generate_daily_puzzle("2026-10-20")
        r2 = generate_daily_puzzle("2026-10-21")
        assert r1 is not None and r2 is not None
        assert r1.givens != r2.givens

    def test_daily_puzzle_is_medium_difficulty(self):
        result = generate_daily_puzzle("2026-10-20")
        assert result is not None
        assert result.grade_result.solved is True
        # Daily maps to medium range
        assert result.grade_result.hardest_technique <= Technique.HIDDEN_PAIR
