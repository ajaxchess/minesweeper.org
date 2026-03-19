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
const ROWS  = 5;
const COLS  = 5;
const MINES = 6;

// Namespace prefix keeps easy-5x5 puzzles distinct from daily 7x7 puzzles
const SEED_PREFIX = 'easy5x5:';

// Classic minesweeper number colours
const NUM_COLOR = [
    '', '#6ab0f5', '#57d474', '#e53935',
    '#3949ab', '#c62828', '#00838f', '#212121', '#757575',
];

// ── Game state ────────────────────────────────────────────────────────────────
let G = {
    cells:           [],
    isPOTD:          true,
    puzzleId:        '',
    startTime:       null,
    elapsed:         0,
    timer:           null,
    won:             false,
    highlightErrors: false,
};

// ── Puzzle generation ─────────────────────────────────────────────────────────
function generatePuzzle(seedStr) {
    const rng = mulberry32(strSeed(SEED_PREFIX + seedStr));

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

// ── Clue contradiction check ──────────────────────────────────────────────────
function isClueInContradiction(idx) {
    const r = Math.floor(idx / COLS), c = idx % COLS;
    const clueVal = G.cells[idx].count;
    let flagged = 0, unknown = 0;
    for (let dr = -1; dr <= 1; dr++) {
        for (let dc = -1; dc <= 1; dc++) {
            if (dr === 0 && dc === 0) continue;
            const nr = r + dr, nc = c + dc;
            if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
            const s = G.cells[nr * COLS + nc].state;
            if (s === 'flagged') flagged++;
            else if (s === 'unknown') unknown++;
        }
    }
    return flagged > clueVal || (flagged + unknown) < clueVal;
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
    el.className = 'cell';
    el.textContent = '';
    el.style.color = '';

    if (cell.state === 'clue') {
        el.classList.add('revealed');
        if (cell.count > 0) {
            el.textContent = cell.count;
            el.style.color = NUM_COLOR[cell.count] || '';
        }
        const idx = parseInt(el.dataset.idx);
        if (G.highlightErrors && !isNaN(idx) && isClueInContradiction(idx))
            el.classList.add('tz-clue-error');
    } else if (cell.state === 'unknown') {
        el.classList.add('hidden');
    } else if (cell.state === 'flagged') {
        el.classList.add('hidden', 'tz-flagged');
        el.textContent = '⭐';
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

function refreshNeighborClues(idx) {
    if (!G.highlightErrors) return;
    const r = Math.floor(idx / COLS), c = idx % COLS;
    for (let dr = -1; dr <= 1; dr++) {
        for (let dc = -1; dc <= 1; dc++) {
            if (dr === 0 && dc === 0) continue;
            const nr = r + dr, nc = c + dc;
            if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
            const nIdx = nr * COLS + nc;
            if (G.cells[nIdx].state === 'clue') refreshCell(nIdx);
        }
    }
}

// ── Interaction ───────────────────────────────────────────────────────────────
function handleClick(idx) {
    if (G.won) return;
    const cell = G.cells[idx];
    if (cell.state === 'clue') return;

    if (!G.startTime) startTimer();

    if      (cell.state === 'unknown') cell.state = 'empty';
    else if (cell.state === 'empty')   cell.state = 'flagged';
    else                               cell.state = 'unknown';

    refreshCell(idx);
    refreshNeighborClues(idx);
    updateFlagCount();
    checkWin();
}

function handleRightClick(idx) {
    if (G.won) return;
    const cell = G.cells[idx];
    if (cell.state === 'clue') return;

    if (!G.startTime) startTimer();

    if      (cell.state === 'unknown') cell.state = 'flagged';
    else if (cell.state === 'flagged') cell.state = 'empty';
    else                               cell.state = 'unknown';

    refreshCell(idx);
    refreshNeighborClues(idx);
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

    const form     = document.getElementById('tz-score-form');
    const username = document.getElementById('tz-board').dataset.username || '';

    if (G.isPOTD) {
        if (username) {
            form.style.display = 'none';
            const msgEl = document.createElement('div');
            msgEl.id = 'tz-score-msg';
            msgEl.style.fontSize = '0.9rem';
            msgEl.textContent = 'Saving score…';
            ov.insertBefore(msgEl, ov.querySelector('.tz-overlay-btns'));
            saveScore(username);
        } else {
            form.style.display = 'flex';
            document.getElementById('tz-name-input').value = localStorage.getItem('tz_name') || '';
            const btn = document.getElementById('tz-save-btn');
            btn.disabled = false;
            btn.textContent = 'Save Score';
        }
    } else {
        form.style.display = 'none';
    }
}

// ── Score submission ──────────────────────────────────────────────────────────
async function saveScore(autoName = null) {
    const inp  = document.getElementById('tz-name-input');
    const btn  = document.getElementById('tz-save-btn');
    const name = autoName || inp?.value.trim();
    if (!name) { inp?.focus(); return; }

    if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }

    try {
        const r = await fetch('/api/tentaizu-easy-scores', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, puzzle_date: G.puzzleDate, time_secs: Math.max(1, G.elapsed) }),
        });
        if (r.ok) {
            localStorage.setItem('tz_name', name);
            if (btn) btn.textContent = '✓ Saved!';
            const msgEl = document.getElementById('tz-score-msg');
            if (msgEl) msgEl.textContent = `✅ Score saved for ${name}!`;
            loadLeaderboard();
        } else {
            if (btn) { btn.textContent = 'Error — retry'; btn.disabled = false; }
            const msgEl = document.getElementById('tz-score-msg');
            if (msgEl) msgEl.textContent = '❌ Could not save score.';
        }
    } catch {
        if (btn) { btn.textContent = 'Error — retry'; btn.disabled = false; }
        const msgEl = document.getElementById('tz-score-msg');
        if (msgEl) msgEl.textContent = '❌ Network error.';
    }
}

// ── Permalink + leaderboard title ─────────────────────────────────────────────
function updatePermalinkAndTitle(dateStr, isPOTD) {
    const board     = document.getElementById('tz-board');
    const realToday = board.dataset.realToday;
    const lbTitle   = document.getElementById('tz-lb-title');
    const permRow   = document.getElementById('tz-permalink-row');
    const permLink  = document.getElementById('tz-permalink-link');

    if (isPOTD) {
        if (lbTitle) lbTitle.textContent = dateStr === realToday
            ? '🏆 Today\'s Best Times'
            : `🏆 Best Times — ${dateStr}`;
        if (permRow && permLink) {
            permLink.href        = `/tentaizu/easy-5x5-6/${dateStr}`;
            permLink.textContent = `minesweeper.org/tentaizu/easy-5x5-6/${dateStr}`;
            permRow.style.display = 'block';
        }
    } else {
        if (permRow) permRow.style.display = 'none';
    }
}

// ── Leaderboard ───────────────────────────────────────────────────────────────
async function loadLeaderboard() {
    if (!G.isPOTD) return;
    const el = document.getElementById('tz-lb-content');
    el.innerHTML = '<div class="lb-loading">Loading…</div>';

    try {
        const r    = await fetch(`/api/tentaizu-easy-scores/${encodeURIComponent(G.puzzleDate)}`);
        const data = await r.json();

        if (!data.length) {
            el.innerHTML = '<div class="lb-empty">No scores yet — be the first!</div>';
            return;
        }

        const medals = ['🥇', '🥈', '🥉'];
        const rows = data.map((s, i) => `
            <tr class="${i < 3 ? 'top-' + (i + 1) : ''}">
                <td class="lb-rank">${medals[i] || i + 1}</td>
                <td class="lb-name">${s.profile_url ? `<a href="${esc(s.profile_url)}" class="lb-profile-link">${esc(s.name)}</a>` : esc(s.name)}</td>
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

    // Previous days links
    const prevEl = document.getElementById('tz-prev-days');
    if (prevEl) {
        const links = [];
        for (let i = 1; i <= 7; i++) {
            const d = new Date(Date.now() - i * 86400000);
            const iso = d.toISOString().slice(0, 10);
            const label = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
            links.push(`<a href="/tentaizu/easy-5x5-6/${iso}" class="tz-prev-day-link">${label}</a>`);
        }
        prevEl.innerHTML = `<span class="tz-prev-days-label">Previous puzzles:</span> ${links.join('')}`;
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
function initGame(dateStr, isPOTD) {
    clearInterval(G.timer);

    G = {
        cells:           generatePuzzle(dateStr),
        isPOTD,
        puzzleId:        isPOTD ? SEED_PREFIX + dateStr : dateStr,
        puzzleDate:      dateStr,   // plain YYYY-MM-DD for API calls
        startTime:       null,
        elapsed:         0,
        timer:           null,
        won:             false,
        highlightErrors: localStorage.getItem('tzHighlightErrors') === 'true',
    };

    const ov = document.getElementById('tz-overlay');
    ov.style.display = 'none';
    ov.className     = '';

    document.getElementById('tz-timer').textContent     = '0:00';
    document.getElementById('tz-mode-label').textContent =
        isPOTD ? '📅 Easy 5×5 Daily' : '🎲 Random Puzzle';

    const lb = document.getElementById('tz-lb-section');
    lb.style.display = isPOTD ? 'block' : 'none';

    updatePermalinkAndTitle(dateStr, isPOTD);
    updateFlagCount();
    renderBoard();

    const btn = document.getElementById('highlight-errors-toggle');
    if (btn) btn.classList.toggle('active', G.highlightErrors);

    if (isPOTD) loadLeaderboard();
}

// ── Entry point ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const board = document.getElementById('tz-board');
    // Override grid to 5 columns
    board.style.gridTemplateColumns = `repeat(${COLS}, var(--cell-size))`;

    const today = board.dataset.today;

    initGame(today, true);

    document.getElementById('tz-potd-btn').addEventListener('click', () =>
        initGame(board.dataset.realToday, true));

    document.getElementById('tz-random-btn').addEventListener('click', () =>
        initGame(Date.now().toString(36) + Math.random().toString(36).slice(2, 6), false));

    document.getElementById('tz-overlay-potd').addEventListener('click', () =>
        initGame(board.dataset.realToday, true));

    document.getElementById('tz-overlay-random').addEventListener('click', () =>
        initGame(Date.now().toString(36) + Math.random().toString(36).slice(2, 6), false));

    document.getElementById('tz-save-btn').addEventListener('click', saveScore);
    document.getElementById('tz-name-input').addEventListener('keydown', e => {
        if (e.key === 'Enter') saveScore();
    });
});
