/**
 * Minesweeper Rush — Game Engine
 *
 * Rules:
 *  - New rows appear at the top on a timer, filling with ✕ marks (incoming).
 *  - When a row finishes filling, it becomes playable (active).
 *  - Left-click to reveal; right-click to flag.
 *  - Hitting a mine adds 2 penalty rows instead of ending the game.
 *  - A row is cleared when all its mines are flagged.
 *  - If unfinished rows drop below MIN_ROWS, 4 new rows are added immediately.
 *  - Game over when active rows exceed maxActive.
 *  - Safety net: if no guaranteed safe move exists, mine hits carry no penalty.
 */

(function () {
'use strict';

// ── Mode configs ──────────────────────────────────────────────────────────────
const RUSH_CFGS = {
  easy:   { cols: 9,  density: 0.10, intervalMs: 12000, maxActive: 12 },
  normal: { cols: 16, density: 0.15, intervalMs:  9000, maxActive: 16 },
  hard:   { cols: 30, density: 0.20, intervalMs:  7000, maxActive: 20 },
};

const INITIAL_ROWS  = 8;    // rows to start with (pre-built, no animation)
const MIN_ROWS      = 4;    // if unfinished rows < this, add 4 immediately
const CLEAR_DELAY   = 500;  // ms before cleared row fades from DOM
const MIN_INTERVAL  = 3000; // fastest possible row-arrival interval (ms)
const SPEED_PER_5   = 400;  // interval reduction per 5 mines found

const NUM_COLORS = ['','#1976D2','#388E3C','#D32F2F','#7B1FA2',
                    '#F57F17','#00838F','#212121','#757575'];

// ── State ─────────────────────────────────────────────────────────────────────
let rush = {};

function freshRush(mode) {
  const cfg = RUSH_CFGS[mode] || RUSH_CFGS.easy;
  return {
    cols:         cfg.cols,
    density:      cfg.density,
    baseInterval: cfg.intervalMs,
    curInterval:  cfg.intervalMs,
    maxActive:    cfg.maxActive,
    mode,

    // Board arrays; index 0 = oldest (bottom of display), high = newest (top)
    board:      [],   // board[r][c] = -1 (mine) or neighbor count
    revealed:   [],   // bool
    flagged:    [],   // 0=none 1=flag 2=question
    rowStatus:  [],   // 'active' | 'incoming' | 'cleared'
    rowMines:   [],   // Set of mine column-indices per row
    rowFillCol: [],   // fill animation progress (how many ✕ shown)
    rowIsInitial: [], // true for initial build rows; false for dynamically added rows

    numRows:        0,
    score:          0,  // currently-flagged mines (internal; drives speed only)
    clearedMines:   0,  // mines in cleared rows (drives display, leaderboard score)
    rowsCleared:    0,
    salvageTokens:  0,  // earned every 20 rows cleared
    cellCountedAt: [],  // cellCountedAt[r][c] = numRows when board[r][c] was last computed
    elapsed:      0,

    started:    false,
    over:       false,
    noSafeMove: false,

    timerID:     null,
    rowTimerID:  null,
    fillIDs:     {},  // rowIdx → setInterval ID
  };
}

// ── Neighbour helpers ─────────────────────────────────────────────────────────
function rushNbs(r, c) {
  const out = [];
  for (let dr = -1; dr <= 1; dr++)
    for (let dc = -1; dc <= 1; dc++) {
      if (dr === 0 && dc === 0) continue;
      const nr = r + dr, nc = c + dc;
      if (nr >= 0 && nr < rush.numRows && nc >= 0 && nc < rush.cols)
        out.push([nr, nc]);
    }
  return out;
}

function neighborMineCount(r, c) {
  let n = 0;
  for (const [nr, nc] of rushNbs(r, c))
    if (rush.board[nr][nc] === -1) n++;
  return n;
}

// ── Stale-number display ───────────────────────────────────────────────────────
// board[r][c] was computed when row r was initialised.  For initial rows every
// neighbour row that existed at build time is included; for dynamically-added
// rows only rows < r were present.  A mine in row nr > r that was added after
// row r was built is NOT counted in board[r][c].
//
// Returns { text, color } for a revealed number cell, or null if not applicable.
//   "?"  – the displayed number is stale because a later row above added unknown mines.
//   "n"  – effective remaining mine count after subtracting cleared/flagged mines.
//   ""   – all neighbouring mines are accounted for (show blank like a 0-cell).
function getCellDisplay(r, c) {
  if (!rush.revealed[r][c] || rush.board[r][c] <= 0) return null;

  let newAboveUnknown = 0; // mines from later rows above not yet resolved
  let knownAboveBelow = 0; // mines that ARE in board[r][c] and are now resolved

  for (const [nr, nc] of rushNbs(r, c)) {
    if (rush.board[nr][nc] !== -1) continue; // not a mine

    const isAbove = nr > r;
    // Was this mine counted in board[r][c] when the cell was last computed?
    // nr < cellCountedAt[r][c] means row nr existed at that time.
    const wasCounted = !isAbove || nr < rush.cellCountedAt[r][c];

    if (!wasCounted) {
      // Mine from a row added after this cell's row was initialised
      if (rush.rowStatus[nr] !== 'cleared') newAboveUnknown++;
    } else {
      // Mine was in the original count
      if (rush.rowStatus[nr] === 'cleared') knownAboveBelow++;
    }
  }

  if (newAboveUnknown > 0) return { text: '?', color: 'var(--text-dim)' };

  const effective = rush.board[r][c] - knownAboveBelow;
  if (effective <= 0) return { text: '', color: '' };
  return { text: String(effective), color: NUM_COLORS[Math.min(effective, 8)] || '' };
}

// Re-render all revealed number cells in rows adjacent to row r.
function updateRevealedNearRow(r) {
  for (let adjRow = r - 1; adjRow <= r + 1; adjRow++) {
    if (adjRow < 0 || adjRow >= rush.numRows) continue;
    if (rush.rowStatus[adjRow] !== 'active') continue;
    for (let c = 0; c < rush.cols; c++) {
      if (!rush.revealed[adjRow][c] || rush.board[adjRow][c] <= 0) continue;
      const el = cellEl(adjRow, c);
      if (!el) continue;
      const disp = getCellDisplay(adjRow, c);
      if (!disp) continue;
      el.textContent = disp.text;
      el.style.color  = disp.color;
    }
  }
}

// ── DOM helpers ───────────────────────────────────────────────────────────────
function rowEl(r)    { return document.querySelector(`.rush-row[data-row="${r}"]`); }
function cellEl(r,c) { return document.querySelector(`.rush-row[data-row="${r}"] [data-r="${r}"][data-c="${c}"]`); }

function boardEl()  { return document.getElementById('rush-board'); }

// ── Stats helpers ─────────────────────────────────────────────────────────────
function activeCount() {
  return rush.rowStatus.filter(s => s === 'active').length;
}
function unfinishedCount() {
  return rush.rowStatus.filter(s => s === 'active' || s === 'incoming').length;
}

// ── Timer ─────────────────────────────────────────────────────────────────────
function startRushTimer() {
  if (rush.timerID) return;
  rush.timerID = setInterval(() => {
    rush.elapsed++;
    document.getElementById('rush-timer').textContent = fmtTime(rush.elapsed);
  }, 1000);
}

function stopRushTimer() {
  clearInterval(rush.timerID);
  rush.timerID = null;
}

function fmtTime(s) {
  return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
}

// ── Row interval timer ────────────────────────────────────────────────────────
function scheduleNextRow() {
  if (rush.rowTimerID) clearTimeout(rush.rowTimerID);
  rush.rowTimerID = setTimeout(() => {
    if (!rush.over) {
      addRow();
      scheduleNextRow();
    }
  }, rush.curInterval);
}

function updateSpeed() {
  const reduction = Math.floor(rush.clearedMines / 5) * SPEED_PER_5;
  rush.curInterval = Math.max(MIN_INTERVAL, rush.baseInterval - reduction);
  const level = Math.floor(rush.clearedMines / 5) + 1;
  document.getElementById('rush-speed').textContent = '×' + level;
}

// ── Add a new row at the top (incoming) ───────────────────────────────────────
function addRow() {
  const r = rush.numRows;

  // Extend arrays
  rush.board.push(new Array(rush.cols).fill(0));
  rush.revealed.push(new Array(rush.cols).fill(false));
  rush.flagged.push(new Array(rush.cols).fill(0));
  rush.rowStatus.push('incoming');
  rush.rowFillCol.push(0);
  rush.rowIsInitial.push(false);
  rush.cellCountedAt.push(new Array(rush.cols).fill(0));  // filled after numRows++ below

  // Place mines
  const mines = new Set();
  for (let c = 0; c < rush.cols; c++)
    if (Math.random() < rush.density) mines.add(c);
  rush.rowMines.push(mines);
  for (const c of mines) rush.board[r][c] = -1;

  rush.numRows++;

  // Recompute neighbor counts for new row (row r-1 now exists below it)
  for (let c = 0; c < rush.cols; c++) {
    if (rush.board[r][c] !== -1) rush.board[r][c] = neighborMineCount(r, c);
    rush.cellCountedAt[r][c] = rush.numRows;
  }

  // Update counts for unrevealed cells in the row below
  if (r > 0) {
    const below = r - 1;
    for (let c = 0; c < rush.cols; c++) {
      if (rush.board[below][c] !== -1 && !rush.revealed[below][c]) {
        rush.board[below][c] = neighborMineCount(below, c);
        rush.cellCountedAt[below][c] = rush.numRows;
        if (rush.rowStatus[below] === 'active') renderCell(below, c);
      }
    }
  }

  // Build DOM row (prepend = visible at top)
  prependRowDOM(r);

  // Start ✕-fill animation
  startFill(r);

  // Update revealed cells just below the new row — they may now show "?"
  if (r > 0) updateRevealedNearRow(r - 1);

  updateActiveCount();
  autoClearIfOverflow();
}

// ── Auto-clear bottom clearable row when > 4 clearable rows accumulate ────────
function isRowClearable(r) {
  if (rush.rowStatus[r] !== 'active') return false;
  if (rush.rowMines[r].size === 0) {
    for (let c = 0; c < rush.cols; c++)
      if (!rush.revealed[r][c]) return false;
    return true;
  }
  return [...rush.rowMines[r]].every(c => rush.flagged[r][c] === 1);
}

function autoClearIfOverflow() {
  const clearable = [];
  for (let r = 0; r < rush.numRows; r++)
    if (isRowClearable(r)) clearable.push(r);
  if (clearable.length > 4)
    clearRow(clearable[0]);  // clearable[0] is the bottom-most (lowest index)
}

// ── Spacer helper (keeps all rows aligned with button-bearing rows) ───────────
function makeSpacer() {
  const s = document.createElement('div');
  s.className = 'rush-row-spacer';
  return s;
}

// ── Hint mark: shown on mine-free rows before all cells are revealed ─────────
function makeRushHintMark() {
  const d = document.createElement('div');
  d.className = 'rush-row-hint';
  d.textContent = '?';
  return d;
}

// ── Clear-button helper ───────────────────────────────────────────────────────
function makeRushClearBtn(r, title) {
  const btn = document.createElement('button');
  btn.className   = 'rush-clear-row-btn';
  btn.title       = title || 'Click to clear row';
  btn.textContent = '✓';
  btn.addEventListener('click', () => clearRow(r));
  return btn;
}

// ── Promote spacers → buttons when a mine-free row is fully revealed ──────────
function checkEmptyRowButtons(r) {
  if (rush.rowStatus[r] !== 'active') return;
  if (rush.rowMines[r].size !== 0) return;

  // Only show buttons if every cell has been revealed
  for (let c = 0; c < rush.cols; c++)
    if (!rush.revealed[r][c]) return;

  const div = rowEl(r);
  if (!div) return;

  const isReplaceable = el => el?.classList?.contains('rush-row-spacer') || el?.classList?.contains('rush-row-hint');
  if (isReplaceable(div.firstChild))
    div.replaceChild(makeRushClearBtn(r, 'No mines — click to clear row'), div.firstChild);
  if (isReplaceable(div.lastChild))
    div.replaceChild(makeRushClearBtn(r, 'No mines — click to clear row'), div.lastChild);
}

// Check all active mine-free rows (called after BFS may have revealed many cells)
function checkAllEmptyRowButtons() {
  for (let r = 0; r < rush.numRows; r++)
    checkEmptyRowButtons(r);
}

// ── Build a row DOM element and prepend it ────────────────────────────────────
function prependRowDOM(r) {
  const div = document.createElement('div');
  div.className   = 'rush-row incoming';
  div.dataset.row = r;

  const grid = document.createElement('div');
  grid.className  = 'rush-cells';

  for (let c = 0; c < rush.cols; c++) {
    const cell = document.createElement('div');
    cell.className  = 'cell rush-incoming-cell';
    cell.dataset.r  = r;
    cell.dataset.c  = c;
    grid.appendChild(cell);
  }

  // Spacers keep every row at the same width as rows with buttons
  div.appendChild(makeSpacer());
  div.appendChild(grid);
  div.appendChild(makeSpacer());

  const board = boardEl();
  board.insertBefore(div, board.firstChild);
}

// ── Fill animation: ✕ marks appear left-to-right ─────────────────────────────
function startFill(r) {
  const stepMs = Math.max(40, Math.floor(rush.curInterval / rush.cols));
  let col = 0;

  const id = setInterval(() => {
    if (rush.over || rush.rowStatus[r] !== 'incoming') {
      clearInterval(id);
      delete rush.fillIDs[r];
      return;
    }

    const el = cellEl(r, col);
    if (el) { el.textContent = '✕'; el.classList.add('rush-fill-mark'); }
    rush.rowFillCol[r] = ++col;

    if (col >= rush.cols) {
      clearInterval(id);
      delete rush.fillIDs[r];
      setTimeout(() => activateRow(r), 150);
    }
  }, stepMs);

  rush.fillIDs[r] = id;
}

// ── Activate row (incoming → active, cells become interactive) ────────────────
function activateRow(r) {
  if (rush.rowStatus[r] !== 'incoming') return;
  rush.rowStatus[r] = 'active';

  const div = rowEl(r);
  if (!div) return;
  div.className = 'rush-row active';
  div.innerHTML = '';

  // Inner cell grid
  const grid = document.createElement('div');
  grid.className = 'rush-cells';
  for (let c = 0; c < rush.cols; c++) {
    const cell = document.createElement('div');
    cell.className   = 'cell hidden';
    cell.dataset.r   = r;
    cell.dataset.c   = c;
    cell.addEventListener('click',       () => rushReveal(r, c));
    cell.addEventListener('contextmenu', e  => { e.preventDefault(); rushFlag(r, c); });
    grid.appendChild(cell);
  }

  // Mine-free rows show a '?' hint mark until all cells are revealed, then ✓ buttons.
  // Mine rows use invisible spacers (buttons appear when all mines are flagged).
  const side = () => rush.rowMines[r].size === 0 ? makeRushHintMark() : makeSpacer();
  div.appendChild(side());
  div.appendChild(grid);
  div.appendChild(side());

  updateActiveCount();
  checkOverflow();
  checkMinRows();
  updateSafetyNet();
}

// ── Render a single cell ──────────────────────────────────────────────────────
function renderCell(r, c, isDetonated = false) {
  const el  = cellEl(r, c);
  if (!el) return;
  const val = rush.board[r][c];
  const f   = rush.flagged[r][c];

  el.className  = 'cell';
  el.style.color = '';

  if (!rush.revealed[r][c]) {
    if (f === 1)      { el.classList.add('flagged');  el.textContent = '🚩'; }
    else if (f === 2) { el.classList.add('question'); el.textContent = '❓'; }
    else              { el.classList.add('hidden');   el.textContent = ''; }
    return;
  }

  el.classList.add('revealed');
  if (val === -1) {
    el.classList.add(isDetonated ? 'mine-detonated' : 'mine');
    el.textContent = '💣';
  } else if (val === 0) {
    el.textContent = '';
  } else {
    const disp = getCellDisplay(r, c);
    if (disp) {
      el.textContent = disp.text;
      el.style.color = disp.color;
      if (disp.text === '?') el.classList.add('rush-stale');
    }
  }
}

// ── Reveal (BFS flood-fill, stops at active-row boundary) ────────────────────
function rushReveal(r, c) {
  if (rush.over) return;
  if (rush.rowStatus[r] !== 'active') return;
  if (rush.flagged[r][c] === 1) return;
  if (rush.revealed[r][c]) {
    // Re-click a stale '?' cell to refresh its count
    const disp = getCellDisplay(r, c);
    if (disp && disp.text === '?') {
      rush.board[r][c] = neighborMineCount(r, c);
      rush.cellCountedAt[r][c] = rush.numRows;
      renderCell(r, c);
    }
    return;
  }

  if (!rush.started) startGame();

  if (rush.board[r][c] === -1) {
    rushBoom(r, c);
    return;
  }

  // BFS
  const queue = [[r, c]];
  while (queue.length) {
    const [cr, cc] = queue.shift();
    if (rush.revealed[cr][cc]) continue;
    if (rush.rowStatus[cr] !== 'active') continue;
    rush.revealed[cr][cc] = true;
    renderCell(cr, cc);
    if (rush.board[cr][cc] === 0) {
      rushNbs(cr, cc).forEach(([nr, nc]) => {
        if (!rush.revealed[nr][nc] && rush.flagged[nr][nc] !== 1)
          queue.push([nr, nc]);
      });
    }
  }

  checkAllEmptyRowButtons();
  updateSafetyNet();
  checkBoardSolved();
}

// ── Flag ──────────────────────────────────────────────────────────────────────
function rushFlag(r, c) {
  if (rush.over) return;
  if (rush.rowStatus[r] !== 'active') return;
  if (rush.revealed[r][c]) return;

  if (!rush.started) startGame();

  const prev = rush.flagged[r][c];
  rush.flagged[r][c] = (prev + 1) % 3;
  renderCell(r, c);

  recomputeScore();
  checkMineRowButtons(r);
  updateSafetyNet();
  checkBoardSolved();
}

// ── Board solved: if every active row is clearable, bring the next row in now ─
function checkBoardSolved() {
  if (!rush.started || rush.over) return;
  let hasActive = false;
  for (let r = 0; r < rush.numRows; r++) {
    if (rush.rowStatus[r] === 'active') {
      hasActive = true;
      if (!isRowClearable(r)) return;
    }
  }
  if (!hasActive) return;
  addRow();
  scheduleNextRow(); // reset the timer so the next row doesn't arrive too soon
}

// ── Score: count correctly-flagged mines across all active rows ───────────────
function recomputeScore() {
  let total = 0;
  for (let r = 0; r < rush.numRows; r++) {
    if (rush.rowStatus[r] === 'cleared') continue;
    for (let c = 0; c < rush.cols; c++)
      if (rush.board[r][c] === -1 && rush.flagged[r][c] === 1) total++;
  }
  rush.score = total;
  updateSpeed();
}

// ── Promote/demote clear button on mine rows based on flagging state ──────────
function checkMineRowButtons(r) {
  if (rush.rowStatus[r] !== 'active') return;
  if (rush.rowMines[r].size === 0) return;  // mine-free rows handled by checkEmptyRowButtons

  const div = rowEl(r);
  if (!div) return;

  const allFlagged = [...rush.rowMines[r]].every(c => rush.flagged[r][c] === 1);

  if (allFlagged) {
    if (div.firstChild?.classList?.contains('rush-row-spacer'))
      div.replaceChild(makeRushClearBtn(r, 'All mines flagged — click to clear row'), div.firstChild);
    if (div.lastChild?.classList?.contains('rush-row-spacer'))
      div.replaceChild(makeRushClearBtn(r, 'All mines flagged — click to clear row'), div.lastChild);
  } else {
    if (div.firstChild?.classList?.contains('rush-clear-row-btn'))
      div.replaceChild(makeSpacer(), div.firstChild);
    if (div.lastChild?.classList?.contains('rush-clear-row-btn'))
      div.replaceChild(makeSpacer(), div.lastChild);
  }
}

// ── Salvage: earned every 20 rows cleared; removes bottom exploded-mine row ───
function rowHasExplodedMine(r) {
  for (let c = 0; c < rush.cols; c++)
    if (rush.board[r][c] === -1 && rush.revealed[r][c]) return true;
  return false;
}

function makeSalvageBtn(r) {
  const btn = document.createElement('button');
  btn.className   = 'rush-salvage-btn';
  btn.title       = 'Use salvage token — remove this exploded row';
  btn.textContent = '🔥';
  btn.addEventListener('click', () => salvageRow(r));
  return btn;
}

function salvageRow(r) {
  if (rush.salvageTokens <= 0) return;
  rush.salvageTokens--;
  updateSalvageDisplay();
  clearRow(r);
}

function updateSalvageDisplay() {
  const ind = document.getElementById('rush-salvage-indicator');
  const cnt = document.getElementById('rush-salvage-tokens');
  if (!ind) return;
  if (rush.salvageTokens > 0) {
    ind.style.display = 'block';
    if (cnt) cnt.textContent = rush.salvageTokens;
  } else {
    ind.style.display = 'none';
  }
}

function checkSalvageButton() {
  // Remove any existing salvage buttons (replace with spacers)
  document.querySelectorAll('.rush-salvage-btn').forEach(btn => {
    if (btn.parentElement) btn.parentElement.replaceChild(makeSpacer(), btn);
  });

  if (rush.salvageTokens <= 0) return;

  // Find the lowest active row that has an exploded mine
  for (let r = 0; r < rush.numRows; r++) {
    if (rush.rowStatus[r] === 'active' && rowHasExplodedMine(r)) {
      const div = rowEl(r);
      if (!div) return;
      if (div.firstChild?.classList?.contains('rush-row-spacer'))
        div.replaceChild(makeSalvageBtn(r), div.firstChild);
      if (div.lastChild?.classList?.contains('rush-row-spacer'))
        div.replaceChild(makeSalvageBtn(r), div.lastChild);
      return;  // only the bottom-most qualifying row
    }
  }
}

function clearRow(r) {
  if (rush.rowStatus[r] !== 'active') return;

  // Count flagged mines in this row before clearing
  for (const c of rush.rowMines[r])
    if (rush.flagged[r][c] === 1) rush.clearedMines++;
  const minesEl = document.getElementById('rush-score');
  if (minesEl) minesEl.textContent = String(rush.clearedMines).padStart(3, '0');
  updateSpeed();

  rush.rowStatus[r] = 'cleared';
  rush.rowsCleared++;
  const el = document.getElementById('rush-rows-cleared');
  if (el) el.textContent = rush.rowsCleared;

  // Grant a salvage token every 20 rows cleared
  if (rush.rowsCleared % 20 === 0) {
    rush.salvageTokens++;
    updateSalvageDisplay();
    flashMessage('🔥 Salvage token!', false);
  }

  const div = rowEl(r);
  if (div) {
    div.classList.add('rush-row-cleared');
    setTimeout(() => div.remove(), CLEAR_DELAY);
  }
  // Recalculate numbers for cells adjacent to this row
  updateRevealedNearRow(r);
  updateActiveCount();
  checkMinRows();
  checkSalvageButton();
}

// ── Mine hit ──────────────────────────────────────────────────────────────────
function rushBoom(r, c) {
  rush.revealed[r][c] = true;
  renderCell(r, c, true);
  rowEl(r)?.classList.add('exploded');

  if (rush.noSafeMove) {
    flashMessage('No penalty!', false);
  } else {
    flashMessage('+2 rows!', true);
    addRow();
    addRow();
  }

  updateActiveCount();
  checkOverflow();
  updateSafetyNet();
  checkSalvageButton();
}

function flashMessage(text, isWarn) {
  const el = document.getElementById('rush-penalty');
  if (!el) return;
  el.textContent  = text;
  el.style.color  = isWarn ? '#e94560' : '#53d8fb';
  el.style.opacity = '1';
  setTimeout(() => { el.style.opacity = '0'; }, 1600);
}

// ── Safety net: detect if any guaranteed-safe reveal exists ──────────────────
function updateSafetyNet() {
  rush.noSafeMove = !hasSafeMove();
  const el = document.getElementById('rush-safe-indicator');
  if (el) el.style.display = rush.noSafeMove ? 'block' : 'none';
}

function hasSafeMove() {
  for (let r = 0; r < rush.numRows; r++) {
    if (rush.rowStatus[r] !== 'active') continue;
    for (let c = 0; c < rush.cols; c++) {
      // An unrevealed zero is always safe
      if (!rush.revealed[r][c] && rush.board[r][c] === 0 && rush.flagged[r][c] !== 1)
        return true;
      // A revealed number whose flag count matches — remaining hidden are safe
      if (rush.revealed[r][c] && rush.board[r][c] > 0) {
        const nbs     = rushNbs(r, c).filter(([nr, nc]) => rush.rowStatus[nr] === 'active');
        const flagged = nbs.filter(([nr, nc]) => rush.flagged[nr][nc] === 1).length;
        const hidden  = nbs.filter(([nr, nc]) => !rush.revealed[nr][nc] && rush.flagged[nr][nc] !== 1);
        if (flagged === rush.board[r][c] && hidden.length > 0) return true;
      }
    }
  }
  return false;
}

// ── Overflow: too many active rows = game over ────────────────────────────────
function checkOverflow() {
  if (activeCount() <= rush.maxActive) return;

  // Last-ditch: spend all salvage tokens on exploded-mine rows (bottom-first)
  for (let r = 0; r < rush.numRows && rush.salvageTokens > 0; r++) {
    if (rush.rowStatus[r] === 'active' && rowHasExplodedMine(r)) {
      rush.salvageTokens--;
      clearRow(r);
    }
  }

  // Then auto-clear every row that's already fully flagged / fully revealed
  for (let r = 0; r < rush.numRows; r++) {
    if (isRowClearable(r)) clearRow(r);
  }

  updateActiveCount();
  updateSalvageDisplay();
  checkSalvageButton();

  if (activeCount() > rush.maxActive) rushGameOver();
}

// ── Min rows: fewer than MIN_ROWS unfinished → add 4 immediately ─────────────
function checkMinRows() {
  if (!rush.over && unfinishedCount() < MIN_ROWS) {
    for (let i = 0; i < 4; i++) addRow();
  }
}

// ── Update active-row counter in UI ──────────────────────────────────────────
function updateActiveCount() {
  const el = document.getElementById('rush-active-rows');
  if (el) el.textContent = activeCount();
}

// ── Start game (on first interaction) ────────────────────────────────────────
function startGame() {
  rush.started = true;
  startRushTimer();
  scheduleNextRow();
}

// ── Game Over ─────────────────────────────────────────────────────────────────
function rushGameOver() {
  if (rush.over) return;
  rush.over = true;
  stopRushTimer();
  clearTimeout(rush.rowTimerID);
  for (const id of Object.values(rush.fillIDs)) clearInterval(id);

  // Reveal all mine positions in active rows
  for (let r = 0; r < rush.numRows; r++) {
    if (rush.rowStatus[r] !== 'active') continue;
    for (const c of rush.rowMines[r]) {
      if (!rush.revealed[r][c]) {
        rush.revealed[r][c] = true;
        renderCell(r, c);
      }
    }
  }

  showRushOverlay();
}

// ── Overlay ───────────────────────────────────────────────────────────────────
function showRushOverlay() {
  let el = document.getElementById('rush-overlay');
  if (!el) {
    el = document.createElement('div');
    el.id = 'rush-overlay';
    document.getElementById('rush-board-wrap').appendChild(el);
  }
  el.className = 'overlay loss';

  const username    = document.getElementById('rush-board').dataset.username || '';
  const timeStr     = fmtTime(rush.elapsed);
  const finalScore  = rush.elapsed + rush.clearedMines * 5;

  let scoreForm;
  if (username) {
    scoreForm = `<div id="rush-score-msg" style="font-size:0.9rem">Saving score…</div>`;
  } else {
    scoreForm = `
      <div class="overlay-score-form">
        <input id="rush-player-name" type="text" maxlength="32"
               placeholder="Enter your name" autocomplete="off" />
        <button onclick="submitRushScore()">Save Score</button>
      </div>
      <div id="rush-score-msg" style="font-size:0.85rem;min-height:1.2em"></div>
      <a class="overlay-lb-link" href="/auth/login">Sign in to skip this step</a>
    `;
  }

  el.innerHTML = `
    <span>💥 Game Over</span>
    <span style="font-size:1rem">
      Mines Cleared: <strong>${rush.clearedMines}</strong>
      &nbsp;|&nbsp;
      Rows Cleared: <strong>${rush.rowsCleared}</strong>
      &nbsp;|&nbsp;
      Time: <strong>${timeStr}</strong>
    </span>
    <span style="font-size:1.1rem;color:var(--accent2)">
      Score: <strong>${finalScore}</strong>
      <span style="font-size:0.8rem;opacity:0.7">(${timeStr} + ${rush.clearedMines}×5)</span>
    </span>
    ${scoreForm}
    <button onclick="initRush('${rush.mode}')">Play Again</button>
  `;
  el.style.display = 'flex';

  if (username) {
    submitRushScore(username);
  } else {
    setTimeout(() => document.getElementById('rush-player-name')?.focus(), 50);
  }
}

async function submitRushScore(autoName = null) {
  const msgEl  = document.getElementById('rush-score-msg');
  const nameEl = document.getElementById('rush-player-name');
  const name   = autoName || nameEl?.value.trim();

  if (!name) { if (msgEl) msgEl.textContent = '⚠️ Please enter your name.'; return; }

  try {
    const res = await fetch('/api/rush-scores', {
      method:  'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        name,
        rush_mode:     rush.mode,
        score:         rush.elapsed + rush.clearedMines * 5,
        cleared_mines: rush.clearedMines,
        time_secs:     rush.elapsed,
        cols:          rush.cols,
      }),
    });
    if (res.ok) {
      if (msgEl) msgEl.textContent = `✅ Score saved for ${name}!`;
      if (nameEl) nameEl.disabled = true;
      const btn = document.querySelector('#rush-overlay .overlay-score-form button');
      if (btn) btn.disabled = true;
      loadRushLeaderboard(rush.mode);
    } else {
      const err = await res.json().catch(() => ({}));
      if (msgEl) msgEl.textContent = `❌ ${err.detail || 'Could not save score.'}`;
    }
  } catch {
    if (msgEl) msgEl.textContent = '❌ Network error.';
  }
}

// ── Leaderboard ───────────────────────────────────────────────────────────────
async function loadRushLeaderboard(mode) {
  const wrap = document.getElementById('rush-lb-content');
  if (!wrap) return;
  wrap.innerHTML = '<div class="lb-loading">Loading…</div>';

  try {
    const res  = await fetch(`/api/rush-scores/${mode}`);
    const rows = await res.json();

    if (!rows.length) {
      wrap.innerHTML = '<div class="lb-empty">No scores yet — be the first!</div>';
      return;
    }

    const medals = ['🥇','🥈','🥉'];
    const trs = rows.map((s, i) => {
      const cls  = i < 3 ? `top-${i+1}` : '';
      const rank = medals[i] || `#${i+1}`;
      const time = fmtTime(s.time_secs);
      return `<tr class="${cls}">
        <td class="lb-rank">${rank}</td>
        <td class="lb-name">${escHtml(s.name)}</td>
        <td class="lb-score">${s.score}</td>
        <td class="lb-score">${s.cleared_mines ?? '—'} mines</td>
        <td class="lb-time">${time}</td>
        <td class="lb-date">${s.created_at}</td>
      </tr>`;
    }).join('');

    wrap.innerHTML = `
      <div class="lb-table-wrap">
        <table class="lb-table">
          <thead><tr>
            <th>#</th><th>Name</th><th>Score</th><th>Mines</th><th>Time</th><th>Date</th>
          </tr></thead>
          <tbody>${trs}</tbody>
        </table>
      </div>`;
  } catch {
    wrap.innerHTML = '<div class="lb-empty">Could not load scores.</div>';
  }
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Build initial board (no animation) ───────────────────────────────────────
function buildInitialBoard() {
  // Add INITIAL_ROWS rows to arrays without animation
  for (let i = 0; i < INITIAL_ROWS; i++) {
    const r = rush.numRows;
    rush.board.push(new Array(rush.cols).fill(0));
    rush.revealed.push(new Array(rush.cols).fill(false));
    rush.flagged.push(new Array(rush.cols).fill(0));
    rush.rowStatus.push('active');
    rush.rowFillCol.push(rush.cols);
    rush.rowIsInitial.push(true);
    rush.cellCountedAt.push(new Array(rush.cols).fill(INITIAL_ROWS));

    const mines = new Set();
    for (let c = 0; c < rush.cols; c++)
      if (Math.random() < rush.density) mines.add(c);
    rush.rowMines.push(mines);
    for (const c of mines) rush.board[r][c] = -1;

    rush.numRows++;
  }

  // Compute all neighbor counts now that all mines are placed
  for (let r = 0; r < rush.numRows; r++)
    for (let c = 0; c < rush.cols; c++)
      if (rush.board[r][c] !== -1)
        rush.board[r][c] = neighborMineCount(r, c);

  // Render DOM: highest index first (newest = top), lowest last (oldest = bottom)
  const board = boardEl();
  board.innerHTML = '';
  board.style.setProperty('--cols', rush.cols);
  for (let r = rush.numRows - 1; r >= 0; r--) {
    const div = document.createElement('div');
    div.className   = 'rush-row active';
    div.dataset.row = r;

    const grid = document.createElement('div');
    grid.className  = 'rush-cells';
    for (let c = 0; c < rush.cols; c++) {
      const cell = document.createElement('div');
      cell.className   = 'cell hidden';
      cell.dataset.r   = r;
      cell.dataset.c   = c;
      cell.addEventListener('click',       () => rushReveal(r, c));
      cell.addEventListener('contextmenu', e  => { e.preventDefault(); rushFlag(r, c); });
      grid.appendChild(cell);
    }

    div.appendChild(makeSpacer());
    div.appendChild(grid);
    div.appendChild(makeSpacer());

    board.appendChild(div);
  }
}

// ── Init / Reset ─────────────────────────────────────────────────────────────
function initRush(mode) {
  // Stop any running timers from previous game
  if (rush.timerID)    clearInterval(rush.timerID);
  if (rush.rowTimerID) clearTimeout(rush.rowTimerID);
  if (rush.fillIDs) for (const id of Object.values(rush.fillIDs)) clearInterval(id);

  rush = freshRush(mode);

  // Update UI
  document.getElementById('rush-board').dataset.mode = mode;
  document.getElementById('rush-timer').textContent = '0:00';
  document.getElementById('rush-score').textContent = '  0';
  document.getElementById('rush-rows-cleared').textContent = '0';
  document.getElementById('rush-speed').textContent = '×1';
  document.getElementById('rush-max-rows').textContent = RUSH_CFGS[mode].maxActive;
  updateSalvageDisplay();

  const overlay = document.getElementById('rush-overlay');
  if (overlay) overlay.style.display = 'none';

  const safeEl = document.getElementById('rush-safe-indicator');
  if (safeEl) safeEl.style.display = 'none';

  boardEl().style.setProperty('--cols', rush.cols);
  boardEl().style.setProperty('--rush-rows', rush.maxActive);
  buildInitialBoard();
  updateActiveCount();
  updateSafetyNet();
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const boardEl = document.getElementById('rush-board');
  if (!boardEl) return;

  // Mode buttons
  document.querySelectorAll('.rush-mode-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.rush-mode-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      initRush(btn.dataset.mode);
    });
  });

  // Reset button
  document.getElementById('rush-reset-btn')
    .addEventListener('click', () => initRush(rush.mode));

  // Leaderboard tabs
  document.querySelectorAll('.rush-lb-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.rush-lb-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      loadRushLeaderboard(tab.dataset.mode);
    });
  });

  // Start on easy
  initRush('easy');
  loadRushLeaderboard('easy');
});

// Expose functions needed by inline onclick handlers in overlay
window.initRush = initRush;
window.submitRushScore = submitRushScore;

})(); // end IIFE
