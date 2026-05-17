"""
analyzer.simulator — Board state replay from a move log.

Given a Game (with mine_layout and move_log), produce a BoardSnapshot at any
move index. The simulator is stateless from the caller's perspective: each
call rebuilds the snapshot from scratch unless you use the incremental form.

Implementation notes:
  - The naive simulate_up_to(i) is O(i) per call. For batch analysis that
    needs snapshots at every move index, use snapshot_at_each_move() which
    is O(n) total instead of O(n²).
  - The chord rule matches the standard minesweeper implementation: a chord
    only fires when adjacent flag count == cell value.
  - Flood reveal uses BFS over 0-cells; numbered cells border the reveal.
"""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from typing import Iterator

from .types import Action, BoardSnapshot, CellState, Game, Move


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def fresh_board(game: Game) -> BoardSnapshot:
    """Empty board: every cell unrevealed."""
    cells = [
        [CellState(kind="unrevealed") for _ in range(game.width)]
        for _ in range(game.height)
    ]
    return BoardSnapshot(
        width=game.width,
        height=game.height,
        mine_layout=game.mine_layout,
        cells=cells,
    )


def simulate_up_to(game: Game, move_index: int) -> BoardSnapshot:
    """
    Return the board state after applying moves [0..move_index] inclusive.
    Use move_index = -1 for the pre-game state.
    """
    board = fresh_board(game)
    for i in range(min(move_index + 1, len(game.move_log))):
        apply_move(board, game.move_log[i])
    return board


def snapshot_at_each_move(game: Game) -> Iterator[tuple[int, BoardSnapshot]]:
    """
    Yield (move_index, board_after_that_move) for every move, in O(n) total.
    Yields the pre-game state as (-1, fresh_board) first.
    """
    board = fresh_board(game)
    yield -1, board
    for i, move in enumerate(game.move_log):
        apply_move(board, move)
        yield i, board


def apply_move(board: BoardSnapshot, move: Move) -> "MoveOutcome":
    """
    Mutate the board in-place by applying the move. Returns the outcome,
    which the analyzer passes use to detect wasted/successful clicks etc.
    """
    cell = board.cells[move.y][move.x]
    cells_revealed = 0
    hit_mine = False

    if move.action == Action.LEFT_CLICK:
        if cell.kind == "unrevealed":
            if board.mine_layout[move.y][move.x]:
                board.cells[move.y][move.x] = CellState(kind="mine")
                hit_mine = True
            else:
                cells_revealed = _flood_reveal(board, move.x, move.y)

    elif move.action == Action.RIGHT_CLICK:
        if cell.kind == "unrevealed":
            board.cells[move.y][move.x] = CellState(kind="flagged")
        elif cell.kind == "flagged":
            board.cells[move.y][move.x] = CellState(kind="unrevealed")

    elif move.action == Action.CHORD:
        if cell.kind == "revealed":
            cells_revealed, hit_mine = _chord_reveal(
                board, move.x, move.y, cell.adjacent_mines
            )

    return MoveOutcome(cells_revealed=cells_revealed, hit_mine=hit_mine)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

class MoveOutcome:
    __slots__ = ("cells_revealed", "hit_mine")

    def __init__(self, cells_revealed: int, hit_mine: bool):
        self.cells_revealed = cells_revealed
        self.hit_mine = hit_mine


def _neighbors(x: int, y: int) -> list[tuple[int, int]]:
    """Eight surrounding cells."""
    return [
        (x + dx, y + dy)
        for dy in (-1, 0, 1)
        for dx in (-1, 0, 1)
        if not (dx == 0 and dy == 0)
    ]


def _count_adj_mines(board: BoardSnapshot, x: int, y: int) -> int:
    return sum(
        1 for nx, ny in _neighbors(x, y)
        if board.in_bounds(nx, ny) and board.mine_layout[ny][nx]
    )


def _flood_reveal(board: BoardSnapshot, x: int, y: int) -> int:
    """BFS flood fill on 0-cells. Returns count of cells newly revealed."""
    queue: deque[tuple[int, int]] = deque([(x, y)])
    revealed_count = 0
    while queue:
        cx, cy = queue.popleft()
        if not board.in_bounds(cx, cy):
            continue
        c = board.cells[cy][cx]
        if c.kind != "unrevealed":
            continue
        adj = _count_adj_mines(board, cx, cy)
        board.cells[cy][cx] = CellState(kind="revealed", adjacent_mines=adj)
        revealed_count += 1
        if adj == 0:
            for nx, ny in _neighbors(cx, cy):
                queue.append((nx, ny))
    return revealed_count


def _chord_reveal(
    board: BoardSnapshot, x: int, y: int, num: int
) -> tuple[int, bool]:
    """
    Chord fires only if adjacent_flags == num. Reveals all unflagged neighbors.
    Returns (cells_revealed, hit_mine).
    """
    flags = sum(
        1 for nx, ny in _neighbors(x, y)
        if board.in_bounds(nx, ny) and board.cells[ny][nx].kind == "flagged"
    )
    if flags != num:
        return 0, False

    revealed = 0
    hit_mine = False
    for nx, ny in _neighbors(x, y):
        if not board.in_bounds(nx, ny):
            continue
        if board.cells[ny][nx].kind != "unrevealed":
            continue
        if board.mine_layout[ny][nx]:
            board.cells[ny][nx] = CellState(kind="mine")
            hit_mine = True
        else:
            revealed += _flood_reveal(board, nx, ny)
    return revealed, hit_mine


# ─────────────────────────────────────────────────────────────────────────────
# Snapshot utilities
# ─────────────────────────────────────────────────────────────────────────────

def clone_board(board: BoardSnapshot) -> BoardSnapshot:
    """Deep copy. Mine layout is shared (immutable)."""
    return BoardSnapshot(
        width=board.width,
        height=board.height,
        mine_layout=board.mine_layout,
        cells=[
            [CellState(kind=c.kind, adjacent_mines=c.adjacent_mines)
             for c in row]
            for row in board.cells
        ],
    )


def boards_equal(a: BoardSnapshot, b: BoardSnapshot) -> bool:
    """Structural equality on visible cell state."""
    if a.width != b.width or a.height != b.height:
        return False
    for y in range(a.height):
        for x in range(a.width):
            ca, cb = a.cells[y][x], b.cells[y][x]
            if ca.kind != cb.kind:
                return False
            if ca.kind == "revealed" and ca.adjacent_mines != cb.adjacent_mines:
                return False
    return True


def count_newly_revealed(before: BoardSnapshot, after: BoardSnapshot) -> int:
    """How many cells were revealed between two snapshots."""
    count = 0
    for y in range(before.height):
        for x in range(before.width):
            if (before.cells[y][x].kind == "unrevealed"
                    and after.cells[y][x].kind == "revealed"):
                count += 1
    return count


def revealed_cells(board: BoardSnapshot) -> list[tuple[int, int]]:
    """All currently-revealed positions."""
    return [
        (x, y)
        for y in range(board.height)
        for x in range(board.width)
        if board.cells[y][x].kind == "revealed"
    ]


def unrevealed_neighbors(
    board: BoardSnapshot, x: int, y: int
) -> list[tuple[int, int]]:
    """Neighbors of (x, y) that are still unrevealed (excludes flagged)."""
    return [
        (nx, ny) for nx, ny in _neighbors(x, y)
        if board.in_bounds(nx, ny) and board.cells[ny][nx].kind == "unrevealed"
    ]


def flagged_neighbors(
    board: BoardSnapshot, x: int, y: int
) -> list[tuple[int, int]]:
    return [
        (nx, ny) for nx, ny in _neighbors(x, y)
        if board.in_bounds(nx, ny) and board.cells[ny][nx].kind == "flagged"
    ]


def all_neighbors(x: int, y: int) -> list[tuple[int, int]]:
    """Public re-export of the 8-neighbor helper."""
    return _neighbors(x, y)
