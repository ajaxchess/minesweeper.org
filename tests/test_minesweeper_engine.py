"""
tests/test_minesweeper_engine.py — server replay of classic Minesweeper (F-MS-VERIFY).

Two kinds of test:
  * parity — games recorded from the real static/src/js/minesweeper.js
    (tests/fixtures/gen_minesweeper_js_games.js) must replay to the same result;
  * rules — each click rule the engine shares with the browser, on tiny boards.
"""
import json
import os

import pytest

from conftest import ROOT
from minesweeper_engine import ReplayError, compute_3bv, decode_board_hash, replay
from ms_games import board_hash

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "minesweeper_js_games.json")
with open(FIXTURE, encoding="utf-8") as fh:
    JS_GAMES = json.load(fh)


def _replay_js(game, **overrides):
    mines = decode_board_hash(game["board_hash"], game["rows"], game["cols"])
    kwargs = {"chording": game["chording"], "evil": game["mode"] == "evil", **overrides}
    return mines, replay(game["rows"], game["cols"], mines, game["log"], **kwargs)


# ── Parity with the browser ───────────────────────────────────────────────────

def test_fixture_covers_every_mode_and_setting():
    assert len(JS_GAMES) >= 30
    assert {g["mode"] for g in JS_GAMES} == {"beginner", "intermediate", "expert", "custom", "evil"}
    assert {g["chording"] for g in JS_GAMES} == {True, False}
    kinds = {entry[1] for g in JS_GAMES for entry in g["log"]}
    assert kinds == {"l", "r", "c"}


def test_fixture_is_what_the_script_posts():
    """The fixture is the body minesweeper.js sends, so these keys are the contract."""
    for game in JS_GAMES:
        assert {"log", "game_token", "chording", "board_hash", "time_ms"} <= set(game)


@pytest.mark.parametrize("game", JS_GAMES, ids=lambda g: f"{g['mode']}-{g['board_hash'][:8]}")
def test_browser_game_replays_to_the_same_result(game):
    mines, result = _replay_js(game)
    assert len(mines) == game["mines"]
    assert result.last_t_ms == game["log"][-1][0]
    assert result.bbbv == game["bbbv"]
    assert (result.left_clicks, result.right_clicks, result.chord_clicks) == (
        game["left_clicks"], game["right_clicks"], game["chord_clicks"])


def test_chord_setting_changes_the_outcome():
    """Games played with chording off contain double-clicks that did nothing; replayed
    with chording on, some of them must go wrong — the setting is part of the rules."""
    off = [g for g in JS_GAMES if not g["chording"]]
    broken = 0
    for game in off:
        try:
            _replay_js(game, chording=True)
        except ReplayError:
            broken += 1
    assert off and broken > 0


@pytest.mark.parametrize("game", JS_GAMES[:8], ids=lambda g: g["board_hash"][:8])
def test_truncated_browser_game_is_not_a_win(game):
    mines = decode_board_hash(game["board_hash"], game["rows"], game["cols"])
    with pytest.raises(ReplayError, match="does not clear"):
        replay(game["rows"], game["cols"], mines, game["log"][:-1],
               chording=game["chording"], evil=game["mode"] == "evil")


# ── Rules on tiny boards ──────────────────────────────────────────────────────
#   WIDE (3×4)      CORNER (2×3)
#   . . . *         * 1 .
#   . . 1 1         1 1 .
#   . . . .
WIDE   = (3, 4, frozenset({3}))
CORNER = (2, 3, frozenset({0}))


def play(board, moves, **kwargs):
    rows, cols, mines = board
    return replay(rows, cols, mines, [[i * 100, kind, r, c] for i, (kind, r, c) in enumerate(moves)], **kwargs)


def test_one_opening_can_win_the_board():
    result = play(WIDE, [("l", 0, 0)])
    assert (result.left_clicks, result.right_clicks, result.chord_clicks) == (1, 0, 0)
    assert result.bbbv == 1 and result.last_t_ms == 0


def test_revealing_a_mine_is_rejected():
    with pytest.raises(ReplayError, match="mine was revealed"):
        play(WIDE, [("l", 0, 3)])


def test_moves_after_the_win_are_rejected():
    with pytest.raises(ReplayError, match="after the game was won"):
        play(WIDE, [("l", 0, 0), ("l", 1, 1)])


def test_flag_blocks_a_click_and_an_opening():
    # (2,3) is flagged: the opening skips it and clicking it does nothing.
    with pytest.raises(ReplayError, match="does not clear"):
        play(WIDE, [("r", 2, 3), ("l", 0, 0), ("l", 2, 3)])


def test_question_mark_blocks_an_opening_but_not_a_click():
    result = play(WIDE, [("r", 2, 3), ("r", 2, 3), ("l", 0, 0), ("l", 2, 3)])
    assert result.right_clicks == 2 and result.left_clicks == 2


def test_third_right_click_clears_the_mark():
    assert play(WIDE, [("r", 2, 3), ("r", 2, 3), ("r", 2, 3), ("l", 0, 0)]).right_clicks == 3


def test_right_click_on_a_revealed_cell_does_nothing():
    # (0,2) is revealed by the opening; right-clicking it must not count as a flag for the chord.
    with pytest.raises(ReplayError, match="does not clear"):
        play(CORNER, [("l", 0, 2), ("r", 0, 1), ("c", 1, 1)])


def test_chord_reveals_when_flags_match_the_number():
    result = play(CORNER, [("l", 0, 2), ("r", 0, 0), ("c", 1, 1)])
    assert result.chord_clicks == 1


def test_chord_does_nothing_without_the_flag():
    with pytest.raises(ReplayError, match="does not clear"):
        play(CORNER, [("l", 0, 2), ("c", 1, 1)])


def test_chord_does_nothing_when_chording_is_off():
    with pytest.raises(ReplayError, match="does not clear"):
        play(CORNER, [("l", 0, 2), ("r", 0, 0), ("c", 1, 1)], chording=False)


def test_chord_on_a_wrong_flag_reveals_the_mine():
    with pytest.raises(ReplayError, match="mine was revealed"):
        play(CORNER, [("l", 0, 2), ("r", 1, 0), ("c", 1, 1)])


def test_question_mark_does_not_count_as_a_flag_for_a_chord():
    with pytest.raises(ReplayError, match="does not clear"):
        play(CORNER, [("l", 0, 2), ("r", 0, 0), ("r", 0, 0), ("c", 1, 1)])


def test_evil_ignores_clicks_before_the_top_right_cell():
    moves = [("l", 0, 0), ("l", 0, 2), ("l", 1, 0)]   # the first click is on the mine
    assert play(CORNER, moves, evil=True).left_clicks == 3
    with pytest.raises(ReplayError, match="mine was revealed"):
        play(CORNER, moves, evil=False)


def test_3bv_counts_openings_and_isolated_numbers():
    assert compute_3bv(*WIDE) == 1
    assert compute_3bv(*CORNER) == 2      # one opening + the isolated 1 at (1,0)


# ── Malformed input never passes and never crashes ───────────────────────────

@pytest.mark.parametrize("log, message", [
    ([],                                   "empty"),
    (None,                                 "empty"),
    ("llll",                               "empty"),
    ([[0, "l", 0]],                        r"\[t_ms, type, row, col\]"),
    (["l"],                                r"\[t_ms, type, row, col\]"),
    ([[0, "x", 0, 0]],                     "unknown action"),
    ([[0, ["l"], 0, 0]],                   "unknown action"),
    ([[0, "l", 3, 0]],                     "off the board"),
    ([[0, "l", 0, -1]],                    "off the board"),
    ([[0.5, "l", 0, 0]],                   "integers"),
    ([[0, "l", True, 0]],                  "integers"),
    ([[0, "l", "0", 0]],                   "integers"),
    ([[500, "r", 2, 3], [100, "l", 0, 0]], "backwards"),
    ([[0, "r", 2, 3]] * 10_001,            "too long"),
])
def test_malformed_log_is_rejected(log, message):
    with pytest.raises(ReplayError, match=message):
        replay(*WIDE, log)


def test_board_hash_round_trips():
    rows, cols, mines = 9, 9, frozenset({0, 8, 40, 80})
    assert decode_board_hash(board_hash(rows, cols, mines), rows, cols) == mines


@pytest.mark.parametrize("bad, message", [
    ("not base64!!",                      "not base64"),
    (board_hash(9, 9, {0}),               "board size"),     # 11 bytes, a 5×5 board needs 4
    ("/w==" * 1,                          "board size"),
    (board_hash(5, 5, {31}),              "outside the board"),
])
def test_bad_board_hash_is_rejected(bad, message):
    with pytest.raises(ReplayError, match=message):
        decode_board_hash(bad, 5, 5)
