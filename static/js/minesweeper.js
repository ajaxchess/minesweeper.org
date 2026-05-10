/**
 * Minesweeper.org — Game Engine
 * Pure vanilla JS, zero dependencies.
 */

// ── Guest login reminder banner ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  const board = document.getElementById('board');
  if (!board || board.dataset.username) return; // not a game page or user is logged in
  if (sessionStorage.getItem('guest-banner-dismissed')) return;

  const loginHref = '/auth/login?next=' + encodeURIComponent(window.location.pathname + window.location.search);
  const banner = document.createElement('div');
  banner.id = 'guest-login-banner';
  const T = window.T || {};
  const pre  = T.guest_banner_pre  || '\u26a0\ufe0f You\u2019re not signed in \u2014';
  const link = T.auth_sign_in      || 'Sign In';
  const post = T.guest_banner_post || 'or your scores will vanish at midnight UTC.';
  banner.innerHTML =
    pre + ' <a href="' + loginHref + '">' + link + '</a> ' + post +
    '<button aria-label="Dismiss">\u00d7</button>';
  document.body.appendChild(banner);
  banner.querySelector('button').addEventListener('click', function () {
    banner.remove();
    sessionStorage.setItem('guest-banner-dismissed', '1');
    // If the iOS app banner is showing, drop it back to bottom
    var ios = document.getElementById('ios-app-banner');
    if (ios) ios.style.bottom = '0';
  });
});

// ── iOS app install banner (F94) ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  if (!document.getElementById('board')) return; // game pages only

  // Detect iPhone / iPad (including modern iPads that report MacIntel)
  var isIOS = /iPhone|iPad|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  if (!isIOS) return;

  // Honour 30-day dismissal
  var ts = localStorage.getItem('ios-app-banner-dismissed');
  if (ts && (Date.now() - parseInt(ts, 10)) < 30 * 24 * 60 * 60 * 1000) return;

  var banner = document.createElement('div');
  banner.id = 'ios-app-banner';
  banner.innerHTML =
    '\uD83D\uDCF1 <a href="https://apps.apple.com/us/app/minesweeper-org/id6761314113"'
    + ' target="_blank" rel="noopener">Download the free Minesweeper app</a>'
    + ' for iPhone &amp; iPad.'
    + '<button aria-label="Dismiss">\u00d7</button>';
  document.body.appendChild(banner);

  banner.querySelector('button').addEventListener('click', function () {
    banner.remove();
    localStorage.setItem('ios-app-banner-dismissed', String(Date.now()));
  });

  // Stack above the guest-login-banner if it is also visible
  requestAnimationFrame(function () {
    var guest = document.getElementById('guest-login-banner');
    if (guest) banner.style.bottom = guest.getBoundingClientRect().height + 'px';
  });
});

// ── Touch helpers ─────────────────────────────────────────────────────────────
// On iOS Safari there is no contextmenu event for touch; we simulate it with a
// long-press (touchstart held ≥ 500 ms). Calling preventDefault() on touchstart
// suppresses the browser's text-selection callout AND the synthetic click event
// that would otherwise fire after the touch, so mouse listeners still work on
// desktop while touch devices get their own path.
// Double-tap (two taps within DOUBLE_TAP_MS) triggers chording, mirroring the
// dblclick handler used on desktop.
const LONG_PRESS_MS  = 500;
const DOUBLE_TAP_MS  = 300;

function addTouchHandlers(el, onTap, onLongPress, onDoubleTap) {
  let timer      = null;
  let moved      = false;
  let startX, startY;
  let lastTapAt  = 0;

  el.addEventListener('touchstart', e => {
    if (e.touches.length > 1) { clearTimeout(timer); timer = null; return; } // pinch-to-zoom
    e.preventDefault();
    moved  = false;
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
    timer  = setTimeout(() => { timer = null; if (!moved) onLongPress(); }, LONG_PRESS_MS);
  }, { passive: false });

  el.addEventListener('touchmove', e => {
    if (e.touches.length > 1) { clearTimeout(timer); timer = null; return; } // pinch in progress
    if (!timer) return;
    if (Math.abs(e.touches[0].clientX - startX) > 10 ||
        Math.abs(e.touches[0].clientY - startY) > 10) {
      moved = true; clearTimeout(timer); timer = null;
    }
  }, { passive: true });

  el.addEventListener('touchend', e => {
    if (e.touches.length > 0) { clearTimeout(timer); timer = null; return; } // other finger still down
    e.preventDefault();
    if (timer) {
      clearTimeout(timer); timer = null;
      if (!moved) {
        const now = Date.now();
        if (onDoubleTap && now - lastTapAt < DOUBLE_TAP_MS) {
          lastTapAt = 0;
          onDoubleTap();
        } else {
          lastTapAt = now;
          onTap();
        }
      }
    }
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
    rewindLog:   [],    // [[t_ms, type, r, c], …] — F74 Rewind
    rewindSent:  false, // guard against duplicate /api/rewind submissions
  };
}

// ── F74 Rewind — event recording ─────────────────────────────────────────────
function rewindRecord(type, r, c) {
  if (!state || state.over) return;
  const t = state.startTime ? Math.round(performance.now() - state.startTime) : 0;
  state.rewindLog.push([t, type, r, c]);
}

function rewindSave(outcome) {
  // Accept legacy boolean callers
  if (outcome === true)  outcome = 'win';
  if (outcome === false) outcome = 'loss';
  if (!outcome || !['win', 'loss', 'abandon'].includes(outcome)) outcome = 'loss';

  if (!state || !state.rewindLog || !state.rewindLog.length || !state.boardHash) return;

  const mode = document.getElementById('board')?.dataset.mode || '';

  // sessionStorage entry stays camelCase — rewind.js reads these keys
  const cacheEntry = {
    rows:      state.rows,
    cols:      state.cols,
    mines:     state.mines,
    boardHash: state.boardHash,
    noGuess:   state.noGuess,
    mode,
    timeMs:    state.timeMs || 0,
    won:       outcome === 'win',
    log:       state.rewindLog,
  };
  try { sessionStorage.setItem('rewind-last', JSON.stringify(cacheEntry)); } catch (_) {}

  if (state.rewindSent) return;
  state.rewindSent = true;

  // Count cells revealed at game end
  let cellsRevealed = 0;
  if (state.revealed) {
    for (const row of state.revealed) {
      for (const cell of row) if (cell) cellsRevealed++;
    }
  }

  // Server payload uses snake_case with Phase 1 analytics fields
  const payload = JSON.stringify({
    rows:             state.rows,
    cols:             state.cols,
    mines:            state.mines,
    board_hash:       state.boardHash,
    no_guess:         !!state.noGuess,
    mode,
    time_ms:          state.timeMs || 0,
    won:              outcome === 'win',
    outcome,
    bbbv:             state.bbbv || null,
    left_clicks:      state.leftClicks  || 0,
    right_clicks:     state.rightClicks || 0,
    chord_clicks:     state.chordClicks || 0,
    cells_revealed:   cellsRevealed,
    cells_total_safe: state.rows * state.cols - state.mines,
    log:              state.rewindLog,
  });

  // sendBeacon for abandons — survives tab close unlike fetch()
  if (outcome === 'abandon' && navigator.sendBeacon) {
    try {
      const blob = new Blob([payload], {type: 'application/json'});
      if (navigator.sendBeacon('/api/rewind', blob)) return;
    } catch (_) {}
  }

  try {
    fetch('/api/rewind', {
      method:    'POST',
      headers:   {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
      body:      payload,
      keepalive: true,
    }).catch(function () {});
  } catch (_) {}
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
    state.elapsed += 1;
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
    // Evil NG: only the top-right corner is a valid first click
    const bEl = document.getElementById('board');
    if (bEl && bEl.dataset.mode === 'evil' && !(r === 0 && c === state.cols - 1)) return;

    const placer = state.noGuess ? placeMinesNoGuess : placeMines;
    const {mineSet, board} = placer(state.rows, state.cols, state.mines, r, c);
    state.mineSet    = mineSet;
    state.board      = board;
    state.started    = true;
    state.startTime  = performance.now();
    state.boardHash  = calcBoardHash(state.rows, state.cols, mineSet);
    state.bbbv       = calc3BV(board, state.rows, state.cols, mineSet);
    startTimer();

    // Remove evil-start marker and show normal hint
    if (bEl && bEl.dataset.mode === 'evil') {
      const sc = cellEl(0, state.cols - 1);
      if (sc) sc.classList.remove('evil-start');
      const startHint = document.getElementById('evil-start-hint');
      const normalHint = document.getElementById('evil-normal-hint');
      if (startHint) startHint.style.display = 'none';
      if (normalHint) normalHint.style.display = '';
    }
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

  updatePctCleared();
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

// ── Percentage cleared ────────────────────────────────────────────────────────
function updatePctCleared() {
  const safe = state.rows * state.cols - state.mines;
  if (safe <= 0) return;
  const revealed = state.revealed.flat().filter(Boolean).length;
  const pct = Math.floor(revealed / safe * 100);
  const el = document.getElementById('pct-cleared');
  if (el) el.textContent = pct + '%';
}

// ── Win / Loss ────────────────────────────────────────────────────────────────
function boom(r, c) {
  state.over   = true;
  state.timeMs = state.startTime ? Math.round(performance.now() - state.startTime) : null;
  stopTimer();
  rewindSave('loss');
  // Reveal all mines
  for (const idx of state.mineSet) {
    const mr = Math.floor(idx / state.cols), mc = idx % state.cols;
    state.revealed[mr][mc] = true;
    renderCell(mr, mc, mr === r && mc === c);
  }
  document.getElementById('reset-btn').textContent = '😵';
  recordSessionLoss();
  showOverlay(window.T.game_over, false);
}

function checkWin() {
  const unrevealed = state.rows * state.cols -
    state.revealed.flat().filter(Boolean).length;
  if (unrevealed === state.mines) {
    state.over   = true;
    state.won    = true;
    state.timeMs = state.startTime ? Math.round(performance.now() - state.startTime) : null;
    stopTimer();
    rewindSave('win');
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
    recordSessionWin();
    showOverlay(window.T.game_you_won.replace('{time}', state.elapsed + 's'), true);

    // Quest hooks
    if (typeof window.questsHook === 'function') {
      const mode = document.getElementById('board')?.dataset.mode;
      if (mode === 'beginner')     window.questsHook('easy_won');
      if (mode === 'intermediate') window.questsHook('intermediate_won');
    }
  }
}

// ── Guest login-and-save helper (used by all game overlays) ──────────────────
async function guestLoginAndSave(e, href, submitFnName, inputId) {
  e.preventDefault();
  const name = document.getElementById(inputId)?.value.trim() || 'Guest';
  const fn = window[submitFnName] || window.submitScore;
  if (typeof fn === 'function') await fn(name);
  window.location.href = href;
}

// ── New-game win handler (F91) ────────────────────────────────────────────────
async function handleNewGameWin(username) {
  const board = document.getElementById('board');
  const bbbv  = state.bbbv || 0;
  const total = (state.leftClicks || 0) + (state.rightClicks || 0) + (state.chordClicks || 0);
  const eff   = total > 0 ? ((bbbv / total) * 100).toFixed(1) : '0.0';
  const secs  = state.elapsed || 0;
  const timeLabel = secs >= 60
    ? Math.floor(secs / 60) + ':' + String(secs % 60).padStart(2, '0')
    : secs + 's';

  // Show toast in #game-result
  const resultEl = document.getElementById('game-result');
  if (resultEl) {
    resultEl.innerHTML = `<div class="win-toast" id="win-toast-el">
      <span class="win-toast-title">🎉 You Win!</span>
      <span class="win-toast-stats">${timeLabel}&ensp;·&ensp;3BV ${bbbv}&ensp;·&ensp;${eff}% eff</span>
    </div>`;
    const toastEl = document.getElementById('win-toast-el');
    // Trigger fade-out after 4.2 s so it's gone by 5 s
    setTimeout(() => { if (toastEl) toastEl.classList.add('win-toast-fade'); }, 4200);
    setTimeout(() => { if (resultEl) resultEl.innerHTML = ''; }, 5000);
  }

  // Submit score silently in background
  if (username) {
    submitScore(username).catch(() => {});
  }

  // Reset board at 0.5 s
  setTimeout(() => resetGame(), 500);
}

// ── New-game lose handler (F92) ───────────────────────────────────────────────
function handleNewGameLose() {
  setTimeout(() => resetGame(), 500);
}

// ── Overlay ──────────────────────────────────────────────────────────────────
function showOverlay(msg, won) {
  const board    = document.getElementById('board');
  const username = board?.dataset.username || '';

  // F91: logged-in users with On Win = New Game skip the overlay entirely
  if (won && username && window.PREF_ON_WIN === 'new_game') {
    handleNewGameWin(username);
    return;
  }

  // F92: logged-in users with On Lose = New Game skip the loss overlay
  if (!won && username && window.PREF_ON_LOSE === 'new_game') {
    handleNewGameLose();
    return;
  }

  let el = document.getElementById('game-overlay');
  if (!el) {
    el = document.createElement('div');
    el.id = 'game-overlay';
    (document.getElementById('game-result') || document.getElementById('board')).appendChild(el);
  }
  el.className = won ? 'overlay win' : 'overlay loss';

  const mode     = board.dataset.mode || 'beginner';

  let scoreForm = '';
  if (won) {
    if (username) {
      // Logged-in: auto-submit immediately, show a confirmation
      scoreForm = `<div id="score-msg" style="font-size:0.9rem">${window.T.rush_saving}</div>`;
    } else {
      const loginHref = '/auth/login?next=' + encodeURIComponent(window.location.pathname + window.location.search);
      scoreForm = `
        <div class="overlay-score-form">
          <input id="player-name" type="text" maxlength="32"
                 placeholder="${window.T.rush_name_placeholder}" autocomplete="off" />
          <button onclick="submitScore()">${window.T.rush_save_score}</button>
        </div>
        <div id="score-msg" style="font-size:0.85rem;min-height:1.2em"></div>
        <div class="overlay-guest-warning">${window.T.game_congrats} <a href="${loginHref}" onclick="guestLoginAndSave(event, '${loginHref}', 'submitScore', 'player-name')">${window.T.auth_sign_in}</a> ${window.T.game_score_vanish}</div>
      `;
    }
  }

  const ngParam = state.noGuess ? '&no_guess=true' : '';
  el.innerHTML = `
    <span>${msg}</span>
    ${state.noGuess ? `<span style="font-size:0.75rem;opacity:0.7">${window.T.game_no_guess_mode}</span>` : ''}
    ${scoreForm}
    <button onclick="resetGame()">${window.T.rush_play_again}</button>
    <a class="overlay-lb-link" href="/leaderboard?mode=${mode}${ngParam}">${window.T.game_view_lb}</a>
  `;
  el.style.display = 'flex';

  // F74 Rewind — show replay bar after game ends
  if (typeof window.rewindInit === 'function' && state.rewindLog && state.rewindLog.length && state.boardHash) {
    window.rewindInit({
      rows:      state.rows,
      cols:      state.cols,
      mines:     state.mines,
      boardHash: state.boardHash,
      noGuess:   state.noGuess,
      mode:      document.getElementById('board')?.dataset.mode || '',
      timeMs:    state.timeMs || 0,
      won,
      log:       state.rewindLog,
    });
  }

  if (won && username) {
    submitScore(username);
  } else if (won) {
    setTimeout(() => {
      const inp = document.getElementById('player-name');
      if (inp) {
        inp.focus();
        inp.addEventListener('keydown', e => { if (e.key === 'Enter') submitScore(); });
      }
    }, 50);
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
      headers: {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
      body:    JSON.stringify(payload),
    });
    if (res.ok) {
      if (msgEl) msgEl.textContent = `${window.T.rush_saved_for} ${name}!`;
      if (nameEl) nameEl.disabled = true;
      const saveBtn = document.querySelector('.overlay-score-form button');
      if (saveBtn) saveBtn.disabled = true;
      if (typeof window.onScoreSaved === 'function') window.onScoreSaved();
    } else {
      const err = await res.json();
      if (msgEl) msgEl.textContent = `❌ ${err.detail || window.T.rush_save_failed}`;
    }
  } catch {
    if (msgEl) msgEl.textContent = '❌ Network error. Score not saved.';
  }
}

// ── Render a single cell ─────────────────────────────────────────────────────
const NUM_COLORS_DARK     = ['','#1976D2','#388E3C','#D32F2F','#7B1FA2',
                              '#F57F17','#00838F','#212121','#757575'];
const NUM_COLORS_CLASSIC  = ['','#0000ff','#008000','#ff0000','#000080',
                              '#800000','#008080','#000000','#808080'];
const NUM_COLORS_TENTAIZU = ['','#7ec8e3','#98e6a8','#ffb3b3','#d4a8ff',
                              '#ffd580','#7ff0e0','#c8c8c8','#909090'];
const NUM_COLORS_FLOWER   = ['','#d4449a','#3a9e5f','#c0392b','#8e44ad',
                              '#e67e22','#16a085','#2c3e50','#7f8c8d'];
const NUM_COLORS_MEXICO   = ['','#42a5f5','#66bb6a','#ef5350','#ab47bc',
                              '#ffa726','#26c6da','#d4a276','#a0856c'];
function getNumColors() {
  const skin = document.documentElement.dataset.skin;
  if (skin === 'classic')                          return NUM_COLORS_CLASSIC;
  if (skin === 'tentaizu')                         return NUM_COLORS_TENTAIZU;
  if (skin === 'flower' || skin === 'flower-light') return NUM_COLORS_FLOWER;
  if (skin === 'mexico')                           return NUM_COLORS_MEXICO;
  return NUM_COLORS_DARK;
}
function getMineEmoji() {
  const skin = document.documentElement.dataset.skin;
  if (skin === 'tentaizu')                         return '⭐';
  if (skin === 'flower' || skin === 'flower-light') return '🌸';
  if (skin === 'mexico')                           return '🪅';
  return '💣';
}
function getFlagEmoji() {
  const skin = document.documentElement.dataset.skin;
  if (skin === 'flower' || skin === 'flower-light') return '🌷';
  if (skin === 'mexico')                           return '🇲🇽';
  return '🚩';
}

function renderCell(r, c, isDetonated = false) {
  const el  = cellEl(r, c);
  const val = state.board[r][c];
  const f   = state.flagged[r][c];

  el.className = 'cell';

  if (!state.revealed[r][c]) {
    if (f === 1) {
      el.classList.add('flagged');
      el.textContent = getFlagEmoji();
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
    el.textContent = getMineEmoji();
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

      cell.addEventListener('click',       () => { if (flagMode) { state.rightClicks++; rewindRecord('r', r, c); flag(r, c); } else { state.leftClicks++; rewindRecord('l', r, c); reveal(r, c); } });
      cell.addEventListener('contextmenu', e  => { e.preventDefault(); state.rightClicks++; rewindRecord('r', r, c); flag(r, c); });
      cell.addEventListener('dblclick',    () => { state.chordClicks++; rewindRecord('c', r, c); chord(r, c); });
      addTouchHandlers(cell,
        () => { if (flagMode) { state.rightClicks++; rewindRecord('r', r, c); flag(r, c); } else { state.leftClicks++; rewindRecord('l', r, c); reveal(r, c); } },
        () => { state.rightClicks++; rewindRecord('r', r, c); flag(r, c); },
        () => { state.chordClicks++; rewindRecord('c', r, c); chord(r, c); }
      );

      boardEl.appendChild(cell);
    }
  }
}

// ── Session stats (F93) ───────────────────────────────────────────────────────
const _CLASSIC_MODES = new Set(['beginner', 'intermediate', 'expert']);
const _ss = {};

function _ssKey() {
  const mode = document.getElementById('board')?.dataset.mode || '';
  return `${mode}:${state.noGuess ? 'noguess' : 'guess'}`;
}

function _ssEntry() {
  const k = _ssKey();
  if (!_ss[k]) _ss[k] = { wins: 0, losses: 0, bestTime: null, bbbvSum: 0, clickSum: 0, timeMsSum: 0 };
  return _ss[k];
}

function recordSessionWin() {
  const mode = document.getElementById('board')?.dataset.mode || '';
  if (!_CLASSIC_MODES.has(mode)) return;
  const e = _ssEntry();
  e.wins++;
  if (state.elapsed != null && (e.bestTime === null || state.elapsed < e.bestTime)) {
    e.bestTime = state.elapsed;
  }
  e.bbbvSum   += (state.bbbv || 0);
  e.clickSum  += (state.leftClicks || 0) + (state.rightClicks || 0) + (state.chordClicks || 0);
  e.timeMsSum += (state.timeMs || (state.elapsed * 1000) || 0);
  renderSessionStats();
}

function recordSessionLoss() {
  const mode = document.getElementById('board')?.dataset.mode || '';
  if (!_CLASSIC_MODES.has(mode)) return;
  _ssEntry().losses++;
  renderSessionStats();
}

function renderSessionStats() {
  const el = document.getElementById('session-stats');
  if (!el) return;
  const e = _ssEntry();
  if (e.wins === 0 && e.losses === 0) { el.innerHTML = ''; return; }
  const bestStr = e.bestTime !== null ? e.bestTime + 's' : '—';
  const avgEff  = e.clickSum > 0 ? Math.round((e.bbbvSum / e.clickSum) * 100) + '%' : '—';
  const cps     = e.timeMsSum > 0 ? (e.clickSum / (e.timeMsSum / 1000)).toFixed(2) : '—';
  el.innerHTML =
    `<div class="session-stats-bar">` +
    `<span class="ss-label">Session</span>` +
    `<span class="ss-item"><span class="ss-val ss-wins">${e.wins}</span> won</span>` +
    `<span class="ss-sep">·</span>` +
    `<span class="ss-item"><span class="ss-val ss-loss">${e.losses}</span> lost</span>` +
    `<span class="ss-sep">·</span>` +
    `<span class="ss-item">Best <span class="ss-val">${bestStr}</span></span>` +
    `<span class="ss-sep">·</span>` +
    `<span class="ss-item">Avg eff <span class="ss-val">${avgEff}</span></span>` +
    `<span class="ss-sep">·</span>` +
    `<span class="ss-item"><span class="ss-val">${cps}</span> clicks/s</span>` +
    `</div>`;
}

// ── Init / Reset ─────────────────────────────────────────────────────────────
function initGame(rows, cols, mines, noGuess = false, chording = true) {
  stopTimer();
  clearFlagMode();
  state = freshState(rows, cols, mines, noGuess, chording);
  document.getElementById('timer').textContent      = '000';
  document.getElementById('mines-left').textContent = String(mines).padStart(3,'0');
  document.getElementById('reset-btn').textContent  = '🙂';
  const pctEl = document.getElementById('pct-cleared');
  if (pctEl) pctEl.textContent = '0%';
  const resultEl = document.getElementById('game-result');
  if (resultEl) resultEl.innerHTML = '';
  if (typeof window.rewindReset === 'function') window.rewindReset();
  buildBoard(rows, cols);
  updateNoGuessUI(noGuess);
  renderSessionStats();

  // Evil NG: mark the forced start cell and reset hint visibility
  const bEl = document.getElementById('board');
  if (bEl && bEl.dataset.mode === 'evil') {
    const sc = cellEl(0, cols - 1);
    if (sc) { sc.classList.add('evil-start'); sc.textContent = '✕'; }
    const startHint  = document.getElementById('evil-start-hint');
    const normalHint = document.getElementById('evil-normal-hint');
    if (startHint)  startHint.style.display  = '';
    if (normalHint) normalHint.style.display = 'none';
  }
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
  const isEvil  = board.dataset.mode === 'evil';
  // ?ng=1 or ?ng=0 in the URL overrides the stored preference (not applicable to evil)
  if (!isEvil) {
    const ngParam = new URLSearchParams(window.location.search).get('ng');
    if (ngParam === '1') localStorage.setItem('noGuess', 'true');
    else if (ngParam === '0') localStorage.setItem('noGuess', 'false');
  }
  // Evil NG is always no-guess; other modes read from localStorage
  const noGuess  = isEvil || (localStorage.getItem('noGuess') === 'true');
  const chording = localStorage.getItem('chording') !== 'false';

  initGame(rows, cols, mines, noGuess, chording);

  document.getElementById('reset-btn')
    .addEventListener('click', resetGame);
});

// ── F74 Rewind — abandon capture (tab close / backgrounding) ─────────────────
(function attachAbandonCapture() {
  if (!document.getElementById('board')) return; // non-game pages: skip
  function maybeSendAbandon() {
    try {
      if (!state || !state.boardHash) return; // game not started
      if (state.over)        return;          // already won or lost
      if (state.rewindSent)  return;          // already sent
      // Capture precise elapsed time since the timer may have stopped
      if (!state.timeMs && state.startTime) {
        state.timeMs = Math.round(performance.now() - state.startTime);
      }
      rewindSave('abandon');
    } catch (_) {}
  }
  // pagehide: fires on tab close, navigation, bfcache stash
  window.addEventListener('pagehide', maybeSendAbandon);
  // visibilitychange: catches backgrounding on iOS where pagehide may not fire
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') maybeSendAbandon();
  });
})();
