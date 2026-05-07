"""
tests/test_tametsi_db.py — Integration tests for F79-B: Tametsi DB models
and the daily puzzle pre-generation scheduler function.

Requires the conftest.py SQLite test database (no MySQL needed).
"""
import sys
import os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import database as _db
from database import TametsiBoard, TametsiDaily, TametsiScore
from main import generate_tametsi_dailies

# Fixed dates to avoid collision with the startup background thread (today = 2026-05-07)
DATE_A = "2026-01-15"
DATE_B = "2026-01-16"

SAMPLE_BOARD_DATA = {
    "mines":      [[0, 1], [1, 2]],
    "row_counts": [1, 1, 0],
    "col_counts": [0, 1, 1],
}


# ── TametsiBoard ──────────────────────────────────────────────────────────────

class TestTametsiBoard:
    def test_insert_and_query(self, client):
        db = _db.SessionLocal()
        try:
            db.add(TametsiBoard(
                board_hash = "a" * 64,
                rows       = 3,
                cols       = 3,
                mines      = 2,
                bbbv       = 5,
                board_data = SAMPLE_BOARD_DATA,
            ))
            db.commit()
            row = db.get(TametsiBoard, "a" * 64)
            assert row is not None
            assert row.rows == 3 and row.mines == 2 and row.bbbv == 5
        finally:
            db.close()

    def test_board_data_json_roundtrip(self, client):
        db = _db.SessionLocal()
        try:
            db.add(TametsiBoard(
                board_hash = "b" * 64,
                rows=3, cols=3, mines=2, bbbv=5,
                board_data = SAMPLE_BOARD_DATA,
            ))
            db.commit()
            row = db.get(TametsiBoard, "b" * 64)
            assert row.board_data["mines"] == [[0, 1], [1, 2]]
            assert row.board_data["row_counts"] == [1, 1, 0]
            assert row.board_data["col_counts"] == [0, 1, 1]
        finally:
            db.close()

    def test_primary_key_is_board_hash(self, client):
        db = _db.SessionLocal()
        try:
            db.add(TametsiBoard(
                board_hash="c" * 64, rows=3, cols=3, mines=2, bbbv=5,
                board_data=SAMPLE_BOARD_DATA,
            ))
            db.commit()
            assert db.get(TametsiBoard, "c" * 64) is not None
            assert db.get(TametsiBoard, "d" * 64) is None
        finally:
            db.close()

    def test_duplicate_hash_raises(self, client):
        from sqlalchemy.exc import IntegrityError
        db = _db.SessionLocal()
        try:
            db.add(TametsiBoard(
                board_hash="e" * 64, rows=3, cols=3, mines=2, bbbv=5,
                board_data=SAMPLE_BOARD_DATA,
            ))
            db.commit()
            db.add(TametsiBoard(
                board_hash="e" * 64, rows=9, cols=9, mines=10, bbbv=20,
                board_data=SAMPLE_BOARD_DATA,
            ))
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()


# ── TametsiDaily ──────────────────────────────────────────────────────────────

class TestTametsiDaily:
    def test_insert_and_query(self, client):
        db = _db.SessionLocal()
        try:
            db.add(TametsiDaily(puzzle_date=DATE_A, level="beginner", board_hash="a" * 64))
            db.commit()
            row = db.query(TametsiDaily).filter_by(puzzle_date=DATE_A, level="beginner").first()
            assert row is not None
            assert row.board_hash == "a" * 64
        finally:
            db.close()

    def test_unique_date_level_constraint(self, client):
        from sqlalchemy.exc import IntegrityError
        db = _db.SessionLocal()
        try:
            db.add(TametsiDaily(puzzle_date=DATE_A, level="intermediate", board_hash="a" * 64))
            db.commit()
            db.add(TametsiDaily(puzzle_date=DATE_A, level="intermediate", board_hash="b" * 64))
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()

    def test_same_date_different_levels_allowed(self, client):
        db = _db.SessionLocal()
        try:
            db.add(TametsiDaily(puzzle_date=DATE_A, level="beginner",     board_hash="a" * 64))
            db.add(TametsiDaily(puzzle_date=DATE_A, level="intermediate", board_hash="b" * 64))
            db.add(TametsiDaily(puzzle_date=DATE_A, level="expert",       board_hash="c" * 64))
            db.commit()
            count = db.query(TametsiDaily).filter_by(puzzle_date=DATE_A).count()
            assert count == 3
        finally:
            db.close()

    def test_different_dates_same_level_allowed(self, client):
        db = _db.SessionLocal()
        try:
            db.add(TametsiDaily(puzzle_date=DATE_A, level="beginner", board_hash="a" * 64))
            db.add(TametsiDaily(puzzle_date=DATE_B, level="beginner", board_hash="b" * 64))
            db.commit()
            assert db.query(TametsiDaily).count() == 2
        finally:
            db.close()


# ── TametsiScore ──────────────────────────────────────────────────────────────

class TestTametsiScore:
    def test_insert_and_query(self, client):
        db = _db.SessionLocal()
        try:
            db.add(TametsiScore(
                board_hash="a" * 64,
                level="beginner",
                is_daily=True,
                name="Alice",
                user_email="alice@example.com",
                time_ms=45000,
                bbbv=12,
            ))
            db.commit()
            row = db.query(TametsiScore).filter_by(name="Alice").first()
            assert row is not None
            assert row.time_ms == 45000 and row.bbbv == 12
        finally:
            db.close()

    def test_guest_score_no_email(self, client):
        db = _db.SessionLocal()
        try:
            db.add(TametsiScore(
                board_hash="a" * 64,
                level="beginner",
                is_daily=False,
                name="Guest",
                time_ms=60000,
                bbbv=8,
            ))
            db.commit()
            row = db.query(TametsiScore).filter_by(name="Guest").first()
            assert row.user_email is None
        finally:
            db.close()

    def test_to_dict_schema(self, client):
        db = _db.SessionLocal()
        try:
            db.add(TametsiScore(
                board_hash="a" * 64,
                level="intermediate",
                is_daily=True,
                name="Bob",
                time_ms=30000,
                bbbv=20,
            ))
            db.commit()
            row = db.query(TametsiScore).filter_by(name="Bob").first()
            d = row.to_dict()
            assert set(d.keys()) == {"id", "board_hash", "level", "is_daily", "name", "time_ms", "bbbv", "created_at"}
            assert d["level"] == "intermediate"
            assert d["is_daily"] is True
        finally:
            db.close()

    def test_multiple_scores_per_board(self, client):
        db = _db.SessionLocal()
        try:
            for i in range(5):
                db.add(TametsiScore(
                    board_hash="a" * 64,
                    level="beginner",
                    is_daily=False,
                    name=f"Player{i}",
                    time_ms=10000 * (i + 1),
                    bbbv=10,
                ))
            db.commit()
            count = db.query(TametsiScore).filter_by(board_hash="a" * 64).count()
            assert count == 5
        finally:
            db.close()


# ── generate_tametsi_dailies ──────────────────────────────────────────────────

class TestGenerateTametsiDailies:
    def test_creates_three_daily_records(self, client):
        generate_tametsi_dailies(DATE_A)
        db = _db.SessionLocal()
        try:
            count = db.query(TametsiDaily).filter_by(puzzle_date=DATE_A).count()
            assert count == 3
        finally:
            db.close()

    def test_creates_board_record_for_each_level(self, client):
        generate_tametsi_dailies(DATE_A)
        db = _db.SessionLocal()
        try:
            daily_rows = db.query(TametsiDaily).filter_by(puzzle_date=DATE_A).all()
            for row in daily_rows:
                board = db.get(TametsiBoard, row.board_hash)
                assert board is not None, f"No TametsiBoard for hash {row.board_hash}"
        finally:
            db.close()

    def test_board_data_has_correct_schema(self, client):
        generate_tametsi_dailies(DATE_A)
        db = _db.SessionLocal()
        try:
            for row in db.query(TametsiDaily).filter_by(puzzle_date=DATE_A).all():
                board = db.get(TametsiBoard, row.board_hash)
                bd = board.board_data
                assert "mines" in bd and "row_counts" in bd and "col_counts" in bd
                assert isinstance(bd["mines"], list)
                assert all(len(m) == 2 for m in bd["mines"])
        finally:
            db.close()

    def test_levels_are_beginner_intermediate_expert(self, client):
        generate_tametsi_dailies(DATE_A)
        db = _db.SessionLocal()
        try:
            levels = {r.level for r in db.query(TametsiDaily).filter_by(puzzle_date=DATE_A).all()}
            assert levels == {"beginner", "intermediate", "expert"}
        finally:
            db.close()

    def test_idempotent_second_call_is_noop(self, client):
        generate_tametsi_dailies(DATE_A)
        generate_tametsi_dailies(DATE_A)
        db = _db.SessionLocal()
        try:
            # Should still be exactly 3 — no duplicates
            count = db.query(TametsiDaily).filter_by(puzzle_date=DATE_A).count()
            assert count == 3
        finally:
            db.close()

    def test_different_dates_produce_different_hashes(self, client):
        generate_tametsi_dailies(DATE_A)
        generate_tametsi_dailies(DATE_B)
        db = _db.SessionLocal()
        try:
            hashes_a = {r.board_hash for r in db.query(TametsiDaily).filter_by(puzzle_date=DATE_A).all()}
            hashes_b = {r.board_hash for r in db.query(TametsiDaily).filter_by(puzzle_date=DATE_B).all()}
            assert hashes_a.isdisjoint(hashes_b), "Same board used for different dates"
        finally:
            db.close()

    def test_board_dimensions_match_level(self, client):
        from tametsi_generator import LEVELS
        generate_tametsi_dailies(DATE_A)
        db = _db.SessionLocal()
        try:
            for row in db.query(TametsiDaily).filter_by(puzzle_date=DATE_A).all():
                board = db.get(TametsiBoard, row.board_hash)
                expected_rows, expected_cols, expected_mines = LEVELS[row.level]
                assert board.rows == expected_rows
                assert board.cols == expected_cols
                assert board.mines == expected_mines
        finally:
            db.close()
