'use strict';

// ── Constants ─────────────────────────────────────────────────────────────────
const NM_COLS  = 9;
const NM_EPOCH = '2024-01-01';

// Matching pairs share a color: 1↔9 red, 2↔8 blue, 3↔7 green, 4↔6 orange, 5↔5 purple
const NM_COLORS = [
    '',         // 0 — empty
    '#e53935',  // 1
    '#1976d2',  // 2
    '#388e3c',  // 3
    '#f57c00',  // 4
    '#7b1fa2',  // 5
    '#f57c00',  // 6
    '#388e3c',  // 7
    '#1976d2',  // 8
    '#e53935',  // 9
];

// ── Game state ─────────────────────────────────────────────────────────────────
let G = {};

// ── Utility ────────────────────────────────────────────────────────────────────
function fmtTime(s) {
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

function esc(s) {
    return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}

// ── Seeded RNG (mirrors Python generator — used for random-mode boards) ────────
function mulberry32(seed) {
    return () => {
        seed |= 0; seed = seed + 0x6D2B79F5 | 0;
        let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
        t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
        return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
}

function fnv1a(s) {
    let h = 0x811c9dc5;
    for (let i = 0; i < s.length; i++) {
        h ^= s.charCodeAt(i);
        h = Math.imul(h, 0x01000193) >>> 0;
    }
    return h;
}

// ── Board number / row count (mirrors numbers_match_generator.py) ──────────────
function boardNumber(dateStr) {
    return Math.floor((new Date(dateStr) - new Date(NM_EPOCH)) / 86400000) + 1;
}

function initialRows(boardNum) {
    return 4;
}

function generateBoardClient(seed, rows) {
    const total = rows * NM_COLS;
    const base  = Array.from({ length: total }, (_, i) => (i % NM_COLS) + 1);
    const rng   = mulberry32(fnv1a(String(seed)));
    for (let i = total - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [base[i], base[j]] = [base[j], base[i]];
    }
    return base;
}

// ── Timer ──────────────────────────────────────────────────────────────────────
function startTimer() {
    if (G.timer) return;
    G.startTime = Date.now() - G.elapsed * 1000;
    G.timer = setInterval(() => {
        G.elapsed = Math.floor((Date.now() - G.startTime) / 1000);
        document.getElementById('nm-timer').textContent = fmtTime(G.elapsed);
    }, 500);
}

function stopTimer() {
    clearInterval(G.timer);
    G.timer = null;
    if (G.startTime) G.elapsed = Math.floor((Date.now() - G.startTime) / 1000);
}

// ── Core game logic ────────────────────────────────────────────────────────────
function canMatch(a, b) {
    return a !== 0 && b !== 0 && (a === b || a + b === 10);
}

function areAdjacent(i, j) {
    if (i === j) return false;
    const [lo, hi] = i < j ? [i, j] : [j, i];
    const rowLo = Math.floor(lo / NM_COLS), colLo = lo % NM_COLS;
    const rowHi = Math.floor(hi / NM_COLS), colHi = hi % NM_COLS;
    const dr = rowHi - rowLo, dc = colHi - colLo;

    // Horizontal — same row
    if (rowLo === rowHi) {
        for (let k = lo + 1; k < hi; k++)
            if (G.board[k] !== 0) return false;
        return true;
    }
    // Vertical — same column
    if (colLo === colHi) {
        for (let k = lo + NM_COLS; k < hi; k += NM_COLS)
            if (G.board[k] !== 0) return false;
        return true;
    }
    // Diagonal
    if (Math.abs(dr) === Math.abs(dc)) {
        const stepC = dc > 0 ? 1 : -1;
        for (let s = 1; s < dr; s++)
            if (G.board[(rowLo + s) * NM_COLS + colLo + s * stepC] !== 0) return false;
        return true;
    }
    // Horizontal wrap — flat path between lo and hi (row-end → row-start counts as horizontal)
    for (let k = lo + 1; k < hi; k++)
        if (G.board[k] !== 0) return false;
    return true;
}

function calcPairScore(i, j) {
    const [lo, hi] = i < j ? [i, j] : [j, i];
    const rowLo = Math.floor(lo / NM_COLS), colLo = lo % NM_COLS;
    const rowHi = Math.floor(hi / NM_COLS), colHi = hi % NM_COLS;
    const dr = rowHi - rowLo, dc = colHi - colLo;
    let empty = 0;

    if (rowLo === rowHi) {
        for (let k = lo + 1; k < hi; k++) if (G.board[k] === 0) empty++;
    } else if (colLo === colHi) {
        for (let k = lo + NM_COLS; k < hi; k += NM_COLS) if (G.board[k] === 0) empty++;
    } else if (Math.abs(dr) === Math.abs(dc)) {
        const stepC = dc > 0 ? 1 : -1;
        for (let s = 1; s < dr; s++)
            if (G.board[(rowLo + s) * NM_COLS + colLo + s * stepC] === 0) empty++;
    } else {
        for (let k = lo + 1; k < hi; k++) if (G.board[k] === 0) empty++;
    }

    return 1 + Math.min(4, empty);   // +1 base, far-apart bonus up to +4
}

function countRowClearBonus(prevBoard) {
    let bonus = 0;
    for (let r = 0; r < G.rows; r++) {
        const start = r * NM_COLS;
        const nowEmpty  = G.board.slice(start, start + NM_COLS).every(v => v === 0);
        const hadValues = prevBoard.slice(start, start + NM_COLS).some(v => v !== 0);
        if (nowEmpty && hadValues) bonus += 10;
    }
    return bonus;
}

// ── Row collapse ──────────────────────────────────────────────────────────────
function collapseEmptyRows() {
    const newBoard = [];
    for (let r = 0; r < G.rows; r++) {
        const row = G.board.slice(r * NM_COLS, (r + 1) * NM_COLS);
        if (row.some(v => v !== 0)) newBoard.push(...row);
    }
    G.rows  = newBoard.length / NM_COLS;
    G.board = newBoard;
}

// ── Undo history ───────────────────────────────────────────────────────────────
function saveHistory() {
    G.history.push({
        board:      [...G.board],
        score:      G.score,
        rows:       G.rows,
        linesAdded: G.linesAdded,
    });
    if (G.history.length > 3) G.history.shift();
}

// ── Actions ────────────────────────────────────────────────────────────────────
function doMatch(i, j) {
    saveHistory();
    const prevBoard = [...G.board];
    G.board[i] = 0;
    G.board[j] = 0;
    G.selected = null;
    G.hintPair = null;
    G.score += calcPairScore(i, j);
    G.score += countRowClearBonus(prevBoard);

    if (G.board.every(v => v === 0)) {
        G.score += 150;
        G.won = true;
        stopTimer();
        if (G.isPOTD && typeof window.questsHook === 'function')
            window.questsHook('numbers_match_solved');
        renderBoard();
        updateHUD();
        showWinOverlay();
        return;
    }
    collapseEmptyRows();
    renderBoard();
    updateHUD();
}

function doUndo() {
    if (G.undosLeft <= 0 || G.history.length === 0 || G.won) return;
    const snap   = G.history.pop();
    G.board      = snap.board;
    G.score      = snap.score;
    G.rows       = snap.rows;
    G.linesAdded = snap.linesAdded;
    G.undosLeft--;
    G.selected   = null;
    G.hintPair   = null;
    renderBoard();
    updateHUD();
}

function findHint() {
    const len = G.board.length;
    for (let i = 0; i < len - 1; i++) {
        if (G.board[i] === 0) continue;
        for (let j = i + 1; j < len; j++) {
            if (G.board[j] === 0) continue;
            if (canMatch(G.board[i], G.board[j]) && areAdjacent(i, j)) return [i, j];
        }
    }
    return null;
}

function doHint() {
    if (G.hintsLeft <= 0 || G.won) return;
    G.selected = null;
    G.hintPair = findHint();
    G.hintsLeft--;
    renderBoard();
    updateHUD();
}

function doAddLines() {
    if (G.won) return;
    const remaining = G.board.filter(v => v !== 0);
    if (!remaining.length) return;
    while (remaining.length % NM_COLS !== 0) remaining.push(0);
    G.board      = [...G.board, ...remaining];
    G.rows      += remaining.length / NM_COLS;
    G.linesAdded++;
    G.selected   = null;
    G.hintPair   = null;
    renderBoard();
}

// ── Cell click ─────────────────────────────────────────────────────────────────
function handleCellClick(idx) {
    if (G.won || G.board[idx] === 0) return;
    if (!G.startTime) startTimer();

    G.hintPair = null;

    if (G.selected === null) {
        G.selected = idx;
        renderBoard();
        return;
    }
    if (G.selected === idx) {
        // Deselect on second tap of same cell
        G.selected = null;
        renderBoard();
        return;
    }

    if (canMatch(G.board[G.selected], G.board[idx]) && areAdjacent(G.selected, idx)) {
        doMatch(G.selected, idx);
    } else {
        // Move selection to newly tapped cell
        G.selected = idx;
        renderBoard();
    }
}

// ── Rendering ──────────────────────────────────────────────────────────────────
function renderBoard() {
    const grid = document.getElementById('nm-grid');
    grid.innerHTML = '';
    grid.style.gridTemplateColumns = `repeat(${NM_COLS}, 1fr)`;

    const hintSet = G.hintPair ? new Set(G.hintPair) : new Set();

    G.board.forEach((val, idx) => {
        const el = document.createElement('div');
        el.className   = 'nm-cell';
        el.dataset.idx = idx;

        if (val === 0) {
            el.classList.add('nm-empty');
        } else {
            el.textContent = val;
            el.style.color = NM_COLORS[val] || '';
            if (idx === G.selected) el.classList.add('nm-selected');
            if (hintSet.has(idx))   el.classList.add('nm-hint');
            el.addEventListener('click', () => handleCellClick(idx));
        }

        grid.appendChild(el);
    });
}

function updateHUD() {
    document.getElementById('nm-score').textContent    = G.score;
    document.getElementById('nm-undo-btn').textContent = `↩ ${G.undosLeft}`;
    document.getElementById('nm-hint-btn').textContent = `💡 ${G.hintsLeft}`;
    document.getElementById('nm-undo-btn').disabled    = G.undosLeft <= 0 || G.history.length === 0;
    document.getElementById('nm-hint-btn').disabled    = G.hintsLeft <= 0;
}

// ── Win overlay ────────────────────────────────────────────────────────────────
function showWinOverlay() {
    const ov = document.getElementById('nm-overlay');
    ov.style.display = 'flex';

    document.getElementById('nm-win-score').textContent = G.score;
    document.getElementById('nm-win-time').textContent  = fmtTime(G.elapsed);

    const form     = document.getElementById('nm-score-form');
    const username = document.getElementById('nm-board').dataset.username || '';

    if (G.isPOTD) {
        if (username) {
            form.style.display = 'none';
            const msgEl = document.getElementById('nm-score-msg');
            if (msgEl) msgEl.textContent = 'Saving score…';
            saveScore(username);
        } else {
            form.style.display = 'flex';
            document.getElementById('nm-name-input').value = localStorage.getItem('nm_name') || '';
            const btn = document.getElementById('nm-save-btn');
            btn.disabled    = false;
            btn.textContent = 'Save Score';
        }
    } else {
        form.style.display = 'none';
    }

    if (G.isPOTD) loadLeaderboard();
}

// ── Score submission ───────────────────────────────────────────────────────────
async function saveScore(autoName = null) {
    const inp  = document.getElementById('nm-name-input');
    const btn  = document.getElementById('nm-save-btn');
    const name = autoName || inp?.value.trim();
    if (!name) { inp?.focus(); return; }

    if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }

    try {
        const r = await fetch('/api/numbers-match-scores', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body:    JSON.stringify({
                name,
                puzzle_date: G.puzzleId,
                score:       G.score,
                time_secs:   Math.max(1, G.elapsed),
                lines_added: G.linesAdded,
            }),
        });
        if (r.ok) {
            localStorage.setItem('nm_name', name);
            if (btn) btn.textContent = '✓ Saved!';
            const msgEl = document.getElementById('nm-score-msg');
            if (msgEl) msgEl.textContent = `✅ Score saved for ${esc(name)}!`;
            loadLeaderboard();
        } else {
            if (btn) { btn.textContent = 'Error — retry'; btn.disabled = false; }
            const msgEl = document.getElementById('nm-score-msg');
            if (msgEl) msgEl.textContent = '❌ Could not save score.';
        }
    } catch {
        if (btn) { btn.textContent = 'Error — retry'; btn.disabled = false; }
        const msgEl = document.getElementById('nm-score-msg');
        if (msgEl) msgEl.textContent = '❌ Network error.';
    }
}

// ── Leaderboard ────────────────────────────────────────────────────────────────
async function loadLeaderboard() {
    if (!G.isPOTD) return;
    const el = document.getElementById('nm-lb-content');
    if (!el) return;
    el.innerHTML = '<div class="lb-loading">Loading…</div>';

    try {
        const r    = await fetch(`/api/numbers-match-scores/${G.puzzleId}`);
        const data = await r.json();

        if (!data.length) {
            el.innerHTML = '<div class="lb-empty">No scores yet — be the first!</div>';
            return;
        }

        const medals = ['🥇', '🥈', '🥉'];
        const rows = data.map((s, i) => {
            const nameHtml = s.profile_url
                ? `<a href="${esc(s.profile_url)}" class="lb-profile-link">${esc(s.name)}</a>`
                : esc(s.name);
            const flag = s.country
                ? `<span class="fi fi-${esc(s.country.toLowerCase())}"></span> `
                : '';
            return `
                <tr class="${i < 3 ? 'top-' + (i + 1) : ''}">
                    <td class="lb-rank">${medals[i] || i + 1}</td>
                    <td class="lb-name">${flag}${nameHtml}</td>
                    <td class="lb-score">${s.score}</td>
                    <td class="lb-time">${fmtTime(s.time_secs)}</td>
                </tr>`;
        }).join('');

        el.innerHTML = `
            <div class="lb-table-wrap">
              <table class="lb-table">
                <thead><tr><th>#</th><th>Name</th><th>Score</th><th>Time</th></tr></thead>
                <tbody>${rows}</tbody>
              </table>
            </div>`;
    } catch {
        el.innerHTML = '<div class="lb-empty">⚠️ Could not load scores.</div>';
    }
}

// ── Game init ──────────────────────────────────────────────────────────────────
async function initDailyGame(dateStr) {
    stopTimer();
    _showLoading(true);

    try {
        const r = await fetch(`/api/numbers-match-board/${dateStr}`);
        if (!r.ok) throw new Error('fetch failed');
        const data = await r.json();
        _startGame(data.board_data, data.rows, dateStr, true);
    } catch {
        _showLoading(false);
        document.getElementById('nm-grid').innerHTML =
            '<div class="nm-error">⚠️ Could not load today\'s puzzle. Please refresh.</div>';
    }
}

function initRandomGame() {
    stopTimer();
    const seed  = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    const bNum  = boardNumber(document.getElementById('nm-board').dataset.realToday);
    const rows  = initialRows(bNum);
    const board = generateBoardClient(seed, rows);
    _startGame(board, rows, seed, false);
}

function _startGame(boardData, rows, puzzleId, isPOTD) {
    clearInterval(G.timer);
    G = {
        board:      boardData.slice(),
        rows,
        score:      0,
        elapsed:    0,
        timer:      null,
        startTime:  null,
        selected:   null,
        hintPair:   null,
        history:    [],
        undosLeft:  3,
        hintsLeft:  9,
        isPOTD,
        puzzleId,
        linesAdded: 0,
        won:        false,
    };

    document.getElementById('nm-overlay').style.display = 'none';
    document.getElementById('nm-timer').textContent     = '0:00';
    document.getElementById('nm-mode-label').textContent =
        isPOTD ? '📅 Daily Puzzle' : '🎲 Random Puzzle';

    document.getElementById('nm-lb-section').style.display = isPOTD ? 'block' : 'none';

    _showLoading(false);
    renderBoard();
    updateHUD();

    if (isPOTD) loadLeaderboard();
}

function _showLoading(show) {
    const loading = document.getElementById('nm-loading');
    const grid    = document.getElementById('nm-grid');
    if (loading) loading.style.display = show ? 'block' : 'none';
    if (grid)    grid.style.display    = show ? 'none'  : 'grid';
}

// ── Entry point ────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const boardEl = document.getElementById('nm-board');
    const today   = boardEl.dataset.today;

    initDailyGame(today);

    document.getElementById('nm-daily-btn').addEventListener('click', () =>
        initDailyGame(boardEl.dataset.realToday));

    document.getElementById('nm-random-btn').addEventListener('click', initRandomGame);

    document.getElementById('nm-overlay-daily').addEventListener('click', () =>
        initDailyGame(boardEl.dataset.realToday));

    document.getElementById('nm-overlay-random').addEventListener('click', initRandomGame);

    document.getElementById('nm-undo-btn').addEventListener('click', doUndo);
    document.getElementById('nm-hint-btn').addEventListener('click', doHint);
    document.getElementById('nm-add-btn').addEventListener('click',  doAddLines);

    document.getElementById('nm-save-btn').addEventListener('click', () => saveScore());
    document.getElementById('nm-name-input').addEventListener('keydown', e => {
        if (e.key === 'Enter') saveScore();
    });
});
