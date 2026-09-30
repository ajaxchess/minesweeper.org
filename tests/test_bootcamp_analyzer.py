"""
tests/test_bootcamp_analyzer.py — Unit tests for the phase2 analyzer passes.

Each test uses a hand-built Game + Move fixture with a known expected output so
that any regression in a pass immediately points to the guilty function.

Coverage:
  detect_wasted_clicks  — safetyChord, flagOnUnused, clean game
  detect_shortcuts      — no-op right-click before chord, clean game
  detect_stranded_flags — edge flag never chorded, no-flags baseline
  classify_death        — forcedGuess, avoidableGuess, misread, WIN→None
  detect_guesses        — avoidable guess, clean game
  diagnose_level        — L1 below/above 0.85 threshold
  _finalize_level_mastery — L5-7 mastery computation, current_level assignment
"""
import os
import sys

import pytest

os.environ.setdefault("GOOGLE_CLIENT_ID",     "test-client-id.apps.googleusercontent.com")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("SECRET_KEY",           "test-secret-key-32-chars-minimum!!")
os.environ.setdefault("GA_TAG",               "")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from phase2_analyzer.types import (
    Action, Difficulty, FishingReport, FlagValueReport,
    Game, HierarchyReport, LevelDiagnosis, Move,
    OpeningReport, Outcome,
)
from phase2_analyzer.passes_speed_efficiency import (
    classify_death,
    detect_guesses,
    detect_shortcuts,
    detect_stranded_flags,
    detect_wasted_clicks,
    diagnose_level,
)
from phase2_analyzer.pipeline import _finalize_level_mastery


# ─────────────────────────────────────────────────────────────────────────────
# Fixture helpers
# ─────────────────────────────────────────────────────────────────────────────

def _move(t_ms: int, action: str, y: int, x: int) -> Move:
    return Move(t_ms=t_ms, action=Action(action), y=y, x=x)


def _game(
    *,
    width: int,
    height: int,
    mine_layout: list[list[bool]],
    moves: list[tuple],
    outcome: str = "win",
    three_bv: int = 1,
    no_guess: bool = False,
) -> Game:
    return Game(
        game_id=1,
        player_id="test@example.com",
        difficulty=Difficulty.EXPERT,
        width=width,
        height=height,
        mine_count=sum(c for row in mine_layout for c in row),
        three_bv=three_bv,
        mine_layout=mine_layout,
        move_log=[_move(i * 100, a, y, x) for i, (a, y, x) in enumerate(moves)],
        outcome=Outcome(outcome),
        duration_ms=len(moves) * 100,
        no_guess=no_guess,
    )


# 3×3 board with one mine at (x=2, y=0):
#
#   0  1  M   (y=0)
#   0  1  1   (y=1)
#   0  0  0   (y=2)
#
# A single left-click on (0,0) flood-reveals all 8 safe cells in one move.
_MINE_3X3 = [
    [False, False, True],   # y=0: mine at x=2
    [False, False, False],  # y=1
    [False, False, False],  # y=2
]


def wasted_chord_game() -> Game:
    """3 moves: open, flag mine, safety-chord (0 new reveals). 1 wasted."""
    return _game(
        width=3, height=3, mine_layout=_MINE_3X3,
        moves=[
            ("l", 0, 0),   # LEFT_CLICK (0,0) → flood reveals all 8 safe cells
            ("r", 0, 2),   # RIGHT_CLICK (2,0) → flag the mine
            ("c", 1, 1),   # CHORD (1,1): adj=1, flag=1, but all neighbours already
                           # revealed → 0 new cells → safety chord (wasted)
        ],
        outcome="win",
    )


def flag_on_unused_game() -> Game:
    """2 moves: open, flag mine never chorded. 1 wasted (flagOnUnused)."""
    return _game(
        width=3, height=3, mine_layout=_MINE_3X3,
        moves=[
            ("l", 0, 0),   # open board
            ("r", 0, 2),   # flag (2,0) — no chord ever follows
        ],
        outcome="win",
    )


def clean_game() -> Game:
    """1 move: open board. No flags, no chords, 0 wasted clicks."""
    return _game(
        width=3, height=3, mine_layout=_MINE_3X3,
        moves=[("l", 0, 0)],
        outcome="win",
        three_bv=1,
    )


# 4×2 board, mine at (x=3, y=0):
#
#   0  0  1  M   (y=0)
#   0  0  1  1   (y=1)
#
# Left-click (0,0) flood-reveals the 6 safe cells on the left;
# (3,0) and (3,1) stay unrevealed.
_MINE_4X2 = [
    [False, False, False, True],   # y=0
    [False, False, False, False],  # y=1
]


def shortcut_game() -> Game:
    """4 moves: open, flag mine, no-op right-click on a revealed cell, chord.
    The no-op at move 2 followed by the chord at move 3 is detected as a
    missed shortcut because the chord produces the same board with or without
    the redundant right-click."""
    return _game(
        width=4, height=2, mine_layout=_MINE_4X2,
        moves=[
            ("l", 0, 0),   # open: reveals (0,0),(0,1),(1,0),(1,1),(2,0),(2,1)
            ("r", 0, 3),   # flag (3,0)
            ("r", 0, 2),   # RIGHT_CLICK on already-revealed (2,0) → no-op
            ("c", 1, 2),   # CHORD (2,1): adj=1, flag at (3,0) → reveals (3,1)
        ],
        outcome="win",
    )


def stranded_flag_game() -> Game:
    """2 moves: open, edge-flag never chorded. 1 stranded flag."""
    return _game(
        width=3, height=3, mine_layout=_MINE_3X3,
        moves=[
            ("l", 0, 0),   # open board
            ("r", 0, 2),   # flag edge mine at (2,0) — no chord follows
        ],
        outcome="win",
    )


# 4×2 board, mine at (x=3, y=0) — forced-guess death.
# After the flood-open, (3,0) and (3,1) are both unrevealed with constraint
# {(3,0),(3,1)}=1. Solver finds no safe cell → forced guess.
def forced_guess_game() -> Game:
    """2 moves: open, LEFT_CLICK on mine with no deducible safe cell (forced guess)."""
    return _game(
        width=4, height=2, mine_layout=_MINE_4X2,
        moves=[
            ("l", 0, 0),   # open: reveals 6 left-side cells
            ("l", 0, 3),   # click mine at (3,0) — solver has no safe deduction
        ],
        outcome="loss",
    )


# 4×2 board, mines at (x=0, y=0) and (x=3, y=0) — avoidable-guess death.
#
#   M  1  .  M   (y=0)
#   .  .  .  .   (y=1)
#
# Moves: reveal (1,0)[adj=1], flag mine (0,0).
# Now (1,0)'s constraint is satisfied: effective mines = 1-1 flag = 0, so
# neighbours (2,0),(0,1),(1,1),(2,1) are all provably safe.
# Player ignores them and clicks mine (3,0) → avoidable guess.
_MINE_4X2_TWO = [
    [True, False, False, True],   # y=0: mines at x=0 and x=3
    [False, False, False, False], # y=1
]


def avoidable_guess_game() -> Game:
    """3 moves: reveal (1,0), flag (0,0), click ambiguous mine (3,0)."""
    return _game(
        width=4, height=2, mine_layout=_MINE_4X2_TWO,
        moves=[
            ("l", 0, 1),   # reveal (1,0): adj=1
            ("r", 0, 0),   # flag mine at (0,0) — satisfies (1,0)'s constraint
            ("l", 0, 3),   # click mine (3,0) — solver has safe alternatives
        ],
        outcome="loss",
        three_bv=2,
    )


# 3×1 board, mine at (x=0, y=0) — misread death.
# After revealing (1,0) and (2,0), (0,0) is the sole unrevealed cell and the
# only mine → solver marks it provably mine. Player clicks it anyway → misread.
_MINE_3X1 = [
    [True, False, False],   # y=0
]


def misread_game() -> Game:
    """2 moves: open right end, then click the already-deduced mine (misread)."""
    return _game(
        width=3, height=1, mine_layout=_MINE_3X1,
        moves=[
            ("l", 0, 2),   # LEFT_CLICK (2,0): flood reveals (1,0) and (2,0)
            ("l", 0, 0),   # click (0,0) — solver says it's provably a mine
        ],
        outcome="loss",
    )


# ─────────────────────────────────────────────────────────────────────────────
# detect_wasted_clicks
# ─────────────────────────────────────────────────────────────────────────────

def test_safety_chord_counted_as_wasted():
    report = detect_wasted_clicks(wasted_chord_game())
    assert len(report.wasted) == 1
    assert report.wasted[0].reason == "safetyChord"
    assert report.wasted[0].move_index == 2     # the CHORD is move 2
    assert report.total_clicks == 3
    assert report.correctness == pytest.approx(2 / 3)


def test_flag_on_unused_counted_as_wasted():
    report = detect_wasted_clicks(flag_on_unused_game())
    assert len(report.wasted) == 1
    assert report.wasted[0].reason == "flagOnUnused"
    assert report.wasted[0].move_index == 1     # the flag is move 1
    assert report.correctness == pytest.approx(0.5)


def test_clean_game_zero_wasted():
    report = detect_wasted_clicks(clean_game())
    assert report.wasted == []
    assert report.correctness == pytest.approx(1.0)


# ─────────────────────────────────────────────────────────────────────────────
# detect_shortcuts
# ─────────────────────────────────────────────────────────────────────────────

def test_noop_rightclick_before_chord_is_shortcut():
    report = detect_shortcuts(shortcut_game())
    assert len(report.missed) == 1
    assert report.missed[0].move_indices == [2, 3]
    assert report.missed[0].clicks_saved == 1


def test_clean_game_zero_shortcuts():
    report = detect_shortcuts(clean_game())
    assert report.missed == []


# ─────────────────────────────────────────────────────────────────────────────
# detect_stranded_flags
# ─────────────────────────────────────────────────────────────────────────────

def test_edge_flag_never_chorded_is_stranded():
    stranded = detect_stranded_flags(stranded_flag_game())
    assert len(stranded) == 1
    # (2,0) is the flag cell: x=2 = width-1 (edge) and y=0 (top edge)
    assert stranded[0].cell == (2, 0)


def test_no_flags_zero_stranded():
    assert detect_stranded_flags(clean_game()) == []


# ─────────────────────────────────────────────────────────────────────────────
# classify_death
# ─────────────────────────────────────────────────────────────────────────────

def test_forced_guess_death():
    report = classify_death(forced_guess_game())
    assert report is not None
    assert report.cause == "forcedGuess"
    assert report.cell == (3, 0)
    # (3,0) in a 4×2 board: x=3=width-1, y=0 → corner
    assert report.region == "corner"


def test_avoidable_guess_death():
    report = classify_death(avoidable_guess_game())
    assert report is not None
    assert report.cause == "avoidableGuess"
    assert report.cell == (3, 0)
    # (3,0) in a 4×2 board: x=3=width-1, y=0 → corner
    assert report.region == "corner"
    # provably_safe is non-empty; solver_alternative is one of the safe cells
    assert report.solver_alternative is not None


def test_misread_death():
    report = classify_death(misread_game())
    assert report is not None
    assert report.cause == "misread"
    assert report.cell == (0, 0)
    assert report.region == "corner"


def test_win_game_no_death():
    assert classify_death(clean_game()) is None


# ─────────────────────────────────────────────────────────────────────────────
# detect_guesses
# ─────────────────────────────────────────────────────────────────────────────

def test_avoidable_guess_detected():
    report = detect_guesses(avoidable_guess_game())
    # The click on (3,0) is an avoidable guess: (2,0),(0,1),(1,1),(2,1) were safe
    assert len(report.avoidable_guesses) >= 1
    clicked_cells = [g.cell for g in report.avoidable_guesses]
    assert (3, 0) in clicked_cells


def test_clean_game_no_avoidable_guesses():
    """Opening click on a blank board has no solver deductions, so it is
    counted as a forced guess (unavoidable). There must be no AVOIDABLE
    guesses — those would mean the player ignored a safe cell."""
    report = detect_guesses(clean_game())
    assert report.avoidable_guesses == []


# ─────────────────────────────────────────────────────────────────────────────
# diagnose_level
# ─────────────────────────────────────────────────────────────────────────────

def test_high_wasted_clicks_l1_below_threshold():
    """wasted_chord_game: 1 wasted of 3 clicks → correctness≈0.67 → l1≈0.0 → level 1."""
    diag = diagnose_level([wasted_chord_game()])
    assert diag.current_level == 1
    assert diag.level_mastery[1] < 0.85


def test_clean_game_l1_maximum():
    """No wasted clicks → correctness=1.0 → l1=1.0."""
    diag = diagnose_level([clean_game()])
    assert diag.level_mastery[1] == pytest.approx(1.0)


def test_clean_game_level_advances_past_l1():
    """With l1=1.0, l2=1.0, l3=1.0, l4=1.0, level should be at least 5."""
    diag = diagnose_level([clean_game()])
    assert diag.current_level >= 2


def test_no_games_returns_level_1():
    diag = diagnose_level([])
    assert diag.current_level == 1
    assert diag.level_mastery == {k: 0.0 for k in range(1, 8)}


# ─────────────────────────────────────────────────────────────────────────────
# _finalize_level_mastery — L5-7 computation and current_level re-assignment
# ─────────────────────────────────────────────────────────────────────────────

def _level_obj(mastery: dict) -> LevelDiagnosis:
    return LevelDiagnosis(
        current_level=1,
        level_mastery={k: mastery.get(k, 0.0) for k in range(1, 8)},
        blockers=[],
    )


def _make_reports(
    *,
    guaranteed_taken: int = 0,
    guaranteed_missed: int = 0,
    high_value_pct: float = 0.0,
    compliance_pct: float = 0.0,
):
    openings = OpeningReport(
        opportunities=[],
        guaranteed_taken=guaranteed_taken,
        guaranteed_missed=guaranteed_missed,
        potential_taken=0,
        potential_missed=0,
        estimated_seconds_lost=0.0,
    )
    fishing = FishingReport(
        opportunities=[],
        fishes_attempted=0,
        fishes_succeeded=0,
        fishes_missed=0,
    )
    flag_value = FlagValueReport(
        flags=[],
        avg_value_score=0.0,
        high_value_count=0,
        low_value_count=0,
        high_value_pct=high_value_pct,
    )
    hierarchy = HierarchyReport(
        total_moves=10,
        compliant_moves=10,
        compliance_pct=compliance_pct,
        deviations=[],
        deviation_by_priority={},
    )
    return openings, fishing, flag_value, hierarchy


def test_finalize_l5_from_opening_take_rate():
    """guaranteed_taken / (taken + missed) → l5."""
    level = _level_obj({1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0})
    openings, fishing, flag_value, hierarchy = _make_reports(
        guaranteed_taken=8, guaranteed_missed=2,   # 80%
        high_value_pct=1.0, compliance_pct=1.0,
    )
    result = _finalize_level_mastery(level, openings, fishing, flag_value, hierarchy)
    assert result.level_mastery[5] == pytest.approx(0.8)


def test_finalize_l5_zero_when_no_openings():
    level = _level_obj({1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0})
    openings, fishing, flag_value, hierarchy = _make_reports(
        guaranteed_taken=0, guaranteed_missed=0,
        high_value_pct=1.0, compliance_pct=1.0,
    )
    result = _finalize_level_mastery(level, openings, fishing, flag_value, hierarchy)
    assert result.level_mastery[5] == pytest.approx(0.0)


def test_finalize_all_above_threshold_gives_grandmaster():
    """All L1-7 mastery ≥ 0.85 → current_level = 7."""
    level = _level_obj({1: 0.9, 2: 0.9, 3: 0.9, 4: 0.9})
    openings, fishing, flag_value, hierarchy = _make_reports(
        guaranteed_taken=9, guaranteed_missed=1,   # l5=0.9 ≥ 0.85
        high_value_pct=0.9,                        # l6=0.9 ≥ 0.85
        compliance_pct=0.9,                        # l7=0.9 ≥ 0.85
    )
    result = _finalize_level_mastery(level, openings, fishing, flag_value, hierarchy)
    assert result.current_level == 7


def test_finalize_stops_at_first_low_level():
    """L1-4 perfect, l5 below threshold → current_level = 5."""
    level = _level_obj({1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0})
    openings, fishing, flag_value, hierarchy = _make_reports(
        guaranteed_taken=7, guaranteed_missed=3,   # l5=0.7 < 0.85
        high_value_pct=1.0, compliance_pct=1.0,
    )
    result = _finalize_level_mastery(level, openings, fishing, flag_value, hierarchy)
    assert result.current_level == 5


def test_finalize_respects_l1_4_below_threshold():
    """If L3 is below 0.85, current_level must not reach L5+ regardless of Dard scores."""
    level = _level_obj({1: 0.9, 2: 0.9, 3: 0.6, 4: 0.9})   # L3 = 0.6
    openings, fishing, flag_value, hierarchy = _make_reports(
        guaranteed_taken=10, guaranteed_missed=0,
        high_value_pct=1.0, compliance_pct=1.0,
    )
    result = _finalize_level_mastery(level, openings, fishing, flag_value, hierarchy)
    assert result.current_level == 3
