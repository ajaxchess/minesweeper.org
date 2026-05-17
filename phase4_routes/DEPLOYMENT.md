# Phase 4 Deployment Runbook

Step-by-step deployment of the analytics API to `~/git/minesweeper.org/`. Designed for a single deploy window — should take ~30 minutes including verification.

## Pre-flight checklist

Before touching anything, confirm:

```sql
-- 1. The analyzer is producing rows
SELECT COUNT(*) AS analyzed_games,
       MIN(created_at) AS first,
       MAX(created_at) AS most_recent
FROM game_analyses;

-- 2. Analyses are recent (within the last few hours)
SELECT COUNT(*) FROM game_analyses
WHERE created_at >= NOW() - INTERVAL 1 HOUR;

-- 3. The Dard signature metrics are populated (not all NULL)
SELECT
  COUNT(hierarchy_compliance_pct) AS has_hierarchy,
  COUNT(openings_guaranteed_taken) AS has_openings,
  COUNT(*) AS total
FROM game_analyses;
```

If `has_hierarchy` is much smaller than `total`, the analyzer is running but the Dard passes aren't writing properly — investigate before proceeding (the routes will return zeros).

## Deployment steps

### Step 1 — Copy the package

```bash
cd ~/git/minesweeper.org
cp -r /path/to/phase4_routes .
git add phase4_routes/
git status     # confirm only phase4_routes/ files are staged
```

No new pip dependencies. Uses FastAPI, Pydantic, and SQLAlchemy — all already in `requirements.txt`.

### Step 2 — Mount the router in `main.py`

This is the only code change to existing files. Add **one block** to `main.py`. Placement matters because of import ordering — see the warning below.

Find the section of `main.py` where other routers/middleware are registered (after `limiter = Limiter(...)` and after `app = FastAPI(...)`, but before any large block of route definitions). Add:

```python
# F96 — Analytics API (Phase 4)
from phase4_routes import router as analytics_router
app.include_router(analytics_router)
```

That's it. Seven endpoints under `/api/` come online.

**⚠ Import-ordering caveat.** `phase4_routes.routes` imports `limiter` from `main`. That import resolves at module load time. So:

- `limiter = Limiter(...)` must be defined **before** the `from phase4_routes import router` line.
- Don't put the import at the top of `main.py` above the limiter setup. Stick it near the other `include_router` calls or just below the existing rate-limiter wiring.

If you see `ImportError: cannot import name 'limiter' from partially initialized module 'main'`, that's this ordering issue.

### Step 3 — Restart and verify

```bash
sudo systemctl restart minesweeper
sudo journalctl -u minesweeper -n 50 --no-pager
```

Watch the boot log for errors. Successful boot looks like normal startup; the new router doesn't print anything on its own.

### Step 4 — Smoke-test the endpoints

Run the smoke-test script (see `smoke_test.py` in this package) from the production host, *as an authenticated user* (or via a guest session with a real `guest_token`):

```bash
cd ~/git/minesweeper.org
python -m phase4_routes.smoke_test \
  --base-url http://localhost:8000 \
  --cookie "session=<your-session-cookie>"
```

Expected output:

```
[✓] GET /api/bootcamp/diagnosis        → 200
[✓] GET /api/bootcamp/level/2          → 200
[✓] GET /api/radar                     → 200
[✓] GET /api/patterns/fluency          → 200
[✓] GET /api/replays                   → 200
[✓] GET /api/replays/<id>              → 200
[✓] GET /api/heatmap                   → 200
All 7 endpoints responded successfully.
```

Possible non-error responses to expect:
- **404 "No games analyzed yet"** on a fresh account — graceful, expected.
- **425 "Analysis pending"** on a replay whose analyzer task hasn't finished yet — graceful, expected.

### Step 5 — Production traffic check

After 10–15 minutes of normal traffic, check that:

```bash
# OpenTelemetry traces — look for the new spans
curl -s http://localhost:8000/api/bootcamp/diagnosis -I
```

In your X-Ray dashboard, filter for `GET /api/bootcamp/diagnosis` and confirm:
- Latency p50 < 100ms
- p99 < 500ms
- Error rate near zero (4xx is fine; 5xx is the problem)

If p99 is significantly above 500ms, the most likely culprit is the analyzer's `game_analyses` table missing the indexes from Phase 2. Run:

```sql
SHOW INDEX FROM game_analyses;
```

You should see `ix_game_analyses_player_created`, `ix_game_analyses_hierarchy`, and `ix_game_analyses_no_guess_created`.

## Feature flag (optional but recommended)

If you want a kill switch without a redeploy, wrap the `include_router` call:

```python
import os
if os.environ.get("ENABLE_ANALYTICS_API", "true").lower() == "true":
    from phase4_routes import router as analytics_router
    app.include_router(analytics_router)
```

Then setting `ENABLE_ANALYTICS_API=false` in the systemd unit and restarting takes the endpoints offline cleanly. Not strictly needed for a low-risk deploy, but useful if you want zero-downtime rollback.

## Rollback plan

If anything goes wrong, rollback is one line and one restart:

```bash
# Edit main.py — comment out the include_router block:
# from phase4_routes import router as analytics_router
# app.include_router(analytics_router)

sudo systemctl restart minesweeper
```

No database changes to revert. The `game_analyses` table is unchanged by this deploy.

## What this deploy does NOT include

- No frontend pages. The endpoints return JSON; nothing renders to users yet.
- No new database tables or columns.
- No changes to existing endpoints.
- No client-side changes (`static/js/minesweeper.js` is untouched).

Players experience no change. This deploy is purely infrastructure for the frontend work that follows.

## Things to watch in the first 24 hours

1. **Error rate on `/api/*` new endpoints.** Should be near zero. If 5xx errors appear, check logs — most likely cause is an analyzer record with an unexpected schema (e.g., malformed JSON in `wasted_clicks_json`).
2. **Rate-limiter hits.** All routes are at 30/min per IP. If you see legit traffic hitting the limit, raise it.
3. **No-guess anomaly detection.** Query:
   ```sql
   SELECT COUNT(*) FROM game_analyses
   WHERE no_guess = TRUE AND death_cause = 'forcedGuess';
   ```
   A non-zero number means the solver is missing deductions. Doesn't block the deploy — but it's a Phase 5 follow-up worth filing.

## What unblocks after this deploy

- **Frontend work.** Each of the five mockup pages (Bootcamp, Radar, Heatmap, Pattern Fluency, Replay) can now be wired to a real API. Start with Bootcamp — it's the central product surface.
- **Analytics partners / collaborators.** If you share a session cookie with Dard or another collaborator, they can hit the endpoints directly and see real data — useful for the partnership conversation.
- **The `/api/dashboard` aggregate route.** Once the home page is designed, bundle the most-used queries into a single response.
