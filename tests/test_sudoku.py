"""
tests/test_sudoku.py — Sudoku score API: assists bitmask (F-SUDOKU-ASSISTS) and page controls.
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
