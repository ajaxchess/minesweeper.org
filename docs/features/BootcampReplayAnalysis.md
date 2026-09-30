# Bootcamp: Replay Analysis Page

**Status:** ready
**Feature ID:** F-BC-REPLAY
**Author:** Richard Cross
**Date:** 2026-09-21

---

## Problem / Motivation

`GET /api/replays` and `GET /api/replays/{game_replay_id}` have been live since
Phase 4 with no frontend. The single-replay endpoint is the most developed thing in
the bootcamp API and the least visible: `_build_move_log_with_annotations()` walks a
player's move log against their `GameAnalysis` and returns every move annotated with
badges, human-readable explanations, severity, tutorial citations and drill links,
across six event classes — wasted clicks, missed shortcuts, missed openings, missed
fishes, low-value flags and hierarchy deviations.

That is a move-by-move coaching commentary on a real game, sitting behind an API
nobody can reach from a browser. Every other bootcamp surface tells a player about
their aggregate tendencies. This one shows them the actual moment they went wrong,
in their own game, with an explanation attached. It is the most convincing thing the
bootcamp can show anyone.

It is also the internal counterpart to F-EMBED's coached mode: the same annotation
stream, rendered for the player themselves rather than for a public embed. Building
this first de-risks that feature and settles the interaction design in a place where
the social stakes are zero.

---

## Success Criteria

- [ ] `/bootcamp/replay/{game_replay_id}` plays back a game with annotations
      appearing on the board at the move they belong to
- [ ] A commentary rail lists every annotation with its number, badge and
      explanation; clicking an entry scrubs playback to that move
- [ ] The scrub bar carries markers at annotated moves
- [ ] A summary strip above the board — wasted clicks, missed chords, missed
      openings, avoidable guesses — before playback starts
- [ ] Each annotation links to its drill and, where present, its tutorial citation
- [ ] `/bootcamp/replays` lists the player's analyzed games with enough per-row
      signal to choose one worth studying
- [ ] Replays are only viewable by their owner, or per the game's public visibility
- [ ] Empty state when a game has no `game_analyses` row, with the option to queue it

---

## Scope

**In this feature:**
- `templates/bootcamp_replay.html` and `bootcamp_replays.html`, page CSS, page JS
- Playback engine reading `log_json` with annotation overlay and synced rail
- Page routes, links from `/bootcamp`, the heatmap drill-down and the profile history
- Translation keys

**Out of scope:**
- Changes to the annotation engine or the analyzer
- Public sharing and embedding of an annotated replay — that is F-EMBED, which
  should reuse this page's playback and overlay code
- Annotating games with no analysis (queue it; don't compute inline)

---

## Key Design Decisions

**Build the playback and overlay as reusable modules.** F-EMBED's coached mode needs
exactly this behaviour inside a stripped, third-party-safe template. If this page's
board renderer, playback clock and annotation overlay are written as standalone
modules rather than page-scoped code, F-EMBED Phase 6 becomes assembly. If they are
not, it becomes a rewrite. This is the single most consequential decision in the
feature and it costs nothing to get right at the start.

**Design source:** `minesweeperbootcamp/docs/replay_analysis_mockup.html`, also in
the analysis project folder.

**Annotation density needs managing.** A sloppy Expert game can produce dozens of
annotations. The rail needs filtering by badge type, and the board needs a rule for
overlapping markers on the same cell. Default to showing all; let the player narrow
to one class ("show me only the missed chords").

**Tone matters even in private.** The commentary strings already exist and are
diagnostic rather than judgemental — "zero new cells revealed", not "you wasted a
click". Keep that register in the page copy around them. A player who feels scolded
by their own replay does not open a second one.

---

## Effort Sizing

**~1.5 to 2 weeks.** The playback engine and synced overlay are real work; the
analysis is free. Build the modules cleanly and F-EMBED Phase 6 drops from 1.5 weeks
to roughly half that.

Dependencies: none. Strongly recommended before F-EMBED Phase 6.

---

## Implementation Notes

_To be filled in after shipping._
