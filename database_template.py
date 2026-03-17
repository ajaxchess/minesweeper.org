"""
database.py — SQLAlchemy setup for MySQL via PyMySQL
"""
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    DateTime, Enum, Index, Boolean
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
    time_secs  = Column(Integer, nullable=False)       # elapsed whole seconds (legacy display)
    time_ms    = Column(Integer, nullable=True)        # precise elapsed milliseconds
    rows       = Column(Integer, nullable=False)
    cols       = Column(Integer, nullable=False)
    mines      = Column(Integer, nullable=False)
    no_guess     = Column(Boolean, default=False, nullable=False)
    board_hash   = Column(String(128), nullable=True)  # base64 bit-array of mine positions
    bbbv         = Column(Integer, nullable=True)       # Bechtel's Board Benchmark Value
    left_clicks  = Column(Integer, nullable=True)
    right_clicks = Column(Integer, nullable=True)
    chord_clicks = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Fast lookups by mode + time for leaderboard queries
    __table_args__ = (
        Index("ix_scores_mode_time", "mode", "time_secs"),
    )

    def to_dict(self):
        return {
            "id":           self.id,
            "name":         self.name,
            "mode":         self.mode,
            "time_secs":    self.time_secs,
            "time_ms":      self.time_ms,
            "rows":         self.rows,
            "cols":         self.cols,
            "mines":        self.mines,
            "no_guess":     self.no_guess,
            "board_hash":   self.board_hash,
            "bbbv":         self.bbbv,
            "left_clicks":  self.left_clicks,
            "right_clicks": self.right_clicks,
            "chord_clicks": self.chord_clicks,
            "created_at":   self.created_at.strftime("%Y-%m-%d"),
        }

# ── Game history model (permanent — never reset) ─────────────────────────────
class GameHistory(Base):
    __tablename__ = "game_history"

    id         = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(256), nullable=False, index=True)
    name       = Column(String(32), nullable=False)
    mode       = Column(Enum(GameMode), nullable=False)
    time_secs  = Column(Integer, nullable=False)
    time_ms    = Column(Integer, nullable=True)
    rows       = Column(Integer, nullable=False)
    cols       = Column(Integer, nullable=False)
    mines      = Column(Integer, nullable=False)
    no_guess     = Column(Boolean, default=False, nullable=False)
    board_hash   = Column(String(128), nullable=True)
    bbbv         = Column(Integer, nullable=True)
    left_clicks  = Column(Integer, nullable=True)
    right_clicks = Column(Integer, nullable=True)
    chord_clicks = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_game_history_email_mode", "user_email", "mode"),
    )

    def to_dict(self):
        return {
            "id":           self.id,
            "name":         self.name,
            "mode":         self.mode,
            "time_secs":    self.time_secs,
            "time_ms":      self.time_ms,
            "rows":         self.rows,
            "cols":         self.cols,
            "mines":        self.mines,
            "no_guess":     self.no_guess,
            "board_hash":   self.board_hash,
            "bbbv":         self.bbbv,
            "left_clicks":  self.left_clicks,
            "right_clicks": self.right_clicks,
            "chord_clicks": self.chord_clicks,
            "created_at":   self.created_at.strftime("%Y-%m-%d"),
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
    rows_cleared  = Column(Integer, nullable=True)           # number of rows cleared
    time_secs     = Column(Integer, nullable=False)          # game duration (seconds)
    cols          = Column(Integer, nullable=False)          # board width
    density       = Column(Float, nullable=True)             # mines/cell (custom mode)
    rush_mode  = Column(String(16), nullable=False)  # easy/normal/hard/custom
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
            "rows_cleared": self.rows_cleared,
            "time_secs":    self.time_secs,
            "cols":         self.cols,
            "density":      self.density,
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

# ── Tentaizu Easy (5×5) Score model ───────────────────────────────────────────
class TentaizuEasyScore(Base):
    __tablename__ = "tentaizu_easy_scores"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(32), nullable=False)
    user_email  = Column(String(256), nullable=True, index=True)
    puzzle_date = Column(String(10), nullable=False)   # YYYY-MM-DD
    time_secs   = Column(Integer, nullable=False)
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_tentaizu_easy_scores_date_time", "puzzle_date", "time_secs"),
    )

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "puzzle_date": self.puzzle_date,
            "time_secs":   self.time_secs,
            "created_at":  self.created_at.strftime("%Y-%m-%d"),
        }

# ── Cylinder Score model (permanent — never reset) ────────────────────────────
class CylinderScore(Base):
    __tablename__ = "cylinder_scores"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(32), nullable=False)
    user_email = Column(String(256), nullable=True, index=True)
    cyl_mode     = Column(String(32), nullable=False)   # easy/intermediate/expert/custom
    time_secs    = Column(Integer, nullable=False)
    time_ms      = Column(Integer, nullable=True)
    rows         = Column(Integer, nullable=False)
    cols         = Column(Integer, nullable=False)
    mines        = Column(Integer, nullable=False)
    no_guess     = Column(Boolean, default=False, nullable=False)
    board_hash   = Column(String(128), nullable=True)
    bbbv         = Column(Integer, nullable=True)
    left_clicks  = Column(Integer, nullable=True)
    right_clicks = Column(Integer, nullable=True)
    chord_clicks = Column(Integer, nullable=True)
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_cylinder_scores_mode_time", "cyl_mode", "time_secs"),
    )

    def to_dict(self):
        return {
            "id":        self.id,
            "name":      self.name,
            "cyl_mode":  self.cyl_mode,
            "time_secs": self.time_secs,
            "rows":      self.rows,
            "cols":      self.cols,
            "mines":     self.mines,
            "created_at": self.created_at.strftime("%Y-%m-%d"),
        }

# ── Toroid Score model (permanent — never reset) ──────────────────────────────
class ToroidScore(Base):
    __tablename__ = "toroid_scores"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(32), nullable=False)
    user_email = Column(String(256), nullable=True, index=True)
    tor_mode     = Column(String(32), nullable=False)   # easy/intermediate/expert/custom
    time_secs    = Column(Integer, nullable=False)
    time_ms      = Column(Integer, nullable=True)
    rows         = Column(Integer, nullable=False)
    cols         = Column(Integer, nullable=False)
    mines        = Column(Integer, nullable=False)
    no_guess     = Column(Boolean, default=False, nullable=False)
    board_hash   = Column(String(128), nullable=True)
    bbbv         = Column(Integer, nullable=True)
    left_clicks  = Column(Integer, nullable=True)
    right_clicks = Column(Integer, nullable=True)
    chord_clicks = Column(Integer, nullable=True)
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_toroid_scores_mode_time", "tor_mode", "time_secs"),
    )

    def to_dict(self):
        return {
            "id":        self.id,
            "name":      self.name,
            "tor_mode":  self.tor_mode,
            "time_secs": self.time_secs,
            "rows":      self.rows,
            "cols":      self.cols,
            "mines":     self.mines,
            "created_at": self.created_at.strftime("%Y-%m-%d"),
        }

# ── User profile model (display name, one row per user) ──────────────────────
class UserProfile(Base):
    __tablename__ = "user_profiles"

    email         = Column(String(256), primary_key=True)
    display_name  = Column(String(32), nullable=False)
    public_id     = Column(String(36), unique=True, nullable=True, index=True)
    is_public     = Column(Boolean, default=False, nullable=False)
    favorite_game = Column(String(32), nullable=True)
    vanity_slug   = Column(String(32), unique=True, nullable=True, index=True)
    pref_sounds   = Column(Boolean, default=False, nullable=False)
    pref_chording = Column(Boolean, default=True,  nullable=False)
    pref_skin     = Column(String(16), default='dark', nullable=False)
    about_text    = Column(String(5000), nullable=True)
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# ── Create tables if they don't exist ────────────────────────────────────────
def init_db():
    Base.metadata.create_all(bind=engine)
