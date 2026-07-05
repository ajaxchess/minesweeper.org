"""
tests/test_drills.py — generator-level tests for all 7 bootcamp drill types.

These test the pure board-generation and click-evaluation logic in
phase7_drills.generator. Route-level behavior (auth, resume, idempotent
submit) is covered by phase7_drills/smoke_test.py against a running app.
"""
import pytest

from phase7_drills import generator as gen
from phase7_drills.generator import (
    ALL_DRILL_TYPES,
    DRILL_TYPE_L1, DRILL_TYPE_L2, DRILL_TYPE_L3, DRILL_TYPE_L4,
    DRILL_TYPE_L5, DRILL_TYPE_L6, DRILL_TYPE_L7,
    MINE_FATAL_TYPES, REVEALED_TARGET_TYPES,
    evaluate_click, generate_drill_set,
    serialize_solution, serialize_visible, deserialize_solution,
)

SEED = 20260701


@pytest.fixture(scope="module")
def boards_by_type():
    """One small drill set per type, generated once for the whole module."""
    return {
        dt: generate_drill_set(base_seed=SEED, n=3, drill_type=dt)
        for dt in ALL_DRILL_TYPES
    }


# ── Registry consistency ─────────────────────────────────────────────────────

def test_all_seven_types_registered():
    assert len(ALL_DRILL_TYPES) == 7
    assert set(gen._GENERATORS) == set(ALL_DRILL_TYPES)
    assert set(gen.DRILL_PROMPTS) == set(ALL_DRILL_TYPES)
    assert set(gen.DRILL_NAMES) == set(ALL_DRILL_TYPES)


def test_response_models_literal_matches_generator():
    from typing import get_args
    from phase7_drills.response_models import DrillType
    assert set(get_args(DrillType)) == set(ALL_DRILL_TYPES)


# ── Generation invariants (every type) ───────────────────────────────────────

@pytest.mark.parametrize("dt", ALL_DRILL_TYPES)
def test_boards_are_valid(dt, boards_by_type):
    for board in boards_by_type[dt]:
        assert board.drill_type == dt
        assert board.correct_cells, "board must have at least one correct cell"
        assert board.optimal_cell in board.correct_cells
        assert board.optimal_opening_size > 0
        assert len(board.mines) == board.num_mines
        # Flags only ever sit on real mines.
        assert board.flags <= board.mines
        # Revealed cells are never mines.
        assert not (board.revealed & board.mines)


@pytest.mark.parametrize("dt", ALL_DRILL_TYPES)
def test_generation_is_deterministic(dt):
    a = generate_drill_set(base_seed=SEED, n=2, drill_type=dt)
    b = generate_drill_set(base_seed=SEED, n=2, drill_type=dt)
    assert [serialize_solution(x) for x in a] == [serialize_solution(x) for x in b]


@pytest.mark.parametrize("dt", ALL_DRILL_TYPES)
def test_visible_payload_never_leaks_mines(dt, boards_by_type):
    for board in boards_by_type[dt]:
        vis = serialize_visible(board)
        assert "mines" not in vis
        assert "correct_cells" not in vis
        assert "optimal_cell" not in vis
        assert vis["prompt"], "every drill type needs a prompt"


@pytest.mark.parametrize("dt", ALL_DRILL_TYPES)
def test_solution_roundtrip_preserves_evaluation(dt, boards_by_type):
    for board in boards_by_type[dt]:
        restored = deserialize_solution(serialize_solution(board))
        r, c = board.optimal_cell
        before = evaluate_click(board, r, c)
        after = evaluate_click(restored, r, c)
        assert before == after
        assert before.is_correct


# ── Click evaluation semantics ───────────────────────────────────────────────

@pytest.mark.parametrize("dt", ALL_DRILL_TYPES)
def test_optimal_click_is_correct(dt, boards_by_type):
    for board in boards_by_type[dt]:
        r, c = board.optimal_cell
        result = evaluate_click(board, r, c)
        assert result.is_correct
        assert not result.is_mine
        assert result.relative_quality == 1.0


@pytest.mark.parametrize("dt", ALL_DRILL_TYPES)
def test_out_of_bounds_and_flagged_clicks_miss(dt, boards_by_type):
    for board in boards_by_type[dt]:
        assert not evaluate_click(board, -1, 0).is_correct
        assert not evaluate_click(board, board.height, board.width).is_correct
        for cell in list(board.flags)[:2]:
            result = evaluate_click(board, *cell)
            assert not result.is_correct
            assert not result.is_mine


@pytest.mark.parametrize("dt", sorted(MINE_FATAL_TYPES))
def test_unrevealed_mine_click_is_fatal(dt, boards_by_type):
    for board in boards_by_type[dt]:
        unflagged_mines = board.mines - board.flags
        if not unflagged_mines:
            continue
        result = evaluate_click(board, *next(iter(unflagged_mines)))
        assert result.is_mine
        assert not result.is_correct


@pytest.mark.parametrize("dt", sorted(REVEALED_TARGET_TYPES))
def test_revealed_target_types_reject_unrevealed_clicks(dt, boards_by_type):
    for board in boards_by_type[dt]:
        unrevealed = [
            (r, c)
            for r in range(board.height) for c in range(board.width)
            if (r, c) not in board.revealed and (r, c) not in board.flags
        ]
        result = evaluate_click(board, *unrevealed[0])
        assert not result.is_correct
        assert not result.is_mine
        assert result.opening_size == 0


@pytest.mark.parametrize("dt", [DRILL_TYPE_L5, DRILL_TYPE_L3, DRILL_TYPE_L7, DRILL_TYPE_L6])
def test_unrevealed_target_types_reject_revealed_clicks(dt, boards_by_type):
    for board in boards_by_type[dt]:
        result = evaluate_click(board, *next(iter(board.revealed)))
        assert not result.is_correct
        assert result.opening_size == 0


# ── Type-specific lessons ────────────────────────────────────────────────────

def test_l1_has_both_chord_and_click_candidates(boards_by_type):
    """The chord-or-click comparison needs a meaningful candidate of each kind."""
    for board in boards_by_type[DRILL_TYPE_L1]:
        chord_ok = any(
            gen._chord_reveal_size(board, r, c) >= gen.MIN_L1_EACH_KIND
            for (r, c) in board.revealed
        )
        safe, _ = gen._tier1_deduce(board)
        click_ok = any(
            gen._flood_size(board, *cell) >= gen.MIN_L1_EACH_KIND for cell in safe
        )
        assert chord_ok and click_ok


def test_l1_accepts_both_target_kinds(boards_by_type):
    for board in boards_by_type[DRILL_TYPE_L1]:
        revealed_correct = [c for c in board.correct_cells if c in board.revealed]
        unrevealed_correct = [c for c in board.correct_cells if c not in board.revealed]
        for cell in (revealed_correct[:1] + unrevealed_correct[:1]):
            assert evaluate_click(board, *cell).is_correct


def test_l2_correct_cells_are_provable_flag_then_chords(boards_by_type):
    for board in boards_by_type[DRILL_TYPE_L2]:
        assert not board.flags, "L2 boards start with no flags — that's the drill"
        for cell in board.correct_cells:
            assert cell in board.revealed
            needed = gen._l2_needed_flags(board, *cell)
            assert needed is not None
            assert 1 <= len(needed) <= gen.MAX_L2_FLAGS_NEEDED
            assert needed <= board.mines, "needed flags must be provable real mines"


def test_l3_correct_cells_are_tier1_provable_and_safe(boards_by_type):
    for board in boards_by_type[DRILL_TYPE_L3]:
        assert not board.flags, "L3 is the no-flag drill"
        safe, _ = gen._tier1_deduce(board)
        assert board.correct_cells <= safe
        assert not (board.correct_cells & board.mines)


def test_l7_requires_fishing(boards_by_type):
    """No tier-1 safe cell may exist, and the answer must be solver-provable."""
    for board in boards_by_type[DRILL_TYPE_L7]:
        tier1_safe, _ = gen._tier1_deduce(board)
        tier1_safe = {s for s in tier1_safe if s not in board.revealed}
        assert not tier1_safe, "L7 must have no trivially-safe cell"
        assert not (board.correct_cells & board.mines)
        assert board.correct_cells <= gen._solver_safe_cells(board)


def test_reveal_preview_matches_score(boards_by_type):
    """compute_reveal_cells must agree with the score used for the verdict."""
    for dt in (DRILL_TYPE_L1, DRILL_TYPE_L2, DRILL_TYPE_L3, DRILL_TYPE_L7):
        for board in boards_by_type[dt]:
            r, c = board.optimal_cell
            revealed = gen.compute_reveal_cells(board, r, c)
            assert len(revealed) == board.optimal_opening_size
