"""
phase7_drills.response_models — Pydantic models for the drill API.

The API surface is small and intentionally so:

  POST /api/drills/start         -> DrillStartResponse
  POST /api/drills/{id}/submit   -> DrillSubmitResponse
  GET  /api/drills/{id}          -> DrillStateResponse

  GET  /drill/{id}               -> HTML (no Pydantic; rendered template)
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Visible board state (sent to client) — never includes mine layout
# ─────────────────────────────────────────────────────────────────────────────

class DrillBoardVisible(BaseModel):
    """The client-visible state of one drill board.

    `revealed` is the list of revealed cells as [row, col] pairs.
    `numbers` is the subset of revealed cells with adjacent mines > 0,
    encoded as [row, col, count] triples.
    """
    width: int
    height: int
    num_mines: int
    revealed: list[list[int]]
    numbers: list[list[int]]


# ─────────────────────────────────────────────────────────────────────────────
# Start a drill
# ─────────────────────────────────────────────────────────────────────────────

class DrillStartRequest(BaseModel):
    drill_type: Literal["l5_opening_recognition"] = "l5_opening_recognition"
    level: int = Field(5, ge=1, le=7)
    difficulty: str = Field("expert", pattern="^(beginner|intermediate|expert)$")
    mode: Literal["standard", "no_guess"] = "standard"
    num_boards: int = Field(10, ge=1, le=20)


class DrillStartResponse(BaseModel):
    drill_id: int
    drill_type: str
    level: int
    mode: str
    difficulty: str
    num_boards: int
    boards: list[DrillBoardVisible]
    drill_version: str
    started_at: str


# ─────────────────────────────────────────────────────────────────────────────
# Submit one board result
# ─────────────────────────────────────────────────────────────────────────────

class DrillSubmitRequest(BaseModel):
    board_index: int = Field(..., ge=0, le=19)
    chosen_row: int = Field(..., ge=0)
    chosen_col: int = Field(..., ge=0)
    decision_ms: int = Field(..., ge=0, le=600_000)


class DrillBoardResult(BaseModel):
    """Per-board verdict returned after a submit."""
    is_correct: bool
    is_mine: bool
    opening_size: int
    relative_quality: float
    optimal_row: int
    optimal_col: int
    optimal_opening_size: int


class DrillSummary(BaseModel):
    """Populated when all boards have been submitted."""
    num_correct: int
    num_total: int
    accuracy_pct: float
    avg_decision_ms: int
    mastery_contribution: float
    counted_toward_mastery: bool


class DrillSubmitResponse(BaseModel):
    drill_id: int
    board_index: int
    result: DrillBoardResult
    completed: bool
    summary: Optional[DrillSummary] = None


# ─────────────────────────────────────────────────────────────────────────────
# Drill state (for resume / refresh)
# ─────────────────────────────────────────────────────────────────────────────

class DrillAttempt(BaseModel):
    board_index: int
    chosen_row: int
    chosen_col: int
    decision_ms: int
    result: DrillBoardResult


class DrillStateResponse(BaseModel):
    drill_id: int
    player_id: str
    drill_type: str
    level: int
    mode: str
    difficulty: str
    num_boards: int
    started_at: str
    completed_at: Optional[str] = None
    boards: list[DrillBoardVisible]
    attempts: list[DrillAttempt]
    summary: Optional[DrillSummary] = None
    drill_version: str
