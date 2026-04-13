"""
database.py — SQLAlchemy setup for MySQL via PyMySQL
"""
from sqlalchemy import (
    create_engine, Column, Integer, BigInteger, String, Float,
    DateTime, Date, Enum, Index, Boolean, text, Text
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime, timezone
import enum

# ── Config — replace with your real credentials ───────────────────────────────
DB_USER     = "the_minesweeper_user"
DB_PASSWORD = "the_password"
DB_HOST     = "localhost"
DB_PORT     = 3306
DB_NAME     = "the_db_name"

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
    guest_token  = Column(String(36), nullable=True, index=True)  # links guest score to login session
    client_type  = Column(String(32), nullable=False, server_default="na")  # chrome/firefox/safari/edge/mobile_browser/ios_app/android_app/na
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Fast lookups by mode + time for leaderboard queries
    __table_args__ = (
        Index("ix_scores_mode_time", "mode", "time_secs"),
    )

    def to_dict(self):
        return {
            "id":           self.id,
            "name":         self.name,
            "user_email":   self.user_email,
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
    client_type  = Column(String(32), nullable=False, server_default="na")
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
    rush_mode    = Column(String(16), nullable=False)  # easy/normal/hard/custom
    guest_token  = Column(String(36), nullable=True, index=True)
    client_type  = Column(String(32), nullable=False, server_default="na")
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))

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
    guest_token = Column(String(36), nullable=True, index=True)
    client_type = Column(String(32), nullable=False, server_default="na")
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
    client_type = Column(String(32), nullable=False, server_default="na")
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

# ── Mosaic Score model ────────────────────────────────────────────────────────
class MosaicScore(Base):
    __tablename__ = "mosaic_scores"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(32), nullable=False)
    user_email  = Column(String(256), nullable=True, index=True)
    puzzle_date = Column(String(10), nullable=False)   # YYYY-MM-DD
    time_secs   = Column(Integer, nullable=False)
    guest_token = Column(String(36), nullable=True, index=True)
    client_type = Column(String(32), nullable=False, server_default="na")
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_mosaic_scores_date_time", "puzzle_date", "time_secs"),
    )

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "puzzle_date": self.puzzle_date,
            "time_secs":   self.time_secs,
            "created_at":  self.created_at.strftime("%Y-%m-%d"),
        }

# ── Mosaic Easy Score model ────────────────────────────────────────────────────
class MosaicEasyScore(Base):
    __tablename__ = "mosaic_easy_scores"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(32), nullable=False)
    user_email  = Column(String(256), nullable=True, index=True)
    puzzle_date = Column(String(10), nullable=False)   # YYYY-MM-DD
    time_secs   = Column(Integer, nullable=False)
    guest_token = Column(String(36), nullable=True, index=True)
    client_type = Column(String(32), nullable=False, server_default="na")
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_mosaic_easy_scores_date_time", "puzzle_date", "time_secs"),
    )

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "puzzle_date": self.puzzle_date,
            "time_secs":   self.time_secs,
            "created_at":  self.created_at.strftime("%Y-%m-%d"),
        }

# ── Mosaic Custom Score model (per hash+mask board) ──────────────────────────
class MosaicCustomScore(Base):
    __tablename__ = "mosaic_custom_scores"

    id         = Column(Integer, primary_key=True, index=True)
    board_id   = Column(String(64), nullable=False)   # SHA-256 of "RxC:hash:mask"
    name       = Column(String(32), nullable=False)
    user_email = Column(String(256), nullable=True, index=True)
    time_secs  = Column(Integer, nullable=False)
    guest_token = Column(String(36), nullable=True, index=True)
    client_type = Column(String(32), nullable=False, server_default="na")
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_mosaic_custom_board_time", "board_id", "time_secs"),
    )

    def to_dict(self):
        return {
            "id":        self.id,
            "name":      self.name,
            "board_id":  self.board_id,
            "time_secs": self.time_secs,
            "created_at": self.created_at.strftime("%Y-%m-%d"),
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
    guest_token  = Column(String(36), nullable=True, index=True)
    client_type  = Column(String(32), nullable=False, server_default="na")
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_cylinder_scores_mode_time", "cyl_mode", "time_secs"),
    )

    def to_dict(self):
        return {
            "id":           self.id,
            "name":         self.name,
            "cyl_mode":     self.cyl_mode,
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
    guest_token  = Column(String(36), nullable=True, index=True)
    client_type  = Column(String(32), nullable=False, server_default="na")
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_toroid_scores_mode_time", "tor_mode", "time_secs"),
    )

    def to_dict(self):
        return {
            "id":           self.id,
            "name":         self.name,
            "tor_mode":     self.tor_mode,
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

# ── Replay Score model (board-specific scores, all topologies) ───────────────
class ReplayScore(Base):
    __tablename__ = "replay_scores"

    id           = Column(Integer, primary_key=True, index=True)
    board_hash   = Column(String(128), nullable=False, index=True)
    variant      = Column(String(16), nullable=False)   # standard / cylinder / toroid
    name         = Column(String(32), nullable=False)
    user_email   = Column(String(256), nullable=True, index=True)
    time_secs    = Column(Integer, nullable=False)
    time_ms      = Column(Integer, nullable=True)
    rows         = Column(Integer, nullable=False)
    cols         = Column(Integer, nullable=False)
    mines        = Column(Integer, nullable=False)
    bbbv         = Column(Integer, nullable=True)
    left_clicks  = Column(Integer, nullable=True)
    right_clicks = Column(Integer, nullable=True)
    chord_clicks = Column(Integer, nullable=True)
    guest_token  = Column(String(36), nullable=True, index=True)
    client_type  = Column(String(32), nullable=False, server_default="na")
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_replay_scores_hash_variant_time", "board_hash", "variant", "time_ms"),
    )

    def to_dict(self):
        return {
            "id":           self.id,
            "board_hash":   self.board_hash,
            "variant":      self.variant,
            "name":         self.name,
            "time_secs":    self.time_secs,
            "time_ms":      self.time_ms,
            "rows":         self.rows,
            "cols":         self.cols,
            "mines":        self.mines,
            "bbbv":         self.bbbv,
            "left_clicks":  self.left_clicks,
            "right_clicks": self.right_clicks,
            "chord_clicks": self.chord_clicks,
            "created_at":   self.created_at.strftime("%Y-%m-%d"),
        }


# ── Hexsweeper Score model (permanent — never reset) ─────────────────────────
class HexsweeperScore(Base):
    __tablename__ = "hexsweeper_scores"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(32), nullable=False)
    user_email = Column(String(256), nullable=True, index=True)
    hex_mode     = Column(String(32), nullable=False)   # beginner/intermediate/expert/custom
    time_secs    = Column(Integer, nullable=False)
    time_ms      = Column(Integer, nullable=True)
    radius       = Column(Integer, nullable=False)
    mines        = Column(Integer, nullable=False)
    board_hash   = Column(String(128), nullable=True)
    bbbv         = Column(Integer, nullable=True)
    left_clicks  = Column(Integer, nullable=True)
    right_clicks = Column(Integer, nullable=True)
    chord_clicks = Column(Integer, nullable=True)
    guest_token  = Column(String(36), nullable=True, index=True)
    client_type  = Column(String(32), nullable=False, server_default="na")
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_hexsweeper_scores_mode_time", "hex_mode", "time_secs"),
    )

    def to_dict(self):
        return {
            "id":           self.id,
            "name":         self.name,
            "hex_mode":     self.hex_mode,
            "time_secs":    self.time_secs,
            "time_ms":      self.time_ms,
            "radius":       self.radius,
            "mines":        self.mines,
            "board_hash":   self.board_hash,
            "bbbv":         self.bbbv,
            "left_clicks":  self.left_clicks,
            "right_clicks": self.right_clicks,
            "chord_clicks": self.chord_clicks,
            "created_at":   self.created_at.strftime("%Y-%m-%d"),
        }


# ── Globesweeper Score model ──────────────────────────────────────────────────
class GlobesweeperScore(Base):
    __tablename__ = "globesweeper_scores"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(32), nullable=False)
    user_email = Column(String(256), nullable=True, index=True)
    glob_mode  = Column(String(20), nullable=False)   # dodecahedron/beginner/intermediate/expert/custom
    time_ms    = Column(Integer, nullable=False)
    t_param    = Column(Integer, nullable=False)       # Goldberg T value (e.g. 1, 3, 7, 25)
    face_count = Column(Integer, nullable=False)       # 10*T+2
    mines      = Column(Integer, nullable=False)
    bbbv        = Column(Integer, nullable=True)        # 3BV of the solved board
    left_clicks = Column(Integer, nullable=True)        # non-rotation left clicks
    board_hash = Column(String(128), nullable=True)
    guest_token = Column(String(36), nullable=True, index=True)
    client_type = Column(String(32), nullable=False, server_default="na")
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_globesweeper_scores_mode_time", "glob_mode", "time_ms"),
    )

    def to_dict(self):
        bbbv_s = f"{self.bbbv / (self.time_ms / 1000):.2f}" if self.bbbv and self.time_ms else "—"
        eff    = f"{round(self.bbbv / self.left_clicks * 100)}%" if (self.bbbv and self.left_clicks) else "—"
        return {
            "id":          self.id,
            "name":        self.name,
            "glob_mode":   self.glob_mode,
            "time_ms":     self.time_ms,
            "t_param":     self.t_param,
            "face_count":  self.face_count,
            "mines":       self.mines,
            "bbbv":        self.bbbv if self.bbbv else "—",
            "bbbv_s":      bbbv_s,
            "eff":         eff,
            "left_clicks": self.left_clicks if self.left_clicks else "—",
            "board_hash":  self.board_hash,
            "created_at":  self.created_at.strftime("%Y-%m-%d"),
        }


# ── CubeSweeper Score model ───────────────────────────────────────────────────
class CubesweeperScore(Base):
    __tablename__ = "cubesweeper_scores"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(32), nullable=False)
    user_email  = Column(String(256), nullable=True, index=True)
    cube_mode   = Column(String(20), nullable=False)   # beginner/intermediate/expert/custom
    grid_size   = Column(Integer, nullable=False)      # N (cells per face edge)
    time_ms     = Column(Integer, nullable=False)
    mines       = Column(Integer, nullable=False)
    no_guess    = Column(Boolean, default=False, nullable=False)
    bbbv        = Column(Integer, nullable=True)
    left_clicks = Column(Integer, nullable=True)
    board_hash  = Column(String(512), nullable=True)
    guest_token = Column(String(36), nullable=True, index=True)
    client_type = Column(String(32), nullable=False, server_default="na")
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_cubesweeper_scores_mode_ng_time", "cube_mode", "no_guess", "time_ms"),
    )

    def to_dict(self):
        bbbv_s = f"{self.bbbv / (self.time_ms / 1000):.2f}" if self.bbbv and self.time_ms else "—"
        eff    = f"{round(self.bbbv / self.left_clicks * 100)}%" if (self.bbbv and self.left_clicks) else "—"
        return {
            "id":          self.id,
            "name":        self.name,
            "cube_mode":   self.cube_mode,
            "grid_size":   self.grid_size,
            "time_ms":     self.time_ms,
            "mines":       self.mines,
            "no_guess":    self.no_guess,
            "bbbv":        self.bbbv if self.bbbv else "—",
            "bbbv_s":      bbbv_s,
            "eff":         eff,
            "left_clicks": self.left_clicks if self.left_clicks else "—",
            "board_hash":  self.board_hash,
            "created_at":  self.created_at.strftime("%Y-%m-%d"),
        }


# ── Guest Score Archive (scores from unregistered players archived at midnight) ─
class GuestScoreArchive(Base):
    __tablename__ = "guest_score_archive"

    id                  = Column(Integer, primary_key=True, index=True)
    source_table        = Column(String(32), nullable=False, index=True)  # e.g. 'scores', 'rush_scores'
    original_id         = Column(Integer, nullable=False)
    guest_token         = Column(String(36), nullable=True, index=True)
    name                = Column(String(32), nullable=True)
    game_mode           = Column(String(32), nullable=True)   # mode/rush_mode/cyl_mode etc.
    time_ms             = Column(Integer, nullable=True)
    rows                = Column(Integer, nullable=True)
    cols                = Column(Integer, nullable=True)
    mines               = Column(Integer, nullable=True)
    bbbv                = Column(Integer, nullable=True)
    board_hash          = Column(String(128), nullable=True)
    original_created_at = Column(DateTime, nullable=True)
    archived_at         = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── PvP Result model (one row per completed PvP match) ───────────────────────
class PvpResult(Base):
    __tablename__ = "pvp_results"

    id            = Column(Integer, primary_key=True, index=True)
    winner_name   = Column(String(32), nullable=True)
    winner_email  = Column(String(256), nullable=True, index=True)
    loser_name    = Column(String(32), nullable=True)
    loser_email   = Column(String(256), nullable=True, index=True)
    elapsed_ms    = Column(Integer, nullable=False)   # winner's elapsed time in ms
    submode       = Column(String(16), nullable=False)  # standard / quick
    rows          = Column(Integer, nullable=False)
    cols          = Column(Integer, nullable=False)
    mines         = Column(Integer, nullable=False)
    board_hash    = Column(String(128), nullable=True)
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_pvp_results_winner_email_date", "winner_email", "created_at"),
    )

    def to_dict(self):
        return {
            "id":           self.id,
            "winner_name":  self.winner_name,
            "winner_email": self.winner_email,
            "loser_name":   self.loser_name,
            "elapsed_ms":   self.elapsed_ms,
            "submode":      self.submode,
            "rows":         self.rows,
            "cols":         self.cols,
            "mines":        self.mines,
            "created_at":   self.created_at.strftime("%Y-%m-%d"),
        }

# ── Anonymous PvP archive (unregistered-user results, archived nightly) ──────
class AnonymousPvpResult(Base):
    __tablename__ = "anonymous_pvp_results"

    id            = Column(Integer, primary_key=True, index=True)
    winner_name   = Column(String(32), nullable=True)
    winner_email  = Column(String(256), nullable=True)
    loser_name    = Column(String(32), nullable=True)
    loser_email   = Column(String(256), nullable=True)
    elapsed_ms    = Column(Integer, nullable=False)
    submode       = Column(String(16), nullable=False)
    rows          = Column(Integer, nullable=False)
    cols          = Column(Integer, nullable=False)
    mines         = Column(Integer, nullable=False)
    board_hash    = Column(String(128), nullable=True)
    created_at    = Column(DateTime, nullable=False)
    archived_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))


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
    pvp_elo       = Column(Integer, default=1200, nullable=False)
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# ── Server Stats model (hourly snapshots) ─────────────────────────────────────
class ServerStats(Base):
    __tablename__ = "server_stats"

    id             = Column(Integer, primary_key=True, index=True)
    recorded_at    = Column(DateTime, nullable=False, index=True)
    cpu_percent    = Column(Float,      nullable=False)
    mem_used_mb    = Column(Float,      nullable=False)
    mem_total_mb   = Column(Float,      nullable=False)
    mem_percent    = Column(Float,      nullable=False)
    disk_used_gb   = Column(Float,      nullable=False)
    disk_total_gb  = Column(Float,      nullable=False)
    disk_percent   = Column(Float,      nullable=False)
    db_size_mb     = Column(Float,      nullable=False)
    net_bytes_sent = Column(BigInteger, nullable=False)   # cumulative since boot
    net_bytes_recv = Column(BigInteger, nullable=False)   # cumulative since boot
    net_delta_sent = Column(BigInteger, nullable=True)    # bytes sent in this hour
    net_delta_recv = Column(BigInteger, nullable=True)    # bytes received in this hour
    http_requests  = Column(Integer,    nullable=False, default=0)  # requests this hour


# ── Blog Comment model ────────────────────────────────────────────────────────
# ── Web Traffic Stats (daily, parsed from Apache access logs) ─────────────────
class WebTrafficStats(Base):
    __tablename__ = "web_traffic_stats"

    id              = Column(Integer, primary_key=True, index=True)
    stat_date       = Column(Date, nullable=False, unique=True, index=True)
    total_requests  = Column(Integer, nullable=False, default=0)
    unique_ips      = Column(Integer, nullable=False, default=0)
    # 2xx
    http_200        = Column(Integer, nullable=False, default=0)
    http_201        = Column(Integer, nullable=False, default=0)
    http_206        = Column(Integer, nullable=False, default=0)
    # 1xx / protocol upgrade
    http_101        = Column(Integer, nullable=False, default=0)
    # 3xx
    http_302        = Column(Integer, nullable=False, default=0)
    http_304        = Column(Integer, nullable=False, default=0)
    http_307        = Column(Integer, nullable=False, default=0)
    # 4xx
    http_403        = Column(Integer, nullable=False, default=0)
    http_404        = Column(Integer, nullable=False, default=0)
    http_405        = Column(Integer, nullable=False, default=0)
    http_422        = Column(Integer, nullable=False, default=0)
    # 5xx
    http_500        = Column(Integer, nullable=False, default=0)
    http_503        = Column(Integer, nullable=False, default=0)
    recorded_at     = Column(DateTime, nullable=True)


class BlogComment(Base):
    __tablename__ = "blog_comments"

    id           = Column(Integer, primary_key=True, index=True)
    post_slug    = Column(String(128), nullable=False, index=True)
    user_email   = Column(String(256), nullable=False, index=True)
    display_name = Column(String(64), nullable=False)
    body         = Column(String(2000), nullable=False)
    approved     = Column(Boolean, default=False, nullable=False, index=True)
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_blog_comments_slug_approved", "post_slug", "approved"),
    )


# ── Nonosweeper Score model ────────────────────────────────────────────────────
class NonosweeperScore(Base):
    __tablename__ = "nonosweeper_scores"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(32), nullable=False)
    user_email  = Column(String(256), nullable=True, index=True)
    puzzle_date = Column(String(10), nullable=False)   # YYYY-MM-DD
    difficulty  = Column(String(16), nullable=False)   # beginner|intermediate|expert
    time_secs   = Column(Integer, nullable=False)
    guest_token = Column(String(36), nullable=True, index=True)
    client_type = Column(String(32), nullable=False, server_default="na")
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_nonosweeper_scores_date_diff_time", "puzzle_date", "difficulty", "time_secs"),
    )

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "puzzle_date": self.puzzle_date,
            "difficulty":  self.difficulty,
            "time_secs":   self.time_secs,
            "created_at":  self.created_at.strftime("%Y-%m-%d"),
        }


# ── 15-Puzzle Score model ─────────────────────────────────────────────────────
class FifteenPuzzleScore(Base):
    __tablename__ = "fifteen_puzzle_scores"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(32), nullable=False)
    user_email  = Column(String(256), nullable=True, index=True)
    puzzle_date = Column(String(10), nullable=False)   # YYYY-MM-DD UTC
    time_ms     = Column(Integer, nullable=False)
    moves       = Column(Integer, nullable=False)
    guest_token = Column(String(36), nullable=True, index=True)
    client_type = Column(String(32), nullable=False, server_default="na")
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_fifteen_puzzle_scores_date_time", "puzzle_date", "time_ms"),
    )

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "puzzle_date": self.puzzle_date,
            "time_ms":     self.time_ms,
            "moves":       self.moves,
            "created_at":  self.created_at.strftime("%Y-%m-%d"),
        }


# ── 15-Puzzle Photo model ─────────────────────────────────────────────────────
class FifteenPuzzlePhoto(Base):
    __tablename__ = "fifteen_puzzle_photos"

    id           = Column(Integer, primary_key=True, index=True)
    user_email   = Column(String(256), nullable=False, index=True)
    filename     = Column(String(256), nullable=False)   # stored filename on disk
    display_name = Column(String(128), nullable=True)    # user-supplied title
    photo_mode   = Column(String(8),   nullable=False)   # 'tiles' or 'reveal'
    board_hash   = Column(String(128), nullable=False, unique=True, index=True)
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── 2048 Score model ─────────────────────────────────────────────────────────
class Game2048Score(Base):
    __tablename__ = "game_2048_scores"

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String(32), nullable=False)
    user_email     = Column(String(256), nullable=True, index=True)
    puzzle_date    = Column(String(10), nullable=False)   # YYYY-MM-DD UTC
    score          = Column(Integer, nullable=False)
    time_ms        = Column(Integer, nullable=False)
    moves          = Column(Integer, nullable=False)
    fours_spawned  = Column(Integer, nullable=True)   # number of 4-tiles spawned during the game
    moves_to_2048  = Column(Integer, nullable=True)   # move number when 2048 was first reached; NULL if not reached
    guest_token    = Column(String(36), nullable=True, index=True)
    client_type    = Column(String(32), nullable=False, server_default="na")
    created_at     = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_game_2048_scores_date_score", "puzzle_date", "score"),
    )

    def to_dict(self):
        return {
            "id":            self.id,
            "name":          self.name,
            "puzzle_date":   self.puzzle_date,
            "score":         self.score,
            "time_ms":       self.time_ms,
            "moves":         self.moves,
            "fours_spawned": self.fours_spawned,
            "moves_to_2048": self.moves_to_2048,
            "created_at":    self.created_at.strftime("%Y-%m-%d"),
        }


# ── 2048 Hexagon Score model ──────────────────────────────────────────────────
class Game2048HexScore(Base):
    __tablename__ = "game_2048hex_scores"

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String(32), nullable=False)
    user_email     = Column(String(256), nullable=True, index=True)
    puzzle_date    = Column(String(10), nullable=False)   # YYYY-MM-DD UTC
    score          = Column(Integer, nullable=False)
    time_ms        = Column(Integer, nullable=False)
    moves          = Column(Integer, nullable=False)
    fours_spawned  = Column(Integer, nullable=True)   # number of 4-tiles spawned during the game
    moves_to_2048  = Column(Integer, nullable=True)   # move number when 2048 was first reached; NULL if not reached
    guest_token    = Column(String(36), nullable=True, index=True)
    client_type    = Column(String(32), nullable=False, server_default="na")
    created_at     = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_game_2048hex_scores_date_score", "puzzle_date", "score"),
    )

    def to_dict(self):
        return {
            "id":            self.id,
            "name":          self.name,
            "puzzle_date":   self.puzzle_date,
            "score":         self.score,
            "time_ms":       self.time_ms,
            "moves":         self.moves,
            "fours_spawned": self.fours_spawned,
            "moves_to_2048": self.moves_to_2048,
            "created_at":    self.created_at.strftime("%Y-%m-%d"),
        }


# ── Schulte Grid Score model ──────────────────────────────────────────────────
class SchulteGridScore(Base):
    __tablename__ = "schulte_grid_scores"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(32), nullable=False)
    user_email  = Column(String(256), nullable=True, index=True)
    mode        = Column(String(16), nullable=False)   # normal|easy|blind_normal|blind_easy|easy_mix|mix
    board_size  = Column(Integer, nullable=False)       # 3–10
    time_ms     = Column(Integer, nullable=False)
    puzzle_date = Column(String(10), nullable=False)   # YYYY-MM-DD UTC (for daily reset)
    guest_token = Column(String(36), nullable=True, index=True)
    client_type = Column(String(32), nullable=False, server_default="na")
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_schulte_grid_scores_date_mode_size_time", "puzzle_date", "mode", "board_size", "time_ms"),
        Index("ix_schulte_grid_scores_email_mode_size_time", "user_email", "mode", "board_size", "time_ms"),
    )

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "mode":        self.mode,
            "board_size":  self.board_size,
            "time_ms":     self.time_ms,
            "puzzle_date": self.puzzle_date,
            "created_at":  self.created_at.strftime("%Y-%m-%d"),
        }


# ── Contact Message model ─────────────────────────────────────────────────────
class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(128), nullable=False)
    email      = Column(String(256), nullable=False)
    message    = Column(String(4000), nullable=False)
    read       = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── Mahjong Solitaire Score model ─────────────────────────────────────────────
class MahjongScore(Base):
    __tablename__ = "mahjong_scores"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(32), nullable=False)
    user_email  = Column(String(256), nullable=True, index=True)
    puzzle_date = Column(String(10), nullable=False)   # YYYY-MM-DD UTC
    board_hash  = Column(String(200), nullable=False)
    time_ms     = Column(Integer, nullable=False)
    guest_token = Column(String(36), nullable=True, index=True)
    client_type = Column(String(32), nullable=False, server_default="na")
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_mahjong_scores_date_time", "puzzle_date", "time_ms"),
        Index("ix_mahjong_scores_hash_time", "board_hash", "time_ms"),
    )

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "puzzle_date": self.puzzle_date,
            "board_hash":  self.board_hash,
            "time_ms":     self.time_ms,
            "created_at":  self.created_at.strftime("%Y-%m-%d"),
        }


# ── Mahjong Solitaire Saved Game model ────────────────────────────────────────
class MahjongSavedGame(Base):
    __tablename__ = "mahjong_saved_games"

    id            = Column(Integer, primary_key=True, index=True)
    user_email    = Column(String(256), nullable=False, index=True)
    board_hash    = Column(String(200), nullable=False)
    puzzle_date   = Column(String(10), nullable=False)   # YYYY-MM-DD UTC
    elapsed_ms    = Column(Integer, nullable=False, default=0)
    removed_pairs = Column(String(4000), nullable=False, default="[]")  # JSON array
    updated_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_mahjong_saved_games_user_hash", "user_email", "board_hash", unique=True),
    )


# ── Jigsaw Score model ────────────────────────────────────────────────────────
class JigsawScore(Base):
    __tablename__ = "jigsaw_scores"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(32), nullable=False)
    user_email  = Column(String(256), nullable=True, index=True)
    puzzle_date = Column(String(10), nullable=False)   # YYYY-MM-DD UTC
    difficulty  = Column(String(16), nullable=False)   # beginner|intermediate|expert
    image_name  = Column(String(256), nullable=False)
    time_ms     = Column(Integer, nullable=False)
    guest_token = Column(String(36), nullable=True, index=True)
    client_type = Column(String(32), nullable=False, server_default="na")
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_jigsaw_scores_date_diff_time", "puzzle_date", "difficulty", "time_ms"),
    )

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "puzzle_date": self.puzzle_date,
            "difficulty":  self.difficulty,
            "time_ms":     self.time_ms,
            "created_at":  self.created_at.strftime("%Y-%m-%d"),
        }


# ── Jigsaw Saved Game model ───────────────────────────────────────────────────
class JigsawSavedGame(Base):
    __tablename__ = "jigsaw_saved_games"

    id          = Column(Integer, primary_key=True, index=True)
    user_email  = Column(String(256), nullable=False, index=True)
    puzzle_date = Column(String(10), nullable=False)
    difficulty  = Column(String(16), nullable=False)
    image_name  = Column(String(256), nullable=False)
    elapsed_ms  = Column(Integer, nullable=False, default=0)
    piece_state = Column(Text, nullable=False, default="[]")  # JSON [{id,x,y,groupId}]
    updated_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_jigsaw_saved_user_date_diff", "user_email", "puzzle_date", "difficulty",
              unique=True),
    )


# ── Jigsaw Photo model (custom generator uploads) ─────────────────────────────
class JigsawPhoto(Base):
    __tablename__ = "jigsaw_photos"

    id           = Column(Integer, primary_key=True, index=True)
    user_email   = Column(String(256), nullable=False, index=True)
    filename     = Column(String(256), nullable=False)
    display_name = Column(String(128), nullable=True)
    board_hash   = Column(String(128), nullable=False, unique=True, index=True)
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── F74 Rewind replay log ─────────────────────────────────────────────────────
class GameReplay(Base):
    __tablename__ = "game_replays"

    id         = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(256), nullable=True, index=True)
    mode       = Column(String(32),  nullable=True)          # beginner/intermediate/expert/custom/daily/…
    rows       = Column(Integer,     nullable=False)
    cols       = Column(Integer,     nullable=False)
    mines      = Column(Integer,     nullable=False)
    no_guess   = Column(Boolean,     default=False, nullable=False)
    board_hash = Column(String(128), nullable=True)
    time_ms    = Column(Integer,     nullable=True)
    log_json   = Column(Text,        nullable=False)          # JSON array of [t_ms, type, r, c]
    created_at = Column(DateTime,    default=lambda: datetime.now(timezone.utc))


# ── Create tables if they don't exist ────────────────────────────────────────
def init_db():
    Base.metadata.create_all(bind=engine)
    _apply_migrations()
    _seed_bot_profiles()


# ── Bot PvP profiles ──────────────────────────────────────────────────────────
_BOT_PROFILES = [
    {"email": "bot-easy@bot.minesweeper.org",   "display_name": "🤖 Bot (Easy)",   "pvp_elo": 1000},
    {"email": "bot-medium@bot.minesweeper.org", "display_name": "🤖 Bot (Medium)", "pvp_elo": 1200},
    {"email": "bot-hard@bot.minesweeper.org",   "display_name": "🤖 Bot (Hard)",   "pvp_elo": 1400},
]

def _seed_bot_profiles():
    """Create UserProfile rows for the three bots if they don't already exist."""
    db = SessionLocal()
    try:
        for bp in _BOT_PROFILES:
            if not db.query(UserProfile).filter(UserProfile.email == bp["email"]).first():
                db.add(UserProfile(
                    email        = bp["email"],
                    display_name = bp["display_name"],
                    pvp_elo      = bp["pvp_elo"],
                    is_public    = False,
                ))
        db.commit()
    finally:
        db.close()


def _apply_migrations():
    """Idempotent ALTER TABLE migrations for columns added after initial deploy."""
    migrations = [
        ("scores",                "guest_token",  "VARCHAR(36) NULL"),
        ("rush_scores",           "guest_token",  "VARCHAR(36) NULL"),
        ("cylinder_scores",       "guest_token",  "VARCHAR(36) NULL"),
        ("toroid_scores",         "guest_token",  "VARCHAR(36) NULL"),
        ("tentaizu_scores",       "guest_token",  "VARCHAR(36) NULL"),
        ("replay_scores",         "guest_token",  "VARCHAR(36) NULL"),
        ("pvp_results",           "board_hash",   "VARCHAR(128) NULL"),
        ("user_profiles",         "pvp_elo",      "INT NOT NULL DEFAULT 1200"),
        # client_type tracking (added 2026-03-27); historical rows default to 'na'
        ("scores",                "client_type",  "VARCHAR(32) NOT NULL DEFAULT 'na'"),
        ("game_history",          "client_type",  "VARCHAR(32) NOT NULL DEFAULT 'na'"),
        ("rush_scores",           "client_type",  "VARCHAR(32) NOT NULL DEFAULT 'na'"),
        ("tentaizu_scores",       "client_type",  "VARCHAR(32) NOT NULL DEFAULT 'na'"),
        ("tentaizu_easy_scores",  "client_type",  "VARCHAR(32) NOT NULL DEFAULT 'na'"),
        ("mosaic_scores",         "client_type",  "VARCHAR(32) NOT NULL DEFAULT 'na'"),
        ("mosaic_easy_scores",    "client_type",  "VARCHAR(32) NOT NULL DEFAULT 'na'"),
        ("mosaic_custom_scores",  "client_type",  "VARCHAR(32) NOT NULL DEFAULT 'na'"),
        ("cylinder_scores",       "client_type",  "VARCHAR(32) NOT NULL DEFAULT 'na'"),
        ("toroid_scores",         "client_type",  "VARCHAR(32) NOT NULL DEFAULT 'na'"),
        ("replay_scores",         "client_type",  "VARCHAR(32) NOT NULL DEFAULT 'na'"),
        ("hexsweeper_scores",     "client_type",  "VARCHAR(32) NOT NULL DEFAULT 'na'"),
        ("globesweeper_scores",   "client_type",  "VARCHAR(32) NOT NULL DEFAULT 'na'"),
        # 3BV + click tracking for Worldsweeper (added 2026-03-29)
        ("globesweeper_scores",   "bbbv",         "INT NULL"),
        ("globesweeper_scores",   "left_clicks",  "INT NULL"),
        ("nonosweeper_scores",    "client_type",  "VARCHAR(32) NOT NULL DEFAULT 'na'"),
        # nonosweeper user/guest tracking — missing from initial deploy
        ("nonosweeper_scores",    "user_email",   "VARCHAR(256) NULL"),
        ("nonosweeper_scores",    "guest_token",  "VARCHAR(36) NULL"),
        # 15-puzzle generator: per-user saved puzzle limit (added 2026-03-30)
        ("user_profiles",         "puzzle_storage_limit", "INT NOT NULL DEFAULT 32"),
        # F68 Jigsaw: tables created via create_all; no column migrations needed yet
    ]
    with engine.connect() as conn:
        for table, column, col_def in migrations:
            exists = conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.columns "
                    "WHERE table_schema = DATABASE() "
                    "AND table_name = :tbl AND column_name = :col"
                ),
                {"tbl": table, "col": column},
            ).scalar()
            if not exists:
                conn.execute(text(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {col_def}"))
                conn.commit()
