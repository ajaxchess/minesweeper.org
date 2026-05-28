"""
phase7_drills.mastery — convert a finished drill into a mastery contribution.

A drill yields three signals:
  1. Accuracy   (num_correct / num_total)             — primary
  2. Avg decision speed (decision_ms)                 — secondary
  3. Difficulty of boards (max optimal_opening_size)  — control variable

We map these to a single 0..1 mastery score, then weight it at DRILL_WEIGHT
when blending with live-game mastery for the rolling-10 average.

Math (designed to be readable, not optimal):

    base       = accuracy                            # 0..1
    speed_bonus = clamp((4000 - avg_ms) / 4000, 0, 0.15)
                                                     # 0..0.15
    mastery    = clamp(base + speed_bonus, 0, 1.0)

So a perfect, fast drill scores ~1.0; a perfect, slow drill scores ~0.85;
a 50% accuracy drill scores ~0.50–0.65 depending on speed.

DRILL_WEIGHT = 0.3 — chosen via the AskUserQuestion options earlier. A drill
counts as 30% of a live game in the rolling-10 mastery average. To raise the
weight later, change this constant and re-run the deploy; mastery_contribution
is recomputed each time anyone hits the diagnosis endpoint.
"""

from __future__ import annotations

from typing import Iterable, Optional


DRILL_WEIGHT = 0.3
DRILL_VERSION = "1.0"


def compute_drill_mastery(
    num_correct: int,
    num_total: int,
    avg_decision_ms: Optional[int],
) -> float:
    """Map drill performance into a 0..1 mastery score.

    Args:
      num_correct      — boards where the player picked a "correct" cell
      num_total        — boards in the drill (typically 10)
      avg_decision_ms  — mean time to make a pick across submitted boards;
                          None or 0 disables the speed bonus

    Returns:
      A score in [0.0, 1.0]. Treat 0.85 as the "mastered" threshold —
      consistent with the level-graduation threshold in queries.LEVEL_META.
    """
    if num_total <= 0:
        return 0.0

    accuracy = max(0.0, min(1.0, num_correct / num_total))

    if avg_decision_ms is None or avg_decision_ms <= 0:
        speed_bonus = 0.0
    else:
        # Up to 0.15 bonus for being snappy. The 4-second baseline matches
        # the median first-glance decision time observed in early Bootcamp
        # data — see README_Drills.md for the rationale.
        raw = (4000.0 - float(avg_decision_ms)) / 4000.0
        speed_bonus = max(0.0, min(0.15, raw))

    return max(0.0, min(1.0, accuracy + speed_bonus))


def weight() -> float:
    """The fraction of a live game one completed drill is worth."""
    return DRILL_WEIGHT


def blend_into_rolling_average(
    game_mastery_values: Iterable[float],
    drill_mastery_values: Iterable[float],
) -> float:
    """Helper for the bootcamp diagnosis / progress queries.

    Computes a weighted average where each live game counts as 1.0 and each
    drill counts as DRILL_WEIGHT. Used by phase4_routes.queries when it
    needs to include drills in a rolling-10 window.

    Returns 0.0 for the empty case so the caller can branch on it.
    """
    games = list(game_mastery_values)
    drills = list(drill_mastery_values)
    num = sum(games) + DRILL_WEIGHT * sum(drills)
    den = len(games) + DRILL_WEIGHT * len(drills)
    return num / den if den > 0 else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Smoke test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cases = [
        (10, 10, 2000, "perfect + fast"),
        (10, 10, 6000, "perfect + slow"),
        (7,  10, 3000, "decent"),
        (5,  10, 5000, "mediocre + slow"),
        (0,  10, 5000, "zero"),
        (10,  0, 3000, "edge: empty drill"),
    ]
    for nc, nt, ms, label in cases:
        m = compute_drill_mastery(nc, nt, ms)
        print(f"{label:25s} → {m:.3f}")

    print(f"\nBlend test: 5 games avg 0.80 + 3 drills avg 0.90 → "
          f"{blend_into_rolling_average([0.80]*5, [0.90]*3):.3f}")
