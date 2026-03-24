"""
tests/test_validation.py — Pydantic input validation for all score endpoints.

All invalid payloads must return 422 Unprocessable Entity, not 500.
"""
from conftest import XHR

BASE_SCORE = {
    "name": "Alice",
    "mode": "beginner",
    "time_secs": 30,
    "rows": 9,
    "cols": 9,
    "mines": 10,
}


class TestClassicScoreValidation:
    def test_missing_required_field_returns_422(self, client):
        bad = {k: v for k, v in BASE_SCORE.items() if k != "name"}
        r = client.post("/api/scores", json=bad, headers=XHR)
        assert r.status_code == 422

    def test_invalid_mode_returns_422(self, client):
        r = client.post("/api/scores", json={**BASE_SCORE, "mode": "ultra"}, headers=XHR)
        assert r.status_code == 422

    def test_time_below_minimum_returns_422(self, client):
        r = client.post("/api/scores", json={**BASE_SCORE, "time_secs": 0}, headers=XHR)
        assert r.status_code == 422

    def test_time_above_maximum_returns_422(self, client):
        r = client.post("/api/scores", json={**BASE_SCORE, "time_secs": 1000}, headers=XHR)
        assert r.status_code == 422

    def test_empty_name_returns_422(self, client):
        r = client.post("/api/scores", json={**BASE_SCORE, "name": "   "}, headers=XHR)
        assert r.status_code == 422

    def test_too_many_mines_returns_422(self, client):
        # 9×9 = 81 cells; 85% max = 68 mines; 80 exceeds that
        r = client.post("/api/scores", json={**BASE_SCORE, "mines": 80}, headers=XHR)
        assert r.status_code == 422

    def test_rows_below_minimum_returns_422(self, client):
        r = client.post("/api/scores", json={**BASE_SCORE, "rows": 2}, headers=XHR)
        assert r.status_code == 422

    def test_name_over_32_chars_rejected(self, client):
        # max_length=32 on the Field rejects names longer than 32 chars
        long_name = "A" * 50
        payload = {**BASE_SCORE, "name": long_name}
        r = client.post("/api/scores", json=payload, headers=XHR)
        assert r.status_code == 422


class TestMosaicValidation:
    def test_bad_date_format_returns_422(self, client):
        r = client.post("/api/mosaic-scores",
                        json={"name": "X", "puzzle_date": "03/23/2026", "time_secs": 30},
                        headers=XHR)
        assert r.status_code == 422

    def test_missing_puzzle_date_returns_422(self, client):
        r = client.post("/api/mosaic-scores",
                        json={"name": "X", "time_secs": 30},
                        headers=XHR)
        assert r.status_code == 422


class TestMosaicCustomValidation:
    def test_rows_below_minimum_returns_422(self, client):
        r = client.post("/api/mosaic-custom-scores",
                        json={"board_hash": "abc", "board_mask": "", "rows": 2,
                              "cols": 9, "name": "X", "time_secs": 10},
                        headers=XHR)
        assert r.status_code == 422

    def test_rows_above_maximum_returns_422(self, client):
        r = client.post("/api/mosaic-custom-scores",
                        json={"board_hash": "abc", "board_mask": "", "rows": 25,
                              "cols": 9, "name": "X", "time_secs": 10},
                        headers=XHR)
        assert r.status_code == 422

    def test_missing_board_hash_returns_422(self, client):
        r = client.post("/api/mosaic-custom-scores",
                        json={"board_mask": "", "rows": 9, "cols": 9,
                              "name": "X", "time_secs": 10},
                        headers=XHR)
        assert r.status_code == 422


class TestReplayValidation:
    def test_invalid_variant_returns_422(self, client):
        r = client.post("/api/replay-scores",
                        json={"board_hash": "abc", "variant": "hexagonal",
                              "name": "X", "time_secs": 10, "time_ms": 10000,
                              "rows": 9, "cols": 9, "mines": 10},
                        headers=XHR)
        assert r.status_code == 422

    def test_empty_board_hash_returns_422(self, client):
        r = client.post("/api/replay-scores",
                        json={"board_hash": "", "variant": "standard",
                              "name": "X", "time_secs": 10, "time_ms": 10000,
                              "rows": 9, "cols": 9, "mines": 10},
                        headers=XHR)
        assert r.status_code == 422
