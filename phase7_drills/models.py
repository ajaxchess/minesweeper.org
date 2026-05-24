"""
phase7_drills.models — SQLAlchemy ORM models for drill sessions.

Single table strategy. We store the per-board state, the per-board attempts,
and the session summary all in one row keyed by drill_id. JSON columns are
MEDIUMTEXT (16MB) for the same reason game_analyses uses it — boards can be
larger than the 64KB TEXT default once we ship harder difficulties.

Mount in main.py the same way game_analyses is mounted (Base is the project's
shared declarative base). If the project uses a separate Base per module, you
can re-export DrillSession from phase7_drills/__init__.py and import it in
main.py.

Why no separate drill_attempts table:
  - One drill session has a fixed small number of boards (≤ 10 today).
  - Attempts are always read together with the session.
  - Saves a join on the hot read path (drill page reload).

Schema migration shipped in schema_sql.py — see README_Drills.md for the
CREATE TABLE statement.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, String, Index,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT

# Try to use the project's shared Base; fall back to a local one for tests.
try:
    from database import Base                          # type: ignore
except ImportError:
    try:
        from main import Base                          # type: ignore
    except ImportError:
        from sqlalchemy.orm import DeclarativeBase

        class Base(DeclarativeBase):                   # type: ignore
            pass


class DrillSession(Base):
    """One drill attempt by one player. Created on POST /api/drills/start
    and updated on each POST /api/drills/{id}/submit. Completed when the
    last board's submission lands.
    """
    __tablename__ = "drill_sessions"

    id              = Column(Integer, primary_key=True, index=True)
    player_id       = Column(String(256), nullable=False, index=True)

    # Drill identity
    drill_type      = Column(String(64), nullable=False)   # 'l5_opening_recognition'
    level           = Column(Integer, nullable=False)      # bootcamp level it counts toward
    difficulty      = Column(String(16), nullable=False, default="expert")
    mode            = Column(String(16), nullable=False, default="standard")  # 'standard' | 'no_guess'
    num_boards      = Column(Integer, nullable=False, default=10)

    # Generated boards (server-side, includes mine layout).
    # Shape: [{width, height, num_mines, seed, mines, revealed,
    #          correct_cells, optimal_cell, optimal_opening_size}, …]
    boards_json     = Column(MEDIUMTEXT, nullable=False)

    # Player attempts as they come in.
    # Shape: [{board_index, chosen_r, chosen_c, decision_ms, is_correct,
    #          is_mine, opening_size, relative_quality}, …]
    attempts_json   = Column(MEDIUMTEXT, nullable=False, default="[]")

    # Session bookkeeping
    started_at      = Column(DateTime, nullable=False,
                              default=lambda: datetime.now(timezone.utc))
    completed_at    = Column(DateTime, nullable=True)

    # Summary (populated when completed_at is set)
    num_correct           = Column(Integer, nullable=True)
    avg_decision_ms       = Column(Integer, nullable=True)
    mastery_contribution  = Column(Float,   nullable=True)
    counted_toward_mastery = Column(Boolean, nullable=False, default=False)

    # Drill version — bump when the generator algorithm changes, so we can
    # filter old drill records out of mastery averages if needed.
    drill_version   = Column(String(16), nullable=False, default="1.0")

    __table_args__ = (
        Index("ix_drill_sessions_player_started", "player_id", "started_at"),
        Index("ix_drill_sessions_player_level", "player_id", "level"),
    )
