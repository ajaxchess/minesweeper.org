# View Progress modal — deployment addendum

Adds the "View progress" button behavior to the Bootcamp page (Phase 5). Click the button on any current-level card → modal opens with a 30-day mastery trend, recent contributing games, and an ETA to graduation.

This is purely additive to the existing Bootcamp deploy — no schema changes, no new tables, no client API contract changes.

## What changed

### Backend (Phase 4 routes package)

| File | Change |
|---|---|
| `phase4_routes/response_models.py` | Added `ProgressDataPoint` and `LevelProgressResponse` |
| `phase4_routes/queries.py` | Added `get_level_progress()` and `_extract_level_mastery()` helpers |
| `phase4_routes/routes.py` | Added `GET /api/bootcamp/level/{n}/progress` route + matching import |

### Frontend (Phase 5 bootcamp package)

| File | Change |
|---|---|
| `templates/bootcamp.html` | Added modal markup at the end of `bc-page`, added Chart.js CDN to the scripts block |
| `static/css/bootcamp.css` | Added `.bc-modal*`, `.bc-progress-*` styles plus a small mobile-responsive block |
| `static/js/bootcamp.js` | Added `bindProgressModal()`, `openProgressModal()`, `renderProgress()`, plus `data-action="view-progress"` attribute on the button |

## Deployment steps

### 1. Update the Phase 4 routes package

```bash
cd /data2/ubuntu/git/minesweeper.org
cp /staged/phase4_routes/response_models.py phase4_routes/response_models.py
cp /staged/phase4_routes/queries.py         phase4_routes/queries.py
cp /staged/phase4_routes/routes.py          phase4_routes/routes.py
```

### 2. Update the Phase 5 bootcamp assets

```bash
cp /staged/phase5_bootcamp/templates/bootcamp.html       templates/bootcamp.html
cp /staged/phase5_bootcamp/static/css/bootcamp.css       static/css/bootcamp.css
cp /staged/phase5_bootcamp/static/js/bootcamp.js         static/js/bootcamp.js
```

### 3. Bump the cache-busters on the changed assets

If your `bootcamp.html` references the CSS and JS with `?v=N`, bump N so browsers pick up the new files:

```html
<link rel="stylesheet" href="/static/css/bootcamp.css?v=2" />
<script src="/static/js/bootcamp.js?v=2"></script>
```

### 4. Restart

```bash
sudo systemctl restart staging-minesweeper
```

### 5. Smoke-test

The new endpoint is wired into the existing `phase4_routes.smoke_test`, but it isn't in the check list yet. Quick manual check:

```bash
curl -s "http://localhost:8002/api/bootcamp/level/4/progress?difficulty=expert&mode=standard" \
  -H "Cookie: session=<your-session>" | python3 -m json.tool | head -40
```

Expected: 200 with a `LevelProgressResponse` JSON. If the player has fewer than 5 games at this level, you'll get a sparse response with `data_points: []` and `trend: "flat"` — that's the empty-state path.

Then in a browser, visit `/bootcamp`, click "View progress" on the current level card. Modal should open, show a chart, list recent games. Close with the ✕, click outside the modal, or press Escape.

## How the data flows

1. Every analyzed game writes a row to `game_analyses` with `level_mastery_json` — a dict `{1: 0.92, 2: 0.85, ...}` — one entry per Bootcamp level.
2. The progress endpoint reads the player's recent rows, extracts the requested level's mastery from each, and computes:
   - **Current mastery** = rolling average over the last 10 games for that level
   - **Trend** = compare last-7-days avg vs prior-7-days avg; ±0.02 threshold for improving/declining/flat
   - **ETA** = linear extrapolation of the recent 30-game slope, projected to hit 0.85; bounded 1–365 days; `None` if flat / declining / already mastered
3. The modal renders these as a stat row, a Chart.js line chart vs. the 85% target line, and a scrollable list of recent contributing games.

## Edge cases handled

- **No games at all** — modal shows "Not enough analyzed games yet" empty state.
- **Fewer than 5 games** — ETA stays `None`. Trend always `flat`.
- **Player already mastered the level** — ETA shows "Mastered". Chart line sits above the 85% line.
- **`level_mastery_json` is malformed** — that single record is skipped; remaining games still chart.
- **No-guess vs standard** — the mode filter from the page's mode toggle is passed through.
- **Modal close** — click backdrop, click ✕, or press Escape. Body overflow is restored.

## What it doesn't do (future work)

- **Click a game in the list to open its replay.** The list items have `data-replay-id` set already; wiring it to `/variants/replay/?id=...` is a one-line addition.
- **Per-habit progress breakdown.** The current view shows total level mastery, not which sub-habits are improving. A nice follow-up.
- **Compare against population.** "Your improvement velocity is in the 70th percentile of players at this level" — needs the `site_percentiles` rollup table mentioned in `README_Routes.md`.
- **Track drill contributions separately.** Once drills exist, the chart could overlay live-game mastery vs. drill mastery as two lines.

## Rollback

The button is inert when JS doesn't load — clicking it does nothing. To fully roll back without removing files:

```python
# In bootcamp.js, comment out the bindProgressModal() call in DOMContentLoaded
```

…and the modal stays hidden forever. No DB cleanup needed; no impact on the existing diagnosis flow.

## What this enables for the "Start today's drill" button

The modal pattern + the data-* attribute event delegation in `bootcamp.js` are the foundation. When we build the drill runner next, "Start today's drill" reuses the same delegated-click pattern. Modal could even become a drill-result modal post-completion ("you took 1.2s on this pattern, top players take 0.4s — try again?"). Pattern is consistent across the page.
