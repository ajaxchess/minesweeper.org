/**
 * 2048.js — Daily 2048 puzzle
 * Self-contained vanilla JS, no dependencies.
 * Seeded by window.T2K_DATE (YYYY-MM-DD) so every player on the same day
 * gets the same tile spawns.
 */

(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // LCG PRNG (same parameters as fifteen_puzzle.js)
  // Exposed as object so undo can save/restore RNG state.
  // ---------------------------------------------------------------------------
  function makeLCG(seed) {
    var s = seed >>> 0;
    return {
      next: function () {
        s = Math.imul(1664525, s) + 1013904223;
        s = s >>> 0;
        return s / 4294967296;
      },
      getState:  function ()       { return s; },
      setState:  function (state)  { s = state >>> 0; }
    };
  }

  function seedFromDateString(dateStr) {
    var seed = 0;
    for (var i = 0; i < dateStr.length; i++) {
      seed = Math.imul(31, seed) + dateStr.charCodeAt(i);
      seed = seed >>> 0;
    }
    return seed;
  }

  // ---------------------------------------------------------------------------
  // Game state
  // ---------------------------------------------------------------------------
  var grid          = [];   // flat array of 16 values (0 = empty)
  var score         = 0;
  var moveCount     = 0;
  var won           = false;
  var over          = false;
  var continued     = false;   // true after player chooses to keep playing past 2048
  var timerInterval = null;
  var startTime     = null;
  var elapsedMs     = 0;
  var dailyDate     = '';
  var userName      = '';
  var rng           = null;

  // Undo
  var undoStack    = [];   // array of saved states
  var disqualified = false;

  // Tile vanish
  var vanishEnabled   = false;
  var vanishThreshold = 512;
  var removedTiles    = 0;

  // ---------------------------------------------------------------------------
  // Grid helpers
  // ---------------------------------------------------------------------------
  function emptyGrid() {
    var g = [];
    for (var i = 0; i < 16; i++) g.push(0);
    return g;
  }

  function getEmpties(g) {
    var e = [];
    for (var i = 0; i < 16; i++) if (g[i] === 0) e.push(i);
    return e;
  }

  function spawnTile(g) {
    var empties = getEmpties(g);
    if (!empties.length) return;
    var idx = empties[Math.floor(rng.next() * empties.length)];
    g[idx] = rng.next() < 0.9 ? 2 : 4;
  }

  // ---------------------------------------------------------------------------
  // Move logic
  // Slides one row of 4 cells leftward, merges adjacent equals once per pair.
  // Returns the new row and score gained.
  // ---------------------------------------------------------------------------
  function slideRow(row) {
    var r = row.filter(function (v) { return v !== 0; });
    var gained = 0;
    for (var i = 0; i < r.length - 1; i++) {
      if (r[i] === r[i + 1]) {
        r[i] *= 2;
        gained += r[i];
        r.splice(i + 1, 1);
      }
    }
    while (r.length < 4) r.push(0);
    return { row: r, gained: gained };
  }

  function arrEq(a, b) {
    for (var i = 0; i < 4; i++) if (a[i] !== b[i]) return false;
    return true;
  }

  // Apply a directional move.  Returns { grid, gained, changed }.
  function applyMove(g, dir) {
    var ng = g.slice();
    var gained  = 0;
    var changed = false;
    var i, res, orig, rev;

    if (dir === 'left') {
      for (i = 0; i < 4; i++) {
        orig = [ng[i*4], ng[i*4+1], ng[i*4+2], ng[i*4+3]];
        res  = slideRow(orig);
        if (!arrEq(orig, res.row)) changed = true;
        gained += res.gained;
        ng[i*4]   = res.row[0]; ng[i*4+1] = res.row[1];
        ng[i*4+2] = res.row[2]; ng[i*4+3] = res.row[3];
      }
    } else if (dir === 'right') {
      for (i = 0; i < 4; i++) {
        orig = [ng[i*4+3], ng[i*4+2], ng[i*4+1], ng[i*4]];
        res  = slideRow(orig);
        rev  = res.row.slice().reverse();
        if (!arrEq([ng[i*4], ng[i*4+1], ng[i*4+2], ng[i*4+3]], rev)) changed = true;
        gained += res.gained;
        ng[i*4]   = rev[0]; ng[i*4+1] = rev[1];
        ng[i*4+2] = rev[2]; ng[i*4+3] = rev[3];
      }
    } else if (dir === 'up') {
      for (i = 0; i < 4; i++) {
        orig = [ng[i], ng[4+i], ng[8+i], ng[12+i]];
        res  = slideRow(orig);
        if (!arrEq(orig, res.row)) changed = true;
        gained += res.gained;
        ng[i] = res.row[0]; ng[4+i] = res.row[1];
        ng[8+i] = res.row[2]; ng[12+i] = res.row[3];
      }
    } else if (dir === 'down') {
      for (i = 0; i < 4; i++) {
        orig = [ng[12+i], ng[8+i], ng[4+i], ng[i]];
        res  = slideRow(orig);
        rev  = res.row.slice().reverse();
        if (!arrEq([ng[i], ng[4+i], ng[8+i], ng[12+i]], rev)) changed = true;
        gained += res.gained;
        ng[i] = rev[0]; ng[4+i] = rev[1];
        ng[8+i] = rev[2]; ng[12+i] = rev[3];
      }
    }

    return { grid: ng, gained: gained, changed: changed };
  }

  function hasMovesLeft(g) {
    for (var i = 0; i < 16; i++) {
      if (g[i] === 0) return true;
      if (i % 4 < 3 && g[i] === g[i + 1]) return true;
      if (i < 12    && g[i] === g[i + 4]) return true;
    }
    return false;
  }

  // ---------------------------------------------------------------------------
  // Undo state management
  // ---------------------------------------------------------------------------
  function saveState() {
    undoStack.push({
      grid:         grid.slice(),
      score:        score,
      moveCount:    moveCount,
      rngState:     rng.getState(),
      won:          won,
      continued:    continued,
      removedTiles: removedTiles,
      elapsedMs:    elapsedMs
    });
  }

  function undoMove() {
    if (undoStack.length === 0) return;

    // Hide end-game overlays and score form
    ['t2k-win-msg', 't2k-over-msg'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.style.display = 'none';
    });
    var form = document.getElementById('t2k-score-form');
    if (form) form.style.display = 'none';
    var msgEl = document.getElementById('t2k-score-msg');
    if (msgEl) { msgEl.textContent = ''; msgEl.style.display = 'none'; }

    // Stop timer before restoring
    clearInterval(timerInterval);
    timerInterval = null;

    var state     = undoStack.pop();
    grid          = state.grid;
    score         = state.score;
    moveCount     = state.moveCount;
    rng.setState(state.rngState);
    won           = state.won;
    continued     = state.continued;
    removedTiles  = state.removedTiles;
    elapsedMs     = state.elapsedMs;
    over          = false;   // undo always exits game-over

    // Using undo disqualifies from the leaderboard
    disqualified  = true;
    updateDisqualifiedUI();
    updateRemovedTilesUI();

    // Resume timer if game is in progress
    if (moveCount > 0) {
      startTime    = Date.now() - elapsedMs;
      timerInterval = setInterval(updateTimer, 100);
    } else {
      startTime = null;
      var timeEl = document.getElementById('t2k-time');
      if (timeEl) timeEl.textContent = '0.0';
    }

    render();
  }

  // ---------------------------------------------------------------------------
  // Tile vanish
  // ---------------------------------------------------------------------------
  function applyVanish() {
    var vanished = false;
    for (var i = 0; i < 16; i++) {
      if (grid[i] > 0 && grid[i] >= vanishThreshold) {
        // Score was already added by the merge; tile simply disappears
        grid[i] = 0;
        removedTiles++;
        vanished = true;
      }
    }
    if (vanished) {
      disqualified = true;
      updateDisqualifiedUI();
      updateRemovedTilesUI();
    }
  }

  // ---------------------------------------------------------------------------
  // UI helpers
  // ---------------------------------------------------------------------------
  function updateDisqualifiedUI() {
    var el = document.getElementById('t2k-disqualified');
    if (el) el.style.display = disqualified ? '' : 'none';
  }

  function updateRemovedTilesUI() {
    var wrap = document.getElementById('t2k-removed-wrap');
    if (wrap) wrap.style.display = removedTiles > 0 ? '' : 'none';
    var cnt = document.getElementById('t2k-removed');
    if (cnt) cnt.textContent = removedTiles;
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  function render() {
    var board = document.getElementById('t2k-board');
    if (!board) return;
    board.innerHTML = '';

    for (var i = 0; i < 16; i++) {
      var cell = document.createElement('div');
      cell.className = 't2k-cell';
      var val = grid[i];
      if (val) {
        cell.textContent = val;
        cell.setAttribute('data-val', Math.min(val, 2048));
      }
      board.appendChild(cell);
    }

    var scoreEl = document.getElementById('t2k-score');
    if (scoreEl) scoreEl.textContent = score;
    var movesEl = document.getElementById('t2k-moves');
    if (movesEl) movesEl.textContent = moveCount;
  }

  // ---------------------------------------------------------------------------
  // Input handling
  // ---------------------------------------------------------------------------
  function handleDir(dir) {
    if (over) return;
    if (won && !continued) return;

    var result = applyMove(grid, dir);
    if (!result.changed) return;

    // Save state for undo BEFORE modifying anything
    saveState();

    if (moveCount === 0 && startTime === null) {
      startTime = Date.now();
      timerInterval = setInterval(updateTimer, 100);
    }

    grid       = result.grid;
    score     += result.gained;
    moveCount++;

    // Check win before vanish so reaching 2048 is still recognized
    if (!won && !continued) {
      for (var i = 0; i < 16; i++) {
        if (grid[i] >= 2048) { won = true; break; }
      }
    }

    // Apply tile vanish if enabled
    if (vanishEnabled) {
      applyVanish();
    }

    spawnTile(grid);

    if (!hasMovesLeft(grid)) over = true;

    render();

    if (won && !continued) {
      stopTimer();
      showWin();
    } else if (over) {
      stopTimer();
      showOver();
    }
  }

  // Keyboard
  var KEY_MAP = {
    ArrowLeft: 'left', ArrowRight: 'right',
    ArrowUp: 'up',     ArrowDown: 'down'
  };
  document.addEventListener('keydown', function (e) {
    var dir = KEY_MAP[e.key];
    if (dir) { e.preventDefault(); handleDir(dir); }
  });

  // Touch swipe
  var _tx = 0, _ty = 0;
  document.addEventListener('touchstart', function (e) {
    _tx = e.touches[0].clientX;
    _ty = e.touches[0].clientY;
  }, { passive: true });
  document.addEventListener('touchend', function (e) {
    var dx = e.changedTouches[0].clientX - _tx;
    var dy = e.changedTouches[0].clientY - _ty;
    if (Math.abs(dx) < 20 && Math.abs(dy) < 20) return;
    handleDir(Math.abs(dx) > Math.abs(dy)
      ? (dx > 0 ? 'right' : 'left')
      : (dy > 0 ? 'down'  : 'up'));
  }, { passive: true });

  // ---------------------------------------------------------------------------
  // Timer
  // ---------------------------------------------------------------------------
  function updateTimer() {
    if (startTime === null) return;
    elapsedMs = Date.now() - startTime;
    var el = document.getElementById('t2k-time');
    if (el) el.textContent = (elapsedMs / 1000).toFixed(1);
  }

  function stopTimer() {
    clearInterval(timerInterval);
    timerInterval = null;
    if (startTime !== null) elapsedMs = Date.now() - startTime;
    var el = document.getElementById('t2k-time');
    if (el) el.textContent = (elapsedMs / 1000).toFixed(1);
  }

  // ---------------------------------------------------------------------------
  // Win / game-over UI
  // ---------------------------------------------------------------------------
  function showWin() {
    var el = document.getElementById('t2k-win-msg');
    if (el) el.style.display = 'block';
    if (!disqualified) {
      if (userName) { autoSubmitScore(); } else { showScoreForm(); }
    }
  }

  function showOver() {
    var el = document.getElementById('t2k-over-msg');
    if (el) el.style.display = 'block';
    if (!disqualified) {
      if (userName) { autoSubmitScore(); } else { showScoreForm(); }
    }
  }

  // ---------------------------------------------------------------------------
  // Continue past 2048
  // ---------------------------------------------------------------------------
  function continueGame() {
    continued = true;
    var winEl = document.getElementById('t2k-win-msg');
    if (winEl) winEl.style.display = 'none';
    var form = document.getElementById('t2k-score-form');
    if (form) form.style.display = 'none';
    // Resume timer from where it stopped
    startTime = Date.now() - elapsedMs;
    timerInterval = setInterval(updateTimer, 100);
  }

  // ---------------------------------------------------------------------------
  // Score submission
  // ---------------------------------------------------------------------------
  function showScoreForm() {
    var form = document.getElementById('t2k-score-form');
    if (!form) return;
    var tv = document.getElementById('t2k-time-val');
    var mv = document.getElementById('t2k-moves-val');
    var sv = document.getElementById('t2k-score-val');
    if (tv) tv.value = Math.round(elapsedMs);
    if (mv) mv.value = moveCount;
    if (sv) sv.value = score;
    form.style.display = 'flex';

    var btn = form.querySelector('#t2k-submit') || form.querySelector('button[type="submit"]');
    if (btn && !btn.dataset.wired) {
      btn.dataset.wired = '1';
      btn.addEventListener('click', function (e) { e.preventDefault(); submitScore(); });
    }
    if (!form.dataset.wired) {
      form.dataset.wired = '1';
      form.addEventListener('submit', function (e) { e.preventDefault(); submitScore(); });
    }
  }

  function submitScore() {
    var nameEl = document.getElementById('t2k-name');
    doSubmit(nameEl ? nameEl.value.trim() : '');
  }

  function autoSubmitScore() {
    doSubmit(userName);
  }

  function doSubmit(name) {
    var msgEl = document.getElementById('t2k-score-msg');
    fetch('/api/2048-scores', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify({
        name:        name,
        puzzle_date: dailyDate,
        score:       score,
        time_ms:     Math.round(elapsedMs),
        moves:       moveCount
      })
    })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function () {
        var form = document.getElementById('t2k-score-form');
        if (form) form.style.display = 'none';
        if (msgEl) { msgEl.textContent = 'Score submitted!'; msgEl.style.display = ''; }
      })
      .catch(function () {
        if (userName) showScoreForm();  // fall back to manual form on error
      });
  }

  // ---------------------------------------------------------------------------
  // Settings
  // ---------------------------------------------------------------------------
  function initSettings() {
    var vanishToggle  = document.getElementById('t2k-vanish-toggle');
    var vanishOptions = document.getElementById('t2k-vanish-options');
    var vanishSelect  = document.getElementById('t2k-vanish-threshold');

    if (vanishToggle) {
      vanishToggle.addEventListener('change', function () {
        vanishEnabled = this.checked;
        if (vanishOptions) vanishOptions.style.display = vanishEnabled ? '' : 'none';
      });
    }

    if (vanishSelect) {
      vanishSelect.addEventListener('change', function () {
        vanishThreshold = parseInt(this.value, 10);
      });
      vanishThreshold = parseInt(vanishSelect.value, 10);
    }
  }

  // ---------------------------------------------------------------------------
  // Reset / init
  // ---------------------------------------------------------------------------
  function resetGame() {
    rng           = makeLCG(seedFromDateString(dailyDate));
    grid          = emptyGrid();
    score         = 0;
    moveCount     = 0;
    won           = false;
    over          = false;
    continued     = false;
    undoStack     = [];
    disqualified  = false;
    removedTiles  = 0;
    clearInterval(timerInterval);
    timerInterval = null;
    startTime     = null;
    elapsedMs     = 0;

    spawnTile(grid);
    spawnTile(grid);

    ['t2k-win-msg', 't2k-over-msg'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.style.display = 'none';
    });
    var form = document.getElementById('t2k-score-form');
    if (form) form.style.display = 'none';
    var msgEl = document.getElementById('t2k-score-msg');
    if (msgEl) { msgEl.textContent = ''; msgEl.style.display = 'none'; }

    var timeEl = document.getElementById('t2k-time');
    if (timeEl) timeEl.textContent = '0.0';

    updateDisqualifiedUI();
    updateRemovedTilesUI();
    render();
  }

  function init() {
    dailyDate = (window.T2K_DATE      || new Date().toISOString().slice(0, 10));
    userName  = (window.T2K_USER_NAME || '');

    var resetBtn = document.getElementById('t2k-reset');
    if (resetBtn) resetBtn.addEventListener('click', resetGame);

    var contBtn = document.getElementById('t2k-continue');
    if (contBtn) contBtn.addEventListener('click', continueGame);

    var undoBtn = document.getElementById('t2k-undo');
    if (undoBtn) undoBtn.addEventListener('click', undoMove);

    initSettings();
    resetGame();
  }

  window.init2048 = init;
  window.addEventListener('DOMContentLoaded', init);
})();
