"""
tests/test_msmobile_replay.py — the server replays games recorded from the mobile
app's own game code with the app's rules (F-MS-VERIFY-APP).

tests/fixtures/msmobile_games.json is written by tests/fixtures/gen_msmobile_games.js,
which plays games through mobile/msmobile/src/hooks/useGameState.js. Regenerate it
after changing the app's reducer or gameEngine.js.
"""
import json
import os

import pytest

import database as db_module
import ms_games
import settings as site_settings
from conftest import ROOT, XHR
from database import Score
from minesweeper_engine import ReplayError, decode_board_hash, replay

with open(os.path.join(ROOT, "tests", "fixtures", "msmobile_games.json"), encoding="utf-8") as fh:
    APP_GAMES = json.load(fh)


def _replay(game, **kw):
    mines = decode_board_hash(game["board_hash"], game["rows"], game["cols"])
    assert len(mines) == game["mines"]
    return replay(game["rows"], game["cols"], mines, game["log"], **kw)


def test_fixture_covers_the_app_modes_and_its_rules():
    modes = {g["mode"] for g in APP_GAMES}
    assert modes == {"beginner", "intermediate", "expert"}
    assert any(g["no_guess"] for g in APP_GAMES) and not all(g["no_guess"] for g in APP_GAMES)
    # The app's flood fill opening a flagged cell is the rule most likely to drift.
    assert sum(1 for g in APP_GAMES if g["expected"]["flagged_cells_opened_by_flood_fill"]) >= 3
    assert any(e[1] == "c" for g in APP_GAMES for e in g["log"])


@pytest.mark.parametrize("i", range(len(APP_GAMES)))
def test_app_game_replays_to_the_apps_result(i):
    game = APP_GAMES[i]
    result = _replay(game, app_rules=True)
    exp = game["expected"]
    assert result.last_t_ms == exp["time_ms"]
    assert result.bbbv == exp["bbbv"]
    assert (result.left_clicks, result.right_clicks, result.chord_clicks) == (
        exp["left_clicks"], exp["right_clicks"], exp["chord_clicks"])


def test_website_rules_would_fail_honest_app_games():
    """Why app_rules exists: replayed with the website's rules, some app wins fail."""
    failures = 0
    for game in APP_GAMES:
        try:
            _replay(game)
        except ReplayError:
            failures += 1
    assert failures > 0


def test_app_rules_toggle_flags_without_a_question_mark():
    # Beginner board with the mines in cells 0-9. Tapping (4,4) twice with a long press
    # is flag on, flag off in the app, so one reveal at (8,8) floods the board and wins.
    # On the website the second tap leaves a question mark, which the flood fill skips.
    mines = frozenset(range(10))
    log = [[0, "r", 4, 4], [10, "r", 4, 4], [20, "l", 8, 8]]
    assert replay(9, 9, mines, log, app_rules=True).last_t_ms == 20
    with pytest.raises(ReplayError):
        replay(9, 9, mines, log)


# ── Through the API ────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def enforce_mode(monkeypatch):
    monkeypatch.setattr(site_settings, "SCORE_VERIFICATION_MODE", "enforce")


def _body(game, name, **changes):
    t = game["expected"]["time_ms"]
    body = {
        "name": name, "mode": game["mode"], "rows": game["rows"], "cols": game["cols"],
        "mines": game["mines"], "no_guess": game["no_guess"], "board_hash": game["board_hash"],
        "time_secs": max(1, t // 1000), "time_ms": max(1, t - 40), "bbbv": game["expected"]["bbbv"],
        "log": game["log"], "rules": "msmobile", "chording": True,
        "game_token": ms_games.game_token(age_ms=t + 1000),
    }
    body.update(changes)
    return body


def _stored(name):
    db = db_module.SessionLocal()
    try:
        return db.query(Score).filter(Score.name == name).one()
    finally:
        db.close()


@pytest.mark.parametrize("client_type", ["android_app", "ios_app"])
def test_app_score_with_a_log_is_verified(client, client_type):
    game = next(g for g in APP_GAMES if g["expected"]["flagged_cells_opened_by_flood_fill"])
    name = f"App {client_type[:3]}"
    r = client.post("/api/scores", json=_body(game, name),
                    headers={**XHR, "X-Client-Type": client_type})
    assert r.status_code == 201 and r.json()["listed"] is True, r.text
    s = _stored(name)
    assert s.verification == "verified" and s.client_type == client_type
    assert s.time_ms == game["expected"]["time_ms"]           # the replayed time is kept


def test_app_log_sent_without_app_rules_fails(client):
    game = next(g for g in APP_GAMES if _fails_on_web(g))
    body = _body(game, "NoRules")
    del body["rules"]
    r = client.post("/api/scores", json=body, headers={**XHR, "X-Client-Type": "android_app"})
    assert r.status_code == 201 and r.json()["listed"] is False
    assert _stored("NoRules").verification == "failed"


def test_app_score_without_a_log_still_gets_the_grace_rule(client):
    game = APP_GAMES[0]
    body = _body(game, "OldBuild")
    for k in ("log", "rules", "game_token"):
        body.pop(k)
    r = client.post("/api/scores", json=body, headers={**XHR, "X-Client-Type": "ios_app"})
    assert r.status_code == 201
    assert _stored("OldBuild").verification == "app"


def test_unknown_rules_value_is_rejected(client):
    r = client.post("/api/scores", json=_body(APP_GAMES[0], "Odd", rules="cheat"), headers=XHR)
    assert r.status_code == 422


def _fails_on_web(game):
    try:
        _replay(game)
    except ReplayError:
        return True
    return False
