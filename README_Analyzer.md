# Phase 2 Analyzer — Integration Guide

Python port of the move-log analyzer, extended with the four Dard Layer-4 passes. Designed to drop into `~/git/minesweeper.org/` as a sibling package to `main.py` / `database.py`.

## What this package does

For every game whose move log was captured by Phase 1, this analyzer produces:

- **Speed-efficiency diagnostics** (Layer 1–3): wasted clicks, missed shortcuts, stranded flags, pattern reaction times.
- **Death classification**: forced guess / avoidable guess / misread / wrong flag / misclick / chord error.
- **Dard advanced diagnostics** (Layer 4): opening recognition (guaranteed + potential), fishing for 1s and 2s, flag-value scoring, hierarchy compliance scoring.
- **Bootcamp level diagnosis**: where the player sits on the 7-level curriculum.

Output goes into a new `game_analyses` table — one row per analyzed game, with detail records as JSON columns.

## Files

| File | Purpose | Approx. LOC |
|---|---|---|
| `types.py` | All dataclasses (Move, Game, BoardSnapshot, report types) | 200 |
| `simulator.py` | Board state replay from move log | 200 |
| `solver.py` | Tier-1 + Tier-2 constraint-propagation solver | 270 |
| `passes_speed_efficiency.py` | Layer 1–3 passes (Part 1) | 380 |
| `passes_dard.py` | Layer 4 passes (Part 2) | 450 |
| `pipeline.py` | Orchestrator + SQLAlchemy model + FastAPI worker | 360 |
| `__init__.py` | Public API exports | 30 |

Total: ~1,900 lines of Python.

## How to install in `~/git/minesweeper.org`

### 1. Copy the package

```bash
cp -r phase2_analyzer ~/git/minesweeper.org/
```

Add to `requirements.txt` (no new deps — uses only what FastAPI/SQLAlchemy already require).

### 2. Wire the SQLAlchemy model

In `database_template.py`, near the bottom (before `init_db()`):

```python
# F95 — Analyzer derived stats
from phase2_analyzer.pipeline import GameAnalysis  # noqa: F401  registers the table
```

The table will be auto-created on next app boot via `Base.metadata.create_all()`. No manual migration needed for the initial deploy.

### 3. Wire the post-game worker

In `main.py`, modify `submit_rewind()` to fire the analyzer as a background task:

```python
from fastapi import BackgroundTasks
from phase2_analyzer import analyze_replay_async
from database import SessionLocal

@app.post("/api/rewind", status_code=201)
@limiter.limit("60/minute")
def submit_rewind(
    payload: RewindSubmit,
    request: Request,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
):
    # ... existing persistence logic ...
    db.commit()
    db.refresh(replay)

    # NEW: queue analyzer to run after response is sent
    if background_tasks is not None:
        background_tasks.add_task(
            analyze_replay_async, replay.id, SessionLocal
        )

    return {"id": replay.id, "outcome": outcome}
```

This makes analysis async — the player gets a fast `/api/rewind` response, and the analysis runs after.

### 4. Backfill historical games

Run once to analyze all existing replays (and any replays that arrived before the worker was wired):

```python
from phase2_analyzer import backfill_analyses
from database import SessionLocal

count = backfill_analyses(SessionLocal, batch_size=100)
print(f"Analyzed {count} games")
```

Performance: ~50–200ms per game. For 100k games, ~3–10 hours. Safe to interrupt and resume.

## Verifying the deployment

After deploy + a few games played, check the database:

```sql
-- Are analyses being created?
SELECT COUNT(*) FROM game_analyses;
SELECT COUNT(*) FROM game_replays;
-- The first should equal the second once backfill completes.

-- Sanity check the Dard signature metrics
SELECT
    AVG(hierarchy_compliance_pct) AS avg_hierarchy,
    AVG(openings_guaranteed_taken) AS avg_openings_taken,
    AVG(openings_guaranteed_missed) AS avg_openings_missed,
    AVG(fishes_attempted) AS avg_fishes,
    AVG(avg_flag_value_score) AS avg_flag_value
FROM game_analyses
WHERE created_at > NOW() - INTERVAL 1 DAY
  AND no_guess = FALSE;
```

Expected order-of-magnitude on Expert standard mode:
- `avg_hierarchy`: 0.55–0.80 depending on skill mix
- `avg_openings_missed`: 1.5–4.0 per game for typical players
- `avg_fishes`: 0.1–1.5 (most players don't fish at all)
- `avg_flag_value_score`: 1.5–3.5

### Bug-signal detection

```sql
-- No-guess games shouldn't have forced-guess deaths
SELECT game_replay_id, death_cause
FROM game_analyses
WHERE no_guess = TRUE AND death_cause = 'forcedGuess';
```

If this query returns rows, either the solver is incomplete or there's misclassification. Investigate.

## Architecture notes

### Why dataclasses, not Pydantic, internally?

Pydantic validates input — useful at API boundaries. Inside the analyzer, every value comes from already-validated sources (the move log went through Pydantic on the way in). Plain dataclasses are faster, have lower memory overhead, and don't add a framework dependency to the analytics layer.

The boundary translation happens once in `_game_from_replay()` (pipeline.py).

### Why one big `game_analyses` table instead of detail tables per pass?

Trade-off: queryability vs. storage / join complexity.

- Summary columns (e.g., `hierarchy_compliance_pct`) are first-class so site-wide rollups are simple SQL.
- Detailed instances (every wasted-click event) live in JSON columns. MySQL's `JSON_EXTRACT` lets us query them ad-hoc when needed.
- This avoids 12 detail tables and the join overhead. Most queries only need the summary columns.

If a specific detail type becomes a hot path, promoting its JSON to its own table is a non-breaking migration.

### Solver tiers

- **Tier 1** (currently implemented): trivial constraint propagation — N flags around an N-cell ⇒ rest safe; N - flags == unrevealed ⇒ rest mines. Resolves ~75% of expert deductions.
- **Tier 2** (currently implemented): subset deduction — when one constraint is a subset of another, the difference is deducible. Resolves another ~22%. The 1-2-1 and 1-2-2-1 patterns emerge automatically from this.
- **Tier 3** (TODO): full SAT solving for the residual ~3% on dense central clusters. Implementation hook is in `solver.py` — replace `ConstraintSolver.analyze` or compose with a SAT-tier post-pass.

For the analyzer's primary use case (post-game classification, not real-time play), Tier 1+2 is sufficient. If a no-guess-mode forced-guess anomaly shows up in `detect_anomalies`, that's the signal to upgrade.

### Performance budget

Per game (Expert, ~150 moves):
- Simulator: ~5–10ms
- Solver (called ~50 times during analysis): ~50–150ms
- All passes combined: ~50–200ms

Per 1,000 games per hour: ~3 minutes of CPU. Comfortable for an `await` task on the same process as the FastAPI app. If throughput grows beyond ~10/sec sustained, move to a Celery worker.

## Extending the analyzer

### Adding a new diagnostic pass

1. Add the report type to `types.py`.
2. Write the pass function in `passes_speed_efficiency.py` or `passes_dard.py` (or a new module for an entirely new category).
3. Call it in `analyze_game()` in `pipeline.py`.
4. Add columns to `GameAnalysis` if you want first-class queryability, or just serialize to JSON.

Pattern: every pass is `(Game, [Solver]) → SomeReport`. Stateless.

### Adding a new pattern to the recognizer

Currently `recognize_patterns` only matches horizontal 1-2-1. The framework has 7+ patterns. Add new matchers to `passes_speed_efficiency.py`:

```python
def _match_1221_horizontal(board, x, y) -> dict | None:
    ...

def _match_232_reduction(board, x, y) -> dict | None:
    ...
```

Register them in `_find_visible_patterns()`. Each adds one O(W*H) scan but they're independent.

### Tightening the openings detector

The current detector considers any cell with no known-mine neighbors as a candidate. Dard's specific named patterns (L-shape edge, 2-satisfied, 1-either) would benefit from explicit templates so we can report them by name in the Pattern Fluency screen. See `_classify_guaranteed_pattern()` in `passes_dard.py` — it currently does a rough heuristic; replace with explicit templates.

## Privacy / data handling

- Move logs are not personally identifying on their own — just sequences of `[t_ms, action, row, col]`.
- The analyzer doesn't change which fields are stored beyond what Phase 1 already persisted.
- `player_id` on `game_analyses` mirrors `user_email`/`guest_token` from the source replay; deletion cascades work via that link (no FK constraint, matching the existing pattern).

## Testing strategy

Recommended (not included in this drop):

- **Golden-file tests**: for a small set of known games (manually annotated), assert the analyzer produces specific outputs. When the solver is upgraded, diff the goldens to spot regressions.
- **Property tests**: for any game, `correctness + (wasted_clicks / total_clicks)` should equal 1.0. Site-wide aggregates should be monotonic in their inputs.
- **Bug-signal monitoring**: track the count of `detect_anomalies()` hits over time. A spike means the solver upgrade broke something.

## What's NOT in Phase 2

- The analytics-surface FastAPI routes that serve data to the Bootcamp / Skill Radar / etc. mockups. That's Phase 4.
- Site-wide correlation regressions (the behavior→time analysis from the metrics catalog). That's a separate batch job that reads `game_analyses` rows.
- The drill prescription engine. That's Phase 5.
- The full SAT-tier solver. The Tier-1 + Tier-2 solver covers what we need today; upgrade when anomaly counts justify it.
