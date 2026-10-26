// Behaviour test for static/src/js/sudoku.js (F-SUDOKU-ASSISTS): runs the real
// script against a stub DOM and plays like a user — tabs, checkboxes, numpad,
// cell clicks — then checks candidates, notes, conflicts, auto check and the
// submitted assists bitmask. CI is Python-only; run it by hand after changes:
//
//   node tests/js/sudoku_behaviour.js
'use strict';
const fs = require('fs'), vm = require('vm'), path = require('path');
const ROOT = path.resolve(__dirname, '..', '..');
const SRC = fs.readFileSync(path.join(ROOT, 'static/src/js/sudoku.js'), 'utf8');

class El {
  constructor(id) { this.id = id; this.children = []; this.listeners = {}; this.dataset = {}; this.style = {};
    this._cls = new Set(); this.textContent = ''; this.checked = false; this.value = ''; }
  get className() { return [...this._cls].join(' '); }
  set className(v) { this._cls = new Set(v.split(/\s+/).filter(Boolean)); }
  get classList() { const s = this._cls; return { add: c => s.add(c), remove: c => s.delete(c),
    toggle: (c, f) => (f ?? !s.has(c)) ? s.add(c) : s.delete(c), contains: c => s.has(c) }; }
  set innerHTML(v) { this.children = []; this._html = v; }
  get innerHTML() { return this._html || ''; }
  appendChild(c) { this.children.push(c); }
  addEventListener(t, f) { (this.listeners[t] ||= []).push(f); }
  fire(t) { (this.listeners[t] || []).forEach(f => f({ target: this })); }
}
const els = {};
const byId = id => (els[id] ||= new El(id));
const numpad = Array.from({ length: 9 }, (_, i) => { const e = new El('np' + (i + 1)); e.dataset.num = String(i + 1); return e; });
const docListeners = {};
const store = {};
let posted = null;
let puzzleReq = null;
// A graded pool puzzle the server hands out for the next game.
const POOL = '003020600900305001001806400008102900700000008006708200002609500800203009005010300';
const later = [];   // timers >= 1 s (the toast hide) run only when the test asks
const GIVENS = '530070000600195000098000060800060003400803001700020006060000280000419005000080079';
const ctx = vm.createContext({
  window: { SUDOKU_CFG: { difficulty: 'easy', seed: 1, givens: GIVENS, today: '2026-10-11' } },
  document: { getElementById: byId, createElement: () => new El(), hidden: false,
    querySelectorAll: s => s === '.su-numpad-btn' ? numpad : [],
    addEventListener: (t, f) => (docListeners[t] ||= []).push(f) },
  localStorage: { getItem: k => store[k] ?? null, setItem: (k, v) => { store[k] = v; } },
  setTimeout: (f, ms) => { if (ms >= 1000) later.push(f); else { try { f(); } catch (e) { console.log('TIMER ERROR', e.message); } } return 1; },
  clearTimeout() {}, setInterval: () => 1, clearInterval() {},
  history: { replaceState() {} }, location: { pathname: '/other/sudoku/easy', search: '' },
  URLSearchParams, Uint32Array,
  performance, crypto: globalThis.crypto, TextEncoder, console, Math, Array, Set, JSON, Object, Number, String, Promise,
  fetch: async (url, o) => {
    if (o && o.method === 'POST') { posted = JSON.parse(o.body); return { ok: true }; }
    if (url.startsWith('/api/sudoku-puzzle')) { puzzleReq = url; return { ok: true, json: async () => ({ givens: POOL }) }; }
    return { ok: true, json: async () => [] };   // leaderboard GET
  },
});
ctx.window.SUDOKU_CFG && (ctx.SUDOKU_CFG = ctx.window.SUDOKU_CFG);
vm.runInContext(SRC, ctx);
docListeners.DOMContentLoaded.forEach(f => f());

const cells = () => byId('su-board').children;
const notesOf = i => { const g = cells()[i].children[0]; return g ? g.children.map(s => s.textContent).filter(Boolean).map(Number) : []; };
const has = (i, c) => cells()[i].classList.contains(c);
const click = i => cells()[i].fire('click');
const press = n => n ? numpad[n - 1].fire('click') : byId('su-erase').fire('click');
const toggle = (id, on) => { byId(id).checked = on; byId(id).fire('change'); };
let fails = 0;
const ok = (cond, msg) => { console.log((cond ? 'PASS ' : 'FAIL ') + msg); if (!cond) fails++; };

// Reference candidates
const g = GIVENS.split('').map(Number);
const cand = (b, i) => { const r = Math.floor(i / 9), c = i % 9, out = [];
  for (let v = 1; v <= 9; v++) { let okv = true;
    for (let k = 0; k < 9; k++) { if (b[r * 9 + k] === v || b[k * 9 + c] === v) okv = false;
      const br = Math.floor(r / 3) * 3 + Math.floor(k / 3), bc = Math.floor(c / 3) * 3 + k % 3; if (b[br * 9 + bc] === v) okv = false; }
    if (okv) out.push(v); } return out; };

ok(cells().length === 81, '81 cells rendered');
ok(notesOf(2).length === 0, 'no notes with every option off');

// Auto candidates
toggle('su-opt-auto-candidates', true);
ok(JSON.stringify(notesOf(2)) === JSON.stringify(cand(g, 2)), `auto candidates for r1c3 = ${cand(g, 2)}`);
ok([...Array(81).keys()].every(i => g[i] || JSON.stringify(notesOf(i)) === JSON.stringify(cand(g, i))), 'auto candidates correct in every empty cell');
ok(JSON.parse(store.su_opts).autoCandidates === true, 'option remembered in localStorage');

// Notes mode with auto candidates: cross one out, restore it
byId('su-mode-notes').fire('click');
click(2); const first = cand(g, 2)[0];
press(first);
ok(!notesOf(2).includes(first), `notes mode crosses out auto candidate ${first}`);
press(first);
ok(notesOf(2).includes(first), 'tapping again restores it');
press(5 === first ? 6 : 5); // a digit that may not be a candidate: must not appear
ok(notesOf(2).every(v => cand(g, 2).includes(v)), 'cannot add a digit the board rules out');

// Manual notes with auto off; placing a digit clears it from peers
toggle('su-opt-auto-candidates', false);
ok(notesOf(2).length === 0, 'auto off: back to (empty) manual notes');
click(2); press(4); press(2);
ok(JSON.stringify(notesOf(2)) === '[2,4]', 'manual notes 2 and 4 in r1c3');
byId('su-mode-normal').fire('click');
click(3); press(4);                          // r1c4 = 4, same row as r1c3
ok(JSON.stringify(notesOf(2)) === '[2]', 'placing 4 in the row removes 4 from r1c3 notes');

// Conflicts: 5 is given at r1c1; put 5 at r1c3 (same row)
toggle('su-opt-conflicts', true);
click(2); press(5);
ok(has(2, 'su-cell--conflict') && has(0, 'su-cell--conflict'), 'conflict marks both the entry and the given');
toggle('su-opt-conflicts', false);
ok(!has(2, 'su-cell--conflict'), 'conflicts off: no marks');

// Auto check: 5 at r1c3 is wrong (solution has 4)
ok(!has(2, 'su-cell--error'), 'auto check off: wrong digit not marked');
toggle('su-opt-auto-check', true);
ok(has(2, 'su-cell--error'), 'auto check on: wrong digit marked');
press(0);
ok(!has(2, 'su-cell--error') && cells()[2].textContent === '', 'erase clears the value');

// Solve and check the submitted assists bitmask (auto candidates 1 + auto check 2)
const SOL = '534678912672195348198342567859761423426853791713924856961537284287419635345286179';
for (let i = 0; i < 81; i++) if (!g[i]) { click(i); press(+SOL[i]); }
Promise.resolve().then(() => new Promise(r => globalThis.setTimeout(r, 50))).then(() => {
  ok(posted && posted.assists === 3, `score saved automatically with assists = ${posted && posted.assists} (expected 3)`);
  ok(posted && posted.name.startsWith('Guest '), `guest gets an automatic name (${posted && posted.name})`);
  const toast = byId('su-toast');
  ok(toast.classList.contains('game-toast--show'), 'result toast shown');
  ok(/Sudoku solved/.test(toast.innerHTML) && /Auto candidates/.test(toast.innerHTML), 'toast shows the result and the assists');
  // The stub DOM doesn't parse innerHTML, so the status line is looked up by id.
  ok(/Score saved for Guest/.test(byId('su-toast-status').textContent), 'toast status updated after saving');
  // Timers under 1 s run immediately here, so the next game already started.
  ok(cells().filter(c => c.textContent === '').length >= 40, 'a new puzzle started automatically');
  ok(puzzleReq === '/api/sudoku-puzzle?difficulty=easy', `next puzzle requested from the server pool (${puzzleReq})`);
  ok(cells().map(c => c.textContent || '0').join('') === POOL, 'next game uses the graded pool puzzle');
  later.forEach(f => f());
  ok(!toast.classList.contains('game-toast--show'), 'toast hides after its timer');
  console.log(fails ? `${fails} FAILED` : 'ALL PASSED');
  process.exit(fails ? 1 : 0);
});
