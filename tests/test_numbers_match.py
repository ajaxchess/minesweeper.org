"""
tests/test_numbers_match.py — Numbers Match (F-NM): board generator, puzzle-day
timezone, board/today APIs, score submission + leaderboard ranking, page render,
and the B52 global-name regression.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from conftest import XHR
import database as _db
from database import NumbersMatchScore
import main
import numbers_match_routes
import numbers_match_generator as gen
from numbers_match_generator import (
    NUMBERS_MATCH_BOARD_REVISION,
    NUMBERS_MATCH_TZ_NAME,
    board_number,
    generate_daily,
    numbers_match_today_str,
)
from numbers_match_engine import (
    are_adjacent, board_for_puzzle, can_match, collapse_empty_rows, replay,
)

ROOT  = Path(__file__).resolve().parent.parent
TODAY = "2026-10-11"
REV   = NUMBERS_MATCH_BOARD_REVISION
DAILY_ID = f"{TODAY}-{REV}"


def score(name="Alice", puzzle_date=DAILY_ID, score=200, time_secs=100, **kw):
    return {"name": name, "puzzle_date": puzzle_date, "score": score,
            "time_secs": time_secs, **kw}


# ── Generator ──────────────────────────────────────────────────────────────────

class TestGenerator:
    def test_board_number_epoch(self):
        assert board_number("2024-01-01") == 1
        assert board_number("2024-01-31") == 31

    def test_daily_board_shape(self):
        b = generate_daily(TODAY)
        assert b["rows"] == 4
        assert len(b["board_data"]) == b["rows"] * 9
        assert all(1 <= v <= 9 for v in b["board_data"])
        # 1-9 repeated: every value appears exactly rows times
        assert sorted(b["board_data"]) == sorted(list(range(1, 10)) * b["rows"])

    def test_daily_board_is_deterministic(self):
        assert generate_daily(TODAY) == generate_daily(TODAY)

    def test_revision_suffix_changes_board(self):
        assert generate_daily(TODAY)["board_data"] != generate_daily(TODAY, seed_suffix=f":{REV}")["board_data"]

    def test_different_days_differ(self):
        assert generate_daily(TODAY)["board_data"] != generate_daily("2026-10-12")["board_data"]


# ── Puzzle day / timezone (single source of truth) ────────────────────────────

class TestPuzzleDay:
    def test_timezone_is_new_york(self):
        assert NUMBERS_MATCH_TZ_NAME == "America/New_York"

    @pytest.mark.parametrize("utc_now, expected", [
        # 03:00 UTC is still the previous evening in New York (EDT, UTC-4)
        (datetime(2026, 10, 12, 3, 0, tzinfo=timezone.utc), "2026-10-11"),
        (datetime(2026, 10, 12, 4, 0, tzinfo=timezone.utc), "2026-10-12"),
        # Winter (EST, UTC-5)
        (datetime(2026, 1, 15, 4, 59, tzinfo=timezone.utc), "2026-01-14"),
        (datetime(2026, 1, 15, 5, 0, tzinfo=timezone.utc), "2026-01-15"),
    ])
    def test_today_uses_new_york_date(self, utc_now, expected):
        assert numbers_match_today_str(utc_now) == expected

    def test_main_and_routes_share_the_generator_definitions(self):
        assert main.numbers_match_today_str is gen.numbers_match_today_str
        assert main.NUMBERS_MATCH_TZ is gen.NUMBERS_MATCH_TZ
        assert numbers_match_routes.numbers_match_today_str is gen.numbers_match_today_str
        assert numbers_match_routes.NUMBERS_MATCH_BOARD_REVISION == REV

    def test_no_hardcoded_revision_or_timezone_outside_generator(self):
        for rel in ("main.py", "numbers_match_routes.py", "static/src/js/numbers_match.js"):
            src = (ROOT / rel).read_text(encoding="utf-8")
            assert "NUMBERS_MATCH_BOARD_REVISION =" not in src, rel
            assert "NUMBERS_MATCH_TZ =" not in src, rel
            assert not re.search(r"_serverRevision\s*=\s*'v\d+'", src), rel


# ── Today / board APIs ────────────────────────────────────────────────────────

class TestTodayApi:
    def test_today_endpoint(self, client):
        r = client.get("/api/numbers-match-today")
        assert r.status_code == 200
        assert r.headers["cache-control"] == "no-store"
        assert r.json() == {
            "today":    numbers_match_today_str(),
            "timezone": NUMBERS_MATCH_TZ_NAME,
            "revision": REV,
        }


class TestBoardApi:
    def test_board_with_revision_matches_generator(self, client):
        r = client.get(f"/api/numbers-match-board/{TODAY}?rev={REV}")
        assert r.status_code == 200
        data = r.json()
        expected = generate_daily(TODAY, seed_suffix=f":{REV}")
        assert data["board_data"] == expected["board_data"]
        assert data["rows"] == 4
        assert data["revision"] == REV

    def test_board_without_revision_is_stored_and_stable(self, client):
        first  = client.get(f"/api/numbers-match-board/{TODAY}").json()
        second = client.get(f"/api/numbers-match-board/{TODAY}").json()
        assert first == second
        assert first["board_data"] == generate_daily(TODAY)["board_data"]

    @pytest.mark.parametrize("path", [
        "/api/numbers-match-board/2026-1-1",
        "/api/numbers-match-board/not-a-date",
        f"/api/numbers-match-board/{TODAY}?rev=v2;drop",
        f"/api/numbers-match-board/{TODAY}?rev=latest",
    ])
    def test_board_rejects_bad_input(self, client, path):
        assert client.get(path).status_code == 400


# ── Score submission + leaderboard (F-NM-VERIFY) ──────────────────────────────

_JS = json.loads((ROOT / "tests/fixtures/numbers_match_js_games.json").read_text())
# A short won game from the real web client, re-timed to 160 ms per match so it
# passes the "too fast" check and stays inside the 5 s token tolerance.
_GAME = min((g for g in _JS["games"] if g["won"] and g["puzzle_id"].endswith("-easy-v2")),
            key=lambda g: len(g["moves"]))


def _timed(moves, ms_per_match=160):
    t, out = 0, []
    for m in moves:
        if m[0] == "m":
            t += ms_per_match
        out.append([m[0], t, *m[2:]])
    return out


GAME_ID    = _GAME["puzzle_id"]
GAME_MOVES = _timed(_GAME["moves"])
GAME_SCORE = replay(_GAME["board"], _GAME["rows"], GAME_MOVES).score


def start(client, puzzle_id=GAME_ID):
    r = client.post("/api/numbers-match-start", json={"puzzle_id": puzzle_id}, headers=XHR)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def submit(client, name="Alice", puzzle_id=GAME_ID, moves=GAME_MOVES, token=None, **extra):
    token = token or start(client, puzzle_id)
    body = {"name": name, "puzzle_date": puzzle_id, "game_token": token, "moves": moves, **extra}
    return client.post("/api/numbers-match-scores", json=body, headers=XHR)


def _solve_daily(puzzle_id):
    """Random legal play with the server engine until the daily board is cleared."""
    import random
    board, rows = board_for_puzzle(puzzle_id)
    for seed in range(200):
        rng, b, r, moves, add_left = random.Random(seed), list(board), rows, [], 5
        while any(b):
            pairs = [(i, j) for i in range(len(b)) for j in range(i + 1, len(b))
                     if can_match(b[i], b[j]) and are_adjacent(b, i, j)]
            if not pairs:
                if not add_left:
                    break
                rem = [v for v in b if v]
                rem += [0] * (-len(rem) % 9)
                b, r, add_left = b + rem, r + len(rem) // 9, add_left - 1
                moves.append(["a", 0])
                continue
            i, j = rng.choice(pairs)
            moves.append(["m", 0, i, j])
            b[i] = b[j] = 0
            if any(b):
                b, r = collapse_empty_rows(b, r)
        if not any(b):
            return _timed(moves)
    raise AssertionError("no solution found")


class TestStartToken:
    def test_start_returns_token_for_leaderboard_puzzles(self, client):
        for pid in (f"{TODAY}-{REV}", f"{TODAY}-easy-{REV}", f"{TODAY}-expert-{REV}"):
            assert start(client, pid)

    @pytest.mark.parametrize("pid", [TODAY, f"{TODAY}-easy", "random-abc", f"{TODAY}-insane-{REV}"])
    def test_start_rejects_non_leaderboard_puzzles(self, client, pid):
        r = client.post("/api/numbers-match-start", json={"puzzle_id": pid}, headers=XHR)
        assert r.status_code == 400


class TestVerifiedScores:
    def test_verified_game_is_saved_with_server_values(self, client):
        r = submit(client, score=99999, time_secs=1)          # client claims are ignored
        assert r.status_code == 201, r.text
        assert r.json()["score"] == GAME_SCORE
        rows = client.get(f"/api/numbers-match-scores/{GAME_ID}").json()
        expected_secs = max(1, GAME_MOVES[-1][1] // 1000)
        assert [(s["name"], s["score"], s["time_secs"]) for s in rows] == [("Alice", GAME_SCORE, expected_secs)]

    def test_daily_game_is_verified(self, client, monkeypatch):
        # Longer than the 5 s tolerance at 160 ms per match; allow it since the
        # token is only milliseconds old in a test.
        monkeypatch.setattr(numbers_match_routes, "TIME_TOLERANCE_MS", 10 * 60 * 1000)
        pid = f"{TODAY}-{REV}"
        moves = _solve_daily(pid)
        r = submit(client, puzzle_id=pid, moves=moves)
        assert r.status_code == 201, r.text

    def test_legacy_payload_without_moves_rejected(self, client):
        r = client.post("/api/numbers-match-scores", headers=XHR, json={
            "name": "Old", "puzzle_date": GAME_ID, "score": 200, "time_secs": 100})
        assert r.status_code == 422

    def test_forged_token_rejected(self, client):
        token = start(client)
        r = submit(client, token=token[:-2] + ("aa" if not token.endswith("aa") else "bb"))
        assert r.status_code == 422
        assert "token" in r.json()["detail"]

    def test_token_for_other_puzzle_rejected(self, client):
        token = start(client, f"{TODAY}-easy-{REV}")
        r = submit(client, token=token)
        assert r.status_code == 422
        assert "different puzzle" in r.json()["detail"]

    def test_token_is_single_use(self, client):
        token = start(client)
        assert submit(client, token=token).status_code == 201
        r = submit(client, name="Bob", token=token)
        assert r.status_code == 422
        assert "already submitted" in r.json()["detail"]

    def test_tampered_moves_rejected(self, client):
        moves = [list(m) for m in GAME_MOVES]
        first = next(m for m in moves if m[0] == "m")
        first[3] = first[2]
        r = submit(client, moves=moves)
        assert r.status_code == 422
        assert "could not be verified" in r.json()["detail"]

    def test_unfinished_game_rejected(self, client):
        r = submit(client, moves=GAME_MOVES[:-1])
        assert r.status_code == 422

    def test_claimed_time_longer_than_real_time_rejected(self, client):
        moves = [list(m) for m in GAME_MOVES]
        moves[-1][1] = 10 * 60 * 1000                          # "took 10 minutes", token is seconds old
        r = submit(client, moves=moves)
        assert r.status_code == 422
        assert "longer than the time since" in r.json()["detail"]

    def test_impossibly_fast_game_rejected(self, client):
        r = submit(client, moves=_timed(_GAME["moves"], ms_per_match=10))
        assert r.status_code == 422
        assert "too fast" in r.json()["detail"]

    def test_variants_are_isolated(self, client):
        submit(client, name="Easy")
        other = f"{TODAY}-medium-{REV}"
        assert client.get(f"/api/numbers-match-scores/{other}").json() == []
        assert {s["name"] for s in client.get(f"/api/numbers-match-scores/{GAME_ID}").json()} == {"Easy"}

    def test_one_row_per_name(self, client):
        submit(client, name="Alice")
        submit(client, name="alice ")
        assert len(client.get(f"/api/numbers-match-scores/{GAME_ID}").json()) == 1

    def test_scores_get_rejects_bad_id(self, client):
        assert client.get("/api/numbers-match-scores/garbage").status_code == 400


def test_leaderboard_ranked_by_score_per_second(client):
    # Ranking is computed on stored rows; insert them directly.
    db = _db.SessionLocal()
    try:
        for name, sc, t in [("Slow", 200, 400), ("Big", 300, 100), ("Quick", 200, 50)]:
            db.add(NumbersMatchScore(name=name, puzzle_date=GAME_ID, score=sc, time_secs=t))
        db.commit()
    finally:
        db.close()
    names = [s["name"] for s in client.get(f"/api/numbers-match-scores/{GAME_ID}").json()]
    assert names == ["Quick", "Big", "Slow"]

# ── Page ──────────────────────────────────────────────────────────────────────

class TestPage:
    def test_page_renders_with_server_revision_and_timezone(self, client):
        r = client.get("/numbers-match")
        assert r.status_code == 200
        assert f'data-revision="{REV}"' in r.text
        assert f'data-timezone="{NUMBERS_MATCH_TZ_NAME}"' in r.text
        assert f'data-real-today="{numbers_match_today_str()}"' in r.text

    def test_permalink_renders_requested_day(self, client):
        r = client.get("/numbers-match/2026-05-09")
        assert r.status_code == 200
        assert 'data-today="2026-05-09"' in r.text
        assert f'data-revision="{REV}"' in r.text

    def test_bad_permalink_redirects(self, client):
        r = client.get("/numbers-match/yesterday", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/numbers-match"


# ── B52 regression: no global-name clashes with base.html's deferred scripts ──

_TOP_LEVEL_NAME = re.compile(r"^(?:async\s+)?function\s+(\w+)|^(?:let|const|var|class)\s+(\w+)", re.M)


def _top_level_names(rel: str) -> set[str]:
    src = (ROOT / rel).read_text(encoding="utf-8")
    return {a or b for a, b in _TOP_LEVEL_NAME.findall(src)}


def test_numbers_match_js_has_no_global_name_clash_with_deferred_scripts():
    """base.html loads these with defer, so they run after numbers_match.js and
    overwrite any global function with the same name (B52: startTimer/stopTimer)."""
    base = (ROOT / "templates/base.html").read_text(encoding="utf-8")
    deferred = re.findall(r'<script src="/static/js/(\w+)\.js[^"]*" defer>', base)
    assert "minesweeper" in deferred
    nm = _top_level_names("static/src/js/numbers_match.js")
    for name in deferred:
        clash = nm & _top_level_names(f"static/src/js/{name}.js")
        assert not clash, f"numbers_match.js redeclares {sorted(clash)} from {name}.js"
