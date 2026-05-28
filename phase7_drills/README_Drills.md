# phase7_drills — "Start today's drill" feature

Adds a procedural drill runner backing the **Start today's drill** button on the Bootcamp page. First drill shipped is **L5 Opening Recognition** — Pick-the-best-cell on a partially-revealed expert board, 10 boards per session.

This is additive to phase4 + phase5. No changes to existing tables, no breaking changes to existing routes.

## What ships

### New package: `phase7_drills/`

| File | Purpose |
|---|---|
| `__init__.py` | Re-exports `api_router` and `page_router` for `app.include_router` |
| `generator.py` | Procedural board generation + click evaluation. Standalone. |
| `mastery.py` | Converts a finished drill into a 0..1 mastery score; weighted at 0.3x |
| `models.py` | `DrillSession` ORM model (one row per drill) |
| `response_models.py` | Pydantic models for the API |
| `routes.py` | Three JSON endpoints + one HTML page |
| `schema_sql.py` | DDL for `drill_sessions` table (idempotent) |
| `templates/drill.html` | Standalone `/drill/{id}` page |
| `static/css/drill.css` | Drill UI styles |
| `static/js/drill.js` | Client-side runner: render board → submit → feedback → results |

### Edits to existing files

| File | Change |
|---|---|
| `phase5_bootcamp/static/js/bootcamp.js` | Added delegated handler for `[data-action="start-drill"]`; only L5 is wired today, other levels show a brief "Drill coming soon" inline |

No DB-schema changes to `game_analyses` or any phase 1-6 tables.

## New endpoints

```
POST /api/drills/start                  start a new drill session
GET  /api/drills/{drill_id}             current state (resume / refresh)
POST /api/drills/{drill_id}/submit      submit one board's chosen cell

GET  /drill/{drill_id}                  renders templates/drill.html
```

Rate limits: `20/min` on start, `60/min` on submit and state.

## Deployment steps

### 1. Apply schema

```bash
cd /home/ubuntu/git/minesweeper.org
cp -r /staged/phase7_drills phase7_drills

# Run as a file path, NOT `python3 -m phase7_drills.schema_sql`. The -m form
# triggers __init__.py which would import the FastAPI routes; the migration
# script itself only needs SQLAlchemy.
python3 phase7_drills/schema_sql.py --apply
```

If you want to see the DDL first without running it:

```bash
python3 phase7_drills/schema_sql.py
```

Creates one new table, `drill_sessions`. Idempotent — safe to re-run.

### 2. Mount routes in `main.py`

Find the existing `app.include_router(analytics_router)` line (the phase4 mount) and add the two new routers next to it:

```python
from phase4_routes import router as analytics_router
from phase7_drills import api_router as drills_api_router, page_router as drills_page_router

app.include_router(analytics_router)
app.include_router(drills_api_router)
app.include_router(drills_page_router)
```

`page_router` needs the project's `templates` and `get_current_user` to be importable from `main`. That's already the case — `phase7_drills/routes.py` matches the same import shape as `phase4_routes/routes.py`.

### 3. Wire the model into the metadata

`DrillSession` uses the project's shared `Base`, so `Base.metadata.create_all()` (or your existing startup hook) will pick it up automatically. The `schema_sql.py` migration in step 1 makes this explicit.

### 4. Copy static + template files

```bash
cp phase7_drills/templates/drill.html       templates/drill.html
cp phase7_drills/static/css/drill.css       static/css/drill.css
cp phase7_drills/static/js/drill.js         static/js/drill.js
```

### 5. Update `bootcamp.js`

Either copy the new file in:

```bash
cp phase5_bootcamp/static/js/bootcamp.js    static/js/bootcamp.js
```

…and bump the cache-buster in `bootcamp.html`:

```html
<link rel="stylesheet" href="/static/css/bootcamp.css?v=2" />
<script src="/static/js/bootcamp.js?v=3"></script>
```

### 6. Restart

```bash
sudo systemctl restart staging-minesweeper
```

### 7. Smoke-test

```bash
# Start a drill
curl -s -X POST "http://localhost:8002/api/drills/start" \
  -H "Cookie: session=<your-session>" \
  -H "Content-Type: application/json" \
  -d '{"drill_type":"l5_opening_recognition","level":5,"difficulty":"expert","mode":"standard","num_boards":3}' \
  | python3 -m json.tool | head -40
```

Expected: `200` with `drill_id`, `boards: [...3 visible boards...]`, `drill_version: "1.0"`.

Then in a browser:
1. Visit `/bootcamp`
2. Click **Start today's drill** on the L5 card (it has to be your current level, or click on the L5 card if you've already mastered it — both should work)
3. You should be on `/drill/{id}` with a board rendered
4. Click cells. After each click, feedback overlay appears showing whether your pick was within 80% of the optimal opening
5. After 10 boards, results screen shows accuracy, avg decision time, mastery score (0..1)

## Data flow

1. Player clicks **Start today's drill** → `bootcamp.js` POSTs `/api/drills/start` with the current mode
2. Server seeds RNG off `(player_id, time)`, generates 10 expert boards (30×16, 99 mines)
3. Each board is generated such that:
   - Some cells are revealed (~25% of board) via flood-fill from a random safe cell
   - At least one *safe* unrevealed cell would open ≥ 12 new cells
   - "Correct" cells = any safe unrevealed cell whose next-opening is ≥ 80% of the maximum
4. Server stores the full board state (including secret mines) in `drill_sessions.boards_json` and returns only the visible state to the client
5. Client renders each board in turn. Click → POST `/api/drills/{id}/submit` with `(board_index, row, col, decision_ms)`
6. Server validates the click via `generator.evaluate_click()`, returns the verdict + the optimal cell (revealed to the player as feedback)
7. After the final board, the server populates `num_correct`, `avg_decision_ms`, `mastery_contribution`, `counted_toward_mastery` and sets `completed_at`

## How mastery contribution is computed

`phase7_drills/mastery.py`:

    base        = accuracy                              # 0..1
    speed_bonus = clamp((4000 - avg_ms) / 4000, 0, 0.15)
    mastery     = clamp(base + speed_bonus, 0, 1.0)

Weight in the rolling-10 average is `DRILL_WEIGHT = 0.3` (chosen via the AskUserQuestion decision earlier). A drill counts as 30% of a live game.

`blend_into_rolling_average(game_values, drill_values)` is the helper for the bootcamp diagnosis query to use when it's extended. Today the diagnosis query reads only `game_analyses`; the integration with drills is the follow-up patch described below.

## What still ships separately (follow-up patches)

The drill writes `mastery_contribution` and `counted_toward_mastery` to its row. Two integration points still need a small patch to actually surface the drill mastery in the UI:

### A. Bootcamp diagnosis query

`phase4_routes/queries.py::get_bootcamp_diagnosis` currently only averages `game_analyses.level_mastery_json`. To include drills:

```python
# In queries.py, near where the rolling-10 mastery is computed:
from phase7_drills.mastery import blend_into_rolling_average, weight as drill_weight
from phase7_drills.models import DrillSession

drill_rows = (
    db.query(DrillSession)
      .filter(DrillSession.player_id == player_id)
      .filter(DrillSession.level == level)
      .filter(DrillSession.completed_at.isnot(None))
      .filter(DrillSession.counted_toward_mastery == True)
      .order_by(DrillSession.completed_at.desc())
      .limit(10).all()
)
drill_values = [d.mastery_contribution for d in drill_rows if d.mastery_contribution is not None]

mastery = blend_into_rolling_average(game_values, drill_values)
```

Same shape applies to `get_level_progress` (the View Progress modal) — we just need to merge drill data points into the time series.

### B. Trigger ETA / trend updates

The View Progress modal computes "ETA to graduation". If drill activity is included, players will see faster ETA. This is desirable but worth flagging on the modal so users understand the blended source.

I've left those two integration patches out of this push to keep it small and reversible. Both are <30 lines.

## Edge cases handled

- **Resume**: refreshing `/drill/{id}` reloads the session and skips already-answered boards.
- **Idempotent submit**: re-submitting the same `board_index` returns the prior verdict (defensive against double-clicks / retries).
- **Drill already completed**: submitting to a completed drill returns 409. Reloading the page shows the results screen.
- **Drill not found / not yours**: returns 404 (no leak of existence).
- **Invalid clicks**: out-of-bounds or on already-revealed cells are scored as "wrong" rather than erroring.
- **Generator can't find a big-opening board**: 20 attempts with different seeds; raises if all fail (extremely rare; default constants make this near-impossible).
- **Empty drill (0 boards)**: rejected by Pydantic — `num_boards >= 1`.
- **Cheating via devtools**: mine layout is never sent to the client; verdicts are server-computed.

## Future work — the rest of the drill catalog

| Level | Drill name | Status |
|---|---|---|
| L1 | Cut waste — chord-or-click | TODO |
| L2 | Effective chord — flag-then-chord rhythm | TODO |
| L3 | Strategic NF — recognise safe non-flag chords | TODO |
| L4 | Pure efficiency — minimum-click solutions | TODO |
| **L5** | **Opening recognition** | **shipped (this README)** |
| L6 | Flag value — which flag opens more | TODO |
| L7 | Fishing & hierarchy — multi-step solver patterns | TODO |

The generator + routes + UI shell are reusable. Each new drill is:
1. A new `generate_lN_*` function in `generator.py`
2. A new `drill_type` literal in `response_models.py`
3. (Optionally) drill-type-specific rendering branches in `drill.js`

The harder ones (L6, L7) will need the constraint propagation solver — we already have one in `phase2_analyzer/solver.py` so the work is wiring it up.

## Rollback

Two options:

```bash
# A) Hide just the start-drill button (modal stays, View Progress works fine)
#    Add a CSS rule to bootcamp.css:
#      [data-action="start-drill"] { display: none; }

# B) Remove the routes entirely
#    Comment out the two include_router lines in main.py and restart.
#    drill_sessions table is harmless — no cron writes to it.
```

The `drill_sessions` table is independent of everything else; leaving it in place after rollback has no cost.

## What this enables next

- **Daily streaks**: the `drill_sessions.started_at` index makes a simple "drilled N days in a row" badge cheap.
- **Per-habit drills**: once each level has a drill, we can recommend tomorrow's drill based on which habit was weakest in the most recent live games (the `weakest_habit` field on `BootcampDiagnosis`).
- **Drill leaderboard**: aggregate `accuracy_pct` + `avg_decision_ms` across players for a given drill seed family.
