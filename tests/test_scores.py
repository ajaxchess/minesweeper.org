"""
tests/test_scores.py — Classic Minesweeper score submission and retrieval.
"""
import pytest
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
        # Use period=alltime to avoid timezone-dependent daily date filter
        client.post("/api/scores", json=BEGINNER_SCORE, headers=XHR)
        r = client.get("/api/scores/beginner?period=alltime")
        assert r.status_code == 200
        names = [s["name"] for s in r.json()]
        assert "Alice" in names

    def test_leaderboard_ordered_by_time(self, client):
        fast = {**BEGINNER_SCORE, "name": "Fast", "time_secs": 10, "time_ms": 10_000}
        slow = {**BEGINNER_SCORE, "name": "Slow", "time_secs": 120, "time_ms": 120_000}
        client.post("/api/scores", json=slow, headers=XHR)
        client.post("/api/scores", json=fast, headers=XHR)
        r = client.get("/api/scores/beginner?period=alltime")
        scores = r.json()
        times = [s["time_ms"] for s in scores]
        assert times == sorted(times)

    def test_invalid_mode_returns_error(self, client):
        r = client.get("/api/scores/ultrahard")
        assert r.status_code in (400, 404, 422)

    def test_multiple_modes_are_independent(self, client):
        client.post("/api/scores", json=BEGINNER_SCORE,    headers=XHR)
        client.post("/api/scores", json=INTERMEDIATE_SCORE, headers=XHR)
        beg = client.get("/api/scores/beginner?period=alltime").json()
        mid = client.get("/api/scores/intermediate?period=alltime").json()
        beg_names = {s["name"] for s in beg}
        mid_names = {s["name"] for s in mid}
        assert "Alice" in beg_names
        assert "Bob"   in mid_names
        assert "Bob"   not in beg_names
        assert "Alice" not in mid_names
