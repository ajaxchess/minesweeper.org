"""
sudoku_grader.py — Logical Sudoku solver that grades puzzles by technique.

Applies human-style solving techniques in order of difficulty and reports the
hardest technique required to solve the puzzle. If the puzzle cannot be solved
with logic alone (requires guessing), it is rejected.

Technique hierarchy (easiest → hardest):
  1. Naked singles
  2. Hidden singles
  3. Naked pairs
  4. Hidden pairs
  5. Naked triples
  6. Pointing pairs / box-line reduction
  7. X-Wing
  8. Swordfish
  9. XY-Wing

Difficulty levels:
  easy   — naked singles + hidden singles only
  medium — up to naked/hidden pairs
  hard   — up to pointing pairs / box-line reduction
  expert — requires X-Wing, Swordfish, or XY-Wing
"""

from __future__ import annotations

from enum import IntEnum
from itertools import combinations
from typing import NamedTuple


class Technique(IntEnum):
    NAKED_SINGLE = 1
    HIDDEN_SINGLE = 2
    NAKED_PAIR = 3
    HIDDEN_PAIR = 4
    NAKED_TRIPLE = 5
    POINTING_PAIR = 6
    X_WING = 7
    SWORDFISH = 8
    XY_WING = 9


TECHNIQUE_NAMES = {
    Technique.NAKED_SINGLE: "Naked Single",
    Technique.HIDDEN_SINGLE: "Hidden Single",
    Technique.NAKED_PAIR: "Naked Pair",
    Technique.HIDDEN_PAIR: "Hidden Pair",
    Technique.NAKED_TRIPLE: "Naked Triple",
    Technique.POINTING_PAIR: "Pointing Pair",
    Technique.X_WING: "X-Wing",
    Technique.SWORDFISH: "Swordfish",
    Technique.XY_WING: "XY-Wing",
}

DIFFICULTY_LEVELS = {
    "easy": Technique.HIDDEN_SINGLE,
    "medium": Technique.HIDDEN_PAIR,
    "hard": Technique.POINTING_PAIR,
    "expert": Technique.XY_WING,
    "daily": Technique.HIDDEN_PAIR,
}


class GradeResult(NamedTuple):
    solved: bool
    hardest_technique: Technique | None
    difficulty: str | None
    techniques_used: set[Technique]


def _peers(cell: int) -> list[int]:
    """Return indices of all cells that share a row, column, or box with cell."""
    r, c = divmod(cell, 9)
    br, bc = (r // 3) * 3, (c // 3) * 3
    peers = set()
    for i in range(9):
        peers.add(r * 9 + i)
        peers.add(i * 9 + c)
    for dr in range(3):
        for dc in range(3):
            peers.add((br + dr) * 9 + (bc + dc))
    peers.discard(cell)
    return sorted(peers)


_PEERS = [_peers(i) for i in range(81)]
_ROWS = [list(range(r * 9, r * 9 + 9)) for r in range(9)]
_COLS = [list(range(c, 81, 9)) for c in range(9)]
_BOXES = []
for br in range(3):
    for bc in range(3):
        box = []
        for dr in range(3):
            for dc in range(3):
                box.append((br * 3 + dr) * 9 + (bc * 3 + dc))
        _BOXES.append(box)

_ALL_UNITS = _ROWS + _COLS + _BOXES

_CELL_TO_ROW = [i // 9 for i in range(81)]
_CELL_TO_COL = [i % 9 for i in range(81)]
_CELL_TO_BOX = [(i // 9 // 3) * 3 + (i % 9 // 3) for i in range(81)]


def _init_candidates(grid: list[int]) -> list[set[int]]:
    """Initialize candidate sets from a grid (0 = empty)."""
    candidates = [set() for _ in range(81)]
    for i in range(81):
        if grid[i] == 0:
            candidates[i] = set(range(1, 10))
    for i in range(81):
        if grid[i] != 0:
            for p in _PEERS[i]:
                candidates[p].discard(grid[i])
    return candidates


def _assign(grid: list[int], candidates: list[set[int]], cell: int, val: int) -> None:
    grid[cell] = val
    candidates[cell] = set()
    for p in _PEERS[cell]:
        candidates[p].discard(val)


def _naked_singles(grid: list[int], candidates: list[set[int]]) -> bool:
    progress = False
    for i in range(81):
        if grid[i] == 0 and len(candidates[i]) == 1:
            val = next(iter(candidates[i]))
            _assign(grid, candidates, i, val)
            progress = True
    return progress


def _hidden_singles(grid: list[int], candidates: list[set[int]]) -> bool:
    progress = False
    for unit in _ALL_UNITS:
        for d in range(1, 10):
            places = [c for c in unit if d in candidates[c]]
            if len(places) == 1:
                _assign(grid, candidates, places[0], d)
                progress = True
    return progress


def _naked_pairs(grid: list[int], candidates: list[set[int]]) -> bool:
    progress = False
    for unit in _ALL_UNITS:
        unsolved = [c for c in unit if grid[c] == 0 and len(candidates[c]) == 2]
        for a, b in combinations(unsolved, 2):
            if candidates[a] == candidates[b]:
                pair_vals = candidates[a]
                for c in unit:
                    if c != a and c != b and grid[c] == 0:
                        before = len(candidates[c])
                        candidates[c] -= pair_vals
                        if len(candidates[c]) < before:
                            progress = True
    return progress


def _hidden_pairs(grid: list[int], candidates: list[set[int]]) -> bool:
    progress = False
    for unit in _ALL_UNITS:
        for d1, d2 in combinations(range(1, 10), 2):
            places1 = {c for c in unit if d1 in candidates[c]}
            places2 = {c for c in unit if d2 in candidates[c]}
            union = places1 | places2
            if len(union) == 2 and len(places1) <= 2 and len(places2) <= 2:
                pair_vals = {d1, d2}
                for c in union:
                    before = len(candidates[c])
                    candidates[c] &= pair_vals
                    if len(candidates[c]) < before:
                        progress = True
    return progress


def _naked_triples(grid: list[int], candidates: list[set[int]]) -> bool:
    progress = False
    for unit in _ALL_UNITS:
        unsolved = [c for c in unit if grid[c] == 0 and 2 <= len(candidates[c]) <= 3]
        for combo in combinations(unsolved, 3):
            union = set()
            for c in combo:
                union |= candidates[c]
            if len(union) == 3:
                for c in unit:
                    if c not in combo and grid[c] == 0:
                        before = len(candidates[c])
                        candidates[c] -= union
                        if len(candidates[c]) < before:
                            progress = True
    return progress


def _pointing_pairs(grid: list[int], candidates: list[set[int]]) -> bool:
    progress = False
    for box_idx, box in enumerate(_BOXES):
        for d in range(1, 10):
            places = [c for c in box if d in candidates[c]]
            if len(places) < 2 or len(places) > 3:
                continue
            rows = {_CELL_TO_ROW[c] for c in places}
            cols = {_CELL_TO_COL[c] for c in places}
            if len(rows) == 1:
                row = next(iter(rows))
                for c in _ROWS[row]:
                    if c not in places and d in candidates[c]:
                        candidates[c].discard(d)
                        progress = True
            elif len(cols) == 1:
                col = next(iter(cols))
                for c in _COLS[col]:
                    if c not in places and d in candidates[c]:
                        candidates[c].discard(d)
                        progress = True
    # Box-line reduction (reverse): if a digit in a row/col is confined to one box
    for line_units, get_box in [(_ROWS, _CELL_TO_BOX), (_COLS, _CELL_TO_BOX)]:
        for line in line_units:
            for d in range(1, 10):
                places = [c for c in line if d in candidates[c]]
                if len(places) < 2 or len(places) > 3:
                    continue
                boxes = {get_box[c] for c in places}
                if len(boxes) == 1:
                    box_idx = next(iter(boxes))
                    for c in _BOXES[box_idx]:
                        if c not in places and d in candidates[c]:
                            candidates[c].discard(d)
                            progress = True
    return progress


def _x_wing(grid: list[int], candidates: list[set[int]]) -> bool:
    progress = False
    # Row-based X-Wing
    for d in range(1, 10):
        row_places = []
        for r in range(9):
            cols = [c % 9 for c in _ROWS[r] if d in candidates[c]]
            row_places.append(cols)
        for r1, r2 in combinations(range(9), 2):
            if len(row_places[r1]) == 2 and row_places[r1] == row_places[r2]:
                c1, c2 = row_places[r1]
                for r in range(9):
                    if r != r1 and r != r2:
                        for col in (c1, c2):
                            cell = r * 9 + col
                            if d in candidates[cell]:
                                candidates[cell].discard(d)
                                progress = True
    # Column-based X-Wing
    for d in range(1, 10):
        col_places = []
        for c in range(9):
            rows = [cell // 9 for cell in _COLS[c] if d in candidates[cell]]
            col_places.append(rows)
        for c1, c2 in combinations(range(9), 2):
            if len(col_places[c1]) == 2 and col_places[c1] == col_places[c2]:
                r1, r2 = col_places[c1]
                for c in range(9):
                    if c != c1 and c != c2:
                        for row in (r1, r2):
                            cell = row * 9 + c
                            if d in candidates[cell]:
                                candidates[cell].discard(d)
                                progress = True
    return progress


def _swordfish(grid: list[int], candidates: list[set[int]]) -> bool:
    progress = False
    # Row-based Swordfish
    for d in range(1, 10):
        row_places = []
        for r in range(9):
            cols = frozenset(c % 9 for c in _ROWS[r] if d in candidates[c])
            row_places.append(cols)
        for rows in combinations(range(9), 3):
            union_cols = set()
            valid = True
            for r in rows:
                if len(row_places[r]) < 2 or len(row_places[r]) > 3:
                    valid = False
                    break
                union_cols |= row_places[r]
            if not valid or len(union_cols) != 3:
                continue
            for r in range(9):
                if r not in rows:
                    for col in union_cols:
                        cell = r * 9 + col
                        if d in candidates[cell]:
                            candidates[cell].discard(d)
                            progress = True
    # Column-based Swordfish
    for d in range(1, 10):
        col_places = []
        for c in range(9):
            rows = frozenset(cell // 9 for cell in _COLS[c] if d in candidates[cell])
            col_places.append(rows)
        for cols in combinations(range(9), 3):
            union_rows = set()
            valid = True
            for c in cols:
                if len(col_places[c]) < 2 or len(col_places[c]) > 3:
                    valid = False
                    break
                union_rows |= col_places[c]
            if not valid or len(union_rows) != 3:
                continue
            for c in range(9):
                if c not in cols:
                    for row in union_rows:
                        cell = row * 9 + c
                        if d in candidates[cell]:
                            candidates[cell].discard(d)
                            progress = True
    return progress


def _xy_wing(grid: list[int], candidates: list[set[int]]) -> bool:
    progress = False
    bi_cells = [i for i in range(81) if grid[i] == 0 and len(candidates[i]) == 2]
    for pivot in bi_cells:
        pv = candidates[pivot]
        pivot_peers = set(_PEERS[pivot])
        for wing1 in bi_cells:
            if wing1 == pivot or wing1 not in pivot_peers:
                continue
            w1 = candidates[wing1]
            shared1 = pv & w1
            if len(shared1) != 1:
                continue
            for wing2 in bi_cells:
                if wing2 == pivot or wing2 == wing1 or wing2 not in pivot_peers:
                    continue
                w2 = candidates[wing2]
                shared2 = pv & w2
                if len(shared2) != 1:
                    continue
                if shared1 == shared2:
                    continue
                # The eliminated digit is the one shared by the two wings but not the pivot
                elim_set = w1 & w2
                if len(elim_set) != 1:
                    continue
                elim = next(iter(elim_set))
                if elim in pv:
                    continue
                # Eliminate from cells that see both wings
                wing1_peers = set(_PEERS[wing1])
                wing2_peers = set(_PEERS[wing2])
                common = wing1_peers & wing2_peers
                for c in common:
                    if c != pivot and elim in candidates[c]:
                        candidates[c].discard(elim)
                        progress = True
    return progress


_TECHNIQUE_FUNCS = [
    (Technique.NAKED_SINGLE, _naked_singles),
    (Technique.HIDDEN_SINGLE, _hidden_singles),
    (Technique.NAKED_PAIR, _naked_pairs),
    (Technique.HIDDEN_PAIR, _hidden_pairs),
    (Technique.NAKED_TRIPLE, _naked_triples),
    (Technique.POINTING_PAIR, _pointing_pairs),
    (Technique.X_WING, _x_wing),
    (Technique.SWORDFISH, _swordfish),
    (Technique.XY_WING, _xy_wing),
]


def grade(givens: str) -> GradeResult:
    """Grade a Sudoku puzzle by the techniques needed to solve it.

    Args:
        givens: 81-char string of digits 0-9 (0 = empty).

    Returns:
        GradeResult with solved flag, hardest technique, difficulty label,
        and set of all techniques used.
    """
    if len(givens) != 81 or not all(c in "0123456789" for c in givens):
        raise ValueError("givens must be 81 digits 0-9")

    grid = [int(c) for c in givens]
    candidates = _init_candidates(grid)

    techniques_used: set[Technique] = set()
    hardest = None

    while any(grid[i] == 0 for i in range(81)):
        made_progress = False
        for technique, func in _TECHNIQUE_FUNCS:
            if func(grid, candidates):
                techniques_used.add(technique)
                if hardest is None or technique > hardest:
                    hardest = technique
                made_progress = True
                break  # restart from easiest technique
        if not made_progress:
            return GradeResult(solved=False, hardest_technique=hardest,
                               difficulty=None, techniques_used=techniques_used)

    # Check validity
    for unit in _ALL_UNITS:
        vals = {grid[c] for c in unit}
        if vals != set(range(1, 10)):
            return GradeResult(solved=False, hardest_technique=hardest,
                               difficulty=None, techniques_used=techniques_used)

    difficulty = None
    if hardest is not None:
        for level, max_technique in DIFFICULTY_LEVELS.items():
            if level == "daily":
                continue
            if hardest <= max_technique:
                difficulty = level
                break

    return GradeResult(solved=True, hardest_technique=hardest,
                       difficulty=difficulty, techniques_used=techniques_used)


def grade_for_difficulty(givens: str, target: str) -> bool:
    """Check whether a puzzle grades exactly into the target difficulty.

    Returns True if the puzzle is solvable by logic alone and its hardest
    technique falls within the target difficulty's range but requires at
    least one technique above the previous level.
    """
    result = grade(givens)
    if not result.solved or result.hardest_technique is None:
        return False

    target_max = DIFFICULTY_LEVELS.get(target)
    if target_max is None:
        return False

    actual_target = target if target != "daily" else "medium"

    ordered = ["easy", "medium", "hard", "expert"]
    idx = ordered.index(actual_target)
    prev_max = DIFFICULTY_LEVELS[ordered[idx - 1]] if idx > 0 else 0

    return prev_max < result.hardest_technique <= target_max
