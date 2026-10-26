"""
tests/test_sudoku.py — Sudoku score API: assists bitmask (F-SUDOKU-ASSISTS),
page controls, and pre-generated puzzle serving (F-SUDOKU-GRADING).
"""
import hashlib

import pytest

from conftest import XHR

GIVENS = "530070000600195000098000060800060003400803001700020006060000280000419005000080079"
TODAY  = "2026-10-11"


def payload(name="Alice", givens=GIVENS, **extra):
    return {"name": name, "puzzle_date": TODAY, "difficulty": "daily",
            "board_hash": hashlib.sha256(givens.encode()).hexdigest(),
            "board_givens": givens, "time_ms": 123456, "hints_used": 0, **extra}


def scores(client):
    r = client.get("/api/sudoku-scores", params={"difficulty": "daily", "period": "today", "puzzle_date": TODAY})
    assert r.status_code == 200
    return r.json()


@pytest.mark.parametrize("assists", [0, 1, 2, 3])
def test_assists_stored_and_returned(client, assists):
    r = client.post("/api/sudoku-scores", json=payload(assists=assists), headers=XHR)
    assert r.status_code == 201, r.text
    assert [s["assists"] for s in scores(client)] == [assists]


def test_assists_default_to_zero_for_older_clients(client):
    assert client.post("/api/sudoku-scores", json=payload(), headers=XHR).status_code == 201
    assert scores(client)[0]["assists"] == 0


@pytest.mark.parametrize("bad", [-1, 4, 99])
def test_invalid_assists_rejected(client, bad):
    r = client.post("/api/sudoku-scores", json=payload(assists=bad), headers=XHR)
    assert r.status_code == 422


class _FrozenNow:
    """01:22 UTC on 2026-10-12 is still 21:22 on 2026-10-11 in New York (B55)."""
    @staticmethod
    def now(tz=None):
        from datetime import datetime, timezone
        return datetime(2026, 10, 12, 1, 22, tzinfo=timezone.utc).astimezone(tz)


@pytest.mark.parametrize("path", ["/other/sudoku/daily", "/other/sudoku/easy", "/other/sudoku/scores"])
def test_sudoku_day_is_new_york_not_utc(client, monkeypatch, path):
    import numbers_match_generator
    monkeypatch.setattr(numbers_match_generator, "datetime", _FrozenNow)
    r = client.get(path)
    assert r.status_code == 200
    assert '"2026-10-11"' in r.text
    assert '"2026-10-12"' not in r.text


def test_sudoku_routes_never_use_server_date():
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent / "sudoku_routes.py").read_text(encoding="utf-8")
    assert "date.today()" not in src


def test_play_page_has_mode_tabs_and_options(client):
    r = client.get("/other/sudoku/easy")
    assert r.status_code == 200
    for el_id in ("su-mode-normal", "su-mode-notes", "su-opt-auto-check",
                  "su-opt-auto-candidates", "su-opt-conflicts"):
        assert f'id="{el_id}"' in r.text


def test_spanish_labels_match_la_nacion_wording(client):
    r = client.get("/other/sudoku/easy?lang=es", follow_redirects=True)
    assert r.status_code == 200
    for label in ("Posibles", "Autocontrol", "Posibles automáticos", "Conflictos"):
        assert label in r.text


# ── F-SUDOKU-GRADING: pre-generated puzzle serving ───────────────────────────

def test_daily_serves_pregenerated_puzzle_when_available(client):
    """When a daily puzzle exists in the pool, the route serves its givens."""
    from database import get_db, SudokuPuzzle
    db = next(get_db())
    puzzle = SudokuPuzzle(
        difficulty="daily", givens=GIVENS,
        solution="5" * 81, board_hash=hashlib.sha256(GIVENS.encode()).hexdigest(),
        givens_count=30, hardest_technique="Hidden Single",
        puzzle_date=TODAY,
    )
    db.add(puzzle)
    db.commit()

    import numbers_match_generator
    class _Frozen:
        @staticmethod
        def now(tz=None):
            from datetime import datetime, timezone
            return datetime(2026, 10, 12, 1, 22, tzinfo=timezone.utc).astimezone(tz)
    import unittest.mock
    with unittest.mock.patch.object(numbers_match_generator, "datetime", _Frozen):
        r = client.get("/other/sudoku/daily")
    assert r.status_code == 200
    assert GIVENS in r.text
    assert "seed" not in r.text or "null" in r.text


def test_easy_serves_pregenerated_puzzle(client):
    """When pool puzzles exist, a non-daily route serves one."""
    from database import get_db, SudokuPuzzle
    db = next(get_db())
    puzzle = SudokuPuzzle(
        difficulty="easy", givens=GIVENS,
        solution="5" * 81, board_hash=hashlib.sha256(GIVENS.encode()).hexdigest(),
        givens_count=30, hardest_technique="Naked Single",
    )
    db.add(puzzle)
    db.commit()

    r = client.get("/other/sudoku/easy")
    assert r.status_code == 200
    assert GIVENS in r.text


def test_fallback_to_seed_when_no_pool(client):
    """When the pool is empty, routes fall back to client-side seed generation."""
    r = client.get("/other/sudoku/hard")
    assert r.status_code == 200
    # Should have a numeric seed, not null
    assert "seed:" in r.text or "seed :" in r.text


def test_served_count_incremented(client):
    """Non-daily puzzles increment served_count on each fetch."""
    from database import get_db, SudokuPuzzle
    db = next(get_db())
    bh = hashlib.sha256(b"test-served-count").hexdigest()
    puzzle = SudokuPuzzle(
        difficulty="medium", givens=GIVENS,
        solution="5" * 81, board_hash=bh,
        givens_count=28, hardest_technique="Naked Pair",
        served_count=0,
    )
    db.add(puzzle)
    db.commit()
    puzzle_id = puzzle.id

    client.get("/other/sudoku/medium")
    db.expire_all()
    updated = db.get(SudokuPuzzle, puzzle_id)
    assert updated.served_count == 1


# ── F-GAME-END + F-SUDOKU-GRADING: graded puzzle for the in-page next game ────

def test_next_puzzle_api_serves_pool_puzzle(client):
    from database import get_db, SudokuPuzzle
    db = next(get_db())
    db.add(SudokuPuzzle(difficulty="hard", givens=GIVENS, solution="5" * 81,
                        board_hash=hashlib.sha256(b"next-hard").hexdigest(),
                        givens_count=24, hardest_technique="X-Wing", served_count=0))
    db.commit()
    r = client.get("/api/sudoku-puzzle", params={"difficulty": "hard"})
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    assert r.json() == {"difficulty": "hard", "givens": GIVENS}
    assert db.query(SudokuPuzzle).filter_by(difficulty="hard").one().served_count == 1


def test_next_puzzle_api_empty_pool_returns_null(client):
    r = client.get("/api/sudoku-puzzle", params={"difficulty": "expert"})
    assert r.status_code == 200
    assert r.json()["givens"] is None


@pytest.mark.parametrize("bad", ["daily", "insane", ""])
def test_next_puzzle_api_rejects_daily_and_unknown(client, bad):
    assert client.get("/api/sudoku-puzzle", params={"difficulty": bad}).status_code == 400
