/**
 * hexsweeper.js — Hexagonal Minesweeper
 *
 * Board geometry: axial coordinates (q, r), pointy-top hexagons.
 * A board of radius R contains all cells where max(|q|, |r|, |q+r|) <= R-1.
 * Cell count = 3R²−3R+1.
 *
 * Neighbours of (q,r): the 6 axial directions.
 * SVG rendering: pixel center = (S*sqrt3*(q + r/2),  S*1.5*r)  offset to canvas center.
 *
 * Depends on: minesweeper.js (getMineEmoji, getFlagEmoji, getNumColors loaded first).
 */
(function () {

  const SQRT3 = Math.sqrt(3);

  // ── State ──────────────────────────────────────────────────────────────────
  let state = {};

  function freshState(radius, mines) {
    const cells = buildCells(radius);
    return {
      radius,
      mines,
      cells,                    // Array of [q,r] in canonical order
      cellIndex: buildCellIndex(cells),  // "q,r" -> array index
      board:     new Map(),     // "q,r" -> mine count (-1 if mine)
      revealed:  new Set(),     // "q,r" strings
      flagged:   new Set(),     // "q,r" strings
      qflagged:  new Set(),     // "q,r" question-mark flags
      minesLeft: mines,
      started:   false,
      over:      false,
      won:       false,
      elapsed:   0,
      timerID:   null,
      startTime: null,
      timeMs:    null,
      boardHash: null,
      bbbv:      null,
      leftClicks:  0,
      rightClicks: 0,
      chordClicks: 0,
    };
  }

  // ── Hex geometry helpers ───────────────────────────────────────────────────

  function buildCells(R) {
    const out = [];
    for (let r = -(R - 1); r <= R - 1; r++) {
      for (let q = -(R - 1); q <= R - 1; q++) {
        if (Math.abs(q) <= R - 1 && Math.abs(r) <= R - 1 && Math.abs(q + r) <= R - 1)
          out.push([q, r]);
      }
    }
    // canonical sort: r then q
    out.sort((a, b) => a[1] !== b[1] ? a[1] - b[1] : a[0] - b[0]);
    return out;
  }

  function buildCellIndex(cells) {
    const idx = new Map();
    cells.forEach(([q, r], i) => idx.set(`${q},${r}`, i));
    return idx;
  }

  function key(q, r) { return `${q},${r}`; }

  const HEX_DIRS = [[1,0],[-1,0],[0,1],[0,-1],[1,-1],[-1,1]];

  function neighbours(q, r, R) {
    const out = [];
    for (const [dq, dr] of HEX_DIRS) {
      const nq = q + dq, nr = r + dr;
      if (Math.abs(nq) <= R - 1 && Math.abs(nr) <= R - 1 && Math.abs(nq + nr) <= R - 1)
        out.push([nq, nr]);
    }
    return out;
  }

  // ── Board hash (canonical bit-array over sorted cells) ────────────────────

  function calcBoardHash(cells, mineSet) {
    const n    = cells.length;
    const bits = new Uint8Array(Math.ceil(n / 8));
    for (let i = 0; i < n; i++) {
      const [q, r] = cells[i];
      if (mineSet.has(key(q, r))) bits[i >> 3] |= (1 << (7 - (i & 7)));
    }
    let s = '';
    for (let i = 0; i < bits.length; i++) s += String.fromCharCode(bits[i]);
    return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }

  // ── Mine placement ─────────────────────────────────────────────────────────

  function placeMines(cells, mines, safeKey) {
    const pool = cells.map(([q, r]) => key(q, r)).filter(k => k !== safeKey);
    for (let i = pool.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [pool[i], pool[j]] = [pool[j], pool[i]];
    }
    return new Set(pool.slice(0, mines));
  }

  function buildBoard(cells, mineSet, R) {
    const board = new Map();
    for (const [q, r] of cells) {
      const k = key(q, r);
      if (mineSet.has(k)) { board.set(k, -1); continue; }
      let count = 0;
      for (const [nq, nr] of neighbours(q, r, R))
        if (mineSet.has(key(nq, nr))) count++;
      board.set(k, count);
    }
    return board;
  }

  // ── 3BV ───────────────────────────────────────────────────────────────────

  function calc3BV(cells, board, mineSet, R) {
    const covered = new Set();
    let bbbv = 0;
    for (const [q, r] of cells) {
      const k = key(q, r);
      if (board.get(k) !== 0 || covered.has(k) || mineSet.has(k)) continue;
      bbbv++;
      const queue = [[q, r]];
      covered.add(k);
      while (queue.length) {
        const [cq, cr] = queue.shift();
        for (const [nq, nr] of neighbours(cq, cr, R)) {
          const nk = key(nq, nr);
          if (covered.has(nk) || mineSet.has(nk)) continue;
          covered.add(nk);
          if (board.get(nk) === 0) queue.push([nq, nr]);
        }
      }
    }
    for (const [q, r] of cells) {
      const k = key(q, r);
      if (board.get(k) > 0 && !covered.has(k)) bbbv++;
    }
    return bbbv;
  }

  // ── SVG rendering ──────────────────────────────────────────────────────────

  const SVG_NS = 'http://www.w3.org/2000/svg';

  let cellSize = 28;   // pixel radius of each hex (center to vertex)
  let svgEl    = null;

  function hexCenter(q, r) {
    const x = cellSize * SQRT3 * (q + r / 2);
    const y = cellSize * 1.5 * r;
    return [x, y];
  }

  function hexPoints(cx, cy, s) {
    const pts = [];
    for (let i = 0; i < 6; i++) {
      const angle = Math.PI / 180 * (60 * i + 30);
      pts.push(`${(cx + s * Math.cos(angle)).toFixed(2)},${(cy + s * Math.sin(angle)).toFixed(2)}`);
    }
    return pts.join(' ');
  }

  function chooseSize(R) {
    // Fit the SVG within ~min(window.innerWidth-40, 540) px
    const maxW = Math.min(window.innerWidth - 40, 540);
    // Board width ≈ SQRT3 * cellSize * (2R-1)
    const fit  = Math.floor(maxW / (SQRT3 * (2 * R - 1)));
    return Math.max(16, Math.min(32, fit));
  }

  function buildSVG(R) {
    cellSize = chooseSize(R);
    const wrap = document.getElementById('hex-board-wrap');
    if (!wrap) return;
    wrap.innerHTML = '';

    // Compute bounding box
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const [q, r] of state.cells) {
      const [cx, cy] = hexCenter(q, r);
      minX = Math.min(minX, cx - cellSize);
      maxX = Math.max(maxX, cx + cellSize);
      minY = Math.min(minY, cy - cellSize);
      maxY = Math.max(maxY, cy + cellSize);
    }
    const pad = 4;
    const W = maxX - minX + pad * 2;
    const H = maxY - minY + pad * 2;
    const ox = -minX + pad;   // offset so (0,0) maps to right place
    const oy = -minY + pad;

    svgEl = document.createElementNS(SVG_NS, 'svg');
    svgEl.setAttribute('width',   W.toFixed(0));
    svgEl.setAttribute('height',  H.toFixed(0));
    svgEl.setAttribute('viewBox', `0 0 ${W.toFixed(0)} ${H.toFixed(0)}`);
    svgEl.id = 'hex-svg';

    for (const [q, r] of state.cells) {
      const [cx, cy] = hexCenter(q, r);
      const g = document.createElementNS(SVG_NS, 'g');
      g.dataset.q = q;
      g.dataset.r = r;
      g.classList.add('hex-cell', 'hex-hidden');

      const poly = document.createElementNS(SVG_NS, 'polygon');
      poly.setAttribute('points', hexPoints(cx + ox, cy + oy, cellSize - 1.5));
      poly.classList.add('hex-poly');

      const txt = document.createElementNS(SVG_NS, 'text');
      txt.setAttribute('x', (cx + ox).toFixed(2));
      txt.setAttribute('y', (cy + oy).toFixed(2));
      txt.setAttribute('text-anchor', 'middle');
      txt.setAttribute('dominant-baseline', 'central');
      txt.classList.add('hex-label');
      txt.style.fontSize = `${Math.round(cellSize * 0.72)}px`;

      g.appendChild(poly);
      g.appendChild(txt);

      g.addEventListener('click',       e => handleClick(e, q, r));
      g.addEventListener('contextmenu', e => handleRightClick(e, q, r));

      // Touch: long-press = flag
      let touchTimer = null;
      g.addEventListener('touchstart', e => {
        touchTimer = setTimeout(() => {
          touchTimer = null;
          handleRightClick(e, q, r);
        }, 500);
      }, { passive: true });
      g.addEventListener('touchend', e => {
        if (touchTimer) {
          clearTimeout(touchTimer);
          touchTimer = null;
          handleClick(e, q, r);
        }
      });
      g.addEventListener('touchmove', () => { clearTimeout(touchTimer); touchTimer = null; });

      svgEl.appendChild(g);
    }
    wrap.appendChild(svgEl);
  }

  function cellGroup(q, r) {
    if (!svgEl) return null;
    return svgEl.querySelector(`[data-q="${q}"][data-r="${r}"]`);
  }

  function renderCell(q, r) {
    const g = cellGroup(q, r);
    if (!g) return;
    const k   = key(q, r);
    const val = state.board.get(k);

    // Reset classes
    g.className.baseVal = 'hex-cell';

    const txt = g.querySelector('.hex-label');

    if (state.flagged.has(k)) {
      g.classList.add('hex-flagged');
      txt.textContent = getFlagEmoji();
      return;
    }
    if (state.qflagged.has(k)) {
      g.classList.add('hex-qflagged');
      txt.textContent = '?';
      return;
    }
    if (!state.revealed.has(k)) {
      g.classList.add('hex-hidden');
      txt.textContent = '';
      return;
    }
    g.classList.add('hex-revealed');
    if (val === -1) {
      g.classList.add(state._explodedKey === k ? 'hex-detonated' : 'hex-mine');
      txt.textContent = getMineEmoji();
    } else if (val === 0) {
      txt.textContent = '';
    } else {
      txt.textContent = val;
      const colors = getNumColors();
      txt.style.fill  = colors[val] || '#fff';
      txt.style.color = colors[val] || '#fff';
    }
  }

  // ── Timer ──────────────────────────────────────────────────────────────────

  function startTimer() {
    if (state.timerID) return;
    state.timerID = setInterval(() => {
      state.elapsed = Math.min(state.elapsed + 1, 999);
      document.getElementById('hex-timer').textContent =
        String(state.elapsed).padStart(3, '0');
    }, 1000);
  }

  function stopTimer() {
    clearInterval(state.timerID);
    state.timerID = null;
  }

  // ── Reveal logic ───────────────────────────────────────────────────────────

  function revealCell(q, r) {
    const k = key(q, r);
    if (state.over || state.revealed.has(k) || state.flagged.has(k)) return;

    if (!state.started) {
      const mineSet    = placeMines(state.cells, state.mines, k);
      state.board      = buildBoard(state.cells, mineSet, state.radius);
      state._mineSet   = mineSet;
      state.started    = true;
      state.startTime  = performance.now();
      state.boardHash  = calcBoardHash(state.cells, mineSet);
      state.bbbv       = calc3BV(state.cells, state.board, mineSet, state.radius);
      startTimer();
    }

    if (state.board.get(k) === -1) { boom(q, r); return; }

    const queue = [[q, r]];
    while (queue.length) {
      const [cq, cr] = queue.shift();
      const ck = key(cq, cr);
      if (state.revealed.has(ck)) continue;
      state.revealed.add(ck);
      renderCell(cq, cr);
      if (state.board.get(ck) === 0) {
        for (const [nq, nr] of neighbours(cq, cr, state.radius)) {
          if (!state.revealed.has(key(nq, nr)) && !state.flagged.has(key(nq, nr)))
            queue.push([nq, nr]);
        }
      }
    }
    checkWin();
  }

  // ── Chord ──────────────────────────────────────────────────────────────────

  function chordCell(q, r) {
    const k = key(q, r);
    if (!state.revealed.has(k) || state.board.get(k) <= 0) return;
    const nb    = neighbours(q, r, state.radius);
    const flags = nb.filter(([nq, nr]) => state.flagged.has(key(nq, nr))).length;
    if (flags === state.board.get(k)) {
      state.chordClicks++;
      nb.forEach(([nq, nr]) => revealCell(nq, nr));
    }
  }

  // ── Flag ───────────────────────────────────────────────────────────────────

  function flagCell(q, r) {
    if (state.over) return;
    const k = key(q, r);
    if (state.revealed.has(k)) return;
    if (state.flagged.has(k)) {
      state.flagged.delete(k);
      state.qflagged.add(k);
      state.minesLeft++;
    } else if (state.qflagged.has(k)) {
      state.qflagged.delete(k);
    } else {
      state.flagged.add(k);
      state.minesLeft--;
    }
    document.getElementById('hex-mines').textContent =
      String(state.minesLeft).padStart(3, '0');
    renderCell(q, r);
  }

  // ── Win / Loss ─────────────────────────────────────────────────────────────

  function boom(q, r) {
    state.over   = true;
    state._explodedKey = key(q, r);
    state.timeMs = state.startTime ? Math.round(performance.now() - state.startTime) : null;
    stopTimer();
    for (const [mq, mr] of state.cells) {
      const mk = key(mq, mr);
      if (state._mineSet.has(mk)) {
        state.revealed.add(mk);
        renderCell(mq, mr);
      }
    }
    document.getElementById('hex-reset').textContent = '😵';
    showOverlay('💥 Game Over', false);
  }

  function checkWin() {
    const totalCells = state.cells.length;
    if (totalCells - state.revealed.size === state.mines) {
      state.over   = true;
      state.won    = true;
      state.timeMs = state.startTime ? Math.round(performance.now() - state.startTime) : null;
      stopTimer();
      document.getElementById('hex-reset').textContent = '😎';
      // Auto-flag remaining mines
      for (const [mq, mr] of state.cells) {
        const mk = key(mq, mr);
        if (state._mineSet && state._mineSet.has(mk) && !state.flagged.has(mk)) {
          state.flagged.add(mk);
          renderCell(mq, mr);
        }
      }
      document.getElementById('hex-mines').textContent = '000';
      showOverlay(`🎉 You Won! — ${state.elapsed}s`, true);
    }
  }

  // ── Click handlers ─────────────────────────────────────────────────────────

  function handleClick(e, q, r) {
    e.preventDefault();
    if (state.over) return;
    const k = key(q, r);
    if (state.revealed.has(k)) {
      chordCell(q, r);
    } else if (!state.flagged.has(k) && !state.qflagged.has(k)) {
      state.leftClicks++;
      revealCell(q, r);
    }
  }

  function handleRightClick(e, q, r) {
    e.preventDefault();
    if (state.over) return;
    state.rightClicks++;
    flagCell(q, r);
  }

  // ── Score submission ───────────────────────────────────────────────────────

  async function submitScore(autoName) {
    const boardEl = document.getElementById('hex-board-wrap');
    const msgEl   = document.getElementById('hex-score-msg');
    const nameEl  = document.getElementById('hex-player-name');
    const name    = autoName || nameEl?.value.trim();
    if (!name) { if (msgEl) msgEl.textContent = '⚠️ Please enter your name.'; return; }

    const hexMode = hexModeKey(boardEl.dataset.mode);
    const payload = {
      name,
      hex_mode:     hexMode,
      time_secs:    state.elapsed,
      time_ms:      state.timeMs,
      radius:       state.radius,
      mines:        state.mines,
      board_hash:   state.boardHash,
      bbbv:         state.bbbv,
      left_clicks:  state.leftClicks,
      right_clicks: state.rightClicks,
      chord_clicks: state.chordClicks,
    };

    try {
      const res = await fetch('/api/hexsweeper-scores', {
        method:  'POST',
        headers: {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
        body:    JSON.stringify(payload),
      });
      if (res.ok) {
        if (msgEl) msgEl.textContent = `✅ Score saved for ${name}!`;
        if (nameEl) nameEl.disabled = true;
        const btn = document.querySelector('#hex-score-form button');
        if (btn) btn.disabled = true;
        loadLeaderboard(hexMode);
      } else {
        const err = await res.json();
        if (msgEl) msgEl.textContent = `❌ ${err.detail || 'Could not save score.'}`;
      }
    } catch {
      if (msgEl) msgEl.textContent = '❌ Network error. Score not saved.';
    }
  }

  function hexModeKey(dataMode) {
    const map = {
      'hex-beginner':     'beginner',
      'hex-intermediate': 'intermediate',
      'hex-expert':       'expert',
      'hex-custom':       'custom',
    };
    return map[dataMode] || 'beginner';
  }

  // ── Overlay ────────────────────────────────────────────────────────────────

  function showOverlay(msg, won) {
    let el = document.getElementById('hex-overlay');
    if (!el) {
      el = document.createElement('div');
      el.id = 'hex-overlay';
      (document.getElementById('hex-result') || document.getElementById('hex-board-wrap')).appendChild(el);
    }
    el.className = won ? 'overlay win' : 'overlay loss';

    const boardEl  = document.getElementById('hex-board-wrap');
    const username = boardEl.dataset.username || '';
    const hexMode  = hexModeKey(boardEl.dataset.mode);

    let scoreForm = '';
    if (won) {
      if (username) {
        scoreForm = `<div id="hex-score-msg" style="font-size:0.9rem">Saving score…</div>`;
      } else {
        const loginHref = '/auth/login?next=' + encodeURIComponent(window.location.pathname + window.location.search);
        scoreForm = `
          <div id="hex-score-form" class="overlay-score-form">
            <input id="hex-player-name" type="text" maxlength="32"
                   placeholder="Enter your name" autocomplete="off" />
            <button onclick="hexSubmitScore()">Save Score</button>
          </div>
          <div id="hex-score-msg" style="font-size:0.85rem;min-height:1.2em"></div>
          <div class="overlay-guest-warning">🎉 Congratulations! <a href="${loginHref}" onclick="guestLoginAndSave(event,'${loginHref}','hexSubmitScore','hex-player-name')">Login with Google</a> or your score will vanish at 0:00 UTC.</div>
        `;
      }
    }

    el.innerHTML = `
      <span>${msg}</span>
      ${scoreForm}
      <button onclick="hexResetGame()">Play Again</button>
    `;
    el.style.display = 'flex';

    if (won && username) {
      submitScore(username);
    } else if (won) {
      setTimeout(() => {
        const inp = document.getElementById('hex-player-name');
        if (inp) {
          inp.focus();
          inp.addEventListener('keydown', e => { if (e.key === 'Enter') hexSubmitScore(); });
        }
      }, 100);
    }
  }

  // ── Leaderboard ────────────────────────────────────────────────────────────

  async function loadLeaderboard(hexMode) {
    const el = document.getElementById('hex-lb-content');
    if (!el) return;
    el.innerHTML = '<div class="lb-loading">Loading…</div>';
    try {
      const res  = await fetch(`/api/hexsweeper-scores/${hexMode}?period=daily`);
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
        return `
        <tr class="${i < 3 ? 'top-' + (i + 1) : ''}">
          <td class="lb-rank">${medals[i] || '#' + (i + 1)}</td>
          <td class="lb-name">${nameCell}</td>
          <td class="lb-time">${fmtTime(s)}</td>
          <td class="lb-board">R${s.radius}</td>
          <td class="lb-mines">${s.mines}</td>
          <td class="lb-stat">${s.bbbv ?? '—'}</td>
          <td class="lb-stat">${fmtBbbvS(s)}</td>
          <td class="lb-stat">${fmtEff(s)}</td>
          <td class="lb-date">${s.created_at}</td>
        </tr>`;
      }).join('');
      el.innerHTML = `
        <div class="lb-table-wrap">
          <table class="lb-table">
            <thead><tr>
              <th>#</th><th>Name</th><th>Time</th><th>Board</th><th>Mines</th>
              <th class="lb-th-stat" data-tip="Minimum clicks to solve">3BV</th>
              <th class="lb-th-stat" data-tip="3BV per second">3BV/s</th>
              <th class="lb-th-stat" data-tip="Efficiency: 3BV ÷ left+chord clicks">Eff</th>
              <th>Date</th>
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

  // ── Init / Reset ───────────────────────────────────────────────────────────

  function hexInitGame(radius, mines) {
    stopTimer();
    state = freshState(radius, mines);
    document.getElementById('hex-mines').textContent = String(mines).padStart(3, '0');
    document.getElementById('hex-timer').textContent = '000';
    document.getElementById('hex-reset').textContent = '🙂';
    buildSVG(radius);
  }

  // ── Public API ─────────────────────────────────────────────────────────────

  window.hexResetGame = function () {
    const wrap = document.getElementById('hex-board-wrap');
    hexInitGame(
      parseInt(wrap.dataset.radius),
      parseInt(wrap.dataset.mines),
    );
  };

  window.hexSubmitScore = function () { submitScore(null); };

  // ── Boot ───────────────────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', () => {
    const wrap = document.getElementById('hex-board-wrap');
    if (!wrap) return;
    const radius = parseInt(wrap.dataset.radius);
    const mines  = parseInt(wrap.dataset.mines);
    hexInitGame(radius, mines);
    const hexMode = hexModeKey(wrap.dataset.mode);
    loadLeaderboard(hexMode);
  });

})();
