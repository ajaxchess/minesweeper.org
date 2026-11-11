"""
tests/ms_games.py — build classic Minesweeper submissions the server can replay
(F-MS-VERIFY). A leaderboard-candidate score is only listed if it carries a start
token and a move log that wins its board, so tests that expect a listed score post
one of these instead of bare numbers.
"""
import base64
import time
from unittest import mock

import minesweeper_engine as engine
import score_verification
from conftest import XHR

BOARDS = {   # mode → (rows, cols, mines)
    "beginner":     (9, 9, 10),
    "intermediate": (16, 16, 40),
    "expert":       (30, 16, 99),
    "evil":         (20, 30, 130),
}


def board_hash(rows, cols, mines):
    """Same encoding as calcBoardHash() in minesweeper.js: bit i = cell i, LSB first."""
    bits = bytearray((rows * cols + 7) // 8)
    for idx in mines:
        bits[idx >> 3] |= 1 << (idx & 7)
    return base64.b64encode(bytes(bits)).decode()


def winning_log(rows, cols, mines, time_ms, evil=False):
    """Left-click safe cells until the board is won; the last click lands on time_ms."""
    mines = frozenset(mines)
    order = [i for i in range(rows * cols) if i not in mines]
    if evil:   # the first reveal must be the top-right cell
        order.remove(cols - 1)
        order.insert(0, cols - 1)
    cells = []
    for idx in order:
        cells.append(idx)
        try:
            engine.replay(rows, cols, mines, [[0, "l", *divmod(i, cols)] for i in cells], evil=evil)
            break
        except engine.ReplayError as exc:
            if "does not clear" not in str(exc):
                cells.pop()   # already revealed by an earlier opening: clicking it again is fine but pointless
    last = len(cells) - 1
    return [[(time_ms * k) // last if last else time_ms, "l", *divmod(idx, cols)]
            for k, idx in enumerate(cells)]


def game_token(age_ms=0):
    """A real start token, optionally issued age_ms in the past."""
    issued = time.time() - age_ms / 1000
    with mock.patch("itsdangerous.timed.time.time", return_value=issued):
        return score_verification.new_game_token()


def submission(name="Alice", mode="beginner", time_ms=30_000, rows=None, cols=None,
               mines=None, no_guess=False, **overrides):
    """A complete, honest /api/scores body: board, winning log and a token old enough."""
    r, c, m = BOARDS.get(mode, (rows, cols, None))
    rows, cols = rows or r, cols or c
    # Default layout: the first cells are mines; evil keeps its forced start row clear.
    mine_cells = mines if mines is not None else range(cols, cols + m) if mode == "evil" else range(m)
    mine_cells = list(mine_cells)
    body = {
        "name": name, "mode": mode, "rows": rows, "cols": cols, "mines": len(mine_cells),
        "no_guess": no_guess, "time_secs": max(1, time_ms // 1000), "time_ms": time_ms,
        "board_hash": board_hash(rows, cols, mine_cells), "chording": True,
        "log": winning_log(rows, cols, mine_cells, time_ms, evil=(mode == "evil")),
        "game_token": game_token(age_ms=time_ms + 1000),
    }
    body.update(overrides)
    return body


def post(client, **kwargs):
    return client.post("/api/scores", json=submission(**kwargs), headers=XHR)
