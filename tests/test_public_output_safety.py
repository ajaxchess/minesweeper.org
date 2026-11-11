"""
tests/test_public_output_safety.py — B66 / B67.

B66: public JSON APIs must never return a player's email address.
B67: user-supplied strings (score names, Sudoku board hashes, display names) must
     be escaped before they reach innerHTML on leaderboard pages.
"""
import glob
import hashlib
import os
import re

import pytest

import database as db_module
from conftest import ROOT, XHR
from database import GameMode, MeowdokuScore, PvpResult, Score, UserProfile

EMAIL = "private.player@example.com"
BOARD = "AAECAwQFBgcICQo="


def _add(*rows):
    db = db_module.SessionLocal()
    try:
        db.add_all(rows)
        db.commit()
    finally:
        db.close()


def _score(name="Alice", time_secs=30, **extra):
    return Score(name=name, user_email=EMAIL, mode=GameMode.beginner, time_secs=time_secs,
                 time_ms=time_secs * 1000, rows=9, cols=9, mines=10, no_guess=False, **extra)


# ── B66: no emails in public responses ────────────────────────────────────────

def test_classic_scores_do_not_return_email(client):
    _add(_score())
    r = client.get("/api/scores/beginner?period=alltime")
    assert r.status_code == 200
    rows = r.json()
    assert [row["name"] for row in rows] == ["Alice"]
    assert "user_email" not in rows[0]
    assert EMAIL not in r.text


def test_board_scores_dedup_by_account_without_returning_email(client):
    """The per-board list keeps one row per account (keyed by email server-side)."""
    _add(_score(name="Alice", time_secs=30, board_hash=BOARD),
         _score(name="Alice renamed", time_secs=40, board_hash=BOARD),
         UserProfile(email=EMAIL, display_name="Alice", public_id="pub-1", is_public=True))
    r = client.get("/api/replay-scores", params={"board_hash": BOARD, "variant": "standard"})
    assert r.status_code == 200
    rows = r.json()
    assert [row["name"] for row in rows] == ["Alice"]
    assert rows[0]["profile_url"] == "/u/pub-1"
    assert "user_email" not in rows[0]
    assert EMAIL not in r.text


def test_meowdoku_scores_do_not_return_email(client):
    _add(MeowdokuScore(name="Alice", user_email=EMAIL, puzzle_date="2026-11-10",
                       grid_size=8, time_secs=90, board_hash="abc"))
    r = client.get("/api/meowdoku-scores/2026-11-10?size=8")
    assert r.status_code == 200
    assert [row["name"] for row in r.json()] == ["Alice"]
    assert EMAIL not in r.text


@pytest.mark.parametrize("path", ["/api/pvp/leaderboard", "/api/pvp/rankings"])
def test_pvp_lists_do_not_return_email(client, path):
    _add(PvpResult(winner_name="Alice", winner_email=EMAIL, loser_name="Bob",
                   loser_email="bob.private@example.com", elapsed_ms=45_000,
                   submode="standard", rows=16, cols=16, mines=40),
         UserProfile(email=EMAIL, display_name="Alice", public_id="pub-1", is_public=True))
    r = client.get(path, params={"period": "alltime"})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert "email" not in rows[0] and "winner_email" not in rows[0]
    assert "@example.com" not in r.text


def test_pvp_rankings_still_link_the_public_profile(client):
    _add(PvpResult(winner_name="Alice", winner_email=EMAIL, loser_name="Bob", elapsed_ms=45_000,
                   submode="standard", rows=16, cols=16, mines=40),
         UserProfile(email=EMAIL, display_name="Alice", public_id="pub-1", is_public=True))
    row = client.get("/api/pvp/rankings?period=alltime").json()[0]
    assert row["wins"] == 1
    assert row["profile_url"] == "/u/pub-1"


# ── B67: Sudoku board hash is a sha256 hex digest, nothing else ───────────────

GIVENS = "530070000600195000098000060800060003400803001700020006060000280000419005000080079"


def _sudoku_payload(board_hash):
    return {"name": "Alice", "puzzle_date": "2026-10-11", "difficulty": "daily",
            "board_hash": board_hash, "board_givens": GIVENS, "time_ms": 123456, "hints_used": 0}


@pytest.mark.parametrize("bad_hash", [
    ('"><img src=x onerror=alert(1)>' + "a" * 64)[:64],
    "A" * 64,            # uppercase is not what the client or the generator produce
    "g" * 64,            # not hex
    "a" * 63,
])
def test_sudoku_rejects_non_sha256_board_hash(client, bad_hash):
    r = client.post("/api/sudoku-scores", json=_sudoku_payload(bad_hash), headers=XHR)
    assert r.status_code == 422


def test_sudoku_accepts_sha256_board_hash(client):
    good = hashlib.sha256(GIVENS.encode()).hexdigest()
    r = client.post("/api/sudoku-scores", json=_sudoku_payload(good), headers=XHR)
    assert r.status_code == 201, r.text


# ── B67: no user-supplied field is interpolated into HTML unescaped ───────────

_USER_FIELDS = r"(?:name|display_name|winner_name|loser_name|player_name|fan_flag_name)"
_UNESCAPED = re.compile(
    r"\$\{\s*[A-Za-z_]\w?\." + _USER_FIELDS + r"\s*\}"           # `${s.name}`
    r"|['\"`]\s*\+\s*[A-Za-z_]\w?\." + _USER_FIELDS + r"\s*\+\s*['\"`]"  # '…' + s.name + '…'
    r"|:\s*[A-Za-z_]\w?\.name\s*\)\s*;"                           # ? link : s.name);
)

_RENDER_FILES = sorted(
    glob.glob(os.path.join(ROOT, "templates", "*.html"))
    + glob.glob(os.path.join(ROOT, "static", "src", "js", "*.js"))
)


def test_render_file_list_is_not_empty():
    assert len(_RENDER_FILES) > 50


@pytest.mark.parametrize("path", _RENDER_FILES, ids=lambda p: os.path.relpath(p, ROOT))
def test_no_unescaped_user_field_in_markup(path):
    with open(path, encoding="utf-8") as fh:
        hits = [f"{n}: {line.strip()[:120]}" for n, line in enumerate(fh, 1) if _UNESCAPED.search(line)]
    assert not hits, "user-supplied field reaches HTML without escHtml():\n" + "\n".join(hits)


def test_unescaped_pattern_catches_the_original_bugs():
    """Guard the guard: the three shapes that shipped in B67 must all match."""
    assert _UNESCAPED.search("<td>${s.name}</td>")
    assert _UNESCAPED.search("? '<a href=\"' + s.profile_url + '\">' + s.name + '</a>'")
    assert _UNESCAPED.search("          : s.name);")
    assert _UNESCAPED.search("<td>${r.display_name}</td>")
    assert not _UNESCAPED.search("<td>${escHtml(s.name)}</td>")
    assert not _UNESCAPED.search("          : escHtml(s.name));")


@pytest.mark.parametrize("template", ["sudoku_scores.html"])
def test_sudoku_scores_escapes_board_hash(template):
    src = open(os.path.join(ROOT, "templates", template), encoding="utf-8").read()
    assert "${r.board_hash}" not in src and "${r.full_hash}" not in src
    assert "escHtml(r.board_hash)" in src and "encodeURIComponent(r.full_hash)" in src
