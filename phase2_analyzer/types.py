"""
analyzer.types — Domain types for the move-log analyzer.

All dataclasses are deliberately plain (no Pydantic) to keep the analyzer
independent of any framework. Pydantic conversion happens at the FastAPI
boundary in pipeline.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class Action(str, Enum):
    LEFT_CLICK   = "l"     # matches client-side rewindLog encoding
    RIGHT_CLICK  = "r"
    CHORD        = "c"


class Difficulty(str, Enum):
    BEGINNER     = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT       = "expert"
    CUSTOM       = "custom"


class Outcome(str, Enum):
    WIN     = "win"
    LOSS    = "loss"
    ABANDON = "abandon"


CellKind = Literal["unrevealed", "flagged", "revealed", "mine"]


# ─────────────────────────────────────────────────────────────────────────────
# Input shapes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(slots=True)
class Move:
    """One row of the rewind log: timestamp + action + position."""
    t_ms:   int            # ms since game start
    action: Action
    y:      int            # row (0-indexed)
    x:      int            # column (0-indexed)

    @classmethod
    def from_log_entry(cls, entry: list) -> "Move":
        """Parse the client wire format: [t_ms, type_str, row, col]."""
        t_ms, type_str, row, col = entry
        return cls(t_ms=t_ms, action=Action(type_str), y=row, x=col)


@dataclass(slots=True)
class Game:
    """A full game record fed to the analyzer."""
    game_id:        int
    player_id:      Optional[str]      # user_email or guest_token
    difficulty:     Difficulty
    width:          int
    height:         int
    mine_count:     int
    three_bv:       int
    mine_layout:    list[list[bool]]   # [y][x] = True if mine
    move_log:       list[Move]
    outcome:        Outcome
    duration_ms:    int
    no_guess:       bool = False
    board_hash:     Optional[str] = None

    @property
    def total_safe_cells(self) -> int:
        return self.width * self.height - self.mine_count


# ─────────────────────────────────────────────────────────────────────────────
# Board snapshot (mutable during simulation)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(slots=True)
class CellState:
    kind: CellKind
    adjacent_mines: int = 0    # only meaningful when kind == "revealed"


@dataclass(slots=True)
class BoardSnapshot:
    width:       int
    height:      int
    mine_layout: list[list[bool]]
    cells:       list[list[CellState]]    # [y][x]

    def __getitem__(self, yx: tuple[int, int]) -> CellState:
        y, x = yx
        return self.cells[y][x]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height


# ─────────────────────────────────────────────────────────────────────────────
# Solver result
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(slots=True)
class SolverResult:
    provably_safe: list[tuple[int, int]]       # (x, y)
    provably_mine: list[tuple[int, int]]
    ambiguous:     list[tuple[int, int]]


# ─────────────────────────────────────────────────────────────────────────────
# Per-pass report types
# ─────────────────────────────────────────────────────────────────────────────

# Speed-Efficiency passes (Part 1)

@dataclass(slots=True)
class BasicStats:
    time_s:                  float
    three_bv:                int
    three_bv_per_sec:        float
    total_clicks:            int
    left_clicks:             int
    right_clicks:            int
    chord_count:             int
    wasted_chords:           int
    successful_chords:       int
    cells_cleared_by_chord:  int
    cells_cleared_by_left:   int
    ioe:                     float        # 3BV / clicks
    throughput:              float        # 3BV/s × IOE
    correctness:             float        # useful_clicks / total_clicks


@dataclass(slots=True)
class WastedClick:
    move_index: int
    move:       Move
    reason:     Literal["safetyChord", "flagOnUnused", "doubleFlag", "reflaggedSafe"]


@dataclass(slots=True)
class WastedClickReport:
    wasted:        list[WastedClick]
    total_clicks:  int
    useful_clicks: int
    correctness:   float


@dataclass(slots=True)
class MissedShortcut:
    move_indices: list[int]
    description:  str
    clicks_saved: int


@dataclass(slots=True)
class ShortcutReport:
    missed: list[MissedShortcut]


@dataclass(slots=True)
class StrandedFlag:
    move_index: int
    cell:       tuple[int, int]


@dataclass(slots=True)
class PatternEvent:
    pattern_type:  str
    appeared_t_ms: int
    resolved_t_ms: Optional[int]
    reaction_ms:   Optional[int]
    cells:         list[tuple[int, int]]


@dataclass(slots=True)
class DeathReport:
    cause:                Literal["forcedGuess", "avoidableGuess", "misread",
                                   "wrongFlag", "misclick", "chordError"]
    cell:                 tuple[int, int]
    region:               Literal["corner", "edge", "center", "denseCluster"]
    surrounding_pattern:  Optional[str]
    solver_alternative:   Optional[tuple[int, int]]


@dataclass(slots=True)
class AvoidableGuess:
    move_index: int
    cell:       tuple[int, int]


@dataclass(slots=True)
class GuessReport:
    total_guesses:     int
    forced_guesses:    int
    avoidable_guesses: list[AvoidableGuess]


@dataclass(slots=True)
class LevelDiagnosis:
    """Bootcamp level diagnosis. Now scores all 7 levels."""
    current_level:    int                # 1–7
    level_mastery:    dict[int, float]   # {1: 0.92, 2: 0.45, ..., 7: 0.0}
    blockers:         list[str]


# ── Dard advanced passes (Part 2) ────────────────────────────────────────────

@dataclass(slots=True)
class OpeningOpportunity:
    move_index:           int                          # move where opportunity existed
    cell:                 tuple[int, int]              # the candidate cell
    kind:                 Literal["guaranteed", "potential"]
    pattern:              Optional[str]                # e.g. "L-shape-edge"
    probability:          float                        # 1.0 for guaranteed
    cells_required_safe:  int                          # for potential openings
    taken_by_player:      bool
    estimated_clicks_saved: int


@dataclass(slots=True)
class OpeningReport:
    opportunities:       list[OpeningOpportunity]
    guaranteed_taken:    int
    guaranteed_missed:   int
    potential_taken:     int
    potential_missed:    int
    estimated_seconds_lost: float


@dataclass(slots=True)
class FishingOpportunity:
    move_index:           int
    cell:                 tuple[int, int]
    kind:                 Literal["fishing-for-1", "fishing-for-2"]
    success_probability:  float
    taken_by_player:      bool
    succeeded:            Optional[bool]      # None if not attempted


@dataclass(slots=True)
class FishingReport:
    opportunities:    list[FishingOpportunity]
    fishes_attempted: int
    fishes_succeeded: int
    fishes_missed:    int


@dataclass(slots=True)
class FlagValue:
    move_index:         int
    cell:               tuple[int, int]
    future_chord_uses:  int       # times this flag participated in a future chord
    value_score:        float     # weighted score (uses + position bonus)
    high_value:         bool      # heuristic threshold


@dataclass(slots=True)
class FlagValueReport:
    flags:                  list[FlagValue]
    avg_value_score:        float
    high_value_count:       int
    low_value_count:        int
    high_value_pct:         float


@dataclass(slots=True)
class HierarchyDeviation:
    move_index:        int
    player_choice:     str       # e.g. "default-NF-click"
    optimal_choice:    str       # e.g. "guaranteed-opening"
    optimal_priority:  int       # 1 (highest) to 5 (lowest)
    chosen_priority:   int
    estimated_cost:    int       # clicks lost


@dataclass(slots=True)
class HierarchyReport:
    total_moves:           int
    compliant_moves:       int
    compliance_pct:        float
    deviations:            list[HierarchyDeviation]
    deviation_by_priority: dict[int, int]   # {1: missed-opening count, 2: ..., ...}


# ─────────────────────────────────────────────────────────────────────────────
# Top-level result
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(slots=True)
class FullAnalysis:
    game_id:        int
    basic_stats:    BasicStats
    wasted_clicks:  WastedClickReport
    shortcuts:      ShortcutReport
    stranded_flags: list[StrandedFlag]
    patterns:       list[PatternEvent]
    guesses:        GuessReport
    death:          Optional[DeathReport]
    level:          LevelDiagnosis
    # Dard-framework passes:
    openings:       OpeningReport
    fishing:        FishingReport
    flag_value:     FlagValueReport
    hierarchy:      HierarchyReport
