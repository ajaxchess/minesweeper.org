# Numbers Match — Cleared Numbers and Rules Popup

**Status:** done
**Feature ID:** F-NM-CLEARED (part of F-NM)
**Author:** Gisela Velazco
**Date:** 2026-10-30

---

## Problem / Motivation

Players had no feedback on progress beyond the score, and the pairing rules were
only described in text below the board. Reference: the Numbers Match mobile app.

---

## Success Criteria

- [x] A "Numbers Cleared" row above the board shows 1–9, with a check for each
      number no longer on the board.
- [x] A short toast announces when the last of a number is removed.
- [x] An ⓘ button opens a popup drawing the four ways a pair can connect:
      diagonal, horizontal, vertical, line to line.

---

## Scope

**In this feature:** web Numbers Match (`/numbers-match`, `/mobile/nmmobile`).

**Out of scope (future):** the nmmobile Expo app; keeping removed numbers visible
as faint ghosts, as the reference app does.

---

## Key Design Decisions

- The row is rebuilt from the board on every HUD update, so Undo brings a number
  back. Add Lines cannot revive a cleared number: it only copies what remains.
- The toast lasts 2.5 s. It shares its spot with the win toast, so each one
  hides the other.
- The elements are created by the script, so both templates stay identical.
  Text comes from `window.NM_T` (translations.py, `nm_cleared_*`, `nm_rule*`;
  en and es, other languages fall back to English).

---

## Implementation Notes

`static/src/js/numbers_match.js` (`?v=24`): `renderCleared()`,
`showClearedToast()`, `setupRulesPopup()`, `ruleDiagram()`. Styles in
`static/src/css/style.css` (`?v=64`). Tests: `tests/js/numbers_match_game_end.js`.
Also verified end to end in a real browser (Edge via Playwright) on a local
server: a real game verified by the server, dark and light themes, phone width.
