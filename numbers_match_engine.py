"""
numbers_match_engine.py — server-side Numbers Match rules and game replay (F-NM-VERIFY).

The server does not trust the score or time a client reports. The client sends
its move log; replay() re-runs every move from the original board with the same
rules as static/src/js/numbers_match.js and mobile/nmmobile/src/gameEngine.js,
rejects any illegal move, and returns the score and time the server will store.

Keep the rules here, in the web JS and in the mobile engine identical. Parity is
covered by tests/test_numbers_match_engine.py.

Move log format — a list of events, each a list:
    ["m", t_ms, i, j]   match the cells at indices i and j
    ["h", t_ms]         hint (only logged when a pair existed and a hint was spent)
    ["u", t_ms]         undo
    ["a", t_ms]         add lines
t_ms is milliseconds since the first cell press (0 for events before it) and must
never decrease. The last event must be the match that clears the board.
"""
import re
from dataclasses import dataclass

from numbers_match_generator import generate_daily

NM_COLS         = 9
HINT_COST       = 3
UNDO_COST       = 5
UNDO_LIMIT      = 3
HINT_LIMIT      = 9
ADD_LINES_LIMIT = 5
HISTORY_DEPTH   = 3
CLEAR_BONUS     = 150
ROW_CLEAR_BONUS = 10
MAX_EVENTS      = 5000

# Easy grew from 4 to 6 rows in revision v3 (F-NM-ROWS); keep in step with the web JS
# (NM_DIFF_LABELS) and the mobile app (GameScreen DIFFICULTIES).
DIFFICULTY_ROWS = {"easy": 6, "medium": 8, "hard": 16, "expert": 32}

# Puzzle ids that can be rebuilt on the server:
#   YYYY-MM-DD-vN               daily board (server-generated, seed suffix ":vN")
#   YYYY-MM-DD-<difficulty>-vN  difficulty board (client algorithm, seed = puzzle id)
VERIFIABLE_PUZZLE_ID = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})(?:-(?P<diff>easy|medium|hard|expert))?-(?P<rev>v\d+)$"
)


class InvalidReplay(ValueError):
    """The move log is malformed or contains a move the rules do not allow."""


# ── Board reconstruction ──────────────────────────────────────────────────────

def _imul(a: int, b: int) -> int:
    """JavaScript Math.imul, as an unsigned 32-bit result."""
    return (a * b) & 0xFFFFFFFF


def _fnv1a(s: str) -> int:
    # Puzzle ids are ASCII, so code points equal JS charCodeAt() UTF-16 units.
    h = 0x811C9DC5
    for ch in s:
        h ^= ord(ch)
        h = _imul(h, 0x01000193)
    return h


def _mulberry32(seed: int):
    state = seed & 0xFFFFFFFF

    def rng() -> float:
        nonlocal state
        state = (state + 0x6D2B79F5) & 0xFFFFFFFF
        t = _imul(state ^ (state >> 15), 1 | state)
        t = ((t + _imul(t ^ (t >> 7), 61 | t)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return rng


def generate_board_client(seed: str, rows: int) -> list[int]:
    """Port of generateBoardClient() — the board the browser builds for difficulty modes."""
    total = rows * NM_COLS
    base = [(i % NM_COLS) + 1 for i in range(total)]
    rng = _mulberry32(_fnv1a(str(seed)))
    for i in range(total - 1, 0, -1):
        j = int(rng() * (i + 1))
        base[i], base[j] = base[j], base[i]
    return base


def board_for_puzzle(puzzle_id: str) -> tuple[list[int], int] | None:
    """Rebuild the starting board for a verifiable puzzle id, or None if unsupported."""
    m = VERIFIABLE_PUZZLE_ID.match(puzzle_id)
    if not m:
        return None
    if m.group("diff"):
        rows = DIFFICULTY_ROWS[m.group("diff")]
        return generate_board_client(puzzle_id, rows), rows
    daily = generate_daily(m.group("date"), seed_suffix=f":{m.group('rev')}")
    return daily["board_data"], daily["rows"]


# ── Rules (mirror of numbers_match.js) ────────────────────────────────────────

def can_match(a: int, b: int) -> bool:
    return a != 0 and b != 0 and (a == b or a + b == 10)


def are_adjacent(board: list[int], i: int, j: int) -> bool:
    if i == j:
        return False
    lo, hi = (i, j) if i < j else (j, i)
    row_lo, col_lo = divmod(lo, NM_COLS)
    row_hi, col_hi = divmod(hi, NM_COLS)
    dr, dc = row_hi - row_lo, col_hi - col_lo
    if row_lo == row_hi:
        return all(board[k] == 0 for k in range(lo + 1, hi))
    if col_lo == col_hi:
        return all(board[k] == 0 for k in range(lo + NM_COLS, hi, NM_COLS))
    if abs(dr) == abs(dc):
        step = 1 if dc > 0 else -1
        return all(board[(row_lo + s) * NM_COLS + col_lo + s * step] == 0 for s in range(1, dr))
    # Horizontal wrap: reading-order path with only empty cells between.
    return all(board[k] == 0 for k in range(lo + 1, hi))


def pair_score(board: list[int], i: int, j: int) -> int:
    lo, hi = (i, j) if i < j else (j, i)
    row_lo, col_lo = divmod(lo, NM_COLS)
    row_hi, col_hi = divmod(hi, NM_COLS)
    dr, dc = row_hi - row_lo, col_hi - col_lo
    if row_lo == row_hi:
        cells = range(lo + 1, hi)
    elif col_lo == col_hi:
        cells = range(lo + NM_COLS, hi, NM_COLS)
    elif abs(dr) == abs(dc):
        step = 1 if dc > 0 else -1
        cells = [(row_lo + s) * NM_COLS + col_lo + s * step for s in range(1, dr)]
    else:
        cells = range(lo + 1, hi)
    empty = sum(1 for k in cells if board[k] == 0)
    return 1 + min(4, empty)


def row_clear_bonus(prev: list[int], board: list[int], rows: int) -> int:
    bonus = 0
    for r in range(rows):
        row_now, row_prev = board[r * NM_COLS:(r + 1) * NM_COLS], prev[r * NM_COLS:(r + 1) * NM_COLS]
        if all(v == 0 for v in row_now) and any(v != 0 for v in row_prev):
            bonus += ROW_CLEAR_BONUS
    return bonus


def collapse_empty_rows(board: list[int], rows: int) -> tuple[list[int], int]:
    kept: list[int] = []
    for r in range(rows):
        row = board[r * NM_COLS:(r + 1) * NM_COLS]
        if any(v != 0 for v in row):
            kept.extend(row)
    return kept, len(kept) // NM_COLS


def find_hint(board: list[int]) -> tuple[int, int] | None:
    n = len(board)
    for i in range(n - 1):
        if board[i] == 0:
            continue
        for j in range(i + 1, n):
            if board[j] != 0 and can_match(board[i], board[j]) and are_adjacent(board, i, j):
                return i, j
    return None


# ── Replay ────────────────────────────────────────────────────────────────────

@dataclass
class ReplayResult:
    score:       int
    time_ms:     int
    matches:     int
    lines_added: int
    hints_used:  int
    undos_used:  int


def replay(board: list[int], rows: int, moves: list) -> ReplayResult:
    """Re-run a move log from the starting board. Raises InvalidReplay on any problem."""
    if not isinstance(moves, list) or not moves:
        raise InvalidReplay("empty move log")
    if len(moves) > MAX_EVENTS:
        raise InvalidReplay("move log too long")

    board = list(board)
    score = 0
    history: list[dict] = []
    undos_left, hints_left, add_left = UNDO_LIMIT, HINT_LIMIT, ADD_LINES_LIMIT
    lines_added = matches = 0
    won = False
    last_t = 0

    def snapshot() -> None:
        history.append({"board": list(board), "score": score, "rows": rows,
                        "lines_added": lines_added, "add_left": add_left})
        if len(history) > HISTORY_DEPTH:
            history.pop(0)

    for n, ev in enumerate(moves):
        if not isinstance(ev, list) or len(ev) < 2 or not isinstance(ev[0], str):
            raise InvalidReplay(f"event {n}: malformed")
        kind, t = ev[0], ev[1]
        if not isinstance(t, int) or isinstance(t, bool) or t < last_t:
            raise InvalidReplay(f"event {n}: bad or decreasing timestamp")
        last_t = t
        if won:
            raise InvalidReplay(f"event {n}: move after the board was cleared")

        if kind == "m":
            if len(ev) != 4 or not all(isinstance(x, int) and not isinstance(x, bool) for x in ev[2:]):
                raise InvalidReplay(f"event {n}: malformed match")
            i, j = ev[2], ev[3]
            if not (0 <= i < len(board) and 0 <= j < len(board)):
                raise InvalidReplay(f"event {n}: cell out of range")
            if not (can_match(board[i], board[j]) and are_adjacent(board, i, j)):
                raise InvalidReplay(f"event {n}: illegal match")
            snapshot()
            prev = list(board)
            board[i] = board[j] = 0
            score += pair_score(prev, i, j)
            score += row_clear_bonus(prev, board, rows)
            matches += 1
            if all(v == 0 for v in board):
                score += CLEAR_BONUS
                won = True
            else:
                board, rows = collapse_empty_rows(board, rows)

        elif kind == "h":
            if len(ev) != 2 or hints_left <= 0 or find_hint(board) is None:
                raise InvalidReplay(f"event {n}: hint not allowed")
            hints_left -= 1
            score = max(0, score - HINT_COST)

        elif kind == "u":
            if len(ev) != 2 or undos_left <= 0 or not history:
                raise InvalidReplay(f"event {n}: undo not allowed")
            snap = history.pop()
            board, rows = list(snap["board"]), snap["rows"]
            lines_added, add_left = snap["lines_added"], snap["add_left"]
            score = max(0, snap["score"] - UNDO_COST)
            undos_left -= 1

        elif kind == "a":
            remaining = [v for v in board if v != 0]
            if len(ev) != 2 or add_left <= 0 or not remaining:
                raise InvalidReplay(f"event {n}: add lines not allowed")
            snapshot()
            remaining += [0] * (-len(remaining) % NM_COLS)
            board = board + remaining
            rows += len(remaining) // NM_COLS
            lines_added += 1
            add_left -= 1

        else:
            raise InvalidReplay(f"event {n}: unknown event type")

    if not won:
        raise InvalidReplay("board not cleared")
    return ReplayResult(score=score, time_ms=last_t, matches=matches, lines_added=lines_added,
                        hints_used=HINT_LIMIT - hints_left, undos_used=UNDO_LIMIT - undos_left)
