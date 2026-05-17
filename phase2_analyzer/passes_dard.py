"""
analyzer.passes_dard — Layer 4 passes from Dard's Speed-Efficiency Part 2.

Four passes:
  detect_openings        — guaranteed + potential openings (2:40, 4:06)
  detect_fishing         — fishing for 1s and 2s (10:21)
  score_flag_value       — per-flag value based on future chord uses (7:24)
  score_hierarchy_compliance — the unifying decision-hierarchy metric (13:20)

Each pass is a coachable signal. The hierarchy compliance pass is the most
important — it operationalizes "playing like Dard" by checking whether each
move chose the highest-priority option available.

The Dard probability table (Part 2 @ 5:21) is the basis for opening EV:
  2 unknowns: expert ~62%, intermediate higher
  3 unknowns: expert 50.0%, intermediate 60.1%
  4 unknowns: expert 39.7%, intermediate 50.7%
"""

from __future__ import annotations

from .simulator import (
    all_neighbors,
    apply_move,
    clone_board,
    flagged_neighbors,
    fresh_board,
    snapshot_at_each_move,
    unrevealed_neighbors,
)
from .solver import (
    DEFAULT_SOLVER,
    Solver,
    adjacent_known_mines,
    adjacent_unknown_count,
    is_on_edge,
)
from .types import (
    Action,
    BoardSnapshot,
    Difficulty,
    FishingOpportunity,
    FishingReport,
    FlagValue,
    FlagValueReport,
    Game,
    HierarchyDeviation,
    HierarchyReport,
    Move,
    OpeningOpportunity,
    OpeningReport,
)


# ═════════════════════════════════════════════════════════════════════════════
# Dard probability tables for potential openings (Part 2 @ 5:21)
# ═════════════════════════════════════════════════════════════════════════════

# probability[difficulty][num_unknown_cells] = chance ALL are non-mine
_OPENING_PROB = {
    Difficulty.BEGINNER: {2: 0.78, 3: 0.71, 4: 0.62, 5: 0.54},
    Difficulty.INTERMEDIATE: {2: 0.72, 3: 0.601, 4: 0.507, 5: 0.422},
    Difficulty.EXPERT: {2: 0.62, 3: 0.500, 4: 0.397, 5: 0.310},
    Difficulty.CUSTOM: {2: 0.55, 3: 0.45, 4: 0.36, 5: 0.28},   # conservative
}

# Threshold for "worth attempting" per Dard's general rules @ 6:18
_OPENING_THRESHOLD = 0.50


def _opening_probability(difficulty: Difficulty, unknowns: int) -> float:
    table = _OPENING_PROB.get(difficulty, _OPENING_PROB[Difficulty.CUSTOM])
    if unknowns <= 1:
        return 1.0          # essentially guaranteed by other logic
    return table.get(unknowns, 0.20)


# ═════════════════════════════════════════════════════════════════════════════
# PASS: OPENING DETECTOR
# (Source: Dard Part 2 @ 2:40 – Guaranteed openings · @ 4:06 – Potential)
# ═════════════════════════════════════════════════════════════════════════════

def detect_openings(game: Game, solver: Solver = DEFAULT_SOLVER) -> OpeningReport:
    """
    Identify opening opportunities throughout the game.

    For each move's board state, find:
      - Guaranteed openings: unrevealed cells where ALL neighbors are provably
        non-mine. Click → flood reveal.
      - Potential openings: unrevealed cells with no known-mine neighbors but
        K unknown neighbors. Probability of opening = product of (cell-not-mine).

    An opportunity is "taken" if the player's next click on that cell is a
    left-click. Otherwise it's "missed."
    """
    opportunities: list[OpeningOpportunity] = []
    seen_cells: set[tuple[int, int]] = set()    # dedupe across moves
    snapshots = list(snapshot_at_each_move(game))

    for i, move in enumerate(game.move_log):
        board = snapshots[i][1]   # state BEFORE this move
        result = solver.analyze(board)
        known_mines = set(result.provably_mine)

        for x, y in result.provably_safe + _all_unknown_with_no_mine_neighbors(board, known_mines):
            if (x, y) in seen_cells:
                continue
            if board.cells[y][x].kind != "unrevealed":
                continue

            unknowns = adjacent_unknown_count(board, x, y, known_mines)
            if unknowns == 0:
                kind = "guaranteed"
                prob = 1.0
                pattern = _classify_guaranteed_pattern(board, x, y)
            else:
                prob = _opening_probability(game.difficulty, unknowns)
                if prob < _OPENING_THRESHOLD:
                    continue
                kind = "potential"
                pattern = None

            taken = (move.action == Action.LEFT_CLICK
                     and move.x == x and move.y == y)
            opportunities.append(OpeningOpportunity(
                move_index=i,
                cell=(x, y),
                kind=kind,
                pattern=pattern,
                probability=prob,
                cells_required_safe=unknowns,
                taken_by_player=taken,
                estimated_clicks_saved=_estimated_clicks_saved(board, x, y),
            ))
            seen_cells.add((x, y))

    # Roll up
    g_taken = sum(1 for o in opportunities if o.kind == "guaranteed" and o.taken_by_player)
    g_missed = sum(1 for o in opportunities if o.kind == "guaranteed" and not o.taken_by_player)
    p_taken = sum(1 for o in opportunities if o.kind == "potential" and o.taken_by_player)
    p_missed = sum(1 for o in opportunities if o.kind == "potential" and not o.taken_by_player)

    # Estimated time cost: 0.5s per missed click avg
    seconds_lost = sum(
        o.estimated_clicks_saved * 0.5
        for o in opportunities
        if not o.taken_by_player
    )

    return OpeningReport(
        opportunities=opportunities,
        guaranteed_taken=g_taken,
        guaranteed_missed=g_missed,
        potential_taken=p_taken,
        potential_missed=p_missed,
        estimated_seconds_lost=round(seconds_lost, 1),
    )


def _all_unknown_with_no_mine_neighbors(
    board: BoardSnapshot, known_mines: set[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Unrevealed cells that have no known-mine adjacent — potential opening
    candidates per Dard's "find a square that is not next to any of your known mines."""
    out: list[tuple[int, int]] = []
    for y in range(board.height):
        for x in range(board.width):
            if board.cells[y][x].kind != "unrevealed":
                continue
            if adjacent_known_mines(board, x, y, known_mines) == 0:
                # Must be adjacent to at least one revealed cell (otherwise
                # we'd consider the whole unexplored region)
                has_revealed_neighbor = False
                for nx, ny in all_neighbors(x, y):
                    if not board.in_bounds(nx, ny):
                        continue
                    if board.cells[ny][nx].kind == "revealed":
                        has_revealed_neighbor = True
                        break
                if has_revealed_neighbor:
                    out.append((x, y))
    return out


def _classify_guaranteed_pattern(
    board: BoardSnapshot, x: int, y: int
) -> str | None:
    """
    Identify which Dard-named guaranteed opening pattern this cell belongs to.
    Returns 'L-shape-edge', '2-satisfied-edge', '1-either-edge', or None.
    """
    if not is_on_edge(board, x, y):
        return None
    # Heuristic: look at adjacent revealed numbers
    adj_ones = adj_twos = 0
    for nx, ny in all_neighbors(x, y):
        if not board.in_bounds(nx, ny):
            continue
        cell = board.cells[ny][nx]
        if cell.kind == "revealed":
            if cell.adjacent_mines == 1:
                adj_ones += 1
            elif cell.adjacent_mines == 2:
                adj_twos += 1
    if adj_ones >= 2:
        return "L-shape-edge"
    if adj_twos >= 1:
        return "2-satisfied-edge"
    if adj_ones >= 1:
        return "1-either-edge"
    return "edge-deduction"


def _estimated_clicks_saved(board: BoardSnapshot, x: int, y: int) -> int:
    """
    Rough estimate of how many cells a flood-reveal from (x, y) would clear.
    Used to weight the cost of missing an opening. A real implementation
    would simulate the flood; this approximation counts adjacent unrevealed
    cells * 1.5 as a reasonable proxy for typical openings.
    """
    unrevealed_adj = sum(
        1 for nx, ny in all_neighbors(x, y)
        if board.in_bounds(nx, ny) and board.cells[ny][nx].kind == "unrevealed"
    )
    return max(1, int(unrevealed_adj * 1.5))


# ═════════════════════════════════════════════════════════════════════════════
# PASS: FISHING DETECTOR
# (Source: Dard Part 2 @ 10:21 – Fishing)
# ═════════════════════════════════════════════════════════════════════════════

def detect_fishing(game: Game, solver: Solver = DEFAULT_SOLVER) -> FishingReport:
    """
    Identify fishing opportunities:
      Fishing for 1 — clicking a known-safe cell adjacent to exactly one
                      unknown mine candidate. If revealed value == 1, a chord
                      opportunity is created.
      Fishing for 2 — known-safe cell adjacent to one flagged mine plus
                      one unknown mine candidate. Revealed 2 → new chord.

    Only known-safe cells count (per Dard @ 11:50: "I will only be referring
    to known safe cells when considering these options").
    """
    opportunities: list[FishingOpportunity] = []
    snapshots = list(snapshot_at_each_move(game))

    for i, move in enumerate(game.move_log):
        board = snapshots[i][1]
        result = solver.analyze(board)
        known_mines = set(result.provably_mine)
        safe_set = set(result.provably_safe)

        # Find fishing candidates for this turn (top-3 by expected value)
        candidates = _fishing_candidates(board, safe_set, known_mines)

        for cand in candidates:
            taken = (move.action == Action.LEFT_CLICK
                     and move.x == cand["x"] and move.y == cand["y"])

            succeeded = None
            if taken:
                # Simulate the click; check if revealed number creates chord
                after = clone_board(board)
                apply_move(after, move)
                if 0 <= move.y < after.height and 0 <= move.x < after.width:
                    revealed = after.cells[move.y][move.x]
                    if revealed.kind == "revealed":
                        # Did this reveal create a chord opportunity?
                        flags_around = len(flagged_neighbors(after, move.x, move.y))
                        succeeded = (revealed.adjacent_mines == flags_around
                                     and revealed.adjacent_mines > 0)

            opportunities.append(FishingOpportunity(
                move_index=i,
                cell=(cand["x"], cand["y"]),
                kind=cand["kind"],
                success_probability=cand["probability"],
                taken_by_player=taken,
                succeeded=succeeded,
            ))

            # Only score the top opportunity per turn to avoid noise
            break

    attempted = sum(1 for o in opportunities if o.taken_by_player)
    succeeded = sum(1 for o in opportunities if o.succeeded is True)
    missed = sum(1 for o in opportunities if not o.taken_by_player)

    return FishingReport(
        opportunities=opportunities,
        fishes_attempted=attempted,
        fishes_succeeded=succeeded,
        fishes_missed=missed,
    )


def _fishing_candidates(
    board: BoardSnapshot,
    safe_set: set[tuple[int, int]],
    known_mines: set[tuple[int, int]],
) -> list[dict]:
    """Return up to 3 best fishing candidates on the board, sorted by EV."""
    candidates: list[dict] = []

    for sx, sy in safe_set:
        # Must still be unrevealed (otherwise the deduction was made already)
        if board.cells[sy][sx].kind != "unrevealed":
            continue

        unknown_neighbors = []
        flagged_count = 0
        for nx, ny in all_neighbors(sx, sy):
            if not board.in_bounds(nx, ny):
                continue
            cell = board.cells[ny][nx]
            if cell.kind == "flagged":
                flagged_count += 1
            elif cell.kind == "unrevealed" and (nx, ny) not in safe_set:
                unknown_neighbors.append((nx, ny))

        n_unknown = len(unknown_neighbors)

        # Fishing for 1: exactly one unknown mine candidate, no flagged
        if flagged_count == 0 and n_unknown == 1:
            candidates.append({
                "x": sx, "y": sy,
                "kind": "fishing-for-1",
                "probability": 0.5,   # rough — refine using global mine density
            })
        # Fishing for 2: one flagged + one unknown candidate
        elif flagged_count == 1 and n_unknown == 1:
            candidates.append({
                "x": sx, "y": sy,
                "kind": "fishing-for-2",
                "probability": 0.5,
            })

    # Sort by probability, return top 3
    candidates.sort(key=lambda c: -c["probability"])
    return candidates[:3]


# ═════════════════════════════════════════════════════════════════════════════
# PASS: FLAG-VALUE SCORER
# (Source: Dard Part 2 @ 7:24 – Efficient flagging)
# ═════════════════════════════════════════════════════════════════════════════

def score_flag_value(game: Game) -> FlagValueReport:
    """
    For each flag placed, count how many subsequent chords used it. Higher
    use → higher value. Plus a position bonus for central flags surrounded
    by uncleared cells (per Dard's "flags deeper and surrounded by more
    uncleared cells are likely to be more valuable").
    """
    flag_records: list[FlagValue] = []
    snapshots = list(snapshot_at_each_move(game))

    for i, move in enumerate(game.move_log):
        if move.action != Action.RIGHT_CLICK:
            continue
        before = snapshots[i][1]
        if before.cells[move.y][move.x].kind != "unrevealed":
            continue  # this was an unflag, not a flag placement

        future_uses = _count_future_chord_uses(game, i, move.x, move.y)
        # Position bonus: how many uncleared cells surround the flag at placement
        uncleared = sum(
            1 for nx, ny in all_neighbors(move.x, move.y)
            if before.in_bounds(nx, ny)
            and before.cells[ny][nx].kind in ("unrevealed", "flagged")
        )
        edge_penalty = 0.5 if is_on_edge(before, move.x, move.y) else 1.0

        # value = future_uses + 0.3 * uncleared_around, scaled by edge_penalty
        score = (future_uses + 0.3 * uncleared) * edge_penalty
        high_value = score >= 2.0

        flag_records.append(FlagValue(
            move_index=i,
            cell=(move.x, move.y),
            future_chord_uses=future_uses,
            value_score=round(score, 2),
            high_value=high_value,
        ))

    if not flag_records:
        return FlagValueReport(
            flags=[], avg_value_score=0.0,
            high_value_count=0, low_value_count=0,
            high_value_pct=0.0,
        )

    avg = sum(f.value_score for f in flag_records) / len(flag_records)
    high = sum(1 for f in flag_records if f.high_value)
    low = len(flag_records) - high
    pct = high / len(flag_records) if flag_records else 0

    return FlagValueReport(
        flags=flag_records,
        avg_value_score=round(avg, 2),
        high_value_count=high,
        low_value_count=low,
        high_value_pct=round(pct, 2),
    )


def _count_future_chord_uses(game: Game, flag_idx: int, fx: int, fy: int) -> int:
    """Count chord moves at adjacent cells after the flag was placed."""
    count = 0
    for j in range(flag_idx + 1, len(game.move_log)):
        m = game.move_log[j]
        if m.action == Action.CHORD and abs(m.x - fx) <= 1 and abs(m.y - fy) <= 1:
            count += 1
        if m.action == Action.RIGHT_CLICK and m.x == fx and m.y == fy:
            break  # flag was removed
    return count


# ═════════════════════════════════════════════════════════════════════════════
# PASS: HIERARCHY COMPLIANCE
# (Source: Dard Part 2 @ 13:20 – The decision hierarchy)
#
# Dard's priority order:
#   1. Opening with >50% chance → left-click
#   2. Worth-it flag-and-chord
#   3. Fishing for a good chord
#   4. Opening with <50% chance (especially when NF-clearing anyway)
#   5. Default no-flag clearing
#
# This pass is the integration point of every other Dard pass. It tags each
# move with the player's chosen priority and the optimal priority available.
# ═════════════════════════════════════════════════════════════════════════════

def score_hierarchy_compliance(
    game: Game,
    opening_report: OpeningReport,
    fishing_report: FishingReport,
    solver: Solver = DEFAULT_SOLVER,
) -> HierarchyReport:
    """
    Per-move compliance scoring against Dard's decision hierarchy.

    Inputs `opening_report` and `fishing_report` provide pre-computed
    opportunities so this pass doesn't re-run the solver from scratch.
    """
    # Index opportunities by move_index for O(1) lookup
    open_by_move: dict[int, list[OpeningOpportunity]] = {}
    for o in opening_report.opportunities:
        open_by_move.setdefault(o.move_index, []).append(o)

    fish_by_move: dict[int, list[FishingOpportunity]] = {}
    for f in fishing_report.opportunities:
        fish_by_move.setdefault(f.move_index, []).append(f)

    deviations: list[HierarchyDeviation] = []
    compliant = 0
    by_priority: dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    for i, move in enumerate(game.move_log):
        if move.action == Action.RIGHT_CLICK:
            # Flags are a means, not a primary choice — skip for compliance
            continue

        opt_priority, opt_label = _optimal_priority(
            open_by_move.get(i, []),
            fish_by_move.get(i, []),
            move,
        )
        chosen_priority, chosen_label = _chosen_priority(
            move, open_by_move.get(i, []), fish_by_move.get(i, [])
        )

        if chosen_priority == opt_priority:
            compliant += 1
        else:
            by_priority[opt_priority] = by_priority.get(opt_priority, 0) + 1
            deviations.append(HierarchyDeviation(
                move_index=i,
                player_choice=chosen_label,
                optimal_choice=opt_label,
                optimal_priority=opt_priority,
                chosen_priority=chosen_priority,
                estimated_cost=_deviation_cost(opt_priority, chosen_priority),
            ))

    total = compliant + len(deviations)
    pct = (compliant / total) if total else 1.0

    return HierarchyReport(
        total_moves=total,
        compliant_moves=compliant,
        compliance_pct=round(pct, 3),
        deviations=deviations,
        deviation_by_priority=by_priority,
    )


def _optimal_priority(
    openings: list[OpeningOpportunity],
    fishes: list[FishingOpportunity],
    move: Move,
) -> tuple[int, str]:
    """Return (priority, label) of the highest-priority option available."""
    # Priority 1: guaranteed or >50% potential opening
    high_ev = [o for o in openings if o.probability > _OPENING_THRESHOLD]
    if high_ev:
        kind = "guaranteed" if any(o.kind == "guaranteed" for o in high_ev) else "potential>50%"
        return 1, f"opening-{kind}"

    # Priority 2: worth-it chord (proxy: any chord that's not on this move)
    # Without re-running the worth-it-chord detection, we approximate:
    # if the move was a chord and cleared cells, treat as P2.
    # (A full implementation would call detect_shortcuts inversely.)

    # Priority 3: fishing
    if fishes:
        return 3, f"fishing-{fishes[0].kind}"

    # Priority 4: low-EV opening
    low_ev = [o for o in openings if o.probability <= _OPENING_THRESHOLD]
    if low_ev:
        return 4, "opening-low-EV"

    # Priority 5: default
    return 5, "default-clearing"


def _chosen_priority(
    move: Move,
    openings: list[OpeningOpportunity],
    fishes: list[FishingOpportunity],
) -> tuple[int, str]:
    """Determine which priority bucket the player's actual move falls into."""
    if move.action == Action.CHORD:
        return 2, "chord"
    if move.action == Action.LEFT_CLICK:
        # Did they click an opening?
        for o in openings:
            if o.cell == (move.x, move.y) and o.taken_by_player:
                if o.probability > _OPENING_THRESHOLD:
                    return 1, f"opening-{o.kind}"
                return 4, "opening-low-EV"
        # Did they fish?
        for f in fishes:
            if f.cell == (move.x, move.y) and f.taken_by_player:
                return 3, f"fishing-{f.kind}"
        return 5, "default-clearing"
    # right-click handled by caller
    return 5, "other"


def _deviation_cost(optimal: int, chosen: int) -> int:
    """Heuristic click-cost of choosing a lower-priority option."""
    gap = chosen - optimal
    return max(1, gap * 2)
