// Plays random games through the nmmobile reducer (mobile/nmmobile/src/hooks/
// useGameState.js) and adds them to numbers_match_js_games.json as
// "mobile_games", so tests/test_numbers_match_engine.py checks mobile/server
// parity too. Bundles the reducer with esbuild (React stubbed out):
//
//   node tests/fixtures/gen_numbers_match_mobile_games.mjs
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
const tmp  = fs.mkdtempSync(path.join(os.tmpdir(), 'nm-mobile-'));
const stub = path.join(tmp, 'react-stub.js');
fs.writeFileSync(stub, 'export const useReducer = () => []; export const useCallback = f => f;');
const out = path.join(tmp, 'bundle.mjs');
const entry = path.join(tmp, 'entry.js');
fs.writeFileSync(entry,
    `export { reducer } from ${JSON.stringify(path.join(ROOT, 'mobile/nmmobile/src/hooks/useGameState.js'))};\n` +
    `export * from ${JSON.stringify(path.join(ROOT, 'mobile/nmmobile/src/gameEngine.js'))};\n`);
execFileSync(process.platform === 'win32' ? 'npx.cmd' : 'npx',
    ['-y', 'esbuild@0.24.0', entry, '--bundle', '--format=esm', `--alias:react=${stub}`, `--outfile=${out}`],
    { stdio: 'inherit', shell: process.platform === 'win32' });
const m = await import(pathToFileURL(out).href);

let s = 98765;
const rand = () => ((s = (s * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);

function play(puzzleId, rows) {
    const board = m.generateBoardClient(puzzleId, rows);
    // INIT builds a fresh state from INITIAL_STATE; the {} is only a placeholder.
    let st = m.reducer({}, { type: 'INIT', boardData: board, rows, puzzleId, isPOTD: true });
    let now = 1_000_000;
    const send = a => { now += 200; st = m.reducer(st, { ...a, now }); };
    for (let step = 0; step < 4000 && !st.won; step++) {
        const r = rand();
        if (r < 0.03) { send({ type: 'HINT' }); continue; }
        if (r < 0.05) { send({ type: 'UNDO' }); continue; }
        const pairs = [];
        for (let i = 0; i < st.board.length; i++) {
            if (!st.board[i]) continue;
            for (let j = i + 1; j < st.board.length; j++)
                if (st.board[j] && m.canMatch(st.board[i], st.board[j]) && m.areAdjacent(st.board, i, j)) pairs.push([i, j]);
        }
        if (!pairs.length) {
            if (st.addLinesLeft <= 0) break;
            send({ type: 'ADD_LINES' });
            continue;
        }
        const [i, j] = pairs[Math.floor(rand() * pairs.length)];
        send({ type: 'CELL_PRESS', idx: i });
        send({ type: 'CELL_PRESS', idx: j });
    }
    return { puzzle_id: puzzleId, rows, board, won: st.won, score: st.score,
             lines_added: st.linesAdded, moves: st.moves };
}

const games = [];
for (let d = 1; d <= 20 && games.length < 30; d++)
    for (const [diff, rows] of [['easy', 6], ['medium', 8], ['hard', 16]]) {
        const g = play(`2026-11-${String(d).padStart(2, '0')}-${diff}-v3`, rows);
        if (g.won) games.push(g);
    }

const file = path.join(HERE, 'numbers_match_js_games.json');
const data = JSON.parse(fs.readFileSync(file, 'utf8'));
data.mobile_games = games;
fs.writeFileSync(file, JSON.stringify(data));
fs.rmSync(tmp, { recursive: true, force: true });
console.log(`mobile games: ${games.length}, kinds: ${[...new Set(games.flatMap(g => g.moves.map(x => x[0])))].join(',')}`);
