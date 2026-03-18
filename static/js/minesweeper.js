/**
 * Minesweeper.org — Game Engine
 * Pure vanilla JS, zero dependencies.
 */

// ── Touch helpers ─────────────────────────────────────────────────────────────
// On iOS Safari there is no contextmenu event for touch; we simulate it with a
// long-press (touchstart held ≥ 500 ms). Calling preventDefault() on touchstart
// suppresses the browser's text-selection callout AND the synthetic click event
// that would otherwise fire after the touch, so mouse listeners still work on
// desktop while touch devices get their own path.
const LONG_PRESS_MS = 500;

function addTouchHandlers(el, onTap, onLongPress) {
  let timer = null;
  let moved = false;
  let startX, startY;

  el.addEventListener('touchstart', e => {
    e.preventDefault();
    moved  = false;
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
    timer  = setTimeout(() => { timer = null; if (!moved) onLongPress(); }, LONG_PRESS_MS);
  }, { passive: false });

  el.addEventListener('touchmove', e => {
    if (!timer) return;
    if (Math.abs(e.touches[0].clientX - startX) > 10 ||
        Math.abs(e.touches[0].clientY - startY) > 10) {
      moved = true; clearTimeout(timer); timer = null;
    }
  }, { passive: true });

  el.addEventListener('touchend', e => {
    e.preventDefault();
    if (timer) { clearTimeout(timer); timer = null; if (!moved) onTap(); }
  }, { passive: false });

  el.addEventListener('touchcancel', () => { clearTimeout(timer); timer = null; });
}

// ── Flag mode (mobile toggle) ─────────────────────────────────────────────────
let flagMode = false;

function toggleFlagMode() {
  flagMode = !flagMode;
  const btn = document.getElementById('flag-mode-btn');
  if (btn) btn.classList.toggle('active', flagMode);
}

function clearFlagMode() {
  flagMode = false;
  const btn = document.getElementById('flag-mode-btn');
  if (btn) btn.classList.remove('active');
}

// ── State ────────────────────────────────────────────────────────────────────
let state = {};

function freshState(rows, cols, mines, noGuess = false, chording = true) {
  return {
    rows, cols, mines,
    board:      Array.from({length: rows}, () => Array(cols).fill(0)),
    revealed:   Array.from({length: rows}, () => Array(cols).fill(false)),
    flagged:    Array.from({length: rows}, () => Array(cols).fill(0)),
    mineSet:    new Set(),
    minesLeft:  mines,
    started:    false,
    over:       false,
    won:        false,
    elapsed:    0,
    timerID:    null,
    startTime:  null,   // performance.now() at first click
    timeMs:     null,   // precise elapsed ms at game end
    noGuess,
    chording,
    leftClicks:  0,
    rightClicks: 0,
    chordClicks: 0,
    boardHash:   null,
    bbbv:        null,
  };
}

// ── Mine Placement (safe first click) ────────────────────────────────────────
function placeMines(rows, cols, mines, safeR, safeC) {
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
  return {mineSet, board};
}

// ── No-Guess Solver ───────────────────────────────────────────────────────────
// Returns true if the board can be fully solved using constraint propagation
// (no random guessing required). Uses single-cell and subset deductions.
function isSolvable(rows, cols, mineSet, board, startR, startC) {
  const n = rows * cols;
  const revealed  = new Uint8Array(n);
  const knownMine = new Uint8Array(n);

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

    // Subset deduction: if constraint A ⊆ constraint B, derive (B − A)
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

function placeMinesNoGuess(rows, cols, mines, safeR, safeC) {
  for (let attempt = 0; attempt < 500; attempt++) {
    const result = placeMines(rows, cols, mines, safeR, safeC);
    if (isSolvable(rows, cols, result.mineSet, result.board, safeR, safeC))
      return result;
  }
  return placeMines(rows, cols, mines, safeR, safeC); // fallback
}

// ── Board Hash ────────────────────────────────────────────────────────────────
// Encodes mine positions as a base64 bit-array. Fully reproducible: same mine
// set → same hash. To reconstruct, decode base64 and read bit i for cell i.
function calcBoardHash(rows, cols, mineSet) {
  const bytes = new Uint8Array(Math.ceil(rows * cols / 8));
  for (const idx of mineSet) bytes[idx >> 3] |= (1 << (idx & 7));
  let bin = '';
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin);
}

// ── 3BV (Bechtel's Board Benchmark Value) ─────────────────────────────────────
// Each opening region (contiguous blank cells + their numbered borders) = 1 click.
// Each numbered cell not adjacent to any opening = 1 click.
function calc3BV(board, rows, cols, mineSet) {
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

// ── Helpers ──────────────────────────────────────────────────────────────────
function neighbors(r, c, rows, cols) {
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

function cellEl(r, c) {
  return document.querySelector(`[data-r="${r}"][data-c="${c}"]`);
}

// ── Timer ─────────────────────────────────────────────────────────────────────
function startTimer() {
  if (state.timerID) return;
  state.timerID = setInterval(() => {
    state.elapsed = Math.min(state.elapsed + 1, 999);
    document.getElementById('timer').textContent =
      String(state.elapsed).padStart(3, '0');
  }, 1000);
}

function stopTimer() {
  clearInterval(state.timerID);
  state.timerID = null;
}

// ── Reveal Logic ─────────────────────────────────────────────────────────────
function reveal(r, c) {
  if (state.over || state.revealed[r][c] || state.flagged[r][c] === 1) return;

  // First click — place mines now (guarantees safe first click)
  if (!state.started) {
    const placer = state.noGuess ? placeMinesNoGuess : placeMines;
    const {mineSet, board} = placer(state.rows, state.cols, state.mines, r, c);
    state.mineSet    = mineSet;
    state.board      = board;
    state.started    = true;
    state.startTime  = performance.now();
    state.boardHash  = calcBoardHash(state.rows, state.cols, mineSet);
    state.bbbv       = calc3BV(board, state.rows, state.cols, mineSet);
    startTimer();
  }

  if (state.board[r][c] === -1) {
    boom(r, c);
    return;
  }

  // BFS flood fill for empty cells
  const queue = [[r, c]];
  while (queue.length) {
    const [cr, cc] = queue.shift();
    if (state.revealed[cr][cc]) continue;
    state.revealed[cr][cc] = true;
    renderCell(cr, cc);
    if (state.board[cr][cc] === 0) {
      neighbors(cr, cc, state.rows, state.cols).forEach(([nr, nc]) => {
        if (!state.revealed[nr][nc] && !state.flagged[nr][nc])
          queue.push([nr, nc]);
      });
    }
  }

  checkWin();
}

// ── Chord (middle-click / double-click) ──────────────────────────────────────
function chord(r, c) {
  if (!state.chording || !state.revealed[r][c] || state.board[r][c] <= 0) return;
  const nb    = neighbors(r, c, state.rows, state.cols);
  const flags = nb.filter(([nr, nc]) => state.flagged[nr][nc] === 1).length;
  if (flags === state.board[r][c])
    nb.forEach(([nr, nc]) => reveal(nr, nc));
}

// ── Flag (cycles: none → flag → question → none) ──────────────────────────────
function flag(r, c) {
  if (state.over || state.revealed[r][c]) return;
  const cur = state.flagged[r][c];   // 0 = none, 1 = flag, 2 = question
  const next = (cur + 1) % 3;
  state.flagged[r][c] = next;
  // Only decrement mine count when placing a flag, increment when removing one
  if (cur === 0 && next === 1) state.minesLeft--;
  if (cur === 1 && next === 2) state.minesLeft++;
  document.getElementById('mines-left').textContent =
    String(state.minesLeft).padStart(3, '0');
  renderCell(r, c);
}

// ── Win / Loss ────────────────────────────────────────────────────────────────
function boom(r, c) {
  state.over   = true;
  state.timeMs = state.startTime ? Math.round(performance.now() - state.startTime) : null;
  stopTimer();
  // Reveal all mines
  for (const idx of state.mineSet) {
    const mr = Math.floor(idx / state.cols), mc = idx % state.cols;
    state.revealed[mr][mc] = true;
    renderCell(mr, mc, mr === r && mc === c);
  }
  document.getElementById('reset-btn').textContent = '😵';
  showOverlay('💥 Game Over', false);
}

function checkWin() {
  const unrevealed = state.rows * state.cols -
    state.revealed.flat().filter(Boolean).length;
  if (unrevealed === state.mines) {
    state.over   = true;
    state.won    = true;
    state.timeMs = state.startTime ? Math.round(performance.now() - state.startTime) : null;
    stopTimer();
    document.getElementById('reset-btn').textContent = '😎';
    // Auto-flag remaining mines
    for (const idx of state.mineSet) {
      const mr = Math.floor(idx / state.cols), mc = idx % state.cols;
      if (!state.flagged[mr][mc]) {
        state.flagged[mr][mc] = true;
        renderCell(mr, mc);
      }
    }
    document.getElementById('mines-left').textContent = '000';
    showOverlay(`🎉 You Won! — ${state.elapsed}s`, true);

    // Quest hooks
    if (typeof window.questsHook === 'function') {
      const mode = document.getElementById('board')?.dataset.mode;
      if (mode === 'beginner')     window.questsHook('easy_won');
      if (mode === 'intermediate') window.questsHook('intermediate_won');
    }
  }
}

// ── Overlay ──────────────────────────────────────────────────────────────────
function showOverlay(msg, won) {
  let el = document.getElementById('game-overlay');
  if (!el) {
    el = document.createElement('div');
    el.id = 'game-overlay';
    document.getElementById('board').appendChild(el);
  }
  el.className = won ? 'overlay win' : 'overlay loss';

  const board    = document.getElementById('board');
  const username = board.dataset.username || '';
  const mode     = board.dataset.mode || 'beginner';

  let scoreForm = '';
  if (won) {
    if (username) {
      // Logged-in: auto-submit immediately, show a confirmation
      scoreForm = `<div id="score-msg" style="font-size:0.9rem">Saving score…</div>`;
    } else {
      scoreForm = `
        <div class="overlay-score-form">
          <input id="player-name" type="text" maxlength="32"
                 placeholder="Enter your name" autocomplete="off" />
          <button onclick="submitScore()">Save Score</button>
        </div>
        <div id="score-msg" style="font-size:0.85rem;min-height:1.2em"></div>
        <a class="overlay-lb-link" href="/auth/login">Sign in with Google to skip this step</a>
      `;
    }
  }

  const ngParam = state.noGuess ? '&no_guess=true' : '';
  el.innerHTML = `
    <span>${msg}</span>
    ${state.noGuess ? '<span style="font-size:0.75rem;opacity:0.7">⚡ No-Guess mode</span>' : ''}
    ${scoreForm}
    <button onclick="resetGame()">Play Again</button>
    <a class="overlay-lb-link" href="/leaderboard?mode=${mode}${ngParam}">View Leaderboard →</a>
  `;
  el.style.display = 'flex';

  if (won && username) {
    submitScore(username);
  } else if (won) {
    setTimeout(() => document.getElementById('player-name')?.focus(), 50);
  }
}

async function submitScore(autoName = null) {
  const board    = document.getElementById('board');
  const msgEl    = document.getElementById('score-msg');
  const nameEl   = document.getElementById('player-name');
  const name     = autoName || nameEl?.value.trim();

  if (!name) { if (msgEl) msgEl.textContent = '⚠️ Please enter your name.'; return; }

  const payload = {
    name,
    mode:         board.dataset.mode,
    time_secs:    state.elapsed,
    time_ms:      state.timeMs,
    rows:         state.rows,
    cols:         state.cols,
    mines:        state.mines,
    no_guess:     state.noGuess,
    board_hash:   state.boardHash,
    bbbv:         state.bbbv,
    left_clicks:  state.leftClicks,
    right_clicks: state.rightClicks,
    chord_clicks: state.chordClicks,
  };

  try {
    const res = await fetch('/api/scores', {
      method:  'POST',
      headers: {'Content-Type': 'application/json'},
      body:    JSON.stringify(payload),
    });
    if (res.ok) {
      if (msgEl) msgEl.textContent = `✅ Score saved for ${name}!`;
      if (nameEl) nameEl.disabled = true;
      const saveBtn = document.querySelector('.overlay-score-form button');
      if (saveBtn) saveBtn.disabled = true;
    } else {
      const err = await res.json();
      if (msgEl) msgEl.textContent = `❌ ${err.detail || 'Could not save score.'}`;
    }
  } catch {
    if (msgEl) msgEl.textContent = '❌ Network error. Score not saved.';
  }
}

// ── Render a single cell ─────────────────────────────────────────────────────
const NUM_COLORS_DARK    = ['','#1976D2','#388E3C','#D32F2F','#7B1FA2',
                             '#F57F17','#00838F','#212121','#757575'];
const NUM_COLORS_CLASSIC = ['','#0000ff','#008000','#ff0000','#000080',
                             '#800000','#008080','#000000','#808080'];
function getNumColors() {
  return document.documentElement.dataset.skin === 'classic'
    ? NUM_COLORS_CLASSIC : NUM_COLORS_DARK;
}

function renderCell(r, c, isDetonated = false) {
  const el  = cellEl(r, c);
  const val = state.board[r][c];
  const f   = state.flagged[r][c];

  el.className = 'cell';

  if (!state.revealed[r][c]) {
    if (f === 1) {
      el.classList.add('flagged');
      el.textContent = '🚩';
    } else if (f === 2) {
      el.classList.add('question');
      el.textContent = '❓';
    } else {
      el.classList.add('hidden');
      el.textContent = '';
    }
    return;
  }

  el.classList.add('revealed');
  if (val === -1) {
    el.classList.add(isDetonated ? 'mine-detonated' : 'mine');
    el.textContent = '💣';
  } else if (val === 0) {
    el.textContent = '';
  } else {
    el.textContent = val;
    el.style.color = getNumColors()[val];
  }
}

// ── Build Board DOM ───────────────────────────────────────────────────────────
function buildBoard(rows, cols) {
  const boardEl = document.getElementById('board');
  boardEl.innerHTML = '';
  boardEl.style.setProperty('--cols', cols);

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const cell = document.createElement('div');
      cell.className = 'cell hidden';
      cell.dataset.r = r;
      cell.dataset.c = c;

      cell.addEventListener('click',       () => { if (flagMode) { state.rightClicks++; flag(r, c); } else { state.leftClicks++; reveal(r, c); } });
      cell.addEventListener('contextmenu', e  => { e.preventDefault(); state.rightClicks++; flag(r, c); });
      cell.addEventListener('dblclick',    () => { state.chordClicks++; chord(r, c); });
      addTouchHandlers(cell,
        () => { if (flagMode) { state.rightClicks++; flag(r, c); } else { state.leftClicks++; reveal(r, c); } },
        () => { state.rightClicks++; flag(r, c); }
      );

      boardEl.appendChild(cell);
    }
  }
}

// ── Init / Reset ─────────────────────────────────────────────────────────────
function initGame(rows, cols, mines, noGuess = false, chording = true) {
  stopTimer();
  clearFlagMode();
  state = freshState(rows, cols, mines, noGuess, chording);
  document.getElementById('timer').textContent      = '000';
  document.getElementById('mines-left').textContent = String(mines).padStart(3,'0');
  document.getElementById('reset-btn').textContent  = '🙂';
  buildBoard(rows, cols);
  updateNoGuessUI(noGuess);
}

function resetGame() {
  initGame(state.rows, state.cols, state.mines, state.noGuess, state.chording);
}

// ── No-Guess Toggle ───────────────────────────────────────────────────────────
function toggleNoGuess() {
  const newVal = !state.noGuess;
  localStorage.setItem('noGuess', newVal);
  initGame(state.rows, state.cols, state.mines, newVal, state.chording);
}

function updateNoGuessUI(active) {
  const btn = document.getElementById('noguess-toggle');
  if (btn) btn.classList.toggle('active', active);
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const board = document.getElementById('board');
  if (!board) return;

  // Don't run the solo game init on the duel, pvp, cylinder, toroid, or replay pages
  if (board.dataset.mode === 'duel' || board.dataset.mode === 'pvp' ||
      board.dataset.mode === 'replay' ||
      board.dataset.mode.startsWith('cylinder') ||
      board.dataset.mode.startsWith('toroid')) return;

  const rows    = parseInt(board.dataset.rows);
  const cols    = parseInt(board.dataset.cols);
  const mines   = parseInt(board.dataset.mines);
  const noGuess  = localStorage.getItem('noGuess')   === 'true';
  const chording = localStorage.getItem('chording') !== 'false';

  initGame(rows, cols, mines, noGuess, chording);

  document.getElementById('reset-btn')
    .addEventListener('click', resetGame);
});
