# Numbers Match

**Feature ID:** F96  
**URL:** /numbers-match (daily permalink: /numbers-match/YYYY-MM-DD)  
**Code:** numbers_match_routes.py, numbers_match_generator.py, templates/numbers_match.html, static/src/js/numbers_match.js

## Overview
A number-pairing puzzle game. Clear the board by matching pairs of numbers, either
identical (1−1, 7−7) or summing to 10 (1−9, 2−8, 3−7, 4−6, 5−5).

## Numbers
- Range: 1–9 only. No 0s or 10s appear on the board.

## Pairing Rules
A valid pair must satisfy both a value rule and an adjacency rule.

**Value rule:** Two numbers match if they are identical or sum to 10.

**Adjacency rule:** Two numbers are eligible to pair if they are connected in a
straight line — horizontally, vertically, or diagonally — with only empty cells
between them (line-of-sight, like a rook or bishop move). Numbers in between
block the match; empty cells do not.

**Wrap-around:** The last cell of a row (col 9, row N) is considered adjacent to
the first cell of the next row (col 1, row N+1). This wrap counts as a horizontal
adjacency only — no diagonal adjacency across the line boundary.


In code (`areAdjacent`), the wrap is any reading-order path (left to right, row by
row) whose cells in between are all empty.

## Elimination
Tap a valid pair to remove both numbers from the board, leaving empty cells.
Rows that become completely empty collapse and are removed from the board.

## Adding Lines
The player can append the current remaining numbers (in their present order) to
the bottom of the board, creating new pairing opportunities. Limited to
**5 per game**. When a hint finds no valid pair, the Add Lines button pulses.

## Board Layout
The board has 9 columns. Every board starts with a fixed number of rows; the row
schedule by board number from the original design is not used.

| Mode | Starting rows | Leaderboard puzzle id |
|------|---------------|-----------------------|
| Daily | 4 | `YYYY-MM-DD-v2` |
| Easy | 4 | `YYYY-MM-DD-easy-v2` |
| Medium | 8 | `YYYY-MM-DD-medium-v2` |
| Hard | 16 | `YYYY-MM-DD-hard-v2` |
| Expert | 32 | `YYYY-MM-DD-expert-v2` |

Boards contain 1–9 repeated and shuffled, so every number has a partner, and
Add Lines lets the game keep progressing.

## Board Generation
- **Daily board:** one shared board per day, the same for all players. The server
  generates it (`numbers_match_generator.generate_daily`) with a SHA-256 seed of
  the date plus the revision (`:v2`). The day is the **America/New_York** date
  (`/api/numbers-match-today`), not the browser's.
- **Difficulty boards (Easy–Expert):** generated in the browser
  (`generateBoardClient`, mulberry32 + FNV-1a) from a seed of date + difficulty +
  revision, so each one is also the same for every player on a given day.
- **Revision:** `v2` is the current board revision. It is hard-coded in three
  places that must change together: `NUMBERS_MATCH_BOARD_REVISION` in
  `numbers_match_routes.py` and `main.py`, and `_serverRevision` in the JS.
- After a win, the next game of the same variant starts automatically (350 ms).

## Scoring
| Event | Points |
|-------|--------|
| Pair removed | +1 |
| Far Apart bonus | +1 per empty cell between the pair, max +4 |
| Full row cleared | +10 |
| Board cleared | +150 |
| Hint used | −3 |
| Undo used | −5 |

The score never goes below 0.

## Timer
The timer starts on the first cell click and stops when the board is cleared.
The elapsed seconds are submitted as `time_secs` (minimum 1).

See bug B52: from 2026-05-13 until the fix, the timer called minesweeper.js's
global `startTimer`/`stopTimer` and every web score was saved as 1 second. The
timer functions are now named `nmStartTimer`/`nmStopTimer`. Do not reuse
global function names that `minesweeper.js` defines; base.html loads it with
`defer`, so it runs after this script and overrides them.

## Leaderboard
Every daily and difficulty variant has its own leaderboard (top 20, one row per
name, flagged names excluded). The score is saved automatically on a win; guests
get a `Guest NNNN` name kept in localStorage. Ranking
(`get_numbers_match_scores`):
1. Score ÷ time (descending): a higher score reached faster ranks higher
2. Score (descending)
3. Time (ascending)

## Player Tools
| Tool | Limit | Behaviour |
|------|-------|-----------|
| Undo | 3 per game, −5 points | Reverses the last elimination or Add Lines |
| Hint | 9 per game, −3 points | Highlights a single valid pair |
| Add Lines | 5 per game | Appends remaining numbers to the bottom |
| Paths | unlimited toggle | Highlights the row, column, diagonals and wrap cells of the hovered number |

## Strategies & Tips
- Focus on smaller numbers first to keep the board open.
- Clearing full rows earns bonus points — prioritise completing rows.
- Use Undo sparingly; it is limited to 3 per game and costs 5 points.
- Use Hints when stuck; 9 are available per game, at 3 points each.