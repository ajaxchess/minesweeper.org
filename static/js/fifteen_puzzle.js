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
  // Solvability check for 4x4 grid
  // A configuration is solvable if (inversions + row_of_blank_from_bottom_1indexed) is even.
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

  function isSolvable(tiles) {
    var inversions = countInversions(tiles);
    var blankIndex = tiles.indexOf(0);
    // row from bottom, 1-indexed (grid is 4 wide)
    var rowFromBottom = 4 - Math.floor(blankIndex / 4);
    return (inversions + rowFromBottom) % 2 === 0;
  }

  // ---------------------------------------------------------------------------
  // Generate daily board
  // ---------------------------------------------------------------------------
  function generateDailyBoard(dateStr) {
    var seed = seedFromDateString(dateStr);
    var rng = makeLCG(seed);
    var base = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 0];

    var tiles;
    var attempts = 0;

    // Try up to 200 times to get a solvable shuffle
    do {
      tiles = shuffle(base, rng);
      attempts++;
    } while (!isSolvable(tiles) && attempts < 200);

    // Force-fix parity if still not solvable: swap tiles[0] and tiles[1]
    // provided neither is blank
    if (!isSolvable(tiles)) {
      var a = 0, b = 1;
      if (tiles[a] === 0) { a = 1; b = 2; }
      if (tiles[b] === 0) { b = 2; }
      var tmp = tiles[a];
      tiles[a] = tiles[b];
      tiles[b] = tmp;
    }

    return tiles;
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
  // Render
  // ---------------------------------------------------------------------------
  function render() {
    var board = getBoard();
    if (!board) return;
    board.innerHTML = '';
    board.style.display = 'grid';
    board.style.gridTemplateColumns = 'repeat(4, 1fr)';

    for (var i = 0; i < 16; i++) {
      var tile = document.createElement('div');
      tile.classList.add('fp-tile');
      if (tiles[i] === 0) {
        tile.classList.add('fp-blank');
        tile.dataset.index = i;
      } else {
        tile.textContent = tiles[i];
        tile.dataset.index = i;
        tile.addEventListener('click', onTileClick);
      }
      board.appendChild(tile);
    }
  }

  // ---------------------------------------------------------------------------
  // Move logic
  // ---------------------------------------------------------------------------
  function onTileClick(e) {
    if (gameWon) return;

    var clickedIndex = parseInt(e.currentTarget.dataset.index, 10);
    var blankIndex = tiles.indexOf(0);

    if (!isAdjacent(clickedIndex, blankIndex)) return;

    // Start timer on first move
    if (moveCount === 0 && startTime === null) {
      startTime = Date.now();
      timerInterval = setInterval(updateTimer, 100);
    }

    // Swap
    tiles[blankIndex] = tiles[clickedIndex];
    tiles[clickedIndex] = 0;
    moveCount++;

    updateMoves();
    render();
    checkWin();
  }

  function isAdjacent(a, b) {
    var rowA = Math.floor(a / 4), colA = a % 4;
    var rowB = Math.floor(b / 4), colB = b % 4;
    return (Math.abs(rowA - rowB) + Math.abs(colA - colB)) === 1;
  }

  // ---------------------------------------------------------------------------
  // Win detection
  // ---------------------------------------------------------------------------
  var WIN_STATE = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 0];

  function checkWin() {
    for (var i = 0; i < 16; i++) {
      if (tiles[i] !== WIN_STATE[i]) return;
    }
    // Won!
    gameWon = true;
    stopTimer();
    var winMsg = document.getElementById('fp-win-msg');
    if (winMsg) winMsg.style.display = 'block';
    showScoreForm();
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
  // Reset
  // ---------------------------------------------------------------------------
  function resetGame() {
    gameWon = false;
    tiles = generateDailyBoard(dailyDate);
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
    dailyDate = (window.FP_DATE || new Date().toISOString().slice(0, 10));

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
