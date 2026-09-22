/* sudoku.js — F53 Sudoku game engine
 * Puzzle generation, input handling, timer, hints, score submission.
 * ?v=1
 */
"use strict";
(function () {

// ── Server-injected globals ───────────────────────────────────────────────────
const CFG        = window.SUDOKU_CFG || {};
const TODAY      = CFG.today      || new Date().toISOString().slice(0, 10);
const DIFFICULTY = CFG.difficulty || "easy";
const SEED       = CFG.seed       || 1;
const GIVENS_STR = CFG.givens     || null;   // 81-char string → replay mode
const USER       = CFG.user       || null;

// ── Seeded RNG: mulberry32 ────────────────────────────────────────────────────
function mkRng(seed) {
  let s = seed >>> 0;
  return function () {
    s = (s + 0x6D2B79F5) >>> 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function shuffle(arr, rng) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

// ── Sudoku validation ─────────────────────────────────────────────────────────
function isValid(board, row, col, num) {
  for (let c = 0; c < 9; c++)
    if (board[row * 9 + c] === num) return false;
  for (let r = 0; r < 9; r++)
    if (board[r * 9 + col] === num) return false;
  const br = Math.floor(row / 3) * 3, bc = Math.floor(col / 3) * 3;
  for (let r = br; r < br + 3; r++)
    for (let c = bc; c < bc + 3; c++)
      if (board[r * 9 + c] === num) return false;
  return true;
}

// ── Puzzle generation ─────────────────────────────────────────────────────────

// Generate a complete valid solution with shuffled candidates (seeded)
function generateSolution(rng) {
  const board = new Array(81).fill(0);
  function solve(pos) {
    if (pos === 81) return true;
    if (board[pos] !== 0) return solve(pos + 1);
    const r = Math.floor(pos / 9), c = pos % 9;
    const digits = shuffle([1,2,3,4,5,6,7,8,9], rng);
    for (const n of digits) {
      if (isValid(board, r, c, n)) {
        board[pos] = n;
        if (solve(pos + 1)) return true;
        board[pos] = 0;
      }
    }
    return false;
  }
  solve(0);
  return board;
}

// Count solutions stopping at 2 — uses MRV heuristic for speed
function countSolutions(boardIn) {
  let count = 0;
  const b = [...boardIn];

  function bestCell() {
    let pos = -1, best = 10;
    for (let i = 0; i < 81; i++) {
      if (b[i] !== 0) continue;
      const r = Math.floor(i / 9), c = i % 9;
      let n = 0;
      for (let v = 1; v <= 9; v++) if (isValid(b, r, c, v)) n++;
      if (n === 0) return -2;       // dead end
      if (n < best) { best = n; pos = i; }
      if (best === 1) break;
    }
    return pos;
  }

  function solve() {
    if (count > 1) return;
    const pos = bestCell();
    if (pos === -2) return;
    if (pos === -1) { count++; return; }
    const r = Math.floor(pos / 9), c = pos % 9;
    for (let v = 1; v <= 9; v++) {
      if (isValid(b, r, c, v)) {
        b[pos] = v;
        solve();
        b[pos] = 0;
      }
    }
  }

  solve();
  return count;
}

// Remove cells from a complete solution while keeping unique solvability
const GIVENS_TARGET = { daily: 38, easy: 38, medium: 32, hard: 27, expert: 24 };

function createPuzzle(solution, rng, difficulty) {
  const target = GIVENS_TARGET[difficulty] || 36;
  const puzzle = [...solution];
  const indices = shuffle([...Array(81).keys()], rng);
  let givens = 81;

  for (const idx of indices) {
    if (givens <= target) break;
    const val = puzzle[idx];
    puzzle[idx] = 0;
    if (countSolutions(puzzle) === 1) {
      givens--;
    } else {
      puzzle[idx] = val;   // restore — removal would create non-unique puzzle
    }
  }
  return puzzle;
}

// Deterministic solver (no shuffle) for reconstructing solution from givens
function solvePuzzle(puzzleIn) {
  const b = [...puzzleIn];
  function solve() {
    let pos = -1, best = 10;
    for (let i = 0; i < 81; i++) {
      if (b[i] !== 0) continue;
      const r = Math.floor(i / 9), c = i % 9;
      let n = 0;
      for (let v = 1; v <= 9; v++) if (isValid(b, r, c, v)) n++;
      if (n === 0) return false;
      if (n < best) { best = n; pos = i; }
      if (best === 1) break;
    }
    if (pos === -1) return true;
    const r = Math.floor(pos / 9), c = pos % 9;
    for (let v = 1; v <= 9; v++) {
      if (isValid(b, r, c, v)) {
        b[pos] = v;
        if (solve()) return true;
        b[pos] = 0;
      }
    }
    return false;
  }
  return solve() ? b : null;
}

function boardToGivens(puzzle) {
  return puzzle.map(n => n || 0).join('');
}

// SHA-256 via Web Crypto (async Promise)
function hashGivens(givensStr) {
  return crypto.subtle.digest('SHA-256', new TextEncoder().encode(givensStr))
    .then(buf => Array.from(new Uint8Array(buf))
      .map(b => b.toString(16).padStart(2, '0')).join(''));
}

// ── Game state ────────────────────────────────────────────────────────────────
let puzzle      = null;    // 81 ints, 0 = empty given
let solution    = null;    // 81 ints, full answer
let board       = null;    // 81 ints, current user state (given cells stay fixed)
let selected    = -1;
let hintsUsed   = 0;
let finished    = false;
let showErrors  = true;
let givensStr   = null;
let boardHashP  = null;    // Promise<string>

// ── Timer ─────────────────────────────────────────────────────────────────────
let timerActive  = false;
let timerStart   = 0;
let timerAccum   = 0;      // accumulated ms when paused
let timerIval    = null;

function startTimer() {
  if (timerActive) return;
  timerActive = true;
  timerStart  = performance.now();
  timerIval   = setInterval(updateTimerDisplay, 200);
}

function pauseTimer() {
  if (!timerActive || !timerIval) return;
  timerAccum += performance.now() - timerStart;
  clearInterval(timerIval);
  timerIval = null;
}

function resumeTimer() {
  if (!timerActive || finished || timerIval) return;
  timerStart = performance.now();
  timerIval  = setInterval(updateTimerDisplay, 200);
}

function stopTimer() {
  if (timerIval) { clearInterval(timerIval); timerIval = null; }
  if (timerActive) timerAccum += performance.now() - timerStart;
}

function elapsedMs() {
  if (!timerActive) return 0;
  if (!timerIval)   return timerAccum;
  return timerAccum + (performance.now() - timerStart);
}

function fmtTime(ms) {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return m > 0
    ? `${m}:${String(s % 60).padStart(2, '0')}`
    : `${s}s`;
}

function updateTimerDisplay() {
  const el = document.getElementById('su-timer');
  if (el) el.textContent = fmtTime(elapsedMs());
}

// Pause/resume on tab visibility
document.addEventListener('visibilitychange', () => {
  if (document.hidden) pauseTimer();
  else                 resumeTimer();
});

// ── DOM helpers ───────────────────────────────────────────────────────────────
function $ (id) { return document.getElementById(id); }

// ── Board rendering ───────────────────────────────────────────────────────────
function renderBoard() {
  const el = $('su-board');
  if (!el) return;
  el.innerHTML = '';

  const selRow = selected >= 0 ? Math.floor(selected / 9) : -1;
  const selCol = selected >= 0 ? selected % 9 : -1;
  const selBox = selected >= 0
    ? Math.floor(selRow / 3) * 3 + Math.floor(selCol / 3) : -1;

  for (let i = 0; i < 81; i++) {
    const cell = document.createElement('div');
    cell.className = 'su-cell';
    cell.dataset.idx = i;

    const r = Math.floor(i / 9), c = i % 9;
    const box = Math.floor(r / 3) * 3 + Math.floor(c / 3);

    if (c % 3 === 0 && c > 0) cell.classList.add('su-cell--bl');
    if (r % 3 === 0 && r > 0) cell.classList.add('su-cell--bt');

    if (puzzle[i] !== 0) {
      cell.classList.add('su-cell--given');
      cell.textContent = puzzle[i];
    } else if (board[i] !== 0) {
      cell.textContent = board[i];
      if (showErrors && board[i] !== solution[i])
        cell.classList.add('su-cell--error');
    }

    if (i === selected) {
      cell.classList.add('su-cell--selected');
    } else if (selected >= 0) {
      if (r === selRow || c === selCol || box === selBox)
        cell.classList.add('su-cell--peer');
    }

    // Highlight same digit
    const selVal = selected >= 0 ? (board[selected] || puzzle[selected]) : 0;
    const cellVal = board[i] || puzzle[i];
    if (selVal > 0 && cellVal === selVal && i !== selected)
      cell.classList.add('su-cell--same-digit');

    cell.addEventListener('click', () => onCellClick(i));
    el.appendChild(cell);
  }
}

function updateHintsDisplay() {
  const el = $('su-hints-used');
  if (el) el.textContent = hintsUsed;
}

// ── Input handling ────────────────────────────────────────────────────────────
function onCellClick(idx) {
  if (finished) return;
  if (puzzle[idx] !== 0) { selectCell(idx); return; }  // given — just select

  if (idx === selected) {
    // Tap-to-cycle: advance through 1–9 then blank
    const cur = board[idx] || 0;
    const next = cur >= 9 ? 0 : cur + 1;
    setCell(idx, next);
  } else {
    selectCell(idx);
  }
}

function selectCell(idx) {
  selected = idx;
  renderBoard();
}

function setCell(idx, num) {
  if (finished || idx < 0 || puzzle[idx] !== 0) return;
  startTimer();
  board[idx] = num;
  renderBoard();
  checkComplete();
}

function onNumpadClick(num) {
  if (finished || selected < 0 || puzzle[selected] !== 0) return;
  setCell(selected, num);
}

function onKeyDown(e) {
  if (finished) return;
  if (e.target.tagName === 'INPUT') return;   // don't intercept name input
  if (e.key >= '1' && e.key <= '9') { e.preventDefault(); onNumpadClick(+e.key); }
  else if (e.key === 'Backspace' || e.key === 'Delete' || e.key === '0') { e.preventDefault(); onNumpadClick(0); }
  else if (e.key === 'ArrowRight') { e.preventDefault(); moveSelect(0,  1); }
  else if (e.key === 'ArrowLeft')  { e.preventDefault(); moveSelect(0, -1); }
  else if (e.key === 'ArrowDown')  { e.preventDefault(); moveSelect(1,  0); }
  else if (e.key === 'ArrowUp')    { e.preventDefault(); moveSelect(-1, 0); }
}

function moveSelect(dr, dc) {
  if (selected < 0) { selectCell(0); return; }
  const r = Math.floor(selected / 9) + dr;
  const c = (selected % 9) + dc;
  if (r >= 0 && r < 9 && c >= 0 && c < 9) selectCell(r * 9 + c);
}

// ── Game logic ────────────────────────────────────────────────────────────────
function hint() {
  if (finished || selected < 0 || puzzle[selected] !== 0) return;
  if (board[selected] === solution[selected]) return;  // already correct
  hintsUsed++;
  setCell(selected, solution[selected]);
  updateHintsDisplay();
}

function checkComplete() {
  for (let i = 0; i < 81; i++)
    if (board[i] !== solution[i]) return;
  onComplete();
}

function onComplete() {
  finished = true;
  stopTimer();
  const ms = Math.round(elapsedMs());

  $('su-result-time').textContent   = fmtTime(ms);
  $('su-result-hints').textContent  =
    hintsUsed === 0 ? 'No hints used'
                    : `${hintsUsed} hint${hintsUsed !== 1 ? 's' : ''} used`;
  $('su-result').style.display = '';

  if (USER && USER.email) {
    const nameEl = $('su-result-authed-name');
    if (nameEl) nameEl.textContent = USER.display_name || USER.email.split('@')[0];
    $('su-form').style.display = 'none';
    doSubmit(USER.display_name || USER.email.split('@')[0], ms);
  } else {
    const saved = localStorage.getItem('su_name');
    if (saved) $('su-name').value = saved;
    $('su-form').style.display = '';
  }
}

async function doSubmit(name, ms) {
  const feedback = $('su-feedback');
  if (feedback) feedback.textContent = 'Submitting…';
  const btn = $('su-submit');
  if (btn) btn.disabled = true;

  try {
    const hash = await boardHashP;
    const res = await fetch('/api/sudoku-scores', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        puzzle_date:  TODAY,
        difficulty:   DIFFICULTY,
        board_hash:   hash,
        board_givens: givensStr,
        time_ms:      ms,
        hints_used:   hintsUsed,
      }),
    });
    if (res.ok) {
      if (feedback) feedback.textContent = 'Score submitted! ✓';
    } else {
      if (feedback) feedback.textContent = 'Could not submit score.';
      if (btn) btn.disabled = false;
    }
  } catch {
    if (feedback) feedback.textContent = 'Network error — try again.';
    if (btn) btn.disabled = false;
  }
}

// ── Initialisation ────────────────────────────────────────────────────────────
function initGame(givensInput) {
  if (givensInput) {
    puzzle = givensInput.split('').map(Number);
    solution = solvePuzzle(puzzle);
    if (!solution) { console.error('Provided puzzle has no solution'); return; }
    givensStr = givensInput;
  } else {
    const rng = mkRng(SEED);
    solution = generateSolution(rng);
    puzzle   = createPuzzle(solution, rng, DIFFICULTY);
    givensStr = boardToGivens(puzzle);
  }

  board      = [...puzzle];
  selected   = -1;
  hintsUsed  = 0;
  finished   = false;
  timerActive = false;
  timerAccum  = 0;
  timerIval   = null;

  boardHashP = hashGivens(givensStr);
  updateHintsDisplay();
  updateTimerDisplay();
  renderBoard();
}

// ── Boot ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const loading = $('su-loading');
  if (loading) loading.style.display = '';

  // Yield one frame so the browser paints the loading message before the
  // potentially-blocking puzzle generation runs.
  setTimeout(() => {
    initGame(GIVENS_STR);
    if (loading) loading.style.display = 'none';

    // Keyboard
    document.addEventListener('keydown', onKeyDown);

    // Numpad
    document.querySelectorAll('.su-numpad-btn').forEach(btn =>
      btn.addEventListener('click', () => onNumpadClick(+btn.dataset.num))
    );
    const erase = $('su-erase');
    if (erase) erase.addEventListener('click', () => onNumpadClick(0));

    // Hint
    const hint_btn = $('su-hint');
    if (hint_btn) hint_btn.addEventListener('click', hint);

    // Mistake highlight toggle
    const toggle = $('su-toggle-errors');
    if (toggle) {
      toggle.classList.toggle('su-btn--on', showErrors);
      toggle.addEventListener('click', () => {
        showErrors = !showErrors;
        toggle.classList.toggle('su-btn--on', showErrors);
        renderBoard();
      });
    }

    // New game
    const newGame = $('su-new-game');
    if (newGame) newGame.addEventListener('click', () => {
      const dest = DIFFICULTY === 'daily' ? '/other/sudoku/daily'
                                          : `/other/sudoku/${DIFFICULTY}`;
      window.location.href = dest;
    });

    // Submit (guest)
    const submitBtn = $('su-submit');
    if (submitBtn) submitBtn.addEventListener('click', () => {
      const nameEl = $('su-name');
      const name = (nameEl.value || '').trim();
      if (!name) { $('su-feedback').textContent = 'Please enter a name.'; return; }
      localStorage.setItem('su_name', name);
      $('su-form').style.display = 'none';
      doSubmit(name, Math.round(elapsedMs()));
    });

    // Play again
    const again = $('su-play-again');
    if (again) again.addEventListener('click', () => {
      const dest = DIFFICULTY === 'daily' ? '/other/sudoku/daily'
                                          : `/other/sudoku/${DIFFICULTY}`;
      window.location.href = dest;
    });

  }, 30);
});

})();
