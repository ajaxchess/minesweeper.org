"""
analyzer.pipeline — Top-level orchestrator + DB integration.

Three responsibilities:
  1. analyze_game(game) — runs every pass and returns a FullAnalysis.
  2. SQLAlchemy GameAnalysis model — stores derived summary per game.
  3. Worker integration — async hook so the FastAPI app runs analysis
     immediately after a game's move log is persisted.

The orchestrator is intentionally simple: every pass is stateless, so we
just call them in dependency order. The Dard hierarchy pass depends on
opening and fishing outputs, so those run first.

DB design: one row per game in game_analyses, with detailed instances
serialized to JSON columns. This avoids 12 separate detail tables while
keeping the rich data queryable via JSON_EXTRACT for ad-hoc analysis.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Index, Integer, String, Text, text
)

from .passes_dard import (
    detect_fishing,
    detect_openings,
    score_flag_value,
    score_hierarchy_compliance,
)
from .passes_speed_efficiency import (
    classify_death,
    compute_basic_stats,
    detect_guesses,
    detect_shortcuts,
    detect_stranded_flags,
    detect_wasted_clicks,
    diagnose_level,
    recognize_patterns,
)
from .solver import DEFAULT_SOLVER, Solver
from .types import (
    BasicStats,
    FullAnalysis,
    Game,
    LevelDiagnosis,
)


# ═════════════════════════════════════════════════════════════════════════════
# Orchestrator
# ═════════════════════════════════════════════════════════════════════════════

def analyze_game(
    game: Game,
    solver: Solver = DEFAULT_SOLVER,
) -> FullAnalysis:
    """
    Run every diagnostic pass over a single game.

    Stateless and idempotent — running twice produces the same output.
    Safe to call from a worker, a backfill job, or a test.

    Typical runtime: 50–200ms per expert game on commodity hardware.
    """
    basic = compute_basic_stats(game)
    wasted = detect_wasted_clicks(game)
    shortcuts = detect_shortcuts(game)
    stranded = detect_stranded_flags(game)
    patterns = recognize_patterns(game, solver)
    guesses = detect_guesses(game, solver)
    death = classify_death(game, solver)

    # Dard passes — order matters: hierarchy depends on openings + fishing
    openings = detect_openings(game, solver)
    fishing = detect_fishing(game, solver)
    flag_value = score_flag_value(game)
    hierarchy = score_hierarchy_compliance(
        game, opening_report=openings, fishing_report=fishing, solver=solver
    )

    # Level diagnosis on this single game (full diagnosis aggregates across N)
    level = diagnose_level([game], solver)
    # Augment L5-7 mastery using Dard reports
    level = _finalize_level_mastery(level, openings, fishing, flag_value, hierarchy)

    return FullAnalysis(
        game_id=game.game_id,
        basic_stats=basic,
        wasted_clicks=wasted,
        shortcuts=shortcuts,
        stranded_flags=stranded,
        patterns=patterns,
        guesses=guesses,
        death=death,
        level=level,
        openings=openings,
        fishing=fishing,
        flag_value=flag_value,
        hierarchy=hierarchy,
    )


def _finalize_level_mastery(level, openings, fishing, flag_value, hierarchy):
    """Fill in L5-7 mastery scores from the Dard report outputs."""
    # L5 — Openings: based on guaranteed opening take rate
    total_guaranteed = openings.guaranteed_taken + openings.guaranteed_missed
    l5 = openings.guaranteed_taken / total_guaranteed if total_guaranteed else 0.0

    # L6 — Flag Value: pct of high-value flags
    l6 = flag_value.high_value_pct

    # L7 — Fishing + Hierarchy combined: compliance pct is the primary signal
    l7 = hierarchy.compliance_pct

    level.level_mastery[5] = round(l5, 3)
    level.level_mastery[6] = round(l6, 3)
    level.level_mastery[7] = round(l7, 3)

    # Recompute current_level now that L5-7 are real
    for lv in range(1, 8):
        if level.level_mastery[lv] < 0.85:
            level.current_level = lv
            break
    else:
        level.current_level = 7

    return level


# ═════════════════════════════════════════════════════════════════════════════
# Bug-signal detection (no-guess "forced guess" anomaly)
# ═════════════════════════════════════════════════════════════════════════════

def detect_anomalies(game: Game, analysis: FullAnalysis) -> list[dict]:
    """
    Flag analyses that look impossible. The canonical case: a no-guess game
    that the classifier labeled 'forcedGuess' — by definition no-guess boards
    have no forced guesses, so either the solver is incomplete or the player
    misclicked. Either way, surface for review.
    """
    anomalies: list[dict] = []
    if game.no_guess and analysis.death and analysis.death.cause == "forcedGuess":
        anomalies.append({
            "type": "no_guess_forced_guess",
            "game_id": game.game_id,
            "details": "Solver classified death as forced guess in a no-guess game",
        })
    return anomalies


# ═════════════════════════════════════════════════════════════════════════════
# SQLAlchemy model
# ═════════════════════════════════════════════════════════════════════════════

# Import-time guard so this module doesn't fail when used standalone
try:
    from database import Base                # type: ignore
except ImportError:
    # When integrating into ~/git/minesweeper.org, replace this with:
    #   from .database import Base
    # For now, allow standalone import:
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        pass


class GameAnalysis(Base):
    """
    Derived analysis for a single game. One row per analyzed game_replay.

    Summary columns are first-class for fast querying. Detailed instances
    (every wasted-click event, every opening opportunity, etc.) are stored
    as JSON in the *_json columns so we don't need 12 detail tables.
    """
    __tablename__ = "game_analyses"

    id              = Column(Integer, primary_key=True, index=True)
    game_replay_id  = Column(Integer, nullable=False, unique=True, index=True)
    game_id         = Column(Integer, nullable=True, index=True)   # join key to scores/game_history if available
    player_id       = Column(String(256), nullable=True, index=True)

    # Basic stats
    ioe                = Column(Float, nullable=True)
    throughput         = Column(Float, nullable=True)
    correctness        = Column(Float, nullable=True)
    three_bv_per_sec   = Column(Float, nullable=True)

    # Click breakdown
    wasted_chords      = Column(Integer, nullable=True)
    successful_chords  = Column(Integer, nullable=True)

    # Speed-efficiency level outputs (1-4)
    wasted_click_count       = Column(Integer, nullable=True)
    missed_shortcut_count    = Column(Integer, nullable=True)
    stranded_flag_count      = Column(Integer, nullable=True)

    # Pattern / death
    avg_pattern_reaction_ms  = Column(Integer, nullable=True)
    death_cause              = Column(String(32), nullable=True)
    death_region             = Column(String(16), nullable=True)

    # Guesses
    forced_guesses     = Column(Integer, nullable=True)
    avoidable_guesses  = Column(Integer, nullable=True)

    # Dard pass outputs (Layer 4)
    openings_guaranteed_taken   = Column(Integer, nullable=True)
    openings_guaranteed_missed  = Column(Integer, nullable=True)
    openings_potential_taken    = Column(Integer, nullable=True)
    openings_potential_missed   = Column(Integer, nullable=True)
    fishes_attempted            = Column(Integer, nullable=True)
    fishes_succeeded            = Column(Integer, nullable=True)
    fishes_missed               = Column(Integer, nullable=True)
    avg_flag_value_score        = Column(Float,   nullable=True)
    high_value_flag_pct         = Column(Float,   nullable=True)
    hierarchy_compliance_pct    = Column(Float,   nullable=True)

    # Bootcamp diagnosis
    bootcamp_level              = Column(Integer, nullable=True)
    level_mastery_json          = Column(Text,    nullable=True)

    # Full detail (JSON serialized — query with MySQL JSON_EXTRACT)
    wasted_clicks_json          = Column(Text, nullable=True)
    shortcuts_json              = Column(Text, nullable=True)
    patterns_json               = Column(Text, nullable=True)
    openings_json               = Column(Text, nullable=True)
    fishing_json                = Column(Text, nullable=True)
    flag_value_json             = Column(Text, nullable=True)
    hierarchy_deviations_json   = Column(Text, nullable=True)

    # Bookkeeping
    no_guess         = Column(Boolean, nullable=False, default=False)
    analyzer_version = Column(String(16), nullable=False, server_default="1.0")
    created_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_game_analyses_player_created", "player_id", "created_at"),
        Index("ix_game_analyses_hierarchy", "hierarchy_compliance_pct"),
        Index("ix_game_analyses_no_guess_created", "no_guess", "created_at"),
    )


# ═════════════════════════════════════════════════════════════════════════════
# Persistence
# ═════════════════════════════════════════════════════════════════════════════

ANALYZER_VERSION = "1.0"


def persist_analysis(
    db_session,
    game_replay_id: int,
    game: Game,
    analysis: FullAnalysis,
) -> GameAnalysis:
    """
    Convert the FullAnalysis dataclass into a GameAnalysis row and insert.
    Uses ON DUPLICATE KEY UPDATE semantics so re-analysis overwrites the
    existing row for the same game_replay_id.
    """
    # Pattern reaction time average (excluding misses)
    reactions = [p.reaction_ms for p in analysis.patterns if p.reaction_ms]
    avg_pattern_ms = int(sum(reactions) / len(reactions)) if reactions else None

    row_data = dict(
        game_replay_id           = game_replay_id,
        game_id                  = game.game_id,
        player_id                = game.player_id,
        ioe                      = analysis.basic_stats.ioe,
        throughput               = analysis.basic_stats.throughput,
        correctness              = analysis.basic_stats.correctness,
        three_bv_per_sec         = analysis.basic_stats.three_bv_per_sec,
        wasted_chords            = analysis.basic_stats.wasted_chords,
        successful_chords        = analysis.basic_stats.successful_chords,
        wasted_click_count       = len(analysis.wasted_clicks.wasted),
        missed_shortcut_count    = len(analysis.shortcuts.missed),
        stranded_flag_count      = len(analysis.stranded_flags),
        avg_pattern_reaction_ms  = avg_pattern_ms,
        death_cause              = analysis.death.cause if analysis.death else None,
        death_region             = analysis.death.region if analysis.death else None,
        forced_guesses           = analysis.guesses.forced_guesses,
        avoidable_guesses        = len(analysis.guesses.avoidable_guesses),
        openings_guaranteed_taken  = analysis.openings.guaranteed_taken,
        openings_guaranteed_missed = analysis.openings.guaranteed_missed,
        openings_potential_taken   = analysis.openings.potential_taken,
        openings_potential_missed  = analysis.openings.potential_missed,
        fishes_attempted           = analysis.fishing.fishes_attempted,
        fishes_succeeded           = analysis.fishing.fishes_succeeded,
        fishes_missed              = analysis.fishing.fishes_missed,
        avg_flag_value_score       = analysis.flag_value.avg_value_score,
        high_value_flag_pct        = analysis.flag_value.high_value_pct,
        hierarchy_compliance_pct   = analysis.hierarchy.compliance_pct,
        bootcamp_level             = analysis.level.current_level,
        level_mastery_json         = json.dumps(analysis.level.level_mastery),
        wasted_clicks_json   = json.dumps([asdict(w) for w in analysis.wasted_clicks.wasted], default=str),
        shortcuts_json       = json.dumps([asdict(s) for s in analysis.shortcuts.missed]),
        patterns_json        = json.dumps([asdict(p) for p in analysis.patterns]),
        openings_json        = json.dumps([asdict(o) for o in analysis.openings.opportunities]),
        fishing_json         = json.dumps([asdict(f) for f in analysis.fishing.opportunities]),
        flag_value_json      = json.dumps([asdict(f) for f in analysis.flag_value.flags]),
        hierarchy_deviations_json = json.dumps([asdict(d) for d in analysis.hierarchy.deviations]),
        no_guess         = game.no_guess,
        analyzer_version = ANALYZER_VERSION,
    )

    existing = db_session.query(GameAnalysis).filter_by(
        game_replay_id=game_replay_id
    ).first()
    if existing:
        for k, v in row_data.items():
            setattr(existing, k, v)
        row = existing
    else:
        row = GameAnalysis(**row_data)
        db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


# ═════════════════════════════════════════════════════════════════════════════
# FastAPI worker integration
# ═════════════════════════════════════════════════════════════════════════════

def analyze_replay_async(replay_id: int, db_session_factory) -> None:
    """
    Worker function. Wire this to fire after submit_rewind() persists a
    GameReplay row.

    Usage in main.py:

        from fastapi import BackgroundTasks
        from phase2_analyzer.pipeline import analyze_replay_async

        @app.post("/api/rewind", status_code=201)
        def submit_rewind(payload, request, db, background_tasks: BackgroundTasks):
            ...  # existing persistence logic ...
            background_tasks.add_task(
                analyze_replay_async, replay.id, SessionLocal
            )
            return {"id": replay.id}
    """
    db = db_session_factory()
    try:
        from database import GameReplay   # imported lazily to avoid hard dep
        replay = db.query(GameReplay).filter_by(id=replay_id).first()
        if not replay:
            return

        game = _game_from_replay(replay)
        if game is None:
            return    # missing required fields; skip silently

        analysis = analyze_game(game)
        persist_analysis(db, replay.id, game, analysis)
    finally:
        db.close()


def _game_from_replay(replay) -> Optional[Game]:
    """Convert a database GameReplay row into an analyzer Game object."""
    from .types import Difficulty, Move, Outcome
    if not replay.board_hash or not replay.log_json:
        return None

    move_log = [Move.from_log_entry(e) for e in json.loads(replay.log_json)]
    mine_layout = _decode_board_hash(replay.board_hash, replay.rows, replay.cols)

    try:
        difficulty = Difficulty(replay.mode) if replay.mode else Difficulty.CUSTOM
    except ValueError:
        difficulty = Difficulty.CUSTOM

    try:
        outcome = Outcome(replay.outcome) if replay.outcome else Outcome.WIN
    except ValueError:
        outcome = Outcome.WIN

    return Game(
        game_id=replay.id,
        player_id=replay.user_email or replay.guest_token,
        difficulty=difficulty,
        width=replay.cols,
        height=replay.rows,
        mine_count=replay.mines,
        three_bv=replay.bbbv or 0,
        mine_layout=mine_layout,
        move_log=move_log,
        outcome=outcome,
        duration_ms=replay.time_ms or 0,
        no_guess=bool(replay.no_guess),
        board_hash=replay.board_hash,
    )


def _decode_board_hash(board_hash: str, rows: int, cols: int) -> list[list[bool]]:
    """
    Decode the base64 bit-array of mine positions. Mirrors the JS-side
    decodeBoardHash() in static/js/replay.js.
    """
    import base64
    raw = base64.b64decode(board_hash)
    layout = [[False] * cols for _ in range(rows)]
    for idx in range(rows * cols):
        byte_idx = idx // 8
        bit_idx = idx % 8
        if byte_idx < len(raw) and (raw[byte_idx] >> (7 - bit_idx)) & 1:
            layout[idx // cols][idx % cols] = True
    return layout


# ═════════════════════════════════════════════════════════════════════════════
# Backfill
# ═════════════════════════════════════════════════════════════════════════════

def backfill_analyses(db_session_factory, batch_size: int = 100) -> int:
    """
    Run the analyzer over every game_replays row that doesn't already have a
    GameAnalysis. Returns count of newly-analyzed games.

    Safe to interrupt and resume — picks up where it left off via the
    unique constraint on game_replay_id.
    """
    db = db_session_factory()
    analyzed = 0
    try:
        from database import GameReplay

        while True:
            # Find unanalyzed replays
            sql = text("""
                SELECT gr.id
                FROM game_replays gr
                LEFT JOIN game_analyses ga ON ga.game_replay_id = gr.id
                WHERE ga.id IS NULL
                ORDER BY gr.id ASC
                LIMIT :batch
            """)
            ids = [r[0] for r in db.execute(sql, {"batch": batch_size})]
            if not ids:
                break

            for replay_id in ids:
                replay = db.query(GameReplay).filter_by(id=replay_id).first()
                if not replay:
                    continue
                game = _game_from_replay(replay)
                if game is None:
                    continue
                try:
                    analysis = analyze_game(game)
                    persist_analysis(db, replay.id, game, analysis)
                    analyzed += 1
                except Exception as exc:                   # noqa: BLE001
                    import logging
                    logging.exception("Backfill failed for replay %s: %s", replay_id, exc)
                    db.rollback()
    finally:
        db.close()
    return analyzed


# ═════════════════════════════════════════════════════════════════════════════
# Migrations for _apply_migrations() in database_template.py
# ═════════════════════════════════════════════════════════════════════════════

PHASE_2_MIGRATIONS = [
    # game_analyses table is created via Base.metadata.create_all(). The list
    # below is for any future ALTER additions; empty on initial deploy.
]
