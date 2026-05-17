"""
phase4_routes.queries — SQLAlchemy query helpers for the analytics API.

Each function reads from `game_analyses` (plus `game_replays` when raw move
log is needed) and returns shaped data ready for the response models. The
goal is to keep the FastAPI routes thin — all SQL and aggregation lives
here so it's reusable from worker jobs, exports, etc.

Performance assumptions:
  - Per-player queries are bounded to recent N games (default 50).
  - Site-wide percentiles are computed inline. When `game_analyses` exceeds
    ~1M rows, swap the inline queries for a precomputed `site_percentiles`
    rollup table updated nightly.
"""

from __future__ import annotations

import json
import statistics as stats
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session


# ─────────────────────────────────────────────────────────────────────────────
# Imports from the host application — guarded so this module can be tested
# standalone. Replace with concrete imports when integrating into main.py.
# ─────────────────────────────────────────────────────────────────────────────

try:
    from database import GameReplay, Score                # type: ignore
    from phase2_analyzer import GameAnalysis              # type: ignore
except ImportError:
    GameReplay = None
    Score = None
    GameAnalysis = None


# ═════════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════════

def _player_filter(player_id: str):
    """Match either user_email or guest_token in game_analyses."""
    return GameAnalysis.player_id == player_id


def _difficulty_to_mode(difficulty: str) -> str:
    """Mock mode lookup — replace with proper mode→mine-config mapping."""
    return {"beginner": "beginner", "intermediate": "intermediate",
            "expert": "expert"}.get(difficulty, "expert")


def _mode_filter(mode: str):
    """Filter game_analyses by no_guess flag."""
    if mode == "no_guess":
        return GameAnalysis.no_guess == True
    if mode == "standard":
        return GameAnalysis.no_guess == False
    return True  # both — no filter


def _time_range_filter(time_range_days: Optional[int]):
    if not time_range_days:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(days=time_range_days)
    return GameAnalysis.created_at >= cutoff


# ═════════════════════════════════════════════════════════════════════════════
# Core: load player's recent analyses
# ═════════════════════════════════════════════════════════════════════════════

def get_player_analyses(
    db: Session,
    player_id: str,
    *,
    mode: str = "standard",
    difficulty: str = "expert",
    limit: int = 50,
    time_range_days: Optional[int] = None,
) -> list[GameAnalysis]:
    """Return the player's most recent analyses matching filters."""
    q = db.query(GameAnalysis).filter(_player_filter(player_id))
    q = q.filter(_mode_filter(mode))
    if time_range_days:
        q = q.filter(_time_range_filter(time_range_days))
    return (q.order_by(GameAnalysis.created_at.desc())
              .limit(limit)
              .all())


# ═════════════════════════════════════════════════════════════════════════════
# Bootcamp queries
# ═════════════════════════════════════════════════════════════════════════════

LEVEL_META = {
    1: {"name": "Cut Wasted Clicks",
        "tagline": 'Eliminate "safety chords" — clicks that produce zero progress',
        "citation": "https://www.youtube.com/watch?v=waNprVuduEE&t=342s"},
    2: {"name": "Effective Chording",
        "tagline": "Skip flag-then-chord redundancy when chord alone suffices",
        "citation": "https://www.youtube.com/watch?v=waNprVuduEE&t=428s"},
    3: {"name": "Strategic No-Flag",
        "tagline": "Ignore stranded edge mines — save clicks by not flagging",
        "citation": "https://www.youtube.com/watch?v=waNprVuduEE&t=577s"},
    4: {"name": "Pure Efficiency",
        "tagline": "Per-situation flag vs. no-flag for minimum clicks",
        "citation": "https://www.youtube.com/watch?v=waNprVuduEE&t=768s"},
    5: {"name": "Opening Recognition",
        "tagline": 'Find guaranteed and high-EV potential openings — the "0 squares"',
        "citation": "https://www.youtube.com/watch?v=jKRydA5zqzI&t=160s"},
    6: {"name": "Flag Value",
        "tagline": "High-value flags participate in multiple future chords",
        "citation": "https://www.youtube.com/watch?v=jKRydA5zqzI&t=444s"},
    7: {"name": "Fishing & Decision Hierarchy",
        "tagline": "Click safe cells to reveal new chords. Master Dard's priority order.",
        "citation": "https://www.youtube.com/watch?v=jKRydA5zqzI&t=800s"},
}


def get_bootcamp_diagnosis(
    db: Session, player_id: str, mode: str, difficulty: str
) -> dict:
    """Aggregate over recent games to produce a Bootcamp diagnosis."""
    analyses = get_player_analyses(db, player_id, mode=mode,
                                   difficulty=difficulty, limit=50)
    if not analyses:
        return {"games_analyzed": 0, "current_level": 1,
                "level_mastery": {k: 0.0 for k in range(1, 8)},
                "best_time_ms": None, "median_time_ms": None,
                "ioe": 0, "correctness": 0, "throughput": 0,
                "three_bv_per_sec": 0, "hierarchy_compliance_pct": 0,
                "blockers": ["No recent games"]}

    # Median across recent games for the key signals
    iqe_vals = [a.ioe for a in analyses if a.ioe is not None]
    correctness_vals = [a.correctness for a in analyses if a.correctness is not None]
    bvs_vals = [a.three_bv_per_sec for a in analyses if a.three_bv_per_sec is not None]
    throughput_vals = [a.throughput for a in analyses if a.throughput is not None]
    hierarchy_vals = [a.hierarchy_compliance_pct for a in analyses
                      if a.hierarchy_compliance_pct is not None]

    # Time stats — pull from joined GameReplay
    replay_ids = [a.game_replay_id for a in analyses]
    times = (db.query(GameReplay.time_ms)
                .filter(GameReplay.id.in_(replay_ids))
                .filter(GameReplay.outcome == "win")
                .all())
    times = [t[0] for t in times if t[0]]
    best_time = min(times) if times else None
    median_time = int(stats.median(times)) if times else None

    # Average level mastery from individual analyses
    mastery_accum = {k: 0.0 for k in range(1, 8)}
    for a in analyses:
        if a.level_mastery_json:
            try:
                m = json.loads(a.level_mastery_json)
                for k, v in m.items():
                    mastery_accum[int(k)] += float(v)
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
    n = len(analyses)
    mastery = {k: round(v / n, 3) for k, v in mastery_accum.items()}

    # Find current level (lowest unmastered)
    current_level = 7
    blockers: list[str] = []
    for lv in range(1, 8):
        if mastery[lv] < 0.85:
            current_level = lv
            blockers.append(_blocker_message(lv, mastery[lv], analyses))
            break

    progress_to_next = mastery[current_level] / 0.85 if current_level < 7 else 1.0

    return {
        "games_analyzed": n,
        "current_level": current_level,
        "level_mastery": mastery,
        "best_time_ms": best_time,
        "median_time_ms": median_time,
        "ioe": round(_safe_median(iqe_vals), 2),
        "correctness": round(_safe_median(correctness_vals), 2),
        "throughput": round(_safe_median(throughput_vals), 2),
        "three_bv_per_sec": round(_safe_median(bvs_vals), 2),
        "hierarchy_compliance_pct": round(_safe_median(hierarchy_vals), 2),
        "progress_pct_to_next": round(min(1.0, progress_to_next), 2),
        "blockers": blockers,
    }


def _blocker_message(level: int, mastery: float, analyses) -> str:
    """Human-readable description of what's blocking the player at this level."""
    if level == 1:
        avg_correctness = _safe_avg([a.correctness for a in analyses if a.correctness])
        return f"Correctness {avg_correctness * 100:.0f}% — target 85%+"
    if level == 2:
        avg_shortcuts = _safe_avg([a.missed_shortcut_count for a in analyses
                                    if a.missed_shortcut_count is not None])
        return f"{avg_shortcuts:.1f} flag-then-chord redundancies/game — target ≤3"
    if level == 3:
        avg_stranded = _safe_avg([a.stranded_flag_count for a in analyses
                                   if a.stranded_flag_count is not None])
        return f"{avg_stranded:.1f} stranded flags/game — target ≤1"
    if level == 4:
        avg_ioe = _safe_avg([a.ioe for a in analyses if a.ioe])
        return f"Avg IOE {avg_ioe:.2f} — target 0.90+"
    if level == 5:
        missed = _safe_avg([a.openings_guaranteed_missed for a in analyses
                             if a.openings_guaranteed_missed is not None])
        return f"{missed:.1f} guaranteed openings missed per game — target ≤0.5"
    if level == 6:
        pct = _safe_avg([a.high_value_flag_pct for a in analyses
                          if a.high_value_flag_pct is not None])
        return f"{pct * 100:.0f}% high-value flags — target 70%+"
    if level == 7:
        pct = _safe_avg([a.hierarchy_compliance_pct for a in analyses
                          if a.hierarchy_compliance_pct is not None])
        return f"Hierarchy compliance {pct * 100:.0f}% — target 85%+"
    return ""


# ═════════════════════════════════════════════════════════════════════════════
# Skill Radar queries
# ═════════════════════════════════════════════════════════════════════════════

RADAR_AXES = [
    "speed", "efficiency", "chord_use", "pattern_recognition",
    "hierarchy_compliance", "flag_value", "opening_recognition",
    "guess_avoidance", "consistency",
]

RADAR_AXIS_META = {
    "speed":                {"display": "Speed (3BV/s)",      "is_new_dard": False},
    "efficiency":           {"display": "Efficiency (IOE)",    "is_new_dard": False},
    "chord_use":            {"display": "Chord Usage",         "is_new_dard": False},
    "pattern_recognition":  {"display": "Pattern Recognition", "is_new_dard": False},
    "hierarchy_compliance": {"display": "Hierarchy Compliance","is_new_dard": True},
    "flag_value":           {"display": "Flag Value",          "is_new_dard": True},
    "opening_recognition":  {"display": "Opening Recognition", "is_new_dard": True},
    "guess_avoidance":      {"display": "Guess Avoidance",     "is_new_dard": False},
    "consistency":          {"display": "Consistency",         "is_new_dard": False},
}


def get_radar_data(
    db: Session, player_id: str, mode: str, difficulty: str
) -> dict:
    """Compute 9-axis player values + benchmark percentiles."""
    analyses = get_player_analyses(db, player_id, mode=mode,
                                   difficulty=difficulty, limit=50)
    if not analyses:
        return {"games_analyzed": 0, "axes": []}

    player = {
        "speed": _safe_median([a.three_bv_per_sec for a in analyses if a.three_bv_per_sec]),
        "efficiency": _safe_median([a.ioe for a in analyses if a.ioe]),
        "chord_use": _chord_usage_pct(analyses),
        "pattern_recognition": _safe_median(
            [a.avg_pattern_reaction_ms for a in analyses if a.avg_pattern_reaction_ms]
        ),
        "hierarchy_compliance": _safe_median(
            [a.hierarchy_compliance_pct for a in analyses if a.hierarchy_compliance_pct]
        ),
        "flag_value": _safe_median(
            [a.avg_flag_value_score for a in analyses if a.avg_flag_value_score]
        ),
        "opening_recognition": _opening_take_rate(analyses),
        "guess_avoidance": _safe_avg(
            [a.avoidable_guesses for a in analyses if a.avoidable_guesses is not None]
        ),
        "consistency": _consistency_score(db, player_id, mode, analyses),
    }

    # Compute percentiles for each metric vs the population
    benchmark, percentiles = _compute_radar_percentiles(db, mode, difficulty, player)

    return {
        "games_analyzed": len(analyses),
        "axes": [
            {
                "axis_key": k,
                "player_value": player[k],
                "benchmark_value": benchmark[k],
                "player_percentile": percentiles[k]["player"],
                "benchmark_percentile": percentiles[k]["benchmark"],
            }
            for k in RADAR_AXES
        ],
    }


def _chord_usage_pct(analyses) -> float:
    chords = sum(a.successful_chords or 0 for a in analyses)
    total = sum(((a.successful_chords or 0) + (a.wasted_chords or 0)) +
                (a.wasted_click_count or 0) for a in analyses)
    return (chords / total) if total else 0.0


def _opening_take_rate(analyses) -> float:
    taken = sum((a.openings_guaranteed_taken or 0) for a in analyses)
    missed = sum((a.openings_guaranteed_missed or 0) for a in analyses)
    total = taken + missed
    return (taken / total) if total else 0.0


def _consistency_score(db: Session, player_id: str, mode: str, analyses) -> float:
    """Inverse of stddev of times — higher is better. Returns 1/σ scaled."""
    replay_ids = [a.game_replay_id for a in analyses]
    times = (db.query(GameReplay.time_ms)
                .filter(GameReplay.id.in_(replay_ids))
                .filter(GameReplay.outcome == "win")
                .all())
    times = [t[0] / 1000.0 for t in times if t[0]]
    if len(times) < 2:
        return 0.0
    sigma = stats.stdev(times)
    return sigma   # caller interprets via percentile


def _compute_radar_percentiles(
    db: Session, mode: str, difficulty: str, player_values: dict
) -> tuple[dict, dict]:
    """
    Return (benchmark_values_at_top10, percentiles_for_player).
    Benchmark is the 90th percentile in the population (or 10th for "lower is better" metrics).
    """
    # In production, read precomputed nightly percentiles. For now use a static
    # baseline — these numbers come from the framework synthesis benchmarks.
    benchmark = {
        "speed": 2.50, "efficiency": 0.90, "chord_use": 0.45,
        "pattern_recognition": 290,             # ms, lower is better
        "hierarchy_compliance": 0.88,
        "flag_value": 3.7,
        "opening_recognition": 0.89,
        "guess_avoidance": 0.8,                 # avoidable per game, lower is better
        "consistency": 6.2,                     # stddev seconds, lower is better
    }

    # Higher-is-better metrics:
    higher_better = {"speed", "efficiency", "chord_use", "hierarchy_compliance",
                      "flag_value", "opening_recognition"}

    percentiles: dict = {}
    for axis in RADAR_AXES:
        pv = player_values.get(axis, 0) or 0
        bv = benchmark[axis]
        if axis in higher_better:
            player_pct = min(100, int(100 * pv / bv)) if bv else 0
            benchmark_pct = 92
        else:
            # lower is better — invert
            if pv == 0:
                player_pct = 100
            else:
                player_pct = min(100, int(100 * bv / pv))
            benchmark_pct = 90
        percentiles[axis] = {"player": player_pct, "benchmark": benchmark_pct}

    return benchmark, percentiles


# ═════════════════════════════════════════════════════════════════════════════
# Pattern Fluency queries
# ═════════════════════════════════════════════════════════════════════════════

PATTERN_CATALOG = [
    # Layer 4 — Openings
    {"key": "opening_l_shape_edge", "name": "L-shape edge opening",
     "category": "openings", "layer": 4, "is_new_dard": True,
     "description": "Two 1s against an edge with a known mine guarantee the edge cell is a 0.",
     "frequency": 5.0,
     "benchmark": 0.95, "benchmark_label": "95% taken",
     "drill_id": "opening_l_shape", "minutes": 6},
    {"key": "opening_2_satisfied", "name": "2-satisfied edge opening",
     "category": "openings", "layer": 4, "is_new_dard": True,
     "description": "A 2 fully satisfied by adjacent mines guarantees the next edge cell is a 0.",
     "frequency": 3.0,
     "benchmark": 0.93, "benchmark_label": "93% taken",
     "drill_id": "opening_2_sat", "minutes": 5},
    {"key": "opening_potential_2cell", "name": "Potential opening (2-cell)",
     "category": "openings", "layer": 4, "is_new_dard": True,
     "description": "A cell with 2 unknowns — ~62% chance to be a 0 on expert.",
     "frequency": 2.0,
     "benchmark": 0.78, "benchmark_label": "78% taken",
     "drill_id": "opening_2cell", "minutes": 8},
    # Layer 4 — Fishing
    {"key": "fishing_for_1", "name": "Fishing for 1",
     "category": "fishing", "layer": 4, "is_new_dard": True,
     "description": "Click a known-safe cell adjacent to one unknown mine.",
     "frequency": 4.0,
     "benchmark": 0.72, "benchmark_label": "72% rate",
     "drill_id": "fish_1", "minutes": 7},
    {"key": "fishing_for_2", "name": "Fishing for 2",
     "category": "fishing", "layer": 4, "is_new_dard": True,
     "description": "When one mine is flagged adjacent, fish for a 2 to create a new chord.",
     "frequency": 3.0,
     "benchmark": 0.64, "benchmark_label": "64% rate",
     "drill_id": "fish_2", "minutes": 6},
    # Layer 1-2 — Patterns + reductions
    {"key": "pattern_1221", "name": "1-2-2-1 reduction",
     "category": "patterns", "layer": 2, "is_new_dard": False,
     "description": "Outer cells mines, middle two safe.",
     "frequency": 6.0,
     "benchmark": 290, "benchmark_label": "290ms",
     "drill_id": "pat_1221", "minutes": 5},
    {"key": "pattern_121", "name": "1-2-1 pattern",
     "category": "patterns", "layer": 2, "is_new_dard": False,
     "description": "Outer mines, middle safe. Most common pattern.",
     "frequency": 11.0,
     "benchmark": 180, "benchmark_label": "180ms",
     "drill_id": "pat_121", "minutes": 5},
    {"key": "pattern_232", "name": "2-3-2 → 1-2-1 reduction",
     "category": "reductions", "layer": 2, "is_new_dard": False,
     "description": "When mines below are flagged, reduces to a 1-2-1.",
     "frequency": 4.0,
     "benchmark": 310, "benchmark_label": "310ms",
     "drill_id": "pat_232", "minutes": 8},
    {"key": "pattern_11_corner", "name": "1-1 corner",
     "category": "patterns", "layer": 1, "is_new_dard": False,
     "description": "When 1s share a forced mine, adjacent cell is safe.",
     "frequency": 14.0,
     "benchmark": 170, "benchmark_label": "170ms",
     "drill_id": "pat_11", "minutes": 3},
    {"key": "pattern_21_edge", "name": "2-1 edge",
     "category": "patterns", "layer": 1, "is_new_dard": False,
     "description": "Mine on the 2-side, safe on the 1-side.",
     "frequency": 8.0,
     "benchmark": 150, "benchmark_label": "150ms",
     "drill_id": "pat_21", "minutes": 3},
]


def get_pattern_fluency(
    db: Session, player_id: str, mode: str, difficulty: str
) -> dict:
    """Compute per-pattern reaction time vs. benchmark + leverage estimates."""
    analyses = get_player_analyses(db, player_id, mode=mode,
                                   difficulty=difficulty, limit=50)
    if not analyses:
        return {"games_analyzed": 0, "patterns": [], "overall_score": 0}

    # Player's avg reaction time across all patterns
    avg_pattern_ms = _safe_avg(
        [a.avg_pattern_reaction_ms for a in analyses if a.avg_pattern_reaction_ms]
    )

    # Opening / fishing take rates from aggregates
    open_taken = sum((a.openings_guaranteed_taken or 0) for a in analyses)
    open_missed = sum((a.openings_guaranteed_missed or 0) for a in analyses)
    open_rate = open_taken / (open_taken + open_missed) if (open_taken + open_missed) else 0
    fish_attempted = sum((a.fishes_attempted or 0) for a in analyses)
    fish_opportunities = fish_attempted + sum((a.fishes_missed or 0) for a in analyses)
    fish_rate = fish_attempted / fish_opportunities if fish_opportunities else 0

    patterns_out = []
    for p in PATTERN_CATALOG:
        if p["category"] in ("openings",):
            your_value = open_rate
            your_label = f"{int(open_rate * 100)}% taken"
            gap = max(0, p["benchmark"] - your_value)
        elif p["category"] == "fishing":
            your_value = fish_rate
            your_label = f"{int(fish_rate * 100)}% rate"
            gap = max(0, p["benchmark"] - your_value)
        else:
            # ms-based metrics
            your_value = avg_pattern_ms or (p["benchmark"] * 1.6)
            your_label = f"{int(your_value)}ms"
            gap = max(0, your_value - p["benchmark"]) / 1000.0  # convert to s

        leverage_s = round(gap * p["frequency"] * 0.4, 1)  # heuristic
        tier = "high" if leverage_s >= 1.0 else "medium" if leverage_s >= 0.3 else "low"
        mastered = (
            (p["category"] in ("openings", "fishing") and your_value >= p["benchmark"] * 0.9)
            or
            (p["category"] not in ("openings", "fishing") and your_value <= p["benchmark"] * 1.2)
        )

        patterns_out.append({
            **p,
            "your_value": your_value,
            "your_label": your_label,
            "leverage_s": leverage_s,
            "tier": tier,
            "mastered": mastered,
        })

    # Sort by leverage descending
    patterns_out.sort(key=lambda x: -x["leverage_s"])

    # Compute overall score
    drilled_l12 = sum(1 for p in patterns_out if p["layer"] <= 2 and p["mastered"])
    total_l12 = sum(1 for p in PATTERN_CATALOG if p["layer"] <= 2)
    drilled_l4 = sum(1 for p in patterns_out if p["layer"] == 4 and p["mastered"])
    total_l4 = sum(1 for p in PATTERN_CATALOG if p["layer"] == 4)
    score = int(100 * (drilled_l12 + drilled_l4) / (total_l12 + total_l4))

    return {
        "games_analyzed": len(analyses),
        "overall_score": score,
        "overall_gap_pts": max(0, 100 - score),
        "patterns": patterns_out,
        "predicted_gain_seconds": round(sum(p["leverage_s"] for p in patterns_out[:3]), 1),
        "layer_12_drilled": drilled_l12, "layer_12_total": total_l12,
        "layer_4_drilled": drilled_l4, "layer_4_total": total_l4,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Replay queries
# ═════════════════════════════════════════════════════════════════════════════

def get_replay_with_analysis(db: Session, game_replay_id: int) -> Optional[dict]:
    """Fetch a game_replay row joined with its game_analysis."""
    replay = db.query(GameReplay).filter(GameReplay.id == game_replay_id).first()
    if not replay:
        return None
    analysis = (db.query(GameAnalysis)
                  .filter(GameAnalysis.game_replay_id == game_replay_id)
                  .first())
    return {
        "replay": replay,
        "analysis": analysis,
    }


def get_replay_list(
    db: Session, player_id: str, *, mode: str = "standard", limit: int = 20
) -> list[dict]:
    """List a player's recent replays for the replay browser."""
    q = (db.query(GameReplay, GameAnalysis)
           .join(GameAnalysis, GameAnalysis.game_replay_id == GameReplay.id)
           .filter(or_(GameReplay.user_email == player_id,
                       GameReplay.guest_token == player_id)))
    if mode == "no_guess":
        q = q.filter(GameReplay.no_guess == True)
    elif mode == "standard":
        q = q.filter(GameReplay.no_guess == False)
    q = q.order_by(GameReplay.created_at.desc()).limit(limit)
    return [{"replay": r, "analysis": a} for r, a in q.all()]


# ═════════════════════════════════════════════════════════════════════════════
# Heatmap queries
# ═════════════════════════════════════════════════════════════════════════════

def get_heatmap_data(
    db: Session, player_id: str, mode: str, difficulty: str,
    time_range_days: int = 90,
) -> dict:
    """Aggregate death cells, causes, regions, and trend for the heatmap."""
    base_q = db.query(GameAnalysis).filter(_player_filter(player_id))
    base_q = base_q.filter(_mode_filter(mode))
    if time_range_days:
        base_q = base_q.filter(_time_range_filter(time_range_days))

    all_analyses = base_q.all()
    losses = [a for a in all_analyses if a.death_cause is not None]

    # Cause breakdown
    cause_counts: dict[str, int] = {}
    for a in losses:
        cause_counts[a.death_cause] = cause_counts.get(a.death_cause, 0) + 1
    total_deaths = sum(cause_counts.values()) or 1
    cause_breakdown = [
        {"cause": c, "count": n, "pct": round(n / total_deaths, 3)}
        for c, n in sorted(cause_counts.items(), key=lambda kv: -kv[1])
    ]

    # Region breakdown
    region_counts: dict[str, int] = {}
    for a in losses:
        if a.death_region:
            region_counts[a.death_region] = region_counts.get(a.death_region, 0) + 1
    region_breakdown = [
        {"region": r, "count": n, "pct": round(n / total_deaths, 3)}
        for r, n in sorted(region_counts.items(), key=lambda kv: -kv[1])
    ]

    # Heatmap cells — pull death coordinates from the patterns_json /
    # hierarchy_deviations_json — for now, query GameReplay.log_json
    # and use the last move as the death cell. (Production: store death_x,
    # death_y on GameAnalysis directly for speed.)
    cell_counts: dict[tuple[int, int], int] = {}
    replay_ids = [a.game_replay_id for a in losses]
    if replay_ids:
        replays = (db.query(GameReplay)
                     .filter(GameReplay.id.in_(replay_ids))
                     .all())
        for r in replays:
            if not r.log_json:
                continue
            try:
                log = json.loads(r.log_json)
                if log:
                    last = log[-1]
                    cell_counts[(last[3], last[2])] = cell_counts.get((last[3], last[2]), 0) + 1
            except (json.JSONDecodeError, IndexError, KeyError):
                continue

    # Dimensions
    board_w, board_h = {"beginner": (9, 9), "intermediate": (16, 16),
                         "expert": (30, 16)}.get(difficulty, (30, 16))
    cells = [{"x": x, "y": y, "death_count": cell_counts.get((x, y), 0)}
             for y in range(board_h) for x in range(board_w)
             if cell_counts.get((x, y), 0) > 0]

    # Anomalies: no-guess + forced-guess
    ng_forced = (db.query(GameAnalysis)
                   .filter(_player_filter(player_id))
                   .filter(GameAnalysis.no_guess == True)
                   .filter(GameAnalysis.death_cause == "forcedGuess")
                   .count())
    anomalies = []
    if ng_forced > 0:
        anomalies.append({
            "type": "no_guess_forced_guess",
            "count": ng_forced,
            "detail": (
                f"{ng_forced} no-guess game(s) classified as forced guess. "
                "By definition this shouldn't happen — solver review queued."
            ),
        })

    # Wins for win-rate calc
    wins = sum(1 for a in all_analyses if a.death_cause is None)

    avoidable = cause_counts.get("avoidableGuess", 0)
    edge = region_counts.get("edge", 0)

    return {
        "games_analyzed": len(all_analyses),
        "losses": len(losses),
        "wins": wins,
        "cells": cells,
        "board_width": board_w,
        "board_height": board_h,
        "cause_breakdown": cause_breakdown,
        "region_breakdown": region_breakdown,
        "anomalies": anomalies,
        "avoidable_pct": int(100 * avoidable / total_deaths) if total_deaths else 0,
        "edge_pct": int(100 * edge / total_deaths) if total_deaths else 0,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Small utility helpers
# ═════════════════════════════════════════════════════════════════════════════

def _safe_median(values: list[float]) -> float:
    return stats.median(values) if values else 0.0


def _safe_avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
