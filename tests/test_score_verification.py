"""
tests/test_score_verification.py — classic scores are listed only after the server
replays them (F-MS-VERIFY).
"""
import json
import os

import pytest

import database as db_module
import ms_games
import settings as site_settings
from conftest import ROOT, XHR
from database import Score

BARE = {   # what a forger (or a browser tab from before the feature) posts
    "name": "Forger", "mode": "beginner", "time_secs": 1, "time_ms": 1,
    "rows": 9, "cols": 9, "mines": 10, "no_guess": False,
}

with open(os.path.join(ROOT, "tests", "fixtures", "minesweeper_js_games.json"), encoding="utf-8") as fh:
    JS_GAMES = json.load(fh)


def listed_names(client, mode="beginner", period="alltime", **params):
    r = client.get(f"/api/scores/{mode}", params={"period": period, **params})
    assert r.status_code == 200
    return [row["name"] for row in r.json()]


def stored(name):
    db = db_module.SessionLocal()
    try:
        return db.query(Score).filter(Score.name == name).one()
    finally:
        db.close()


def post(client, body, **headers):
    return client.post("/api/scores", json=body, headers={**XHR, **headers})


# ── The honest path ───────────────────────────────────────────────────────────

def test_start_returns_a_token_that_is_not_cached(client):
    r = client.post("/api/scores/start", json={}, headers=XHR)
    assert r.status_code == 200
    assert len(r.json()["token"]) > 40
    assert r.headers["cache-control"] == "no-store"


def test_replayed_game_is_listed(client):
    r = ms_games.post(client, name="Alice", time_ms=30_000)
    assert r.status_code == 201 and r.json()["listed"] is True
    assert stored("Alice").verification == "verified"
    assert listed_names(client) == ["Alice"]


@pytest.mark.parametrize("game", [JS_GAMES[0], JS_GAMES[11], JS_GAMES[17], JS_GAMES[-1]],
                         ids=lambda g: g["mode"])
def test_game_recorded_from_the_browser_is_listed(client, game):
    """The exact body minesweeper.js posts, with a real token in place of the stub."""
    body = {**game, "name": "Browser", "time_secs": max(1, game["time_ms"] // 1000),
            "game_token": ms_games.game_token(age_ms=game["time_ms"] + 1000)}
    r = post(client, body)
    assert r.status_code == 201 and r.json()["listed"] is True, r.text
    row = stored("Browser")
    assert row.verification == "verified"
    assert (row.time_ms, row.bbbv) == (game["log"][-1][0], game["bbbv"])
    assert listed_names(client, game["mode"], no_guess=game["no_guess"]) == ["Browser"]


def test_time_3bv_and_clicks_come_from_the_replay_not_the_request(client):
    body = ms_games.submission(name="Liar", time_ms=30_000)
    lies = {"time_ms": 1, "time_secs": 1, "bbbv": 9999, "left_clicks": 1, "right_clicks": 77, "chord_clicks": 88}
    assert post(client, {**body, **lies}).status_code == 201
    row = stored("Liar")
    assert row.verification == "verified"
    assert (row.time_ms, row.time_secs) == (30_000, 30)
    assert row.bbbv == ms_games.engine.compute_3bv(9, 9, frozenset(range(10)))
    assert (row.left_clicks, row.right_clicks, row.chord_clicks) == (len(body["log"]), 0, 0)


# ── Forgeries are saved but never listed ──────────────────────────────────────

def test_score_without_a_log_is_not_listed(client):
    r = post(client, BARE)
    assert r.status_code == 201 and r.json()["listed"] is False
    assert stored("Forger").verification == "unverified"
    for period in ("daily", "weekly", "monthly", "season", "yearly", "alltime"):
        assert listed_names(client, period=period) == []


def test_unlisted_score_is_absent_from_every_public_list(client):
    body = {**BARE, "board_hash": ms_games.board_hash(9, 9, range(10))}
    post(client, body)
    assert "Forger" not in client.get("/api/leaderboards/classic-beginner?period=alltime").text
    assert "Forger" not in client.get("/api/leaderboards/cards?period=alltime").text
    r = client.get("/api/replay-scores", params={"board_hash": body["board_hash"], "variant": "standard"})
    assert r.status_code == 200 and r.json() == []


def _failed(client, name, mines=range(10), **changes):
    body = {**ms_games.submission(name=name, time_ms=30_000, mines=list(mines)), **changes}
    r = post(client, body)
    assert r.status_code == 201 and r.json()["listed"] is False, r.text
    assert stored(name).verification == "failed"
    assert name not in listed_names(client)


def test_log_that_does_not_win_the_board_fails(client):
    _failed(client, "Short", log=ms_games.submission()["log"][:-1])


def test_log_that_reveals_a_mine_fails(client):
    _failed(client, "Boom", log=[[0, "l", 0, 0]])


def test_log_for_another_board_fails(client):
    _failed(client, "Swap", board_hash=ms_games.board_hash(9, 9, range(71, 81)))


def test_mine_count_must_match_the_board(client):
    body = {**ms_games.submission(name="Count"), "mines": 9}
    assert post(client, body).json()["listed"] is False
    assert stored("Count").verification == "failed"


def test_fixed_mode_must_be_played_on_its_own_board(client):
    easy = ms_games.submission(name="Tiny", mode="custom", rows=5, cols=5, mines=[0, 7, 24])
    r = post(client, {**easy, "mode": "expert"})
    assert r.status_code == 201 and stored("Tiny").verification == "failed"


def test_game_cannot_claim_more_time_than_passed_since_its_token(client):
    """A token issued now cannot carry a 30 s game: the log was made up."""
    _failed(client, "Instant", game_token=ms_games.game_token(age_ms=0))


def test_tampered_or_foreign_token_fails(client):
    _failed(client, "Tamper", game_token=ms_games.game_token(age_ms=60_000)[:-2] + "xx")
    # A second board: guests get one score per board, whatever its status.
    _failed(client, "Foreign", mines=range(20, 30), game_token="not-a-token")


def test_expired_token_fails(client):
    _failed(client, "Expired", game_token=ms_games.game_token(age_ms=13 * 3600 * 1000))


def test_token_buys_one_score(client):
    first = ms_games.submission(name="First", time_ms=30_000)
    assert post(client, first).json()["listed"] is True
    second = ms_games.submission(name="Second", time_ms=30_000, mines=list(range(71, 81)))
    r = post(client, {**second, "game_token": first["game_token"]})
    assert r.status_code == 201 and r.json()["listed"] is False
    assert stored("Second").verification == "failed"


@pytest.mark.parametrize("log", [
    [1, 2, 3], [[0, "l", 0]], [[0, "l", True, 0]], [{"t": 0}], [[0, "l", 0, 0, 0]],
    [[[["deep"]]]], [[0, "l", 99, 99]], [["0", "l", "0", "0"]],
])
def test_junk_log_is_a_failed_score_not_a_server_error(client, log):
    _failed(client, "Junk", log=log)


def test_oversized_log_is_rejected_before_it_is_stored(client):
    body = ms_games.submission(name="Huge")
    assert post(client, {**body, "log": [[0, "r", 0, 0]] * 10_001}).status_code == 422


# ── Only leaderboard candidates are replayed ──────────────────────────────────

def _fill_list(client, n=site_settings.SCORE_LIST_SIZE):
    for i in range(n):
        assert ms_games.post(client, name=f"Tester{chr(65 + i)}", time_ms=10_000 + i,
                             mines=list(range(i, i + 10))).json()["listed"] is True


def test_score_beaten_by_a_full_list_is_stored_without_replay(client):
    _fill_list(client)
    r = post(client, {**BARE, "name": "Slow", "time_secs": 99, "time_ms": 99_000, "log": [[0, "l", 0, 0]]})
    assert r.status_code == 201 and r.json()["listed"] is False
    assert stored("Slow").verification == "unchecked"      # the losing log was never replayed
    assert "Slow" not in listed_names(client)


def test_score_that_would_enter_a_full_list_is_replayed(client):
    _fill_list(client)
    assert post(client, {**BARE, "name": "Sneak", "time_ms": 5_000, "time_secs": 5}).status_code == 201
    assert stored("Sneak").verification == "unverified"
    assert ms_games.post(client, name="Champ", time_ms=5_000, mines=list(range(40, 50))).json()["listed"] is True
    assert listed_names(client)[0] == "Champ"


def test_one_player_cannot_fill_the_list_to_shut_others_out(client):
    """Candidates are counted by player: fifteen scores from one player leave room."""
    for i in range(site_settings.SCORE_LIST_SIZE):
        ms_games.post(client, name="Solo", time_ms=10_000 + i, mines=list(range(i, i + 10)))
    assert ms_games.post(client, name="Other", time_ms=50_000, mines=list(range(40, 50))).json()["listed"] is True
    assert "Other" in listed_names(client)


def test_unlisted_scores_do_not_count_against_candidates(client):
    for i in range(site_settings.SCORE_LIST_SIZE):
        post(client, {**BARE, "name": f"F{i:02d}", "time_ms": 1 + i})
    assert ms_games.post(client, name="Honest", time_ms=60_000).json()["listed"] is True
    assert listed_names(client) == ["Honest"]


# ── Mobile app grace rule and the rollout switch ──────────────────────────────

def test_app_score_without_a_log_is_listed_under_the_grace_rule(client):
    r = post(client, {**BARE, "name": "AppUser", "time_ms": 20_000, "time_secs": 20}, **{"X-Client-Type": "ios_app"})
    assert r.json()["listed"] is True
    assert stored("AppUser").verification == "app"
    assert listed_names(client) == ["AppUser"]


def test_app_grace_can_be_switched_off(client, monkeypatch):
    monkeypatch.setattr(site_settings, "SCORE_VERIFICATION_APP_GRACE", False)
    r = post(client, {**BARE, "name": "AppUser"}, **{"X-Client-Type": "android_app"})
    assert r.json()["listed"] is False
    assert stored("AppUser").verification == "unverified"


def test_observe_mode_records_the_outcome_but_lists_everything(client, monkeypatch):
    monkeypatch.setattr(site_settings, "SCORE_VERIFICATION_MODE", "observe")
    assert post(client, BARE).json()["listed"] is True
    assert stored("Forger").verification == "unverified"
    assert listed_names(client) == ["Forger"]


def test_off_mode_changes_nothing(client, monkeypatch):
    monkeypatch.setattr(site_settings, "SCORE_VERIFICATION_MODE", "off")
    assert post(client, BARE).json()["listed"] is True
    assert stored("Forger").verification is None
    assert listed_names(client) == ["Forger"]


def test_scores_saved_before_the_feature_stay_listed(client):
    db = db_module.SessionLocal()
    db.add(Score(name="Veteran", mode="beginner", time_secs=40, time_ms=40_000, rows=9, cols=9, mines=10))
    db.commit()
    db.close()
    assert listed_names(client) == ["Veteran"]


# ── The browser sends what the server needs ───────────────────────────────────

def test_script_sends_token_log_and_chord_setting():
    src = open(os.path.join(ROOT, "static", "src", "js", "minesweeper.js"), encoding="utf-8").read()
    submit = src[src.index("async function submitScore"):]
    submit = submit[:submit.index("\n}\n")]
    for field in ("game_token:", "chording:", "log:"):
        assert field in submit
    assert "state.gameTokenP = fetchGameToken();" in src
    # After the token wait `state` may already be the next game.
    payload = submit[submit.index("const payload = {"):submit.index("};")]
    assert "state." not in payload
