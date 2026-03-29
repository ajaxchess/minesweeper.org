# Nonosweeper No-Guess Solver Specification

## Overview

This spec describes `isNonosweeperSolvable(rows, cols, mineSet)` — a
JavaScript function that determines whether a Nonosweeper board can be
solved from its nonogram clues alone, without any guessing.

The function is used in `generatePuzzle()` to guarantee that every
Puzzle of the Day is uniquely solvable.

---

## Key difference from classic minesweeper no-guess

The classic minesweeper solver (`isSolvable` in `minesweeper.js`) uses
local adjacency constraints — each numbered cell constrains its 8
neighbours. The information is revealed gradually as the player clicks.

The Nonosweeper solver has access to **all clues at once** — the
complete row and column run-length arrays — but uses a different and
harder constraint: each clue encodes only the sizes of consecutive mine
groups, not their positions. This is a nonogram constraint satisfaction
problem.

---

## Definitions

```
rows, cols          — board dimensions
mineSet             — Set of mine indices (idx = r * cols + c)
rowClues[r]         — array of run lengths for row r  e.g. [3, 1, 2]
colClues[c]         — array of run lengths for col c
UNKNOWN = 0
MINE    = 1
SAFE    = 2
grid[r][c]          — current knowledge: UNKNOWN | MINE | SAFE
```

A **run** is a maximal consecutive sequence of mines in a line.
A **clue** is the ordered list of run lengths in reading order
(left-to-right for rows, top-to-bottom for cols).
A clue of `[]` means the line has no mines at all.

---

## Step 1 — Compute clues from mineSet

```js
function computeClues(rows, cols, mineSet) {
    const rowClues = Array.from({length: rows}, (_, r) => {
        const clue = [];
        let run = 0;
        for (let c = 0; c < cols; c++) {
            if (mineSet.has(r * cols + c)) { run++; }
            else if (run > 0)              { clue.push(run); run = 0; }
        }
        if (run > 0) clue.push(run);
        return clue;
    });
    const colClues = Array.from({length: cols}, (_, c) => {
        const clue = [];
        let run = 0;
        for (let r = 0; r < rows; r++) {
            if (mineSet.has(r * cols + c)) { run++; }
            else if (run > 0)              { clue.push(run); run = 0; }
        }
        if (run > 0) clue.push(run);
        return clue;
    });
    return { rowClues, colClues };
}
```

---

## Step 2 — Line solver (the "overlap" technique)

The line solver takes a single row or column and deduces which cells
are definitely mines or safe, given what is already known.

### Inputs

```
line   — array of N values (UNKNOWN | MINE | SAFE)
clue   — array of run lengths e.g. [3, 1, 2]
```

### Output

Returns a new array of length N with additional cells marked MINE or
SAFE. If a contradiction is detected (no valid placement exists),
throws an error — this indicates the grid state is inconsistent.

### Algorithm

**Find leftmost valid placement:**

Place each run as far left as possible, respecting known cells.

```
function leftmostPlacement(line, clue):
    pos = 0
    starts = []
    for each run length k in clue:
        // Advance past any known SAFE cells — a mine run cannot start here
        while pos < N and line[pos] == SAFE:
            pos++
        if pos + k > N: return null  // no valid placement

        // Try to place k mines at [pos, pos+k-1]
        // Scan forward until we find k consecutive non-SAFE cells
        while true:
            // check if cells [pos, pos+k-1] are all MINE or UNKNOWN
            end = pos + k - 1
            if end >= N: return null
            safe_in_range = first index j in [pos, end] where line[j] == SAFE
            if safe_in_range exists:
                pos = safe_in_range + 1  // skip past it and retry
                // but we may have skipped past a required MINE — check
                continue
            break

        // Verify no MINE cell between this run's end and the next run
        // (the gap cell immediately after this run must not be MINE)
        if pos + k < N and line[pos + k] == MINE:
            // The gap must be safe but it's a mine — shift right
            pos++
            continue loop (retry this run from new pos)

        starts.push(pos)
        pos = pos + k + 1  // advance past run + mandatory gap

    // After all runs, verify remaining cells are not required MINE
    for i from pos to N-1:
        if line[i] == MINE: return null  // unaccounted mine
    return starts
```

**Find rightmost valid placement** — symmetric: scan from right, place
each run as far right as possible. Reverse the clue, run the same
algorithm on the reversed line, then un-reverse the result.

**Compute overlap:**

```
for each run i:
    left  = leftStarts[i]
    right = rightStarts[i]
    k     = clue[i]

    // Cells covered by run i in ALL valid placements
    // = cells in both [left, left+k-1] and [right, right+k-1]
    // = [right, left+k-1]  (when right <= left+k-1, i.e. k > right-left)
    for c = right to left+k-1:
        mark cell c as MINE

// Cells not covered by ANY run in ANY valid placement are SAFE
// Build union of covered cells across all runs and both placements
coveredByAnyRun = union of [leftStarts[i], rightStarts[i]+k-1] for each i
for c = 0 to N-1:
    if c not in coveredByAnyRun and line[c] == UNKNOWN:
        mark cell c as SAFE
```

---

## Step 3 — Iterative propagation

Apply the line solver to every row and column repeatedly until no
cell changes state.

```js
function propagate(grid, rowClues, colClues, rows, cols):
    changed = true
    while changed:
        changed = false
        for r = 0 to rows-1:
            newLine = lineSolve(grid[r], rowClues[r])
            for c = 0 to cols-1:
                if newLine[c] != UNKNOWN and grid[r][c] == UNKNOWN:
                    grid[r][c] = newLine[c]
                    changed = true
        for c = 0 to cols-1:
            colLine = [grid[r][c] for r in 0..rows-1]
            newLine = lineSolve(colLine, colClues[c])
            for r = 0 to rows-1:
                if newLine[r] != UNKNOWN and grid[r][c] == UNKNOWN:
                    grid[r][c] = newLine[r]
                    changed = true
    return grid
```

---

## Step 4 — Backtracking (completeness)

After propagation stalls, check if any cells are still UNKNOWN. If so,
a guess would be required — but we first verify whether the board is
uniquely solvable by searching for exactly one consistent solution.

```js
function countSolutions(grid, rowClues, colClues, rows, cols, depthLimit):
    // Propagate first
    grid = propagate(deepCopy(grid), rowClues, colClues, rows, cols)

    // Check for contradiction
    if isContradiction(grid, rowClues, colClues): return 0

    // Check if fully solved
    if allKnown(grid): return 1

    // Depth limit exceeded — treat as "ambiguous" (conservative)
    if depthLimit <= 0: return 2

    // Pick first unknown cell
    (r, c) = firstUnknown(grid)

    // Branch: try MINE
    gridMine = deepCopy(grid)
    gridMine[r][c] = MINE
    n = countSolutions(gridMine, rowClues, colClues, rows, cols, depthLimit - 1)
    if n >= 2: return 2  // already ambiguous, short-circuit

    // Branch: try SAFE
    gridSafe = deepCopy(grid)
    gridSafe[r][c] = SAFE
    n += countSolutions(gridSafe, rowClues, colClues, rows, cols, depthLimit - 1)
    return Math.min(n, 2)  // cap at 2 — we only need to know 0, 1, or 2+
```

`isContradiction` verifies no line has zero valid placements given
the current grid state.

---

## Main function

```js
function isNonosweeperSolvable(rows, cols, mineSet) {
    const { rowClues, colClues } = computeClues(rows, cols, mineSet);

    // Initial grid — all unknown
    const grid = Array.from({length: rows}, () => new Uint8Array(cols));
    // UNKNOWN = 0, no initialization needed

    const solutions = countSolutions(grid, rowClues, colClues, rows, cols, /*depthLimit=*/30);
    return solutions === 1;
}
```

---

## Step 5 — Integration with `generatePuzzle`

Replace the single-seed generation with a candidate search:

```js
function generatePuzzle(seedStr, difficulty, isPOTD = true) {
    const { rows, cols, mines } = DIFFICULTIES[difficulty];

    if (!isPOTD) {
        // Random puzzles: no solvability guarantee
        return generateBoard(seedStr + ':' + difficulty, rows, cols, mines);
    }

    // POTD: search for a no-guess board
    const MAX_ATTEMPTS = 50;
    for (let i = 0; i < MAX_ATTEMPTS; i++) {
        const candidate = generateBoard(
            seedStr + ':' + difficulty + ':' + i, rows, cols, mines
        );
        if (isNonosweeperSolvable(rows, cols, candidate.mineSet)) {
            return candidate;
        }
    }

    // Fallback: return the ':0' candidate (deterministic, same as legacy seed)
    return generateBoard(seedStr + ':' + difficulty + ':0', rows, cols, mines);
}
```

`generateBoard(seed, rows, cols, mines)` is the existing seeded
Fisher-Yates placement extracted from the current `generatePuzzle`.

### Backward compatibility

The `:0` suffix was not present in the original seed format. Existing
POTD solves (stored in `nonosweeper_scores` with `puzzle_date`) remain
valid — the score submission uses `puzzle_date`, not the seed. Players
who already completed a puzzle before this feature launched will not
have their results invalidated.

The first time a player visits after the feature is deployed, they will
see a new (potentially different) puzzle for today. This is acceptable.

---

## Contradiction check

A grid state is a contradiction if any line has no valid placement:

```js
function isContradiction(grid, rowClues, colClues):
    for each row r: if leftmostPlacement(grid[r], rowClues[r]) == null: return true
    for each col c: if leftmostPlacement(colLine, colClues[c]) == null: return true
    return false
```

---

## Performance

| Board | Cells | Stage 1 only | With backtracking (depth 30) |
|---|---|---|---|
| Beginner 8×8, 16 mines | 64 | < 2 ms | < 10 ms |
| Intermediate 10×10, 35 mines | 100 | < 5 ms | < 30 ms |
| Expert 15×15, 75 mines | 225 | < 15 ms | < 100 ms |

50 candidates × worst-case 100 ms = 5 s total for expert.
Run `generatePuzzle` in a `setTimeout(fn, 0)` so it does not block the
initial page render. Show a "Generating puzzle…" state while it runs.

---

## Edge cases

| Case | Handling |
|---|---|
| Empty clue `[]` | Entire line is SAFE — mark all cells safe |
| Single-run clue `[N]` where N == line length | Entire line is MINE |
| Contradiction in a branch | `countSolutions` returns 0 for that branch |
| Depth limit hit | Treated as ambiguous (returns 2) — conservative, may reject a uniquely solvable board, but avoids hanging |
| All 50 candidates fail | Return `:0` fallback — extremely rare for beginner/intermediate, possible for expert |

---

## Testing

Validate against known boards before shipping:

1. A board where all mines can be deduced by line-solving alone (Stage 1 suffices) → `isNonosweeperSolvable` returns `true`
2. A board where at least one guess is required (two distinct valid mine configurations exist) → returns `false`
3. A board that requires backtracking but is still unique → returns `true`
4. An empty board (0 mines, all clues `[]`) → all cells immediately safe, returns `true`
5. A board where every cell is a mine → all clues are `[cols]` (or `[rows]`), returns `true`

Write test vectors in `src/__tests__/nonosweeper.test.js` covering all
five cases before wiring to `generatePuzzle`.
