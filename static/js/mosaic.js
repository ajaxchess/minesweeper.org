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

function esc(s) {
    return String(s).replace(/[&<>"]/g, c =>
        ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

// ── Game state ────────────────────────────────────────────────────────────────
let G = {
    rows:         10,
    cols:         10,
    hints:        [],
    solution:     [],
    player:       [],
    totalMines:   0,
    isPOTD:       true,
    isHashBoard:  false,   // true when a custom hash+mask board has a score API
    boardHash:    '',
    boardMask:    '',
    seedStr:      '',
    scoreApi:     '/api/mosaic-scores',   // overridden for easy mode
    startTime:    null,
    elapsed:      0,
    timer:        null,
    won:          false,
    density:      null,    // null → use generatePuzzle default; number → override
    maskedCells:  new Set(), // indices whose hint is hidden (from mask hash)
};

// ── Puzzle generation ─────────────────────────────────────────────────────────
function generatePuzzle(seedStr, rows, cols) {
    const rng = mulberry32(strSeed(`mosaic:${rows}x${cols}:${seedStr}`));
    // 5×5 easy targets ~8 black cells (32%); standard 9×9 uses 35%; custom overrides
    const density = G.density !== null ? G.density
                  : ((rows <= 5 && cols <= 5) ? 0.32 : 0.35);
    const solution = Array.from({ length: rows * cols }, () => rng() < density ? 1 : 0);

    const hints = [];
    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            let count = 0;
            for (let dr = -1; dr <= 1; dr++) {
                for (let dc = -1; dc <= 1; dc++) {
                    const nr = r + dr, nc = c + dc;
                    if (nr >= 0 && nr < rows && nc >= 0 && nc < cols)
                        count += solution[nr * cols + nc];
                }
            }
            hints.push(count);
        }
    }

    const totalMines = solution.reduce((a, b) => a + b, 0);
    return { solution, hints, totalMines };
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function neighborCount(r, c) {
    let count = 0;
    for (let dr = -1; dr <= 1; dr++) {
        for (let dc = -1; dc <= 1; dc++) {
            const nr = r + dr, nc = c + dc;
            if (nr >= 0 && nr < G.rows && nc >= 0 && nc < G.cols)
                if (G.player[nr * G.cols + nc] === 1) count++;
        }
    }
    return count;
}

function checkWin() {
    for (let r = 0; r < G.rows; r++)
        for (let c = 0; c < G.cols; c++)
            if (neighborCount(r, c) !== G.hints[r * G.cols + c]) return false;
    return true;
}

function updateMineCount() {
    const el = document.getElementById('ms-mine-count');
    if (!el) return;
    const filled = G.player.reduce((a, b) => a + (b === 1 ? 1 : 0), 0);
    el.textContent = `${filled}/${G.totalMines}`;
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
    const idx = r * G.cols + c;
    const el  = document.querySelector(`.ms-cell[data-idx="${idx}"]`);
    if (!el) return;

    el.classList.toggle('ms-black', G.player[idx] === 1);
    el.classList.toggle('ms-white', G.player[idx] === 0);

    const span     = el.querySelector('.ms-hint');
    const hint     = G.hints[idx];
    const isMasked = G.maskedCells.has(idx);
    const current  = neighborCount(r, c);
    span.textContent = isMasked ? '' : hint;
    span.classList.remove('ms-hint-ok', 'ms-hint-over');
    if (!isMasked) {
        if (current === hint)    span.classList.add('ms-hint-ok');
        else if (current > hint) span.classList.add('ms-hint-over');
    }
}

function renderBoard() {
    const board    = document.getElementById('ms-board');
    const cellSize = parseInt(board.dataset.cellSize) || 42;
    board.innerHTML = '';
    board.style.gridTemplateColumns = `repeat(${G.cols}, ${cellSize}px)`;

    for (let r = 0; r < G.rows; r++) {
        for (let c = 0; c < G.cols; c++) {
            const idx  = r * G.cols + c;
            const cell = document.createElement('div');
            cell.className  = 'ms-cell';
            cell.dataset.idx = idx;
            cell.style.width  = `${cellSize}px`;
            cell.style.height = `${cellSize}px`;
            if (G.player[idx] === 1)      cell.classList.add('ms-black');
            else if (G.player[idx] === 0) cell.classList.add('ms-white');

            const span = document.createElement('span');
            span.className   = 'ms-hint';
            const isMasked   = G.maskedCells.has(idx);
            span.textContent = isMasked ? '' : G.hints[idx];
            const current = neighborCount(r, c);
            if (!isMasked) {
                if (current === G.hints[idx])    span.classList.add('ms-hint-ok');
                else if (current > G.hints[idx]) span.classList.add('ms-hint-over');
            }
            cell.appendChild(span);

            cell.addEventListener('mousedown', e => {
                if (e.button !== 0 && e.button !== 2) return;
                e.preventDefault();   // prevent text selection while dragging
                if (G.won) return;
                if (!G.startTime) startTimer();
                const dir = e.button === 2 ? 1 : 0;
                dragTarget = dir === 0 ? LEFT_NEXT[G.player[idx]] : RIGHT_NEXT[G.player[idx]];
                dragActive = true;
                paintCell(r, c);
            });
            cell.addEventListener('mouseenter', () => { if (dragActive) paintCell(r, c); });
            cell.addEventListener('contextmenu', e => e.preventDefault());
            board.appendChild(cell);
        }
    }
}

function refreshAffected(r, c) {
    for (let dr = -1; dr <= 1; dr++)
        for (let dc = -1; dc <= 1; dc++) {
            const nr = r + dr, nc = c + dc;
            if (nr >= 0 && nr < G.rows && nc >= 0 && nc < G.cols) renderCell(nr, nc);
        }
}

// ── Click / drag painting ─────────────────────────────────────────────────────
// States: 0=white/safe  1=black/mine  2=unknown (initial)
// Left  click (dir=0) cycles: white→black→unknown→white  (0→1→2→0)
// Right click (dir=1) cycles: black→white→unknown→black  (1→0→2→1)
const LEFT_NEXT  = [1, 2, 0];   // next state indexed by current state, left click
const RIGHT_NEXT = [2, 0, 1];   // next state indexed by current state, right click

// Drag state: set on mousedown, cleared on mouseup.
// dragTarget is the state every cell is painted to for the duration of the drag.
let dragActive = false;
let dragTarget = null;

function paintCell(r, c) {
    if (G.won) return;
    const idx = r * G.cols + c;
    if (G.player[idx] === dragTarget) return;   // already the right state — no-op
    G.player[idx] = dragTarget;
    refreshAffected(r, c);
    updateMineCount();
    if (checkWin()) {
        stopTimer();
        G.won = true;
        onWin();
    }
}

// ── Hide Numbers toggle ───────────────────────────────────────────────────────
function toggleHideNumbers() {
    const board  = document.getElementById('ms-board');
    const hidden = board.classList.toggle('ms-hints-hidden');
    const btn    = document.getElementById('ms-hide-numbers-btn');
    if (btn) btn.textContent = hidden ? '🔢 Show Numbers' : '🔢 Hide Numbers';
}

// ── Win ───────────────────────────────────────────────────────────────────────
function onWin() {
    // Reveal the full solution: flip all non-mine cells to white
    for (let i = 0; i < G.player.length; i++) {
        if (G.solution[i] !== 1) G.player[i] = 0;
    }
    for (let r = 0; r < G.rows; r++)
        for (let c = 0; c < G.cols; c++) renderCell(r, c);

    document.getElementById('ms-win-time').textContent = fmtTime(G.elapsed);
    document.getElementById('ms-overlay').style.display = 'flex';

    const board    = document.getElementById('ms-board');
    const username = board.dataset.username || '';
    const form     = document.getElementById('ms-score-form');

    if (G.isPOTD || G.isHashBoard) {
        if (username) {
            if (form) form.style.display = 'none';
            const msg = document.getElementById('ms-score-msg');
            if (msg) msg.textContent = 'Saving score…';
            saveScore(username);
        } else {
            if (form) {
                form.style.display = 'flex';
                const inp = document.getElementById('ms-name-input');
                if (inp) inp.value = localStorage.getItem('ms_name') || '';
            }
        }
    } else {
        if (form) form.style.display = 'none';
    }

    updatePermalink();
}

// ── Score submission ───────────────────────────────────────────────────────────
async function saveScore(autoName = null) {
    const inp  = document.getElementById('ms-name-input');
    const btn  = document.getElementById('ms-save-btn');
    const msg  = document.getElementById('ms-score-msg');
    const name = autoName || inp?.value.trim();
    if (!name) { inp?.focus(); return; }

    if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }

    try {
        const body = G.isHashBoard
            ? { board_hash: G.boardHash, board_mask: G.boardMask, rows: G.rows, cols: G.cols,
                name, time_secs: Math.max(1, G.elapsed) }
            : { name, puzzle_date: G.seedStr, time_secs: Math.max(1, G.elapsed) };
        const r = await fetch(G.scoreApi, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body:    JSON.stringify(body),
        });
        if (r.ok) {
            const data = await r.json();
            if (data.board_id) G._boardId = data.board_id;
            localStorage.setItem('ms_name', name);
            if (btn) btn.textContent = '✓ Saved!';
            if (msg) msg.textContent = `✅ Score saved for ${esc(name)}!`;
            loadLeaderboard();
        } else {
            if (btn) { btn.textContent = 'Error — retry'; btn.disabled = false; }
            if (msg) msg.textContent = '❌ Could not save score.';
        }
    } catch {
        if (btn) { btn.textContent = 'Error — retry'; btn.disabled = false; }
        if (msg) msg.textContent = '❌ Network error.';
    }
}

// ── Permalink / hash ──────────────────────────────────────────────────────────
function updatePermalink() {
    const row  = document.getElementById('ms-permalink-row');
    const link = document.getElementById('ms-permalink-link');
    if (!row || !link) return;

    const url = `/mosaic/replay?seed=${encodeURIComponent(G.seedStr)}&rows=${G.rows}&cols=${G.cols}`;
    link.href        = url;
    link.textContent = G.seedStr;
    row.style.display = 'block';
}

// ── Leaderboard ───────────────────────────────────────────────────────────────
async function loadLeaderboard() {
    if (!G.isPOTD && !G.isHashBoard) return;
    const el = document.getElementById('ms-lb-content');
    if (!el) return;
    el.innerHTML = '<div class="lb-loading">Loading…</div>';

    const title = document.getElementById('ms-lb-title');
    if (title) title.textContent = G.isPOTD ? `🏆 Best Times — ${G.seedStr}` : '🏆 Best Times — This Board';

    const lbUrl = G.isHashBoard
        ? `${G.scoreApi}/${G._boardId}`
        : `${G.scoreApi}/${G.seedStr}`;

    try {
        const r    = await fetch(lbUrl);
        const data = await r.json();

        if (!data.length) {
            el.innerHTML = '<div class="lb-empty">No scores yet — be the first!</div>';
            return;
        }

        const medals = ['🥇', '🥈', '🥉'];
        const rows = data.map((s, i) => `
            <tr class="${i < 3 ? 'top-' + (i + 1) : ''}">
                <td class="lb-rank">${medals[i] || i + 1}</td>
                <td class="lb-name">${s.profile_url
                    ? `<a href="${esc(s.profile_url)}" class="lb-profile-link">${esc(s.name)}</a>`
                    : esc(s.name)}</td>
                <td class="lb-time">${fmtTime(s.time_secs)}</td>
                ${G.isPOTD ? `<td class="lb-replay"><a href="/mosaic/replay?seed=${esc(s.puzzle_date)}&rows=${G.rows}&cols=${G.cols}" class="ms-replay-link" title="Replay this puzzle">🔗</a></td>` : ''}
            </tr>`).join('');

        el.innerHTML = `
            <div class="lb-table-wrap">
              <table class="lb-table">
                <thead><tr><th>#</th><th>Name</th><th>Time</th>${G.isPOTD ? '<th></th>' : ''}</tr></thead>
                <tbody>${rows}</tbody>
              </table>
            </div>`;
    } catch {
        el.innerHTML = '<div class="lb-empty">⚠️ Could not load scores.</div>';
    }
}

// ── Board ID (SHA-256 of "RxC:hash:mask") ─────────────────────────────────────
async function computeBoardId(rows, cols, boardHash, boardMask) {
    const raw = `${rows}x${cols}:${boardHash}:${boardMask}`;
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(raw));
    return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
}

// ── Hash-based init (custom board) ────────────────────────────────────────────
function initGameFromHash(hash, rows, cols, maskHash) {
    if (G.timer) { clearInterval(G.timer); G.timer = null; }

    const solution = new Array(rows * cols).fill(0);
    try {
        const bin = atob(hash);
        for (let i = 0; i < rows * cols; i++) {
            if (bin.charCodeAt(i >> 3) & (1 << (i & 7))) solution[i] = 1;
        }
    } catch { /* invalid hash — all white */ }

    const hints = [];
    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            let count = 0;
            for (let dr = -1; dr <= 1; dr++) {
                for (let dc = -1; dc <= 1; dc++) {
                    const nr = r + dr, nc = c + dc;
                    if (nr >= 0 && nr < rows && nc >= 0 && nc < cols)
                        count += solution[nr * cols + nc];
                }
            }
            hints.push(count);
        }
    }

    // Decode mask: cells with bit set will have their hint hidden
    const maskedCells = new Set();
    if (maskHash) {
        try {
            const maskBin = atob(maskHash);
            for (let i = 0; i < rows * cols; i++) {
                if (maskBin.charCodeAt(i >> 3) & (1 << (i & 7))) maskedCells.add(i);
            }
        } catch { /* invalid mask — show all hints */ }
    }

    const board   = document.getElementById('ms-board');
    G.rows        = rows;
    G.cols        = cols;
    G.won         = false;
    G.isPOTD      = false;
    G.boardHash   = hash;
    G.boardMask   = maskHash || '';
    G.isHashBoard = !!(board && board.dataset.scoreApi);
    G.scoreApi    = (board && board.dataset.scoreApi) || G.scoreApi;
    G.seedStr     = '';
    G.elapsed     = 0;
    G.startTime   = null;
    G.solution    = solution;
    G.hints       = hints;
    G.totalMines  = solution.reduce((a, b) => a + b, 0);
    G.player      = new Array(rows * cols).fill(2);
    G.maskedCells = maskedCells;

    document.getElementById('ms-overlay').style.display = 'none';
    document.getElementById('ms-timer').textContent = '0:00';
    updateMineCount();
    renderBoard();

    if (G.isHashBoard) {
        computeBoardId(rows, cols, hash, maskHash || '').then(id => {
            G._boardId = id;
            loadLeaderboard();
        });
    }
}

// ── Init ──────────────────────────────────────────────────────────────────────
function initGame(seedStr, isPOTD) {
    if (G.timer) { clearInterval(G.timer); G.timer = null; }

    const board = document.getElementById('ms-board');
    G.rows     = parseInt(board.dataset.rows)     || 10;
    G.cols     = parseInt(board.dataset.cols)     || 10;
    G.scoreApi = board.dataset.scoreApi           || '/api/mosaic-scores';

    G.won       = false;
    G.isPOTD    = isPOTD;
    G.seedStr   = seedStr;
    G.elapsed   = 0;
    G.startTime = null;

    const { solution, hints, totalMines } = generatePuzzle(seedStr, G.rows, G.cols);
    G.solution   = solution;
    G.hints      = hints;
    G.totalMines = totalMines;
    G.player     = new Array(G.rows * G.cols).fill(2);  // 2=unknown initial state

    document.getElementById('ms-overlay').style.display = 'none';
    document.getElementById('ms-timer').textContent = '0:00';

    const label = document.getElementById('ms-mode-label');
    if (label) label.textContent = isPOTD ? '📅 Puzzle of the Day' : '🎲 Random Puzzle';

    // Hide permalink until solved
    const row = document.getElementById('ms-permalink-row');
    if (row) row.style.display = 'none';

    // Reset score form
    const form = document.getElementById('ms-score-form');
    if (form) form.style.display = 'none';
    const msg = document.getElementById('ms-score-msg');
    if (msg) msg.textContent = '';

    updateMineCount();
    renderBoard();

    if (isPOTD) loadLeaderboard();
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const board    = document.getElementById('ms-board');
    const today    = board.dataset.today;
    const initHash = board.dataset.hash || '';
    const initMask = board.dataset.mask || '';

    // Apply density override from data-density attribute (custom page)
    const dataDensity = parseFloat(board.dataset.density);
    if (!isNaN(dataDensity)) G.density = dataDensity;

    if (initHash) {
        // Custom board: initialize from board hash
        initGameFromHash(
            initHash,
            parseInt(board.dataset.rows) || 9,
            parseInt(board.dataset.cols) || 9,
            initMask
        );
    } else if (board.dataset.custom === '1') {
        // Custom config page with no hash: start with a random board
        initGame(Math.random().toString(36).slice(2, 10), false);
    } else {
        // Allow pre-seeding from data-seed (replay page)
        const initSeed = board.dataset.seed || today;
        const initPOTD = !board.dataset.seed;
        initGame(initSeed, initPOTD);
    }

    // Custom board config panel — "Generate" button
    document.getElementById('mc-generate')?.addEventListener('click', () => {
        const board   = document.getElementById('ms-board');
        const rows    = Math.max(3, Math.min(20, parseInt(document.getElementById('mc-rows')?.value) || 9));
        const cols    = Math.max(3, Math.min(20, parseInt(document.getElementById('mc-cols')?.value) || 9));
        const density = parseFloat(document.getElementById('mc-density')?.value) || 0.35;
        board.dataset.rows = rows;
        board.dataset.cols = cols;
        G.density = density;
        initGame(Math.random().toString(36).slice(2, 10), false);
    });

    document.getElementById('ms-potd-btn')?.addEventListener('click', () => initGame(today, true));
    document.getElementById('ms-random-btn')?.addEventListener('click', () =>
        initGame(Math.random().toString(36).slice(2, 10), false));
    document.getElementById('ms-overlay-potd')?.addEventListener('click', () => {
        document.getElementById('ms-overlay').style.display = 'none';
        initGame(today, true);
    });
    document.getElementById('ms-overlay-random')?.addEventListener('click', () => {
        document.getElementById('ms-overlay').style.display = 'none';
        initGame(Math.random().toString(36).slice(2, 10), false);
    });

    // End drag when mouse button is released anywhere on the page
    document.addEventListener('mouseup', () => { dragActive = false; });

    // Manual score save button
    document.getElementById('ms-save-btn')?.addEventListener('click', () => saveScore());

    // Hide Numbers toggle (shown in win overlay)
    document.getElementById('ms-hide-numbers-btn')?.addEventListener('click', toggleHideNumbers);
});
