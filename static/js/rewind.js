/**
 * rewind.js — F74 Rewind replay player for minesweeper.org
 *
 * Standalone module; no external dependencies.
 * Calls window.rewindInit(entry) after a game ends (triggered by minesweeper.js).
 * Borrows getMineEmoji / getFlagEmoji / getNumColors from minesweeper.js globals.
 *
 * entry shape: { rows, cols, mines, boardHash, noGuess, mode, timeMs, won,
 *                log: [[t_ms, type, r, c], …] }
 *   type: 'l' = left-click (reveal), 'r' = right-click (flag cycle), 'c' = chord
 */
(function () {
  'use strict';

  // ── CSS (injected once on first init) ───────────────────────────────────────
  function _injectCSS() {
    if (document.getElementById('rw-css')) return;
    const s = document.createElement('style');
    s.id = 'rw-css';
    s.textContent = [
      '#rw-bar{display:flex;align-items:center;gap:0.4rem;padding:0.3rem 0.5rem;',
      'background:var(--surface2);border:1px solid var(--border);',
      'border-radius:0 0 6px 6px;font-size:0.82rem;flex-wrap:wrap;',
      'box-sizing:border-box;}',
      '#rw-play-btn{background:var(--surface2);border:1px solid var(--border);',
      'border-radius:4px;color:var(--text);cursor:pointer;',
      'padding:0.15rem 0.5rem;font-size:0.9rem;line-height:1.4;}',
      '#rw-play-btn:hover{border-color:var(--accent2);color:var(--accent2);}',
      '#rw-scrubber{flex:1;min-width:60px;accent-color:var(--accent2);cursor:pointer;}',
      '#rw-time{color:var(--text-dim);white-space:nowrap;font-size:0.8rem;}',
      '#rw-speeds{display:flex;gap:0.2rem;}',
      '.rw-speed{background:var(--surface2);border:1px solid var(--border);',
      'border-radius:3px;color:var(--text-dim);cursor:pointer;',
      'padding:0.1rem 0.35rem;font-size:0.78rem;}',
      '.rw-speed:hover{border-color:var(--accent2);}',
      '.rw-speed.active{border-color:var(--accent2);color:var(--accent2);}',
    ].join('');
    document.head.appendChild(s);
  }

  // ── Board reconstruction ────────────────────────────────────────────────────

  function _decodeBoardHash(hash, rows, cols) {
    const bin = atob(hash);
    const mines = new Set();
    const n = rows * cols;
    for (let i = 0; i < n; i++) {
      if ((bin.charCodeAt(i >> 3) >> (i & 7)) & 1) mines.add(i);
    }
    return mines;
  }

  function _buildAdjBoard(rows, cols, mineSet) {
    const board = Array.from({ length: rows }, function () { return Array(cols).fill(0); });
    mineSet.forEach(function (idx) {
      const r = (idx / cols) | 0, c = idx % cols;
      board[r][c] = -1;
      for (let dr = -1; dr <= 1; dr++)
        for (let dc = -1; dc <= 1; dc++) {
          const nr = r + dr, nc = c + dc;
          if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && board[nr][nc] !== -1)
            board[nr][nc]++;
        }
    });
    return board;
  }

  function _flood(revealed, board, rows, cols, sr, sc) {
    const stack = [[sr, sc]];
    while (stack.length) {
      const pair = stack.pop();
      const r = pair[0], c = pair[1];
      if (r < 0 || r >= rows || c < 0 || c >= cols || revealed[r][c]) continue;
      revealed[r][c] = true;
      if (board[r][c] === 0) {
        for (let dr = -1; dr <= 1; dr++)
          for (let dc = -1; dc <= 1; dc++)
            if (dr || dc) stack.push([r + dr, c + dc]);
      }
    }
  }

  // Compute board state after applying all log events with t <= ms
  function _stateAt(entry, ms) {
    const rows = entry._p.rows, cols = entry._p.cols;
    const mineSet = entry._p.mineSet, board = entry._p.board;
    const revealed = Array.from({ length: rows }, function () { return Array(cols).fill(false); });
    const flagged  = Array.from({ length: rows }, function () { return Array(cols).fill(0); });
    let detonR = -1, detonC = -1, over = false;

    const log = entry.log;
    for (let i = 0; i < log.length; i++) {
      const ev = log[i];
      if (ev[0] > ms) break;
      if (over) break;
      const type = ev[1], r = ev[2], c = ev[3];
      if (type === 'l') {
        if (revealed[r][c] || flagged[r][c] === 1) continue;
        if (mineSet.has(r * cols + c)) {
          over = true; detonR = r; detonC = c;
          // Mirror boom(): reveal all mines immediately
          mineSet.forEach(function (idx) {
            revealed[(idx / cols) | 0][idx % cols] = true;
          });
        } else {
          _flood(revealed, board, rows, cols, r, c);
        }
      } else if (type === 'r') {
        if (revealed[r][c]) continue;
        flagged[r][c] = (flagged[r][c] + 1) % 3;
      } else if (type === 'c') {
        if (!revealed[r][c] || board[r][c] <= 0) continue;
        let fc = 0;
        for (let dr = -1; dr <= 1; dr++)
          for (let dc = -1; dc <= 1; dc++) {
            const nr = r + dr, nc = c + dc;
            if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && flagged[nr][nc] === 1) fc++;
          }
        if (fc === board[r][c]) {
          for (let dr = -1; dr <= 1; dr++)
            for (let dc = -1; dc <= 1; dc++) {
              const nr = r + dr, nc = c + dc;
              if (nr < 0 || nr >= rows || nc < 0 || nc >= cols) continue;
              if (revealed[nr][nc] || flagged[nr][nc] === 1) continue;
              if (mineSet.has(nr * cols + nc)) {
                over = true; detonR = nr; detonC = nc;
                mineSet.forEach(function (idx) {
                  revealed[(idx / cols) | 0][idx % cols] = true;
                });
              } else {
                _flood(revealed, board, rows, cols, nr, nc);
              }
            }
        }
      }
    }
    return { revealed: revealed, flagged: flagged, detonR: detonR, detonC: detonC };
  }

  // ── Cell rendering ──────────────────────────────────────────────────────────

  function _renderBoard(entry, gs) {
    const rows = entry._p.rows, cols = entry._p.cols;
    const board = entry._p.board;
    const boardEl = document.getElementById('board');
    if (!boardEl) return;
    const colors  = (typeof getNumColors  === 'function') ? getNumColors()  : ['', '#1976D2', '#388E3C', '#D32F2F', '#7B1FA2', '#F57F17', '#00838F', '#212121', '#757575'];
    const mineGlyph = (typeof getMineEmoji === 'function') ? getMineEmoji() : '\uD83D\uDCA3';
    const flagGlyph = (typeof getFlagEmoji === 'function') ? getFlagEmoji() : '\uD83D\uDEA9';

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const el = boardEl.children[r * cols + c];
        if (!el) continue;
        el.className = 'cell';
        el.style.color = '';
        el.textContent = '';
        if (!gs.revealed[r][c]) {
          const f = gs.flagged[r][c];
          if (f === 1)      { el.classList.add('flagged');  el.textContent = flagGlyph; }
          else if (f === 2) { el.classList.add('question'); el.textContent = '❓'; }
          else                el.classList.add('hidden');
          continue;
        }
        el.classList.add('revealed');
        const val = board[r][c];
        if (val === -1) {
          el.classList.add(r === gs.detonR && c === gs.detonC ? 'mine-detonated' : 'mine');
          el.textContent = mineGlyph;
        } else if (val > 0) {
          el.textContent = val;
          el.style.color = colors[val];
        }
      }
    }
  }

  // ── Player state ────────────────────────────────────────────────────────────

  var _e       = null;
  var _pos     = 0;
  var _total   = 0;
  var _speed   = 1;
  var _running = false;
  var _raf     = null;
  var _lastRt  = 0;

  function _fmt(ms) {
    var s = Math.floor(ms / 1000);
    return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
  }

  function _updateUI() {
    var sc = document.getElementById('rw-scrubber');
    var te = document.getElementById('rw-time');
    if (sc) sc.value = _total > 0 ? Math.round(_pos / _total * 10000) : 0;
    if (te) te.textContent = _fmt(_pos) + ' / ' + _fmt(_total);
  }

  function _applyPos(ms) {
    var gs = _stateAt(_e, ms);
    _renderBoard(_e, gs);
    var timerEl = document.getElementById('timer');
    if (timerEl) timerEl.textContent = String(Math.min(Math.floor(ms / 1000), 999)).padStart(3, '0');
  }

  function _setRunning(yes) {
    _running = yes;
    var btn = document.getElementById('rw-play-btn');
    if (btn) btn.textContent = yes ? '⏸' : '▶';
    // Show/hide the game-over overlay while replaying
    var ov = document.getElementById('game-overlay');
    if (ov) ov.style.display = yes ? 'none' : 'flex';
  }

  function _tick(rts) {
    if (!_running) return;
    _pos = Math.min(_pos + (rts - _lastRt) * _speed, _total);
    _lastRt = rts;
    _applyPos(_pos);
    _updateUI();
    if (_pos >= _total) { _setRunning(false); return; }
    _raf = requestAnimationFrame(_tick);
  }

  function _play() {
    if (_pos >= _total) _pos = 0;
    _setRunning(true);
    _lastRt = performance.now();
    _raf = requestAnimationFrame(_tick);
  }

  function _pause() {
    _setRunning(false);
    if (_raf) { cancelAnimationFrame(_raf); _raf = null; }
  }

  function _seek(ms) {
    _pause();
    _pos = Math.max(0, Math.min(ms, _total));
    _applyPos(_pos);
    _updateUI();
  }

  // ── Public API ──────────────────────────────────────────────────────────────

  window.rewindInit = function (entry) {
    if (!entry || !entry.log || !entry.log.length || !entry.boardHash) return;
    _injectCSS();

    // Stop any running replay
    if (_raf) { cancelAnimationFrame(_raf); _raf = null; }
    _running = false;

    _e     = entry;
    var mineSet = _decodeBoardHash(entry.boardHash, entry.rows, entry.cols);
    var board   = _buildAdjBoard(entry.rows, entry.cols, mineSet);
    _e._p  = { rows: entry.rows, cols: entry.cols, mineSet: mineSet, board: board };
    _total = entry.timeMs || 0;
    _pos   = _total;
    _speed = 1;

    // Show final board state
    _applyPos(_total);

    // Build or replace the rewind bar
    var old = document.getElementById('rw-bar');
    if (old) old.remove();
    var bar = document.createElement('div');
    bar.id = 'rw-bar';
    bar.innerHTML =
      '<button id="rw-play-btn" title="Play replay">\u25b6</button>' +
      '<input type="range" id="rw-scrubber" min="0" max="10000" value="10000">' +
      '<span id="rw-time">' + _fmt(_total) + ' / ' + _fmt(_total) + '</span>' +
      '<div id="rw-speeds">' +
        [1, 2, 4, 8, 16].map(function (s) {
          return '<button class="rw-speed' + (s === 1 ? ' active' : '') + '" data-s="' + s + '">' + s + '\xd7</button>';
        }).join('') +
      '</div>';

    var boardEl = document.getElementById('board');
    if (boardEl) boardEl.insertAdjacentElement('afterend', bar);

    document.getElementById('rw-play-btn').addEventListener('click', function () {
      if (_running) _pause(); else _play();
    });

    document.getElementById('rw-scrubber').addEventListener('input', function () {
      _seek(parseInt(this.value, 10) / 10000 * _total);
    });

    bar.querySelectorAll('.rw-speed').forEach(function (btn) {
      btn.addEventListener('click', function () {
        _speed = parseInt(this.dataset.s, 10);
        bar.querySelectorAll('.rw-speed').forEach(function (b) { b.classList.remove('active'); });
        this.classList.add('active');
      });
    });
  };

  window.rewindReset = function () {
    if (_raf) { cancelAnimationFrame(_raf); _raf = null; }
    _running = false;
    _e = null;
    var bar = document.getElementById('rw-bar');
    if (bar) bar.remove();
  };

}());
