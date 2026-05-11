# No-Guess Solver Specification

## Source of truth

The canonical implementation lives entirely in `static/js/minesweeper.js`.
There is no Python solver — the web client generates and verifies no-guess
boards client-side. The React Native app should do the same.

Relevant functions (lines 105–229):

| Function | Purpose |
|---|---|
| `placeMines(rows, cols, mines, safeR, safeC)` | Random mine placement, safe zone around first click |
| `isSolvable(rows, cols, mineSet, board, startR, startC)` | Constraint solver — returns true if board needs no guesses |
| `placeMinesNoGuess(rows, cols, mines, safeR, safeC)` | Retries placement until `isSolvable` passes (max 500 attempts) |
| `neighbors(r, c, rows, cols)` | Returns up to 8 adjacent `[row, col]` pairs, bounds-checked |

---

## Board representation

```
idx = row * cols + col          // row-major, 0-based
board[r][c] = -1                // mine
board[r][c] = 0                 // blank (no adjacent mines)
board[r][c] = 1..8              // count of adjacent mines
mineSet = Set<idx>              // set of mine indices
```

---

## Step 1 — Mine placement (`placeMines`)

1. Build a **forbidden zone**: the 3×3 neighbourhood of the first-click cell
   `(safeR, safeC)`, clipped to board bounds. These cells can never be mines.
2. Collect all non-forbidden cell indices into `pool`.
3. Fisher-Yates partial shuffle: for i = 0..mines-1, swap `pool[i]` with a
   random element from `pool[i..pool.length-1]`. The first `mines` elements
   of `pool` become the mine set.
4. Build the `board` 2-D array: set mine cells to -1, increment all
   non-mine neighbours of each mine.

---

## Step 2 — Solvability check (`isSolvable`)

### Initial state

```
revealed[i] = 0 for all i
knownMine[i] = 0 for all i
```

### BFS reveal (`bfsReveal`)

Flood-fills from a starting cell index, revealing non-mine cells.
If a revealed cell has value 0 (blank), its neighbours are queued.
Mines are never revealed.

The first call is `bfsReveal(safeR * cols + safeC)` — simulating the
player's first click.

### Constraint propagation loop

Repeat until no progress in a full pass:

**For every revealed numbered cell `(r, c)` (value > 0):**

1. Collect its unrevealed, non-mine neighbours → `hidden[]`
2. Count already-confirmed mines among its neighbours → `mineCount`
3. `remaining = board[r][c] - mineCount`
4. Apply simple deductions:
   - If `remaining == 0` and `hidden` is non-empty → all hidden cells are
     safe; call `bfsReveal` on each. Mark progress.
   - If `remaining == hidden.length` and `remaining > 0` → all hidden cells
     are mines; set `knownMine[ni] = 1` for each. Mark progress.
   - Otherwise → record as a constraint `{ cells: hidden[], count: remaining }`

**Subset deduction** over all collected constraints:

For every pair of constraints `(A, B)` where `A.cells ⊆ B.cells`:

- Compute `diff = B.cells − A.cells`,  `diffCount = B.count − A.count`
- If `diffCount < 0` or `diffCount > diff.length` → skip (invalid)
- If `diffCount == 0` and `diff` is non-empty → all diff cells are safe;
  `bfsReveal` each. Mark progress.
- If `diffCount == diff.length` and `diffCount > 0` → all diff cells are
  mines; set `knownMine`. Mark progress.

### Termination

After the loop stabilises, check: if any non-mine cell is still unrevealed,
return `false` (board requires a guess). Otherwise return `true`.

```
for i in 0..rows*cols-1:
    if i not in mineSet and revealed[i] == 0: return false
return true
```

---

## Step 3 — No-guess placement (`placeMinesNoGuess`)

```
for attempt in 0..499:
    result = placeMines(rows, cols, mines, safeR, safeC)
    if isSolvable(rows, cols, result.mineSet, result.board, safeR, safeC):
        return result
return placeMines(rows, cols, mines, safeR, safeC)  // fallback if all 500 fail
```

The fallback means a board that technically requires a guess can be returned
if no solvable board is found in 500 attempts. This is rare for standard
board sizes but possible for very high mine densities.

---

## React Native port

All four functions can be copied from `minesweeper.js` into the app with
minimal changes. The only dependency between them is `neighbors`.

```js
// Paste these verbatim from minesweeper.js:
//   neighbors()
//   placeMines()
//   isSolvable()
//   placeMinesNoGuess()
```

`Uint8Array` is available in React Native's JS engine (Hermes and JSC both
support typed arrays). `Set`, `Array.from`, and `Math.random` behave
identically. No polyfills are required.

---

## Performance

For standard board sizes, `isSolvable` is fast enough to run synchronously:

| Board | Cells | Typical `isSolvable` time |
|---|---|---|
| Beginner 9×9, 10 mines | 81 | < 1 ms |
| Intermediate 16×16, 40 mines | 256 | < 5 ms |
| Expert 30×16, 99 mines | 480 | < 15 ms |

`placeMinesNoGuess` calls `isSolvable` up to 500 times but typically succeeds
within 5–20 attempts for standard sizes. Total generation time is well under
500 ms even on low-end devices. Run on a background thread (e.g. in a
`setTimeout` or `InteractionManager.runAfterInteractions`) if UI jank is
observed.
