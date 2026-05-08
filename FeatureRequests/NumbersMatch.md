# Numbers Match

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

## Elimination
Tap a valid pair to remove both numbers from the board, leaving empty cells.

## Adding Lines
If no valid moves remain, the player can append the current remaining numbers
(in their present order) to the bottom of the board, creating new pairing
opportunities.

## Board Layout
The board has 9 columns. Row count increases with board number:

| Board(s) | Rows |
|----------|------|
| 1        | 3    |
| 2–3      | 4    |
| 4–6      | 5    |
| 7–10     | 6    |
| 11–15    | 7    |
| 16–21    | 8    |
| 22–28    | 9    |
| 29–36    | 10   |
| …        | …    |

Every board is guaranteed to have at least one solution.

## Board Generation
- **Daily board:** One shared board per day, the same for all players. Generated
  from a hash encoding the board number and the placement of all numbers.
- **Random board:** Players can also generate a random board on demand via a
  dedicated button.

## Scoring
| Event | Points |
|-------|--------|
| Pair removed | +1 |
| Full row cleared | +10 |
| Far Apart bonus | +1 per empty cell between the pair, max +4 |
| Board cleared | +150 |

The Far Apart bonus applies when matched numbers are not directly adjacent —
each empty cell along the line between them adds 1 point, capped at 4.

## Timer
A timer runs for the duration of the game and is recorded on completion.

## Leaderboard
The daily board leaderboard ranks players by:
1. Score (descending) — primary criterion
2. Time (ascending) — tiebreaker

## Player Tools
| Tool | Limit | Behaviour |
|------|-------|-----------|
| Undo | 3 per game | Reverses the last elimination |
| Hint | 9 per game | Highlights a single valid pair |
| Check | TBD | To be defined after initial implementation |

## Strategies & Tips
- Focus on smaller numbers first to keep the board open.
- Clearing full rows earns bonus points — prioritise completing rows.
- Use Undo sparingly; it is limited to 3 per game.
- Use Hints when stuck; 9 are available per game.
