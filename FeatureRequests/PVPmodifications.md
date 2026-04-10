# PvP Beta Modifications
Target: https://minesweeper.org/pvpbeta
Plan: test in pvpbeta, then promote to replace /pvp

---

## Feature A: Mouseover Player Stats (F69)

Hovering a player's name in the match header shows a floating stat card.

**Stats shown:**
- Best time (for the active PvP board size)
- Elo Rating
- Wins / Losses

**Rules:**
- Guest/anonymous players with no stats: card does not appear
- No named rank tiers (not enough player base yet) — show raw Elo number
- Win streak: not shown

**Implementation notes:**
- New API endpoint: `GET /api/pvp/player-stats/{player_id}` returning best_time, elo, wins, losses
- Client: mouseover listener on player name elements; fetch on first hover, cache result; render floating div

---

## Feature B: Frontier / Playable Area (F70)

Only cells within **Chebyshev distance 2** of any revealed cell are clickable.
All other unrevealed cells are locked (visually distinct — light grey).

**Rules:**
- Enforced both client-side (visual lock + click rejection) and server-side (reveal() rejects out-of-frontier clicks)
- At game start, the initial frontier wraps the shared pre-revealed center zone
- After any reveal (including BFS flood-fill), frontier is recomputed
- After a 3×3 mine-hit reset (Feature C), frontier recomputes based on the new revealed state

**Implementation notes:**
- Server: add `frontier: set[tuple]` computed property on `PlayerState`; `reveal()` returns early if `(r,c)` not in frontier
- Client: maintain local frontier set; render frontier cells with a lighter background; ignore clicks outside it
- Frontier cells are: all unrevealed cells where `max(|dr|, |dc|) <= 2` for any revealed cell `(r, c)`

---

## Feature C: Mine Reallocation on Hit — no instant loss (F71)

Clicking a mine triggers a local scramble instead of ending the game.

### Animation sequence (client):
1. Clicked cell flashes red (the mine)
2. Red border ripples outward: 1×1 → 2×2 → 3×3 around the mine
3. The 3×3 area resets to unrevealed (dark/unknown)
4. Adjacent revealed numbers briefly flash to show recalculation

### Server logic on mine hit:
1. Identify all cells in the 3×3 area centred on hit cell (clamped to board edges)
2. Count mines currently in those 9 cells
3. Randomly redistribute those mines among the same 9 cells (mine CAN land back on the clicked cell)
4. Reset all 9 cells to unrevealed in this player's `revealed` array
5. Recalculate `board[r][c]` values for all cells adjacent to any changed mine position
6. Increment `mine_hits` counter for this player
7. Do NOT penalise score — the 3×3 loss of progress is the only penalty

### Visibility:
- Reallocation and board divergence are **per-player only** — the opponent's board is unaffected
- **Both players** see the explosion animation on the hitter's board (opponent receives an animation event)
- The opponent's view of the hitter's board shows the 3×3 going dark

### Mine-hit counter:
- Displayed in the match header for both players (e.g. "💥 2")
- Updated in real time via existing score/update messages

### New WebSocket messages needed:
- `mine_hit` (server → both players): `{ type: "mine_hit", player_id, r, c, reset_cells: [[r,c],...], updated_values: {r,c: val,...} }`
  - Hitter receives updated board values so they can re-render numbers
  - Opponent receives `reset_cells` so their view of the hitter's board goes dark; no updated values (boards diverge)

### Interaction with Feature B (Frontier):
- After the 3×3 reset, the frontier recomputes — cells in the reset area that are no longer adjacent to any revealed cell fall out of the frontier

---

## Resolved design decisions
- **Frontier visual:** outermost ring only — cells at Chebyshev distance **exactly 2** from the nearest revealed cell get the light grey indicator. Distance-1 cells render as normal unrevealed tiles.
- **Frontier on opponent's board:** yes — both boards show the frontier ring, so you can see how far your opponent can reach.
