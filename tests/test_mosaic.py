"""
tests/test_mosaic.py — Mosaic daily, easy, and custom-board (F44) score tests.
"""
import hashlib
from conftest import XHR, board_id

TODAY = "2026-03-23"

MOSAIC_SCORE = {"name": "Alice", "puzzle_date": TODAY, "time_secs": 45}
MOSAIC_EASY  = {"name": "Bob",   "puzzle_date": TODAY, "time_secs": 20}

CUSTOM_PAYLOAD = {
    "board_hash": "AAAAgAMHDoAdOwA=",
    "board_mask": "7v///9/9//////7gE=",
    "rows": 9,
    "cols": 9,
    "name": "Alice",
    "time_secs": 38,
}


class TestMosaicDailyScores:
    def test_submit_returns_201(self, client):
        r = client.post("/api/mosaic-scores", json=MOSAIC_SCORE, headers=XHR)
        assert r.status_code == 201

    def test_score_appears_in_leaderboard(self, client):
        client.post("/api/mosaic-scores", json=MOSAIC_SCORE, headers=XHR)
        r = client.get(f"/api/mosaic-scores/{TODAY}")
        assert r.status_code == 200
        names = [s["name"] for s in r.json()]
        assert "Alice" in names

    def test_leaderboard_ordered_by_time(self, client):
        fast = {**MOSAIC_SCORE, "name": "Fast", "time_secs": 10}
        slow = {**MOSAIC_SCORE, "name": "Slow", "time_secs": 90}
        client.post("/api/mosaic-scores", json=slow, headers=XHR)
        client.post("/api/mosaic-scores", json=fast, headers=XHR)
        scores = client.get(f"/api/mosaic-scores/{TODAY}").json()
        times = [s["time_secs"] for s in scores]
        assert times == sorted(times)

    def test_different_dates_are_isolated(self, client):
        other_date = "2026-03-24"
        client.post("/api/mosaic-scores", json=MOSAIC_SCORE, headers=XHR)
        r = client.get(f"/api/mosaic-scores/{other_date}")
        assert r.json() == []


class TestMosaicEasyScores:
    def test_submit_easy_returns_201(self, client):
        r = client.post("/api/mosaic-easy-scores", json=MOSAIC_EASY, headers=XHR)
        assert r.status_code == 201

    def test_easy_and_standard_are_isolated(self, client):
        client.post("/api/mosaic-easy-scores",  json=MOSAIC_EASY,  headers=XHR)
        client.post("/api/mosaic-scores",        json=MOSAIC_SCORE, headers=XHR)
        easy_names = {s["name"] for s in client.get(f"/api/mosaic-easy-scores/{TODAY}").json()}
        std_names  = {s["name"] for s in client.get(f"/api/mosaic-scores/{TODAY}").json()}
        assert "Bob"   in easy_names
        assert "Alice" in std_names
        assert "Bob"   not in std_names
        assert "Alice" not in easy_names


class TestMosaicCustomScores:
    """F44 — per-board leaderboard keyed by (hash, mask)."""

    def test_submit_custom_returns_201(self, client):
        r = client.post("/api/mosaic-custom-scores", json=CUSTOM_PAYLOAD, headers=XHR)
        assert r.status_code == 201

    def test_submit_response_includes_board_id(self, client):
        r = client.post("/api/mosaic-custom-scores", json=CUSTOM_PAYLOAD, headers=XHR)
        data = r.json()
        assert data.get("ok") is True
        assert len(data.get("board_id", "")) == 64  # SHA-256 hex

    def test_board_id_matches_sha256(self, client):
        r = client.post("/api/mosaic-custom-scores", json=CUSTOM_PAYLOAD, headers=XHR)
        returned_id = r.json()["board_id"]
        expected_id = board_id(
            CUSTOM_PAYLOAD["rows"],
            CUSTOM_PAYLOAD["cols"],
            CUSTOM_PAYLOAD["board_hash"],
            CUSTOM_PAYLOAD["board_mask"],
        )
        assert returned_id == expected_id

    def test_score_retrievable_by_board_id(self, client):
        r = client.post("/api/mosaic-custom-scores", json=CUSTOM_PAYLOAD, headers=XHR)
        bid = r.json()["board_id"]
        scores = client.get(f"/api/mosaic-custom-scores/{bid}").json()
        assert len(scores) == 1
        assert scores[0]["name"] == "Alice"

    def test_leaderboard_ordered_by_time(self, client):
        fast = {**CUSTOM_PAYLOAD, "name": "Fast", "time_secs": 5}
        slow = {**CUSTOM_PAYLOAD, "name": "Slow", "time_secs": 99}
        client.post("/api/mosaic-custom-scores", json=slow, headers=XHR)
        client.post("/api/mosaic-custom-scores", json=fast, headers=XHR)
        bid = board_id(CUSTOM_PAYLOAD["rows"], CUSTOM_PAYLOAD["cols"],
                       CUSTOM_PAYLOAD["board_hash"], CUSTOM_PAYLOAD["board_mask"])
        scores = client.get(f"/api/mosaic-custom-scores/{bid}").json()
        times = [s["time_secs"] for s in scores]
        assert times == sorted(times)

    def test_different_masks_have_separate_leaderboards(self, client):
        mask_a = {**CUSTOM_PAYLOAD, "board_mask": "maskAAAA", "name": "Alice"}
        mask_b = {**CUSTOM_PAYLOAD, "board_mask": "maskBBBB", "name": "Bob"}
        r_a = client.post("/api/mosaic-custom-scores", json=mask_a, headers=XHR)
        r_b = client.post("/api/mosaic-custom-scores", json=mask_b, headers=XHR)
        bid_a = r_a.json()["board_id"]
        bid_b = r_b.json()["board_id"]
        assert bid_a != bid_b
        names_a = {s["name"] for s in client.get(f"/api/mosaic-custom-scores/{bid_a}").json()}
        names_b = {s["name"] for s in client.get(f"/api/mosaic-custom-scores/{bid_b}").json()}
        assert names_a == {"Alice"}
        assert names_b == {"Bob"}

    def test_invalid_board_id_returns_400(self, client):
        r = client.get("/api/mosaic-custom-scores/not-a-valid-sha256-hash")
        assert r.status_code == 400

    def test_empty_mask_is_valid(self, client):
        no_mask = {**CUSTOM_PAYLOAD, "board_mask": ""}
        r = client.post("/api/mosaic-custom-scores", json=no_mask, headers=XHR)
        assert r.status_code == 201

    def test_leaderboard_capped_at_20_entries(self, client):
        for i in range(25):
            payload = {**CUSTOM_PAYLOAD, "name": f"Player{i}", "time_secs": i + 1}
            client.post("/api/mosaic-custom-scores", json=payload, headers=XHR)
        bid = board_id(CUSTOM_PAYLOAD["rows"], CUSTOM_PAYLOAD["cols"],
                       CUSTOM_PAYLOAD["board_hash"], CUSTOM_PAYLOAD["board_mask"])
        scores = client.get(f"/api/mosaic-custom-scores/{bid}").json()
        assert len(scores) <= 20
