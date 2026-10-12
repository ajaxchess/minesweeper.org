# Game End: Result Toast and Automatic Next Game

**Status:** done
**Feature ID:** F-GAME-END (Numbers Match and Sudoku)
**Author:** Gisela Velazco
**Date:** 2026-10-12

---

## Problem / Motivation

- Numbers Match showed its win overlay for only 350 ms before loading the next
  game, so players never saw their result.
- Sudoku only stopped the timer: the result panel rendered below the number pad,
  off screen, and guests had to type a name and press Submit.
- Sudoku's leaderboard was only on a separate Scores page; Numbers Match shows
  it under the board.

---

## Success Criteria

- [x] When a game ends, a toast shows the result (Numbers Match: score and time;
      Sudoku: time, hints and assists) for 5 seconds, with the save status.
- [x] The score is saved automatically and the next game starts immediately.
- [x] Sudoku shows today's leaderboard for the current level under the board.

---

## Scope

**In this feature:** web Numbers Match (`/numbers-match`, `/mobile/nmmobile`)
and Sudoku (`/other/sudoku/*`).

**Out of scope:** the nmmobile Expo app keeps its win modal.

---

## Key Design Decisions

- **Toast duration** (decision 2026-10-12): 5 s, then it hides on its own.
  Shared CSS `.game-toast` in `style.css`; each game creates its own element
  (`#nm-toast`, `#su-toast`).
- **Next game** (decision 2026-10-12): after the Daily comes Easy; after any
  other level, another board of the same level.
  - **Sudoku:** every Easy/Medium/Hard/Expert game is a new random, ranked board.
    After the Daily the page switches to Easy in place (URL, subnav and
    leaderboard follow).
  - **Numbers Match:** each day's Daily/Easy/Medium/Hard/Expert is one fixed,
    server-verified board (F-NM-VERIFY). Daily → today's ranked Easy. Once a
    ranked board is finished (tracked in `localStorage` `nm_played`), the next
    board of that size is a random **practice** board, labelled
    "· Practice", not ranked; the leaderboard of the last ranked puzzle stays
    on screen.
- **Names:** signed-in players use their profile name. Sudoku guests get an
  automatic `Guest NNNN` (as in Numbers Match) and can set their own name in the
  field above the Sudoku leaderboard (`su_name`).
- The Numbers Match highlight of reachable cells stays in the Paths mode as is.

---

## Implementation Notes

- `static/src/js/numbers_match.js` (`?v=22`): `showGameToast()`,
  `setToastStatus()`, `startNextGame()`, `initPracticeGame()`, `markPlayed()`;
  `loadLeaderboard(puzzleId)`; replaced `rememberVariant` / `startLastVariant`.
- `static/src/js/sudoku.js` (`?v=4`): `showToast()`, `playerName()`,
  `startNextGame()`, `loadLeaderboard()`; `doSubmit()` takes the finished game's
  data so the next game can start before the save returns; `initGame(givens, seed)`.
- `templates/sudoku_play.html`: result panel replaced by the leaderboard section.
- `static/src/css/style.css` (`?v=63`): `.game-toast*`, `.su-lb*`, `.su-name-row`.
- Tests (run with `node`; CI is Python-only):
  `tests/js/numbers_match_game_end.js` (16 checks: toast, save, Daily → ranked
  Easy → practice, practice not saved) and `tests/js/sudoku_behaviour.js`
  (26 checks, now including auto-save, guest name, toast and next puzzle).
