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
    rows:       10,
    cols:       10,
    hints:      [],
    solution:   [],
    player:     [],
    totalMines: 0,
    isPOTD:     true,
    seedStr:    '',
    scoreApi:   '/api/mosaic-scores',   // overridden for easy mode
    startTime:  null,
    elapsed:    0,
    timer:      null,
    won:        false,
};

// ── Puzzle generation ─────────────────────────────────────────────────────────
function generatePuzzle(seedStr, rows, cols) {
    const rng = mulberry32(strSeed(`mosaic:${rows}x${cols}:${seedStr}`));
    // 5×5 easy targets ~8 black cells (32%); standard 9×9 uses 35%
    const density = (rows <= 5 && cols <= 5) ? 0.32 : 0.35;
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
                count += G.player[nr * G.cols + nc];
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
    const filled = G.player.reduce((a, b) => a + b, 0);
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

    const span    = el.querySelector('.ms-hint');
    const hint    = G.hints[idx];
    const current = neighborCount(r, c);
    span.classList.remove('ms-hint-ok', 'ms-hint-over');
    if (current === hint)    span.classList.add('ms-hint-ok');
    else if (current > hint) span.classList.add('ms-hint-over');
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
            if (G.player[idx] === 1) cell.classList.add('ms-black');

            const span = document.createElement('span');
            span.className   = 'ms-hint';
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

function refreshAffected(r, c) {
    for (let dr = -1; dr <= 1; dr++)
        for (let dc = -1; dc <= 1; dc++) {
            const nr = r + dr, nc = c + dc;
            if (nr >= 0 && nr < G.rows && nc >= 0 && nc < G.cols) renderCell(nr, nc);
        }
}

// ── Click ─────────────────────────────────────────────────────────────────────
function handleClick(r, c) {
    if (G.won) return;
    if (!G.startTime) startTimer();

    const idx = r * G.cols + c;
    G.player[idx] = G.player[idx] === 1 ? 0 : 1;
    refreshAffected(r, c);
    updateMineCount();

    if (checkWin()) {
        stopTimer();
        G.won = true;
        onWin();
    }
}

// ── Win ───────────────────────────────────────────────────────────────────────
function onWin() {
    document.getElementById('ms-win-time').textContent = fmtTime(G.elapsed);
    document.getElementById('ms-overlay').style.display = 'flex';

    const board    = document.getElementById('ms-board');
    const username = board.dataset.username || '';
    const form     = document.getElementById('ms-score-form');

    if (G.isPOTD) {
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
        const r = await fetch(G.scoreApi, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ name, puzzle_date: G.seedStr, time_secs: Math.max(1, G.elapsed) }),
        });
        if (r.ok) {
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
    if (!G.isPOTD) return;
    const el = document.getElementById('ms-lb-content');
    if (!el) return;
    el.innerHTML = '<div class="lb-loading">Loading…</div>';

    const title = document.getElementById('ms-lb-title');
    if (title) title.textContent = `🏆 Best Times — ${G.seedStr}`;

    try {
        const r    = await fetch(`${G.scoreApi}/${G.seedStr}`);
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
                <td class="lb-replay"><a href="/mosaic/replay?seed=${esc(s.puzzle_date)}&rows=${G.rows}&cols=${G.cols}" class="ms-replay-link" title="Replay this puzzle">🔗</a></td>
            </tr>`).join('');

        el.innerHTML = `
            <div class="lb-table-wrap">
              <table class="lb-table">
                <thead><tr><th>#</th><th>Name</th><th>Time</th><th></th></tr></thead>
                <tbody>${rows}</tbody>
              </table>
            </div>`;
    } catch {
        el.innerHTML = '<div class="lb-empty">⚠️ Could not load scores.</div>';
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
    G.player     = new Array(G.rows * G.cols).fill(0);

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
    const board   = document.getElementById('ms-board');
    const today   = board.dataset.today;
    // Allow pre-seeding from data-seed (replay page)
    const initSeed = board.dataset.seed || today;
    const initPOTD = !board.dataset.seed;

    initGame(initSeed, initPOTD);

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

    // Manual score save button
    document.getElementById('ms-save-btn')?.addEventListener('click', () => saveScore());
});
