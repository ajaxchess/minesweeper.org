// Records real games from the mobile app's game code for the server replay parity
// test (F-MS-VERIFY-APP, tests/test_msmobile_replay.py).
//
// Loads mobile/msmobile/src/gameEngine.js and the reducer in
// mobile/msmobile/src/hooks/useGameState.js (import/export lines stripped, no React
// needed) and plays each game to a win by dispatching the same actions the app's
// GameScreen does. What gets saved is the move log the reducer recorded, the board,
// and the counts the app shows, so the test proves minesweeper_engine.py (app_rules)
// reaches the same result.
//
// The player knows where the mines are, which lets it win every game while still
// doing what real players do: flags before the first tap, wrong flags left in place
// (the app's flood fill opens them), flags put on and taken off, taps on open cells
// and chords that do nothing.
//
// Regenerate after changing the app's reducer, bfsReveal or gameEngine.js:
//
//   node tests/fixtures/gen_msmobile_games.js
'use strict';
const fs = require('fs'), vm = require('vm'), path = require('path');
const ROOT = path.resolve(__dirname, '..', '..');
const APP = path.join(ROOT, 'mobile', 'msmobile', 'src');
const OUT = path.join(__dirname, 'msmobile_games.json');

function strip(src) {
  return src
    .replace(/^import[\s\S]*?from\s+['"][^'"]+['"];?\s*$/gm, '')
    .replace(/^export default function /gm, 'function ')
    .replace(/^export (function|const|let) /gm, '$1 ');
}

const code = [
  strip(fs.readFileSync(path.join(APP, 'gameEngine.js'), 'utf8')),
  strip(fs.readFileSync(path.join(APP, 'hooks', 'useGameState.js'), 'utf8')),
  'globalThis.__app = { reducer, makeInitialState, calc3BV, calcBoardHash, BOARD_SIZES };',
].join('\n');

// Deterministic PRNG (mulberry32): the fixture only changes when the rules do.
function prng(seed) {
  return () => {
    seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rnd = prng(20261126);
const ctx = vm.createContext({ __rnd: rnd, Buffer });   // calcBoardHash uses the global Buffer
vm.runInContext('Math.random = __rnd;\n' + code, ctx, { filename: 'msmobile' });
const { reducer, makeInitialState, calc3BV, calcBoardHash } = ctx.__app;

const pick = arr => arr[Math.floor(rnd() * arr.length)];
const chance = p => rnd() < p;

function neighbours(i, rows, cols) {
  const r = Math.floor(i / cols), c = i % cols, out = [];
  for (let dr = -1; dr <= 1; dr++) for (let dc = -1; dc <= 1; dc++) {
    if (!dr && !dc) continue;
    const nr = r + dr, nc = c + dc;
    if (nr >= 0 && nr < rows && nc >= 0 && nc < cols) out.push(nr * cols + nc);
  }
  return out;
}

function play(mode, noGuess) {
  let s = makeInitialState(mode, noGuess);
  let now = 1_700_000_000_000 + Math.floor(rnd() * 1e6);
  const act = (type, idx) => {
    now += 40 + Math.floor(rnd() * 700);
    s = reducer(s, { type, idx, now });
  };
  const n = s.rows * s.cols;
  const cell = () => Math.floor(rnd() * n);

  // A flag or two before the first tap (t_ms 0), sometimes taken off again.
  if (chance(0.4)) { const i = cell(); act('TOGGLE_FLAG', i); if (chance(0.5)) act('TOGGLE_FLAG', i); }
  let first = cell();
  while (s.flagged[first]) first = cell();
  act('REVEAL', first);

  let guard = 0;
  while (!s.won && guard++ < 20000) {
    if (s.over) throw new Error('the scripted player lost');
    const mines = s.mineSet, board = s.board;
    const isMine = i => mines.has(i);
    const val = i => board[Math.floor(i / s.cols)][i % s.cols];
    const closed = [...Array(n).keys()].filter(i => !s.revealed[i]);
    const safeClosed = closed.filter(i => !isMine(i));

    const roll = rnd();
    if (roll < 0.06) {                      // tap an open cell: the app ignores it
      const open = [...Array(n).keys()].filter(i => s.revealed[i] && val(i) === 0);
      if (open.length) act('REVEAL', pick(open));
    } else if (roll < 0.14) {               // wrong flag on a safe cell, often left there
      act('TOGGLE_FLAG', pick(safeClosed));
    } else if (roll < 0.30) {               // flag a mine
      const m = closed.filter(i => isMine(i) && !s.flagged[i]);
      if (m.length) act('TOGGLE_FLAG', pick(m));
    } else if (roll < 0.42) {               // chord a number (does nothing unless flags match)
      const nums = [...Array(n).keys()].filter(i => s.revealed[i] && val(i) > 0 &&
        neighbours(i, s.rows, s.cols).some(j => !s.revealed[j] && !s.flagged[j]));
      const ready = nums.filter(i => neighbours(i, s.rows, s.cols).every(j =>
        isMine(j) ? s.flagged[j] : !s.flagged[j] || s.revealed[j]));
      // A useless chord: the flag count does not match the number, so nothing opens.
      const idle = nums.filter(i => neighbours(i, s.rows, s.cols)
        .filter(j => s.flagged[j]).length !== val(i));
      const pool = ready.length && chance(0.8) ? ready : idle;
      if (pool.length) act('CHORD', pick(pool));
    } else {                                // reveal a safe cell, taking a wrong flag off first
      const target = pick(safeClosed);
      if (s.flagged[target]) act('TOGGLE_FLAG', target);
      act('REVEAL', target);
    }
  }
  if (!s.won) throw new Error('game did not finish');

  const flaggedOpen = [...Array(n).keys()].filter(i => s.flagged[i] && s.revealed[i]).length;
  return {
    mode, no_guess: noGuess, rows: s.rows, cols: s.cols, mines: s.mines,
    board_hash: calcBoardHash(s.rows, s.cols, s.mineSet),
    log: s.log,
    expected: {
      time_ms: s.log[s.log.length - 1][0],
      bbbv: calc3BV(s.board, s.rows, s.cols, s.mineSet),
      left_clicks: s.leftClicks, right_clicks: s.rightClicks, chord_clicks: s.chordClicks,
      flagged_cells_opened_by_flood_fill: flaggedOpen,
    },
  };
}

const games = [];
for (const [mode, count] of [['beginner', 12], ['intermediate', 6], ['expert', 4]]) {
  for (let k = 0; k < count; k++) games.push(play(mode, k % 2 === 1));
}
fs.writeFileSync(OUT, JSON.stringify(games) + '\n');
console.log(`wrote ${games.length} games to ${path.relative(ROOT, OUT)}; ` +
  `${games.filter(g => g.expected.flagged_cells_opened_by_flood_fill).length} with a flagged cell opened by flood fill`);
