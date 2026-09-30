# Bootcamp: Skill Radar Page

**Status:** done
**Feature ID:** F-BC-RADAR
**Author:** Richard Cross
**Date:** 2026-09-21

---

## Problem / Motivation

`GET /api/radar` has been live since Phase 4 and nothing calls it. It returns a
multi-axis skill profile with per-axis values, formatted labels, generated insights
and a recommendation — a complete picture of where a player is strong and weak — and
today the only way to see any of it is with curl.

The bootcamp page answers "what level am I and what do I drill next". The radar
answers a different and complementary question: "what shape is my game". A player
who is fast but wasteful and a player who is efficient but slow can sit at the same
bootcamp level with completely different problems, and the ladder does not show that
difference. The radar does, in one glance.

This is the cheapest remaining product surface in the bootcamp: the API, the
insight generation and the recommendation text all already exist in
`phase4_routes/routes.py` (`get_radar`, `_format_axis_label`, `_generate_radar_insights`,
`_generate_radar_recommendation`). This is a page, not a feature.

---

## Success Criteria

- [ ] `/bootcamp/radar` renders the authenticated player's skill radar from `/api/radar`
- [ ] Each axis shows its value and the existing formatted label, not a bare number
- [ ] The generated insights and recommendation are displayed, not just the chart
- [ ] Standard / no-guess mode toggle and difficulty selector match `/bootcamp` behaviour
- [ ] Empty state for players with too few analyzed games, matching `/bootcamp`'s
- [ ] Reachable from `/bootcamp` and from the nav
- [ ] Fully localized — no English-only fallbacks

---

## Scope

**In this feature:**
- `templates/bootcamp_radar.html`, `static/css/bootcamp_radar.css`, `static/js/bootcamp_radar.js`
- Page route (in the bootcamp router if F-BC-CONSOLIDATE has landed; otherwise `main.py`)
- Translation keys
- Link from the bootcamp page and nav

**Out of scope:**
- Any change to `/api/radar` itself
- Comparing your radar against another player's, or against a cohort average — a
  strong v2 but it needs a peer-percentile endpoint that does not exist
- Radar history / change over time

---

## Key Design Decisions

**Follow the established surface pattern.** `/bootcamp` is skeleton Jinja template +
page-scoped CSS + vanilla JS calling the API with `credentials: same-origin` and
`X-Requested-With`, with `BOOTCAMP_CONFIG` bootstrapping copy and API base. Copy it.
No framework, no build step.

**Chart.js is already loaded** for the View Progress modal on `/bootcamp` and
supports a radar chart type — reuse it rather than adding a dependency.

**Design source:** `minesweeperbootcamp/docs/skill_radar_mockup.html`, also present
in the analysis project folder. It is a complete visual treatment; the work is
wiring it to live data.

**Insights are the point, not the polygon.** A radar chart on its own is decorative.
The value is `_generate_radar_insights()` and `_generate_radar_recommendation()`,
which already produce prose. Give them at least equal visual weight to the chart,
and make the recommendation a link into the relevant drill.

---

## Effort Sizing

**~1 week.** Template, CSS, JS, route, translations, empty/error states. There is no
backend work and no data modelling.

Dependencies: none. This is the best next surface to build because it is the one
where the most existing work is sitting unused.

---

## Implementation Notes

Route, template, and JS all existed. The only work was fixing five field name
mismatches between the API response and the JS, adding auth headers to the fetch,
adding one missing translation key, and wiring the nav drawer link.

**Field name fixes in `static/js/bootcamp_radar.js`:**
- `a.axis` → `a.axis_key` (in `buildChart` and `renderAxes`)
- `AXIS_LABELS[a.axis]` → `a.display_name` (API provides the label directly)
- `DARD2_AXES.has(a.axis)` → `a.is_new_dard` (API returns boolean)
- `i.type` → `i.kind` in `renderInsights`
- `item.axis` → `item.axis_display` in `renderInsights`
- `data.recommendation_cta_text` → `data.recommendation_cta_label` in `renderRec`
- Added `credentials: 'same-origin'` and `X-Requested-With` header to `fetchRadar`

**translations.py:** added `radar_games_analyzed` key.

**templates/base.html:** added Skill Radar sub-link under Bootcamp in the nav drawer.

**main.py:** changed `mode` from `"bootcamp"` to `"bootcamp-radar"` so the drawer
sub-link activates on this page.
