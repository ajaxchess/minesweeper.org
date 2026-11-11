"""
minesweeper_engine.py — server-side replay of a classic Minesweeper game (F-MS-VERIFY).

Replays the move log recorded by static/src/js/minesweeper.js on the board encoded
in board_hash, with the browser's exact click rules, and reports whether the game
was won and when. The rules live in three functions there — reveal(), chord() and
flag() — and must stay identical here; tests/test_minesweeper_engine.py replays
games recorded from the real script (tests/fixtures/minesweeper_js_games.json).

No database or web imports: this module is pure so it can be tested on its own.
"""
from __future__ import annotations

import base64
import binascii
from collections import deque
from dataclasses import dataclass

MAX_LOG_ENTRIES = 10_000

LEFT, RIGHT, CHORD = "l", "r", "c"


class ReplayError(ValueError):
    """The submitted game is not a legal win on the submitted board."""


@dataclass(frozen=True)
class ReplayResult:
    last_t_ms:    int   # timestamp of the winning click
    bbbv:         int   # 3BV of the board, computed here
    left_clicks:  int
    right_clicks: int
    chord_clicks: int


def decode_board_hash(board_hash: str, rows: int, cols: int) -> frozenset[int]:
    """Mine cell indexes (row * cols + col) from calcBoardHash()'s base64 bit array.

    Bit i of the array is cell i, least significant bit first within each byte.
    """
    n = rows * cols
    try:
        raw = base64.b64decode(board_hash, validate=True)
    except (binascii.Error, ValueError, TypeError):
        raise ReplayError("board_hash is not base64")
    if len(raw) != (n + 7) // 8:
        raise ReplayError("board_hash does not match the board size")
    mines = frozenset(i for i in range(n) if (raw[i >> 3] >> (i & 7)) & 1)
    if any((raw[i >> 3] >> (i & 7)) & 1 for i in range(n, len(raw) * 8)):
        raise ReplayError("board_hash has mines outside the board")
    return mines


def _neighbours(idx: int, rows: int, cols: int) -> list[int]:
    r, c = divmod(idx, cols)
    return [
        nr * cols + nc
        for nr in (r - 1, r, r + 1) if 0 <= nr < rows
        for nc in (c - 1, c, c + 1) if 0 <= nc < cols and (nr, nc) != (r, c)
    ]


def _adjacency(rows: int, cols: int, mines: frozenset[int]) -> tuple[list[list[int]], list[int]]:
    """(neighbour lists, adjacent-mine counts with -1 on mines)."""
    nbrs = [_neighbours(i, rows, cols) for i in range(rows * cols)]
    counts = [-1 if i in mines else sum(1 for j in nbrs[i] if j in mines) for i in range(rows * cols)]
    return nbrs, counts


def compute_3bv(rows: int, cols: int, mines: frozenset[int]) -> int:
    """3BV: one click per opening, plus one per numbered cell no opening touches."""
    nbrs, counts = _adjacency(rows, cols, mines)
    covered = [False] * (rows * cols)
    bbbv = 0
    for start in range(rows * cols):
        if counts[start] != 0 or covered[start]:
            continue
        bbbv += 1
        covered[start] = True
        queue = deque([start])
        while queue:
            for j in nbrs[queue.popleft()]:
                if covered[j] or counts[j] < 0:
                    continue
                covered[j] = True
                if counts[j] == 0:
                    queue.append(j)
    return bbbv + sum(1 for i in range(rows * cols) if counts[i] > 0 and not covered[i])


def _parse_log(log, rows: int, cols: int) -> list[tuple[int, str, int]]:
    if not isinstance(log, list) or not log:
        raise ReplayError("move log is empty")
    if len(log) > MAX_LOG_ENTRIES:
        raise ReplayError("move log is too long")
    moves = []
    prev_t = 0
    for entry in log:
        if not isinstance(entry, (list, tuple)) or len(entry) != 4:
            raise ReplayError("log entry must be [t_ms, type, row, col]")
        t, kind, r, c = entry
        # bool is an int in Python; JSON true/false are not timestamps or coordinates.
        if any(type(v) is not int for v in (t, r, c)):
            raise ReplayError("log entry fields must be integers")
        if kind not in (LEFT, RIGHT, CHORD):
            raise ReplayError("unknown action in move log")
        if not (0 <= r < rows and 0 <= c < cols):
            raise ReplayError("move is off the board")
        if t < prev_t:
            raise ReplayError("move log timestamps go backwards")
        prev_t = t
        moves.append((t, kind, r * cols + c))
    return moves


def replay(rows: int, cols: int, mines: frozenset[int], log, *,
           chording: bool = True, evil: bool = False) -> ReplayResult:
    """Replay the log; return the result of a won game or raise ReplayError."""
    n = rows * cols
    moves = _parse_log(log, rows, cols)
    nbrs, counts = _adjacency(rows, cols, mines)

    revealed = [False] * n
    mark = [0] * n            # 0 none, 1 flag, 2 question mark
    hidden = n
    started = False
    won = False
    evil_start = cols - 1     # top-right cell

    def reveal(idx: int) -> None:
        nonlocal started, hidden, won
        if won or revealed[idx] or mark[idx] == 1:
            return
        if not started:
            if evil and idx != evil_start:
                return
            started = True
        if counts[idx] < 0:
            raise ReplayError("a mine was revealed")
        queue = deque([idx])
        while queue:
            cur = queue.popleft()
            if revealed[cur]:
                continue
            revealed[cur] = True
            hidden -= 1
            if counts[cur] == 0:
                queue.extend(j for j in nbrs[cur] if not revealed[j] and not mark[j])
        if hidden == len(mines):
            won = True

    clicks = {LEFT: 0, RIGHT: 0, CHORD: 0}
    for t, kind, idx in moves:
        if won:
            raise ReplayError("moves continue after the game was won")
        clicks[kind] += 1
        if kind == LEFT:
            reveal(idx)
        elif kind == RIGHT:
            if not revealed[idx]:
                mark[idx] = (mark[idx] + 1) % 3
        elif chording and revealed[idx] and counts[idx] > 0:
            if sum(1 for j in nbrs[idx] if mark[j] == 1) == counts[idx]:
                for j in nbrs[idx]:
                    reveal(j)

    if not won:
        raise ReplayError("the move log does not clear the board")

    return ReplayResult(
        last_t_ms=moves[-1][0],
        bbbv=compute_3bv(rows, cols, mines),
        left_clicks=clicks[LEFT],
        right_clicks=clicks[RIGHT],
        chord_clicks=clicks[CHORD],
    )
