"""
phase4_routes.response_models — Pydantic response shapes for the analytics API.

One model per UI surface. Field names match the mockup field names so the
frontend can render directly from the API response without reshape.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Bootcamp
# ─────────────────────────────────────────────────────────────────────────────

class LevelMastery(BaseModel):
    level: int = Field(..., ge=1, le=7)
    name: str
    mastery: float = Field(..., ge=0, le=1)
    status: Literal["complete", "current", "locked"]
    tagline: str
    citation_url: Optional[str] = None


class HabitProgress(BaseModel):
    name: str
    progress_pct: float = Field(..., ge=0, le=1)
    state: Literal["done", "partial", "not_started"]


class DrillRecommendation(BaseModel):
    drill_id: str
    name: str
    board_count: int
    estimated_minutes: int
    target: str


class GraduationCriterion(BaseModel):
    description: str
    current_value: float
    target_value: float
    on_track: bool


class BootcampDiagnosis(BaseModel):
    """GET /api/bootcamp/diagnosis response."""
    player_id: str
    difficulty: str
    mode: Literal["standard", "no_guess"]
    current_level: int = Field(..., ge=1, le=7)
    current_level_name: str
    current_level_tagline: str
    progress_pct_to_next: float = Field(..., ge=0, le=1)
    blockers: list[str]
    # Top-strip stats
    best_time_ms: Optional[int]
    median_time_ms: Optional[int]
    three_bv_per_sec: float
    ioe: float
    correctness: float
    hierarchy_compliance_pct: float
    throughput: float
    # Level summary
    levels: list[LevelMastery]


class BootcampLevelDetail(BaseModel):
    """GET /api/bootcamp/level/{level_num} response."""
    level: int
    name: str
    tagline: str
    status: Literal["complete", "current", "locked"]
    habits: list[HabitProgress]
    drills: list[DrillRecommendation]
    graduation: GraduationCriterion
    citation_url: Optional[str] = None
    # For complete levels: improvement earned
    improvement_summary: Optional[dict] = None


# ─────────────────────────────────────────────────────────────────────────────
# Skill Radar
# ─────────────────────────────────────────────────────────────────────────────

class RadarAxis(BaseModel):
    axis_key: str
    display_name: str
    is_new_dard: bool
    player_value: float            # the underlying metric (e.g. 1.71 for 3BV/s)
    player_value_label: str        # display string like "1.71" or "480ms"
    benchmark_value: float
    benchmark_value_label: str
    player_percentile: int = Field(..., ge=0, le=100)
    benchmark_percentile: int = Field(..., ge=0, le=100)
    pill: Literal["weak", "average", "strong"]
    note: Optional[str] = None     # e.g. "slowest on 1-2-2-1"


class RadarInsight(BaseModel):
    kind: Literal["top_axis", "weakness", "leverage"]
    axis_display: str
    summary: str                   # one-line takeaway
    detail: str                    # longer paragraph


class RadarResponse(BaseModel):
    """GET /api/radar response."""
    player_id: str
    difficulty: str
    mode: Literal["standard", "no_guess", "both"]
    compare_to: str
    games_analyzed: int
    axes: list[RadarAxis]
    insights: list[RadarInsight]
    recommendation_title: str
    recommendation_body: str
    recommendation_cta_label: str
    recommendation_cta_url: str


# ─────────────────────────────────────────────────────────────────────────────
# Pattern Fluency
# ─────────────────────────────────────────────────────────────────────────────

class PatternFluencyEntry(BaseModel):
    pattern_key: str
    display_name: str
    category: Literal["openings", "fishing", "patterns", "reductions"]
    layer: int                     # Dard layer 1-4
    is_new_dard: bool
    description: str
    frequency_per_board: float     # avg occurrences per expert board
    your_value: float              # raw value (ms or pct)
    your_value_label: str
    benchmark_value: float
    benchmark_value_label: str
    leverage_seconds: float        # expected gain if you closed the gap
    leverage_tier: Literal["high", "medium", "low"]
    drill_id: Optional[str] = None
    drill_estimated_minutes: Optional[int] = None
    mastered: bool = False


class WeeklyDrillDay(BaseModel):
    days_label: str                # e.g. "Mon · Wed · Fri"
    pattern_name: str
    board_count: int
    minutes: int
    target: str


class PatternFluencyResponse(BaseModel):
    """GET /api/patterns/fluency response."""
    player_id: str
    difficulty: str
    mode: Literal["standard", "no_guess"]
    overall_score: int             # 0-100
    overall_gap_pts: int           # vs top 10%
    headline_message: str
    layer_12_drilled: int
    layer_12_total: int
    layer_4_drilled: int
    layer_4_total: int
    predicted_gain_seconds: float
    patterns: list[PatternFluencyEntry]
    weekly_plan: list[WeeklyDrillDay]
    plan_note: str


# ─────────────────────────────────────────────────────────────────────────────
# Replay Analysis
# ─────────────────────────────────────────────────────────────────────────────

class ReplayMove(BaseModel):
    move_index: int
    t_ms: int
    action: Literal["l", "r", "c"]
    x: int
    y: int
    # Optional annotation (only present for coachable moves)
    badge: Optional[Literal[
        "wasted", "slow", "death", "good", "shortcut",
        "opening", "fish", "flagval", "hierarchy",
    ]] = None
    annotation_number: Optional[int] = None
    detail: Optional[str] = None


class ReplayAnnotation(BaseModel):
    annotation_number: int
    badge: str
    move_index: int
    cell_x: int
    cell_y: int


class ReplayInsight(BaseModel):
    annotation_number: int
    severity: Literal["warn", "bad", "good", "opening", "fish", "flagval", "hierarchy"]
    title: str
    body: str
    citation_url: Optional[str] = None
    drill_id: Optional[str] = None
    drill_label: Optional[str] = None


class ReplayResponse(BaseModel):
    """GET /api/replays/{game_replay_id} response."""
    game_replay_id: int
    player_id: str
    difficulty: str
    mode: Literal["standard", "no_guess"]
    outcome: Literal["win", "loss", "abandon"]
    completion_pct: float
    duration_ms: int
    three_bv: int
    three_bv_per_sec: float
    ioe: float
    correctness: float
    hierarchy_compliance_pct: float
    openings_taken: int
    openings_missed: int
    fishes_attempted: int
    fishes_opportunities: int
    wasted_clicks: int
    death_cause: Optional[str] = None
    death_region: Optional[str] = None
    # Replay data
    board_hash: str
    board_width: int
    board_height: int
    mine_count: int
    move_log: list[ReplayMove]
    annotations: list[ReplayAnnotation]
    insights: list[ReplayInsight]


class ReplayListEntry(BaseModel):
    game_replay_id: int
    outcome: Literal["win", "loss", "abandon"]
    difficulty: str
    mode: Literal["standard", "no_guess"]
    duration_ms: Optional[int]
    three_bv: int
    ioe: float
    hierarchy_compliance_pct: float
    created_at: str


class ReplayListResponse(BaseModel):
    """GET /api/replays response."""
    player_id: str
    total: int
    replays: list[ReplayListEntry]


# ─────────────────────────────────────────────────────────────────────────────
# Mistake Heatmap
# ─────────────────────────────────────────────────────────────────────────────

class HeatmapCell(BaseModel):
    x: int
    y: int
    death_count: int
    top_cause: Optional[str] = None


class CauseBreakdown(BaseModel):
    cause: str
    display_name: str
    count: int
    pct: float
    color: str


class RegionBreakdown(BaseModel):
    region: Literal["center", "edge", "corner", "denseCluster"]
    display_name: str
    count: int
    pct: float


class TrendPoint(BaseModel):
    week_label: str
    standard_avoidable_per_game: float
    no_guess_avoidable_per_game: Optional[float] = None


class HeatmapAnomaly(BaseModel):
    type: str
    count: int
    detail: str


class HeatmapResponse(BaseModel):
    """GET /api/heatmap response."""
    player_id: str
    difficulty: str
    mode: Literal["standard", "no_guess", "both"]
    time_range_days: int
    games_analyzed: int
    wins: int
    losses: int
    standard_pct: float
    no_guess_pct: float
    standard_win_rate: float
    no_guess_win_rate: float
    # heatmap data
    board_width: int
    board_height: int
    cells: list[HeatmapCell]
    cause_breakdown: list[CauseBreakdown]
    region_breakdown: list[RegionBreakdown]
    trend: list[TrendPoint]
    avg_survival_pct: float
    # insights
    avoidable_pct: int             # whole-number pct for display
    edge_pct: int
    site_avoidable_pct: int        # for comparison
    site_avoidable_top10_pct: int  # for comparison
    anomalies: list[HeatmapAnomaly]


# ─────────────────────────────────────────────────────────────────────────────
# Common error
# ─────────────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
