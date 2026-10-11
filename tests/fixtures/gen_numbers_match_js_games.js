// Generates tests/fixtures/numbers_match_js_games.json by running the REAL web
// client (static/src/js/numbers_match.js) in Node with a stub DOM and playing
// random games through its own click/hint/undo/add-lines handlers.
//
// tests/test_numbers_match_engine.py replays every recorded game with the
// server engine and asserts the same score, so web and server rules can't drift.
// Re-run after changing game rules in either place:
//
//   node tests/fixtures/gen_numbers_match_js_games.js
'use strict';
const fs   = require('fs');
const path = require('path');
const vm   = require('vm');

const ROOT = path.resolve(__dirname, '..', '..');
const SRC  = fs.readFileSync(path.join(ROOT, 'static/src/js/numbers_match.js'), 'utf8');

function stubEl() {
    return {
        style: {}, dataset: {}, textContent: '', innerHTML: '', disabled: false,
        classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
        appendChild() {}, addEventListener() {}, focus() {}, scrollIntoView() {},
    };
}
const document = {
    getElementById: () => stubEl(),
    createElement:  () => stubEl(),
    querySelector:  () => null,
    querySelectorAll: () => [],
    addEventListener() {},
};
const ctx = vm.createContext({
    document, window: {}, console, Date, Math, JSON, Intl,
    localStorage: { getItem: () => null, setItem() {} },
    setTimeout: () => 0, clearTimeout() {}, setInterval: () => 0, clearInterval() {},
});
// Expose the script's lexical bindings (G, handlers) to this harness.
vm.runInContext(SRC + '\n;globalThis.__nm = { get G() { return G; }, _startGame, handleCellClick, doHint, doUndo, doAddLines, canMatch, areAdjacent, generateBoardClient };', ctx);
const nm = ctx.__nm;

// Deterministic PRNG for the harness's own choices.
let s = 12345;
const rand = () => ((s = (s * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);

function legalPairs() {
    const b = nm.G.board, out = [];
    for (let i = 0; i < b.length; i++) {
        if (!b[i]) continue;
        for (let j = i + 1; j < b.length; j++)
            if (b[j] && nm.canMatch(b[i], b[j]) && nm.areAdjacent(i, j)) out.push([i, j]);
    }
    return out;
}

function play(puzzleId, rows) {
    const board = nm.generateBoardClient(puzzleId, rows);
    nm._startGame(board, rows, puzzleId, false);
    for (let step = 0; step < 4000 && !nm.G.won; step++) {
        const r = rand();
        if (r < 0.03) { nm.doHint(); continue; }
        if (r < 0.05) { nm.doUndo(); continue; }
        const pairs = legalPairs();
        if (!pairs.length) {
            if (nm.G.addLinesLeft <= 0) break;
            nm.doAddLines();
            continue;
        }
        const [i, j] = pairs[Math.floor(rand() * pairs.length)];
        nm.handleCellClick(i);
        nm.handleCellClick(j);
    }
    return { puzzle_id: puzzleId, rows, board, won: nm.G.won, score: nm.G.score,
             lines_added: nm.G.linesAdded, moves: nm.G.moves };
}

const games = [];
const DIFFS = [['easy', 4], ['medium', 8], ['hard', 16], ['expert', 32]];
for (let d = 1; d <= 28 && games.filter(g => g.won).length < 60; d++) {
    for (const [diff, rows] of DIFFS) {
        const g = play(`2026-10-${String(d).padStart(2, '0')}-${diff}-v2`, rows);
        if (g.won || games.filter(x => !x.won).length < 10) games.push(g);
    }
}
const vectors = ['2026-10-11-easy-v2', '2026-10-11-expert-v2', 'abc', ''].map(seed => (
    { seed, rows: 4, board: nm.generateBoardClient(seed, 4) }
));
const file = path.join(__dirname, 'numbers_match_js_games.json');
const previous = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : {};
fs.writeFileSync(file, JSON.stringify({
    generated_by: 'tests/fixtures/gen_numbers_match_js_games.js + gen_numbers_match_mobile_games.mjs',
    vectors, games,
    mobile_games: previous.mobile_games || [],   // kept; regenerate with the .mjs script
}));
console.log(`games: ${games.length} (won ${games.filter(g => g.won).length}), ` +
            `with hints ${games.filter(g => g.moves.some(m => m[0] === 'h')).length}, ` +
            `undos ${games.filter(g => g.moves.some(m => m[0] === 'u')).length}, ` +
            `add lines ${games.filter(g => g.moves.some(m => m[0] === 'a')).length}`);
