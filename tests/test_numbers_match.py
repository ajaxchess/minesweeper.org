"""
tests/test_numbers_match.py — Numbers Match (F-NM): board generator, puzzle-day
timezone, board/today APIs, score submission + leaderboard ranking, page render,
and the B52 global-name regression.
"""
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from conftest import XHR
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


# ── Score submission + leaderboard ────────────────────────────────────────────

class TestScores:
    def test_submit_returns_201_and_keeps_time(self, client):
        r = client.post("/api/numbers-match-scores", json=score(time_secs=187), headers=XHR)
        assert r.status_code == 201
        rows = client.get(f"/api/numbers-match-scores/{DAILY_ID}").json()
        assert [(s["name"], s["time_secs"]) for s in rows] == [("Alice", 187)]

    def test_zero_time_rejected(self, client):
        r = client.post("/api/numbers-match-scores", json=score(time_secs=0), headers=XHR)
        assert r.status_code == 422

    @pytest.mark.parametrize("pid", [
        f"{TODAY}-easy-{REV}", f"{TODAY}-medium-{REV}",
        f"{TODAY}-hard-{REV}", f"{TODAY}-expert-{REV}", TODAY,
    ])
    def test_difficulty_puzzle_ids_accepted(self, client, pid):
        r = client.post("/api/numbers-match-scores", json=score(puzzle_date=pid), headers=XHR)
        assert r.status_code == 201

    @pytest.mark.parametrize("pid", [f"{TODAY}-insane-{REV}", "2026/10/11", f"{TODAY}-v2x"])
    def test_bad_puzzle_id_rejected(self, client, pid):
        r = client.post("/api/numbers-match-scores", json=score(puzzle_date=pid), headers=XHR)
        assert r.status_code == 422

    def test_variants_are_isolated(self, client):
        client.post("/api/numbers-match-scores", json=score(name="Daily"), headers=XHR)
        client.post("/api/numbers-match-scores",
                    json=score(name="Easy", puzzle_date=f"{TODAY}-easy-{REV}"), headers=XHR)
        daily = {s["name"] for s in client.get(f"/api/numbers-match-scores/{DAILY_ID}").json()}
        easy  = {s["name"] for s in client.get(f"/api/numbers-match-scores/{TODAY}-easy-{REV}").json()}
        assert daily == {"Daily"}
        assert easy == {"Easy"}

    def test_ranked_by_score_per_second(self, client):
        # ratios: Quick 200/50=4.0, Big 300/100=3.0, Slow 200/400=0.5
        for name, sc, t in [("Slow", 200, 400), ("Big", 300, 100), ("Quick", 200, 50)]:
            client.post("/api/numbers-match-scores", json=score(name=name, score=sc, time_secs=t), headers=XHR)
        names = [s["name"] for s in client.get(f"/api/numbers-match-scores/{DAILY_ID}").json()]
        assert names == ["Quick", "Big", "Slow"]

    def test_one_row_per_name(self, client):
        client.post("/api/numbers-match-scores", json=score(name="Alice", time_secs=50), headers=XHR)
        client.post("/api/numbers-match-scores", json=score(name="alice ", time_secs=500), headers=XHR)
        rows = client.get(f"/api/numbers-match-scores/{DAILY_ID}").json()
        assert len(rows) == 1
        assert rows[0]["time_secs"] == 50

    def test_scores_get_rejects_bad_id(self, client):
        assert client.get("/api/numbers-match-scores/garbage").status_code == 400


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
