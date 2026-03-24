"""
tests/test_variants.py — Cylinder, Toroid, and Replay score submission + retrieval.
"""
from conftest import XHR

CYLINDER_SCORE = {
    "name": "Alice",
    "cyl_mode": "easy",
    "time_secs": 25,
    "time_ms": 25_000,
    "rows": 9,
    "cols": 9,
    "mines": 10,
    "no_guess": False,
    "bbbv": 30,
}

TOROID_SCORE = {
    "name": "Bob",
    "tor_mode": "easy",
    "time_secs": 35,
    "time_ms": 35_000,
    "rows": 9,
    "cols": 9,
    "mines": 10,
    "no_guess": False,
    "bbbv": 28,
}

REPLAY_SCORE = {
    "board_hash": "AAABBBCCC123",
    "variant": "standard",
    "name": "Carol",
    "time_secs": 20,
    "time_ms": 20_500,
    "rows": 9,
    "cols": 9,
    "mines": 10,
    "bbbv": 35,
}


class TestCylinderScores:
    def test_submit_returns_201(self, client):
        r = client.post("/api/cylinder-scores", json=CYLINDER_SCORE, headers=XHR)
        assert r.status_code == 201

    def test_score_appears_in_leaderboard(self, client):
        client.post("/api/cylinder-scores", json=CYLINDER_SCORE, headers=XHR)
        r = client.get("/api/cylinder-scores/easy")
        assert r.status_code == 200
        assert "Alice" in [s["name"] for s in r.json()]

    def test_modes_are_independent(self, client):
        expert = {**CYLINDER_SCORE, "name": "Expert", "cyl_mode": "expert",
                  "rows": 16, "cols": 30, "mines": 99}
        client.post("/api/cylinder-scores", json=CYLINDER_SCORE, headers=XHR)
        client.post("/api/cylinder-scores", json=expert,         headers=XHR)
        easy_names   = {s["name"] for s in client.get("/api/cylinder-scores/easy").json()}
        expert_names = {s["name"] for s in client.get("/api/cylinder-scores/expert").json()}
        assert "Alice"  in easy_names
        assert "Expert" in expert_names
        assert "Expert" not in easy_names


class TestToroidScores:
    def test_submit_returns_201(self, client):
        r = client.post("/api/toroid-scores", json=TOROID_SCORE, headers=XHR)
        assert r.status_code == 201

    def test_score_appears_in_leaderboard(self, client):
        client.post("/api/toroid-scores", json=TOROID_SCORE, headers=XHR)
        r = client.get("/api/toroid-scores/easy")
        assert r.status_code == 200
        assert "Bob" in [s["name"] for s in r.json()]


class TestReplayScores:
    def test_submit_returns_201(self, client):
        r = client.post("/api/replay-scores", json=REPLAY_SCORE, headers=XHR)
        assert r.status_code == 201

    def test_score_appears_in_leaderboard(self, client):
        client.post("/api/replay-scores", json=REPLAY_SCORE, headers=XHR)
        r = client.get("/api/replay-scores", params={"board_hash": REPLAY_SCORE["board_hash"]})
        assert r.status_code == 200
        assert "Carol" in [s["name"] for s in r.json()]

    def test_invalid_variant_rejected(self, client):
        bad = {**REPLAY_SCORE, "variant": "sphere"}
        r = client.post("/api/replay-scores", json=bad, headers=XHR)
        assert r.status_code == 422

    def test_cylinder_replay_variant(self, client):
        cyl = {**REPLAY_SCORE, "name": "Dave", "variant": "cylinder"}
        r = client.post("/api/replay-scores", json=cyl, headers=XHR)
        assert r.status_code == 201
