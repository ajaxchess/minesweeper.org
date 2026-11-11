"""
tests/test_bootcamp_board_hash.py — B68.

The analyzer must read the mine layout the way the browser wrote it
(calcBoardHash() in static/src/js/minesweeper.js: bit i = cell i, least significant
bit first), and the backfill must redo analyses made before that was fixed.
"""
import base64
import json

import pytest

import database as db_module
from database import GameReplay
from phase2_analyzer import ANALYZER_VERSION, GameAnalysis
from phase2_analyzer.pipeline import _decode_board_hash, analyze_replay_async, backfill_analyses


def js_board_hash(rows, cols, mines):
    """Line-for-line port of calcBoardHash()."""
    data = bytearray(-(-rows * cols // 8))
    for idx in mines:
        data[idx >> 3] |= 1 << (idx & 7)
    return base64.b64encode(bytes(data)).decode()


def mine_cells(layout):
    cols = len(layout[0])
    return {r * cols + c for r, row in enumerate(layout) for c, is_mine in enumerate(row) if is_mine}


def test_single_mine_in_the_first_cell():
    # Byte 0 = 0x01: the browser means cell 0, i.e. the top-left corner.
    layout = _decode_board_hash("AQAAAAAAAAAAAAA=", 9, 9)
    assert mine_cells(layout) == {0}


@pytest.mark.parametrize("rows, cols, mines", [
    (9, 9, {0, 7, 8, 9, 40, 72, 80}),
    (16, 16, set(range(0, 256, 7))),
    (16, 30, {1, 29, 30, 239, 240, 479}),
    (5, 7, {6, 13, 34}),              # 35 cells: the last byte is only partly used
])
def test_decodes_the_layout_the_browser_encoded(rows, cols, mines):
    layout = _decode_board_hash(js_board_hash(rows, cols, mines), rows, cols)
    assert (len(layout), len(layout[0])) == (rows, cols)
    assert mine_cells(layout) == mines


# A 2×3 board with the mine in the corner, won in two clicks.
ROWS, COLS, MINES = 2, 3, {0}
LOG = [[0, "l", 0, 2], [800, "l", 1, 0]]


def _add_replay():
    db = db_module.SessionLocal()
    try:
        replay = GameReplay(mode="custom", rows=ROWS, cols=COLS, mines=len(MINES), no_guess=False,
                            board_hash=js_board_hash(ROWS, COLS, MINES), time_ms=800,
                            log_json=json.dumps(LOG), outcome="win", bbbv=2, left_clicks=2,
                            right_clicks=0, chord_clicks=0, guest_token="guest-1")
        db.add(replay)
        db.commit()
        return replay.id
    finally:
        db.close()


def _analysis(replay_id):
    db = db_module.SessionLocal()
    try:
        return db.query(GameAnalysis).filter_by(game_replay_id=replay_id).one_or_none()
    finally:
        db.close()


def _set_version(replay_id, version):
    db = db_module.SessionLocal()
    try:
        db.query(GameAnalysis).filter_by(game_replay_id=replay_id).update({"analyzer_version": version})
        db.commit()
    finally:
        db.close()


def test_new_analysis_is_stamped_with_the_current_version():
    replay_id = _add_replay()
    analyze_replay_async(replay_id, db_module.SessionLocal)
    assert _analysis(replay_id).analyzer_version == ANALYZER_VERSION
    assert ANALYZER_VERSION != "1.0"      # 1.0 analyses used the wrong mine layout


def test_backfill_redoes_analyses_from_an_older_version():
    replay_id = _add_replay()
    analyze_replay_async(replay_id, db_module.SessionLocal)
    _set_version(replay_id, "1.0")

    assert backfill_analyses(db_module.SessionLocal) == 1
    assert _analysis(replay_id).analyzer_version == ANALYZER_VERSION
    assert backfill_analyses(db_module.SessionLocal) == 0     # nothing left to redo


def test_backfill_still_analyzes_replays_that_have_no_analysis():
    replay_id = _add_replay()
    assert _analysis(replay_id) is None
    assert backfill_analyses(db_module.SessionLocal) == 1
    assert _analysis(replay_id).analyzer_version == ANALYZER_VERSION


def test_backfill_ends_when_a_replay_cannot_be_analyzed():
    """A replay that fails every time must not be fetched again and again."""
    db = db_module.SessionLocal()
    db.add(GameReplay(mode="custom", rows=ROWS, cols=COLS, mines=1, board_hash="AQ==",
                      log_json='[["not", "a", "move"]]', outcome="win", guest_token="guest-2"))
    db.commit()
    db.close()
    good = _add_replay()
    assert backfill_analyses(db_module.SessionLocal, batch_size=1) == 1
    assert _analysis(good) is not None
