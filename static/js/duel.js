/**
 * duel.js — Head-to-head Minesweeper client.
 * Loaded only on the duel page. minesweeper.js is also loaded but its
 * bootstrap guard skips init when data-mode="duel".
 */

// getNumColors() is defined in minesweeper.js — reuse it directly.

document.addEventListener('DOMContentLoaded', () => {
  const boardEl = document.getElementById('board');
  if (!boardEl || !['duel', 'pvp', 'pvp-bot'].includes(boardEl.dataset.mode)) return;

  // ── Config ────────────────────────────────────────────────────────────────
  const ROWS        = parseInt(boardEl.dataset.rows);
  const COLS        = parseInt(boardEl.dataset.cols);
  const GAME_ID     = boardEl.dataset.gameId;
  const PLAYER_ID   = boardEl.dataset.playerId;
  const MODE        = boardEl.dataset.mode;
  const IS_PVP      = MODE === 'pvp';
  const IS_BOT      = MODE === 'pvp-bot';
  const IS_CREATOR  = boardEl.dataset.isCreator === 'true';
  const SUBMODE     = boardEl.dataset.submode || 'standard';
  const BOT_DIFF    = boardEl.dataset.botDifficulty || 'medium';
  const OPP_DELAY_MS = (parseInt(boardEl.dataset.oppDelay || '0')) * 1000;

  // ── Local state ───────────────────────────────────────────────────────────
  let revealed   = Array.from({length: ROWS}, () => Array(COLS).fill(false));
  let flagged    = Array.from({length: ROWS}, () => Array(COLS).fill(0));
  let boardVals  = Array.from({length: ROWS}, () => Array(COLS).fill(null));
  let gameActive = false;
  let exploded   = false;
  let timerID    = null;
  let elapsed    = 0;

  // ── Opponent board state ──────────────────────────────────────────────────
  const oppBoardEl  = document.getElementById('opp-board');
  const oppWaitEl   = document.getElementById('opp-board-waiting');
  let oppRevealed   = Array.from({length: ROWS}, () => Array(COLS).fill(false));
  let oppBoardVals  = Array.from({length: ROWS}, () => Array(COLS).fill(null));
  let oppExploded   = false;
  // Queue: [{applyAt: ms timestamp, cells: [[r,c,val],...], exploded: bool, cleared: bool}]
  const pendingOppUpdates = [];

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
        el.textContent = '🚩';
      } else if (flagged[r][c] === 2) {
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
      el.classList.add(exploded ? 'mine-detonated' : 'mine');
      el.textContent = '💣';
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
      el.classList.add('hidden');
      el.textContent = '';
      return;
    }
    el.classList.add('revealed');
    if (val === -1) {
      el.classList.add(oppExploded ? 'mine-detonated' : 'mine');
      el.textContent = '💣';
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
      batch.cells.forEach(([r, c, val]) => {
        oppRevealed[r][c]  = true;
        oppBoardVals[r][c] = val;
        renderOppCell(r, c);
      });
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
  }

  // ── Actions ───────────────────────────────────────────────────────────────
  function onReveal(r, c) {
    if (!gameActive || revealed[r][c] || flagged[r][c] === 1 || exploded) return;
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
    nbs.forEach(([nr, nc]) => {
      if (!flagged[nr][nc] && !revealed[nr][nc])
        ws.send(JSON.stringify({type: 'reveal', r: nr, c: nc}));
    });
  }

  function onFlag(r, c) {
    if (!gameActive || revealed[r][c]) return;
    flagged[r][c] = (flagged[r][c] + 1) % 3;
    renderCell(r, c);
  }

  function setStatus(msg) {
    document.getElementById('duel-status').textContent = msg;
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
    wsPath = `/ws/pvp/bot/${PLAYER_ID}?m=${SUBMODE}&d=${BOT_DIFF}`;
  } else if (IS_PVP) {
    wsPath = SUBMODE === 'quick'
      ? `/ws/pvp/quick/${PLAYER_ID}`
      : `/ws/pvp/${PLAYER_ID}`;
  } else {
    wsPath = `/ws/${GAME_ID}/${PLAYER_ID}`;
  }
  const wsUrl = `${proto}://${location.host}${wsPath}`;
  const ws     = new WebSocket(wsUrl);

  ws.addEventListener('open', () => {
    const playerName  = boardEl.dataset.username  || '';
    const playerEmail = boardEl.dataset.useremail || '';
    if (playerName) {
      ws.send(JSON.stringify({type: 'player_name', name: playerName, email: playerEmail}));
    }
    if (IS_CREATOR) {
      const link = `${location.origin}/duel/${GAME_ID}`;
      const inp  = document.getElementById('share-link');
      if (inp) inp.value = link;
      document.getElementById('share-box').style.display = 'flex';

      const watchInp = document.getElementById('watch-link-inp');
      if (watchInp) watchInp.value = `${location.origin}/duel/${GAME_ID}/watch`;
      const watchBox = document.getElementById('watch-box');
      if (watchBox) watchBox.style.display = 'flex';
    }
  });

  ws.addEventListener('message', e => {
    const msg = JSON.parse(e.data);

    switch (msg.type) {

      case 'queued':
        setStatus(`🔍 ${msg.msg} (${msg.queue_pos} in queue)`);
        break;

      case 'matched':
        setStatus('🎯 ' + msg.msg);
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
          msg.prerev.forEach(([r, c]) => {
            const val = msg.board_values[`${r},${c}`];
            revealed[r][c]    = true;
            boardVals[r][c]   = val;
            renderCell(r, c);
            // Mirror same opening on opponent board (no delay — it's the starting state)
            oppRevealed[r][c]  = true;
            oppBoardVals[r][c] = val;
            renderOppCell(r, c);
          });
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
        newCells.forEach(([r, c]) => {
          revealed[r][c]  = true;
          boardVals[r][c] = boardValsM[`${r},${c}`];
          renderCell(r, c);
        });
        if (msg.exploded) {
          exploded = true;
          gameActive = false;
          stopTimer();
          setStatus('💥 You hit a mine! Waiting for opponent to finish…');
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
            <a href="${IS_PVP ? '/pvp' : '/duel'}?m=${SUBMODE}" class="duel-play-again duel-play-again--secondary">⚔️ New Duel</a>
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

      case 'error':
        setStatus('❌ ' + msg.msg);
        break;

      case 'chat':
        appendChat(msg.from, msg.text, msg.pid === PLAYER_ID);
        break;
    }
  });

  ws.addEventListener('close', () => {
    if (gameActive) setStatus('⚠️ Connection lost.');
  });

  // ── Init ──────────────────────────────────────────────────────────────────
  buildBoard();
  buildOppBoard();

  const chatInput = document.getElementById('duel-chat-input');
  if (chatInput) {
    chatInput.addEventListener('keydown', e => { if (e.key === 'Enter') window.sendChat(); });
  }
});
