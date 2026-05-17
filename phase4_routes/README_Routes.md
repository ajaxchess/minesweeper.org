# Phase 4 Routes — Analytics API

FastAPI routes that serve analyzer output to the five mockup screens. Drop into `~/git/minesweeper.org/` as a sibling package to `main.py`, `database.py`, and `phase2_analyzer/`.

## What this package does

For each mockup screen built in Phase 4 mockups, this package provides the API route that returns the data shape the screen expects. The frontend renders directly from these responses — no reshape, no extra requests.

## Route summary

| Endpoint | Screen | Returns |
|---|---|---|
| `GET /api/bootcamp/diagnosis` | Bootcamp | Level diagnosis, 7-level ladder, top-strip stats |
| `GET /api/bootcamp/level/{n}` | Bootcamp | Habits, drills, graduation criteria for one level |
| `GET /api/radar` | Skill Radar | 9-axis player profile + benchmarks + insights |
| `GET /api/patterns/fluency` | Pattern Fluency | Pattern reaction times + leverage + weekly drill plan |
| `GET /api/replays` | Replay browser | Recent replays list |
| `GET /api/replays/{id}` | Replay Analysis | Full replay with annotations + insights |
| `GET /api/heatmap` | Mistake Heatmap | Death cells, cause/region breakdown, anomalies |

All endpoints:
- Require player identity via `get_current_user()` or `guest_token`
- Rate-limited at 30/min per IP
- Support `difficulty=` and `mode=` (`standard|no_guess|both`) query parameters
- Return typed Pydantic responses

## Files

| File | Purpose | Approx. LOC |
|---|---|---|
| `response_models.py` | Pydantic response shapes | 250 |
| `queries.py` | SQLAlchemy query helpers + business logic | 530 |
| `routes.py` | FastAPI endpoints | 580 |
| `__init__.py` | Router export | 10 |

Total: ~1,400 lines.

## How to install

### 1. Copy the package

```bash
cp -r phase4_routes ~/git/minesweeper.org/
```

No new dependencies — uses what FastAPI + Pydantic v2 + SQLAlchemy already provide.

### 2. Mount the router

In `main.py`, near the other route registrations:

```python
from phase4_routes import router as analytics_router
app.include_router(analytics_router)
```

That's it. The router has a `/api` prefix so it doesn't conflict with existing routes.

### 3. Verify

Spin up locally and hit:

```bash
curl http://localhost:8000/api/bootcamp/diagnosis?difficulty=expert
curl http://localhost:8000/api/radar?difficulty=expert&mode=standard
curl http://localhost:8000/api/patterns/fluency?difficulty=expert
curl http://localhost:8000/api/heatmap?difficulty=expert&time_range_days=90
curl http://localhost:8000/api/replays?limit=10
```

Each should return a 200 with the expected JSON shape (or 404 / 425 if the player has no analyzed games yet).

## Response shape contracts

Frontend rendering depends on stable response shapes. The Pydantic models in `response_models.py` are the contract — any field rename or removal needs a coordinated frontend change.

To add a new field that's backward-compatible:
- Add to the Pydantic model with a default value
- Populate it in the corresponding query helper

To remove a field:
- Mark it `Optional` and stop populating it (one release)
- Remove the field declaration (next release)

## Architecture notes

### Why is the query layer separate from the routes?

Three reasons:
1. Reusability — site-wide rollup jobs, exports, and admin tools all need the same queries.
2. Testability — queries can be unit-tested without spinning up FastAPI.
3. Cleaner routes — handlers become 10-line orchestrators that don't hide complex SQL.

### Why benchmarks are inline rather than from a percentiles table

For the first version, axis benchmarks (top-10% values) live as constants in `queries.RADAR_AXIS_META` and `queries.PATTERN_CATALOG`. They come from the framework synthesis document — Dard's stated targets.

**Production should add a `site_percentiles` table** updated nightly:

```sql
CREATE TABLE site_percentiles (
    metric_key   VARCHAR(64),
    mode         VARCHAR(16),
    difficulty   VARCHAR(16),
    p10  FLOAT, p25  FLOAT, p50  FLOAT,
    p75  FLOAT, p90  FLOAT, p99  FLOAT,
    sample_size  INT,
    computed_at  DATETIME,
    PRIMARY KEY (metric_key, mode, difficulty)
);
```

Replace `_compute_radar_percentiles()` in `queries.py` with a lookup against this table. Same for the pattern fluency benchmarks. This decouples response time from data-set size.

### Auth model

`_player_id()` in `routes.py` returns either the logged-in user's email or a `guest_token` from the session. Both flow through to `GameAnalysis.player_id` because Phase 1 stores them on `game_replays` and the analyzer propagates them through.

Anonymous users get a session-bound `guest_token` (UUID, same pattern as scores). When they log in later, you can merge their guest games into their user record by updating `game_replays.user_email` where `guest_token` matches — Phase 1 doesn't do this yet but the schema supports it.

### Caching strategy

These routes are read-heavy and player-scoped — perfect for HTTP caching with short TTL:

```python
@router.get("/radar", response_model=RadarResponse)
@limiter.limit("30/minute")
def get_radar(..., response: Response = None):
    if response:
        response.headers["Cache-Control"] = "private, max-age=60"
    ...
```

60-second cache is fine for these surfaces — the player won't notice a one-minute delay and it cuts the analyzer's read load substantially.

### Performance budget

Per request, typical:
- Bootcamp diagnosis: ~30ms (one indexed scan over 50 rows)
- Radar: ~40ms
- Pattern Fluency: ~35ms
- Heatmap: ~80ms (joins with `game_replays` for cells)
- Replay (single game): ~20ms

The slowest endpoint is `/api/replays/{id}` if a backfill is running concurrently — the analyzer table writes will contend on the same row. Mitigate by setting a lower priority on backfill or by routing reads to a replica.

## Limitations to address in Phase 5

- **Drill catalog is hardcoded.** Moving to a `drills` table lets product iterate on copy and add new drills without redeploy.
- **Heatmap death cells are derived from `log_json`.** Adds I/O. Should add `death_x` and `death_y` columns to `game_analyses` and populate them in `persist_analysis`.
- **Trend chart on `/api/heatmap` returns an empty array.** Wire up the time-bucketed query — straightforward SQL but left unwritten for the first cut.
- **No `/api/dashboard` aggregate.** When the home page launches, we'll want a single endpoint that bundles "your current level + this week's drill + recent PB + alerts" so the home page renders with one HTTP call.
- **No `/api/coach/tip` endpoint.** A short auto-generated coaching tip ("you missed 3 openings yesterday — try this drill") is product surface waiting for an endpoint.

## What this enables

After this phase deploys:
- The five mockup screens have real backend data, ready for the frontend to wire up.
- The analytics pipeline runs end-to-end: client emits move log → server stores → analyzer derives → routes serve → UI renders → player learns.
- Site-wide rollups can read from the same `game_analyses` table without touching anything in this package.

The product is now an actual minesweeper coach.
