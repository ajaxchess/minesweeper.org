'use strict';

// ── Seeded RNG ────────────────────────────────────────────────────────────────
function mulberry32(seed) {
    return function () {
        seed |= 0; seed = seed + 0x6D2B79F5 | 0;
        let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
        t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
        return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
}

function strSeed(s) {
    let h = 0x811c9dc5;
    for (let i = 0; i < s.length; i++) {
        h ^= s.charCodeAt(i);
        h = Math.imul(h, 0x01000193) >>> 0;
    }
    return h;
}

// ── Constants ─────────────────────────────────────────────────────────────────
const ROWS = 10;
const COLS = 10;

// ── Game state ────────────────────────────────────────────────────────────────
let G = {
    hints:     [],   // ROWS×COLS flat array of hint numbers (count of black in 3×3 neighborhood)
    solution:  [],   // ROWS×COLS flat array of 0/1 (correct answer)
    player:    [],   // ROWS×COLS flat array of 0/1 (player's marks)
    isPOTD:    true,
    seedStr:   '',
    startTime: null,
    elapsed:   0,
    timer:     null,
    won:       false,
};

// ── Puzzle generation ─────────────────────────────────────────────────────────
function generatePuzzle(seedStr) {
    const rng = mulberry32(strSeed('mosaic:' + seedStr));

    // Random black/white solution (~40% black)
    const solution = Array.from({ length: ROWS * COLS }, () => rng() < 0.40 ? 1 : 0);

    // Compute neighborhood count for every cell
    const hints = [];
    for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS; c++) {
            let count = 0;
            for (let dr = -1; dr <= 1; dr++) {
                for (let dc = -1; dc <= 1; dc++) {
                    const nr = r + dr, nc = c + dc;
                    if (nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS) {
                        count += solution[nr * COLS + nc];
                    }
                }
            }
            hints.push(count);
        }
    }

    return { solution, hints };
}

// ── Neighborhood count based on player marks ──────────────────────────────────
function neighborCount(r, c) {
    let count = 0;
    for (let dr = -1; dr <= 1; dr++) {
        for (let dc = -1; dc <= 1; dc++) {
            const nr = r + dr, nc = c + dc;
            if (nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS) {
                count += G.player[nr * COLS + nc];
            }
        }
    }
    return count;
}

// ── Win check ─────────────────────────────────────────────────────────────────
function checkWin() {
    for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS; c++) {
            if (neighborCount(r, c) !== G.hints[r * COLS + c]) return false;
        }
    }
    return true;
}

// ── Timer ─────────────────────────────────────────────────────────────────────
function startTimer() {
    if (G.timer) return;
    G.startTime = Date.now() - G.elapsed * 1000;
    G.timer = setInterval(() => {
        G.elapsed = Math.floor((Date.now() - G.startTime) / 1000);
        const el = document.getElementById('ms-timer');
        if (el) el.textContent = fmtTime(G.elapsed);
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

// ── Render ────────────────────────────────────────────────────────────────────
function renderCell(r, c) {
    const idx = r * COLS + c;
    const el = document.querySelector(`.ms-cell[data-idx="${idx}"]`);
    if (!el) return;

    const isBlack = G.player[idx] === 1;
    el.classList.toggle('ms-black', isBlack);

    const hint = G.hints[idx];
    const current = neighborCount(r, c);
    const span = el.querySelector('.ms-hint');
    span.classList.remove('ms-hint-ok', 'ms-hint-over', 'ms-hint-under');
    if (current === hint)      span.classList.add('ms-hint-ok');
    else if (current > hint)   span.classList.add('ms-hint-over');
}

function renderBoard() {
    const board = document.getElementById('ms-board');
    board.innerHTML = '';
    board.style.gridTemplateColumns = `repeat(${COLS}, 42px)`;

    for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS; c++) {
            const idx = r * COLS + c;
            const cell = document.createElement('div');
            cell.className = 'ms-cell';
            cell.dataset.idx = idx;
            if (G.player[idx] === 1) cell.classList.add('ms-black');

            const span = document.createElement('span');
            span.className = 'ms-hint';
            span.textContent = G.hints[idx];
            const current = neighborCount(r, c);
            if (current === G.hints[idx])    span.classList.add('ms-hint-ok');
            else if (current > G.hints[idx]) span.classList.add('ms-hint-over');
            cell.appendChild(span);

            cell.addEventListener('click', () => handleClick(r, c));
            cell.addEventListener('contextmenu', e => { e.preventDefault(); handleClick(r, c); });
            board.appendChild(cell);
        }
    }
}

// Refresh a cell and all cells whose neighborhood includes it
function refreshAffected(r, c) {
    for (let dr = -1; dr <= 1; dr++) {
        for (let dc = -1; dc <= 1; dc++) {
            const nr = r + dr, nc = c + dc;
            if (nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS) {
                renderCell(nr, nc);
            }
        }
    }
}

// ── Click handler ─────────────────────────────────────────────────────────────
function handleClick(r, c) {
    if (G.won) return;
    if (!G.startTime) startTimer();

    const idx = r * COLS + c;
    G.player[idx] = G.player[idx] === 1 ? 0 : 1;
    refreshAffected(r, c);

    if (checkWin()) {
        stopTimer();
        G.won = true;
        document.getElementById('ms-win-time').textContent = fmtTime(G.elapsed);
        document.getElementById('ms-overlay').style.display = 'flex';
    }
}

// ── Init ──────────────────────────────────────────────────────────────────────
function initGame(seedStr, isPOTD) {
    if (G.timer) { clearInterval(G.timer); G.timer = null; }
    G.won       = false;
    G.isPOTD    = isPOTD;
    G.seedStr   = seedStr;
    G.elapsed   = 0;
    G.startTime = null;

    const { solution, hints } = generatePuzzle(seedStr);
    G.solution = solution;
    G.hints    = hints;
    G.player   = new Array(ROWS * COLS).fill(0);

    document.getElementById('ms-overlay').style.display = 'none';
    document.getElementById('ms-timer').textContent = '0:00';

    // Mode label
    const label = document.getElementById('ms-mode-label');
    if (label) label.textContent = isPOTD ? '📅 Puzzle of the Day' : '🎲 Random Puzzle';

    renderBoard();
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const board = document.getElementById('ms-board');
    const today = board.dataset.today;

    initGame(today, true);

    document.getElementById('ms-potd-btn').addEventListener('click', () => {
        initGame(today, true);
    });
    document.getElementById('ms-random-btn').addEventListener('click', () => {
        initGame(Math.random().toString(36).slice(2, 10), false);
    });
    document.getElementById('ms-overlay-potd').addEventListener('click', () => {
        initGame(today, true);
        document.getElementById('ms-overlay').style.display = 'none';
    });
    document.getElementById('ms-overlay-random').addEventListener('click', () => {
        initGame(Math.random().toString(36).slice(2, 10), false);
        document.getElementById('ms-overlay').style.display = 'none';
    });
});
