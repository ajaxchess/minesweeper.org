"""
tametsi_generator.py — Board generator and constraint solver for Tametsi (F79-A).

Generates no-guess-solvable boards via reject-and-retry:
  1. Place mines randomly, (0,0) guaranteed safe.
  2. Compute row/col mine counts.
  3. Run constraint solver (adjacency + row/col rules) from (0,0).
  4. Accept if fully solved; otherwise retry.
  5. Compute 3BV and board hash on acceptance.
"""

import hashlib
import json
import random
from collections import deque
from dataclasses import dataclass
from typing import Optional


# ── Difficulty presets (rows, cols, mines) ─────────────────────────────────────

LEVELS: dict[str, tuple[int, int, int]] = {
    "beginner":     (9,  9,  10),
    "intermediate": (16, 16, 40),
    "expert":       (16, 30, 99),
}

MAX_ATTEMPTS = 10_000

# ── Data class ─────────────────────────────────────────────────────────────────

@dataclass
class TametsiBoard:
    rows: int
    cols: int
    mines: frozenset          # frozenset of (row, col) tuples
    row_counts: list[int]
    col_counts: list[int]
    bbbv: int
    board_hash: str           # full SHA-256 hex of canonical mine layout
    board_data: dict          # JSON-serialisable; matches DB board_data column schema


# ── Internal helpers ───────────────────────────────────────────────────────────

def _neighbors(r: int, c: int, rows: int, cols: int):
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                yield nr, nc


def _adjacency_count(r: int, c: int, mine_set: frozenset, rows: int, cols: int) -> int:
    return sum(1 for nr, nc in _neighbors(r, c, rows, cols) if (nr, nc) in mine_set)


def _compute_3bv(mine_set: frozenset, rows: int, cols: int) -> int:
    """Standard minesweeper 3BV: opening regions + isolated numbered cells."""
    counts = {
        (r, c): _adjacency_count(r, c, mine_set, rows, cols)
        for r in range(rows)
        for c in range(cols)
        if (r, c) not in mine_set
    }
    visited: set = set()
    openings = 0

    for r in range(rows):
        for c in range(cols):
            if (r, c) in mine_set or (r, c) in visited or counts[(r, c)] != 0:
                continue
            openings += 1
            queue: deque = deque([(r, c)])
            while queue:
                cr, cc = queue.popleft()
                if (cr, cc) in visited:
                    continue
                visited.add((cr, cc))
                if counts[(cr, cc)] == 0:
                    for nr, nc in _neighbors(cr, cc, rows, cols):
                        if (nr, nc) not in mine_set and (nr, nc) not in visited:
                            queue.append((nr, nc))

    isolated = sum(
        1 for r in range(rows) for c in range(cols)
        if (r, c) not in mine_set and (r, c) not in visited
    )
    return openings + isolated


def _board_hash(rows: int, cols: int, mine_set: frozenset) -> str:
    payload = json.dumps(
        {"r": rows, "c": cols, "m": sorted([r, c] for r, c in mine_set)},
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


# ── Constraint solver ──────────────────────────────────────────────────────────

_UNKNOWN = 0
_SAFE    = 1
_MINE    = 2


def _solve(mine_set: frozenset, rows: int, cols: int,
           row_counts: list[int], col_counts: list[int]) -> bool:
    """
    Simulate a player solving from (0,0) using only deterministic deduction.
    Returns True iff every cell is resolved without guessing.
    """
    state = [[_UNKNOWN] * cols for _ in range(rows)]

    adj = [
        [_adjacency_count(r, c, mine_set, rows, cols) for c in range(cols)]
        for r in range(rows)
    ]

    def _flood_reveal(start_r: int, start_c: int) -> None:
        queue: deque = deque([(start_r, start_c)])
        while queue:
            r, c = queue.popleft()
            if state[r][c] != _UNKNOWN:
                continue
            state[r][c] = _SAFE
            if adj[r][c] == 0:
                for nr, nc in _neighbors(r, c, rows, cols):
                    if state[nr][nc] == _UNKNOWN and (nr, nc) not in mine_set:
                        queue.append((nr, nc))

    _flood_reveal(0, 0)

    changed = True
    while changed:
        changed = False

        # Rule 1: cell-adjacency constraints
        for r in range(rows):
            for c in range(cols):
                if state[r][c] != _SAFE or adj[r][c] == 0:
                    continue
                nbrs = list(_neighbors(r, c, rows, cols))
                unknown  = [(nr, nc) for nr, nc in nbrs if state[nr][nc] == _UNKNOWN]
                n_flagged = sum(1 for nr, nc in nbrs if state[nr][nc] == _MINE)
                remaining = adj[r][c] - n_flagged
                if remaining < 0:
                    return False
                if remaining == len(unknown) and remaining > 0:
                    for nr, nc in unknown:
                        state[nr][nc] = _MINE
                    changed = True
                elif remaining == 0 and unknown:
                    for nr, nc in unknown:
                        _flood_reveal(nr, nc)
                    changed = True

        # Rule 2: row constraints
        for r in range(rows):
            unknown  = [(r, c) for c in range(cols) if state[r][c] == _UNKNOWN]
            n_flagged = sum(1 for c in range(cols) if state[r][c] == _MINE)
            remaining = row_counts[r] - n_flagged
            if remaining < 0:
                return False
            if remaining == len(unknown) and remaining > 0:
                for r2, c2 in unknown:
                    state[r2][c2] = _MINE
                changed = True
            elif remaining == 0 and unknown:
                for r2, c2 in unknown:
                    _flood_reveal(r2, c2)
                changed = True

        # Rule 3: column constraints
        for c in range(cols):
            unknown  = [(r, c) for r in range(rows) if state[r][c] == _UNKNOWN]
            n_flagged = sum(1 for r in range(rows) if state[r][c] == _MINE)
            remaining = col_counts[c] - n_flagged
            if remaining < 0:
                return False
            if remaining == len(unknown) and remaining > 0:
                for r2, c2 in unknown:
                    state[r2][c2] = _MINE
                changed = True
            elif remaining == 0 and unknown:
                for r2, c2 in unknown:
                    _flood_reveal(r2, c2)
                changed = True

    safe_cells = rows * cols - len(mine_set)
    n_revealed = sum(state[r][c] == _SAFE for r in range(rows) for c in range(cols))
    n_flagged  = sum(state[r][c] == _MINE for r in range(rows) for c in range(cols))
    return n_revealed == safe_cells and n_flagged == len(mine_set)


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_board(
    rows: int,
    cols: int,
    num_mines: int,
    rng: Optional[random.Random] = None,
    max_attempts: int = MAX_ATTEMPTS,
) -> TametsiBoard:
    """
    Generate a no-guess-solvable Tametsi board.
    Raises RuntimeError if no solvable board is found within max_attempts.
    """
    if rng is None:
        rng = random.Random()

    if num_mines >= rows * cols:
        raise ValueError(f"Too many mines ({num_mines}) for a {rows}×{cols} board")

    candidates = [(r, c) for r in range(rows) for c in range(cols) if (r, c) != (0, 0)]

    for _ in range(max_attempts):
        mine_set = frozenset(map(tuple, rng.sample(candidates, num_mines)))

        row_counts = [0] * rows
        col_counts = [0] * cols
        for r, c in mine_set:
            row_counts[r] += 1
            col_counts[c] += 1

        if not _solve(mine_set, rows, cols, row_counts, col_counts):
            continue

        bbbv = _compute_3bv(mine_set, rows, cols)
        h    = _board_hash(rows, cols, mine_set)
        board_data = {
            "mines":      sorted([r, c] for r, c in mine_set),
            "row_counts": row_counts,
            "col_counts": col_counts,
        }
        return TametsiBoard(
            rows=rows, cols=cols,
            mines=mine_set,
            row_counts=row_counts, col_counts=col_counts,
            bbbv=bbbv,
            board_hash=h,
            board_data=board_data,
        )

    raise RuntimeError(
        f"Could not generate a solvable {rows}×{cols} board with {num_mines} mines "
        f"after {max_attempts} attempts"
    )


def daily_rng(level: str, date_str: str) -> random.Random:
    """Deterministic seeded RNG for daily puzzle generation (reproducible from level + date)."""
    if level not in LEVELS:
        raise ValueError(f"Unknown level {level!r}; expected one of {list(LEVELS)}")
    seed = int(hashlib.md5(f"tametsi:{level}:{date_str}".encode()).hexdigest(), 16) & 0xFFFF_FFFF
    return random.Random(seed)


def generate_daily(level: str, date_str: str) -> TametsiBoard:
    """Generate (or reproduce) the daily Tametsi puzzle for a given level and date."""
    rows, cols, mines = LEVELS[level]
    return generate_board(rows, cols, mines, rng=daily_rng(level, date_str))
