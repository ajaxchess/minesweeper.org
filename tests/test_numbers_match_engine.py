"""
tests/test_numbers_match_engine.py — server-side replay engine (F-NM-VERIFY).

Parity: fixtures/numbers_match_js_games.json holds games played by the real web
client (static/src/js/numbers_match.js) in Node. The server engine must rebuild
the same boards and compute the same score for every one of them.
"""
import json
from pathlib import Path

import pytest

from numbers_match_engine import (
    InvalidReplay, board_for_puzzle, generate_board_client, replay,
)
from numbers_match_generator import generate_daily

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "numbers_match_js_games.json").read_text())
WON  = [g for g in FIXTURE["games"] if g["won"]]
LOST = [g for g in FIXTURE["games"] if not g["won"]]


# ── Parity with the web client ────────────────────────────────────────────────

@pytest.mark.parametrize("vec", FIXTURE["vectors"], ids=lambda v: v["seed"] or "empty")
def test_board_generation_matches_js(vec):
    assert generate_board_client(vec["seed"], vec["rows"]) == vec["board"]


@pytest.mark.parametrize("game", FIXTURE["games"], ids=lambda g: g["puzzle_id"])
def test_board_for_puzzle_matches_js(game):
    board, rows = board_for_puzzle(game["puzzle_id"])
    assert (board, rows) == (game["board"], game["rows"])


@pytest.mark.parametrize("game", WON, ids=lambda g: g["puzzle_id"])
def test_replay_score_matches_js(game):
    result = replay(game["board"], game["rows"], game["moves"])
    assert result.score == game["score"]
    assert result.lines_added == game["lines_added"]


@pytest.mark.parametrize("game", FIXTURE["mobile_games"], ids=lambda g: "mobile-" + g["puzzle_id"])
def test_mobile_app_replay_matches(game):
    """Games played through the nmmobile reducer replay to the same score."""
    assert board_for_puzzle(game["puzzle_id"]) == (game["board"], game["rows"])
    result = replay(game["board"], game["rows"], game["moves"])
    assert result.score == game["score"]
    assert result.lines_added == game["lines_added"]


def test_mobile_fixture_present():
    assert len(FIXTURE["mobile_games"]) >= 20
    assert {m[0] for g in FIXTURE["mobile_games"] for m in g["moves"]} == {"m", "h", "u", "a"}


def test_fixture_covers_every_event_type():
    kinds = {m[0] for g in WON for m in g["moves"]}
    assert kinds == {"m", "h", "u", "a"}
    assert len(WON) >= 50


@pytest.mark.parametrize("game", LOST[:5], ids=lambda g: g["puzzle_id"])
def test_unfinished_game_rejected(game):
    with pytest.raises(InvalidReplay, match="not cleared"):
        replay(game["board"], game["rows"], game["moves"])


# ── Board reconstruction ──────────────────────────────────────────────────────

def test_daily_board_uses_revision_suffix():
    board, rows = board_for_puzzle("2026-10-11-v3")
    assert board == generate_daily("2026-10-11", seed_suffix=":v3")["board_data"]
    assert rows == 6


def test_daily_and_easy_have_six_rows():
    """F-NM-ROWS: Daily and Easy grew from 4 to 6 rows; the other levels are unchanged."""
    assert board_for_puzzle("2026-10-11-v3")[1] == 6
    assert {d: board_for_puzzle(f"2026-10-11-{d}-v3")[1] for d in ("easy", "medium", "hard", "expert")} \
        == {"easy": 6, "medium": 8, "hard": 16, "expert": 32}


@pytest.mark.parametrize("pid", [
    "2026-10-11",                 # legacy daily without revision
    "2026-10-11-easy",            # legacy difficulty without revision
    "2026-10-11-insane-v2",
    "abc123",
])
def test_unverifiable_puzzle_ids(pid):
    assert board_for_puzzle(pid) is None


# ── Tampering ─────────────────────────────────────────────────────────────────

GAME = WON[0]


def _replay(moves):
    return replay(GAME["board"], GAME["rows"], moves)


def _copy():
    return [list(m) for m in GAME["moves"]]


def test_replayed_score_ignores_nothing_from_client():
    # The log carries no score; tampering means changing moves.
    assert _replay(_copy()).score == GAME["score"]


def test_illegal_match_rejected():
    moves = _copy()
    first = next(m for m in moves if m[0] == "m")
    first[3] = first[2]                                    # match a cell with itself
    with pytest.raises(InvalidReplay, match="illegal match"):
        _replay(moves)


def test_dropped_move_rejected():
    moves = _copy()
    idx = next(i for i, m in enumerate(moves) if m[0] == "m")
    del moves[idx]
    with pytest.raises(InvalidReplay):
        _replay(moves)


def test_hint_without_an_available_pair_rejected():
    # The harness only adds lines when no pair exists, so a hint right before
    # an add-lines event has nothing to point at; the client never logs that.
    game = next(g for g in WON if any(m[0] == "a" for m in g["moves"]))
    moves = [list(m) for m in game["moves"]]
    idx = next(i for i, m in enumerate(moves) if m[0] == "a")
    moves.insert(idx, ["h", moves[idx][1]])
    with pytest.raises(InvalidReplay, match="hint not allowed"):
        replay(game["board"], game["rows"], moves)


def test_hint_limit_enforced():
    with pytest.raises(InvalidReplay, match="event 9: hint not allowed"):
        _replay([["h", 0]] * 10)


def test_decreasing_timestamp_rejected():
    moves = _copy()
    moves[-1][1] = -1
    with pytest.raises(InvalidReplay, match="timestamp"):
        _replay(moves)


@pytest.mark.parametrize("bad", [
    [["m", 0, 0]], [["m", 0, 0, "1"]], [["x", 0]], [["m", "0", 0, 1]],
    [["m", 0, 0, 999999]], [[]], [["h", 0, 1]], [["m", True, 0, 1]],
])
def test_malformed_events_rejected(bad):
    with pytest.raises(InvalidReplay):
        _replay(bad)


def test_undo_limits_enforced():
    with pytest.raises(InvalidReplay, match="undo"):
        _replay([["u", 0]])                               # nothing to undo yet


def test_add_lines_limit_enforced():
    with pytest.raises(InvalidReplay, match="add lines"):
        _replay([["a", 0]] * 6)


def test_move_after_win_rejected():
    with pytest.raises(InvalidReplay, match="after the board was cleared"):
        _replay(_copy() + [["a", 10**9]])
