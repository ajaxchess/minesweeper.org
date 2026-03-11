"""
database.py — SQLAlchemy setup for MySQL via PyMySQL
"""
from sqlalchemy import (
    create_engine, Column, Integer, String,
    DateTime, Enum, Index
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime, timezone
import enum

# ── Config — replace with your real credentials ───────────────────────────────
DB_USER     = "the_minesweeper_user"
DB_PASSWORD = "the_password"
DB_HOST     = "localhost"
DB_PORT     = 3306
DB_NAME     = "minesweeper"

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # drops stale connections automatically
    pool_recycle=3600,    # recycle connections every hour
    echo=False,           # set True to log SQL queries during dev
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# ── Base ──────────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass

# ── Enum for game mode ────────────────────────────────────────────────────────
class GameMode(str, enum.Enum):
    beginner     = "beginner"
    intermediate = "intermediate"
    expert       = "expert"
    custom       = "custom"

# ── Score model ───────────────────────────────────────────────────────────────
class Score(Base):
    __tablename__ = "scores"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(32), nullable=False)
    user_email = Column(String(256), nullable=True, index=True)
    mode       = Column(Enum(GameMode), nullable=False)
    time_secs  = Column(Integer, nullable=False)       # elapsed seconds
    rows       = Column(Integer, nullable=False)
    cols       = Column(Integer, nullable=False)
    mines      = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Fast lookups by mode + time for leaderboard queries
    __table_args__ = (
        Index("ix_scores_mode_time", "mode", "time_secs"),
    )

    def to_dict(self):
        return {
            "id":         self.id,
            "name":       self.name,
            "mode":       self.mode,
            "time_secs":  self.time_secs,
            "rows":       self.rows,
            "cols":       self.cols,
            "mines":      self.mines,
            "created_at": self.created_at.strftime("%Y-%m-%d"),
        }

# ── Game history model (permanent — never reset) ─────────────────────────────
class GameHistory(Base):
    __tablename__ = "game_history"

    id         = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(256), nullable=False, index=True)
    name       = Column(String(32), nullable=False)
    mode       = Column(Enum(GameMode), nullable=False)
    time_secs  = Column(Integer, nullable=False)
    rows       = Column(Integer, nullable=False)
    cols       = Column(Integer, nullable=False)
    mines      = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_game_history_email_mode", "user_email", "mode"),
    )

    def to_dict(self):
        return {
            "id":         self.id,
            "name":       self.name,
            "mode":       self.mode,
            "time_secs":  self.time_secs,
            "rows":       self.rows,
            "cols":       self.cols,
            "mines":      self.mines,
            "created_at": self.created_at.strftime("%Y-%m-%d"),
        }

# ── DB session dependency (used in FastAPI routes) ───────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── Rush Score model (separate table — never reset) ───────────────────────────
class RushScore(Base):
    __tablename__ = "rush_scores"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(32), nullable=False)
    user_email = Column(String(256), nullable=True, index=True)
    score         = Column(Integer, nullable=False)          # elapsed + cleared_mines*5
    cleared_mines = Column(Integer, nullable=True)           # mines in cleared rows
    time_secs     = Column(Integer, nullable=False)          # game duration (seconds)
    cols          = Column(Integer, nullable=False)          # board width
    rush_mode  = Column(String(16), nullable=False)  # easy/normal/hard
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_rush_scores_mode_score", "rush_mode", "score"),
    )

    def to_dict(self):
        return {
            "id":           self.id,
            "name":         self.name,
            "score":        self.score,
            "cleared_mines":self.cleared_mines,
            "time_secs":    self.time_secs,
            "cols":         self.cols,
            "rush_mode":    self.rush_mode,
            "created_at":   self.created_at.strftime("%Y-%m-%d"),
        }

# ── Tentaizu Score model (permanent — one per player per day) ─────────────────
class TentaizuScore(Base):
    __tablename__ = "tentaizu_scores"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(32), nullable=False)
    user_email  = Column(String(256), nullable=True, index=True)
    puzzle_date = Column(String(10), nullable=False)   # YYYY-MM-DD
    time_secs   = Column(Integer, nullable=False)
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_tentaizu_scores_date_time", "puzzle_date", "time_secs"),
    )

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "puzzle_date": self.puzzle_date,
            "time_secs":   self.time_secs,
            "created_at":  self.created_at.strftime("%Y-%m-%d"),
        }

# ── Create tables if they don't exist ────────────────────────────────────────
def init_db():
    Base.metadata.create_all(bind=engine)
