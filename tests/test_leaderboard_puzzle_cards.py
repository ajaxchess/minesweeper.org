"""
tests/test_leaderboard_puzzle_cards.py — Numbers Match and Sudoku on /leaderboard (B60).
"""
import pytest

import database as _db
from database import NumbersMatchScore, SudokuScore
import leaderboard_platform as lp
import main

TODAY = "2026-10-30"
HASH  = "a" * 64


def add(*rows):
    db = _db.SessionLocal()
    try:
        db.add_all(rows)
        db.commit()
    finally:
        db.close()


def nm(name, puzzle_date, score=200, **kw):
    return NumbersMatchScore(name=name, puzzle_date=puzzle_date, score=score, time_secs=100, **kw)


def su(name, difficulty="daily", time_ms=100000, board_hash=HASH):
    return SudokuScore(name=name, difficulty=difficulty, board_hash=board_hash, board_givens="0" * 81,
                       time_ms=time_ms, puzzle_date=TODAY, variant="standard")


def names(leaderboard_id, **kw):
    db = _db.SessionLocal()
    try:
        return [r["name"] for r in lp.leaderboard_rows(db, leaderboard_id, **kw)["rows"]]
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _tables(client):
    """The app's startup creates the tables."""


@pytest.fixture
def new_york_day(monkeypatch):
    monkeypatch.setattr(lp, "numbers_match_today_str", lambda: TODAY)


def test_numbers_match_daily_card_matches_puzzle_ids_with_revision(new_york_day):
    add(nm("Daily", f"{TODAY}-v3"), nm("Easy", f"{TODAY}-easy-v3"))
    assert names("numbers-match") == ["Daily"]


@pytest.mark.parametrize("level", ["easy", "medium", "hard", "expert"])
def test_numbers_match_level_cards(new_york_day, level):
    add(nm("Daily", f"{TODAY}-v3"), nm("Player", f"{TODAY}-{level}-v3"))
    assert names(f"numbers-match-{level}") == ["Player"]


def test_numbers_match_other_days_excluded(new_york_day):
    add(nm("Yesterday", "2026-10-29-v3"))
    assert names("numbers-match") == []


def test_numbers_match_longer_periods_stay_on_their_level(new_york_day):
    add(nm("Daily", f"{TODAY}-v3"), nm("Easy", f"{TODAY}-easy-v3"))
    assert names("numbers-match-easy", period="alltime") == ["Easy"]
    assert names("numbers-match", period="alltime") == ["Daily"]


def test_sudoku_daily_shows_every_player_of_the_shared_board(new_york_day):
    """All players share the Daily's board_hash; one row per board hid all but the first."""
    add(su("Fast", time_ms=90000), su("Slow", time_ms=200000))
    assert names("sudoku-daily") == ["Fast", "Slow"]


@pytest.mark.parametrize("level", ["easy", "medium", "hard", "expert"])
def test_sudoku_level_cards(new_york_day, level):
    add(su("Daily"), su("Player", difficulty=level, board_hash="b" * 64))
    assert names(f"sudoku-{level}") == ["Player"]


def test_cards_use_the_new_york_day_at_night_utc(client, monkeypatch):
    """At 01:00 UTC on the 31st it is still the 30th for both games."""
    monkeypatch.setattr(lp, "numbers_match_today_str", lambda: TODAY)
    add(su("Player"), nm("Player", f"{TODAY}-v3"))
    cards = {c["id"]: c for c in client.get("/api/leaderboards/cards?category=puzzles").json()}
    assert [r["name"] for r in cards["sudoku-daily"]["rows"]] == ["Player"]
    assert [r["name"] for r in cards["numbers-match"]["rows"]] == ["Player"]


def test_guest_archive_keeps_the_current_numbers_match_day(monkeypatch):
    """The job runs at midnight UTC (8 pm New York): today's guest scores must stay."""
    monkeypatch.setattr(main, "numbers_match_today_str", lambda: TODAY)
    add(nm("Today", f"{TODAY}-v3", guest_token="g1"), nm("Old", "2026-10-29-v3", guest_token="g2"))
    main.archive_guest_scores()
    db = _db.SessionLocal()
    try:
        left = [r.name for r in db.query(NumbersMatchScore).all()]
    finally:
        db.close()
    assert left == ["Today"]
