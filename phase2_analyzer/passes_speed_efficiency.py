"""
analyzer.passes_speed_efficiency — Layer 0-3 passes (Beginners + Part 1).

All passes here are stateless: (game, [solver]) -> Report. They consume the
raw move log and produce structured analysis records.

Citations: each function header notes the Dard video timestamp where the
underlying concept is taught. Behavioral changes should consult those sources.
"""

from __future__ import annotations

from .simulator import (
    apply_move,
    clone_board,
    count_newly_revealed,
    fresh_board,
    snapshot_at_each_move,
)
from .solver import Solver, DEFAULT_SOLVER, is_in_corner, is_on_edge
from .types import (
    Action,
    AvoidableGuess,
    BasicStats,
    DeathReport,
    Game,
    GuessReport,
    LevelDiagnosis,
    MissedShortcut,
    Move,
    Outcome,
    PatternEvent,
    ShortcutReport,
    StrandedFlag,
    WastedClick,
    WastedClickReport,
)


# ═════════════════════════════════════════════════════════════════════════════
# BASIC STATS — IOE, ThRoughput, click breakdown
# (Source: Dard Part 1 — Game stats walkthrough @ 14:07)
# ═════════════════════════════════════════════════════════════════════════════

def compute_basic_stats(game: Game) -> BasicStats:
    left_clicks = 0
    right_clicks = 0
    chord_count = 0
    cells_by_chord = 0
    cells_by_left = 0
    wasted_chords = 0

    for i, (_, before) in enumerate(_paired_snapshots(game)):
        if i >= len(game.move_log):
            break
        move = game.move_log[i]
        # We need the state BEFORE the move and the state AFTER.
        after = clone_board(before)
        apply_move(after, move)
        cleared = count_newly_revealed(before, after)

        if move.action == Action.LEFT_CLICK:
            left_clicks += 1
            cells_by_left += cleared
        elif move.action == Action.RIGHT_CLICK:
            right_clicks += 1
        elif move.action == Action.CHORD:
            chord_count += 1
            cells_by_chord += cleared
            if cleared == 0:
                wasted_chords += 1

    wasted = detect_wasted_clicks(game)
    total_clicks = wasted.total_clicks
    time_s = game.duration_ms / 1000.0 if game.duration_ms else 0.0
    ioe = game.three_bv / total_clicks if total_clicks else 0.0
    bv_per_sec = game.three_bv / time_s if time_s else 0.0
    throughput = bv_per_sec * ioe

    return BasicStats(
        time_s=time_s,
        three_bv=game.three_bv,
        three_bv_per_sec=bv_per_sec,
        total_clicks=total_clicks,
        left_clicks=left_clicks,
        right_clicks=right_clicks,
        chord_count=chord_count,
        wasted_chords=wasted_chords,
        successful_chords=chord_count - wasted_chords,
        cells_cleared_by_chord=cells_by_chord,
        cells_cleared_by_left=cells_by_left,
        ioe=ioe,
        throughput=throughput,
        correctness=wasted.correctness,
    )


# ═════════════════════════════════════════════════════════════════════════════
# LEVEL 1: WASTED CLICKS (Safety chording habit)
# (Source: Dard Part 1 @ 5:42 — "Reducing wasted clicks")
# ═════════════════════════════════════════════════════════════════════════════

def detect_wasted_clicks(game: Game) -> WastedClickReport:
    """
    A move is wasted if it produces zero board progress AND doesn't enable
    a future chord (in the case of flags).
    """
    wasted: list[WastedClick] = []

    snapshots = list(snapshot_at_each_move(game))
    # snapshots[i] is the state AFTER move (i-1), with index -1 = pre-game.

    for i, move in enumerate(game.move_log):
        before = snapshots[i][1]      # state before move i
        after = snapshots[i + 1][1]   # state after move i

        if move.action == Action.CHORD:
            if count_newly_revealed(before, after) == 0:
                wasted.append(WastedClick(
                    move_index=i, move=move, reason="safetyChord"
                ))

        elif move.action == Action.RIGHT_CLICK:
            # Was this a flag placement (vs. removal)?
            was_placement = before.cells[move.y][move.x].kind == "unrevealed"
            if was_placement and not _flag_used_later(game, i, move.x, move.y):
                wasted.append(WastedClick(
                    move_index=i, move=move, reason="flagOnUnused"
                ))

    total = len(game.move_log)
    useful = total - len(wasted)
    return WastedClickReport(
        wasted=wasted,
        total_clicks=total,
        useful_clicks=useful,
        correctness=(useful / total) if total else 1.0,
    )


def _flag_used_later(game: Game, flag_idx: int, fx: int, fy: int) -> bool:
    """True if a later chord at adjacent cell uses this flag."""
    for j in range(flag_idx + 1, len(game.move_log)):
        m = game.move_log[j]
        if m.action == Action.CHORD and abs(m.x - fx) <= 1 and abs(m.y - fy) <= 1:
            return True
        if m.action == Action.RIGHT_CLICK and m.x == fx and m.y == fy:
            return False  # flag was removed before use
    return False


# ═════════════════════════════════════════════════════════════════════════════
# LEVEL 2: EFFECTIVE CHORDING (flag-then-chord redundancy)
# (Source: Dard Part 1 @ 7:08)
# ═════════════════════════════════════════════════════════════════════════════

def detect_shortcuts(game: Game) -> ShortcutReport:
    """
    Find flag→chord pairs where the chord alone would have produced the
    same result. These are 1-click waste each.
    """
    missed: list[MissedShortcut] = []
    snapshots = list(snapshot_at_each_move(game))

    for i in range(len(game.move_log) - 1):
        a = game.move_log[i]
        b = game.move_log[i + 1]
        if a.action != Action.RIGHT_CLICK:
            continue
        if b.action != Action.CHORD:
            continue
        before = snapshots[i][1]            # state before the flag
        with_both = snapshots[i + 2][1]     # state after the chord

        # Hypothetical: skip the flag, do chord only
        hypothetical = clone_board(before)
        apply_move(hypothetical, b)

        if _boards_visually_equal(with_both, hypothetical):
            missed.append(MissedShortcut(
                move_indices=[i, i + 1],
                description=f"Flag ({a.x},{a.y}) → chord ({b.x},{b.y}): "
                            "chord alone yields same result",
                clicks_saved=1,
            ))

    return ShortcutReport(missed=missed)


def _boards_visually_equal(a, b) -> bool:
    """Same kind + adjacent_mines on every cell."""
    for y in range(a.height):
        for x in range(a.width):
            ca, cb = a.cells[y][x], b.cells[y][x]
            if ca.kind != cb.kind:
                return False
            if ca.kind == "revealed" and ca.adjacent_mines != cb.adjacent_mines:
                return False
    return True


# ═════════════════════════════════════════════════════════════════════════════
# LEVEL 3: STRATEGIC NO-FLAG (stranded edge flags)
# (Source: Dard Part 1 @ 9:37)
# ═════════════════════════════════════════════════════════════════════════════

def detect_stranded_flags(game: Game) -> list[StrandedFlag]:
    """
    A flag is "stranded" if it (a) was placed (not removed) and (b) never
    participated in a subsequent chord and (c) sits on the board edge.
    Edge bias matches Dard's "stranded mines tend to be around the edges."
    """
    stranded: list[StrandedFlag] = []
    snapshots = list(snapshot_at_each_move(game))

    for i, move in enumerate(game.move_log):
        if move.action != Action.RIGHT_CLICK:
            continue
        before = snapshots[i][1]
        if before.cells[move.y][move.x].kind != "unrevealed":
            continue
        if _flag_used_later(game, i, move.x, move.y):
            continue
        if not is_on_edge(before, move.x, move.y):
            continue
        stranded.append(StrandedFlag(move_index=i, cell=(move.x, move.y)))
    return stranded


# ═════════════════════════════════════════════════════════════════════════════
# PATTERN RECOGNITION (Layer 1)
# (Source: Beginners Guide @ 11:41)
# ═════════════════════════════════════════════════════════════════════════════

def recognize_patterns(game: Game, solver: Solver = DEFAULT_SOLVER) -> list[PatternEvent]:
    """
    Detect when known patterns became visible and measure the player's
    reaction time to act on them.

    Currently detects: 1-2-1 horizontal. Production should extend with the
    full template library (1-1, 1-2-2-1, reductions, etc.).
    """
    events: list[PatternEvent] = []
    snapshots = list(snapshot_at_each_move(game))

    for i, move in enumerate(game.move_log):
        before = snapshots[i][1]
        prev_t = game.move_log[i - 1].t_ms if i > 0 else 0

        # Find any 1-2-1 horizontal pattern visible BEFORE this move
        for pattern in _find_visible_patterns(before):
            if _move_resolves_pattern(pattern, move):
                events.append(PatternEvent(
                    pattern_type=pattern["type"],
                    appeared_t_ms=prev_t,
                    resolved_t_ms=move.t_ms,
                    reaction_ms=move.t_ms - prev_t,
                    cells=pattern["cells"],
                ))
    return events


def _find_visible_patterns(board) -> list[dict]:
    """Pattern templates. Extend with 1-1, 1-2-2-1, etc. for full coverage."""
    found = []
    for y in range(board.height):
        for x in range(board.width - 2):
            p = _match_121_horizontal(board, x, y)
            if p:
                found.append(p)
    return found


def _match_121_horizontal(board, x: int, y: int) -> dict | None:
    """1-2-1 in a row, with unrevealed/flagged cells in adjacent row."""
    row = board.cells[y]
    if x + 2 >= board.width:
        return None
    a, b, c = row[x], row[x + 1], row[x + 2]
    if a.kind != "revealed" or a.adjacent_mines != 1: return None
    if b.kind != "revealed" or b.adjacent_mines != 2: return None
    if c.kind != "revealed" or c.adjacent_mines != 1: return None
    # Check the row above is unrevealed (or row below)
    above = y - 1
    if above < 0: return None
    above_cells = [board.cells[above][x + i] for i in range(3)]
    if not all(c.kind in ("unrevealed", "flagged") for c in above_cells):
        return None
    return {
        "type": "1-2-1",
        "cells": [(x, y), (x + 1, y), (x + 2, y)],
        "deduced_safe": [(x + 1, above)],
        "deduced_mines": [(x, above), (x + 2, above)],
    }


def _move_resolves_pattern(pattern: dict, move: Move) -> bool:
    if move.action == Action.LEFT_CLICK:
        return (move.x, move.y) in pattern.get("deduced_safe", [])
    if move.action == Action.RIGHT_CLICK:
        return (move.x, move.y) in pattern.get("deduced_mines", [])
    return False


# ═════════════════════════════════════════════════════════════════════════════
# DEATH CAUSE CLASSIFIER
# (Source: framework — operationalizes "avoidable vs. forced guess" from
#  Beginners Guide @ 10:43)
# ═════════════════════════════════════════════════════════════════════════════

def classify_death(game: Game, solver: Solver = DEFAULT_SOLVER) -> DeathReport | None:
    if game.outcome != Outcome.LOSS or not game.move_log:
        return None

    last_idx = len(game.move_log) - 1
    last_move = game.move_log[last_idx]
    snapshots = list(snapshot_at_each_move(game))
    board_before = snapshots[last_idx][1]

    result = solver.analyze(board_before)
    was_provably_safe = (last_move.x, last_move.y) in result.provably_safe
    was_provably_mine = (last_move.x, last_move.y) in result.provably_mine
    had_any_deduction = bool(result.provably_safe)

    if was_provably_mine:
        cause = "misread"
    elif last_move.action == Action.CHORD:
        cause = "chordError"
    elif had_any_deduction and not was_provably_safe:
        cause = "avoidableGuess"
    else:
        cause = "forcedGuess"

    if is_in_corner(board_before, last_move.x, last_move.y):
        region = "corner"
    elif is_on_edge(board_before, last_move.x, last_move.y):
        region = "edge"
    else:
        region = "center"

    return DeathReport(
        cause=cause,
        cell=(last_move.x, last_move.y),
        region=region,
        surrounding_pattern=None,
        solver_alternative=result.provably_safe[0] if result.provably_safe else None,
    )


# ═════════════════════════════════════════════════════════════════════════════
# GUESS DETECTOR
# ═════════════════════════════════════════════════════════════════════════════

def detect_guesses(game: Game, solver: Solver = DEFAULT_SOLVER) -> GuessReport:
    forced = 0
    avoidable: list[AvoidableGuess] = []
    snapshots = list(snapshot_at_each_move(game))

    for i, move in enumerate(game.move_log):
        if move.action != Action.LEFT_CLICK:
            continue
        board = snapshots[i][1]
        result = solver.analyze(board)

        if (move.x, move.y) in result.provably_safe:
            continue  # not a guess

        if result.provably_safe:
            avoidable.append(AvoidableGuess(
                move_index=i, cell=(move.x, move.y)
            ))
        else:
            forced += 1

    return GuessReport(
        total_guesses=forced + len(avoidable),
        forced_guesses=forced,
        avoidable_guesses=avoidable,
    )


# ═════════════════════════════════════════════════════════════════════════════
# LEVEL DIAGNOSIS — now scores all 7 Bootcamp levels
# (Source: framework — Bootcamp levels 1-7)
# ═════════════════════════════════════════════════════════════════════════════

def diagnose_level(recent_games: list[Game], solver: Solver = DEFAULT_SOLVER) -> LevelDiagnosis:
    """
    Aggregate across recent games to determine current Bootcamp level.

    Levels 1-4 use the Part 1 framework metrics.
    Levels 5-7 import their criteria from the Dard passes (see passes_dard.py
    where each level's mastery is computed).

    This function only computes Levels 1-4 mastery here; Levels 5-7 are
    finalized by pipeline.diagnose_level_full() once all reports are available.
    """
    if not recent_games:
        return LevelDiagnosis(
            current_level=1, level_mastery={k: 0.0 for k in range(1, 8)},
            blockers=["No recent games"],
        )

    total_wasted = total_clicks = total_shortcuts = total_stranded = 0
    total_ioe = 0.0
    n = 0

    for g in recent_games:
        w = detect_wasted_clicks(g)
        s = detect_shortcuts(g)
        sf = detect_stranded_flags(g)
        total_wasted += len(w.wasted)
        total_clicks += w.total_clicks
        total_shortcuts += len(s.missed)
        total_stranded += len(sf)
        total_ioe += (g.three_bv / w.total_clicks) if w.total_clicks else 0
        n += 1

    correctness = (total_clicks - total_wasted) / total_clicks if total_clicks else 0
    avg_shortcuts = total_shortcuts / n
    avg_stranded = total_stranded / n
    avg_ioe = total_ioe / n

    l1 = _clamp01((correctness - 0.7) / 0.2)
    l2 = _clamp01(1 - avg_shortcuts / 12)
    l3 = _clamp01(1 - avg_stranded / 8)
    l4 = _clamp01((avg_ioe - 0.7) / 0.2)

    # L5-7 placeholders — finalized by pipeline once Dard passes have run
    mastery = {1: l1, 2: l2, 3: l3, 4: l4, 5: 0.0, 6: 0.0, 7: 0.0}

    blockers: list[str] = []
    current = 7
    for level in range(1, 8):
        if mastery[level] < 0.85:
            current = level
            if level == 1:
                blockers.append(f"Correctness {correctness*100:.0f}% — target 85%+")
            elif level == 2:
                blockers.append(f"{avg_shortcuts:.1f} flag-then-chord redundancies/game — target ≤3")
            elif level == 3:
                blockers.append(f"{avg_stranded:.1f} stranded flags/game — target ≤1")
            elif level == 4:
                blockers.append(f"Avg IOE {avg_ioe:.2f} — target 0.90+")
            break

    return LevelDiagnosis(
        current_level=current,
        level_mastery=mastery,
        blockers=blockers,
    )


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


# ═════════════════════════════════════════════════════════════════════════════
# Helpers (private)
# ═════════════════════════════════════════════════════════════════════════════

def _paired_snapshots(game: Game):
    """Iterator over (move_index, board_before) for the basic stats loop."""
    board = fresh_board(game)
    yield -1, board
    for i in range(len(game.move_log)):
        yield i, clone_board(board)
        apply_move(board, game.move_log[i])
