"""
phase2_analyzer — Move-log analyzer for minesweeper.org

Public API:
    analyze_game(game)              — run every pass over one game
    analyze_replay_async(id, db)    — FastAPI worker hook
    backfill_analyses(db)           — backfill historical games
    persist_analysis(...)           — write analysis to DB
    GameAnalysis                    — SQLAlchemy model

Citations are in dard_framework_synthesis.md.
"""

from .pipeline import (
    ANALYZER_VERSION,
    GameAnalysis,
    analyze_game,
    analyze_replay_async,
    backfill_analyses,
    detect_anomalies,
    persist_analysis,
)
from .types import (
    Action,
    Difficulty,
    FullAnalysis,
    Game,
    Move,
    Outcome,
)

__all__ = [
    "ANALYZER_VERSION",
    "Action",
    "Difficulty",
    "FullAnalysis",
    "Game",
    "GameAnalysis",
    "Move",
    "Outcome",
    "analyze_game",
    "analyze_replay_async",
    "backfill_analyses",
    "detect_anomalies",
    "persist_analysis",
]
