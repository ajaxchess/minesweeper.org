"""
tests/test_tametsi_generator.py — Unit tests for F79-A: Tametsi board generator.

These tests are standalone — no FastAPI app or database required.
"""
import random
import sys
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tametsi_generator import (
    LEVELS,
    TametsiBoard,
    _adjacency_count,
    _board_hash,
    _compute_3bv,
    _solve,
    daily_rng,
    generate_board,
    generate_daily,
)

FIXED_RNG = random.Random(42)


# ── Override conftest's clean_db — these are pure unit tests, no DB used ───────

@pytest.fixture(autouse=True)
def clean_db():
    pass


# ── Helpers ────────────────────────────────────────────────────────────────────

def fresh_rng(seed=42):
    return random.Random(seed)


# ── _adjacency_count ───────────────────────────────────────────────────────────

class TestAdjacencyCount:
    def test_corner_with_no_mines(self):
        assert _adjacency_count(0, 0, frozenset(), 3, 3) == 0

    def test_centre_surrounded_by_mines(self):
        mines = frozenset({(0,0),(0,1),(0,2),(1,0),(1,2),(2,0),(2,1),(2,2)})
        assert _adjacency_count(1, 1, mines, 3, 3) == 8

    def test_edge_cell_partial_neighbors(self):
        mines = frozenset({(0, 1), (1, 1)})
        assert _adjacency_count(0, 0, mines, 3, 3) == 2


# ── _compute_3bv ───────────────────────────────────────────────────────────────

class TestCompute3BV:
    def test_all_zeros_is_one_opening(self):
        # 3×3 board with no mines → one big opening
        assert _compute_3bv(frozenset(), 3, 3) == 1

    def test_isolated_numbered_cells(self):
        # Single mine in the centre of 3×3 — all 8 safe cells have count ≥ 1
        # and are isolated numbered cells; no openings
        mines = frozenset({(1, 1)})
        assert _compute_3bv(mines, 3, 3) == 8

    def test_positive_integer(self):
        mines = frozenset({(0, 1), (2, 3)})
        result = _compute_3bv(mines, 4, 5)
        assert isinstance(result, int) and result > 0


# ── _board_hash ────────────────────────────────────────────────────────────────

class TestBoardHash:
    def test_stable_same_input(self):
        mines = frozenset({(0, 1), (1, 2)})
        assert _board_hash(3, 3, mines) == _board_hash(3, 3, mines)

    def test_different_mines_different_hash(self):
        m1 = frozenset({(0, 1)})
        m2 = frozenset({(1, 0)})
        assert _board_hash(3, 3, m1) != _board_hash(3, 3, m2)

    def test_different_dimensions_different_hash(self):
        mines = frozenset({(0, 1)})
        assert _board_hash(3, 3, mines) != _board_hash(4, 4, mines)

    def test_is_64_char_hex(self):
        h = _board_hash(3, 3, frozenset({(0, 1)}))
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


# ── _solve ─────────────────────────────────────────────────────────────────────

class TestSolve:
    def test_trivial_board_no_mines(self):
        # 2×2, no mines — (0,0) opens the whole board immediately
        assert _solve(frozenset(), 2, 2, [0, 0], [0, 0]) is True

    def test_single_mine_deducible_from_row_col(self):
        # 2×2, one mine at (1,1). row_counts=[0,1], col_counts=[0,1]
        # (0,0) adj=1, row 0 has 0 mines → (0,1) is safe; col 0 has 0 mines → (1,0) safe
        # then row 1 has 1 mine and only (1,1) unknown → mine at (1,1)
        mines = frozenset({(1, 1)})
        assert _solve(mines, 2, 2, [0, 1], [0, 1]) is True

    def test_unsolvable_returns_false(self):
        # 5×5 board with 4 mines along the main diagonal.
        # Constraints resolve (1,1) and (2,2) uniquely, but the bottom-right
        # 2×2 sub-problem is a pure 50/50: mines at {(3,3),(4,4)} vs
        # {(3,4),(4,3)} produce identical row/col counts and identical
        # adjacency numbers at every revealed cell.
        mines = frozenset({(1, 1), (2, 2), (3, 3), (4, 4)})
        row_counts = [0, 1, 1, 1, 1]
        col_counts = [0, 1, 1, 1, 1]
        assert _solve(mines, 5, 5, row_counts, col_counts) is False

    def test_origin_never_a_mine(self):
        # Solver always starts by revealing (0,0); if (0,0) were a mine the
        # board would be invalid — generator prevents this, but solver should
        # not crash if given a valid board where (0,0) is safe
        mines = frozenset({(0, 1)})
        row_counts = [1, 0]
        col_counts = [0, 1]
        # (0,0) adj=1; col 0 has 0 mines → (1,0) safe; row 0 has 1 mine, only (0,1) left
        assert _solve(mines, 2, 2, row_counts, col_counts) is True


# ── generate_board ─────────────────────────────────────────────────────────────

class TestGenerateBoard:
    def test_returns_tametsi_board(self):
        board = generate_board(9, 9, 10, rng=fresh_rng())
        assert isinstance(board, TametsiBoard)

    def test_origin_is_never_a_mine(self):
        for seed in range(20):
            board = generate_board(9, 9, 10, rng=fresh_rng(seed))
            assert (0, 0) not in board.mines

    def test_correct_mine_count(self):
        board = generate_board(9, 9, 10, rng=fresh_rng())
        assert len(board.mines) == 10

    def test_row_col_counts_are_correct(self):
        board = generate_board(9, 9, 10, rng=fresh_rng())
        for r in range(board.rows):
            expected = sum(1 for mr, mc in board.mines if mr == r)
            assert board.row_counts[r] == expected
        for c in range(board.cols):
            expected = sum(1 for mr, mc in board.mines if mc == c)
            assert board.col_counts[c] == expected

    def test_board_is_no_guess_solvable(self):
        board = generate_board(9, 9, 10, rng=fresh_rng())
        assert _solve(board.mines, board.rows, board.cols,
                      board.row_counts, board.col_counts) is True

    def test_bbbv_is_positive_int(self):
        board = generate_board(9, 9, 10, rng=fresh_rng())
        assert isinstance(board.bbbv, int) and board.bbbv > 0

    def test_board_hash_is_64_char_hex(self):
        board = generate_board(9, 9, 10, rng=fresh_rng())
        assert len(board.board_hash) == 64
        assert all(c in "0123456789abcdef" for c in board.board_hash)

    def test_board_hash_stable(self):
        b1 = generate_board(9, 9, 10, rng=fresh_rng(7))
        b2 = generate_board(9, 9, 10, rng=fresh_rng(7))
        assert b1.board_hash == b2.board_hash

    def test_different_rng_seeds_usually_give_different_hashes(self):
        hashes = {generate_board(9, 9, 10, rng=fresh_rng(s)).board_hash for s in range(10)}
        assert len(hashes) > 1

    def test_board_data_schema(self):
        board = generate_board(9, 9, 10, rng=fresh_rng())
        bd = board.board_data
        assert set(bd.keys()) == {"mines", "row_counts", "col_counts"}
        assert len(bd["mines"]) == 10
        assert all(len(m) == 2 for m in bd["mines"])
        assert len(bd["row_counts"]) == board.rows
        assert len(bd["col_counts"]) == board.cols

    def test_board_data_mines_sorted(self):
        board = generate_board(9, 9, 10, rng=fresh_rng())
        mines = board.board_data["mines"]
        assert mines == sorted(mines)

    def test_too_many_mines_raises(self):
        with pytest.raises(ValueError, match="Too many mines"):
            generate_board(3, 3, 9, rng=fresh_rng())

    def test_max_attempts_zero_raises_runtime_error(self):
        with pytest.raises(RuntimeError, match="Could not generate"):
            generate_board(9, 9, 10, rng=fresh_rng(), max_attempts=0)


# ── generate_board — difficulty presets ───────────────────────────────────────

class TestDifficultyLevels:
    def test_beginner_generates(self):
        rows, cols, mines = LEVELS["beginner"]
        board = generate_board(rows, cols, mines, rng=fresh_rng())
        assert board.rows == 9 and board.cols == 9 and len(board.mines) == 10

    def test_intermediate_generates(self):
        rows, cols, mines = LEVELS["intermediate"]
        board = generate_board(rows, cols, mines, rng=fresh_rng())
        assert board.rows == 16 and board.cols == 16 and len(board.mines) == 40

    @pytest.mark.slow
    def test_expert_generates(self):
        rows, cols, mines = LEVELS["expert"]
        board = generate_board(rows, cols, mines, rng=fresh_rng())
        assert board.rows == 16 and board.cols == 30 and len(board.mines) == 99


# ── daily_rng + generate_daily ─────────────────────────────────────────────────

class TestDailyGeneration:
    def test_same_level_date_gives_same_board(self):
        b1 = generate_daily("beginner", "2026-05-07")
        b2 = generate_daily("beginner", "2026-05-07")
        assert b1.board_hash == b2.board_hash

    def test_different_dates_give_different_boards(self):
        b1 = generate_daily("beginner", "2026-05-07")
        b2 = generate_daily("beginner", "2026-05-08")
        assert b1.board_hash != b2.board_hash

    def test_different_levels_give_different_boards(self):
        b1 = generate_daily("beginner",     "2026-05-07")
        b2 = generate_daily("intermediate", "2026-05-07")
        assert b1.board_hash != b2.board_hash

    def test_daily_board_is_solvable(self):
        board = generate_daily("beginner", "2026-05-07")
        assert _solve(board.mines, board.rows, board.cols,
                      board.row_counts, board.col_counts) is True

    def test_unknown_level_raises(self):
        with pytest.raises(ValueError, match="Unknown level"):
            daily_rng("legendary", "2026-05-07")
