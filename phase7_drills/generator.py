"""
phase7_drills.generator — procedural board generation for drills.

All seven bootcamp drill types are implemented, all using the same
pick-the-best-cell shell (one click per board):

  l1_cut_waste           — Chord-or-click. Both chord-ready numbers AND
                           provably-safe unrevealed cells are candidates;
                           pick whichever single action reveals the most.
                           Trains cutting wasted clicks.

  l2_effective_chord     — Pick the revealed number with the best
                           flag-then-chord payoff. Its missing flags are
                           all provable; the drill scores the chord that
                           placing them would enable. Trains the
                           flag-then-chord rhythm.

  l3_strategic_nf        — No flags anywhere on the board. Pick a cell
                           that is provably safe from the raw numbers
                           (tier-1 deduction). Trains no-flag reading.

  l4_pure_efficiency     — Pick the revealed-number cell that, when chorded,
                           reveals the largest area. The drill pre-places
                           correct flags so a chord is legal. Trains
                           efficient mid-game play.

  l5_opening_recognition — Pick the unrevealed cell that opens the largest
                           area. Trains opening recognition.

  l6_flag_value          — Pick the provably-mine cell whose flag enables
                           the most chord opportunities. Trains flag-value
                           prioritization.

  l7_fishing             — No trivial (tier-1) safe cell exists. Pick the
                           cell that multi-constraint (subset) deduction
                           proves safe. Uses phase2_analyzer's
                           ConstraintSolver. Trains fishing & the decision
                           hierarchy.

Design constraints:
  - All randomness must be derivable from a seed so we can replay drill
    boards (server-side validation, debugging).
  - Mine layouts are kept server-side. Only the visible state (revealed,
    numbers, flags, prompt) is sent to the client.
  - Each board must have a meaningful "best" answer — at least some teaching
    value. Boards that don't qualify are retried with a fresh seed.

Public API:
  generate_l1_cut_waste_board(seed)  -> DrillBoard
  generate_l2_chord_board(seed)      -> DrillBoard
  generate_l3_nf_board(seed)         -> DrillBoard
  generate_l4_efficiency_board(seed) -> DrillBoard
  generate_l5_opening_board(seed)    -> DrillBoard
  generate_l6_flag_value_board(seed) -> DrillBoard
  generate_l7_fishing_board(seed)    -> DrillBoard
  generate_drill_set(base_seed, drill_type, n) -> list[DrillBoard]
  serialize_visible(board)           -> dict (client-safe)
  evaluate_click(board, r, c)        -> EvaluatedClick
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field
from typing import Iterable, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Board constants
# ─────────────────────────────────────────────────────────────────────────────

EXPERT_WIDTH = 30
EXPERT_HEIGHT = 16
EXPERT_MINES = 99

# L5 uses a smaller board so the whole frontier is visible at a glance.
# The lesson is "read the numbers", not "scan a wall of grey." Density is
# kept moderate so the openings still exist behind the frontier.
L5_WIDTH = 16
L5_HEIGHT = 10
L5_MINES = 26     # ~16% density (intermediate-ish)

# Minimum opening size for the best pick.
MIN_L5_OPENING = 4

# The best cell's pressure must be at or below this — i.e., the player can
# look at the surrounding numbers and conclude it's clearly the safest pick.
L5_BEST_MAX_PRESSURE = 0.34

# Composite score for L5 is (1 - pressure) × opening_size.
# This rewards picks that are BOTH safe AND productive — exactly what the
# lesson trains. The "best" cell must beat the runner-up by this multiple
# so the right answer is unambiguous.
L5_BEST_MIN_LEAD = 1.5    # best.score must be ≥ 1.5 × second.score
L5_BEST_MIN_SCORE = 3.0   # best.score must be ≥ 3.0 absolute

# Minimum chord-reveal size for L4 — best chord must open at least this many.
MIN_L4_CHORD_SIZE = 4

# Minimum flag-enabling value for L6 — best flag must enable at least this much.
MIN_L6_FLAG_VALUE = 2

# Fraction of board revealed as the starter state.
STARTER_TARGET_REVEAL_FRACTION = 0.25
L5_STARTER_TARGET_REVEAL_FRACTION = 0.35   # denser reveal on the small board

# A cell counts as "correct" if its score is within this fraction of the max.
CORRECT_THRESHOLD = 0.80


# L1 — best action (chord or click) must reveal at least this many cells,
# and both an interesting chord AND an interesting click must exist so the
# comparison is a real decision.
MIN_L1_BEST = 4
MIN_L1_EACH_KIND = 2

# L2 — the best flag-then-chord must open at least this many cells.
MIN_L2_CHORD_SIZE = 4
# ...and must need at most this many flags (keeps the rhythm tight).
MAX_L2_FLAGS_NEEDED = 2

# L3 — small board like L5; optimal safe cell must open at least this many.
MIN_L3_OPTIMAL = 2
# Frontier must be at least this multiple of the provably-safe set, so
# "find the safe cell" is a real search, not a giveaway.
L3_MIN_FRONTIER_RATIO = 3.0

# L7 — small board; number of solver-provable safe cells required.
MIN_L7_SAFE = 1

# Small-board dimensions shared by L3 / L7 (same rationale as L5 — the
# lesson is reading numbers, not scanning a wall of grey).
SMALL_WIDTH = 16
SMALL_HEIGHT = 10
L3_MINES = 26
L7_MINES = 24
L7_STARTER_TARGET_REVEAL_FRACTION = 0.40


# Supported drill types — single source of truth.
DRILL_TYPE_L1 = "l1_cut_waste"
DRILL_TYPE_L2 = "l2_effective_chord"
DRILL_TYPE_L3 = "l3_strategic_nf"
DRILL_TYPE_L4 = "l4_pure_efficiency"
DRILL_TYPE_L5 = "l5_opening_recognition"
DRILL_TYPE_L6 = "l6_flag_value"
DRILL_TYPE_L7 = "l7_fishing"

ALL_DRILL_TYPES = (
    DRILL_TYPE_L1, DRILL_TYPE_L2, DRILL_TYPE_L3, DRILL_TYPE_L4,
    DRILL_TYPE_L5, DRILL_TYPE_L6, DRILL_TYPE_L7,
)

# Which cells are clickable, per type. L1 allows both.
REVEALED_TARGET_TYPES = frozenset({DRILL_TYPE_L4, DRILL_TYPE_L2})
BOTH_TARGET_TYPES = frozenset({DRILL_TYPE_L1})

# Types where clicking an unrevealed mine is fatal (a real click).
MINE_FATAL_TYPES = frozenset({
    DRILL_TYPE_L5, DRILL_TYPE_L3, DRILL_TYPE_L7, DRILL_TYPE_L1,
})

# Per-drill prompt text shown to the player above the board.
DRILL_PROMPTS = {
    DRILL_TYPE_L1: "Chord or click — which single move reveals the most?",
    DRILL_TYPE_L2: "Which number gives the best flag-then-chord?",
    DRILL_TYPE_L3: "No flags. Which cell is provably safe?",
    DRILL_TYPE_L4: "Which revealed number would you chord next?",
    DRILL_TYPE_L5: "Which unrevealed cell would you click next?",
    DRILL_TYPE_L6: "Which cell would you flag next?",
    DRILL_TYPE_L7: "No easy move exists. Which cell can you prove safe?",
}

# Per-drill description for the results blurb.
DRILL_NAMES = {
    DRILL_TYPE_L1: "Cut Waste",
    DRILL_TYPE_L2: "Effective Chording",
    DRILL_TYPE_L3: "Strategic No-Flag",
    DRILL_TYPE_L4: "Pure Efficiency",
    DRILL_TYPE_L5: "Opening Recognition",
    DRILL_TYPE_L6: "Flag Value",
    DRILL_TYPE_L7: "Fishing & Hierarchy",
}


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DrillBoard:
    """A generated drill board.

    Common fields apply to every drill type. Type-specific scoring is folded
    into `correct_cells` / `optimal_cell` / `optimal_opening_size`, which
    mean slightly different things per drill:

      L5: opening size in cells
      L4: chord-reveal size in cells
      L6: count of chord opportunities the flag enables (× their sizes)
    """
    width: int
    height: int
    num_mines: int
    seed: int

    # Set on every drill type
    drill_type: str = DRILL_TYPE_L5
    mines: set[tuple[int, int]] = field(default_factory=set)
    revealed: set[tuple[int, int]] = field(default_factory=set)
    flags: set[tuple[int, int]] = field(default_factory=set)
    numbers: dict[tuple[int, int], int] = field(default_factory=dict)

    correct_cells: set[tuple[int, int]] = field(default_factory=set)
    optimal_cell: Optional[tuple[int, int]] = None
    optimal_opening_size: int = 0


@dataclass
class EvaluatedClick:
    """Result of evaluating a player's click on a drill board."""
    is_correct: bool
    is_mine: bool
    opening_size: int
    relative_quality: float
    optimal_cell: tuple[int, int]
    optimal_opening_size: int


# ─────────────────────────────────────────────────────────────────────────────
# Public generators
# ─────────────────────────────────────────────────────────────────────────────

def generate_l5_opening_board(seed: int) -> DrillBoard:
    """L5 Opening Recognition — see module docstring."""
    rng = random.Random(seed)
    for _ in range(200):
        attempt_seed = rng.randrange(1, 1_000_000_000)
        board = _try_generate_l5(attempt_seed)
        if board is not None:
            return board
    raise RuntimeError(
        f"Could not generate a valid L5 board after 200 attempts (seed={seed})"
    )


def generate_l4_efficiency_board(seed: int) -> DrillBoard:
    """L4 Pure Efficiency — see module docstring."""
    rng = random.Random(seed)
    for _ in range(40):
        attempt_seed = rng.randrange(1, 1_000_000_000)
        board = _try_generate_l4(attempt_seed)
        if board is not None:
            return board
    raise RuntimeError(
        f"Could not generate a valid L4 board after 40 attempts (seed={seed})"
    )


def generate_l6_flag_value_board(seed: int) -> DrillBoard:
    """L6 Flag Value — see module docstring."""
    rng = random.Random(seed)
    for _ in range(40):
        attempt_seed = rng.randrange(1, 1_000_000_000)
        board = _try_generate_l6(attempt_seed)
        if board is not None:
            return board
    raise RuntimeError(
        f"Could not generate a valid L6 board after 40 attempts (seed={seed})"
    )


def generate_l1_cut_waste_board(seed: int) -> DrillBoard:
    """L1 Cut Waste (chord-or-click) — see module docstring."""
    return _retry_generate(_try_generate_l1, seed, attempts=60, name="L1")


def generate_l2_chord_board(seed: int) -> DrillBoard:
    """L2 Effective Chording (flag-then-chord) — see module docstring."""
    return _retry_generate(_try_generate_l2, seed, attempts=60, name="L2")


def generate_l3_nf_board(seed: int) -> DrillBoard:
    """L3 Strategic No-Flag — see module docstring."""
    return _retry_generate(_try_generate_l3, seed, attempts=200, name="L3")


def generate_l7_fishing_board(seed: int) -> DrillBoard:
    """L7 Fishing & Hierarchy — see module docstring."""
    return _retry_generate(_try_generate_l7, seed, attempts=400, name="L7")


def _retry_generate(fn, seed: int, attempts: int, name: str) -> DrillBoard:
    rng = random.Random(seed)
    for _ in range(attempts):
        attempt_seed = rng.randrange(1, 1_000_000_000)
        board = fn(attempt_seed)
        if board is not None:
            return board
    raise RuntimeError(
        f"Could not generate a valid {name} board after {attempts} attempts (seed={seed})"
    )


_GENERATORS = {
    DRILL_TYPE_L1: generate_l1_cut_waste_board,
    DRILL_TYPE_L2: generate_l2_chord_board,
    DRILL_TYPE_L3: generate_l3_nf_board,
    DRILL_TYPE_L4: generate_l4_efficiency_board,
    DRILL_TYPE_L5: generate_l5_opening_board,
    DRILL_TYPE_L6: generate_l6_flag_value_board,
    DRILL_TYPE_L7: generate_l7_fishing_board,
}


def generate_drill_set(
    base_seed: int,
    n: int = 10,
    drill_type: str = DRILL_TYPE_L5,
) -> list[DrillBoard]:
    """Generate n boards with distinct, seeded layouts for the given drill type."""
    if drill_type not in _GENERATORS:
        raise ValueError(f"Unknown drill_type: {drill_type!r}")
    rng = random.Random(base_seed)
    gen = _GENERATORS[drill_type]
    return [gen(rng.randrange(1, 1_000_000_000)) for _ in range(n)]


# ─────────────────────────────────────────────────────────────────────────────
# Serialization
# ─────────────────────────────────────────────────────────────────────────────

def serialize_visible(board: DrillBoard) -> dict:
    """Visible payload sent to the client — NO mines."""
    return {
        "drill_type": board.drill_type,
        "prompt": DRILL_PROMPTS.get(board.drill_type, ""),
        "width": board.width,
        "height": board.height,
        "num_mines": board.num_mines,
        "revealed": [[r, c] for (r, c) in sorted(board.revealed)],
        "flags":    [[r, c] for (r, c) in sorted(board.flags)],
        "numbers": [
            [r, c, n] for (r, c), n in sorted(board.numbers.items())
        ],
    }


def serialize_solution(board: DrillBoard) -> dict:
    """Full state we persist server-side so we can validate clicks later."""
    return {
        "drill_type": board.drill_type,
        "width": board.width,
        "height": board.height,
        "num_mines": board.num_mines,
        "seed": board.seed,
        "mines":    [[r, c] for (r, c) in sorted(board.mines)],
        "revealed": [[r, c] for (r, c) in sorted(board.revealed)],
        "flags":    [[r, c] for (r, c) in sorted(board.flags)],
        "correct_cells": [[r, c] for (r, c) in sorted(board.correct_cells)],
        "optimal_cell": list(board.optimal_cell) if board.optimal_cell else None,
        "optimal_opening_size": board.optimal_opening_size,
    }


def deserialize_solution(d: dict) -> DrillBoard:
    board = DrillBoard(
        width=d["width"],
        height=d["height"],
        num_mines=d["num_mines"],
        seed=d["seed"],
        drill_type=d.get("drill_type", DRILL_TYPE_L5),
    )
    board.mines    = {tuple(p) for p in d.get("mines",    [])}
    board.revealed = {tuple(p) for p in d.get("revealed", [])}
    board.flags    = {tuple(p) for p in d.get("flags",    [])}
    board.correct_cells = {tuple(p) for p in d.get("correct_cells", [])}
    board.optimal_cell = tuple(d["optimal_cell"]) if d.get("optimal_cell") else None
    board.optimal_opening_size = int(d.get("optimal_opening_size", 0))
    board.numbers = _compute_numbers(board)
    return board


# ─────────────────────────────────────────────────────────────────────────────
# Click evaluation
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_click(board: DrillBoard, r: int, c: int) -> EvaluatedClick:
    """Score the player's click.

    The shape is identical across drill types. The generator decides what
    counts as "correct" (it populated correct_cells) and what counts as a
    fatal mistake (it populated mines / revealed):

      L5/L3/L7: clicking a mine is fatal, clicking a revealed cell is invalid
      L4/L2:    clicking an unrevealed cell is invalid (targets are revealed
                numbers), mine click is impossible
      L1:       both revealed (chord) and unrevealed (click) cells are valid
                targets; clicking an unrevealed mine is fatal
      L6:       clicking a non-mine cell counts as "wrong but not fatal" since
                you can't actually trigger a mine by flagging — but we score
                it as wrong (player thought it was a mine and was wrong)

    For simplicity, the scoring rule is uniform:
      - in correct_cells                  → correct
      - is a mine (MINE_FATAL_TYPES only) → is_mine=True, correct=False
      - everything else                   → correct=False
    """
    in_bounds = 0 <= r < board.height and 0 <= c < board.width

    if not in_bounds:
        return _miss(board)

    dt = board.drill_type

    # Flagged cells are never valid targets.
    if (r, c) in board.flags:
        return _miss(board)

    # L4 / L2: clicking a non-revealed cell is invalid
    if dt in REVEALED_TARGET_TYPES and (r, c) not in board.revealed:
        return _miss(board)

    # L5 / L6 / L3 / L7: clicking an already-revealed cell is invalid.
    # (L1 allows both, L4/L2 handled above.)
    if (
        dt not in REVEALED_TARGET_TYPES
        and dt not in BOTH_TARGET_TYPES
        and (r, c) in board.revealed
    ):
        return _miss(board)

    is_mine = (r, c) in board.mines and (r, c) not in board.revealed
    if dt in MINE_FATAL_TYPES and is_mine:
        return EvaluatedClick(
            is_correct=False, is_mine=True, opening_size=0,
            relative_quality=0.0,
            optimal_cell=board.optimal_cell or (0, 0),
            optimal_opening_size=board.optimal_opening_size,
        )

    # Score size depends on drill type — use generator-provided lookup table.
    score = _score_for(board, r, c)
    relative = (
        score / board.optimal_opening_size
        if board.optimal_opening_size > 0
        else 0.0
    )

    return EvaluatedClick(
        is_correct=(r, c) in board.correct_cells,
        is_mine=False,
        opening_size=score,
        relative_quality=round(relative, 3),
        optimal_cell=board.optimal_cell or (0, 0),
        optimal_opening_size=board.optimal_opening_size,
    )


def compute_reveal_cells(board: DrillBoard, r: int, c: int) -> list[list[int]]:
    """Return [row, col, number] for every cell that would be uncovered by
    a click on (r, c). Honors the drill type:

      L5/L3/L7 — flood-fill from (r, c) if safe; empty if mine
      L4       — chord-reveal from (r, c) if chord-ready; empty otherwise
      L2       — flag-then-chord reveal from (r, c) with its provable flags
                 hypothetically placed; empty otherwise
      L1       — chord-reveal if (r, c) is revealed, flood otherwise
      L6       — empty (flagging doesn't open anything)

    Used by the client to draw what would have happened on this pick — gives
    the player a concrete sense of the lesson even when they picked wrong.
    """
    if board.drill_type == DRILL_TYPE_L6:
        return []
    if not (0 <= r < board.height and 0 <= c < board.width):
        return []
    if board.drill_type == DRILL_TYPE_L4:
        if (r, c) not in board.revealed:
            return []
        return _chord_reveal_cells(board, r, c)
    if board.drill_type == DRILL_TYPE_L2:
        if (r, c) not in board.revealed:
            return []
        synthetic = _l2_board_with_needed_flags(board, r, c)
        if synthetic is None:
            return []
        return _chord_reveal_cells(synthetic, r, c)
    if board.drill_type == DRILL_TYPE_L1 and (r, c) in board.revealed:
        return _chord_reveal_cells(board, r, c)
    # L5 / L3 / L7 / L1-unrevealed
    if (r, c) in board.revealed or (r, c) in board.mines:
        return []
    return _flood_reveal_cells(board, r, c)


def _flood_reveal_cells(board: DrillBoard, r: int, c: int) -> list[list[int]]:
    """BFS flood, returning the (row, col, number) triples of newly-uncovered cells."""
    out: list[list[int]] = []
    visited: set[tuple[int, int]] = set()
    q: deque[tuple[int, int]] = deque([(r, c)])
    while q:
        cr, cc = q.popleft()
        if not (0 <= cr < board.height and 0 <= cc < board.width):
            continue
        if (cr, cc) in visited or (cr, cc) in board.revealed:
            continue
        if (cr, cc) in board.mines or (cr, cc) in board.flags:
            continue
        visited.add((cr, cc))
        n = _count_adj_mines(board, cr, cc)
        out.append([cr, cc, n])
        if n == 0:
            for nr, nc in _neighbors(cr, cc):
                if (nr, nc) not in visited:
                    q.append((nr, nc))
    return out


def _chord_reveal_cells(board: DrillBoard, r: int, c: int) -> list[list[int]]:
    """For a chord-ready cell, return the cells uncovered by the chord."""
    n = _count_adj_mines(board, r, c)
    if n == 0:
        return []
    flagged = sum(1 for nr, nc in _neighbors(r, c) if (nr, nc) in board.flags)
    if flagged != n:
        return []

    already: set[tuple[int, int]] = set(board.revealed)
    out: list[list[int]] = []
    for nr, nc in _neighbors(r, c):
        if not (0 <= nr < board.height and 0 <= nc < board.width):
            continue
        if (nr, nc) in board.flags or (nr, nc) in already:
            continue
        if (nr, nc) in board.mines:
            continue
        # Flood from this neighbour, accumulating into `already` so multi-direction
        # chord reveals don't double-count cells in the same zero region.
        q: deque[tuple[int, int]] = deque([(nr, nc)])
        while q:
            cr, cc = q.popleft()
            if not (0 <= cr < board.height and 0 <= cc < board.width):
                continue
            if (cr, cc) in already or (cr, cc) in board.mines or (cr, cc) in board.flags:
                continue
            already.add((cr, cc))
            nn = _count_adj_mines(board, cr, cc)
            out.append([cr, cc, nn])
            if nn == 0:
                for ar, ac in _neighbors(cr, cc):
                    q.append((ar, ac))
    return out


def _miss(board: DrillBoard) -> EvaluatedClick:
    return EvaluatedClick(
        is_correct=False, is_mine=False, opening_size=0, relative_quality=0.0,
        optimal_cell=board.optimal_cell or (0, 0),
        optimal_opening_size=board.optimal_opening_size,
    )


def _score_for(board: DrillBoard, r: int, c: int) -> int:
    """Compute the per-drill score for cell (r, c). Drives the feedback text."""
    if board.drill_type in (DRILL_TYPE_L5, DRILL_TYPE_L3, DRILL_TYPE_L7):
        return _flood_size(board, r, c)
    if board.drill_type == DRILL_TYPE_L4:
        return _chord_reveal_size(board, r, c)
    if board.drill_type == DRILL_TYPE_L6:
        return _flag_value(board, r, c)
    if board.drill_type == DRILL_TYPE_L2:
        return _l2_flag_then_chord_size(board, r, c)
    if board.drill_type == DRILL_TYPE_L1:
        if (r, c) in board.revealed:
            return _chord_reveal_size(board, r, c)
        return _flood_size(board, r, c)
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# L5 — Opening Recognition
# ─────────────────────────────────────────────────────────────────────────────

def _try_generate_l5(seed: int) -> Optional[DrillBoard]:
    """Build a small skill-based L5 board.

    The "correct" cell is the frontier cell with the lowest *mine pressure* —
    a number-based safety estimate — AND a meaningful opening size. We retry
    until the best cell is clearly safer than every runner-up, so the answer
    is derivable from the board state alone.
    """
    rng = random.Random(seed)
    board = DrillBoard(
        width=L5_WIDTH,
        height=L5_HEIGHT,
        num_mines=L5_MINES,
        seed=seed,
        drill_type=DRILL_TYPE_L5,
    )
    _place_random_mines(board, rng)
    _make_starter_reveal_l5(board, rng)

    # Need numbers before _mine_pressure can read them.
    board.numbers = _compute_numbers(board)

    # Score every frontier cell on (1 - pressure) × opening_size.
    # That composite rewards picks that are BOTH safe AND productive.
    scored: list[tuple[tuple[int, int], float, int, float]] = []
    for r in range(board.height):
        for c in range(board.width):
            if (r, c) in board.revealed or (r, c) in board.mines:
                continue
            if not _is_on_frontier(board, r, c):
                continue
            pressure = _mine_pressure(board, r, c)
            opening  = _flood_size(board, r, c)
            score    = (1.0 - pressure) * opening
            scored.append(((r, c), pressure, opening, score))

    if not scored:
        return None

    scored.sort(key=lambda x: -x[3])
    best_cell, best_pressure, best_opening, best_score = scored[0]

    if best_pressure > L5_BEST_MAX_PRESSURE:
        return None
    if best_opening < MIN_L5_OPENING:
        return None
    if best_score < L5_BEST_MIN_SCORE:
        return None

    # Runner-up must lag the best by a clear multiple so the answer is
    # unambiguous to a player who can read the numbers.
    if len(scored) >= 2:
        runner_score = scored[1][3]
        if runner_score <= 0:
            pass  # any positive lead over zero is fine
        elif best_score < runner_score * L5_BEST_MIN_LEAD:
            return None

    # "Correct" cells = anything tied with the best (same score within 1%).
    correct: set[tuple[int, int]] = set()
    for cell, _p, _o, score in scored:
        if score >= best_score * 0.99:
            correct.add(cell)

    board.correct_cells = correct
    board.optimal_cell = best_cell
    board.optimal_opening_size = best_opening
    return board


def _make_starter_reveal_l5(board: DrillBoard, rng: random.Random) -> None:
    """Smaller-board variant of the starter reveal — slightly denser target."""
    target = int(board.width * board.height * L5_STARTER_TARGET_REVEAL_FRACTION)
    safe_cells = _safe_cells(board)
    rng.shuffle(safe_cells)
    for cell in safe_cells:
        if cell in board.revealed:
            continue
        if _flood_size(board, *cell) < 3:
            continue
        _reveal_flood(board, *cell)
        if len(board.revealed) >= target:
            break
    if not board.revealed:
        # Pathological fallback — reveal something to give the player a frontier.
        for cell in safe_cells:
            _reveal_flood(board, *cell)
            if board.revealed:
                break


def _mine_pressure(board: DrillBoard, r: int, c: int) -> float:
    """Estimate the local probability that (r, c) is a mine.

    For each revealed-number neighbour N of the cell, we get a constraint:
    N is the count of mines among N's unrevealed neighbours. If N has U
    unrevealed neighbours and K of them are already flagged, then
    P(any single one is a mine) ≈ (N - K) / (U - K).

    We take the MAX over all such neighbours (the most restrictive
    constraint wins). If the cell has no revealed-number neighbours, we
    return 1.0 — meaning "we can't reason about this cell, treat as worst".
    That prevents stray non-frontier cells from looking artificially safe.
    """
    if (r, c) in board.revealed:
        return 1.0
    pressures: list[float] = []
    for nr, nc in _neighbors(r, c):
        if not (0 <= nr < board.height and 0 <= nc < board.width):
            continue
        if (nr, nc) not in board.revealed:
            continue
        n_value = board.numbers.get((nr, nc))
        if n_value is None:
            # Revealed "0" cell — its neighbours are all safe by definition,
            # but those cells would already have been flooded open. If we
            # somehow have a frontier cell next to a zero, it's safe.
            return 0.0
        unrev = 0
        known_mines = 0
        for ar, ac in _neighbors(nr, nc):
            if not (0 <= ar < board.height and 0 <= ac < board.width):
                continue
            if (ar, ac) in board.revealed:
                continue
            if (ar, ac) in board.flags:
                known_mines += 1
            else:
                unrev += 1
        remaining = n_value - known_mines
        if unrev <= 0:
            continue
        pressures.append(remaining / unrev)
    if not pressures:
        return 1.0
    return max(pressures)


def _is_on_frontier(board: DrillBoard, r: int, c: int) -> bool:
    """True if (r, c) is an unrevealed cell adjacent to a revealed cell."""
    if (r, c) in board.revealed:
        return False
    for nr, nc in _neighbors(r, c):
        if not (0 <= nr < board.height and 0 <= nc < board.width):
            continue
        if (nr, nc) in board.revealed:
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# L4 — Pure Efficiency
# ─────────────────────────────────────────────────────────────────────────────

def _try_generate_l4(seed: int) -> Optional[DrillBoard]:
    rng = random.Random(seed)
    board = _seed_board(seed, DRILL_TYPE_L4)
    _place_random_mines(board, rng)
    _make_starter_reveal(board, rng)

    # Place flags on adjacent-mine cells where the constraint is unambiguous:
    # a revealed number with k adjacent unrevealed cells equal to its mine
    # quota means all those neighbors are mines.
    _place_inferable_flags(board)

    # Find chord-ready revealed cells (number == flagged adjacent count and
    # at least one unrevealed-unflagged neighbor to reveal).
    sizes: dict[tuple[int, int], int] = {}
    for (r, c) in board.revealed:
        n = _count_adj_mines(board, r, c)
        if n == 0:
            continue
        flagged_adj = sum(
            1 for nr, nc in _neighbors(r, c)
            if (nr, nc) in board.flags
        )
        if flagged_adj != n:
            continue
        sz = _chord_reveal_size(board, r, c)
        if sz > 0:
            sizes[(r, c)] = sz

    if not sizes:
        return None
    max_size = max(sizes.values())
    if max_size < MIN_L4_CHORD_SIZE:
        return None

    threshold = max(1, int(max_size * CORRECT_THRESHOLD))
    correct = {cell for cell, sz in sizes.items() if sz >= threshold}
    optimal = max(sizes, key=sizes.get)

    board.correct_cells = correct
    board.optimal_cell = optimal
    board.optimal_opening_size = max_size
    board.numbers = _compute_numbers(board)
    return board


def _chord_reveal_size(board: DrillBoard, r: int, c: int) -> int:
    """Non-mutating: how many cells would be revealed by chording (r, c)?

    Chord rule: only fires when adjacent_flags == number. Returns 0 if the
    cell isn't chord-ready, or for any cell that isn't a revealed number.
    """
    if (r, c) not in board.revealed:
        return 0
    n = _count_adj_mines(board, r, c)
    if n == 0:
        return 0
    flagged = sum(1 for nr, nc in _neighbors(r, c) if (nr, nc) in board.flags)
    if flagged != n:
        return 0

    revealed_after = set(board.revealed)
    new_cells = 0
    for nr, nc in _neighbors(r, c):
        if not (0 <= nr < board.height and 0 <= nc < board.width):
            continue
        if (nr, nc) in board.flags or (nr, nc) in revealed_after:
            continue
        if (nr, nc) in board.mines:
            # Player would have detonated a wrongly-flagged-around chord, but
            # in our generator chord-ready cells always have correct flags,
            # so this branch shouldn't fire. Be defensive: don't count it.
            continue
        # Simulate the flood-fill from this newly-revealed neighbor.
        sz = _flood_size_into(board, nr, nc, revealed_after)
        new_cells += sz
    return new_cells


def _flood_size_into(
    board: DrillBoard,
    r: int,
    c: int,
    already_revealed: set[tuple[int, int]],
) -> int:
    """Flood from (r,c), counting newly-revealed cells, mutating already_revealed.

    Used by _chord_reveal_size so a single chord across multiple neighbors
    doesn't double-count cells that flood-fill into the same zero region.
    """
    if (r, c) in already_revealed or (r, c) in board.mines or (r, c) in board.flags:
        return 0
    if not (0 <= r < board.height and 0 <= c < board.width):
        return 0
    q: deque[tuple[int, int]] = deque([(r, c)])
    count = 0
    while q:
        cr, cc = q.popleft()
        if not (0 <= cr < board.height and 0 <= cc < board.width):
            continue
        if (cr, cc) in already_revealed:
            continue
        if (cr, cc) in board.mines or (cr, cc) in board.flags:
            continue
        already_revealed.add((cr, cc))
        count += 1
        if _count_adj_mines(board, cr, cc) == 0:
            for nr, nc in _neighbors(cr, cc):
                q.append((nr, nc))
    return count


# ─────────────────────────────────────────────────────────────────────────────
# L6 — Flag Value
# ─────────────────────────────────────────────────────────────────────────────

def _try_generate_l6(seed: int) -> Optional[DrillBoard]:
    rng = random.Random(seed)
    board = _seed_board(seed, DRILL_TYPE_L6)
    _place_random_mines(board, rng)
    _make_starter_reveal(board, rng)

    # Find provably-mine cells: any unrevealed neighbor of a revealed number
    # where the number's unrevealed-unflagged count equals (number - flags).
    # We DON'T place those flags — the drill is to do so. We do place flags
    # where the lesson would be uninteresting (cells whose flag wouldn't open
    # anything) so the candidate set is meaningful.
    provably_mine = _find_provably_mine_cells(board)
    if not provably_mine:
        return None

    sizes: dict[tuple[int, int], int] = {}
    for cell in provably_mine:
        v = _flag_value(board, *cell)
        if v > 0:
            sizes[cell] = v

    if not sizes:
        return None
    max_v = max(sizes.values())
    if max_v < MIN_L6_FLAG_VALUE:
        return None

    threshold = max(1, int(max_v * CORRECT_THRESHOLD))
    correct = {cell for cell, v in sizes.items() if v >= threshold}
    optimal = max(sizes, key=sizes.get)

    board.correct_cells = correct
    board.optimal_cell = optimal
    board.optimal_opening_size = max_v
    board.numbers = _compute_numbers(board)
    return board


def _find_provably_mine_cells(board: DrillBoard) -> set[tuple[int, int]]:
    """Cells that simple constraint propagation proves are mines.

    Rule: revealed cell with number N, F flagged neighbors, U unrevealed
    unflagged neighbors. If U == N - F, then every cell in U is a mine.
    """
    proven: set[tuple[int, int]] = set()
    for (r, c) in board.revealed:
        n = _count_adj_mines(board, r, c)
        if n == 0:
            continue
        flagged = []
        unrev_unflagged = []
        for nr, nc in _neighbors(r, c):
            if not (0 <= nr < board.height and 0 <= nc < board.width):
                continue
            if (nr, nc) in board.flags:
                flagged.append((nr, nc))
            elif (nr, nc) not in board.revealed:
                unrev_unflagged.append((nr, nc))
        if len(unrev_unflagged) == n - len(flagged) and unrev_unflagged:
            proven.update(unrev_unflagged)
    return proven


def _flag_value(board: DrillBoard, r: int, c: int) -> int:
    """If we flagged (r,c), how many new chord opportunities would open up?

    We score the flag by:  sum over neighbouring revealed-number cells X of
    the chord-reveal size X would have AFTER placing this flag (only if X
    wasn't already chord-ready and becomes chord-ready as a result).

    This rewards flags that unlock the BIGGEST new chord.
    """
    if (r, c) not in board.mines:
        return 0
    if (r, c) in board.flags or (r, c) in board.revealed:
        return 0

    # Hypothetical state with the flag placed.
    new_flags = set(board.flags)
    new_flags.add((r, c))

    total = 0
    for nr, nc in _neighbors(r, c):
        if (nr, nc) not in board.revealed:
            continue
        num = _count_adj_mines(board, nr, nc)
        if num == 0:
            continue
        flagged_before = sum(
            1 for ar, ac in _neighbors(nr, nc) if (ar, ac) in board.flags
        )
        flagged_after = flagged_before + (
            1 if (r, c) in {(ar, ac) for ar, ac in _neighbors(nr, nc)} else 0
        )
        # We only credit chords newly enabled by THIS flag.
        if flagged_before == num:
            continue
        if flagged_after != num:
            continue

        # Compute the chord reveal as if (r,c) were flagged.
        synthetic = _board_with_flags(board, new_flags)
        total += _chord_reveal_size(synthetic, nr, nc)

    return total


def _board_with_flags(base: DrillBoard, flags: set[tuple[int, int]]) -> DrillBoard:
    """Cheap shallow copy with the flags set replaced. Mines/revealed shared."""
    return DrillBoard(
        width=base.width,
        height=base.height,
        num_mines=base.num_mines,
        seed=base.seed,
        drill_type=base.drill_type,
        mines=base.mines,
        revealed=base.revealed,
        flags=flags,
        numbers=base.numbers,
    )


# ─────────────────────────────────────────────────────────────────────────────
# L1 — Cut Waste (chord-or-click)
# ─────────────────────────────────────────────────────────────────────────────

def _try_generate_l1(seed: int) -> Optional[DrillBoard]:
    """Both chord-ready numbers and provably-safe clicks are candidates.

    The lesson: before clicking cell-by-cell, check whether a chord (or a
    bigger click) does the same work in one action. A valid board needs a
    meaningful candidate of EACH kind so the comparison is a real decision.
    """
    rng = random.Random(seed)
    board = _seed_board(seed, DRILL_TYPE_L1)
    _place_random_mines(board, rng)
    _make_starter_reveal(board, rng)
    _place_inferable_flags(board)
    board.numbers = _compute_numbers(board)

    # Chord candidates — chord-ready revealed numbers.
    chord_sizes: dict[tuple[int, int], int] = {}
    for (r, c) in board.revealed:
        sz = _chord_reveal_size(board, r, c)
        if sz > 0:
            chord_sizes[(r, c)] = sz

    # Click candidates — tier-1 provably-safe unrevealed cells.
    safe, _mines = _tier1_deduce(board)
    click_sizes: dict[tuple[int, int], int] = {}
    for cell in safe:
        sz = _flood_size(board, *cell)
        if sz > 0:
            click_sizes[cell] = sz

    if not chord_sizes or not click_sizes:
        return None
    if max(chord_sizes.values()) < MIN_L1_EACH_KIND:
        return None
    if max(click_sizes.values()) < MIN_L1_EACH_KIND:
        return None

    sizes = {**chord_sizes, **click_sizes}
    max_size = max(sizes.values())
    if max_size < MIN_L1_BEST:
        return None

    threshold = max(1, int(max_size * CORRECT_THRESHOLD))
    board.correct_cells = {cell for cell, sz in sizes.items() if sz >= threshold}
    board.optimal_cell = max(sizes, key=sizes.get)
    board.optimal_opening_size = max_size
    return board


# ─────────────────────────────────────────────────────────────────────────────
# L2 — Effective Chording (flag-then-chord)
# ─────────────────────────────────────────────────────────────────────────────

def _try_generate_l2(seed: int) -> Optional[DrillBoard]:
    """No flags are pre-placed. Candidates are revealed numbers whose missing
    flags are ALL provable mines — so flag-then-chord is safe — scored by the
    chord reveal that placing those flags would enable.
    """
    rng = random.Random(seed)
    board = _seed_board(seed, DRILL_TYPE_L2)
    _place_random_mines(board, rng)
    _make_starter_reveal(board, rng)
    board.numbers = _compute_numbers(board)

    sizes: dict[tuple[int, int], int] = {}
    for (r, c) in board.revealed:
        sz = _l2_flag_then_chord_size(board, r, c)
        if sz > 0:
            sizes[(r, c)] = sz

    if not sizes:
        return None
    max_size = max(sizes.values())
    if max_size < MIN_L2_CHORD_SIZE:
        return None

    threshold = max(1, int(max_size * CORRECT_THRESHOLD))
    board.correct_cells = {cell for cell, sz in sizes.items() if sz >= threshold}
    board.optimal_cell = max(sizes, key=sizes.get)
    board.optimal_opening_size = max_size
    return board


def _l2_needed_flags(board: DrillBoard, r: int, c: int) -> Optional[set[tuple[int, int]]]:
    """The provable mines a chord on (r, c) still needs flagged, or None if
    flag-then-chord on (r, c) isn't provably safe / isn't a real opportunity.

    Conditions:
      - (r, c) is a revealed number N with F adjacent flags, F < N
      - the missing (N - F) flags are all tier-1 provable mines
      - at most MAX_L2_FLAGS_NEEDED flags are missing
      - after flagging, the chord actually reveals something
    """
    if (r, c) not in board.revealed:
        return None
    n = _count_adj_mines(board, r, c)
    if n == 0:
        return None
    flagged = sum(1 for nr, nc in _neighbors(r, c) if (nr, nc) in board.flags)
    missing = n - flagged
    if missing <= 0 or missing > MAX_L2_FLAGS_NEEDED:
        return None

    proven = _find_provably_mine_cells(board)
    needed: set[tuple[int, int]] = set()
    for nr, nc in _neighbors(r, c):
        if not (0 <= nr < board.height and 0 <= nc < board.width):
            continue
        if (nr, nc) in board.flags or (nr, nc) in board.revealed:
            continue
        if (nr, nc) in board.mines:
            if (nr, nc) not in proven:
                return None      # an adjacent mine we can't prove — unsafe chord
            needed.add((nr, nc))
    if len(needed) != missing:
        return None              # counts disagree — over/under-flagged, skip
    return needed


def _l2_board_with_needed_flags(board: DrillBoard, r: int, c: int) -> Optional[DrillBoard]:
    needed = _l2_needed_flags(board, r, c)
    if needed is None:
        return None
    return _board_with_flags(board, set(board.flags) | needed)


def _l2_flag_then_chord_size(board: DrillBoard, r: int, c: int) -> int:
    """Cells revealed by chording (r, c) after placing its provable flags."""
    synthetic = _l2_board_with_needed_flags(board, r, c)
    if synthetic is None:
        return 0
    return _chord_reveal_size(synthetic, r, c)


# ─────────────────────────────────────────────────────────────────────────────
# L3 — Strategic No-Flag
# ─────────────────────────────────────────────────────────────────────────────

def _try_generate_l3(seed: int) -> Optional[DrillBoard]:
    """Small board, zero flags. Correct cells are those tier-1 deduction
    proves safe from the raw numbers. The frontier must be much larger than
    the safe set so spotting the safe cell is a real read.
    """
    rng = random.Random(seed)
    board = DrillBoard(
        width=SMALL_WIDTH,
        height=SMALL_HEIGHT,
        num_mines=L3_MINES,
        seed=seed,
        drill_type=DRILL_TYPE_L3,
    )
    _place_random_mines(board, rng)
    _make_starter_reveal_l5(board, rng)   # same denser small-board reveal
    board.numbers = _compute_numbers(board)

    safe, _mines = _tier1_deduce(board)
    sizes = {cell: _flood_size(board, *cell) for cell in safe}
    sizes = {cell: sz for cell, sz in sizes.items() if sz > 0}
    if not sizes:
        return None
    max_size = max(sizes.values())
    if max_size < MIN_L3_OPTIMAL:
        return None

    frontier = sum(
        1 for r in range(board.height) for c in range(board.width)
        if _is_on_frontier(board, r, c)
    )
    if frontier < len(sizes) * L3_MIN_FRONTIER_RATIO:
        return None

    # Any provably-safe cell is a correct NF read; the biggest flood is optimal.
    board.correct_cells = set(sizes.keys())
    board.optimal_cell = max(sizes, key=sizes.get)
    board.optimal_opening_size = max_size
    return board


# ─────────────────────────────────────────────────────────────────────────────
# L7 — Fishing & Decision Hierarchy
# ─────────────────────────────────────────────────────────────────────────────

def _try_generate_l7(seed: int) -> Optional[DrillBoard]:
    """Small board where NO tier-1 safe cell exists but subset (tier-2)
    deduction proves at least one cell safe. That's the fishing lesson:
    when the easy moves run out, chain constraints instead of guessing.

    Provable mines ARE pre-flagged (tier-1 closure) so the player's
    attention goes to the deduction, not to flag bookkeeping.
    """
    rng = random.Random(seed)
    board = DrillBoard(
        width=SMALL_WIDTH,
        height=SMALL_HEIGHT,
        num_mines=L7_MINES,
        seed=seed,
        drill_type=DRILL_TYPE_L7,
    )
    _place_random_mines(board, rng)

    target = int(board.width * board.height * L7_STARTER_TARGET_REVEAL_FRACTION)
    safe_cells = _safe_cells(board)
    rng.shuffle(safe_cells)
    for cell in safe_cells:
        if cell in board.revealed:
            continue
        if _flood_size(board, *cell) < 3:
            continue
        _reveal_flood(board, *cell)
        if len(board.revealed) >= target:
            break
    if not board.revealed:
        return None

    # Drive the board to a "stuck" state: play out every trivial move
    # (flag provable mines, reveal provable safes) until tier-1 deduction
    # yields nothing. That's exactly the moment fishing matters.
    for _ in range(50):
        _place_inferable_flags(board)
        tier1_safe, _tier1_mines = _tier1_deduce(board)
        tier1_safe = {s for s in tier1_safe if s not in board.revealed}
        if not tier1_safe:
            break
        for cell in tier1_safe:
            _reveal_flood(board, *cell)
    else:
        return None
    board.numbers = _compute_numbers(board)

    solver_safe = _solver_safe_cells(board)
    fishing_safe = {cell for cell in solver_safe if cell not in board.revealed}
    if len(fishing_safe) < MIN_L7_SAFE:
        return None

    sizes = {cell: max(1, _flood_size(board, *cell)) for cell in fishing_safe}
    board.correct_cells = set(sizes.keys())
    board.optimal_cell = max(sizes, key=sizes.get)
    board.optimal_opening_size = max(sizes.values())
    return board


def _solver_safe_cells(board: DrillBoard) -> set[tuple[int, int]]:
    """Run phase2_analyzer's ConstraintSolver (tier-1 + tier-2 subset
    deduction) and return provably-safe unrevealed cells as (r, c).

    Imported lazily so the generator stays standalone when phase2_analyzer
    isn't on the path (e.g. isolated tooling).
    """
    from phase2_analyzer.solver import ConstraintSolver
    from phase2_analyzer.types import BoardSnapshot, CellState

    cells: list[list] = []
    mine_layout: list[list[bool]] = []
    for r in range(board.height):
        row_cells = []
        row_mines = []
        for c in range(board.width):
            row_mines.append((r, c) in board.mines)
            if (r, c) in board.flags:
                row_cells.append(CellState(kind="flagged"))
            elif (r, c) in board.revealed:
                row_cells.append(CellState(
                    kind="revealed",
                    adjacent_mines=_count_adj_mines(board, r, c),
                ))
            else:
                row_cells.append(CellState(kind="unrevealed"))
        cells.append(row_cells)
        mine_layout.append(row_mines)

    snapshot = BoardSnapshot(
        width=board.width,
        height=board.height,
        mine_layout=mine_layout,
        cells=cells,
    )
    result = ConstraintSolver().analyze(snapshot)
    # Solver speaks (x, y); we speak (r, c).
    return {(y, x) for (x, y) in result.provably_safe}


def _tier1_deduce(board: DrillBoard) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
    """Iterated trivial deduction to a fixpoint.

    For each revealed number N: count flags + already-proven mines among its
    neighbours as known. Then:
      - if remaining quota == remaining unknown neighbours → all are mines
      - if remaining quota == 0                            → all are safe

    Returns (safe, mines) — unrevealed, unflagged cells only.
    """
    proven_mines: set[tuple[int, int]] = set()
    proven_safe: set[tuple[int, int]] = set()
    changed = True
    while changed:
        changed = False
        for (r, c) in board.revealed:
            n = _count_adj_mines(board, r, c)
            if n == 0:
                continue
            known_mines = 0
            unknown: list[tuple[int, int]] = []
            for nr, nc in _neighbors(r, c):
                if not (0 <= nr < board.height and 0 <= nc < board.width):
                    continue
                if (nr, nc) in board.revealed:
                    continue
                if (nr, nc) in board.flags or (nr, nc) in proven_mines:
                    known_mines += 1
                elif (nr, nc) in proven_safe:
                    continue
                else:
                    unknown.append((nr, nc))
            remaining = n - known_mines
            if not unknown:
                continue
            if remaining == 0:
                proven_safe.update(unknown)
                changed = True
            elif remaining == len(unknown):
                proven_mines.update(unknown)
                changed = True
    return proven_safe, proven_mines


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _seed_board(seed: int, drill_type: str) -> DrillBoard:
    return DrillBoard(
        width=EXPERT_WIDTH,
        height=EXPERT_HEIGHT,
        num_mines=EXPERT_MINES,
        seed=seed,
        drill_type=drill_type,
    )


def _place_random_mines(board: DrillBoard, rng: random.Random) -> None:
    cells = [(r, c) for r in range(board.height) for c in range(board.width)]
    rng.shuffle(cells)
    board.mines = set(cells[:board.num_mines])


def _make_starter_reveal(board: DrillBoard, rng: random.Random) -> None:
    """Reveal one or two safe openings to seed the partial state."""
    target = int(board.width * board.height * STARTER_TARGET_REVEAL_FRACTION)
    safe_cells = _safe_cells(board)
    rng.shuffle(safe_cells)

    revealed_count = 0
    for cell in safe_cells:
        if cell in board.revealed:
            continue
        sz = _flood_size(board, *cell)
        if sz < 4:
            continue
        _reveal_flood(board, *cell)
        revealed_count = len(board.revealed)
        if revealed_count >= target:
            break

    if revealed_count < target:
        for cell in safe_cells:
            if cell in board.revealed:
                continue
            _reveal_flood(board, *cell)
            if len(board.revealed) >= target:
                break


def _place_inferable_flags(board: DrillBoard) -> None:
    """Auto-place flags wherever a revealed number unambiguously identifies
    its mines.

    Re-runs until no new flags can be placed (handles cascades — a flag
    that's placed may complete the constraint on a neighbouring number,
    which then becomes chord-ready instead of contributing more flags).
    """
    changed = True
    while changed:
        changed = False
        for (r, c) in board.revealed:
            n = _count_adj_mines(board, r, c)
            if n == 0:
                continue
            flagged = []
            unrev_unflagged = []
            for nr, nc in _neighbors(r, c):
                if not (0 <= nr < board.height and 0 <= nc < board.width):
                    continue
                if (nr, nc) in board.flags:
                    flagged.append((nr, nc))
                elif (nr, nc) not in board.revealed:
                    unrev_unflagged.append((nr, nc))
            if (
                len(unrev_unflagged) == n - len(flagged)
                and unrev_unflagged
            ):
                # All remaining unrevealed neighbours are mines.
                for cell in unrev_unflagged:
                    if cell not in board.flags:
                        board.flags.add(cell)
                        changed = True


def _reveal_flood(board: DrillBoard, r: int, c: int) -> int:
    if (r, c) in board.mines:
        return 0
    q: deque[tuple[int, int]] = deque([(r, c)])
    count = 0
    while q:
        cr, cc = q.popleft()
        if not (0 <= cr < board.height and 0 <= cc < board.width):
            continue
        if (cr, cc) in board.revealed or (cr, cc) in board.mines:
            continue
        board.revealed.add((cr, cc))
        count += 1
        if _count_adj_mines(board, cr, cc) == 0:
            for nr, nc in _neighbors(cr, cc):
                q.append((nr, nc))
    return count


def _flood_size(board: DrillBoard, r: int, c: int) -> int:
    """Non-mutating: how many cells *would* be revealed if we clicked (r, c)?"""
    if (r, c) in board.mines or (r, c) in board.revealed or (r, c) in board.flags:
        return 0
    if not (0 <= r < board.height and 0 <= c < board.width):
        return 0
    visited: set[tuple[int, int]] = set()
    q: deque[tuple[int, int]] = deque([(r, c)])
    count = 0
    while q:
        cr, cc = q.popleft()
        if (cr, cc) in visited or (cr, cc) in board.revealed:
            continue
        if not (0 <= cr < board.height and 0 <= cc < board.width):
            continue
        if (cr, cc) in board.mines or (cr, cc) in board.flags:
            continue
        visited.add((cr, cc))
        count += 1
        if _count_adj_mines(board, cr, cc) == 0:
            for nr, nc in _neighbors(cr, cc):
                if (nr, nc) not in visited:
                    q.append((nr, nc))
    return count


def _neighbors(r: int, c: int) -> Iterable[tuple[int, int]]:
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            yield (r + dr, c + dc)


def _count_adj_mines(board: DrillBoard, r: int, c: int) -> int:
    return sum(
        1 for nr, nc in _neighbors(r, c)
        if 0 <= nr < board.height and 0 <= nc < board.width
        and (nr, nc) in board.mines
    )


def _safe_cells(board: DrillBoard) -> list[tuple[int, int]]:
    return [
        (r, c) for r in range(board.height) for c in range(board.width)
        if (r, c) not in board.mines
    ]


def _compute_numbers(board: DrillBoard) -> dict[tuple[int, int], int]:
    out: dict[tuple[int, int], int] = {}
    for (r, c) in board.revealed:
        n = _count_adj_mines(board, r, c)
        if n > 0:
            out[(r, c)] = n
    return out


# ─────────────────────────────────────────────────────────────────────────────
# CLI smoke test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    for drill_type in ALL_DRILL_TYPES:
        print(f"\n── {drill_type} ──")
        boards = generate_drill_set(base_seed=42, n=5, drill_type=drill_type)
        for i, board in enumerate(boards, 1):
            print(
                f"  Board {i}: revealed={len(board.revealed):>3}  "
                f"flags={len(board.flags):>2}  "
                f"correct={len(board.correct_cells):>3}  "
                f"optimal=({board.optimal_cell[0]},{board.optimal_cell[1]})  "
                f"score={board.optimal_opening_size}"
            )
    print("\nOK")
