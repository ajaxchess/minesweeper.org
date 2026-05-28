"""
phase7_drills.generator — procedural board generation for drills.

Currently implements the L5 Opening Recognition drill format:

  Pick-the-best-cell: show a partially-revealed expert board, ask the player
  which unrevealed cell they'd click next. "Correct" cells are the
  unrevealed cells that are NOT mines AND would reveal an opening within
  80% of the maximum next-opening across all safe unrevealed cells.

Design constraints:
  - All randomness must be derivable from a seed so we can replay drill
    boards (server-side validation, debugging, replays of a drill).
  - Mine layouts are kept server-side. Only the "visible state" (revealed
    cells + numbers) is sent to the client.
  - The board must always have at least one large opening available (≥ 12
    cells) — otherwise the drill teaches the wrong reflex (any random click
    is fine).

Public API:
  generate_l5_opening_board(seed) -> DrillBoard
  serialize_visible(board)        -> dict (safe to send to client)
  evaluate_click(board, r, c)     -> EvaluatedClick
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

# Minimum opening size we want available on a drill board. If the max opening
# is below this, we regenerate. A truly tight board doesn't teach the lesson.
MIN_TARGET_OPENING = 12

# A cell counts as "correct" if its next-opening is within this fraction of
# the maximum next-opening across all safe unrevealed cells.
CORRECT_THRESHOLD = 0.80

# How many cells to reveal in the "starter" — the partial reveal the player
# sees when the drill begins.
STARTER_TARGET_REVEAL_FRACTION = 0.25   # ~120 cells out of 480 on expert


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DrillBoard:
    """A generated drill board.

    Attributes:
      width, height       — board dimensions
      num_mines           — total mine count
      seed                — RNG seed (lets us replay the board if needed)
      mines               — set of (r, c) mine positions (SECRET)
      revealed            — set of (r, c) revealed cells (visible to player)
      numbers             — (r, c) -> adjacent mine count, only for revealed
                            cells with adjacent_mines > 0
      correct_cells       — set of (r, c) cells that are "correct" picks
                            (safe + opening ≥ 80% of max)
      optimal_cell        — single (r, c) with the largest opening
      optimal_opening_size — size of the best opening
    """
    width: int
    height: int
    num_mines: int
    seed: int

    mines: set[tuple[int, int]] = field(default_factory=set)
    revealed: set[tuple[int, int]] = field(default_factory=set)
    numbers: dict[tuple[int, int], int] = field(default_factory=dict)

    correct_cells: set[tuple[int, int]] = field(default_factory=set)
    optimal_cell: Optional[tuple[int, int]] = None
    optimal_opening_size: int = 0


@dataclass
class EvaluatedClick:
    """Result of evaluating a player's click on a drill board."""
    is_correct: bool
    is_mine: bool
    opening_size: int        # how many cells *would* have been revealed
    relative_quality: float  # 0..1, ratio vs the optimal opening size
    optimal_cell: tuple[int, int]
    optimal_opening_size: int


# ─────────────────────────────────────────────────────────────────────────────
# Public generators
# ─────────────────────────────────────────────────────────────────────────────

def generate_l5_opening_board(seed: int) -> DrillBoard:
    """
    Generate one L5 Opening Recognition drill board.

    The RNG is seeded so the same seed always produces the same board. We
    retry generation if the resulting board has no large opening available;
    we cap retries at 20 (collisions are very rare with default constants).
    """
    rng = random.Random(seed)
    for attempt in range(20):
        attempt_seed = rng.randrange(1, 1_000_000_000)
        board = _try_generate(attempt_seed)
        if board is not None:
            return board
    raise RuntimeError(
        f"Could not generate a valid drill board after 20 attempts (seed={seed})"
    )


def generate_drill_set(base_seed: int, n: int = 10) -> list[DrillBoard]:
    """Generate n boards with deterministic, distinct seeds derived from base_seed."""
    rng = random.Random(base_seed)
    return [generate_l5_opening_board(rng.randrange(1, 1_000_000_000)) for _ in range(n)]


def serialize_visible(board: DrillBoard) -> dict:
    """Return the JSON-safe visible state for the client (mines NOT included)."""
    return {
        "width": board.width,
        "height": board.height,
        "num_mines": board.num_mines,
        "revealed": [[r, c] for (r, c) in sorted(board.revealed)],
        "numbers": [
            [r, c, n] for (r, c), n in sorted(board.numbers.items())
        ],
    }


def serialize_solution(board: DrillBoard) -> dict:
    """Server-side state we persist so we can validate clicks later."""
    return {
        "width": board.width,
        "height": board.height,
        "num_mines": board.num_mines,
        "seed": board.seed,
        "mines": [[r, c] for (r, c) in sorted(board.mines)],
        "revealed": [[r, c] for (r, c) in sorted(board.revealed)],
        "correct_cells": [[r, c] for (r, c) in sorted(board.correct_cells)],
        "optimal_cell": list(board.optimal_cell) if board.optimal_cell else None,
        "optimal_opening_size": board.optimal_opening_size,
    }


def deserialize_solution(d: dict) -> DrillBoard:
    """Reverse of serialize_solution — rehydrate a board from stored JSON."""
    board = DrillBoard(
        width=d["width"],
        height=d["height"],
        num_mines=d["num_mines"],
        seed=d["seed"],
    )
    board.mines = {tuple(p) for p in d["mines"]}
    board.revealed = {tuple(p) for p in d["revealed"]}
    board.correct_cells = {tuple(p) for p in d["correct_cells"]}
    board.optimal_cell = tuple(d["optimal_cell"]) if d.get("optimal_cell") else None
    board.optimal_opening_size = int(d.get("optimal_opening_size", 0))
    # Recompute numbers from the mine layout — saves storage
    board.numbers = _compute_numbers(board)
    return board


def evaluate_click(board: DrillBoard, r: int, c: int) -> EvaluatedClick:
    """
    Score the player's click. Always returns a verdict even for invalid
    coordinates (which are treated as wrong, not error).
    """
    in_bounds = 0 <= r < board.height and 0 <= c < board.width
    already_revealed = (r, c) in board.revealed
    is_mine = (r, c) in board.mines

    if not in_bounds or already_revealed:
        return EvaluatedClick(
            is_correct=False,
            is_mine=False,
            opening_size=0,
            relative_quality=0.0,
            optimal_cell=board.optimal_cell or (0, 0),
            optimal_opening_size=board.optimal_opening_size,
        )

    if is_mine:
        return EvaluatedClick(
            is_correct=False,
            is_mine=True,
            opening_size=0,
            relative_quality=0.0,
            optimal_cell=board.optimal_cell or (0, 0),
            optimal_opening_size=board.optimal_opening_size,
        )

    opening_size = _flood_size(board, r, c)
    relative = (
        opening_size / board.optimal_opening_size
        if board.optimal_opening_size > 0
        else 0.0
    )

    return EvaluatedClick(
        is_correct=(r, c) in board.correct_cells,
        is_mine=False,
        opening_size=opening_size,
        relative_quality=round(relative, 3),
        optimal_cell=board.optimal_cell or (0, 0),
        optimal_opening_size=board.optimal_opening_size,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Internal — board generation
# ─────────────────────────────────────────────────────────────────────────────

def _try_generate(seed: int) -> Optional[DrillBoard]:
    rng = random.Random(seed)
    board = DrillBoard(
        width=EXPERT_WIDTH,
        height=EXPERT_HEIGHT,
        num_mines=EXPERT_MINES,
        seed=seed,
    )

    # 1) Place mines randomly
    cells = [(r, c) for r in range(board.height) for c in range(board.width)]
    rng.shuffle(cells)
    board.mines = set(cells[:board.num_mines])

    # 2) Compute the "starter reveal" — a few openings the player sees
    _make_starter_reveal(board, rng)

    # 3) Identify the best next opening among safe unrevealed cells
    best_cell, best_size = _find_best_next_opening(board)
    if best_cell is None or best_size < MIN_TARGET_OPENING:
        return None  # caller will retry

    # 4) Collect all "correct" cells (within CORRECT_THRESHOLD of the best)
    threshold = max(1, int(best_size * CORRECT_THRESHOLD))
    correct: set[tuple[int, int]] = set()
    for r in range(board.height):
        for c in range(board.width):
            if (r, c) in board.revealed or (r, c) in board.mines:
                continue
            sz = _flood_size(board, r, c)
            if sz >= threshold:
                correct.add((r, c))

    board.correct_cells = correct
    board.optimal_cell = best_cell
    board.optimal_opening_size = best_size

    # 5) Precompute numbers for revealed cells (cheap; client uses these)
    board.numbers = _compute_numbers(board)

    return board


def _make_starter_reveal(board: DrillBoard, rng: random.Random) -> None:
    """
    Reveal one or two safe openings to seed the partial state.

    We pick a random safe cell, flood-reveal it, then if too few cells are
    revealed, pick another safe cell elsewhere on the board and reveal that.
    """
    target = int(board.width * board.height * STARTER_TARGET_REVEAL_FRACTION)
    safe_cells = _safe_cells(board)
    rng.shuffle(safe_cells)

    revealed_count = 0
    for cell in safe_cells:
        if cell in board.revealed:
            continue
        # Only pick a "real" opening — at least 4 cells — for the starter, so
        # the player can see something. Skip cells whose opening is just 1.
        sz = _flood_size(board, *cell)
        if sz < 4:
            continue
        _reveal_flood(board, *cell)
        revealed_count = len(board.revealed)
        if revealed_count >= target:
            break

    # Fallback: if no large opening was reachable from any random cell, take
    # the smallest 1-cell reveals until we hit the target (rare)
    if revealed_count < target:
        for cell in safe_cells:
            if cell in board.revealed:
                continue
            _reveal_flood(board, *cell)
            if len(board.revealed) >= target:
                break


def _reveal_flood(board: DrillBoard, r: int, c: int) -> int:
    """Mutating BFS flood-fill: reveal all connected 0-region cells.

    Returns count of newly revealed cells.
    """
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
    """Non-mutating: how many cells *would* be revealed if we clicked (r, c)?

    Returns 0 if (r, c) is a mine or already revealed.
    """
    if (r, c) in board.mines or (r, c) in board.revealed:
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
        if (cr, cc) in board.mines:
            continue
        visited.add((cr, cc))
        count += 1
        if _count_adj_mines(board, cr, cc) == 0:
            for nr, nc in _neighbors(cr, cc):
                if (nr, nc) not in visited:
                    q.append((nr, nc))
    return count


def _find_best_next_opening(board: DrillBoard) -> tuple[Optional[tuple[int, int]], int]:
    """Among safe unrevealed cells, find the one with the largest opening."""
    best_cell: Optional[tuple[int, int]] = None
    best_size = 0
    for r in range(board.height):
        for c in range(board.width):
            if (r, c) in board.revealed or (r, c) in board.mines:
                continue
            sz = _flood_size(board, r, c)
            if sz > best_size:
                best_size = sz
                best_cell = (r, c)
    return best_cell, best_size


# ─────────────────────────────────────────────────────────────────────────────
# Internal — board math
# ─────────────────────────────────────────────────────────────────────────────

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
    """For each revealed cell with adjacent mines > 0, store the count.

    Zero-cells are omitted; the client renders revealed cells without a number
    as empty squares.
    """
    out: dict[tuple[int, int], int] = {}
    for (r, c) in board.revealed:
        n = _count_adj_mines(board, r, c)
        if n > 0:
            out[(r, c)] = n
    return out


# ─────────────────────────────────────────────────────────────────────────────
# CLI smoke test — `python3 phase7_drills/generator.py` to sanity-check
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Generating 5 drill boards…\n")
    for i, board in enumerate(generate_drill_set(base_seed=42, n=5), 1):
        print(
            f"Board {i}: revealed={len(board.revealed):>3}/{board.width*board.height}  "
            f"correct={len(board.correct_cells):>3}  "
            f"optimal=({board.optimal_cell[0]},{board.optimal_cell[1]}) "
            f"opens {board.optimal_opening_size} cells"
        )
    print("\nOK")
