"""
tests/test_globesweeper.py — Worldsweeper score submission and leaderboard (F55).
"""
from conftest import XHR

# Beginner: GP(1,1) T=3, 32 faces, 4 mines
BEGINNER_SCORE = {
    "name":       "Alice",
    "glob_mode":  "beginner",
    "time_ms":    15_000,
    "t_param":    3,
    "face_count": 32,
    "mines":      4,
}

# Intermediate: GP(2,1) T=7, 72 faces, 8 mines
INTERMEDIATE_SCORE = {
    "name":       "Bob",
    "glob_mode":  "intermediate",
    "time_ms":    45_000,
    "t_param":    7,
    "face_count": 72,
    "mines":      8,
}

# Expert: GP(5,0) T=25, 252 faces, 50 mines
EXPERT_SCORE = {
    "name":       "Carol",
    "glob_mode":  "expert",
    "time_ms":    180_000,
    "t_param":    25,
    "face_count": 252,
    "mines":      50,
}


class TestGlobesweeperPages:
    def test_beginner_page_ok(self, client):
        r = client.get("/worldsweeper")
        assert r.status_code == 200

    def test_intermediate_page_ok(self, client):
        r = client.get("/worldsweeper/intermediate")
        assert r.status_code == 200

    def test_expert_page_ok(self, client):
        r = client.get("/worldsweeper/expert")
        assert r.status_code == 200

    def test_custom_page_ok(self, client):
        r = client.get("/worldsweeper/custom")
        assert r.status_code == 200

    def test_leaderboard_page_ok(self, client):
        r = client.get("/worldsweeper/leaderboard")
        assert r.status_code == 200


class TestGlobesweeperScoreSubmit:
    def test_beginner_submit_returns_201(self, client):
        r = client.post("/api/worldsweeper-scores", json=BEGINNER_SCORE, headers=XHR)
        assert r.status_code == 201

    def test_intermediate_submit_returns_201(self, client):
        r = client.post("/api/worldsweeper-scores", json=INTERMEDIATE_SCORE, headers=XHR)
        assert r.status_code == 201

    def test_expert_submit_returns_201(self, client):
        r = client.post("/api/worldsweeper-scores", json=EXPERT_SCORE, headers=XHR)
        assert r.status_code == 201

    def test_submit_returns_id(self, client):
        r = client.post("/api/worldsweeper-scores", json=BEGINNER_SCORE, headers=XHR)
        body = r.json()
        assert body["ok"] is True
        assert isinstance(body["id"], int)

    def test_submit_with_board_hash(self, client):
        score = {**BEGINNER_SCORE, "board_hash": "AAABBBCCC123"}
        r = client.post("/api/worldsweeper-scores", json=score, headers=XHR)
        assert r.status_code == 201

    def test_custom_mode_submit(self, client):
        score = {
            "name":       "Dave",
            "glob_mode":  "custom",
            "time_ms":    30_000,
            "t_param":    7,
            "face_count": 72,
            "mines":      12,
        }
        r = client.post("/api/worldsweeper-scores", json=score, headers=XHR)
        assert r.status_code == 201


class TestGlobesweeperLeaderboard:
    def test_empty_leaderboard(self, client):
        r = client.get("/api/worldsweeper-scores/beginner")
        assert r.status_code == 200
        assert r.json() == []

    def test_score_appears_in_leaderboard(self, client):
        client.post("/api/worldsweeper-scores", json=BEGINNER_SCORE, headers=XHR)
        r = client.get("/api/worldsweeper-scores/beginner")
        assert r.status_code == 200
        names = [s["name"] for s in r.json()]
        assert "Alice" in names

    def test_leaderboard_sorted_by_time_asc(self, client):
        slow = {**BEGINNER_SCORE, "name": "Slow", "time_ms": 30_000}
        fast = {**BEGINNER_SCORE, "name": "Fast", "time_ms": 5_000}
        client.post("/api/worldsweeper-scores", json=slow, headers=XHR)
        client.post("/api/worldsweeper-scores", json=fast, headers=XHR)
        scores = client.get("/api/worldsweeper-scores/beginner").json()
        names = [s["name"] for s in scores]
        assert names.index("Fast") < names.index("Slow")

    def test_modes_are_independent(self, client):
        client.post("/api/worldsweeper-scores", json=BEGINNER_SCORE,      headers=XHR)
        client.post("/api/worldsweeper-scores", json=INTERMEDIATE_SCORE,  headers=XHR)
        beg_names  = {s["name"] for s in client.get("/api/worldsweeper-scores/beginner").json()}
        int_names  = {s["name"] for s in client.get("/api/worldsweeper-scores/intermediate").json()}
        assert "Alice" in beg_names
        assert "Bob"   in int_names
        assert "Bob"   not in beg_names

    def test_deduplication_keeps_best(self, client):
        """Same player submitting twice — only their best appears once."""
        fast = {**BEGINNER_SCORE, "name": "Alice", "time_ms": 5_000}
        slow = {**BEGINNER_SCORE, "name": "Alice", "time_ms": 30_000}
        client.post("/api/worldsweeper-scores", json=fast, headers=XHR)
        client.post("/api/worldsweeper-scores", json=slow, headers=XHR)
        scores = client.get("/api/worldsweeper-scores/beginner").json()
        alice_scores = [s for s in scores if s["name"] == "Alice"]
        assert len(alice_scores) == 1
        assert alice_scores[0]["time_ms"] == 5_000

    def test_invalid_mode_returns_400(self, client):
        r = client.get("/api/worldsweeper-scores/sphere")
        assert r.status_code == 400


class TestGlobesweeperValidation:
    def test_missing_name_rejected(self, client):
        bad = {k: v for k, v in BEGINNER_SCORE.items() if k != "name"}
        r = client.post("/api/worldsweeper-scores", json=bad, headers=XHR)
        assert r.status_code == 422

    def test_invalid_glob_mode_rejected(self, client):
        bad = {**BEGINNER_SCORE, "glob_mode": "sphere"}
        r = client.post("/api/worldsweeper-scores", json=bad, headers=XHR)
        assert r.status_code == 422

    def test_negative_time_rejected(self, client):
        bad = {**BEGINNER_SCORE, "time_ms": -1}
        r = client.post("/api/worldsweeper-scores", json=bad, headers=XHR)
        assert r.status_code == 422

    def test_too_many_mines_rejected(self, client):
        bad = {**BEGINNER_SCORE, "mines": 32}  # mines >= face_count (32)
        r = client.post("/api/worldsweeper-scores", json=bad, headers=XHR)
        assert r.status_code == 422

    def test_no_csrf_header_rejected(self, client):
        r = client.post("/api/worldsweeper-scores", json=BEGINNER_SCORE)
        assert r.status_code == 403

    def test_blank_name_rejected(self, client):
        bad = {**BEGINNER_SCORE, "name": "   "}
        r = client.post("/api/worldsweeper-scores", json=bad, headers=XHR)
        assert r.status_code == 422
