"""
tests/test_scores.py — Classic Minesweeper score submission and retrieval.
"""
import pytest
import ms_games
from conftest import XHR

BEGINNER_SCORE = {
    "name": "Alice",
    "mode": "beginner",
    "time_secs": 30,
    "time_ms": 30_000,
    "rows": 9,
    "cols": 9,
    "mines": 10,
    "no_guess": False,
    "bbbv": 42,
    "left_clicks": 50,
    "right_clicks": 5,
    "chord_clicks": 0,
}

INTERMEDIATE_SCORE = {**BEGINNER_SCORE, "name": "Bob", "mode": "intermediate",
                      "rows": 16, "cols": 16, "mines": 40, "time_secs": 90}

EXPERT_SCORE = {**BEGINNER_SCORE, "name": "Carol", "mode": "expert",
                "rows": 16, "cols": 30, "mines": 99, "time_secs": 120}


class TestScoreSubmission:
    def test_submit_beginner_score_returns_201(self, client):
        r = client.post("/api/scores", json=BEGINNER_SCORE, headers=XHR)
        assert r.status_code == 201

    def test_submit_intermediate_score_returns_201(self, client):
        r = client.post("/api/scores", json=INTERMEDIATE_SCORE, headers=XHR)
        assert r.status_code == 201

    def test_submit_expert_score_returns_201(self, client):
        r = client.post("/api/scores", json=EXPERT_SCORE, headers=XHR)
        assert r.status_code == 201

    def test_submit_response_body(self, client):
        r = client.post("/api/scores", json=BEGINNER_SCORE, headers=XHR)
        assert r.status_code == 201
        data = r.json()
        assert data.get("ok") is True
        assert isinstance(data.get("id"), int)

    def test_name_is_trimmed_and_sanitized(self, client):
        payload = {**BEGINNER_SCORE, "name": "  Alice  "}
        r = client.post("/api/scores", json=payload, headers=XHR)
        assert r.status_code == 201


class TestScoreRetrieval:
    def test_get_beginner_leaderboard_empty(self, client):
        r = client.get("/api/scores/beginner")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_submitted_score_appears_in_leaderboard(self, client):
        # Use period=alltime to avoid timezone-dependent daily date filter.
        # Only a game the server can replay is listed (F-MS-VERIFY).
        ms_games.post(client, name="Alice")
        r = client.get("/api/scores/beginner?period=alltime")
        assert r.status_code == 200
        names = [s["name"] for s in r.json()]
        assert "Alice" in names

    def test_leaderboard_ordered_by_time(self, client):
        ms_games.post(client, name="Slow", time_ms=120_000)
        ms_games.post(client, name="Fast", time_ms=10_000, mines=list(range(40, 50)))
        r = client.get("/api/scores/beginner?period=alltime")
        scores = r.json()
        assert [(s["name"], s["time_ms"]) for s in scores] == [("Fast", 10_000), ("Slow", 120_000)]

    def test_invalid_mode_returns_error(self, client):
        r = client.get("/api/scores/ultrahard")
        assert r.status_code in (400, 404, 422)

    def test_multiple_modes_are_independent(self, client):
        ms_games.post(client, name="Alice", mode="beginner")
        ms_games.post(client, name="Bob",   mode="intermediate")
        beg = client.get("/api/scores/beginner?period=alltime").json()
        mid = client.get("/api/scores/intermediate?period=alltime").json()
        beg_names = {s["name"] for s in beg}
        mid_names = {s["name"] for s in mid}
        assert "Alice" in beg_names
        assert "Bob"   in mid_names
        assert "Bob"   not in beg_names
        assert "Alice" not in mid_names
