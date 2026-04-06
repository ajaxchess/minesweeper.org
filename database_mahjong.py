"""
Mahjong Solitaire database models — defined here (tracked in git) so
the server's database.py does not need to be modified manually before
the new routes can start.  main.py imports MahjongScore and
MahjongSavedGame from this module.
"""
from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone

# Re-use the same Base (and therefore the same metadata / engine) as the
# rest of the app by importing from the live database module.
try:
    from database import Base, engine, init_db as _orig_init_db
    _standalone = False
except ImportError:                          # local dev without database.py
    class Base(DeclarativeBase): pass
    engine = None
    _standalone = True


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


class MahjongSavedGame(Base):
    __tablename__ = "mahjong_saved_games"

    id            = Column(Integer, primary_key=True, index=True)
    user_email    = Column(String(256), nullable=False, index=True)
    board_hash    = Column(String(200), nullable=False)
    puzzle_date   = Column(String(10), nullable=False)   # YYYY-MM-DD UTC
    elapsed_ms    = Column(Integer, nullable=False, default=0)
    removed_pairs = Column(String(4000), nullable=False, default="[]")
    updated_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_mahjong_saved_games_user_hash", "user_email", "board_hash", unique=True),
    )


def create_mahjong_tables():
    """Create mahjong tables if they don't already exist."""
    if engine is not None:
        Base.metadata.create_all(bind=engine)
