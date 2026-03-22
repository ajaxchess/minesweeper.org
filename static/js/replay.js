/**
 * Replay Game Engine — minesweeper.org
 * Replays a specific board (decoded from hash) in Standard, Cylinder, or Toroid topology.
 * Uses addTouchHandlers, cellEl, getNumColors from minesweeper.js (loaded first).
 */
(function () {

  // ── URL params ─────────────────────────────────────────────────────────────
  const params   = new URLSearchParams(window.location.search);
  const ROWS     = parseInt(params.get('rows'))  || 9;
  const COLS     = parseInt(params.get('cols'))  || 9;
  const MINES    = parseInt(params.get('mines')) || 10;
  let   HASH     = params.get('hash')  || '';
  const ORIG_DATE = params.get('date') || '';
  const ORIG_MODE = params.get('mode') || '';
  const INIT_VARIANT = params.get('game') || 'standard';

  let currentVariant = INIT_VARIANT;

  // ── State ──────────────────────────────────────────────────────────────────
  let state = {};

  function freshState() {
    return {
      rows: ROWS, cols: COLS, mines: MINES,
      board:      Array.from({length: ROWS}, () => Array(COLS).fill(0)),
      revealed:   Array.from({length: ROWS}, () => Array(COLS).fill(false)),
      flagged:    Array.from({length: ROWS}, () => Array(COLS).fill(0)),
      mineSet:    new Set(),
      minesLeft:  MINES,
      started:    false,
      over:       false,
      won:        false,
      elapsed:    0,
      timerID:    null,
      startTime:  null,
      timeMs:     null,
      bbbv:       null,
      leftClicks:  0,
      rightClicks: 0,
      chordClicks: 0,
    };
  }

  // ── Topology neighbor functions ────────────────────────────────────────────
  function stdNeighbors(r, c, rows, cols) {
    const out = [];
    for (let dr = -1; dr <= 1; dr++)
      for (let dc = -1; dc <= 1; dc++) {
        if (dr === 0 && dc === 0) continue;
        const nr = r + dr, nc = c + dc;
        if (nr >= 0 && nr < rows && nc >= 0 && nc < cols) out.push([nr, nc]);
      }
    return out;
  }

  function cylNeighbors(r, c, rows, cols) {
    const out = [];
    for (let dr = -1; dr <= 1; dr++)
      for (let dc = -1; dc <= 1; dc++) {
        if (dr === 0 && dc === 0) continue;
        const nr = r + dr;
        const nc = (c + dc + cols) % cols;
        if (nr >= 0 && nr < rows) out.push([nr, nc]);
      }
    return out;
  }

  function torNeighbors(r, c, rows, cols) {
    const out = [];
    for (let dr = -1; dr <= 1; dr++)
      for (let dc = -1; dc <= 1; dc++) {
        if (dr === 0 && dc === 0) continue;
        const nr = (r + dr + rows) % rows;
        const nc = (c + dc + cols) % cols;
        out.push([nr, nc]);
      }
    return out;
  }

  function getNeighborFn(variant) {
    if (variant === 'cylinder') return cylNeighbors;
    if (variant === 'toroid')   return torNeighbors;
    return stdNeighbors;
  }

  // ── Decode board hash → mine set ──────────────────────────────────────────
  function decodeBoardHash(hash, rows, cols) {
    try {
      const bin    = atob(hash);
      const mineSet = new Set();
      const n = rows * cols;
      for (let i = 0; i < n; i++) {
        if (bin.charCodeAt(i >> 3) & (1 << (i & 7))) mineSet.add(i);
      }
      return mineSet;
    } catch {
      return new Set();
    }
  }

  // ── Build board values from mine set + neighbor function ──────────────────
  function buildBoardFromMineSet(mineSet, rows, cols, neighborFn) {
    const board = Array.from({length: rows}, () => Array(cols).fill(0));
    for (const idx of mineSet) {
      const r = Math.floor(idx / cols), c = idx % cols;
      board[r][c] = -1;
      neighborFn(r, c, rows, cols).forEach(([nr, nc]) => {
        if (board[nr][nc] !== -1) board[nr][nc]++;
      });
    }
    return board;
  }

  // ── 3BV (topology-aware) ──────────────────────────────────────────────────
  function calc3BV(board, rows, cols, mineSet, neighborFn) {
    const n       = rows * cols;
    const covered = new Uint8Array(n);
    let   bbbv    = 0;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const idx = r * cols + c;
        if (board[r][c] !== 0 || covered[idx] || mineSet.has(idx)) continue;
        bbbv++;
        const queue = [[r, c]];
        covered[idx] = 1;
        while (queue.length) {
          const [cr, cc] = queue.shift();
          for (const [nr, nc] of neighborFn(cr, cc, rows, cols)) {
            const ni = nr * cols + nc;
            if (covered[ni] || mineSet.has(ni)) continue;
            covered[ni] = 1;
            if (board[nr][nc] === 0) queue.push([nr, nc]);
          }
        }
      }
    }
    for (let i = 0; i < n; i++) {
      const r = Math.floor(i / cols), c = i % cols;
      if (board[r][c] > 0 && !covered[i]) bbbv++;
    }
    return bbbv;
  }

  // ── Timer ──────────────────────────────────────────────────────────────────
  function startTimer() {
    if (state.timerID) return;
    state.timerID = setInterval(() => {
      state.elapsed = Math.min(state.elapsed + 1, 999);
      document.getElementById('timer').textContent = String(state.elapsed).padStart(3, '0');
    }, 1000);
  }

  function stopTimer() {
    clearInterval(state.timerID);
    state.timerID = null;
  }

  // ── Reveal ─────────────────────────────────────────────────────────────────
  function reveal(r, c) {
    if (state.over || state.revealed[r][c] || state.flagged[r][c] === 1) return;

    if (!state.started) {
      state.started   = true;
      state.startTime = performance.now();
      startTimer();
    }

    if (state.board[r][c] === -1) {
      boom(r, c);
      return;
    }

    const neighborFn = getNeighborFn(currentVariant);
    const queue = [[r, c]];
    while (queue.length) {
      const [cr, cc] = queue.shift();
      if (state.revealed[cr][cc]) continue;
      state.revealed[cr][cc] = true;
      renderCell(cr, cc);
      if (state.board[cr][cc] === 0) {
        neighborFn(cr, cc, state.rows, state.cols).forEach(([nr, nc]) => {
          if (!state.revealed[nr][nc] && !state.flagged[nr][nc]) queue.push([nr, nc]);
        });
      }
    }
    checkWin();
    updateClickDisplay();
  }

  // ── Chord ──────────────────────────────────────────────────────────────────
  function chord(r, c) {
    if (!state.revealed[r][c] || state.board[r][c] <= 0) return;
    const neighborFn = getNeighborFn(currentVariant);
    const nb    = neighborFn(r, c, state.rows, state.cols);
    const flags = nb.filter(([nr, nc]) => state.flagged[nr][nc] === 1).length;
    if (flags === state.board[r][c]) nb.forEach(([nr, nc]) => reveal(nr, nc));
    updateClickDisplay();
  }

  // ── Live click counter ─────────────────────────────────────────────────────
  function updateClickDisplay() {
    const l = document.getElementById('clicks-left');
    const f = document.getElementById('clicks-flag');
    const c = document.getElementById('clicks-chord');
    if (l) l.textContent = state.leftClicks  || 0;
    if (f) f.textContent = state.rightClicks || 0;
    if (c) c.textContent = state.chordClicks || 0;
  }

  // ── Flag ───────────────────────────────────────────────────────────────────
  function flag(r, c) {
    if (state.over || state.revealed[r][c]) return;
    const cur = state.flagged[r][c];
    const next = (cur + 1) % 3;
    state.flagged[r][c] = next;
    if (cur === 0 && next === 1) state.minesLeft--;
    if (cur === 1 && next === 2) state.minesLeft++;
    document.getElementById('mines-left').textContent = String(state.minesLeft).padStart(3, '0');
    renderCell(r, c);
    updateClickDisplay();
  }

  // ── Win / Loss ─────────────────────────────────────────────────────────────
  function boom(r, c) {
    state.over   = true;
    state.timeMs = state.startTime ? Math.round(performance.now() - state.startTime) : null;
    stopTimer();
    for (const idx of state.mineSet) {
      const mr = Math.floor(idx / state.cols), mc = idx % state.cols;
      state.revealed[mr][mc] = true;
      renderCell(mr, mc, mr === r && mc === c);
    }
    document.getElementById('reset-btn').textContent = '😵';
    showOverlay('💥 Game Over', false);
  }

  function checkWin() {
    const unrevealed = state.rows * state.cols - state.revealed.flat().filter(Boolean).length;
    if (unrevealed === state.mines) {
      state.over   = true;
      state.won    = true;
      state.timeMs = state.startTime ? Math.round(performance.now() - state.startTime) : null;
      stopTimer();
      document.getElementById('reset-btn').textContent = '😎';
      for (const idx of state.mineSet) {
        const mr = Math.floor(idx / state.cols), mc = idx % state.cols;
        if (!state.flagged[mr][mc]) {
          state.flagged[mr][mc] = true;
          renderCell(mr, mc);
        }
      }
      document.getElementById('mines-left').textContent = '000';
      const secs = state.timeMs != null ? (state.timeMs / 1000).toFixed(3) : state.elapsed;
      showOverlay(`🎉 You Won! — ${secs}s`, true);
    }
  }

  // ── Efficiency helpers ─────────────────────────────────────────────────────
  function fmtEff(bbbv, leftClicks, chordClicks) {
    if (!bbbv) return '—';
    const total = (leftClicks || 0) + (chordClicks || 0);
    if (!total) return '—';
    return Math.round(bbbv / total * 100) + '%';
  }

  function fmtBbbvS(bbbv, timeMs, timeSecs) {
    if (!bbbv) return '—';
    const secs = timeMs != null ? timeMs / 1000 : timeSecs;
    if (!secs) return '—';
    return (bbbv / secs).toFixed(3);
  }

  // ── Overlay ────────────────────────────────────────────────────────────────
  function showOverlay(msg, won) {
    let el = document.getElementById('game-overlay');
    if (!el) {
      el = document.createElement('div');
      el.id = 'game-overlay';
      (document.getElementById('game-result') || document.getElementById('board')).appendChild(el);
    }
    el.className = won ? 'overlay win' : 'overlay loss';

    const board    = document.getElementById('board');
    const username = board.dataset.username || '';

    let statsHtml = '';
    if (won && state.bbbv) {
      const eff        = fmtEff(state.bbbv, state.leftClicks, state.chordClicks);
      const bbbvs      = fmtBbbvS(state.bbbv, state.timeMs, state.elapsed);
      const totalClicks = (state.leftClicks || 0) + (state.rightClicks || 0) + (state.chordClicks || 0);
      const clickDetail = `L:${state.leftClicks || 0} F:${state.rightClicks || 0} C:${state.chordClicks || 0}`;
      statsHtml = `
        <div class="replay-win-stats">
          <span>3BV: <strong>${state.bbbv}</strong></span>
          <span>3BV/s: <strong>${bbbvs}</strong></span>
          <span>Efficiency: <strong>${eff}</strong></span>
          <span>Clicks: <strong>${totalClicks}</strong> <span class="replay-click-detail">(${clickDetail})</span></span>
        </div>`;
    }

    let scoreForm = '';
    if (won) {
      if (username) {
        scoreForm = `<div id="replay-score-msg" style="font-size:0.9rem">Saving score…</div>`;
      } else {
        const loginHref = '/auth/login?next=' + encodeURIComponent(window.location.pathname + window.location.search);
        scoreForm = `
          <div class="overlay-score-form">
            <input id="replay-player-name" type="text" maxlength="32"
                   placeholder="Enter your name" autocomplete="off" />
            <button onclick="replaySubmitScore()">Save Score</button>
          </div>
          <div id="replay-score-msg" style="font-size:0.85rem;min-height:1.2em"></div>
          <div class="overlay-guest-warning">🎉 Congratulations! <a href="${loginHref}" onclick="guestLoginAndSave(event, '${loginHref}', 'replaySubmitScore', 'replay-player-name')">Login with Google</a> or your score will vanish at 0:00 UTC.</div>
        `;
      }
    }

    el.innerHTML = `
      <span>${msg}</span>
      ${statsHtml}
      ${scoreForm}
      <button onclick="replayResetGame()">Play Again</button>
    `;
    el.style.display = 'flex';

    if (won && username) {
      submitScore(username);
    } else if (won) {
      setTimeout(() => {
        const inp = document.getElementById('replay-player-name');
        if (inp) {
          inp.focus();
          inp.addEventListener('keydown', e => { if (e.key === 'Enter') replaySubmitScore(); });
        }
      }, 50);
    }
  }

  // ── Score submission ────────────────────────────────────────────────────────
  async function submitScore(autoName = null) {
    const msgEl  = document.getElementById('replay-score-msg');
    const nameEl = document.getElementById('replay-player-name');
    const name   = autoName || nameEl?.value.trim();

    if (!name) { if (msgEl) msgEl.textContent = '⚠️ Please enter your name.'; return; }

    const payload = {
      board_hash:   HASH,
      variant:      currentVariant,
      name,
      time_secs:    Math.max(1, state.elapsed),
      time_ms:      state.timeMs,
      rows:         state.rows,
      cols:         state.cols,
      mines:        state.mines,
      bbbv:         state.bbbv,
      left_clicks:  state.leftClicks,
      right_clicks: state.rightClicks,
      chord_clicks: state.chordClicks,
    };

    try {
      const res = await fetch('/api/replay-scores', {
        method:  'POST',
        headers: {'Content-Type': 'application/json'},
        body:    JSON.stringify(payload),
      });
      if (res.ok) {
        if (msgEl) msgEl.textContent = `✅ Score saved for ${name}!`;
        if (nameEl) nameEl.disabled = true;
        const saveBtn = document.querySelector('.overlay-score-form button');
        if (saveBtn) saveBtn.disabled = true;
        // Refresh leaderboard after saving
        loadLeaderboard(currentVariant);
      } else {
        const err = await res.json();
        const detail = Array.isArray(err.detail)
          ? err.detail.map(e => e.msg || String(e)).join('; ')
          : (err.detail || 'Could not save score.');
        if (msgEl) msgEl.textContent = `❌ ${detail}`;
      }
    } catch {
      if (msgEl) msgEl.textContent = '❌ Network error.';
    }
  }

  // ── Render cell ────────────────────────────────────────────────────────────
  function renderCell(r, c, isDetonated = false) {
    const el  = cellEl(r, c);
    const val = state.board[r][c];
    const f   = state.flagged[r][c];

    el.className = 'cell';
    if (!state.revealed[r][c]) {
      if (f === 1)      { el.classList.add('flagged');  el.textContent = '🚩'; }
      else if (f === 2) { el.classList.add('question'); el.textContent = '❓'; }
      else              { el.classList.add('hidden');   el.textContent = ''; }
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

  // ── Build board DOM ────────────────────────────────────────────────────────
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

        cell.addEventListener('click', () => {
          if (flagMode) { state.rightClicks++; flag(r, c); }
          else          { state.leftClicks++;  reveal(r, c); }
        });
        cell.addEventListener('contextmenu', e => {
          e.preventDefault(); state.rightClicks++; flag(r, c);
        });
        cell.addEventListener('dblclick', () => { state.chordClicks++; chord(r, c); });
        addTouchHandlers(cell,
          () => { if (flagMode) { state.rightClicks++; flag(r, c); } else { state.leftClicks++; reveal(r, c); } },
          () => { state.rightClicks++; flag(r, c); }
        );
        boardEl.appendChild(cell);
      }
    }
  }

  // ── Init game for a given variant ─────────────────────────────────────────
  function initGame(variant) {
    currentVariant = variant;
    stopTimer();
    if (typeof clearFlagMode === 'function') clearFlagMode();

    const neighborFn = getNeighborFn(variant);
    const mineSet    = decodeBoardHash(HASH, ROWS, COLS);
    const board      = buildBoardFromMineSet(mineSet, ROWS, COLS, neighborFn);
    const bbbv       = calc3BV(board, ROWS, COLS, mineSet, neighborFn);

    state            = freshState();
    state.mineSet    = mineSet;
    state.board      = board;
    state.bbbv       = bbbv;

    document.getElementById('timer').textContent      = '000';
    document.getElementById('mines-left').textContent = String(MINES).padStart(3, '0');
    document.getElementById('reset-btn').textContent  = '🙂';
    const resultEl = document.getElementById('game-result');
    if (resultEl) resultEl.innerHTML = '';
    updateClickDisplay();
    buildBoard(ROWS, COLS);

    // Update 3BV display
    const bbbvEl = document.getElementById('replay-bbbv-value');
    if (bbbvEl) bbbvEl.textContent = bbbv;

    // Update wrap label
    const wrapLabel = document.getElementById('replay-wrap-label');
    if (wrapLabel) {
      if (variant === 'cylinder')    wrapLabel.textContent = '↩ left & right edges connect ↪';
      else if (variant === 'toroid') wrapLabel.textContent = '↩↕ all edges connect ↔↕';
      else                           wrapLabel.textContent = '';
    }

    // Update board class for visual distinction
    const boardEl = document.getElementById('board');
    boardEl.classList.remove('cylinder-board', 'toroid-board');
    if (variant === 'cylinder') boardEl.classList.add('cylinder-board');
    if (variant === 'toroid')   boardEl.classList.add('toroid-board');

    // Highlight active variant tab
    document.querySelectorAll('.replay-variant-tab').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.variant === variant);
    });

    // Load leaderboard for this variant
    loadLeaderboard(variant);
  }

  // ── Leaderboard ────────────────────────────────────────────────────────────
  function esc(s) {
    return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  }

  function fmtTime(s) {
    if (s.time_ms != null) return (s.time_ms / 1000).toFixed(3) + 's';
    return s.time_secs + 's';
  }

  function fmtBbbvSRow(s) {
    if (!s.bbbv) return '—';
    const secs = s.time_ms != null ? s.time_ms / 1000 : s.time_secs;
    if (!secs) return '—';
    return (s.bbbv / secs).toFixed(3);
  }

  function fmtEffRow(s) {
    if (!s.bbbv) return '—';
    const total = (s.left_clicks || 0) + (s.chord_clicks || 0);
    if (!total) return '—';
    return Math.round(s.bbbv / total * 100) + '%';
  }

  const MEDALS = ['🥇', '🥈', '🥉'];

  async function loadLeaderboard(variant) {
    const el = document.getElementById('replay-lb-content');
    if (!el) return;

    // Update leaderboard title
    const titleEl = document.getElementById('replay-lb-title');
    if (titleEl) {
      const label = variant === 'cylinder' ? '🔄 Cylinder' : variant === 'toroid' ? '🍩 Toroid' : '🏁 Standard';
      if (HASH) {
        const rp = new URLSearchParams(window.location.search);
        rp.set('game', variant);
        const short = HASH.slice(0, 8) + '…';
        titleEl.innerHTML = `🏆 Board High Scores — ${label} — <a href="/variants/replay/?${rp}" class="lb-replay-link" title="${esc(HASH)}">${esc(short)}</a>`;
      } else {
        titleEl.textContent = `🏆 Board High Scores — ${label}`;
      }
    }

    el.innerHTML = '<div class="lb-loading">Loading…</div>';
    try {
      const url = `/api/replay-scores?board_hash=${encodeURIComponent(HASH)}&variant=${variant}`;
      const res  = await fetch(url);
      const data = await res.json();

      if (!data.length) {
        el.innerHTML = '<div class="lb-empty">No scores yet — be the first!</div>';
        return;
      }

      const rows = data.map((s, i) => {
        const nameCell = s.profile_url
          ? `<a href="${esc(s.profile_url)}" class="lb-profile-link">${esc(s.name)}</a>`
          : esc(s.name);
        return `<tr class="${i < 3 ? 'top-' + (i+1) : ''}">
          <td class="lb-rank">${MEDALS[i] ?? i + 1}</td>
          <td class="lb-name">${nameCell}</td>
          <td class="lb-time">${fmtTime(s)}</td>
          <td class="lb-stat">${s.bbbv ?? '—'}</td>
          <td class="lb-stat">${fmtBbbvSRow(s)}</td>
          <td class="lb-stat">${fmtEffRow(s)}</td>
          <td class="lb-date">${s.created_at}</td>
        </tr>`;
      }).join('');

      el.innerHTML = `
        <div class="lb-table-wrap">
          <table class="lb-table">
            <thead><tr>
              <th>#</th><th>Name</th><th>Time</th>
              <th class="lb-th-stat" title="3BV">3BV</th>
              <th class="lb-th-stat" title="3BV per second">3BV/s</th>
              <th class="lb-th-stat" title="Efficiency: 3BV ÷ clicks">Eff</th>
              <th>Date</th>
            </tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>`;
    } catch {
      el.innerHTML = '<div class="lb-empty">⚠️ Could not load scores.</div>';
    }
  }

  // ── Setup form helpers ─────────────────────────────────────────────────────
  function generateHash(rows, cols, mines) {
    const safeR = Math.floor(rows / 2), safeC = Math.floor(cols / 2);
    const { mineSet } = placeMines(rows, cols, mines, safeR, safeC);
    return calcBoardHash(rows, cols, mineSet);
  }

  function navigateToBoard() {
    const rows  = parseInt(document.getElementById('setup-rows').value)  || ROWS;
    const cols  = parseInt(document.getElementById('setup-cols').value)  || COLS;
    const mines = parseInt(document.getElementById('setup-mines').value) || MINES;
    const hash  = document.getElementById('setup-hash').value.trim();
    if (!hash) return;
    const p = new URLSearchParams({ rows, cols, mines, hash });
    window.location.href = '/variants/replay/?' + p.toString();
  }

  function populateSetupForm(rows, cols, mines, hash) {
    const r = document.getElementById('setup-rows');
    const c = document.getElementById('setup-cols');
    const m = document.getElementById('setup-mines');
    const h = document.getElementById('setup-hash');
    if (r) r.value = rows;
    if (c) c.value = cols;
    if (m) m.value = mines;
    if (h) h.value = hash;

    // Highlight matching preset button
    document.querySelectorAll('.replay-preset-btn').forEach(btn => {
      btn.classList.toggle('active',
        parseInt(btn.dataset.rows)  === rows &&
        parseInt(btn.dataset.cols)  === cols &&
        parseInt(btn.dataset.mines) === mines
      );
    });
  }

  // ── Expose to window ───────────────────────────────────────────────────────
  window.replayResetGame   = () => initGame(currentVariant);
  window.replaySubmitScore = submitScore;

  // ── Bootstrap ──────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    const board = document.getElementById('board');
    if (!board || board.dataset.mode !== 'replay') return;

    // Determine hash to use — generate one if not supplied
    if (!HASH) {
      HASH = generateHash(ROWS, COLS, MINES);
      // Update the URL so the page is immediately shareable
      const newParams = new URLSearchParams(params);
      newParams.set('hash', HASH);
      history.replaceState(null, '', '/variants/replay/?' + newParams.toString());
    }

    // Populate the setup form with current values
    populateSetupForm(ROWS, COLS, MINES, HASH);

    // Preset buttons
    document.querySelectorAll('.replay-preset-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const r = parseInt(btn.dataset.rows);
        const c = parseInt(btn.dataset.cols);
        const m = parseInt(btn.dataset.mines);
        populateSetupForm(r, c, m, generateHash(r, c, m));
      });
    });

    // Re-generate hash when dimensions change
    ['setup-rows', 'setup-cols', 'setup-mines'].forEach(id => {
      document.getElementById(id)?.addEventListener('change', () => {
        const r = parseInt(document.getElementById('setup-rows').value)  || 9;
        const c = parseInt(document.getElementById('setup-cols').value)  || 9;
        const m = parseInt(document.getElementById('setup-mines').value) || 10;
        document.getElementById('setup-hash').value = generateHash(r, c, m);
        document.querySelectorAll('.replay-preset-btn').forEach(b => b.classList.remove('active'));
      });
    });

    // 🎲 randomise button
    document.getElementById('regen-hash-btn')?.addEventListener('click', () => {
      const r = parseInt(document.getElementById('setup-rows').value)  || ROWS;
      const c = parseInt(document.getElementById('setup-cols').value)  || COLS;
      const m = parseInt(document.getElementById('setup-mines').value) || MINES;
      document.getElementById('setup-hash').value = generateHash(r, c, m);
    });

    // Play button & Enter key in hash field
    document.getElementById('play-board-btn')?.addEventListener('click', navigateToBoard);
    document.getElementById('setup-hash')?.addEventListener('keydown', e => {
      if (e.key === 'Enter') navigateToBoard();
    });

    // Variant tabs
    document.querySelectorAll('.replay-variant-tab').forEach(btn => {
      btn.addEventListener('click', () => initGame(btn.dataset.variant));
    });

    document.getElementById('reset-btn')?.addEventListener('click', () => initGame(currentVariant));

    initGame(INIT_VARIANT);
  });

})();
