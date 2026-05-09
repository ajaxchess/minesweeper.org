'use strict';

// ── Constants ─────────────────────────────────────────────────────────────────
const NM_COLS      = 9;
const NM_EPOCH     = '2024-01-01';
const NM_DIFF_LABELS = { 4: 'Easy', 8: 'Medium', 16: 'Hard', 32: 'Expert' };
const HINT_COST       = 3;   // score penalty per hint used
const UNDO_COST       = 5;   // score penalty per undo used
const ADD_LINES_LIMIT = 5;   // max Add Lines uses per game

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
let _lbReqId = 0;          // incremented each loadLeaderboard call; stale responses are discarded
let _showConnections = false; // persists across games; toggled by the Paths button

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
        board:         [...G.board],
        score:         G.score,
        rows:          G.rows,
        linesAdded:    G.linesAdded,
        addLinesLeft:  G.addLinesLeft,
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
    G.board        = snap.board;
    G.score        = Math.max(0, snap.score - UNDO_COST);
    G.rows         = snap.rows;
    G.linesAdded   = snap.linesAdded;
    G.addLinesLeft = snap.addLinesLeft ?? ADD_LINES_LIMIT;
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
    const pair = findHint();
    if (!pair) {
        const btn = document.getElementById('nm-add-btn');
        btn.classList.add('nm-add-pulse');
        setTimeout(() => btn.classList.remove('nm-add-pulse'), 700);
        return;
    }
    G.hintPair  = pair;
    G.hintsLeft--;
    G.score = Math.max(0, G.score - HINT_COST);
    renderBoard();
    updateHUD();
}

function doAddLines() {
    if (G.won || G.addLinesLeft <= 0) return;
    const remaining = G.board.filter(v => v !== 0);
    if (!remaining.length) return;
    saveHistory();
    while (remaining.length % NM_COLS !== 0) remaining.push(0);
    G.board         = [...G.board, ...remaining];
    G.rows         += remaining.length / NM_COLS;
    G.linesAdded++;
    G.addLinesLeft--;
    G.selected      = null;
    G.hintPair      = null;
    renderBoard();
    updateHUD();
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

// ── Connections (Paths mode) ───────────────────────────────────────────────────
function applyAxisHighlight(hovIdx) {
    clearAxisHighlight();
    if (!_showConnections || hovIdx === null) return;
    const hovRow = Math.floor(hovIdx / NM_COLS);
    const hovCol = hovIdx % NM_COLS;
    const cells  = document.querySelectorAll('#nm-grid .nm-cell');
    cells.forEach(el => {
        const idx = parseInt(el.dataset.idx, 10);
        if (isNaN(idx) || idx === hovIdx) return;
        const r = Math.floor(idx / NM_COLS);
        const c = idx % NM_COLS;
        const isWrap = (hovCol === 0 && idx === hovIdx - 1) ||
                       (hovCol === NM_COLS - 1 && idx === hovIdx + 1);
        if (r === hovRow || c === hovCol ||
            (r - hovRow) === (c - hovCol) || (r - hovRow) === -(c - hovCol) || isWrap) {
            el.classList.add('nm-axis');
        }
    });
}

function clearAxisHighlight() {
    document.querySelectorAll('#nm-grid .nm-axis').forEach(el => el.classList.remove('nm-axis'));
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
            if (idx === G.selected)  el.classList.add('nm-selected');
            if (hintSet.has(idx))    el.classList.add('nm-hint');
            el.addEventListener('click', () => handleCellClick(idx));
        }

        grid.appendChild(el);
    });
}

function updateHUD() {
    document.getElementById('nm-score').textContent    = G.score;
    document.getElementById('nm-undo-btn').textContent = `↩ ${G.undosLeft}`;
    document.getElementById('nm-hint-btn').textContent = `💡 ${G.hintsLeft}`;
    document.getElementById('nm-add-btn').textContent  = `+ Add Lines (${G.addLinesLeft})`;
    document.getElementById('nm-undo-btn').disabled    = G.undosLeft <= 0 || G.history.length === 0;
    document.getElementById('nm-hint-btn').disabled    = G.hintsLeft <= 0;
    document.getElementById('nm-add-btn').disabled     = G.addLinesLeft <= 0;
}

// ── Win overlay ────────────────────────────────────────────────────────────────
function showWinOverlay() {
    document.getElementById('nm-grid').style.display = 'none';
    const ov = document.getElementById('nm-overlay');
    ov.style.display = 'flex';

    document.getElementById('nm-win-score').textContent = G.score;
    document.getElementById('nm-win-time').textContent  = fmtTime(G.elapsed);

    const form     = document.getElementById('nm-score-form');
    const username = document.getElementById('nm-board').dataset.username || '';

    const msgEl = document.getElementById('nm-score-msg');

    if (G.isPOTD) {
        if (username) {
            form.style.display = 'none';
            if (msgEl) { msgEl.style.display = 'block'; msgEl.textContent = 'Saving score…'; }
            saveScore(username);   // loadLeaderboard is called by saveScore on success
        } else {
            form.style.display = 'flex';
            if (msgEl) msgEl.style.display = 'none';
            document.getElementById('nm-name-input').value = localStorage.getItem('nm_name') || '';
            const btn = document.getElementById('nm-save-btn');
            btn.disabled    = false;
            btn.textContent = 'Save Score';
            loadLeaderboard();   // show current standings while the guest fills in their name
        }
    } else {
        form.style.display = 'none';
        if (msgEl) msgEl.style.display = 'none';
    }
}

// ── Score submission ───────────────────────────────────────────────────────────
async function saveScore(autoName = null) {
    if (G.scoreSaved) return;
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
        const msgEl = document.getElementById('nm-score-msg');
        if (r.ok) {
            G.scoreSaved = true;
            localStorage.setItem('nm_name', name);
            if (btn) btn.textContent = '✓ Saved!';
            if (msgEl) { msgEl.style.display = 'block'; msgEl.textContent = `✅ Score saved for ${esc(name)}!`; }
            loadLeaderboard();
        } else {
            if (btn) { btn.textContent = 'Save Score'; btn.disabled = false; }
            if (msgEl) { msgEl.style.display = 'block'; msgEl.textContent = '❌ Could not save score. Try again.'; }
            // If auto-save failed for a logged-in user, expose the form so they can retry
            const form = document.getElementById('nm-score-form');
            if (form && form.style.display === 'none') {
                form.style.display = 'flex';
                document.getElementById('nm-name-input').value = autoName || '';
            }
        }
    } catch {
        if (btn) { btn.textContent = 'Save Score'; btn.disabled = false; }
        const msgEl = document.getElementById('nm-score-msg');
        if (msgEl) { msgEl.style.display = 'block'; msgEl.textContent = '❌ Network error. Try again.'; }
        const form = document.getElementById('nm-score-form');
        if (form && form.style.display === 'none') {
            form.style.display = 'flex';
            document.getElementById('nm-name-input').value = autoName || '';
        }
    }
}

// ── Leaderboard ────────────────────────────────────────────────────────────────
async function loadLeaderboard() {
    if (!G.isPOTD) return;
    const el = document.getElementById('nm-lb-content');
    if (!el) return;
    const myId = ++_lbReqId;
    el.innerHTML = '<div class="lb-loading">Loading…</div>';

    try {
        const r    = await fetch(`/api/numbers-match-scores/${G.puzzleId}`);
        const data = await r.json();
        if (myId !== _lbReqId) return;   // a newer request already arrived

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
        document.getElementById('nm-lb-section')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch {
        if (myId !== _lbReqId) return;
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

function initRandomGame(rows) {
    stopTimer();
    const seed     = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    const board    = generateBoardClient(seed, rows);
    const today    = document.getElementById('nm-board').dataset.realToday;
    const diffKey  = NM_DIFF_LABELS[rows]?.toLowerCase();
    const puzzleId = diffKey ? `${today}-${diffKey}` : seed;
    _startGame(board, rows, puzzleId, !!diffKey);
}

function _startGame(boardData, rows, puzzleId, isPOTD) {
    clearInterval(G.timer);
    G = {
        board:      boardData.slice(),
        rows,
        diffRows:   rows,
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
        linesAdded:    0,
        addLinesLeft:  ADD_LINES_LIMIT,
        won:           false,
        scoreSaved:    false,
    };

    document.getElementById('nm-overlay').style.display = 'none';
    document.getElementById('nm-timer').textContent     = '0:00';

    const isDailyPuzzle = isPOTD && /^\d{4}-\d{2}-\d{2}$/.test(puzzleId);
    document.getElementById('nm-mode-label').textContent =
        isDailyPuzzle ? '📅 Daily Puzzle'
                      : `🎲 ${NM_DIFF_LABELS[rows] || rows + ' rows'}`;

    document.querySelectorAll('.nm-diff-btn').forEach(btn => {
        btn.classList.toggle('nm-diff-btn--active',
            !isDailyPuzzle && parseInt(btn.dataset.rows) === rows);
    });

    document.getElementById('nm-lb-section').style.display = isPOTD ? 'block' : 'none';

    const lbTitle = document.querySelector('.nm-lb-title');
    if (lbTitle) {
        lbTitle.textContent = isDailyPuzzle
            ? '🏆 Today\'s Leaderboard'
            : `🏆 ${NM_DIFF_LABELS[rows] || rows + ' rows'} — Today's Best`;
    }

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

    document.querySelectorAll('.nm-diff-btn').forEach(btn =>
        btn.addEventListener('click', () => initRandomGame(parseInt(btn.dataset.rows))));

    document.getElementById('nm-overlay-daily').addEventListener('click', () =>
        initDailyGame(boardEl.dataset.realToday));

    document.getElementById('nm-overlay-random').addEventListener('click', () =>
        initRandomGame(G.diffRows || 4));

    document.getElementById('nm-undo-btn').addEventListener('click', doUndo);
    document.getElementById('nm-hint-btn').addEventListener('click', doHint);
    document.getElementById('nm-add-btn').addEventListener('click',  doAddLines);

    document.getElementById('nm-connect-btn').addEventListener('click', () => {
        _showConnections = !_showConnections;
        document.getElementById('nm-connect-btn').classList.toggle('nm-connect-active', _showConnections);
        if (!_showConnections) clearAxisHighlight();
    });

    const grid = document.getElementById('nm-grid');
    grid.addEventListener('mouseover', e => {
        const cell = e.target.closest('.nm-cell');
        if (!cell || cell.classList.contains('nm-empty')) return;
        applyAxisHighlight(parseInt(cell.dataset.idx, 10));
    });
    grid.addEventListener('mouseleave', () => clearAxisHighlight());

    document.getElementById('nm-save-btn').addEventListener('click', () => saveScore());
    document.getElementById('nm-name-input').addEventListener('keydown', e => {
        if (e.key === 'Enter') saveScore();
    });
});
