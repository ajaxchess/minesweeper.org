# Bootcamp: Mistake Heatmap Page

**Status:** ready
**Feature ID:** F-BC-HEATMAP
**Author:** Richard Cross
**Date:** 2026-09-21

---

## Problem / Motivation

`GET /api/heatmap` has been live since Phase 4 with no frontend. It aggregates death
cells, death causes, board regions and a trend over a configurable time window — the
data needed to answer "where on the board do I actually die, and why".

This is the most viscerally useful of the unbuilt surfaces. Bootcamp levels and
radar axes are abstractions; a board with your own deaths burned into it is not. A
player who discovers that two thirds of their losses are on the bottom edge, or that
their deaths cluster in the opening rather than the endgame, learns something they
cannot get from any number.

It is also the surface most likely to be screenshotted and shared, which makes it
worth building well.

---

## Success Criteria

- [ ] `/bootcamp/heatmap` renders a board-shaped heatmap of the player's death cells
- [ ] Death causes are broken out (the `death_cause` and `death_region` dimensions
      already on `GameAnalysis`)
- [ ] Time-window selector, defaulting to the API's 90-day default
- [ ] Difficulty selector — a beginner heatmap and an expert heatmap are different
      board shapes and must not be blended
- [ ] Standard / no-guess mode toggle
- [ ] Clicking a hot cell lists the games that died there, linking to each replay
- [ ] Empty state for players with no analyzed losses
- [ ] Fully localized

---

## Scope

**In this feature:**
- `templates/bootcamp_heatmap.html`, page CSS, page JS
- Page route and nav/bootcamp links
- Translation keys

**Out of scope:**
- Changes to `/api/heatmap`
- Heatmaps of anything other than deaths (a wasted-click heatmap is appealing and
  would need a new endpoint)
- Comparing against other players

---

## Key Design Decisions

**Board geometry is the hard part.** An Expert heatmap is 30×16 = 480 cells and must
stay legible on a phone. Render as a grid of divs or a canvas sized to the
difficulty, with a documented minimum cell size and horizontal scroll on narrow
screens rather than illegible shrinking.

**Colour scale must survive both themes.** The site ships multiple skins including
light and dark. Use a sequential scale with a legend and explicit empty-cell
styling; do not rely on a single hue that vanishes on one of the backgrounds.

**Difficulty cannot be blended.** `game_analyses.difficulty` exists and is indexed
precisely so beginner and expert games are not averaged together. The heatmap must
filter on it — a 9×9 death overlaid on a 30×16 grid is meaningless.

**Design source:** `minesweeperbootcamp/docs/mistake_heatmap_mockup.html`.

**Drill-down is what makes it actionable.** A hot cell that lists "you died here in
these 6 games" with links into replay analysis (F-BC-REPLAY) closes the loop from
pattern to evidence. Build the list even if replay analysis lands later; link to
`/game/{id}` in the meantime.

---

## Effort Sizing

**~1 to 1.5 weeks.** Slightly more than the radar because of the board rendering,
responsive behaviour and the drill-down list.

Dependencies: none hard. Pairs well with F-BC-REPLAY.

---

## Implementation Notes

_To be filled in after shipping._
