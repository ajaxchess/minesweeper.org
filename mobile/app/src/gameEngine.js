/**
 * gameEngine.js
 *
 * Core minesweeper logic ported from static/js/minesweeper.js.
 * Pure JS — no DOM, no React Native APIs.
 *
 * Functions are copied verbatim from the web source with one change:
 *   calcBoardHash uses Buffer.from().toString('base64') instead of btoa(),
 *   because btoa is not available in the React Native JS engine (Hermes/JSC).
 *
 * See mobile/ios/BoardHashSpec.md and mobile/ios/NoGuessSolverSpec.md
 * for the full specifications and test vectors.
 */

// ── Board sizes ────────────────────────────────────────────────────────────────

export const BOARD_SIZES = {
  beginner:     { rows: 9,  cols: 9,  mines: 10 },
  intermediate: { rows: 16, cols: 16, mines: 40 },
  expert:       { rows: 16, cols: 30, mines: 99 },
};

// ── Neighbours ────────────────────────────────────────────────────────────────
// Returns up to 8 adjacent [row, col] pairs, clipped to board bounds.

export function neighbors(r, c, rows, cols) {
  const out = [];
  for (let dr = -1; dr <= 1; dr++)
    for (let dc = -1; dc <= 1; dc++) {
      if (dr === 0 && dc === 0) continue;
      const nr = r + dr, nc = c + dc;
      if (nr >= 0 && nr < rows && nc >= 0 && nc < cols)
        out.push([nr, nc]);
    }
  return out;
}

// ── Mine placement ────────────────────────────────────────────────────────────
// Places mines at random, guaranteeing the 3×3 zone around (safeR, safeC)
// is mine-free (first-click safety).
//
// Returns { mineSet: Set<idx>, board: number[][] }
//   board[r][c] = -1 for mines, 0–8 for adjacent mine count.

export function placeMines(rows, cols, mines, safeR, safeC) {
  const forbidden = new Set();
  for (let dr = -1; dr <= 1; dr++)
    for (let dc = -1; dc <= 1; dc++) {
      const nr = safeR + dr, nc = safeC + dc;
      if (nr >= 0 && nr < rows && nc >= 0 && nc < cols)
        forbidden.add(nr * cols + nc);
    }

  const pool = [];
  for (let i = 0; i < rows * cols; i++)
    if (!forbidden.has(i)) pool.push(i);

  // Fisher-Yates partial shuffle
  for (let i = 0; i < mines; i++) {
    const j = i + Math.floor(Math.random() * (pool.length - i));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }

  const mineSet = new Set(pool.slice(0, mines));
  const board   = Array.from({length: rows}, () => Array(cols).fill(0));

  for (const idx of mineSet) {
    const r = Math.floor(idx / cols), c = idx % cols;
    board[r][c] = -1;
    neighbors(r, c, rows, cols).forEach(([nr, nc]) => {
      if (board[nr][nc] !== -1) board[nr][nc]++;
    });
  }
  return { mineSet, board };
}

// ── No-guess solver ───────────────────────────────────────────────────────────
// Returns true if the board can be fully solved by constraint propagation
// from (startR, startC) without any random guessing.
// Uses single-cell deductions + subset deduction (A ⊆ B → derive B−A).

export function isSolvable(rows, cols, mineSet, board, startR, startC) {
  const n          = rows * cols;
  const revealed   = new Uint8Array(n);
  const knownMine  = new Uint8Array(n);

  function bfsReveal(startIdx) {
    const q = [startIdx];
    while (q.length) {
      const idx = q.pop();
      if (revealed[idx] || mineSet.has(idx)) continue;
      revealed[idx] = 1;
      if (board[Math.floor(idx / cols)][idx % cols] === 0) {
        for (const [nr, nc] of neighbors(Math.floor(idx / cols), idx % cols, rows, cols)) {
          const ni = nr * cols + nc;
          if (!revealed[ni] && !mineSet.has(ni)) q.push(ni);
        }
      }
    }
  }

  bfsReveal(startR * cols + startC);

  let progress = true;
  while (progress) {
    progress = false;
    const constraints = [];

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const i = r * cols + c;
        if (!revealed[i] || board[r][c] <= 0) continue;

        const hidden = [];
        let mineCount = 0;
        for (const [nr, nc] of neighbors(r, c, rows, cols)) {
          const ni = nr * cols + nc;
          if (knownMine[ni]) mineCount++;
          else if (!revealed[ni]) hidden.push(ni);
        }
        const remaining = board[r][c] - mineCount;
        if (remaining < 0 || remaining > hidden.length) continue;

        if (remaining === 0 && hidden.length > 0) {
          hidden.forEach(ni => bfsReveal(ni));
          progress = true;
        } else if (remaining > 0 && remaining === hidden.length) {
          hidden.forEach(ni => { knownMine[ni] = 1; });
          progress = true;
        } else if (hidden.length > 0) {
          constraints.push({ cells: hidden, count: remaining });
        }
      }
    }

    // Subset deduction: if A ⊆ B, derive (B − A)
    for (let i = 0; i < constraints.length; i++) {
      for (let j = 0; j < constraints.length; j++) {
        if (i === j) continue;
        const ci = constraints[i], cj = constraints[j];
        if (ci.cells.length >= cj.cells.length) continue;
        const ciSet = new Set(ci.cells);
        if (!ci.cells.every(x => cj.cells.indexOf(x) >= 0)) continue;
        const diff      = cj.cells.filter(x => !ciSet.has(x));
        const diffCount = cj.count - ci.count;
        if (diffCount < 0 || diffCount > diff.length) continue;
        if (diffCount === 0 && diff.length > 0) {
          diff.forEach(ni => bfsReveal(ni));
          progress = true;
        } else if (diffCount > 0 && diffCount === diff.length) {
          diff.forEach(ni => { knownMine[ni] = 1; });
          progress = true;
        }
      }
    }
  }

  for (let i = 0; i < n; i++) {
    if (!mineSet.has(i) && !revealed[i]) return false;
  }
  return true;
}

// ── No-guess board generation ─────────────────────────────────────────────────
// Retries mine placement up to 500 times until isSolvable passes.
// Falls back to a random board if no solvable layout is found (rare).

export function placeMinesNoGuess(rows, cols, mines, safeR, safeC) {
  for (let attempt = 0; attempt < 500; attempt++) {
    const result = placeMines(rows, cols, mines, safeR, safeC);
    if (isSolvable(rows, cols, result.mineSet, result.board, safeR, safeC))
      return result;
  }
  return placeMines(rows, cols, mines, safeR, safeC); // fallback
}

// ── Board hash ────────────────────────────────────────────────────────────────
// Encodes the mine positions as a base64 bit-array.
// Identical to the web version (calcBoardHash in minesweeper.js) except
// Buffer.from().toString('base64') replaces btoa().
// See mobile/ios/BoardHashSpec.md for the full specification.

export function calcBoardHash(rows, cols, mineSet) {
  const bytes = new Uint8Array(Math.ceil(rows * cols / 8));
  for (const idx of mineSet) bytes[idx >> 3] |= (1 << (idx & 7));
  return Buffer.from(bytes).toString('base64');
}

// ── 3BV (Bechtel's Board Benchmark Value) ─────────────────────────────────────
// Each opening region (contiguous blank cells + their numbered borders) = 1.
// Each isolated numbered cell (not adjacent to any opening) = 1.

export function calc3BV(board, rows, cols, mineSet) {
  const n       = rows * cols;
  const covered = new Uint8Array(n);
  let   bbbv    = 0;

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const idx = r * cols + c;
      if (board[r][c] !== 0 || covered[idx] || mineSet.has(idx)) continue;
      bbbv++;
      // BFS through blank cells, marking blanks + numbered borders as covered
      const queue = [[r, c]];
      covered[idx] = 1;
      while (queue.length) {
        const [cr, cc] = queue.shift();
        for (const [nr, nc] of neighbors(cr, cc, rows, cols)) {
          const ni = nr * cols + nc;
          if (covered[ni] || mineSet.has(ni)) continue;
          covered[ni] = 1;
          if (board[nr][nc] === 0) queue.push([nr, nc]);
        }
      }
    }
  }

  // Isolated numbered cells not touched by any opening
  for (let i = 0; i < n; i++) {
    const r = Math.floor(i / cols), c = i % cols;
    if (board[r][c] > 0 && !covered[i]) bbbv++;
  }

  return bbbv;
}
