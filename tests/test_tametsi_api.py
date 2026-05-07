"""
tests/test_tametsi_api.py — Integration tests for F79-C: Tametsi API endpoints.
"""
import sys
import os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from conftest import XHR
import database as _db
from database import TametsiBoard, TametsiDaily, TametsiScore

# ── Helpers ───────────────────────────────────────────────────────────────────

FAKE_HASH = "a" * 64     # valid hex-format, non-existent board
BAD_HASH  = "g" * 64     # invalid hex (g is not hex)

BOARD_PAYLOAD = {
    "board_hash": FAKE_HASH,
    "rows":       9,
    "cols":       9,
    "mines":      10,
    "bbbv":       12,
    "board_data": {
        "mines":      [[0, 1]],
        "row_counts": [1, 0, 0, 0, 0, 0, 0, 0, 0],
        "col_counts": [0, 1, 0, 0, 0, 0, 0, 0, 0],
    },
}


def _seed_board(board_hash=FAKE_HASH):
    """Insert a TametsiBoard row directly for tests that need a known board."""
    db = _db.SessionLocal()
    try:
        if not db.get(TametsiBoard, board_hash):
            db.add(TametsiBoard(
                board_hash = board_hash,
                rows       = 9,
                cols       = 9,
                mines      = 10,
                bbbv       = 12,
                board_data = {
                    "mines":      [[0, 1]],
                    "row_counts": [1, 0, 0, 0, 0, 0, 0, 0, 0],
                    "col_counts": [0, 1, 0, 0, 0, 0, 0, 0, 0],
                },
            ))
            db.commit()
    finally:
        db.close()


def _seed_daily(board_hash=FAKE_HASH, level="beginner", date_str="2026-05-07"):
    _seed_board(board_hash)
    db = _db.SessionLocal()
    try:
        if not db.query(TametsiDaily).filter_by(puzzle_date=date_str, level=level).first():
            db.add(TametsiDaily(puzzle_date=date_str, level=level, board_hash=board_hash))
            db.commit()
    finally:
        db.close()


SCORE_PAYLOAD = {
    "board_hash": FAKE_HASH,
    "level":      "beginner",
    "is_daily":   False,
    "name":       "Alice",
    "time_ms":    45000,
    "bbbv":       12,
}


# ── GET /api/tametsi/daily/{level} ────────────────────────────────────────────

class TestTametsiDailyEndpoint:
    def test_returns_board_for_valid_level(self, client):
        r = client.get("/api/tametsi/daily/beginner")
        assert r.status_code == 200
        data = r.json()
        assert "board_hash" in data
        assert data["rows"] == 9 and data["cols"] == 9 and data["mines"] == 10

    def test_intermediate_returns_16x16(self, client):
        r = client.get("/api/tametsi/daily/intermediate")
        assert r.status_code == 200
        data = r.json()
        assert data["rows"] == 16 and data["cols"] == 16 and data["mines"] == 40

    def test_invalid_level_returns_400(self, client):
        r = client.get("/api/tametsi/daily/legendary")
        assert r.status_code == 400

    def test_board_data_schema(self, client):
        r = client.get("/api/tametsi/daily/beginner")
        bd = r.json()["board_data"]
        assert "mines" in bd and "row_counts" in bd and "col_counts" in bd
        assert len(bd["row_counts"]) == 9
        assert len(bd["col_counts"]) == 9

    def test_same_level_idempotent(self, client):
        h1 = client.get("/api/tametsi/daily/beginner").json()["board_hash"]
        h2 = client.get("/api/tametsi/daily/beginner").json()["board_hash"]
        assert h1 == h2

    def test_different_levels_different_hashes(self, client):
        h_beg = client.get("/api/tametsi/daily/beginner").json()["board_hash"]
        h_int = client.get("/api/tametsi/daily/intermediate").json()["board_hash"]
        assert h_beg != h_int


# ── GET /api/tametsi/random/{level} ──────────────────────────────────────────

class TestTametsiRandomEndpoint:
    def test_returns_board_for_valid_level(self, client):
        r = client.get("/api/tametsi/random/beginner")
        assert r.status_code == 200
        data = r.json()
        assert "board_hash" in data
        assert data["rows"] == 9 and data["cols"] == 9 and data["mines"] == 10

    def test_board_data_present(self, client):
        r = client.get("/api/tametsi/random/beginner")
        bd = r.json()["board_data"]
        assert len(bd["row_counts"]) == 9
        assert len(bd["col_counts"]) == 9

    def test_invalid_level_returns_400(self, client):
        r = client.get("/api/tametsi/random/superhard")
        assert r.status_code == 400

    def test_board_stored_in_db(self, client):
        r = client.get("/api/tametsi/random/beginner")
        board_hash = r.json()["board_hash"]
        db = _db.SessionLocal()
        try:
            assert db.get(TametsiBoard, board_hash) is not None
        finally:
            db.close()

    def test_repeated_calls_return_different_boards(self, client):
        h1 = client.get("/api/tametsi/random/beginner").json()["board_hash"]
        h2 = client.get("/api/tametsi/random/beginner").json()["board_hash"]
        # Different random boards almost certainly have different hashes
        # (could theoretically collide but probability is negligible)
        assert h1 != h2


# ── GET /api/tametsi/board/{hash} ─────────────────────────────────────────────

class TestTametsiLoadBoard:
    def test_returns_board_when_exists(self, client):
        _seed_board()
        r = client.get(f"/api/tametsi/board/{FAKE_HASH}")
        assert r.status_code == 200
        assert r.json()["board_hash"] == FAKE_HASH

    def test_404_for_unknown_hash(self, client):
        r = client.get(f"/api/tametsi/board/{'b' * 64}")
        assert r.status_code == 404

    def test_400_for_invalid_hash_format(self, client):
        r = client.get(f"/api/tametsi/board/{BAD_HASH}")
        assert r.status_code == 400

    def test_response_includes_board_data(self, client):
        _seed_board()
        r = client.get(f"/api/tametsi/board/{FAKE_HASH}")
        data = r.json()
        assert set(data.keys()) == {"board_hash", "rows", "cols", "mines", "bbbv", "board_data"}
        assert "mines" in data["board_data"]


# ── POST /api/tametsi/scores ──────────────────────────────────────────────────

class TestTametsiScoreSubmission:
    def test_submit_random_score_returns_201(self, client):
        _seed_board()
        r = client.post("/api/tametsi/scores", json=SCORE_PAYLOAD, headers=XHR)
        assert r.status_code == 201
        assert r.json()["ok"] is True
        assert "id" in r.json()

    def test_score_stored_in_db(self, client):
        _seed_board()
        client.post("/api/tametsi/scores", json=SCORE_PAYLOAD, headers=XHR)
        db = _db.SessionLocal()
        try:
            row = db.query(TametsiScore).filter_by(name="Alice").first()
            assert row is not None
            assert row.time_ms == 45000 and row.bbbv == 12
        finally:
            db.close()

    def test_unknown_board_hash_returns_404(self, client):
        payload = {**SCORE_PAYLOAD, "board_hash": "b" * 64}
        r = client.post("/api/tametsi/scores", json=payload, headers=XHR)
        assert r.status_code == 404

    def test_without_xhr_header_uses_json_content_type(self, client):
        # The CSRF middleware allows Content-Type: application/json in addition to XHR header.
        # The test client sends application/json by default when using json= param.
        _seed_board()
        r = client.post("/api/tametsi/scores", json=SCORE_PAYLOAD)
        assert r.status_code == 201

    def test_invalid_level_rejected(self, client):
        _seed_board()
        payload = {**SCORE_PAYLOAD, "level": "legendary"}
        r = client.post("/api/tametsi/scores", json=payload, headers=XHR)
        assert r.status_code == 422

    def test_negative_time_ms_rejected(self, client):
        _seed_board()
        payload = {**SCORE_PAYLOAD, "time_ms": -1}
        r = client.post("/api/tametsi/scores", json=payload, headers=XHR)
        assert r.status_code == 422

    def test_daily_score_wrong_hash_rejected(self, client):
        _seed_board()
        # is_daily=True but no daily record exists for today
        payload = {**SCORE_PAYLOAD, "is_daily": True}
        r = client.post("/api/tametsi/scores", json=payload, headers=XHR)
        assert r.status_code == 400

    def test_daily_score_matching_hash_accepted(self, client):
        _seed_daily(board_hash=FAKE_HASH, level="beginner")
        payload = {**SCORE_PAYLOAD, "is_daily": True}
        r = client.post("/api/tametsi/scores", json=payload, headers=XHR)
        assert r.status_code == 201

    def test_random_board_capped_at_15_scores(self, client):
        _seed_board()
        for i in range(18):
            payload = {**SCORE_PAYLOAD, "name": f"Player{i}", "time_ms": 10000 + i * 100}
            client.post("/api/tametsi/scores", json=payload, headers=XHR)
        db = _db.SessionLocal()
        try:
            count = db.query(TametsiScore).filter_by(board_hash=FAKE_HASH).count()
            assert count == 15
        finally:
            db.close()

    def test_cap_retains_fastest_scores(self, client):
        _seed_board()
        # Submit 17 scores with time_ms 1000..17000
        for i in range(1, 18):
            payload = {**SCORE_PAYLOAD, "name": f"P{i}", "time_ms": i * 1000}
            client.post("/api/tametsi/scores", json=payload, headers=XHR)
        db = _db.SessionLocal()
        try:
            scores = (
                db.query(TametsiScore)
                .filter_by(board_hash=FAKE_HASH)
                .order_by(TametsiScore.time_ms.asc())
                .all()
            )
            assert len(scores) == 15
            # Slowest retained should be at most 15000ms
            assert max(s.time_ms for s in scores) <= 15000
        finally:
            db.close()

    def test_name_sanitized(self, client):
        _seed_board()
        payload = {**SCORE_PAYLOAD, "name": "  Alice\x00\x01  "}
        r = client.post("/api/tametsi/scores", json=payload, headers=XHR)
        assert r.status_code == 201
        db = _db.SessionLocal()
        try:
            row = db.query(TametsiScore).filter_by(board_hash=FAKE_HASH).first()
            assert row.name == "Alice"
        finally:
            db.close()


# ── GET /api/tametsi/leaderboard/{level} ─────────────────────────────────────

class TestTametsiDailyLeaderboard:
    def test_empty_when_no_daily_exists(self, client):
        r = client.get("/api/tametsi/leaderboard/beginner")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_scores_for_todays_daily(self, client):
        _seed_daily()
        payload = {**SCORE_PAYLOAD, "is_daily": True}
        client.post("/api/tametsi/scores", json=payload, headers=XHR)
        r = client.get("/api/tametsi/leaderboard/beginner")
        assert r.status_code == 200
        names = [s["name"] for s in r.json()]
        assert "Alice" in names

    def test_scores_ordered_by_time_ms(self, client):
        _seed_daily()
        for ms in [60000, 30000, 45000]:
            payload = {**SCORE_PAYLOAD, "name": f"P{ms}", "time_ms": ms, "is_daily": True}
            client.post("/api/tametsi/scores", json=payload, headers=XHR)
        scores = client.get("/api/tametsi/leaderboard/beginner").json()
        times = [s["time_ms"] for s in scores]
        assert times == sorted(times)

    def test_excludes_random_scores(self, client):
        _seed_daily()
        # Random score for same board
        client.post("/api/tametsi/scores", json=SCORE_PAYLOAD, headers=XHR)
        r = client.get("/api/tametsi/leaderboard/beginner")
        assert r.json() == []

    def test_invalid_level_returns_400(self, client):
        r = client.get("/api/tametsi/leaderboard/legendary")
        assert r.status_code == 400

    def test_response_has_expected_keys(self, client):
        _seed_daily()
        payload = {**SCORE_PAYLOAD, "is_daily": True}
        client.post("/api/tametsi/scores", json=payload, headers=XHR)
        scores = client.get("/api/tametsi/leaderboard/beginner").json()
        assert len(scores) > 0
        # Guest scores don't include profile_url; registered user scores do
        assert {"id", "board_hash", "level", "is_daily", "name", "time_ms", "bbbv", "created_at"}.issubset(
            scores[0].keys()
        )


# ── GET /api/tametsi/leaderboard/board/{hash} ────────────────────────────────

class TestTametsiRandomLeaderboard:
    def test_empty_for_unknown_board(self, client):
        r = client.get(f"/api/tametsi/leaderboard/board/{'b' * 64}")
        assert r.status_code == 200
        assert r.json() == []

    def test_400_for_invalid_hash_format(self, client):
        r = client.get(f"/api/tametsi/leaderboard/board/{BAD_HASH}")
        assert r.status_code == 400

    def test_returns_scores_for_board(self, client):
        _seed_board()
        client.post("/api/tametsi/scores", json=SCORE_PAYLOAD, headers=XHR)
        r = client.get(f"/api/tametsi/leaderboard/board/{FAKE_HASH}")
        assert r.status_code == 200
        names = [s["name"] for s in r.json()]
        assert "Alice" in names

    def test_capped_at_15(self, client):
        _seed_board()
        for i in range(15):
            payload = {**SCORE_PAYLOAD, "name": f"P{i}", "time_ms": 10000 + i * 100}
            client.post("/api/tametsi/scores", json=payload, headers=XHR)
        r = client.get(f"/api/tametsi/leaderboard/board/{FAKE_HASH}")
        assert len(r.json()) <= 15

    def test_scores_ordered_by_time_ms(self, client):
        _seed_board()
        for ms in [50000, 20000, 35000]:
            payload = {**SCORE_PAYLOAD, "name": f"P{ms}", "time_ms": ms}
            client.post("/api/tametsi/scores", json=payload, headers=XHR)
        scores = client.get(f"/api/tametsi/leaderboard/board/{FAKE_HASH}").json()
        times = [s["time_ms"] for s in scores]
        assert times == sorted(times)

    def test_response_includes_bbbv(self, client):
        _seed_board()
        client.post("/api/tametsi/scores", json=SCORE_PAYLOAD, headers=XHR)
        scores = client.get(f"/api/tametsi/leaderboard/board/{FAKE_HASH}").json()
        assert len(scores) > 0
        assert "bbbv" in scores[0]
