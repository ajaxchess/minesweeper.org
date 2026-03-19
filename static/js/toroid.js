/**
 * Toroid Minesweeper — Game Engine
 * The board wraps on all sides: left↔right and top↔bottom edges are connected.
 * Uses addTouchHandlers, cellEl, getNumColors from minesweeper.js (loaded first).
 */
(function () {

  // ── State ──────────────────────────────────────────────────────────────────
  let state = {};

  function freshState(rows, cols, mines, noGuess = false, chording = true) {
    return {
      rows, cols, mines,
      board:     Array.from({length: rows}, () => Array(cols).fill(0)),
      revealed:  Array.from({length: rows}, () => Array(cols).fill(false)),
      flagged:   Array.from({length: rows}, () => Array(cols).fill(0)),
      mineSet:   new Set(),
      minesLeft: mines,
      started:   false,
      over:      false,
      won:       false,
      elapsed:   0,
      timerID:   null,
      noGuess,
      chording,
      startTime:   null,
      timeMs:      null,
      boardHash:   null,
      bbbv:        null,
      leftClicks:  0,
      rightClicks: 0,
      chordClicks: 0,
    };
  }

  // ── Toroid Neighbors (both rows and columns wrap) ──────────────────────────
  function neighbors(r, c, rows, cols) {
    const out = [];
    for (let dr = -1; dr <= 1; dr++)
      for (let dc = -1; dc <= 1; dc++) {
        if (dr === 0 && dc === 0) continue;
        const nr = (r + dr + rows) % rows; // wrap rows
        const nc = (c + dc + cols) % cols; // wrap cols
        out.push([nr, nc]);
      }
    return out;
  }

  // ── 3BV (toroid-aware, uses local wrapping neighbors) ─────────────────────
  function calc3BV(board, rows, cols, mineSet) {
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
          for (const [nr, nc] of neighbors(cr, cc, rows, cols)) {
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

  // ── Mine Placement (safe first click) ─────────────────────────────────────
  function placeMines(rows, cols, mines, safeR, safeC) {
    // Forbidden zone wraps both rows and cols
    const forbidden = new Set();
    for (let dr = -1; dr <= 1; dr++)
      for (let dc = -1; dc <= 1; dc++) {
        const nr = (safeR + dr + rows) % rows;
        const nc = (safeC + dc + cols) % cols;
        forbidden.add(nr * cols + nc);
      }

    const pool = [];
    for (let i = 0; i < rows * cols; i++)
      if (!forbidden.has(i)) pool.push(i);

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

  // ── No-Guess Solver (toroid-aware) ────────────────────────────────────────
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
            constraints.push({cells: hidden, count: remaining});
          }
        }
      }

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
    return placeMines(rows, cols, mines, safeR, safeC);
  }

  // ── Timer ──────────────────────────────────────────────────────────────────
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

  // ── Reveal ─────────────────────────────────────────────────────────────────
  function reveal(r, c) {
    if (state.over || state.revealed[r][c] || state.flagged[r][c] === 1) return;

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

    if (state.board[r][c] === -1) { boom(r, c); return; }

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

  // ── Chord ──────────────────────────────────────────────────────────────────
  function chord(r, c) {
    if (!state.chording || !state.revealed[r][c] || state.board[r][c] <= 0) return;
    const nb    = neighbors(r, c, state.rows, state.cols);
    const flags = nb.filter(([nr, nc]) => state.flagged[nr][nc] === 1).length;
    if (flags === state.board[r][c]) nb.forEach(([nr, nc]) => reveal(nr, nc));
  }

  // ── Flag ───────────────────────────────────────────────────────────────────
  function flag(r, c) {
    if (state.over || state.revealed[r][c]) return;
    const cur  = state.flagged[r][c];
    const next = (cur + 1) % 3;
    state.flagged[r][c] = next;
    if (cur === 0 && next === 1) state.minesLeft--;
    if (cur === 1 && next === 2) state.minesLeft++;
    document.getElementById('mines-left').textContent =
      String(state.minesLeft).padStart(3, '0');
    renderCell(r, c);
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
    const unrevealed = state.rows * state.cols -
      state.revealed.flat().filter(Boolean).length;
    if (unrevealed === state.mines) {
      state.over   = true;
      state.won    = true;
      state.timeMs = state.startTime ? Math.round(performance.now() - state.startTime) : null;
      stopTimer();
      document.getElementById('reset-btn').textContent = '😎';
      for (const idx of state.mineSet) {
        const mr = Math.floor(idx / state.cols), mc = idx % state.cols;
        if (!state.flagged[mr][mc]) { state.flagged[mr][mc] = true; renderCell(mr, mc); }
      }
      document.getElementById('mines-left').textContent = '000';
      showOverlay(`🎉 You Won! — ${state.elapsed}s`, true);
    }
  }

  // ── Score submission ───────────────────────────────────────────────────────
  async function submitScore(autoName = null) {
    const board   = document.getElementById('board');
    const msgEl   = document.getElementById('tor-score-msg');
    const nameEl  = document.getElementById('tor-player-name');
    const name    = autoName || nameEl?.value.trim();

    if (!name) { if (msgEl) msgEl.textContent = '⚠️ Please enter your name.'; return; }

    const torMode = torModeKey(board.dataset.mode);
    const payload = {
      name,
      tor_mode:     torMode,
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
      const res = await fetch('/api/toroid-scores', {
        method:  'POST',
        headers: {'Content-Type': 'application/json'},
        body:    JSON.stringify(payload),
      });
      if (res.ok) {
        if (msgEl) msgEl.textContent = `✅ Score saved for ${name}!`;
        if (nameEl) nameEl.disabled = true;
        const saveBtn = document.querySelector('#tor-score-form button');
        if (saveBtn) saveBtn.disabled = true;
        loadLeaderboard(torMode, state.noGuess);
      } else {
        const err = await res.json();
        if (msgEl) msgEl.textContent = `❌ ${err.detail || 'Could not save score.'}`;
      }
    } catch {
      if (msgEl) msgEl.textContent = '❌ Network error. Score not saved.';
    }
  }

  // Map data-mode to API tor_mode key
  function torModeKey(dataMode) {
    const map = {
      'toroid-beginner':     'easy',
      'toroid-intermediate': 'intermediate',
      'toroid-expert':       'expert',
      'toroid-custom':       'custom',
    };
    return map[dataMode] || 'easy';
  }

  // ── Leaderboard ────────────────────────────────────────────────────────────
  const TOR_MODE_LABELS = { easy: 'Easy', intermediate: 'Medium', expert: 'Hard', custom: 'Custom' };

  async function loadLeaderboard(torMode, noGuess = false) {
    const el      = document.getElementById('tor-lb-content');
    const titleEl = document.getElementById('tor-lb-title');
    if (!el) return;
    if (titleEl) {
      const label = TOR_MODE_LABELS[torMode] || torMode;
      titleEl.textContent = `🏆 Today's Best — ${noGuess ? '⚡ No-Guess ' : ''}${label}`;
    }
    el.innerHTML = '<div class="lb-loading">Loading…</div>';
    try {
      const res  = await fetch(`/api/toroid-scores/${torMode}?no_guess=${noGuess}&period=daily`);
      const data = await res.json();
      if (!data.length) {
        el.innerHTML = '<div class="lb-empty">No scores yet — be the first!</div>';
        return;
      }
      const medals = ['🥇', '🥈', '🥉'];
      const rows = data.map((s, i) => {
        const nameCell = s.profile_url
          ? `<a href="${esc(s.profile_url)}" class="lb-profile-link">${esc(s.name)}</a>`
          : esc(s.name);
        let hashCell = '<td class="lb-hash">—</td>';
        if (s.board_hash) {
          const rp = new URLSearchParams({
            rows: s.rows, cols: s.cols, mines: s.mines,
            hash: s.board_hash, date: s.created_at,
            mode: torMode, game: 'toroid',
          });
          const short = s.board_hash.slice(0, 8) + '…';
          hashCell = `<td class="lb-hash"><a href="/variants/replay/?${rp}" class="lb-replay-link" title="${esc(s.board_hash)}">${short}</a></td>`;
        }
        return `
        <tr class="${i < 3 ? 'top-' + (i + 1) : ''}">
          <td class="lb-rank">${medals[i] || '#' + (i + 1)}</td>
          <td class="lb-name">${nameCell}</td>
          <td class="lb-time">${fmtTime(s)}</td>
          <td class="lb-board">${s.rows}×${s.cols}</td>
          <td class="lb-mines">${s.mines}</td>
          <td class="lb-stat">${s.bbbv ?? '—'}</td>
          <td class="lb-stat">${fmtBbbvS(s)}</td>
          <td class="lb-stat">${fmtEff(s)}</td>
          <td class="lb-date">${s.created_at}</td>
          ${hashCell}
        </tr>`;
      }).join('');
      el.innerHTML = `
        <div class="lb-table-wrap">
          <table class="lb-table">
            <thead><tr>
              <th>#</th><th>Name</th><th>Time</th><th>Board</th><th>Mines</th>
              <th class="lb-th-stat" data-tip="Minimum clicks to solve the board">3BV</th>
              <th class="lb-th-stat" data-tip="3BV per second">3BV/s</th>
              <th class="lb-th-stat" data-tip="Efficiency: 3BV ÷ left+chord clicks">Eff</th>
              <th>Date</th>
              <th>Board</th>
            </tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>`;
    } catch {
      el.innerHTML = '<div class="lb-empty">⚠️ Could not load scores.</div>';
    }
  }

  function fmtTime(s) {
    if (s.time_ms != null) return (s.time_ms / 1000).toFixed(3) + 's';
    return s.time_secs + 's';
  }

  function fmtBbbvS(s) {
    if (!s.bbbv) return '—';
    const secs = s.time_ms != null ? s.time_ms / 1000 : s.time_secs;
    if (!secs) return '—';
    return (s.bbbv / secs).toFixed(3);
  }

  function fmtEff(s) {
    if (!s.bbbv) return '—';
    const total = (s.left_clicks || 0) + (s.chord_clicks || 0);
    if (!total) return '—';
    return Math.round(s.bbbv / total * 100) + '%';
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  }

  // ── Overlay ────────────────────────────────────────────────────────────────
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
    const torMode  = torModeKey(board.dataset.mode);

    let scoreForm = '';
    if (won) {
      if (username) {
        scoreForm = `<div id="tor-score-msg" style="font-size:0.9rem">Saving score…</div>`;
      } else {
        const loginHref = '/auth/login?next=' + encodeURIComponent(window.location.pathname + window.location.search);
        scoreForm = `
          <div id="tor-score-form" class="overlay-score-form">
            <input id="tor-player-name" type="text" maxlength="32"
                   placeholder="Enter your name" autocomplete="off" />
            <button onclick="torSubmitScore()">Save Score</button>
          </div>
          <div id="tor-score-msg" style="font-size:0.85rem;min-height:1.2em"></div>
          <div class="overlay-guest-warning">🎉 Congratulations! <a href="${loginHref}" onclick="guestLoginAndSave(event, '${loginHref}', 'torSubmitScore', 'tor-player-name')">Login with Google</a> or your score will vanish at 0:00 UTC.</div>
        `;
      }
    }

    el.innerHTML = `
      <span>${msg}</span>
      ${scoreForm}
      <button onclick="torResetGame()">Play Again</button>
    `;
    el.style.display = 'flex';

    if (won && username) {
      submitScore(username);
    } else if (won) {
      setTimeout(() => {
        const inp = document.getElementById('tor-player-name');
        if (inp) {
          inp.focus();
          inp.addEventListener('keydown', e => { if (e.key === 'Enter') torSubmitScore(); });
        }
      }, 50);
    }
  }

  // ── Render Cell ────────────────────────────────────────────────────────────
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

  // ── Build Board DOM ────────────────────────────────────────────────────────
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

        cell.addEventListener('click',       () => { state.leftClicks++;  reveal(r, c); });
        cell.addEventListener('contextmenu', e  => { e.preventDefault(); state.rightClicks++; flag(r, c); });
        cell.addEventListener('dblclick',    () => { state.chordClicks++; chord(r, c); });
        addTouchHandlers(cell, () => { state.leftClicks++; reveal(r, c); }, () => { state.rightClicks++; flag(r, c); });

        boardEl.appendChild(cell);
      }
    }
  }

  // ── Init / Reset ───────────────────────────────────────────────────────────
  function initGame(rows, cols, mines, noGuess = false, chording = true) {
    stopTimer();
    state = freshState(rows, cols, mines, noGuess, chording);
    document.getElementById('timer').textContent      = '000';
    document.getElementById('mines-left').textContent = String(mines).padStart(3, '0');
    document.getElementById('reset-btn').textContent  = '🙂';
    buildBoard(rows, cols);
    updateNoGuessUI(noGuess);
  }

  function resetGame() {
    initGame(state.rows, state.cols, state.mines, state.noGuess, state.chording);
  }

  // ── No-Guess Toggle ────────────────────────────────────────────────────────
  function toggleNoGuess() {
    const newVal = !state.noGuess;
    localStorage.setItem('torNoGuess', newVal);
    initGame(state.rows, state.cols, state.mines, newVal, state.chording);
    const board = document.getElementById('board');
    loadLeaderboard(torModeKey(board.dataset.mode), newVal);
  }

  function updateNoGuessUI(active) {
    const btn = document.getElementById('noguess-toggle');
    if (btn) btn.classList.toggle('active', active);
  }

  // ── Expose to window ───────────────────────────────────────────────────────
  window.torResetGame     = resetGame;
  window.torInitGame      = initGame;
  window.torToggleNoGuess = toggleNoGuess;
  window.torSubmitScore   = submitScore;
  window.torState         = () => state; // read-only access for custom form

  // ── Bootstrap ──────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    const board = document.getElementById('board');
    if (!board || !board.dataset.mode.startsWith('toroid')) return;

    board.classList.add('toroid-board');

    const rows    = parseInt(board.dataset.rows);
    const cols    = parseInt(board.dataset.cols);
    const mines   = parseInt(board.dataset.mines);
    const noGuess  = localStorage.getItem('torNoGuess')  === 'true';
    const chording = localStorage.getItem('chording') !== 'false';

    initGame(rows, cols, mines, noGuess, chording);

    document.getElementById('reset-btn').addEventListener('click', resetGame);

    // Load leaderboard on page open
    loadLeaderboard(torModeKey(board.dataset.mode), noGuess);
  });

})();
