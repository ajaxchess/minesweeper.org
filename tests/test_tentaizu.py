"""
tests/test_tentaizu.py — Tentaizu daily and easy score submission and retrieval.
"""
from conftest import XHR

TODAY = "2026-03-23"

DAILY_SCORE = {"name": "Alice", "puzzle_date": TODAY, "time_secs": 120}
EASY_SCORE  = {"name": "Bob",   "puzzle_date": TODAY, "time_secs": 40}


class TestTentaizuDailyScores:
    def test_submit_returns_201(self, client):
        r = client.post("/api/tentaizu-scores", json=DAILY_SCORE, headers=XHR)
        assert r.status_code == 201

    def test_score_appears_in_leaderboard(self, client):
        client.post("/api/tentaizu-scores", json=DAILY_SCORE, headers=XHR)
        r = client.get(f"/api/tentaizu-scores/{TODAY}")
        assert r.status_code == 200
        assert "Alice" in [s["name"] for s in r.json()]

    def test_leaderboard_ordered_by_time(self, client):
        fast = {**DAILY_SCORE, "name": "Fast", "time_secs": 30}
        slow = {**DAILY_SCORE, "name": "Slow", "time_secs": 300}
        client.post("/api/tentaizu-scores", json=slow, headers=XHR)
        client.post("/api/tentaizu-scores", json=fast, headers=XHR)
        scores = client.get(f"/api/tentaizu-scores/{TODAY}").json()
        times = [s["time_secs"] for s in scores]
        assert times == sorted(times)

    def test_different_dates_are_isolated(self, client):
        client.post("/api/tentaizu-scores", json=DAILY_SCORE, headers=XHR)
        r = client.get("/api/tentaizu-scores/2026-03-24")
        assert r.json() == []


class TestTentaizuEasyScores:
    def test_submit_easy_returns_201(self, client):
        r = client.post("/api/tentaizu-easy-scores", json=EASY_SCORE, headers=XHR)
        assert r.status_code == 201

    def test_easy_and_daily_are_isolated(self, client):
        client.post("/api/tentaizu-easy-scores", json=EASY_SCORE,  headers=XHR)
        client.post("/api/tentaizu-scores",       json=DAILY_SCORE, headers=XHR)
        easy_names  = {s["name"] for s in client.get(f"/api/tentaizu-easy-scores/{TODAY}").json()}
        daily_names = {s["name"] for s in client.get(f"/api/tentaizu-scores/{TODAY}").json()}
        assert "Bob"   in easy_names
        assert "Alice" in daily_names
        assert "Alice" not in easy_names
        assert "Bob"   not in daily_names
