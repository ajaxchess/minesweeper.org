/**
 * duel.js — Head-to-head Minesweeper client.
 * Loaded only on the duel page. minesweeper.js is also loaded but its
 * bootstrap guard skips init when data-mode="duel".
 */

// getNumColors() is defined in minesweeper.js — reuse it directly.

document.addEventListener('DOMContentLoaded', () => {
  const boardEl = document.getElementById('board');
  if (!boardEl || !['duel', 'pvp', 'pvp-bot', 'pvp-beta', 'pvp-bot-beta'].includes(boardEl.dataset.mode)) return;

  // ── Config ────────────────────────────────────────────────────────────────
  const ROWS        = parseInt(boardEl.dataset.rows);
  const COLS        = parseInt(boardEl.dataset.cols);
  const MINES       = parseInt(boardEl.dataset.mines || '0');
  const SAFE_CELLS  = ROWS * COLS - MINES;
  const GAME_ID     = boardEl.dataset.gameId;
  const PLAYER_ID   = boardEl.dataset.playerId;
  const MODE        = boardEl.dataset.mode;
  const IS_BETA     = MODE === 'pvp-beta' || MODE === 'pvp-bot-beta';
  const IS_PVP      = MODE === 'pvp' || MODE === 'pvp-beta';
  const IS_BOT      = MODE === 'pvp-bot' || MODE === 'pvp-bot-beta';
  const IS_CREATOR  = boardEl.dataset.isCreator === 'true';
  const SUBMODE     = boardEl.dataset.submode || 'standard';
  const BOT_DIFF    = boardEl.dataset.botDifficulty || 'medium';
  const OPP_DELAY_MS   = (parseInt(boardEl.dataset.oppDelay || '0')) * 1000;
  const MY_PUBLIC_ID   = boardEl.dataset.userPublicId || '';

  // ── Local state ───────────────────────────────────────────────────────────
  let revealed   = Array.from({length: ROWS}, () => Array(COLS).fill(false));
  let flagged    = Array.from({length: ROWS}, () => Array(COLS).fill(0));
  let boardVals  = Array.from({length: ROWS}, () => Array(COLS).fill(null));
  let gameActive = false;
  let exploded   = false;
  let timerID    = null;
  let elapsed    = 0;

  // ── Debug panel state (Standard PvP only) ─────────────────────────────────
  const DEBUG_CAPABLE = IS_PVP && SUBMODE === 'standard';
  let debugEnabled    = false;
  let debugClickCount = 0;
  let debugPending    = [];   // moves awaiting a server response
  let debugLog        = [];   // completed moves, newest first

  window.toggleDebug = function() {
    if (!DEBUG_CAPABLE) return;
    debugEnabled = !debugEnabled;
    const panel = document.getElementById('debug-panel');
    const btn   = document.getElementById('debug-toggle-btn');
    if (panel) panel.style.display = debugEnabled ? 'flex' : 'none';
    if (btn)   btn.classList.toggle('active', debugEnabled);
  };

  function _debugAddMove(r, c, type, outcome, cls) {
    debugClickCount++;
    const entry = { num: debugClickCount, r: r + 1, c: c + 1, type, outcome, cls };
    debugLog.unshift(entry);
    _debugRender();
    return entry;
  }

  function _debugAddPending(r, c, type) {
    debugClickCount++;
    const entry = { num: debugClickCount, r: r + 1, c: c + 1, type, outcome: '…', cls: 'dm-pending' };
    debugPending.push(entry);
    debugLog.unshift(entry);
    _debugRender();
    return entry;
  }

  function _debugResolve(outcome, cls) {
    const entry = debugPending.shift();
    if (!entry) return;
    entry.outcome = outcome;
    entry.cls     = cls;
    _debugRender();
  }

  function _debugRender() {
    const el = document.getElementById('debug-log');
    if (!el) return;
    el.innerHTML = debugLog.slice(0, 60).map(e =>
      `<li class="${e.cls}">${e.num}. R${e.r}C${e.c} ${e.type} → ${e.outcome}</li>`
    ).join('');
  }

  // ── Opponent board state ──────────────────────────────────────────────────
  const oppBoardEl  = document.getElementById('opp-board');
  const oppWaitEl   = document.getElementById('opp-board-waiting');
  let oppRevealed   = Array.from({length: ROWS}, () => Array(COLS).fill(false));
  let oppBoardVals  = Array.from({length: ROWS}, () => Array(COLS).fill(null));
  let oppExploded   = false;
  // Queue: [{applyAt: ms timestamp, cells: [[r,c,val],...], exploded: bool, cleared: bool}]
  const pendingOppUpdates = [];

  // ── F70: Frontier distance matrices ──────────────────────────────────────
  // minDist[r][c] = min Chebyshev distance to any revealed cell (Infinity = unreachable)
  let minDist    = Array.from({length: ROWS}, () => Array(COLS).fill(Infinity));
  let oppMinDist = Array.from({length: ROWS}, () => Array(COLS).fill(Infinity));

  // ── F71: Mine-hit counters ────────────────────────────────────────────────
  let myMineHits  = 0;
  let oppMineHits = 0;

  // Rebuild a distance matrix from scratch based on current revealed state (F71: after reset).
  function recomputeMinDist(distMatrix, revMatrix) {
    for (let r = 0; r < ROWS; r++)
      for (let c = 0; c < COLS; c++)
        distMatrix[r][c] = revMatrix[r][c] ? 0 : Infinity;
    for (let r = 0; r < ROWS; r++) {
      for (let c = 0; c < COLS; c++) {
        if (!revMatrix[r][c]) continue;
        for (let dr = -2; dr <= 2; dr++) {
          for (let dc = -2; dc <= 2; dc++) {
            const nr = r + dr, nc = c + dc;
            if (nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS && !revMatrix[nr][nc]) {
              const d = Math.max(Math.abs(dr), Math.abs(dc));
              if (d < distMatrix[nr][nc]) distMatrix[nr][nc] = d;
            }
          }
        }
      }
    }
  }

  // Update a distance matrix given newly revealed cells; returns cells whose dist changed.
  function updateMinDist(newlyCells, distMatrix) {
    const changed = [];
    newlyCells.forEach(cell => {
      const r = cell[0], c = cell[1];
      distMatrix[r][c] = 0;
      for (let dr = -2; dr <= 2; dr++) {
        for (let dc = -2; dc <= 2; dc++) {
          const nr = r + dr, nc = c + dc;
          if (nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS) {
            const d = Math.max(Math.abs(dr), Math.abs(dc));
            if (d > 0 && d < distMatrix[nr][nc]) {
              distMatrix[nr][nc] = d;
              changed.push([nr, nc]);
            }
          }
        }
      }
    });
    return changed;
  }

  // ── Stat card (F69) ───────────────────────────────────────────────────────
  let oppPublicId   = null;
  const statCardEl  = document.getElementById('pvp-stat-card');
  const statCache   = {};   // public_id → fetched data
  let   statHideTimer = null;

  function showStatCard(publicId, anchorEl) {
    if (!IS_BETA || !publicId || !statCardEl) return;
    const fetch_ = (id) => {
      if (statCache[id]) { renderStatCard(statCache[id], anchorEl); return; }
      fetch(`/api/pvp/player-card/${id}`)
        .then(r => r.json())
        .then(data => { if (data && data.name) { statCache[id] = data; renderStatCard(data, anchorEl); } })
        .catch(() => {});
    };
    fetch_(publicId);
  }

  function renderStatCard(data, anchorEl) {
    const nameEl = statCardEl.querySelector('.pvp-stat-card-name');
    const rowsEl = statCardEl.querySelector('.pvp-stat-card-rows');
    nameEl.textContent = data.name || '—';
    const rows = [];
    if (data.elo   != null) rows.push(['Elo',    data.elo]);
    if (data.wins  != null) rows.push(['Wins',   data.wins]);
    if (data.losses!= null) rows.push(['Losses', data.losses]);
    if (data.best_time != null) rows.push(['Best time', data.best_time + 's']);
    rowsEl.innerHTML = rows.map(([label, val]) =>
      `<div class="pvp-stat-row"><span class="psr-label">${label}</span><span class="psr-value">${val}</span></div>`
    ).join('');
    positionStatCard(anchorEl);
    statCardEl.style.display = 'block';
  }

  function positionStatCard(anchorEl) {
    const rect = anchorEl.getBoundingClientRect();
    const cardW = 180;
    let left = rect.left + rect.width / 2 - cardW / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - cardW - 8));
    statCardEl.style.left = left + 'px';
    statCardEl.style.top  = (rect.bottom + 6) + 'px';
  }

  function hideStatCard() {
    if (statCardEl) statCardEl.style.display = 'none';
  }

  function attachStatCard(el, getPublicId) {
    if (!IS_BETA) return;
    el.addEventListener('mouseenter', () => {
      clearTimeout(statHideTimer);
      const pid = getPublicId();
      if (pid) { el.classList.add('has-card'); showStatCard(pid, el); }
    });
    el.addEventListener('mouseleave', () => {
      statHideTimer = setTimeout(hideStatCard, 150);
    });
  }

  // ── F71: Mine-hit helpers ─────────────────────────────────────────────────
  function updateMineHits(count, isMe) {
    const el = document.getElementById(isMe ? 'my-mine-hits' : 'opp-mine-hits');
    if (!el) return;
    el.textContent   = `💥 ${count}`;
    el.style.display = 'inline';
  }

  // Animate a mine hit on either own board or opponent's board.
  // t=0: red flash on hit cell; t=250ms: 3×3 ring; t=750ms: apply reset + rerender + number flash.
  function animateMineHit(hr, hc, resetCells, updatedValues, isOpp) {
    const getCellFn = isOpp ? oppCellEl : cellEl;
    const rev       = isOpp ? oppRevealed  : revealed;
    const vals      = isOpp ? oppBoardVals : boardVals;
    const dist      = isOpp ? oppMinDist   : minDist;
    const renderFn  = isOpp ? renderOppCell : renderCell;

    // t=0: flash the hit cell red
    const hitEl = getCellFn(hr, hc);
    if (hitEl) hitEl.classList.add('mine-explode');

    // t=250ms: expand ring around hit cell
    setTimeout(() => {
      for (let dr = -1; dr <= 1; dr++) {
        for (let dc = -1; dc <= 1; dc++) {
          if (dr === 0 && dc === 0) continue;
          const nr = hr + dr, nc = hc + dc;
          if (nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS) {
            const el = getCellFn(nr, nc);
            if (el) el.classList.add('mine-ring');
          }
        }
      }
    }, 250);

    // t=750ms: apply reset, update values, recompute frontier, re-render
    setTimeout(() => {
      // Remove animation classes
      if (hitEl) hitEl.classList.remove('mine-explode');
      for (let dr = -1; dr <= 1; dr++) {
        for (let dc = -1; dc <= 1; dc++) {
          if (dr === 0 && dc === 0) continue;
          const nr = hr + dr, nc = hc + dc;
          if (nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS) {
            const el = getCellFn(nr, nc);
            if (el) el.classList.remove('mine-ring');
          }
        }
      }

      // Unrevealed the reset cells
      resetCells.forEach(([r, c]) => {
        rev[r][c]  = false;
        vals[r][c] = null;
      });

      // Apply updated values (own board only — boards diverge intentionally)
      const flashCells = new Set();
      if (updatedValues) {
        Object.entries(updatedValues).forEach(([key, val]) => {
          const [r, c] = key.split(',').map(Number);
          vals[r][c] = val;
          if (rev[r][c] && val > 0) flashCells.add(key);
        });
      }

      // Recompute frontier from scratch (cells were removed from revealed set)
      if (IS_BETA) {
        recomputeMinDist(dist, rev);
        // Frontier shrinkage may extend well beyond the local 5×5 — re-render
        // every unrevealed cell so stale frontier/locked CSS classes can't silently
        // block clicks on cells that appear highlighted but are now outside frontier.
        for (let r = 0; r < ROWS; r++)
          for (let c = 0; c < COLS; c++)
            if (!rev[r][c]) renderFn(r, c);
      }

      // Re-render the local 5×5 for updated board values and flash animation
      for (let dr = -2; dr <= 2; dr++) {
        for (let dc = -2; dc <= 2; dc++) {
          const nr = hr + dr, nc = hc + dc;
          if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
          renderFn(nr, nc);
          if (flashCells.has(`${nr},${nc}`)) {
            const el = getCellFn(nr, nc);
            if (el) {
              el.classList.add('number-flash');
              setTimeout(() => el.classList.remove('number-flash'), 800);
            }
          }
        }
      }
    }, 750);
  }

  // ── Build player board DOM ────────────────────────────────────────────────
  function buildBoard() {
    boardEl.innerHTML = '';
    boardEl.style.setProperty('--cols', COLS);
    for (let r = 0; r < ROWS; r++) {
      for (let c = 0; c < COLS; c++) {
        const cell = document.createElement('div');
        cell.className = 'cell hidden';
        cell.dataset.r = r;
        cell.dataset.c = c;
        cell.addEventListener('click',       () => onReveal(r, c));
        cell.addEventListener('dblclick',    () => onChord(r, c));
        cell.addEventListener('contextmenu', e  => { e.preventDefault(); onFlag(r, c); });
        boardEl.appendChild(cell);
      }
    }
    // Mouse-position tracking for debug panel
    if (DEBUG_CAPABLE) {
      boardEl.addEventListener('mousemove', e => {
        if (!debugEnabled) return;
        const posEl = document.getElementById('debug-position');
        if (!posEl) return;
        const cell = e.target.closest('[data-r][data-c]');
        if (cell) {
          posEl.textContent = `Row ${+cell.dataset.r + 1}, Col ${+cell.dataset.c + 1}`;
        } else {
          posEl.textContent = 'NA';
        }
      });
      boardEl.addEventListener('mouseleave', () => {
        if (!debugEnabled) return;
        const posEl = document.getElementById('debug-position');
        if (posEl) posEl.textContent = 'NA';
      });
    }
  }

  // ── Build opponent board DOM (read-only) ──────────────────────────────────
  function buildOppBoard() {
    if (!oppBoardEl) return;
    oppBoardEl.innerHTML = '';
    oppBoardEl.style.setProperty('--cols', COLS);
    for (let r = 0; r < ROWS; r++) {
      for (let c = 0; c < COLS; c++) {
        const cell = document.createElement('div');
        cell.className = 'cell hidden opp-cell';
        cell.dataset.r = r;
        cell.dataset.c = c;
        oppBoardEl.appendChild(cell);
      }
    }
  }

  function cellEl(r, c) {
    return boardEl.querySelector(`[data-r="${r}"][data-c="${c}"]`);
  }

  function oppCellEl(r, c) {
    return oppBoardEl ? oppBoardEl.querySelector(`[data-r="${r}"][data-c="${c}"]`) : null;
  }

  function renderCell(r, c) {
    const el  = cellEl(r, c);
    const val = boardVals[r][c];
    el.className = 'cell';

    if (!revealed[r][c]) {
      if (flagged[r][c] === 1) {
        el.classList.add('flagged');
        el.textContent = getFlagEmoji();
      } else if (flagged[r][c] === 2) {
        el.classList.add('question');
        el.textContent = '❓';
      } else {
        el.textContent = '';
        if (IS_BETA) {
          const d = minDist[r][c];
          el.classList.add(d === 2 ? 'frontier' : (d > 2 ? 'locked' : 'hidden'));
        } else {
          el.classList.add('hidden');
        }
      }
      return;
    }
    el.classList.add('revealed');
    if (val === -1) {
      el.classList.add(exploded ? 'mine-detonated' : 'mine');
      el.textContent = getMineEmoji();
    } else if (val === 0) {
      el.textContent = '';
    } else {
      el.textContent = val;
      el.style.color = getNumColors()[val];
    }
  }

  function renderOppCell(r, c) {
    const el  = oppCellEl(r, c);
    if (!el) return;
    const val = oppBoardVals[r][c];
    el.className = 'cell opp-cell';

    if (!oppRevealed[r][c]) {
      el.textContent = '';
      if (IS_BETA) {
        const d = oppMinDist[r][c];
        el.classList.add(d === 2 ? 'frontier' : (d > 2 ? 'locked' : 'hidden'));
      } else {
        el.classList.add('hidden');
      }
      return;
    }
    el.classList.add('revealed');
    if (val === -1) {
      el.classList.add(oppExploded ? 'mine-detonated' : 'mine');
      el.textContent = getMineEmoji();
    } else if (val === 0) {
      el.textContent = '';
    } else {
      el.textContent = val;
      el.style.color = getNumColors()[val];
    }
  }

  // ── Opponent board delayed flush ──────────────────────────────────────────
  function flushOppUpdates() {
    const now = Date.now();
    while (pendingOppUpdates.length && pendingOppUpdates[0].applyAt <= now) {
      const batch = pendingOppUpdates.shift();

      // F71: mine-hit batch on opponent board
      if (batch.type === 'mine_hit') {
        animateMineHit(batch.r, batch.c, batch.reset_cells, null, true);
        continue;
      }

      // F70: update opponent frontier before rendering
      let oppZoneChanged = [];
      if (IS_BETA) oppZoneChanged = updateMinDist(batch.cells, oppMinDist);
      const batchKeys = IS_BETA ? new Set(batch.cells.map(([r, c]) => `${r},${c}`)) : null;
      batch.cells.forEach(([r, c, val]) => {
        oppRevealed[r][c]  = true;
        oppBoardVals[r][c] = val;
        renderOppCell(r, c);
      });
      if (IS_BETA) {
        oppZoneChanged.forEach(([r, c]) => {
          if (!batchKeys.has(`${r},${c}`) && !oppRevealed[r][c]) renderOppCell(r, c);
        });
      }
      if (batch.exploded) {
        oppExploded = true;
      }
    }
  }

  setInterval(flushOppUpdates, 100);

  function showOppBoard() {
    if (oppWaitEl) oppWaitEl.style.display = 'none';
    if (oppBoardEl) oppBoardEl.style.display = 'grid';
  }

  // ── Timer ─────────────────────────────────────────────────────────────────
  function startTimer() {
    if (timerID) return;
    timerID = setInterval(() => {
      elapsed = Math.min(elapsed + 1, 999);
      document.getElementById('duel-timer').textContent =
        String(elapsed).padStart(3, '0');
    }, 1000);
  }

  function stopTimer() {
    clearInterval(timerID);
    timerID = null;
  }

  // ── Score display ─────────────────────────────────────────────────────────
  function updateScores(myScore, myTiles, oppScore, oppTiles) {
    if (myScore  != null) document.getElementById('my-score').textContent  = myScore;
    if (oppScore != null) document.getElementById('opp-score').textContent = oppScore;
    if (myTiles  != null) document.getElementById('my-tiles').textContent  = `${myTiles} tiles`;
    if (oppTiles != null) document.getElementById('opp-tiles').textContent = `${oppTiles} tiles`;
    if (IS_BETA && SAFE_CELLS > 0) {
      const myPctEl  = document.getElementById('my-pct');
      const oppPctEl = document.getElementById('opp-pct');
      if (myPctEl  && myTiles  != null) myPctEl.textContent  = Math.floor(myTiles  / SAFE_CELLS * 100) + '%';
      if (oppPctEl && oppTiles != null) oppPctEl.textContent = Math.floor(oppTiles / SAFE_CELLS * 100) + '%';
    }
  }

  // ── Actions ───────────────────────────────────────────────────────────────
  function onReveal(r, c) {
    if (!gameActive || revealed[r][c] || flagged[r][c] === 1 || exploded) {
      if (debugEnabled) _debugAddMove(r, c, 'L', revealed[r][c] ? 'already revealed' : 'blocked', 'dm-locked');
      return;
    }
    if (IS_BETA && minDist[r][c] > 2) {
      if (debugEnabled) _debugAddMove(r, c, 'L', 'outside playable area', 'dm-locked');
      return;
    }
    if (debugEnabled) _debugAddPending(r, c, 'L');
    ws.send(JSON.stringify({type: 'reveal', r, c}));
  }

  function onChord(r, c) {
    if (!gameActive || exploded) return;
    if (localStorage.getItem('chording') === 'false') return;
    if (!revealed[r][c] || boardVals[r][c] <= 0) return;
    const nbs = [];
    for (let dr = -1; dr <= 1; dr++)
      for (let dc = -1; dc <= 1; dc++) {
        if (dr === 0 && dc === 0) continue;
        const nr = r + dr, nc = c + dc;
        if (nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS) nbs.push([nr, nc]);
      }
    const flagCount = nbs.filter(([nr, nc]) => flagged[nr][nc] === 1).length;
    if (flagCount !== boardVals[r][c]) return;
    const toReveal = nbs.filter(([nr, nc]) => !flagged[nr][nc] && !revealed[nr][nc]);
    if (debugEnabled && toReveal.length) _debugAddPending(r, c, 'DL');
    toReveal.forEach(([nr, nc]) => ws.send(JSON.stringify({type: 'reveal', r: nr, c: nc})));
  }

  function onFlag(r, c) {
    if (!gameActive || revealed[r][c]) return;
    flagged[r][c] = (flagged[r][c] + 1) % 3;
    renderCell(r, c);
    if (debugEnabled) {
      const label = flagged[r][c] === 0 ? 'unflagged' : flagged[r][c] === 1 ? 'flag 🚩' : 'question ❓';
      _debugAddMove(r, c, 'R', label, 'dm-flag');
    }
  }

  function setStatus(msg) {
    document.getElementById('duel-status').textContent = msg;
  }

  function setOppName(name, publicId) {
    const scoreLabel = document.getElementById('opp-score-label');
    if (scoreLabel) scoreLabel.textContent = name;
    const boardLabel = document.getElementById('opp-board-label');
    if (boardLabel) {
      const badge = boardLabel.querySelector('.opp-board-delay-badge');
      boardLabel.textContent = '👁 ' + name;
      if (badge) boardLabel.appendChild(badge);
    }
    if (publicId) oppPublicId = publicId;
  }

  // Attach stat card hover to both score labels once (beta only)
  if (IS_BETA) {
    const myLabel  = document.querySelector('#my-score-box .score-label');
    const oppLabel = document.getElementById('opp-score-label');
    if (myLabel)  attachStatCard(myLabel,  () => MY_PUBLIC_ID);
    if (oppLabel) attachStatCard(oppLabel, () => oppPublicId);
  }

  // ── Overlay ───────────────────────────────────────────────────────────────
  function showDuelOverlay(html) {
    const ov = document.getElementById('duel-overlay');
    ov.innerHTML     = html;
    ov.style.display = 'flex';
  }

  // ── Start button (creator only) ───────────────────────────────────────────
  window.sendStart = function() {
    ws.send(JSON.stringify({type: 'start'}));
    document.getElementById('start-btn').style.display = 'none';
  };

  window.copyLink = function() {
    const inp = document.getElementById('share-link');
    navigator.clipboard.writeText(inp.value).catch(() => { inp.select(); });
    document.querySelector('#share-box button').textContent = 'Copied!';
  };

  window.requestRematch = function() {
    const btn = document.querySelector('.duel-rematch-btn');
    if (btn) btn.textContent = '⏳ Waiting for opponent…';
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({type: 'rematch'}));
    }
  };

  window.copyWatchLink = function() {
    const inp = document.getElementById('watch-link-inp');
    navigator.clipboard.writeText(inp.value).catch(() => { inp.select(); });
    document.querySelector('#watch-box button').textContent = 'Copied!';
  };

  // ── Chat ──────────────────────────────────────────────────────────────────
  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function appendChat(from, text, isMe) {
    const log = document.getElementById('duel-chat-log');
    if (!log) return;
    const div = document.createElement('div');
    div.className = 'duel-chat-msg' + (isMe ? ' duel-chat-msg-me' : '');
    div.innerHTML = `<span class="duel-chat-from">${escHtml(from)}:</span> <span class="duel-chat-text">${escHtml(text)}</span>`;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
  }

  function appendChatSystem(text) {
    const log = document.getElementById('duel-chat-log');
    if (!log) return;
    const div = document.createElement('div');
    div.className = 'duel-chat-system';
    div.textContent = text;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
  }

  window.sendChat = function() {
    const inp = document.getElementById('duel-chat-input');
    if (!inp) return;
    const text = inp.value.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({type: 'chat', text}));
    inp.value = '';
  };

  // ── WebSocket ─────────────────────────────────────────────────────────────
  const proto  = location.protocol === 'https:' ? 'wss' : 'ws';
  let wsPath;
  if (IS_BOT) {
    const botBase = IS_BETA ? '/ws/pvpbeta/bot' : '/ws/pvp/bot';
    wsPath = `${botBase}/${PLAYER_ID}?m=${SUBMODE}&d=${BOT_DIFF}`;
  } else if (IS_PVP) {
    const pvpBase = IS_BETA ? '/ws/pvpbeta' : '/ws/pvp';
    wsPath = SUBMODE === 'quick'
      ? `${pvpBase}/quick/${PLAYER_ID}`
      : `${pvpBase}/${PLAYER_ID}`;
  } else {
    wsPath = `/ws/${GAME_ID}/${PLAYER_ID}`;
  }
  const wsUrl = `${proto}://${location.host}${wsPath}`;

  let ws;
  let reconnectAttempts = 0;
  const MAX_RECONNECT   = 5;
  let   firstConnect    = true;

  function connectWs() {
    ws = new WebSocket(wsUrl);

    ws.addEventListener('open', () => {
      reconnectAttempts = 0;
      const playerName  = boardEl.dataset.username  || '';
      const playerEmail = boardEl.dataset.useremail || '';
      if (playerName) {
        ws.send(JSON.stringify({type: 'player_name', name: playerName, email: playerEmail}));
      }
      if (firstConnect && IS_CREATOR) {
        const link = `${location.origin}/duel/${GAME_ID}`;
        const inp  = document.getElementById('share-link');
        if (inp) inp.value = link;
        document.getElementById('share-box').style.display = 'flex';

        const watchInp = document.getElementById('watch-link-inp');
        if (watchInp) watchInp.value = `${location.origin}/duel/${GAME_ID}/watch`;
        const watchBox = document.getElementById('watch-box');
        if (watchBox) watchBox.style.display = 'flex';
      }
      firstConnect = false;
    });

  ws.addEventListener('message', e => {
    const msg = JSON.parse(e.data);

    switch (msg.type) {

      case 'queued':
        setStatus(`🔍 ${msg.msg} (${msg.queue_pos} in queue)`);
        break;

      case 'matched':
        setStatus('🎯 ' + msg.msg);
        if (IS_BETA) {
          const pName  = boardEl.dataset.username  || '';
          const pEmail = boardEl.dataset.useremail || '';
          if (pName) ws.send(JSON.stringify({type: 'player_name', name: pName, email: pEmail}));
        }
        break;

      case 'connected':
        setStatus(msg.msg);
        break;

      case 'ready':
        setStatus(msg.msg);
        if (IS_CREATOR) {
          const btn = document.getElementById('start-btn');
          if (btn) btn.style.display = 'inline-block';
        }
        break;

      case 'start': {
        setStatus('⚔️ Game on!');
        gameActive = true;
        appendChatSystem('⚔️ Game started — say hi!');
        showOppBoard();
        startTimer();
        // Render shared pre-revealed opening on both boards
        if (msg.prerev && msg.board_values) {
          // Apply state first, then compute frontier, then render everything
          msg.prerev.forEach(([r, c]) => {
            const val = msg.board_values[`${r},${c}`];
            revealed[r][c]     = true;
            boardVals[r][c]    = val;
            oppRevealed[r][c]  = true;
            oppBoardVals[r][c] = val;
          });
          if (IS_BETA) {
            updateMinDist(msg.prerev, minDist);
            updateMinDist(msg.prerev, oppMinDist);
          }
          // Full board render so frontier/locked classes are applied from the start
          for (let r = 0; r < ROWS; r++) {
            for (let c = 0; c < COLS; c++) {
              renderCell(r, c);
              renderOppCell(r, c);
            }
          }
        }
        if (msg.prerev_score != null) {
          updateScores(msg.prerev_score, msg.prerev ? msg.prerev.length : 0,
                       msg.prerev_score, msg.prerev ? msg.prerev.length : 0);
        }
        break;
      }

      case 'update': {
        const newCells   = msg.newly_revealed;
        const boardValsM = msg.board_values;
        // F70: update frontier distances before rendering so zone classes are correct
        let zoneChanged = [];
        if (IS_BETA) zoneChanged = updateMinDist(newCells, minDist);
        const newKeys = IS_BETA ? new Set(newCells.map(([r, c]) => `${r},${c}`)) : null;
        newCells.forEach(([r, c]) => {
          revealed[r][c]  = true;
          boardVals[r][c] = boardValsM[`${r},${c}`];
          renderCell(r, c);
        });
        // Re-render unrevealed neighbour cells whose zone class changed
        if (IS_BETA) {
          zoneChanged.forEach(([r, c]) => {
            if (!newKeys.has(`${r},${c}`) && !revealed[r][c]) renderCell(r, c);
          });
        }
        if (msg.exploded) {
          exploded = true;
          gameActive = false;
          stopTimer();
          setStatus('💥 You hit a mine! Waiting for opponent to finish…');
          if (debugEnabled) _debugResolve('💥 mine', 'dm-mine');
        } else {
          if (debugEnabled) _debugResolve(`safe ×${newCells.length}`, 'dm-safe');
        }
        updateScores(msg.score, msg.tiles, msg.opp_score, null);
        break;
      }

      case 'opp_update': {
        // Schedule opponent board reveal after delay
        const cells = msg.opp_newly_revealed || [];
        if (cells.length > 0 || msg.opp_exploded) {
          pendingOppUpdates.push({
            applyAt:  Date.now() + OPP_DELAY_MS,
            cells:    cells,
            exploded: msg.opp_exploded || false,
          });
        }
        // Score/tile count updates are immediate (no delay)
        updateScores(null, null, msg.opp_score, msg.opp_tiles);
        if (msg.opp_exploded) {
          setStatus('💥 Opponent hit a mine! Keep playing…');
        } else if (msg.opp_cleared) {
          setStatus('🎉 Opponent cleared their board! Keep playing…');
        }
        break;
      }

      case 'game_over': {
        stopTimer();
        gameActive = false;
        // Flush all remaining opponent updates immediately on game over
        pendingOppUpdates.forEach(batch => {
          batch.cells.forEach(([r, c, val]) => {
            oppRevealed[r][c]  = true;
            oppBoardVals[r][c] = val;
            renderOppCell(r, c);
          });
        });
        pendingOppUpdates.length = 0;

        const myScore  = msg.scores[PLAYER_ID] ?? 0;
        const oppId    = Object.keys(msg.scores).find(id => id !== PLAYER_ID);
        const oppScore = oppId ? msg.scores[oppId] : 0;
        updateScores(myScore, null, oppScore, null);

        let headline, sub;
        if (!msg.winner_id) {
          headline = '💥 Double KO!';
          sub      = 'Both players hit a mine.';
        } else if (msg.winner_id === PLAYER_ID) {
          headline = '🏆 You Win!';
          sub      = `Final score: ${myScore} vs ${oppScore}`;
        } else {
          headline = '😵 You Lose!';
          sub      = `Final score: ${myScore} vs ${oppScore}`;
        }

        const hashLine = msg.board_hash
          ? (function() {
              const p = new URLSearchParams({
                hash: msg.board_hash,
                rows: msg.rows, cols: msg.cols, mines: msg.mines,
              });
              return `<p class="result-hash">Board: <a href="/variants/replay/?${p}" target="_blank">${msg.board_hash.slice(0, 12)}…</a></p>`;
            })()
          : '';
        const rematchBtn = (!IS_PVP && !IS_BOT)
          ? `<button class="duel-play-again duel-rematch-btn" onclick="window.requestRematch()">🔄 Rematch</button>`
          : '';
        showDuelOverlay(`
          <div class="duel-result">
            <h2>${headline}</h2>
            <p>${sub}</p>
            <p class="result-time">Time: ${msg.elapsed}s</p>
            ${hashLine}
            ${rematchBtn}
            <a href="${IS_PVP ? '/pvp' : IS_BETA ? '/pvpbeta' : '/duel'}?m=${SUBMODE}" class="duel-play-again duel-play-again--secondary">⚔️ New Duel</a>
          </div>
        `);
        break;
      }

      case 'opp_disconnected':
        setStatus('⚠️ ' + msg.msg);
        stopTimer();
        gameActive = false;
        appendChatSystem('⚠️ Opponent disconnected.');
        break;

      case 'rematch_ready':
        location.href = `/duel/${msg.game_id}`;
        break;

      case 'watch_redirect':
        setStatus('👁 Game is full — joining as spectator…');
        setTimeout(() => {
          location.href = `/duel/${msg.game_id}/watch`;
        }, 1200);
        break;

      case 'opp_name':
        setOppName(msg.name || 'Opponent', msg.public_id || null);
        break;

      case 'mine_hit': {
        // Own board: mine struck, 3×3 reset, no game-over
        myMineHits = msg.mine_hits;
        updateMineHits(myMineHits, true);
        updateScores(msg.score, msg.tiles, msg.opp_score, null);
        if (debugEnabled) _debugResolve('💥 mine (reallocated)', 'dm-mine');
        animateMineHit(msg.r, msg.c, msg.reset_cells, msg.updated_values, false);
        break;
      }

      case 'opp_mine_hit': {
        // Opponent hit a mine — queue delayed animation on their board
        oppMineHits = msg.mine_hits;
        updateMineHits(oppMineHits, false);
        updateScores(null, null, msg.opp_score, msg.opp_tiles);
        pendingOppUpdates.push({
          applyAt:     Date.now() + OPP_DELAY_MS,
          type:        'mine_hit',
          r:           msg.r,
          c:           msg.c,
          reset_cells: msg.reset_cells,
        });
        break;
      }

      case 'error':
        setStatus('❌ ' + msg.msg);
        break;

      case 'chat':
        appendChat(msg.from, msg.text, msg.pid === PLAYER_ID);
        break;

      case 'reconnected': {
        // Server recognised our player_id and resumed the existing game.
        gameActive = msg.active !== false;
        // Restore own board
        msg.my_revealed.forEach(([r, c]) => {
          revealed[r][c]  = true;
          boardVals[r][c] = msg.board_values[`${r},${c}`];
        });
        if (IS_BETA) recomputeMinDist(minDist, revealed);
        // Restore opponent board
        msg.opp_revealed.forEach(([r, c, val]) => {
          oppRevealed[r][c]  = true;
          oppBoardVals[r][c] = val;
        });
        if (IS_BETA) recomputeMinDist(oppMinDist, oppRevealed);
        // Full board re-render
        for (let r = 0; r < ROWS; r++)
          for (let c = 0; c < COLS; c++) { renderCell(r, c); renderOppCell(r, c); }
        updateScores(msg.my_score, msg.my_tiles, msg.opp_score, msg.opp_tiles);
        if (msg.opp_name) setOppName(msg.opp_name, null);
        showOppBoard();
        if (gameActive) {
          elapsed = msg.elapsed || elapsed;
          document.getElementById('duel-timer').textContent = String(elapsed).padStart(3, '0');
          if (!timerID) startTimer();
        }
        setStatus('🔄 Reconnected — game is live!');
        appendChatSystem('🔄 Reconnected to game.');
        break;
      }

      case 'opp_reconnected':
        setStatus('✅ ' + (msg.msg || 'Opponent reconnected!'));
        gameActive = true;
        if (!timerID) startTimer();
        appendChatSystem('✅ ' + (msg.msg || 'Opponent reconnected.'));
        break;
    }
  });

    ws.addEventListener('close', () => {
      if (reconnectAttempts < MAX_RECONNECT) {
        reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts - 1), 15000);
        setStatus(`⚠️ Connection lost. Reconnecting… (${reconnectAttempts}/${MAX_RECONNECT})`);
        setTimeout(connectWs, delay);
      } else {
        setStatus('⚠️ Connection lost. Please refresh the page.');
      }
    });
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  buildBoard();
  buildOppBoard();

  const chatInput = document.getElementById('duel-chat-input');
  if (chatInput) {
    chatInput.addEventListener('keydown', e => { if (e.key === 'Enter') window.sendChat(); });
  }

  connectWs();
});
