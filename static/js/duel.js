/**
 * duel.js — Head-to-head Minesweeper client.
 * Loaded only on the duel page. minesweeper.js is also loaded but its
 * bootstrap guard skips init when data-mode="duel".
 */

// getNumColors() is defined in minesweeper.js — reuse it directly.

document.addEventListener('DOMContentLoaded', () => {
  const boardEl = document.getElementById('board');
  if (!boardEl || (boardEl.dataset.mode !== 'duel' && boardEl.dataset.mode !== 'pvp')) return;

  // ── Config ────────────────────────────────────────────────────────────────
  const ROWS      = parseInt(boardEl.dataset.rows);
  const COLS      = parseInt(boardEl.dataset.cols);
  const GAME_ID   = boardEl.dataset.gameId;
  const PLAYER_ID = boardEl.dataset.playerId;
  const IS_PVP     = boardEl.dataset.mode === 'pvp';
  const IS_CREATOR = boardEl.dataset.isCreator === 'true';
  const SUBMODE    = boardEl.dataset.submode || 'standard';

  console.log('GAME_ID:', GAME_ID, 'PLAYER_ID:', PLAYER_ID, 'IS_PVP:', IS_PVP);

  // ── Local state ───────────────────────────────────────────────────────────
  let revealed   = Array.from({length: ROWS}, () => Array(COLS).fill(false));
  let flagged    = Array.from({length: ROWS}, () => Array(COLS).fill(0));
  let boardVals  = Array.from({length: ROWS}, () => Array(COLS).fill(null));
  let gameActive = false;
  let exploded   = false;
  let timerID    = null;
  let elapsed    = 0;

  // ── Build board DOM ───────────────────────────────────────────────────────
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

  function cellEl(r, c) {
    return boardEl.querySelector(`[data-r="${r}"][data-c="${c}"]`);
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
    document.querySelector('.share-box button').textContent = 'Copied!';
  };

  // ── WebSocket ─────────────────────────────────────────────────────────────
  const proto  = location.protocol === 'https:' ? 'wss' : 'ws';
  let pvpWsPath = SUBMODE === 'quick'
    ? `/ws/pvp/quick/${PLAYER_ID}`
    : `/ws/pvp/${PLAYER_ID}`;
  const wsUrl  = IS_PVP
    ? `${proto}://${location.host}${pvpWsPath}`
    : `${proto}://${location.host}/ws/${GAME_ID}/${PLAYER_ID}`;
  const ws     = new WebSocket(wsUrl);

  ws.addEventListener('open', () => {
    // Send player identity so server can attribute PvP results
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

      case 'start':
        setStatus('⚔️ Game on!');
        gameActive = true;
        startTimer();
        break;

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

      case 'opp_update':
        updateScores(null, null, msg.opp_score, msg.opp_tiles);
        if (msg.opp_exploded) {
          setStatus('💥 Opponent hit a mine! Keep playing…');
        } else if (msg.opp_cleared) {
          setStatus('🎉 Opponent cleared their board! Keep playing…');
        }
        break;

      case 'game_over': {
        stopTimer();
        gameActive = false;
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

        showDuelOverlay(`
          <div class="duel-result">
            <h2>${headline}</h2>
            <p>${sub}</p>
            <p class="result-time">Time: ${msg.elapsed}s</p>
            <a href="${IS_PVP ? '/pvp' : '/duel'}?m=${SUBMODE}" class="duel-play-again">⚔️ New Duel</a>
          </div>
        `);
        break;
      }

      case 'opp_disconnected':
        setStatus('⚠️ ' + msg.msg);
        stopTimer();
        gameActive = false;
        break;

      case 'error':
        setStatus('❌ ' + msg.msg);
        break;
    }
  });

  ws.addEventListener('close', () => {
    if (gameActive) setStatus('⚠️ Connection lost.');
  });

  // ── Init ──────────────────────────────────────────────────────────────────
  buildBoard();
});
