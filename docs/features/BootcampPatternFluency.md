# Bootcamp: Pattern Fluency Page

**Status:** done
**Feature ID:** F-BC-FLUENCY
**Author:** Richard Cross
**Date:** 2026-09-21

---

## Problem / Motivation

`GET /api/patterns/fluency` has been live since Phase 4 with no frontend. It reports
per-pattern recognition performance — how long a player takes to act on a 1-1, a
1-2-1, a 1-2-2-1, a reduction — derived from the `patterns_json` and
`avg_pattern_reaction_ms` outputs of the analyzer.

This is the diagnostic closest to how players actually think about improving. Nobody
sets out to "raise their IOE"; they set out to stop freezing on 1-2-1s. Pattern
fluency names the specific shapes costing a player time, and it is the surface with
the most direct line into a drill: slowest pattern in, drill for that pattern out.

It is also the only bootcamp surface that measures *speed of recognition* rather
than correctness of outcome, which makes it the right place to send a player who is
accurate but slow — a group the ladder currently has little to say to.

---

## Success Criteria

- [ ] `/bootcamp/patterns` lists the player's patterns with reaction time and a
      fluency indicator, ordered worst-first
- [ ] The slowest pattern is called out explicitly as the recommended focus
- [ ] Each pattern links to the drill that trains it
- [ ] Each pattern shows what it looks like — a small rendered board fragment, not
      just the pattern's name
- [ ] Difficulty and mode selectors consistent with the other bootcamp surfaces
- [ ] Empty state for players with too few analyzed games
- [ ] Fully localized

---

## Scope

**In this feature:**
- `templates/bootcamp_patterns.html`, page CSS, page JS
- Small reusable board-fragment renderer for pattern illustrations
- Page route, nav and bootcamp links, translation keys

**Out of scope:**
- Changes to `/api/patterns/fluency`
- New pattern classes in the analyzer — this presents what the analyzer already
  detects
- Peer comparison ("you are slower than 70% of players at 1-2-1") — wanted, but
  needs a percentile endpoint that does not exist

---

## Key Design Decisions

**Show the pattern, don't just name it.** "1-2-2-1: 840ms" means nothing to an
improving player who has not learned that name yet. Each row needs a small rendered
board fragment showing the shape. That renderer is reusable by the drill pages and
by F-BC-HEATMAP, so build it as a shared component rather than inline.

**Reaction time needs a reference point.** A raw millisecond figure is not
interpretable on its own. Show it against the player's own median across all
patterns, so "this one is slow *for you*" is legible without any cross-player data.

**Design source:** `minesweeperbootcamp/docs/pattern_fluency_mockup.html`.

**The drill link is the payoff.** The existing annotation engine already emits
`drill_id` per event class; make sure the pattern rows resolve to real drill types
in the `l1_…`–`l7_…` namespace rather than a second disconnected set of IDs. The
repo has been through that mismatch once already — see the drill-button fix in the
July roadmap — and should not reintroduce it.

---

## Effort Sizing

**~1 week**, plus a few days if the board-fragment renderer is built properly as a
shared component (worth it — two other surfaces want it).

Dependencies: none.

---

## Implementation Notes

New page wired to the existing `/api/patterns/fluency` endpoint with no backend changes.

**Files created:**
- `templates/bootcamp_patterns.html` — Jinja template using `.bc-page` variables; purple/indigo summary card, pattern list with inline CSS for tier-coloured left borders, Windows-95-style mini-board cells, reaction-time bar with benchmark tick, weekly drill-plan prescription card.
- `static/js/bootcamp_patterns.js` — vanilla JS following the same fetch/render/state pattern as radar and heatmap. Key pieces: `BOARDS` lookup table mapping each `pattern_key` to a mini-board cell grid (10 patterns defined), `buildMiniBoard()` renderer, `renderSummary/PatternList/WeeklyPlan()`, mode toggle, and drill-start delegation.

**Files modified:**
- `translations.py` — 16 new `fluency_*` keys plus `bootcamp_patterns_link`.
- `main.py` — new `GET /bootcamp/patterns` route, `mode="bootcamp-patterns"`.
- `templates/base.html` — "Pattern Fluency" sub-link under Bootcamp in nav drawer.
- `templates/bootcamp.html` — "Pattern Fluency →" link in page footer.

**Mini-board boards defined:** `pattern_121`, `pattern_1221`, `pattern_232`, `pattern_11_corner`, `pattern_21_edge`, `opening_l_shape_edge`, `opening_2_satisfied`, `opening_potential_2cell`, `fishing_for_1`, `fishing_for_2`.

**Drill start** resolves layer from drill_id prefix (`opening_`/`fish_` → L5, `pat_` → L2) and POSTs to `/api/drills/start`, then navigates to `/drill/{id}`.
