/**
 * spectate.js — Spectator client for duel games.
 * Connects read-only to a running duel, renders both boards, and allows chat.
 */

document.addEventListener('DOMContentLoaded', () => {
  const rootEl  = document.getElementById('board-p1');
  if (!rootEl) return;

  const GAME_ID  = rootEl.dataset.gameId;
  const SPEC_ID  = rootEl.dataset.specId;
  const ROWS     = parseInt(rootEl.dataset.rows);
  const COLS     = parseInt(rootEl.dataset.cols);
  const username = rootEl.dataset.username || 'Spectator';

  // ── Per-player board state ─────────────────────────────────────────────────
  // boards[0] = player 1 (left), boards[1] = player 2 (right)
  const boards = [
    {
      el:       document.getElementById('board-p1'),
      overlay:  document.getElementById('spec-overlay-p1'),
      nameEl:   document.getElementById('p1-name'),
      boardLbl: document.getElementById('p1-board-label'),
      scoreEl:  document.getElementById('p1-score'),
      tilesEl:  document.getElementById('p1-tiles'),
      pid:      null,
      revealed: Array.from({length: ROWS}, () => Array(COLS).fill(false)),
      vals:     Array.from({length: ROWS}, () => Array(COLS).fill(null)),
      exploded: false,
    },
    {
      el:       document.getElementById('board-p2'),
      overlay:  document.getElementById('spec-overlay-p2'),
      nameEl:   document.getElementById('p2-name'),
      boardLbl: document.getElementById('p2-board-label'),
      scoreEl:  document.getElementById('p2-score'),
      tilesEl:  document.getElementById('p2-tiles'),
      pid:      null,
      revealed: Array.from({length: ROWS}, () => Array(COLS).fill(false)),
      vals:     Array.from({length: ROWS}, () => Array(COLS).fill(null)),
      exploded: false,
    },
  ];

  // ── Board building ─────────────────────────────────────────────────────────
  function buildBoard(b) {
    b.el.innerHTML = '';
    b.el.style.setProperty('--cols', COLS);
    for (let r = 0; r < ROWS; r++) {
      for (let c = 0; c < COLS; c++) {
        const cell = document.createElement('div');
        cell.className    = 'cell hidden opp-cell';
        cell.dataset.r    = r;
        cell.dataset.c    = c;
        b.el.appendChild(cell);
      }
    }
  }

  function cellEl(b, r, c) {
    return b.el.querySelector(`[data-r="${r}"][data-c="${c}"]`);
  }

  function renderCell(b, r, c) {
    const el  = cellEl(b, r, c);
    if (!el) return;
    const val = b.vals[r][c];
    el.className = 'cell opp-cell';
    if (!b.revealed[r][c]) {
      el.classList.add('hidden');
      el.textContent = '';
      return;
    }
    el.classList.add('revealed');
    if (val === -1) {
      el.classList.add(b.exploded ? 'mine-detonated' : 'mine');
      el.textContent = getMineEmoji();
    } else if (val === 0) {
      el.textContent = '';
    } else {
      el.textContent = val;
      el.style.color = getNumColors()[val];
    }
  }

  // ── Timer ──────────────────────────────────────────────────────────────────
  let timerID = null;
  let elapsed  = 0;

  function startTimer(fromSec) {
    if (timerID) return;
    elapsed = fromSec || 0;
    document.getElementById('spec-timer').textContent = String(Math.round(elapsed)).padStart(3, '0');
    timerID = setInterval(() => {
      elapsed = Math.min(elapsed + 1, 999);
      document.getElementById('spec-timer').textContent = String(Math.round(elapsed)).padStart(3, '0');
    }, 1000);
  }

  function stopTimer() {
    clearInterval(timerID);
    timerID = null;
  }

  function setStatus(msg) {
    document.getElementById('spec-status').textContent = msg;
  }

  // ── Chat helpers ───────────────────────────────────────────────────────────
  function escHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function appendChat(from, text) {
    const log = document.getElementById('duel-chat-log');
    if (!log) return;
    const div = document.createElement('div');
    div.className = 'duel-chat-msg';
    div.innerHTML = `<span class="duel-chat-from">${escHtml(from)}:</span> <span class="duel-chat-text">${escHtml(text)}</span>`;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
  }

  function appendChatSystem(text) {
    const log = document.getElementById('duel-chat-log');
    if (!log) return;
    const div = document.createElement('div');
    div.className   = 'duel-chat-system';
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

  // ── Overlay ────────────────────────────────────────────────────────────────
  function showOverlay(b, html) {
    b.overlay.innerHTML     = html;
    b.overlay.style.display = 'flex';
  }

  // ── WebSocket ──────────────────────────────────────────────────────────────
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws    = new WebSocket(`${proto}://${location.host}/ws/${GAME_ID}/spectate/${SPEC_ID}`);

  ws.addEventListener('open', () => {
    if (username) {
      ws.send(JSON.stringify({type: 'spectator_name', name: username}));
    }
  });

  ws.addEventListener('message', e => {
    const msg = JSON.parse(e.data);

    switch (msg.type) {

      case 'spec_init': {
        // Populate player info and render any already-revealed cells
        msg.players.forEach((p, idx) => {
          if (idx >= 2) return;
          const b      = boards[idx];
          b.pid        = p.player_id;
          b.exploded   = p.exploded;
          const name   = p.name || `Player ${idx + 1}`;
          b.nameEl.textContent   = name;
          b.boardLbl.textContent = `⚔️ ${name}`;
          b.scoreEl.textContent  = p.score;
          b.tilesEl.textContent  = `${p.tiles} tiles`;
          p.cells.forEach(([r, c, val]) => {
            b.revealed[r][c] = true;
            b.vals[r][c]     = val;
          });
          // Render all revealed cells
          for (let r = 0; r < ROWS; r++)
            for (let c = 0; c < COLS; c++)
              if (b.revealed[r][c]) renderCell(b, r, c);
        });

        if (msg.status === 'active') {
          setStatus('👁 Game in progress');
          startTimer(msg.elapsed);
        } else if (msg.status === 'finished') {
          setStatus('👁 Game has ended');
        } else {
          setStatus('👁 Waiting for game to start…');
        }
        appendChatSystem('👁 You joined as a spectator.');
        break;
      }

      case 'spec_update': {
        // Find which board this player_id belongs to
        const b = boards.find(x => x.pid === msg.player_id);
        if (!b) break;
        b.scoreEl.textContent = msg.score;
        b.tilesEl.textContent = `${msg.tiles} tiles`;
        if (msg.exploded) b.exploded = true;
        msg.newly_revealed.forEach(([r, c]) => {
          const val        = msg.board_values[`${r},${c}`];
          b.revealed[r][c] = true;
          b.vals[r][c]     = val;
          renderCell(b, r, c);
        });
        break;
      }

      case 'start': {
        setStatus('⚔️ Game started!');
        appendChatSystem('⚔️ Game started!');
        startTimer(0);
        // Render the shared opening on both boards
        if (msg.prerev && msg.board_values) {
          boards.forEach(b => {
            msg.prerev.forEach(([r, c]) => {
              const val    = msg.board_values[`${r},${c}`];
              b.revealed[r][c] = true;
              b.vals[r][c]     = val;
              renderCell(b, r, c);
            });
            b.scoreEl.textContent = msg.prerev_score || 0;
            b.tilesEl.textContent = `${msg.prerev ? msg.prerev.length : 0} tiles`;
          });
        }
        break;
      }

      case 'game_over': {
        stopTimer();
        setStatus('🏁 Game over!');

        const scores = msg.scores || {};
        boards.forEach(b => {
          if (!b.pid) return;
          const score = scores[b.pid] ?? 0;
          b.scoreEl.textContent = score;
          const isWinner = msg.winner_id && msg.winner_id === b.pid;
          const isDraw   = !msg.winner_id;
          let headline;
          if (isDraw)      headline = '💥 Draw!';
          else if (isWinner) headline = '🏆 Winner!';
          else               headline = '😵 Loser';
          showOverlay(b, `<div class="duel-result"><h2>${headline}</h2><p>Score: ${score}</p></div>`);
        });

        appendChatSystem(`🏁 Game over! Time: ${msg.elapsed}s`);
        break;
      }

      case 'chat':
        appendChat(msg.from, msg.text);
        break;

      case 'opp_disconnected':
        setStatus('⚠️ A player disconnected.');
        appendChatSystem('⚠️ A player disconnected.');
        break;
    }
  });

  ws.addEventListener('close', () => {
    setStatus('⚠️ Connection lost.');
  });

  // ── Init ───────────────────────────────────────────────────────────────────
  boards.forEach(buildBoard);

  const chatInput = document.getElementById('duel-chat-input');
  if (chatInput) {
    chatInput.addEventListener('keydown', e => { if (e.key === 'Enter') window.sendChat(); });
  }
});
