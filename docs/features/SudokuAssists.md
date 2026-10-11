# Sudoku — Notes, Auto Candidates, Auto Check, Conflicts

**Status:** done
**Feature ID:** F-SUDOKU-ASSISTS (extends F53 Sudoku)
**Author:** Gisela Velazco
**Date:** 2026-10-11

---

## Problem / Motivation

Our Sudoku only let players place a final digit per cell: no way to pencil in
candidates, and a single "Mistakes" toggle (on by default) that silently
compared entries with the solution without affecting the leaderboard. Popular
newspaper Sudokus (reference: La Nación, lanacion.com.ar/juegos/sudoku) offer a
Normal / candidates entry mode plus three independent checkboxes: automatic
candidates, auto check and conflicts.

---

## Success Criteria

- [x] Players can switch between **Normal** and **Notes** entry with tabs (or `N`).
- [x] Notes appear as a 3×3 mini-grid in the cell, digit n always in slot n.
- [x] **Auto candidates** shows, in every empty cell, the digits not yet used in
      its row, column and box, updating as the board changes.
- [x] **Auto check** marks entries that differ from the solution.
- [x] **Conflicts** marks digits repeated in a row, column or box (no solution needed).
- [x] The leaderboard shows which assists a time was set with.

---

## Scope

**In this feature:**
- Notes mode, the three options, assists bitmask stored with each score and
  shown on the leaderboard.

**Out of scope (future):**
- Undo.
- Server-side verification of Sudoku times, hints and assists. Like Numbers
  Match before F-NM-VERIFY, the API trusts `time_ms`, `hints_used` and now
  `assists` from the client, and does not check `board_hash` against
  `board_givens`. Candidate follow-up feature.

---

## Key Design Decisions

- **Defaults** (decision 2026-10-11): all three options off for a new player;
  each choice is remembered in `localStorage` (`su_opts`).
- **Leaderboard** (decision 2026-10-11): assists are *marked*, not separated.
  `sudoku_scores.assists` is a bitmask — `1` auto candidates, `2` auto check —
  set if the option was on at any moment during the game (including when the
  game starts with a remembered option on). Shown as ✎ / ✓ next to the time.
  Conflicts and manual notes never count: they don't reveal the solution.
- **Notes with Auto candidates on**: displayed candidates = computed candidates
  minus the ones the player crossed out in Notes mode. Only digits the board
  still allows can be crossed out or restored. Turning Auto candidates off shows
  the player's own manual notes again.
- **Placing a digit** clears that cell's notes and removes the digit from the
  manual notes of its row, column and box. Erase on an empty cell clears its notes.
- Tap-to-cycle on the selected cell stays in Normal mode only.
- Spanish labels follow La Nación's wording: Normal / Posibles, Autocontrol,
  Posibles automáticos, Conflictos. Other languages fall back to English.

---

## Implementation Notes

- `static/src/js/sudoku.js` (`?v=2`): `noteMode`, `notes` / `eliminated`
  (Set per cell), `opts` + `saveOpts()`, `recordAssists()`, `candidatesFor()`,
  `findConflicts()`, `toggleNote()`, `setNoteMode()`; `assists` sent with the score.
- `templates/sudoku_play.html`: tabs and checkboxes; `templates/sudoku_scores.html`:
  ✎ / ✓ icons and legend; `static/src/css/style.css` (`?v=62`): `.su-notes`,
  `.su-cell--conflict`, `.su-mode-tab`, `.su-option`, `.su-assist`.
- `sudoku_routes.py` / `database_template.py`: `assists` field (0–3), column and
  idempotent migration; returned by `GET /api/sudoku-scores`.
- `translations.py`: `sudoku_mode_*` and `sudoku_opt_*` keys (en, es).
- Tests: `tests/test_sudoku.py` (API + page), `tests/js/sudoku_behaviour.js`
  (plays the real script against a stub DOM; run with `node` — CI is Python-only).
