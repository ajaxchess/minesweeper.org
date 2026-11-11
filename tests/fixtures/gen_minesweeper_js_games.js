// Records real games from static/src/js/minesweeper.js for the server replay
// parity test (F-MS-VERIFY, tests/test_minesweeper_engine.py).
//
// Runs the real script against a stub DOM and plays each game to a win by firing
// the same cell events a browser does (click, contextmenu, dblclick, flag mode).
// What gets saved is the exact body the script posts to /api/scores, so the test
// proves minesweeper_engine.py reaches the same result from the same request.
//
// The player knows where the mines are (it reads the script's own state), which
// lets it win every game while still doing the awkward things real players do:
// wrong flags, question marks, clicks on revealed cells, chords that do nothing.
//
// Regenerate after changing reveal(), chord(), flag() or the click handlers:
//
//   node tests/fixtures/gen_minesweeper_js_games.js
'use strict';
const fs = require('fs'), vm = require('vm'), path = require('path');
const ROOT = path.resolve(__dirname, '..', '..');
const SRC = fs.readFileSync(path.join(ROOT, 'static/src/js/minesweeper.js'), 'utf8');
const OUT = path.join(__dirname, 'minesweeper_js_games.json');

// Deterministic PRNG (mulberry32) so the fixture only changes when the rules do.
function prng(seed) {
  return () => {
    seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rnd = prng(20261111);
const pick = arr => arr[Math.floor(rnd() * arr.length)];

class El {
  constructor(id) {
    this.id = id; this.children = []; this.listeners = {}; this.dataset = {};
    this.style = { setProperty() {} }; this._cls = new Set(); this.textContent = ''; this.value = '';
  }
  get className() { return [...this._cls].join(' '); }
  set className(v) { this._cls = new Set(String(v).split(/\s+/).filter(Boolean)); }
  get classList() {
    const s = this._cls;
    return { add: c => s.add(c), remove: c => s.delete(c), contains: c => s.has(c),
             toggle: (c, f) => ((f ?? !s.has(c)) ? s.add(c) : s.delete(c)) };
  }
  set innerHTML(v) { this.children = []; this._html = v; }
  get innerHTML() { return this._html || ''; }
  appendChild(c) { this.children.push(c); return c; }
  addEventListener(t, f) { (this.listeners[t] ||= []).push(f); }
  fire(t) { (this.listeners[t] || []).forEach(f => f({ preventDefault() {}, target: this, touches: [] })); }
  querySelector() { return new El(); }
  querySelectorAll() { return []; }
  focus() {} remove() {} setAttribute() {} getAttribute() { return null; }
}

const els = {};
const byId = id => (els[id] ||= new El(id));
const board = byId('board');
board.dataset.username = 'Fixture';   // logged in: the script submits the score itself
Object.assign(board.dataset, { mode: 'beginner', rows: '9', cols: '9', mines: '10' });

let clock = 0;
const posted = [];
let tokenRequests = 0;
const docListeners = {};
const store = { noGuess: 'false' };
const storage = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); },
                  removeItem: k => { delete store[k]; } };

const ctx = vm.createContext({
  console, URLSearchParams, Promise, btoa, atob,
  setTimeout: () => 0, clearTimeout() {}, setInterval: () => 1, clearInterval() {},
  performance: { now: () => clock },
  navigator: { userAgent: 'fixture', sendBeacon: () => true },
  localStorage: storage, sessionStorage: storage,
  fetch: (url, opts) => {
    if (url === '/api/scores') posted.push(JSON.parse(opts.body));
    if (url === '/api/scores/start') tokenRequests++;
    return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true, id: 1, token: 'fixture-token' }) });
  },
  document: {
    body: new El('body'), documentElement: new El('html'), visibilityState: 'visible',
    getElementById: byId, createElement: () => new El(),
    querySelector: sel => {
      const m = /\[data-r="(\d+)"\]\[data-c="(\d+)"\]/.exec(sel);
      return m ? cell(+m[1], +m[2]) : null;
    },
    querySelectorAll: () => [],
    addEventListener: (t, f) => (docListeners[t] ||= []).push(f),
  },
});
ctx.window = ctx;
ctx.T = new Proxy({}, { get: (_, k) => String(k) });
ctx.location = { pathname: '/', search: '' };
ctx.addEventListener = () => {};
vm.runInContext(SRC, ctx);
// The script's Math is the context's own; make its mine placement repeatable too.
ctx.__rnd = prng(987654321);
vm.runInContext('Math.random = __rnd;', ctx);

const state = () => vm.runInContext('state', ctx);
const cell = (r, c) => board.children[r * state().cols + c];

const tick = () => { clock += 20 + Math.floor(rnd() * 900); };

function playGame({ mode, rows, cols, mines, noGuess, chording }) {
  board.dataset.mode = mode;
  clock = 1000 + Math.floor(rnd() * 5000);
  vm.runInContext(`initGame(${rows}, ${cols}, ${mines}, ${noGuess}, ${chording})`, ctx);
  const evil = mode === 'evil';
  const all = [];
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) all.push([r, c]);

  // Before the first reveal: stray flags, and in evil mode clicks the game ignores.
  if (rnd() < 0.4) { const [r, c] = pick(all); if (!(evil && r === 0 && c === cols - 1)) cell(r, c).fire('contextmenu'); }
  if (evil) for (let i = 0; i < 2; i++) { const [r, c] = pick(all.filter(([r, c]) => !(r === 0 && c === cols - 1))); cell(r, c).fire('click'); }

  // First reveal. A flag on that cell would block it, so clear it the way a player would.
  const first = evil ? [0, cols - 1] : pick(all);
  while (state().flagged[first[0]][first[1]] === 1) cell(...first).fire('contextmenu');
  cell(...first).fire('click');

  let guard = 0;
  while (!state().over) {
    if (++guard > 20000) throw new Error('game did not finish');
    tick();
    const s = state();
    const isMine = (r, c) => s.mineSet.has(r * cols + c);
    const hidden = all.filter(([r, c]) => !s.revealed[r][c]);
    const safeHidden = hidden.filter(([r, c]) => !isMine(r, c));
    const nbrs = (r, c) => all.filter(([nr, nc]) => Math.abs(nr - r) <= 1 && Math.abs(nc - c) <= 1 && !(nr === r && nc === c));
    const roll = rnd();

    if (roll < 0.14) {                                   // flag a mine (or cycle its mark)
      const m = hidden.filter(([r, c]) => isMine(r, c));
      if (m.length) cell(...pick(m)).fire('contextmenu');
    } else if (roll < 0.19) {                            // wrong flag / question mark on a safe cell
      cell(...pick(safeHidden)).fire('contextmenu');
    } else if (roll < 0.24) {                            // same, through the mobile flag-mode toggle
      vm.runInContext('toggleFlagMode()', ctx);
      cell(...pick(hidden)).fire('click');
      vm.runInContext('toggleFlagMode()', ctx);
    } else if (roll < 0.30) {                            // click that does nothing
      const revealed = all.filter(([r, c]) => s.revealed[r][c]);
      cell(...pick(revealed.length ? revealed : safeHidden)).fire('click');
    } else if (roll < 0.50) {                            // chord, only where it cannot lose
      const ok = all.filter(([r, c]) => s.revealed[r][c] && s.board[r][c] > 0 &&
        nbrs(r, c).every(([nr, nc]) => s.revealed[nr][nc] || isMine(nr, nc) === (s.flagged[nr][nc] === 1)));
      if (ok.length) {
        const [r, c] = pick(ok);
        if (rnd() < 0.5) { cell(r, c).fire('click'); cell(r, c).fire('click'); }   // mouse double-click
        cell(r, c).fire('dblclick');
      }
    } else {                                             // reveal a safe cell
      const [r, c] = pick(safeHidden);
      if (s.flagged[r][c] === 1) cell(r, c).fire('contextmenu');   // flag → question mark, which does not block
      cell(r, c).fire('click');
    }
  }
  if (!state().won) throw new Error('fixture player lost a game');
}

const GAMES = [];
const add = (n, g) => { for (let i = 0; i < n; i++) GAMES.push(g); };
add(6, { mode: 'beginner',     rows: 9,  cols: 9,  mines: 10, noGuess: false, chording: true });
add(3, { mode: 'beginner',     rows: 9,  cols: 9,  mines: 10, noGuess: false, chording: false });
add(2, { mode: 'beginner',     rows: 9,  cols: 9,  mines: 10, noGuess: true,  chording: true });
add(4, { mode: 'intermediate', rows: 16, cols: 16, mines: 40, noGuess: false, chording: true });
add(2, { mode: 'intermediate', rows: 16, cols: 16, mines: 40, noGuess: false, chording: false });
add(3, { mode: 'expert',       rows: 30, cols: 16, mines: 99, noGuess: false, chording: true });
add(3, { mode: 'custom',       rows: 5,  cols: 5,  mines: 3,  noGuess: false, chording: true });
add(3, { mode: 'custom',       rows: 8,  cols: 13, mines: 30, noGuess: false, chording: true });
add(2, { mode: 'custom',       rows: 7,  cols: 50, mines: 60, noGuess: false, chording: false });
add(2, { mode: 'evil',         rows: 20, cols: 30, mines: 130, noGuess: true, chording: true });

(async () => {
  (docListeners.DOMContentLoaded || []).forEach(f => f());
  const out = [];
  for (const g of GAMES) {
    const before = posted.length;
    playGame(g);
    for (let i = 0; i < 5; i++) await new Promise(r => setImmediate(r));   // let submitScore finish
    if (posted.length !== before + 1) throw new Error('the script did not post exactly one score');
    if (tokenRequests !== out.length + 1) throw new Error('the script must request one start token per game');
    out.push(posted[posted.length - 1]);
  }
  fs.writeFileSync(OUT, JSON.stringify(out) + '\n');
  const moves = out.reduce((n, p) => n + p.log.length, 0);
  console.log(`wrote ${out.length} games, ${moves} moves → ${path.relative(ROOT, OUT)}`);
})().catch(e => { console.error(e); process.exit(1); });
