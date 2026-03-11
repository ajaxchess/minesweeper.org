'use strict';

// ── Seeded RNG: mulberry32 ────────────────────────────────────────────────────
function mulberry32(seed) {
    return function () {
        seed |= 0; seed = seed + 0x6D2B79F5 | 0;
        let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
        t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
        return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
}

// FNV-1a hash to turn any string into a 32-bit seed
function strSeed(s) {
    let h = 0x811c9dc5;
    for (let i = 0; i < s.length; i++) {
        h ^= s.charCodeAt(i);
        h = Math.imul(h, 0x01000193) >>> 0;
    }
    return h;
}

// ── Constants ─────────────────────────────────────────────────────────────────
const ROWS  = 7;
const COLS  = 7;
const MINES = 10;

// Classic minesweeper number colours
const NUM_COLOR = [
    '', '#6ab0f5', '#57d474', '#e53935',
    '#3949ab', '#c62828', '#00838f', '#212121', '#757575',
];

// ── Game state ────────────────────────────────────────────────────────────────
// Each cell: { isMine: bool, count: 0-8, state: 'clue'|'unknown'|'flagged'|'empty' }
let G = {
    cells:          [],
    isPOTD:         true,
    puzzleId:       '',   // date string for POTD, random hex for randoms
    startTime:      null,
    elapsed:        0,
    timer:          null,
    won:            false,
    highlightErrors: false,
};

// ── Puzzle generation ─────────────────────────────────────────────────────────
function generatePuzzle(seedStr) {
    const rng = mulberry32(strSeed(seedStr));

    // Fisher-Yates shuffle of cell indices, pick first MINES as mine positions
    const idx = Array.from({ length: ROWS * COLS }, (_, i) => i);
    for (let i = idx.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [idx[i], idx[j]] = [idx[j], idx[i]];
    }
    const mines = new Set(idx.slice(0, MINES));

    const cells = [];
    for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS; c++) {
            const i = r * COLS + c;
            const isMine = mines.has(i);
            let count = 0;
            if (!isMine) {
                for (let dr = -1; dr <= 1; dr++) {
                    for (let dc = -1; dc <= 1; dc++) {
                        if (dr === 0 && dc === 0) continue;
                        const nr = r + dr, nc = c + dc;
                        if (nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS && mines.has(nr * COLS + nc)) {
                            count++;
                        }
                    }
                }
            }
            // Clue: non-mine cells adjacent to at least one mine (revealed as hints)
            const state = (!isMine && count > 0) ? 'clue' : 'unknown';
            cells.push({ isMine, count, state });
        }
    }
    return cells;
}

// ── Timer ─────────────────────────────────────────────────────────────────────
function startTimer() {
    if (G.timer) return;
    G.startTime = Date.now() - G.elapsed * 1000;
    G.timer = setInterval(() => {
        G.elapsed = Math.floor((Date.now() - G.startTime) / 1000);
        document.getElementById('tz-timer').textContent = fmtTime(G.elapsed);
    }, 500);
}

function stopTimer() {
    clearInterval(G.timer);
    G.timer = null;
    G.elapsed = Math.floor((Date.now() - G.startTime) / 1000);
}

function fmtTime(s) {
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

// ── Rendering ─────────────────────────────────────────────────────────────────
function renderBoard() {
    const board = document.getElementById('tz-board');
    board.innerHTML = '';

    G.cells.forEach((cell, idx) => {
        const el = document.createElement('div');
        el.className = 'cell';
        el.dataset.idx = idx;
        applyCell(el, cell);

        if (cell.state !== 'clue') {
            el.addEventListener('click', () => handleClick(idx));
            el.addEventListener('contextmenu', e => { e.preventDefault(); handleRightClick(idx); });
        }
        board.appendChild(el);
    });
}

function applyCell(el, cell) {
    // Reset classes and content
    el.className = 'cell';
    el.textContent = '';
    el.style.color = '';

    if (cell.state === 'clue') {
        el.classList.add('revealed');
        if (cell.count > 0) {
            el.textContent = cell.count;
            el.style.color = NUM_COLOR[cell.count] || '';
        }
    } else if (cell.state === 'unknown') {
        el.classList.add('hidden');
    } else if (cell.state === 'flagged') {
        el.classList.add('hidden', 'tz-flagged');
        el.textContent = '💣';
        if (G.highlightErrors && !cell.isMine) el.classList.add('tz-error');
    } else if (cell.state === 'empty') {
        el.classList.add('hidden', 'tz-empty');
        el.textContent = '✓';
        if (G.highlightErrors && cell.isMine) el.classList.add('tz-error');
    }
}

function refreshCell(idx) {
    const el = document.querySelector(`#tz-board [data-idx="${idx}"]`);
    if (el) applyCell(el, G.cells[idx]);
}

// ── Interaction ───────────────────────────────────────────────────────────────
function handleClick(idx) {
    if (G.won) return;
    const cell = G.cells[idx];
    if (cell.state === 'clue') return;

    // Start timer on first interaction
    if (!G.startTime) startTimer();

    // Cycle: unknown → flagged → empty → unknown
    if      (cell.state === 'unknown') cell.state = 'flagged';
    else if (cell.state === 'flagged') cell.state = 'empty';
    else                               cell.state = 'unknown';

    refreshCell(idx);
    updateFlagCount();
    checkWin();
}

function handleRightClick(idx) {
    if (G.won) return;
    const cell = G.cells[idx];
    if (cell.state === 'clue') return;

    if (!G.startTime) startTimer();

    // Toggle: unknown/empty → flagged, flagged → unknown
    cell.state = cell.state === 'flagged' ? 'unknown' : 'flagged';

    refreshCell(idx);
    updateFlagCount();
    checkWin();
}

// ── Flag counter ──────────────────────────────────────────────────────────────
function updateFlagCount() {
    const n = G.cells.filter(c => c.state === 'flagged').length;
    document.getElementById('tz-flag-count').textContent = n;
}

// ── Win detection ─────────────────────────────────────────────────────────────
function checkWin() {
    // Win: every mine is flagged AND no non-mine is flagged
    const won = G.cells.every(c =>
        (c.isMine  && c.state === 'flagged') ||
        (!c.isMine && c.state !== 'flagged')
    );
    if (!won) return;

    G.won = true;
    stopTimer();
    showWinOverlay();
}

// ── Win overlay ───────────────────────────────────────────────────────────────
function showWinOverlay() {
    const ov = document.getElementById('tz-overlay');
    ov.className = 'win';
    ov.style.display = 'flex';

    document.getElementById('tz-win-time').textContent = fmtTime(G.elapsed);

    const form = document.getElementById('tz-score-form');
    if (G.isPOTD) {
        form.style.display = 'flex';
        document.getElementById('tz-name-input').value = localStorage.getItem('tz_name') || '';
        const btn = document.getElementById('tz-save-btn');
        btn.disabled = false;
        btn.textContent = 'Save Score';
    } else {
        form.style.display = 'none';
    }
}

// ── Score submission ──────────────────────────────────────────────────────────
async function saveScore() {
    const inp = document.getElementById('tz-name-input');
    const btn = document.getElementById('tz-save-btn');
    const name = inp.value.trim();
    if (!name) { inp.focus(); return; }

    btn.disabled = true;
    btn.textContent = 'Saving…';

    try {
        const r = await fetch('/api/tentaizu-scores', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, puzzle_date: G.puzzleId, time_secs: G.elapsed }),
        });
        if (r.ok) {
            localStorage.setItem('tz_name', name);
            btn.textContent = '✓ Saved!';
            loadLeaderboard();
        } else {
            btn.textContent = 'Error — retry';
            btn.disabled = false;
        }
    } catch {
        btn.textContent = 'Error — retry';
        btn.disabled = false;
    }
}

// ── Leaderboard ───────────────────────────────────────────────────────────────
async function loadLeaderboard() {
    if (!G.isPOTD) return;
    const el = document.getElementById('tz-lb-content');
    el.innerHTML = '<div class="lb-loading">Loading…</div>';

    try {
        const r    = await fetch(`/api/tentaizu-scores/${G.puzzleId}`);
        const data = await r.json();

        if (!data.length) {
            el.innerHTML = '<div class="lb-empty">No scores yet — be the first!</div>';
            return;
        }

        const medals = ['🥇', '🥈', '🥉'];
        const rows = data.map((s, i) => `
            <tr class="${i < 3 ? 'top-' + (i + 1) : ''}">
                <td class="lb-rank">${medals[i] || i + 1}</td>
                <td class="lb-name">${esc(s.name)}</td>
                <td class="lb-time">${fmtTime(s.time_secs)}</td>
            </tr>`).join('');

        el.innerHTML = `
            <div class="lb-table-wrap">
              <table class="lb-table">
                <thead><tr><th>#</th><th>Name</th><th>Time</th></tr></thead>
                <tbody>${rows}</tbody>
              </table>
            </div>`;
    } catch {
        el.innerHTML = '<div class="lb-empty">⚠️ Could not load scores.</div>';
    }
}

function esc(s) {
    return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

// ── Highlight Errors Toggle ────────────────────────────────────────────────────
function toggleHighlightErrors() {
    G.highlightErrors = !G.highlightErrors;
    localStorage.setItem('tzHighlightErrors', G.highlightErrors);
    const btn = document.getElementById('highlight-errors-toggle');
    if (btn) btn.classList.toggle('active', G.highlightErrors);
    G.cells.forEach((_, idx) => refreshCell(idx));
}

// ── Game init ─────────────────────────────────────────────────────────────────
function initGame(seedStr, isPOTD) {
    clearInterval(G.timer);

    G = {
        cells:          generatePuzzle(seedStr),
        isPOTD,
        puzzleId:       seedStr,
        startTime:      null,
        elapsed:        0,
        timer:          null,
        won:            false,
        highlightErrors: localStorage.getItem('tzHighlightErrors') === 'true',
    };

    const ov = document.getElementById('tz-overlay');
    ov.style.display = 'none';
    ov.className     = '';

    document.getElementById('tz-timer').textContent     = '0:00';
    document.getElementById('tz-mode-label').textContent =
        isPOTD ? '📅 Puzzle of the Day' : '🎲 Random Puzzle';

    const lb = document.getElementById('tz-lb-section');
    lb.style.display = isPOTD ? 'block' : 'none';

    updateFlagCount();
    renderBoard();

    const btn = document.getElementById('highlight-errors-toggle');
    if (btn) btn.classList.toggle('active', G.highlightErrors);

    if (isPOTD) loadLeaderboard();
}

// ── Entry point ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const today = document.getElementById('tz-board').dataset.today;

    // Start with today's Puzzle of the Day
    initGame(today, true);

    // Mode buttons
    document.getElementById('tz-potd-btn').addEventListener('click', () =>
        initGame(document.getElementById('tz-board').dataset.today, true));

    document.getElementById('tz-random-btn').addEventListener('click', () =>
        initGame(Date.now().toString(36) + Math.random().toString(36).slice(2, 6), false));

    // Overlay buttons
    document.getElementById('tz-overlay-potd').addEventListener('click', () =>
        initGame(document.getElementById('tz-board').dataset.today, true));

    document.getElementById('tz-overlay-random').addEventListener('click', () =>
        initGame(Date.now().toString(36) + Math.random().toString(36).slice(2, 6), false));

    // Score form
    document.getElementById('tz-save-btn').addEventListener('click', saveScore);
    document.getElementById('tz-name-input').addEventListener('keydown', e => {
        if (e.key === 'Enter') saveScore();
    });
});
