/**
 * fifteen_puzzle.js — Daily 15-puzzle (sliding tile) game
 * Self-contained vanilla JS, no dependencies.
 * Seeded by window.FP_DATE (YYYY-MM-DD string set by template).
 */

(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // LCG PRNG
  // ---------------------------------------------------------------------------
  function makeLCG(seed) {
    // LCG parameters from Numerical Recipes
    var s = seed >>> 0;
    return function () {
      s = Math.imul(1664525, s) + 1013904223;
      s = s >>> 0;
      return s / 4294967296;
    };
  }

  function seedFromDateString(dateStr) {
    // Convert date string chars to a numeric seed
    var seed = 0;
    for (var i = 0; i < dateStr.length; i++) {
      seed = Math.imul(31, seed) + dateStr.charCodeAt(i);
      seed = seed >>> 0;
    }
    return seed;
  }

  // ---------------------------------------------------------------------------
  // Fisher-Yates shuffle using provided rng
  // ---------------------------------------------------------------------------
  function shuffle(arr, rng) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(rng() * (i + 1));
      var tmp = a[i];
      a[i] = a[j];
      a[j] = tmp;
    }
    return a;
  }

  // ---------------------------------------------------------------------------
  // Solvability — works for any NxN grid
  //   Even N: solvable iff (inversions + rowFromBottom) is odd
  //   Odd  N: solvable iff inversions is even
  // ---------------------------------------------------------------------------
  function countInversions(tiles) {
    var count = 0;
    for (var i = 0; i < tiles.length; i++) {
      if (tiles[i] === 0) continue;
      for (var j = i + 1; j < tiles.length; j++) {
        if (tiles[j] === 0) continue;
        if (tiles[i] > tiles[j]) count++;
      }
    }
    return count;
  }

  function isSolvable(tiles, n) {
    var inversions  = countInversions(tiles);
    var blankIndex  = tiles.indexOf(0);
    if (n % 2 === 1) {
      return inversions % 2 === 0;
    }
    var rowFromBottom = n - Math.floor(blankIndex / n);
    return (inversions + rowFromBottom) % 2 === 1;
  }

  // ---------------------------------------------------------------------------
  // Generate daily board for any NxN
  // Seeded by date string + grid size so each size gets a unique scramble
  // ---------------------------------------------------------------------------
  function generateDailyBoard(dateStr, n) {
    var seedStr = dateStr + ':' + n;
    var seed = seedFromDateString(seedStr);
    var rng  = makeLCG(seed);
    var total = n * n;
    var base = [];
    for (var k = 1; k < total; k++) base.push(k);
    base.push(0);

    var t;
    var attempts = 0;
    do {
      t = shuffle(base, rng);
      attempts++;
    } while (!isSolvable(t, n) && attempts < 200);

    if (!isSolvable(t, n)) {
      var a = 0, b = 1;
      if (t[a] === 0) { a = 1; b = 2; }
      if (t[b] === 0) { b = 2; }
      var tmp = t[a]; t[a] = t[b]; t[b] = tmp;
    }
    return t;
  }

  // ---------------------------------------------------------------------------
  // Board hash decode (for photo puzzles)
  // ---------------------------------------------------------------------------
  function hashToTiles(hash) {
    try {
      var b64 = hash.replace(/-/g, '+').replace(/_/g, '/');
      while (b64.length % 4) b64 += '=';
      var bin = atob(b64);
      // bytes[0]=cols, bytes[1]=rows, bytes[2..] = tiles
      var tiles = [];
      for (var i = 2; i < bin.length; i++) tiles.push(bin.charCodeAt(i));
      return tiles;
    } catch (e) {
      return null;
    }
  }

  // ---------------------------------------------------------------------------
  // Game state
  // ---------------------------------------------------------------------------
  var tiles = [];
  var moveCount = 0;
  var timerInterval = null;
  var startTime = null;
  var elapsedMs = 0;
  var gameWon = false;
  var dailyDate = '';
  var gridSize = '4x4';  // e.g. "5x5"
  var COLS = 4;
  var WIN_STATE = [];
  var photoUrl = '';
  var photoMode = '';   // 'tiles' | 'reveal'
  var revealUrl = '';   // member puzzles: separate image shown full-bleed on win
  var isPhotoPuzzle = false;
  var userName = '';    // non-empty when a user is logged in

  // ---------------------------------------------------------------------------
  // DOM helpers
  // ---------------------------------------------------------------------------
  function getBoard()       { return document.getElementById('fp-board'); }
  function getTimeEl()      { return document.getElementById('fp-time'); }
  function getMovesEl()     { return document.getElementById('fp-moves'); }
  function getScoreForm()   { return document.getElementById('fp-score-form'); }
  function getTimeValEl()   { return document.getElementById('fp-time-val'); }
  function getMovesValEl()  { return document.getElementById('fp-moves-val'); }
  function getResetBtn()    { return document.getElementById('fp-reset'); }

  // ---------------------------------------------------------------------------
  // Font / gap helpers — scale gracefully for large grids
  // ---------------------------------------------------------------------------
  function tileFontSize(n) {
    if (n <= 3)  return '2rem';
    if (n <= 4)  return '1.5rem';
    if (n <= 5)  return '1.2rem';
    if (n <= 6)  return '1rem';
    if (n <= 7)  return '0.85rem';
    if (n <= 8)  return '0.72rem';
    if (n <= 9)  return '0.62rem';
    return '0.54rem';
  }

  function boardGap(n) { return n <= 6 ? '5px' : n <= 8 ? '3px' : '2px'; }
  function boardPad(n) { return n <= 6 ? '7px' : n <= 8 ? '5px' : '3px'; }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  function render() {
    var board = getBoard();
    if (!board) return;
    board.innerHTML = '';
    board.style.display = 'grid';
    board.style.gridTemplateColumns = 'repeat(' + COLS + ', 1fr)';

    var revealWon   = isPhotoPuzzle && photoUrl && gameWon;
    var photoActive = isPhotoPuzzle && photoUrl && photoMode === 'tiles' && !gameWon;

    if (revealWon || photoActive) {
      board.style.gap          = '0';
      board.style.padding      = '0';
      board.style.border       = 'none';
      board.style.borderRadius = '0';
    } else {
      board.style.gap          = boardGap(COLS);
      board.style.padding      = boardPad(COLS);
      board.style.border       = '';
      board.style.borderRadius = '';
    }

    var fontSize = tileFontSize(COLS);
    var total    = COLS * COLS;

    for (var i = 0; i < total; i++) {
      var tile = document.createElement('div');
      tile.classList.add('fp-tile');
      tile.style.fontSize = fontSize;

      if (revealWon) {
        tile.style.cssText = 'background:transparent;border:none;border-radius:0;';
      } else if (tiles[i] === 0) {
        tile.classList.add('fp-blank');
        tile.dataset.index = i;
      } else {
        tile.dataset.index = i;
        tile.addEventListener('click', onTileClick);

        if (isPhotoPuzzle && photoUrl && photoMode === 'tiles') {
          var solvedPos = tiles[i] - 1;
          var solvedCol = solvedPos % COLS;
          var solvedRow = Math.floor(solvedPos / COLS);
          tile.style.backgroundImage    = 'url(' + photoUrl + ')';
          tile.style.backgroundSize     = (COLS * 100) + '% ' + (COLS * 100) + '%';
          tile.style.backgroundPosition =
            (solvedCol / (COLS - 1) * 100) + '% ' + (solvedRow / (COLS - 1) * 100) + '%';
          tile.style.backgroundRepeat   = 'no-repeat';
          tile.style.border             = '2px solid rgba(255,255,255,0.25)';
          var lbl = document.createElement('span');
          lbl.textContent = tiles[i];
          lbl.style.cssText = 'position:absolute;bottom:2px;right:3px;font-size:0.55rem;' +
            'color:#fff;text-shadow:0 1px 2px #000;pointer-events:none;';
          tile.style.position = 'relative';
          tile.style.fontSize = fontSize;
          tile.appendChild(lbl);
        } else {
          tile.textContent = tiles[i];
        }
      }
      board.appendChild(tile);
    }

    // On win: show reveal image if provided, otherwise fall back to tile image
    if (isPhotoPuzzle && photoUrl && gameWon) {
      var winBg = revealUrl || photoUrl;
      board.style.backgroundImage    = 'url(' + winBg + ')';
      board.style.backgroundSize     = 'cover';
      board.style.backgroundPosition = 'center';
    } else {
      board.style.backgroundImage = '';
    }
  }

  // ---------------------------------------------------------------------------
  // Move logic
  // ---------------------------------------------------------------------------
  function onTileClick(e) {
    if (gameWon) return;

    var clickedIndex = parseInt(e.currentTarget.dataset.index, 10);
    var blankIndex   = tiles.indexOf(0);

    var clickedRow = Math.floor(clickedIndex / COLS);
    var clickedCol = clickedIndex % COLS;
    var blankRow   = Math.floor(blankIndex / COLS);
    var blankCol   = blankIndex % COLS;

    var steps = 0;

    if (clickedRow === blankRow && clickedCol !== blankCol) {
      var dir = clickedCol < blankCol ? -1 : 1;
      var col = blankCol;
      while (col !== clickedCol) {
        var nextCol = col + dir;
        tiles[blankRow * COLS + col] = tiles[blankRow * COLS + nextCol];
        col = nextCol;
        steps++;
      }
      tiles[blankRow * COLS + clickedCol] = 0;
    } else if (clickedCol === blankCol && clickedRow !== blankRow) {
      var dir = clickedRow < blankRow ? -1 : 1;
      var row = blankRow;
      while (row !== clickedRow) {
        var nextRow = row + dir;
        tiles[row * COLS + blankCol] = tiles[nextRow * COLS + blankCol];
        row = nextRow;
        steps++;
      }
      tiles[clickedRow * COLS + blankCol] = 0;
    } else {
      return;
    }

    // Start timer on first move
    if (moveCount === 0 && startTime === null) {
      startTime = Date.now();
      timerInterval = setInterval(updateTimer, 100);
    }

    moveCount += steps;
    updateMoves();
    render();
    checkWin();
  }

  function isAdjacent(a, b) {
    var rowA = Math.floor(a / COLS), colA = a % COLS;
    var rowB = Math.floor(b / COLS), colB = b % COLS;
    return (Math.abs(rowA - rowB) + Math.abs(colA - colB)) === 1;
  }

  // ---------------------------------------------------------------------------
  // Win detection
  // ---------------------------------------------------------------------------
  function checkWin() {
    var total = COLS * COLS;
    for (var i = 0; i < total; i++) {
      if (tiles[i] !== WIN_STATE[i]) return;
    }
    // Won!
    gameWon = true;
    stopTimer();
    render(); // re-render so reveal-mode shows the background photo
    var winMsg = document.getElementById('fp-win-msg');
    if (winMsg) winMsg.style.display = 'block';
    if (userName) {
      autoSubmitScore();
    } else {
      showScoreForm();
    }
  }

  // ---------------------------------------------------------------------------
  // Timer
  // ---------------------------------------------------------------------------
  function updateTimer() {
    if (startTime === null) return;
    elapsedMs = Date.now() - startTime;
    var timeEl = getTimeEl();
    if (timeEl) {
      timeEl.textContent = (elapsedMs / 1000).toFixed(1);
    }
  }

  function stopTimer() {
    if (timerInterval !== null) {
      clearInterval(timerInterval);
      timerInterval = null;
    }
    if (startTime !== null) {
      elapsedMs = Date.now() - startTime;
    }
    var timeEl = getTimeEl();
    if (timeEl) {
      timeEl.textContent = (elapsedMs / 1000).toFixed(1);
    }
  }

  function resetTimer() {
    stopTimer();
    startTime = null;
    elapsedMs = 0;
    var timeEl = getTimeEl();
    if (timeEl) timeEl.textContent = '0.0';
  }

  // ---------------------------------------------------------------------------
  // Move counter
  // ---------------------------------------------------------------------------
  function updateMoves() {
    var movesEl = getMovesEl();
    if (movesEl) movesEl.textContent = moveCount;
  }

  function resetMoves() {
    moveCount = 0;
    updateMoves();
  }

  // ---------------------------------------------------------------------------
  // Score form
  // ---------------------------------------------------------------------------
  function showScoreForm() {
    var form = getScoreForm();
    if (!form) return;

    var timeValEl = getTimeValEl();
    var movesValEl = getMovesValEl();

    if (timeValEl) timeValEl.value = Math.round(elapsedMs);
    if (movesValEl) movesValEl.value = moveCount;

    form.style.display = 'flex';

    // Wire up submission (once)
    var submitBtn = form.querySelector('#fp-submit') || form.querySelector('button[type="submit"]') || form.querySelector('button');
    if (submitBtn && !submitBtn.dataset.wired) {
      submitBtn.dataset.wired = '1';
      submitBtn.addEventListener('click', function (e) {
        e.preventDefault();
        submitScore();
      });
    }

    // Also handle native form submit
    if (!form.dataset.wired) {
      form.dataset.wired = '1';
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        submitScore();
      });
    }
  }

  function hideScoreForm() {
    var form = getScoreForm();
    if (form) form.style.display = 'none';
  }

  // ---------------------------------------------------------------------------
  // Score submission
  // ---------------------------------------------------------------------------
  function submitScore() {
    var nameEl = document.getElementById('fp-name');
    var timeValEl = getTimeValEl();
    var movesValEl = getMovesValEl();
    var msgEl = document.getElementById('fp-score-msg');

    var name = nameEl ? nameEl.value.trim() : '';
    var time_ms = timeValEl ? parseInt(timeValEl.value, 10) : Math.round(elapsedMs);
    var moves = movesValEl ? parseInt(movesValEl.value, 10) : moveCount;

    var payload = {
      name: name,
      puzzle_date: dailyDate,
      grid_size: gridSize,
      time_ms: time_ms,
      moves: moves
    };

    fetch('/api/fifteen-puzzle-scores', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify(payload)
    })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function () {
        hideScoreForm();
        if (msgEl) {
          msgEl.textContent = 'Score submitted!';
          msgEl.style.display = '';
        }
      })
      .catch(function () {
        if (msgEl) {
          msgEl.textContent = 'Failed to submit score.';
          msgEl.style.display = '';
        }
      });
  }

  // ---------------------------------------------------------------------------
  // Auto-submit (logged-in users)
  // ---------------------------------------------------------------------------
  function autoSubmitScore() {
    var msgEl = document.getElementById('fp-score-msg');
    var payload = {
      name: userName,
      puzzle_date: dailyDate,
      grid_size: gridSize,
      time_ms: Math.round(elapsedMs),
      moves: moveCount
    };

    fetch('/api/fifteen-puzzle-scores', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify(payload)
    })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function () {
        if (msgEl) {
          msgEl.textContent = 'Score submitted!';
          msgEl.style.display = '';
        }
      })
      .catch(function () {
        // Fall back to the manual form on error
        showScoreForm();
      });
  }

  // ---------------------------------------------------------------------------
  // Reset
  // ---------------------------------------------------------------------------
  function resetGame() {
    gameWon = false;
    var total = COLS * COLS;
    var boardHash = (window.FP_BOARD_HASH || '');
    if (isPhotoPuzzle && boardHash) {
      var decoded = hashToTiles(boardHash);
      tiles = (decoded && decoded.length === total) ? decoded : generateDailyBoard(dailyDate, COLS);
    } else {
      tiles = generateDailyBoard(dailyDate, COLS);
    }
    resetTimer();
    resetMoves();
    hideScoreForm();

    var msgEl = document.getElementById('fp-score-msg');
    if (msgEl) { msgEl.textContent = ''; msgEl.style.display = 'none'; }

    var winMsg = document.getElementById('fp-win-msg');
    if (winMsg) winMsg.style.display = 'none';

    render();
  }

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  function initFifteenPuzzle() {
    dailyDate    = (window.FP_DATE       || new Date().toISOString().slice(0, 10));
    gridSize     = (window.FP_GRID_SIZE  || '4x4');
    COLS         = parseInt(gridSize.split('x')[0], 10) || 4;
    photoUrl     = (window.FP_PHOTO_URL  || '');
    photoMode    = (window.FP_PHOTO_MODE || '');
    revealUrl    = (window.FP_REVEAL_URL || '');
    isPhotoPuzzle = !!(photoUrl && photoMode);
    userName     = (window.FP_USER_NAME  || '');

    // Build win state: [1, 2, ..., N*N-1, 0]
    WIN_STATE = [];
    for (var w = 1; w < COLS * COLS; w++) WIN_STATE.push(w);
    WIN_STATE.push(0);

    // For photo puzzles, decode the fixed board from the hash rather than
    // re-seeding by date so the scramble always matches the uploaded layout.
    var boardHash = (window.FP_BOARD_HASH || '');
    if (isPhotoPuzzle && boardHash) {
      var decoded = hashToTiles(boardHash);
      if (decoded && decoded.length === COLS * COLS) {
        tiles = decoded;
      }
    }

    // Hide score form initially
    hideScoreForm();

    // Wire reset button
    var resetBtn = getResetBtn();
    if (resetBtn) {
      resetBtn.addEventListener('click', resetGame);
    }

    resetGame();
  }

  // Export
  window.initFifteenPuzzle = initFifteenPuzzle;

  window.addEventListener('DOMContentLoaded', initFifteenPuzzle);
})();
