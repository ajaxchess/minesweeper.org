# Phase 5 Bootcamp — Frontend Integration

The first real user-facing surface for the analytics product. Renders the player's Bootcamp diagnosis at `/bootcamp`, populated live from `/api/bootcamp/diagnosis` and `/api/bootcamp/level/{n}`.

## Files in this drop

| File | Destination in repo | What it is |
|---|---|---|
| `templates/bootcamp.html` | `~/git/minesweeper.org/templates/bootcamp.html` | Jinja2 template; renders an empty skeleton and bootstraps `BOOTCAMP_CONFIG` |
| `static/js/bootcamp.js` | `~/git/minesweeper.org/static/js/bootcamp.js` | Vanilla JS — fetches diagnosis, renders cards, handles mode toggle |
| `static/css/bootcamp.css` | `~/git/minesweeper.org/static/css/bootcamp.css` | Page-specific stylesheet |
| `main_py_changes.py` | Apply to `main.py` | Route handler `/bootcamp` |
| `base_html_change.html` | Apply to `templates/base.html` | One-line addition of `{% block extra_head %}` |

## Pre-flight

The page only works if Phase 4 routes are live. Confirm with:

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Cookie: session=<your-session>" \
  http://localhost:8000/api/bootcamp/diagnosis?difficulty=expert
```

Expected: `200` if you have analyzed games, `404` if not. Anything else (5xx) means the API isn't ready — fix that before deploying the frontend.

## Deployment steps

### 1. Copy assets

```bash
cd ~/git/minesweeper.org
cp /staged/templates/bootcamp.html       templates/bootcamp.html
cp /staged/static/js/bootcamp.js         static/js/bootcamp.js
cp /staged/static/css/bootcamp.css       static/css/bootcamp.css
```

If you have a JS/CSS minification pipeline (terser, csso-cli per the project notes), make sure it picks up the two new static files.

### 2. Patch `base.html`

Open `templates/base.html`. Find this line (around line 21):

```html
<link rel="stylesheet" href="/static/css/style.css?v=60" />
```

Add **one line** immediately after it:

```html
{% block extra_head %}{% endblock %}
```

This block is overridden by `bootcamp.html` to load `bootcamp.css`. It also unblocks `archive_day.html`, which already references the same block but had no parent definition.

### 3. Patch `main.py`

Add the route handler from `main_py_changes.py`. Drop it next to the existing `quests_page` (around line 3490) so it's grouped with the other page routes.

```python
@app.get("/bootcamp", response_class=HTMLResponse)
async def bootcamp_page(request: Request):
    return templates.TemplateResponse(request, "bootcamp.html", {
        "mode": "bootcamp",
        "user": get_current_user(request),
        "lang": get_lang(request),
        "t": get_t(request),
    })
```

### 4. Restart and smoke-test

```bash
sudo systemctl restart minesweeper
curl -I http://localhost:8000/bootcamp
# → 200 OK with content-type: text/html
```

Open `http://localhost:8000/bootcamp` in a browser logged in to an account with analyzed games. You should see your diagnosis render after a brief loading state.

## How the page works

```
Browser hits /bootcamp
      ↓
FastAPI serves bootcamp.html (empty skeleton + BOOTCAMP_CONFIG)
      ↓
bootcamp.js DOMContentLoaded → fetch /api/bootcamp/diagnosis
      ↓
On success: render diagnosis panel, ladder, 7 level cards
On 404:     show empty state ("play a few games first")
On error:   show error state
      ↓
For the current level, lazily fetch /api/bootcamp/level/{N}
to populate habits, drills, and graduation criteria
      ↓
Mode-toggle clicks re-run the load with mode=no_guess
```

## Verification checklist

After deploy, verify each:

- [ ] **Logged-in user with analyzed games** — sees diagnosis, ladder shows complete/current/locked, current level expands with habits/drills.
- [ ] **Logged-in user with no analyzed games** — sees the empty state with "Play a game" CTA, not a broken page.
- [ ] **Guest user** — same as above (the API uses `guest_token` from the session).
- [ ] **Mode toggle** — clicking "No-Guess track" re-fetches and updates without a page reload.
- [ ] **Dark mode / other skins** — switching skin in the corner doesn't break the page. CSS has a dark-mode block.
- [ ] **Mobile** — diagnosis-stats grid collapses cleanly, ladder still readable.
- [ ] **404 on /api fails** — the page falls back to the error state instead of throwing in the console.

## Translation keys

The template uses `{{ t.bootcamp_* | default("English text") }}` so English works out of the box. To localize, add these keys to your translation files (one per supported language):

| Key | English default |
|---|---|
| `bootcamp_title` | Bootcamp |
| `bootcamp_subtitle` | The 7-level grand-master curriculum. |
| `bootcamp_dard_badge` | ★ Dard-curated |
| `bootcamp_mode_standard` | Standard |
| `bootcamp_mode_no_guess` | No-Guess track |
| `bootcamp_loading` | Loading your diagnosis… |
| `bootcamp_empty_title` | Play a few games to unlock your diagnosis |
| `bootcamp_empty_body` | (longer description — see template) |
| `bootcamp_empty_cta` | ▶ Play a game |
| `bootcamp_error` | Something went wrong loading your diagnosis. Please refresh. |
| `bootcamp_current_level` | Your current level |
| `bootcamp_profile` | Profile |
| `bootcamp_stat_best` | Best (Expert) |
| `bootcamp_stat_top` | Top: 2.5+ |
| `bootcamp_stat_ioe_target` | Target 0.85+ |
| `bootcamp_stat_correctness` | Correctness |
| `bootcamp_stat_correctness_target` | Target 0.90 |
| `bootcamp_stat_hierarchy` | Hierarchy |
| `bootcamp_stat_hierarchy_target` | Top: 88%+ |
| `bootcamp_stat_throughput` | ThRoughput |
| `bootcamp_stat_throughput_target` | Top 30% |
| `bootcamp_progress_to_next` | Progress to next level |
| `bootcamp_ladder_part1` | Speed-Efficiency (Part 1) |
| `bootcamp_ladder_part2` | Advanced Decision-Making (Part 2) |
| `bootcamp_habit_notice_title` | Heads up: expect a temporary slowdown |
| `bootcamp_habit_notice_body` | (longer body — see template) |
| `bootcamp_footer_attribution` | Curriculum based on Dard's Grand Master video series |
| `bootcamp_footer_view_videos` | view source videos |
| `bootcamp_levels_to_master` | more level(s) to grand-master |
| `bootcamp_progress_to_level` | Progress to Level |
| `bootcamp_tag_current` | In Progress |
| `bootcamp_tag_complete` | Complete |
| `bootcamp_tag_locked` | Locked |
| `bootcamp_tag_grandmaster` | Grand-Master |
| `bootcamp_habits_label` | Habits to install |
| `bootcamp_drills_label` | Recommended drills |
| `bootcamp_graduation_label` | 🎓 Graduation |
| `bootcamp_start_drill` | ▶ Start |
| `bootcamp_view_progress` | View progress |
| `bootcamp_review_level` | Review |
| `bootcamp_redrill` | Re-drill if needed |
| `bootcamp_preview` | Preview |
| `bootcamp_analyzed_from_last` | Diagnosis based on your last {n} expert games |
| `nav_bootcamp` | Bootcamp (for the navigation menu) |

## Rollback

To take the page offline without removing files:

```python
# In main.py, comment out:
# @app.get("/bootcamp", response_class=HTMLResponse)
# async def bootcamp_page(request: Request):
#     ...
```

Restart. The page now 404s. No DB or asset cleanup needed.

To take the page offline AND remove assets:

```bash
rm templates/bootcamp.html static/js/bootcamp.js static/css/bootcamp.css
# Revert main.py and base.html changes
git checkout main.py templates/base.html
```

## What this enables

Players now have an actual coaching surface. From their perspective:

1. They play games (existing flow, unchanged).
2. The analyzer runs in the background (Phase 2).
3. They visit `/bootcamp`, see their level diagnosis with concrete metrics.
4. They see what habits to install next, with drills to do.
5. They see Dard's video citations linked to the relevant moments.

The next surfaces to ship (Skill Radar, Mistake Heatmap, Pattern Fluency, Replay) follow the same pattern: empty Jinja2 skeleton + vanilla JS that fetches from the API + page-specific CSS. The Bootcamp page is the template for all of them.

## Known follow-ups for Phase 6

- **Add `/bootcamp` to the nav menu in base.html.** Currently the page is only reachable by direct URL.
- **Wire drill buttons.** The "Start drill" buttons currently do nothing. Hook them to whatever drill execution surface gets built next.
- **Localize.** Add the translation keys above to each supported language file.
- **Onboarding hook.** When a logged-in user first hits 50 analyzed games, surface a banner pointing to `/bootcamp` from the main game page.
