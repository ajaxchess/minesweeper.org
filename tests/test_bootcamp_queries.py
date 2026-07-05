"""
tests/test_bootcamp_queries.py — diagnosis blend, cache, and progress tests.

Covers the phase4↔phase7 integration: drill mastery blending into the
bootcamp diagnosis and level progress (at DRILL_WEIGHT = 0.3× a live game),
the short-TTL diagnosis cache, and its invalidation on drill completion.

Uses a standalone in-memory SQLite engine — no MySQL, no app server.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import pytest

# Same env defaults tests/conftest.py sets — repeated here so this file also
# runs standalone (pytest --noconftest / python -m pytest path/to/file).
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-chars-minimum!!")
os.environ.setdefault("GA_TAG", "")
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker


# SQLite doesn't know MEDIUMTEXT (mysql-only) — emit plain TEXT.
@compiles(MEDIUMTEXT, "sqlite")
def _sqlite_mediumtext(_type, _compiler, **_kw):
    return "TEXT"


from database import Base, GameReplay                       # noqa: E402
from phase2_analyzer import GameAnalysis                    # noqa: E402
from phase7_drills.models import DrillSession               # noqa: E402
from phase7_drills.mastery import DRILL_WEIGHT              # noqa: E402
from phase4_routes import queries                           # noqa: E402


PLAYER = "blend-test@example.com"


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    # Only the tables this test touches — full-metadata create_all trips on
    # a duplicate index name in an unrelated table (wc2026_scores).
    Base.metadata.create_all(engine, tables=[
        GameAnalysis.__table__, GameReplay.__table__, DrillSession.__table__,
    ])
    session = sessionmaker(bind=engine)()
    queries._diagnosis_cache.clear()
    yield session
    session.close()


def _add_analysis(db, *, replay_id: int, mastery: dict, days_ago: float = 0.0):
    created = datetime.now(timezone.utc) - timedelta(days=days_ago)
    db.add(GameAnalysis(
        game_replay_id=replay_id,
        player_id=PLAYER,
        no_guess=False,
        ioe=0.8, correctness=0.9, throughput=1.0, three_bv_per_sec=1.5,
        hierarchy_compliance_pct=0.7,
        level_mastery_json=json.dumps({str(k): v for k, v in mastery.items()}),
        created_at=created.replace(tzinfo=None),
    ))
    db.commit()


def _add_drill(db, *, level: int, contribution: float, days_ago: float = 0.0,
               completed: bool = True, counted: bool = True):
    now = datetime.now(timezone.utc) - timedelta(days=days_ago)
    db.add(DrillSession(
        player_id=PLAYER,
        drill_type=f"l{level}_test",
        level=level,
        difficulty="expert",
        mode="standard",
        num_boards=10,
        boards_json="[]",
        attempts_json="[]",
        started_at=now.replace(tzinfo=None),
        completed_at=now.replace(tzinfo=None) if completed else None,
        num_correct=8,
        avg_decision_ms=2000,
        mastery_contribution=contribution,
        counted_toward_mastery=counted,
    ))
    db.commit()


GAME_MASTERY = {1: 0.5, 2: 0.4, 3: 0.3, 4: 0.2, 5: 0.1, 6: 0.0, 7: 0.0}


def _expected_blend(game_values, drill_values):
    num = sum(game_values) + DRILL_WEIGHT * sum(drill_values)
    den = len(game_values) + DRILL_WEIGHT * len(drill_values)
    return num / den


# ── Diagnosis blend ──────────────────────────────────────────────────────────

def test_diagnosis_without_drills_matches_game_average(db):
    for i in range(3):
        _add_analysis(db, replay_id=100 + i, mastery=GAME_MASTERY)
    d = queries.get_bootcamp_diagnosis(db, PLAYER, "standard", "expert")
    assert d["games_analyzed"] == 3
    assert d["level_mastery"][1] == pytest.approx(0.5, abs=1e-3)


def test_diagnosis_blends_completed_drills(db):
    for i in range(3):
        _add_analysis(db, replay_id=100 + i, mastery=GAME_MASTERY)
    _add_drill(db, level=1, contribution=1.0)
    _add_drill(db, level=1, contribution=1.0)

    d = queries.get_bootcamp_diagnosis(db, PLAYER, "standard", "expert")
    expected = _expected_blend([0.5, 0.5, 0.5], [1.0, 1.0])
    assert d["level_mastery"][1] == pytest.approx(expected, abs=1e-3)
    assert d["level_mastery"][1] > 0.5, "drills must pull mastery up"
    # Levels without drills are unchanged.
    assert d["level_mastery"][2] == pytest.approx(0.4, abs=1e-3)


def test_diagnosis_ignores_incomplete_and_uncounted_drills(db):
    _add_analysis(db, replay_id=100, mastery=GAME_MASTERY)
    _add_drill(db, level=1, contribution=1.0, completed=False)
    _add_drill(db, level=1, contribution=1.0, counted=False)
    d = queries.get_bootcamp_diagnosis(db, PLAYER, "standard", "expert")
    assert d["level_mastery"][1] == pytest.approx(0.5, abs=1e-3)


def test_diagnosis_uses_at_most_10_recent_drills(db):
    _add_analysis(db, replay_id=100, mastery=GAME_MASTERY)
    # 12 old low drills + newest 10 high — only the newest 10 count.
    for i in range(12):
        _add_drill(db, level=1, contribution=0.0, days_ago=5 + i)
    for i in range(10):
        _add_drill(db, level=1, contribution=1.0, days_ago=0)
    d = queries.get_bootcamp_diagnosis(db, PLAYER, "standard", "expert")
    expected = _expected_blend([0.5], [1.0] * 10)
    assert d["level_mastery"][1] == pytest.approx(expected, abs=1e-3)


def test_drills_can_advance_current_level(db):
    """A player one habit away can graduate a level through drilling."""
    near = {**GAME_MASTERY, 1: 0.84}
    _add_analysis(db, replay_id=100, mastery=near)
    d = queries.get_bootcamp_diagnosis(db, PLAYER, "standard", "expert")
    assert d["current_level"] == 1

    queries.invalidate_diagnosis_cache(PLAYER)
    for _ in range(10):
        _add_drill(db, level=1, contribution=1.0)
    d = queries.get_bootcamp_diagnosis(db, PLAYER, "standard", "expert")
    assert d["level_mastery"][1] >= 0.85
    assert d["current_level"] == 2


# ── Cache behavior ───────────────────────────────────────────────────────────

def test_diagnosis_is_cached_and_invalidation_busts_it(db):
    _add_analysis(db, replay_id=100, mastery=GAME_MASTERY)
    d1 = queries.get_bootcamp_diagnosis(db, PLAYER, "standard", "expert")
    assert d1["games_analyzed"] == 1

    # New data, cache still warm → same answer.
    _add_analysis(db, replay_id=101, mastery=GAME_MASTERY)
    d2 = queries.get_bootcamp_diagnosis(db, PLAYER, "standard", "expert")
    assert d2["games_analyzed"] == 1

    # Explicit invalidation (what drill completion triggers) → fresh answer.
    queries.invalidate_diagnosis_cache(PLAYER)
    d3 = queries.get_bootcamp_diagnosis(db, PLAYER, "standard", "expert")
    assert d3["games_analyzed"] == 2


def test_cache_is_scoped_per_player_and_mode(db):
    _add_analysis(db, replay_id=100, mastery=GAME_MASTERY)
    queries.get_bootcamp_diagnosis(db, PLAYER, "standard", "expert")
    keys = set(queries._diagnosis_cache)
    assert (PLAYER, "standard", "expert") in keys
    queries.invalidate_diagnosis_cache("someone-else")
    assert (PLAYER, "standard", "expert") in queries._diagnosis_cache


# ── Level progress blend ─────────────────────────────────────────────────────

def test_level_progress_blends_drills(db):
    # No GameReplay rows needed — the time_ms join tolerates missing replays
    # (data points render with time_ms=None).
    for i in range(4):
        _add_analysis(db, replay_id=100 + i, mastery=GAME_MASTERY, days_ago=i)
    p0 = queries.get_level_progress(db, PLAYER, 1, mode="standard",
                                    difficulty="expert", days_window=30)
    assert p0["current_mastery"] == pytest.approx(0.5, abs=1e-3)

    for _ in range(5):
        _add_drill(db, level=1, contribution=1.0)
    p1 = queries.get_level_progress(db, PLAYER, 1, mode="standard",
                                    difficulty="expert", days_window=30)
    expected = _expected_blend([0.5] * 4, [1.0] * 5)
    assert p1["current_mastery"] == pytest.approx(expected, abs=1e-3)
    assert len(p1["data_points"]) == 4, "drills don't add chart points (games only)"
