// Behaviour test for the Numbers Match game end (F-GAME-END): runs the real
// static/src/js/numbers_match.js against a stub DOM and checks the 5 s result
// toast, automatic score saving and the next game: Daily -> today's ranked Easy,
// a finished ranked board -> random practice board of the same size.
// CI is Python-only; run it by hand after changes:
//
//   node tests/js/numbers_match_game_end.js
'use strict';
const fs = require('fs'), vm = require('vm'), path = require('path');
const ROOT = path.resolve(__dirname, '..', '..');
const SRC = fs.readFileSync(path.join(ROOT, 'static/src/js/numbers_match.js'), 'utf8');

const els = {};
function stubEl(id) {
  const cls = new Set();
  return { id, style: {}, dataset: {}, textContent: '', _html: '', disabled: false,
    set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html; },
    set className(v) { v.split(/\s+/).filter(Boolean).forEach(c => cls.add(c)); },
    classList: { add: c => cls.add(c), remove: c => cls.delete(c), toggle: (c, f) => (f ?? !cls.has(c)) ? cls.add(c) : cls.delete(c), contains: c => cls.has(c) },
    appendChild() {}, addEventListener() {}, setAttribute() {}, focus() {}, scrollIntoView() {} };
}
const byId = id => (els[id] ||= stubEl(id));
const store = {};
const posts = [];
const later = [];
const lbGets = [];   // leaderboard requests, newest last
const ctx = vm.createContext({
  document: { getElementById: byId, createElement: () => stubEl(), querySelector: sel => sel === '.nm-lb-title' ? byId('lb-title') : null,
              querySelectorAll: () => [], addEventListener() {}, body: { appendChild() {} } },
  window: {}, console, Date, Math, JSON, Intl, Promise,
  localStorage: { getItem: k => store[k] ?? null, setItem: (k, v) => { store[k] = v; } },
  setTimeout: (f, ms) => { if (ms >= 1000) later.push(f); else Promise.resolve().then(f); return 1; },
  clearTimeout() {}, setInterval: () => 0, clearInterval() {},
  fetch: async (url, o) => {
    if (url.startsWith('/api/numbers-match-today')) return { ok: true, json: async () => ({ today: '2026-10-12', revision: 'v2' }) };
    if (url.startsWith('/api/numbers-match-start')) return { ok: true, json: async () => ({ token: 'tok' }) };
    if (o && o.method === 'POST') { posts.push(JSON.parse(o.body)); return { ok: true, json: async () => ({}) }; }
    if (url.startsWith('/api/numbers-match-board')) return { ok: true, json: async () => ({ board_data: [1,9,1,9,1,9,1,9,1, 9,1,9,1,9,1,9,1,9], rows: 2 }) };
    if (url.startsWith('/api/numbers-match-scores/')) lbGets.push(url.split('?')[0].split('/').pop());
    return { ok: true, json: async () => [] };
  },
});
vm.runInContext(SRC + '\n;globalThis.__nm = { get G() { return G; }, _startGame, handleCellClick, canMatch, areAdjacent, generateBoardClient, initRandomGame };', ctx);
const nm = ctx.__nm;
let fails = 0;
const ok = (c, m) => { console.log((c ? 'PASS ' : 'FAIL ') + m); if (!c) fails++; };
const tick = () => new Promise(r => setTimeout(r, 30));

function winCurrent() {
  // Test the game-end flow, not a solver: give the current game a trivially clearable board.
  nm.G.board = [1,9,1,9,1,9,1,9,1, 9,1,9,1,9,1,9,1,9]; nm.G.rows = 2;
  for (let n = 0; n < 5000 && !nm.G.won; n++) {
    const b = nm.G.board; let done = false;
    for (let i = 0; i < b.length && !done; i++) for (let j = i + 1; j < b.length && !done; j++)
      if (b[i] && b[j] && nm.canMatch(b[i], b[j]) && nm.areAdjacent(i, j)) { nm.handleCellClick(i); nm.handleCellClick(j); done = true; }
    if (!done) return false;
  }
  return nm.G.won;
}

(async () => {
  // A trivially clearable "daily" board.
  nm._startGame([1,9,1,9,1,9,1,9,1, 9,1,9,1,9,1,9,1,9], 2, '2026-10-12-v2', true);
  await tick();
  ok(nm.G.gameToken === 'tok', 'daily game got a token');
  ok(winCurrent(), 'daily board cleared');
  ok(byId('nm-toast').classList.contains('game-toast--show'), 'toast shown on win');
  ok(/Board cleared/.test(byId('nm-toast').innerHTML), 'toast has the result');
  await tick(); await tick();
  ok(posts.length === 1 && posts[0].puzzle_date === '2026-10-12-v2', 'daily score saved');
  ok(/Score saved/.test(byId('nm-toast-status').textContent), 'toast status says saved');
  ok(nm.G.puzzleId === '2026-10-12-easy-v2' && nm.G.isPOTD && nm.G.diffRows === 6,
     `after Daily → today's ranked Easy, 6 rows (${nm.G.puzzleId}, ${nm.G.diffRows} rows)`);
  // B57: the Daily's ranking stays on screen while the Easy is played.
  ok(lbGets[lbGets.length - 1] === '2026-10-12-v2', `leaderboard still shows the Daily (${lbGets[lbGets.length - 1]})`);
  ok(/Today's Leaderboard/.test(byId('lb-title').textContent), `leaderboard title is the Daily's (${byId('lb-title').textContent})`);

  // Win the ranked Easy → it's marked played, next is a practice Easy.
  ok(winCurrent(), 'easy board cleared');
  await tick(); await tick();
  ok(posts.length === 2 && posts[1].puzzle_date === '2026-10-12-easy-v2', 'easy score saved');
  ok(lbGets[lbGets.length - 1] === '2026-10-12-easy-v2' && /Easy/.test(byId('lb-title').textContent),
     'after winning Easy the leaderboard shows the Easy ranking');
  ok(!nm.G.isPOTD && nm.G.diffRows === 6, `after ranked Easy → practice Easy (${nm.G.puzzleId})`);
  ok(/Practice/.test(byId('nm-mode-label').textContent), 'label says Practice');

  // Practice win: no save, next is another practice board of the same size.
  const prevId = nm.G.puzzleId;
  ok(winCurrent(), 'practice board cleared');
  ok(/not ranked/.test(byId('nm-toast').innerHTML), 'toast says practice is not ranked');
  await tick(); await tick();
  ok(posts.length === 2, 'practice score not saved');
  ok(!nm.G.isPOTD && nm.G.puzzleId !== prevId && nm.G.diffRows === 6, 'next practice board started');
  ok(lbGets[lbGets.length - 1] === '2026-10-12-easy-v2', 'practice keeps the last ranked leaderboard');

  // F-NM-CLEARED: last 5s removed → toast; winning right after replaces it.
  nm.G.board = [5,5,1,0,0,0,0,0,9, 2,8,0,0,0,0,0,0,0]; nm.G.rows = 2;
  nm.handleCellClick(0); nm.handleCellClick(1);
  ok(byId('nm-clear-toast').classList.contains('game-toast--show'), 'toast when a number is gone');
  ok(/No more 5 left/.test(byId('nm-clear-toast').innerHTML), 'toast names the number');
  ok(/nm-cleared-digit--done" title="5"/.test(byId('nm-cleared').innerHTML), 'bar marks 5 as cleared');
  nm.handleCellClick(2); nm.handleCellClick(8);
  ok(/nm-cleared-digit--done" title="1"/.test(byId('nm-cleared').innerHTML), 'bar updates as numbers clear');
  // The emptied first row collapsed, so the last pair is now at 0 and 1.
  nm.handleCellClick(0); nm.handleCellClick(1);
  ok(nm.G.won, 'board cleared');
  ok(!byId('nm-clear-toast').classList.contains('game-toast--show'), 'win toast replaces the cleared toast');
  ok(byId('nm-toast').classList.contains('game-toast--show'), 'win toast shown');
  await tick(); await tick();

  later.forEach(f => f());
  ok(!byId('nm-toast').classList.contains('game-toast--show'), 'toast hides after 5 s timer');
  console.log(fails ? `${fails} FAILED` : 'ALL PASSED');
  process.exit(fails ? 1 : 0);
})();
