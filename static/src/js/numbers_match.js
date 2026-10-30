'use strict';

// ── Constants ─────────────────────────────────────────────────────────────────
const NM_COLS      = 9;
const NM_EPOCH     = '2024-01-01';
// Easy grew from 4 to 6 rows in revision v3 (F-NM-ROWS); mirrors numbers_match_engine.py.
const NM_DIFF_LABELS = { 6: 'Easy', 8: 'Medium', 16: 'Hard', 32: 'Expert' };
const NM_EASY_ROWS   = 6;
const HINT_COST       = 3;   // score penalty per hint used
const UNDO_COST       = 5;   // score penalty per undo used
const ADD_LINES_LIMIT = 5;   // max Add Lines uses per game
const AUTO_NEXT_DELAY_MS = 350;

// Matching pairs share a colour class (.nm-n1 … .nm-n9); the palette per theme is in style.css.

// Text from translations.py, passed by the page as window.NM_T.
const NM_TEXT = Object.assign({
    clearedLabel:   'Numbers Cleared',
    clearedToast:   'No more {n} left on the board',
    rulesTitle:     'Same numbers or sum of 10',
    rulesButton:    'How pairs connect',
    ruleDiagonal:   'Diagonal',
    ruleHorizontal: 'Horizontal',
    ruleVertical:   'Vertical',
    ruleLine:       'Line to line',
}, window.NM_T || {});

// ── Game state ─────────────────────────────────────────────────────────────────
let G = {};
let _lbReqId = 0;          // incremented each loadLeaderboard call; stale responses are discarded
let _showConnections = false; // persists across games; toggled by the Paths button
let _autoNextTimer = null;
let _gameSeq = 0;
let _pendingGameId = 0;    // guards against stale initDailyGame completing after a newer load started
// Board revision and puzzle-day timezone come from the server
// (numbers_match_generator.py) via data attributes on #nm-board.
const _nmBoardData   = document.getElementById('nm-board')?.dataset || {};
let   _serverRevision = _nmBoardData.revision || '';
const _nmTimeZone     = _nmBoardData.timezone || 'America/New_York';

// ── Utility ────────────────────────────────────────────────────────────────────
function fmtTime(s) {
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

function esc(s) {
    return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}

// Puzzle date (YYYY-MM-DD) in the server's puzzle timezone, used when
// /api/numbers-match-today is unreachable. en-CA formats as YYYY-MM-DD.
function nmToday() {
    try {
        return new Intl.DateTimeFormat('en-CA', {
            timeZone: _nmTimeZone, year: 'numeric', month: '2-digit', day: '2-digit',
        }).format(new Date());
    } catch {
        return _nmBoardData.realToday || new Date().toISOString().slice(0, 10);
    }
}

async function serverToday() {
    try {
        const r = await fetch(cacheBustUrl('/api/numbers-match-today'), { cache: 'no-store' });
        if (!r.ok) throw new Error('today failed');
        const data = await r.json();
        if (/^v\d+$/.test(data.revision || '')) _serverRevision = data.revision;
        if (/^\d{4}-\d{2}-\d{2}$/.test(data.today)) return data.today;
    } catch {
        // Fall back to the browser clock in the puzzle timezone.
    }
    return nmToday();
}

function cacheBustUrl(path) {
    const sep = path.includes('?') ? '&' : '?';
    return `${path}${sep}_=${Date.now()}`;
}

function boardUrl(dateStr) {
    return cacheBustUrl(`/api/numbers-match-board/${dateStr}?rev=${encodeURIComponent(_serverRevision)}`);
}

function scorePuzzleId(dateStr, diffKey = null) {
    return diffKey ? `${dateStr}-${diffKey}-${_serverRevision}` : `${dateStr}-${_serverRevision}`;
}

function playerName() {
    const username = document.getElementById('nm-board')?.dataset.username?.trim() || '';
    const saved    = localStorage.getItem('nm_name')?.trim() || '';
    if (username || saved) return username || saved;
    let guest = localStorage.getItem('nm_guest_name')?.trim() || '';
    if (!guest) {
        guest = `Guest ${Math.floor(1000 + Math.random() * 9000)}`;
        localStorage.setItem('nm_guest_name', guest);
    }
    return guest;
}

// ── Next game after a win (F-GAME-END) ─────────────────────────────────────────
// After the Daily comes Easy; after a difficulty, another board of the same size.
// Each day's Daily/Easy/Medium/Hard/Expert board is one fixed, ranked puzzle, so
// once the player has finished it the next board of that size is a random,
// unranked practice board.
const PLAYED_KEY = 'nm_played';

function playedToday(today) {
    try {
        const all = JSON.parse(localStorage.getItem(PLAYED_KEY) || '[]');
        return all.filter(id => id.startsWith(today));
    } catch { return []; }
}

function markPlayed(puzzleId) {
    try {
        const today = puzzleId.slice(0, 10);
        const ids = playedToday(today);
        if (!ids.includes(puzzleId)) ids.push(puzzleId);
        localStorage.setItem(PLAYED_KEY, JSON.stringify(ids));
    } catch {}
}

function isDailyId(puzzleId) {
    return /^\d{4}-\d{2}-\d{2}-v\d+$/.test(puzzleId || '');
}

async function startNextGame(finishedRows) {
    const pendingAtStart = _pendingGameId;
    const today = await serverToday();
    if (_pendingGameId !== pendingAtStart) return; // a manual game load started while we awaited
    const rows = NM_DIFF_LABELS[finishedRows] ? finishedRows : NM_EASY_ROWS;
    const rankedId = scorePuzzleId(today, NM_DIFF_LABELS[rows].toLowerCase());
    // autoNext: keep the finished game's leaderboard on screen (B57).
    if (playedToday(today).includes(rankedId)) initPracticeGame(rows, true);
    else initRandomGame(rows, today, true);
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
    return 6;
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
function nmStartTimer() {
    if (G.timer) return;
    G.startTime = Date.now() - G.elapsed * 1000;
    G.timer = setInterval(() => {
        G.elapsed = Math.floor((Date.now() - G.startTime) / 1000);
        document.getElementById('nm-timer').textContent = fmtTime(G.elapsed);
    }, 500);
}

function nmStopTimer() {
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

// ── Move log (F-NM-VERIFY) ───────────────────────────────────────────────────────
// The server replays this log to compute the score it stores; see
// numbers_match_engine.py for the format. t = ms since the first cell press.
function logMove(kind, ...cells) {
    const t = G.startTime ? Date.now() - G.startTime : 0;
    G.moves.push([kind, t, ...cells]);
    return t;
}

async function requestGameToken(gameId, puzzleId) {
    try {
        const r = await fetch('/api/numbers-match-start', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body:    JSON.stringify({ puzzle_id: puzzleId }),
            cache:   'no-store',
        });
        if (!r.ok) return;
        const data = await r.json();
        if (G.gameId === gameId) G.gameToken = data.token;
    } catch {
        // Without a token the game can still be played; the score just can't be saved.
    }
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

// ── Numbers cleared (F-NM-CLEARED) ─────────────────────────────────────────────
const CLEARED_TOAST_MS = 2500;
let _clearedTimer = null;

function remainingDigits() {
    return new Set(G.board.filter(Boolean));
}

function renderCleared() {
    let bar = document.getElementById('nm-cleared');
    if (!bar) {
        bar = document.createElement('div');
        bar.id = 'nm-cleared';
        bar.className = 'nm-cleared';
        const wrap = document.getElementById('nm-board-wrap');
        wrap?.parentNode?.insertBefore(bar, wrap);
    }
    const left = remainingDigits();
    const digits = [1, 2, 3, 4, 5, 6, 7, 8, 9].map(n => left.has(n)
        ? `<span class="nm-cleared-digit">${n}</span>`
        : `<span class="nm-cleared-digit nm-cleared-digit--done" title="${n}">✓</span>`).join('');
    bar.innerHTML = `<span class="nm-cleared-label">${esc(NM_TEXT.clearedLabel)}</span>` +
                    `<span class="nm-cleared-digits">${digits}</span>`;
}

function hideToast(id) {
    document.getElementById(id)?.classList.remove('game-toast--show');
}

function showClearedToast(digits) {
    hideToast('nm-toast');   // both toasts share the same spot
    let el = document.getElementById('nm-clear-toast');
    if (!el) {
        el = document.createElement('div');
        el.id = 'nm-clear-toast';
        el.className = 'game-toast';
        el.setAttribute('role', 'status');
        document.body?.appendChild(el);
    }
    el.innerHTML = `<div class="game-toast-title">✓ ${esc(NM_TEXT.clearedToast.replace('{n}', digits.join(', ')))}</div>`;
    el.classList.add('game-toast--show');
    clearTimeout(_clearedTimer);
    _clearedTimer = setTimeout(() => el.classList.remove('game-toast--show'), CLEARED_TOAST_MS);
}

// ── Actions ────────────────────────────────────────────────────────────────────
function doMatch(i, j) {
    const t = logMove('m', i, j);
    const digitsBefore = remainingDigits();
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
        nmStopTimer();
        G.elapsed = Math.max(1, Math.floor(t / 1000));   // same rounding as the server replay
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
    const left = remainingDigits();
    const gone = [...digitsBefore].filter(d => !left.has(d)).sort();
    if (gone.length) showClearedToast(gone);
}

function doUndo() {
    if (G.undosLeft <= 0 || G.history.length === 0 || G.won) return;
    logMove('u');
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
    logMove('h');
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
    logMove('a');
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
    if (!G.startTime) nmStartTimer();

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
            el.classList.add(`nm-n${val}`);
            if (idx === G.selected)  el.classList.add('nm-selected');
            if (hintSet.has(idx))    el.classList.add('nm-hint');
            el.addEventListener('click', () => handleCellClick(idx));
        }

        grid.appendChild(el);
    });
}

function updateHUD() {
    renderCleared();
    document.getElementById('nm-score').textContent    = G.score;
    document.getElementById('nm-undo-btn').textContent = `↩ ${G.undosLeft}`;
    document.getElementById('nm-hint-btn').textContent = `💡 ${G.hintsLeft}`;
    document.getElementById('nm-add-btn').textContent  = `+ Add Lines (${G.addLinesLeft})`;
    document.getElementById('nm-undo-btn').disabled    = G.undosLeft <= 0 || G.history.length === 0;
    document.getElementById('nm-hint-btn').disabled    = G.hintsLeft <= 0;
    document.getElementById('nm-add-btn').disabled     = G.addLinesLeft <= 0;
}

// ── Game end (F-GAME-END) ──────────────────────────────────────────────────────
// A toast shows the result for 5 s while the next game starts right away.
const TOAST_MS = 5000;
let _toastTimer = null;

function showGameToast(title, detail, status) {
    let el = document.getElementById('nm-toast');
    if (!el) {
        el = document.createElement('div');
        el.id = 'nm-toast';
        el.className = 'game-toast';
        el.setAttribute('role', 'status');
        document.body?.appendChild(el);
    }
    el.innerHTML = `<div class="game-toast-title">${esc(title)}</div>` +
                   `<div class="game-toast-detail">${esc(detail)}</div>` +
                   `<div class="game-toast-status" id="nm-toast-status">${esc(status)}</div>`;
    el.classList.add('game-toast--show');
    clearTimeout(_toastTimer);
    _toastTimer = setTimeout(() => el.classList.remove('game-toast--show'), TOAST_MS);
}

function setToastStatus(text) {
    const el = document.getElementById('nm-toast-status');
    if (el) el.textContent = text;
}

function showWinOverlay() {
    hideToast('nm-clear-toast');   // the win toast replaces it
    showGameToast('🎉 Board cleared!',
                  `⭐ ${G.score}  ·  ⏱ ${fmtTime(G.elapsed)}`,
                  G.isPOTD ? 'Saving score…' : 'Practice board — not ranked');
    if (G.isPOTD) {
        markPlayed(G.puzzleId);
        saveScore(playerName());
    }
    const rows = isDailyId(G.puzzleId) ? NM_EASY_ROWS : G.diffRows;   // Daily → Easy
    _autoNextTimer = setTimeout(() => startNextGame(rows), AUTO_NEXT_DELAY_MS);
}

// ── Score submission ───────────────────────────────────────────────────────────
async function saveScore(autoName = null) {
    if (G.scoreSaved) return;
    const inp  = document.getElementById('nm-name-input');
    const btn  = document.getElementById('nm-save-btn');
    const name = autoName || inp?.value.trim() || playerName();
    if (!name) { inp?.focus(); return; }
    if (!G.gameToken) {
        setToastStatus('This game could not be verified, so the score was not saved.');
        return;
    }
    const gameId = G.gameId;
    const puzzleId = G.puzzleId;
    const payload = {
        name,
        puzzle_date: G.puzzleId,
        game_token:  G.gameToken,
        moves:       G.moves,
        score:       G.score,
        time_secs:   Math.max(1, G.elapsed),
        lines_added: G.linesAdded,
    };
    G.scoreSaved = true;

    if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }

    try {
        const r = await fetch('/api/numbers-match-scores', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body:    JSON.stringify(payload),
        });
        if (r.ok) {
            localStorage.setItem('nm_name', name);
            if (btn) btn.textContent = '✓ Saved!';
            setToastStatus(`✅ Score saved for ${name}`);
            // Show the ranking of the game just finished, even though the next one
            // has already started (B57).
            showLeaderboardFor(puzzleId);
        } else {
            if (G.gameId === gameId) G.scoreSaved = false;
            if (btn) { btn.textContent = 'Save Score'; btn.disabled = false; }
            setToastStatus('Could not save score.');
        }
    } catch {
        if (G.gameId === gameId) G.scoreSaved = false;
        if (btn) { btn.textContent = 'Save Score'; btn.disabled = false; }
        setToastStatus('Network error saving score.');
    }
}

// ── Leaderboard ────────────────────────────────────────────────────────────────
async function loadLeaderboard(puzzleId = G.isPOTD ? G.puzzleId : null) {
    if (!puzzleId) return;
    const el = document.getElementById('nm-lb-content');
    if (!el) return;
    const myId = ++_lbReqId;
    el.innerHTML = '<div class="lb-loading">Loading…</div>';

    try {
        const r    = await fetch(cacheBustUrl(`/api/numbers-match-scores/${puzzleId}`), { cache: 'no-store' });
        const data = await r.json();
        if (myId !== _lbReqId) return;   // a newer request already arrived

        if (!data.length) {
            el.innerHTML = '<div class="lb-empty">No scores yet — be the first!</div>';
            return;
        }

        const rows = data.map((s, i) => {
            const nameHtml = s.profile_url
                ? `<a href="${esc(s.profile_url)}" class="lb-profile-link">${esc(s.name)}</a>`
                : esc(s.name);
            const flag = s.country
                ? `<span class="fi fi-${esc(s.country.toLowerCase())}"></span> `
                : '';
            return `
                <tr class="${i % 2 === 1 ? 'lb-even' : ''}">
                    <td class="lb-rank">${i + 1}</td>
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
    const myPendingId = ++_pendingGameId;
    nmStopTimer();
    _showLoading(true);
    const requestedDate = dateStr || nmToday();

    try {
        const r = await fetch(boardUrl(requestedDate), { cache: 'no-store' });
        if (!r.ok) throw new Error('fetch failed');
        const data = await r.json();
        if (myPendingId !== _pendingGameId) return;  // superseded by a newer load
        _startGame(data.board_data, data.rows, scorePuzzleId(requestedDate), true);
    } catch {
        if (myPendingId !== _pendingGameId) return;
        _showLoading(false);
        document.getElementById('nm-grid').innerHTML =
            '<div class="nm-error">⚠️ Could not load today\'s puzzle. Please refresh.</div>';
    }
}

function initRandomGame(rows, dateStr = null, autoNext = false) {
    ++_pendingGameId;  // cancel any in-flight initDailyGame
    nmStopTimer();
    const today    = dateStr || nmToday();
    const diffKey  = NM_DIFF_LABELS[rows]?.toLowerCase();
    const seed     = diffKey ? scorePuzzleId(today, diffKey) : Date.now().toString(36);
    const board    = generateBoardClient(seed, rows);
    const puzzleId = diffKey ? scorePuzzleId(today, diffKey) : seed;
    _startGame(board, rows, puzzleId, !!diffKey, autoNext);
}

// Random, unranked board of the given size (after the day's ranked one is done).
function initPracticeGame(rows, autoNext = false) {
    ++_pendingGameId;  // cancel any in-flight initDailyGame
    nmStopTimer();
    const seed = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    _startGame(generateBoardClient(seed, rows), rows, seed, false, autoNext);
}

// autoNext: started automatically after a win; the leaderboard keeps showing the
// finished game until its score is saved (B57).
function _startGame(boardData, rows, puzzleId, isPOTD, autoNext = false) {
    clearInterval(G.timer);
    clearTimeout(_autoNextTimer);
    G = {
        gameId:     ++_gameSeq,
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
        moves:         [],
        gameToken:     null,
    };
    if (isPOTD) requestGameToken(G.gameId, puzzleId);

    document.getElementById('nm-overlay').style.display = 'none';
    document.getElementById('nm-score-form').style.display = 'none';
    document.getElementById('nm-score-msg').style.display = 'none';
    document.getElementById('nm-timer').textContent     = '0:00';

    const isDailyPuzzle = isPOTD && /^\d{4}-\d{2}-\d{2}-v\d+$/.test(puzzleId);
    document.getElementById('nm-mode-label').textContent =
        isDailyPuzzle ? '📅 Daily Puzzle'
                      : `🎲 ${NM_DIFF_LABELS[rows] || rows + ' rows'}${isPOTD ? '' : ' · Practice'}`;

    document.querySelectorAll('.nm-diff-btn').forEach(btn => {
        btn.classList.toggle('nm-diff-btn--active',
            !isDailyPuzzle && parseInt(btn.dataset.rows) === rows);
    });

    _showLoading(false);
    renderBoard();
    updateHUD();

    // Practice boards have no ranking, and after a win the finished game's ranking
    // stays up: only a ranked game the player picked switches the leaderboard.
    if (isPOTD && !autoNext) showLeaderboardFor(puzzleId);
}

function showLeaderboardFor(puzzleId) {
    document.getElementById('nm-lb-section').style.display = 'block';
    const lbTitle = document.querySelector('.nm-lb-title');
    if (lbTitle) {
        const diff = (puzzleId.match(/-(easy|medium|hard|expert)-v\d+$/) || [])[1];
        lbTitle.textContent = isDailyId(puzzleId)
            ? '🏆 Today\'s Leaderboard'
            : `🏆 ${diff ? diff[0].toUpperCase() + diff.slice(1) : ''} — Today's Best`;
    }
    renderLbTabs(puzzleId);
    loadLeaderboard(puzzleId);
}

// The ranking has its own tabs: after a win it shows the game just finished while
// the mode buttons show the game being played (B62). Labels come from those buttons.
function renderLbTabs(puzzleId) {
    const tabs = document.getElementById('nm-lb-tabs');
    if (!tabs) return;
    const date = puzzleId.slice(0, 10);
    const rev  = (puzzleId.match(/-(v\d+)$/) || [])[1] || _serverRevision;
    const entries = [{ id: `${date}-${rev}`, label: document.getElementById('nm-daily-btn')?.textContent }];
    document.querySelectorAll('.nm-diff-btn').forEach(btn => {
        const key = NM_DIFF_LABELS[btn.dataset.rows]?.toLowerCase();
        if (key) entries.push({ id: `${date}-${key}-${rev}`, label: btn.textContent });
    });
    tabs.innerHTML = '';
    entries.forEach(({ id, label }) => {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'lb-tab' + (id === puzzleId ? ' lb-tab--active' : '');
        b.textContent = label;
        b.addEventListener('click', () => showLeaderboardFor(id));
        tabs.appendChild(b);
    });
}

function _showLoading(show) {
    const loading = document.getElementById('nm-loading');
    const grid    = document.getElementById('nm-grid');
    if (loading) loading.style.display = show ? 'block' : 'none';
    if (grid)    grid.style.display    = show ? 'none'  : 'grid';
}

// ── Rules popup: the four ways a pair can connect ──────────────────────────────
// Each diagram is a 2×2 sample; `on` are the two matched tiles, `link` draws what
// joins them. Tile n sits at TILE[n].
const TILE = [[3, 3], [47, 3], [3, 47], [47, 47]];

function ruleDiagram(values, on, link) {
    const tiles = values.map((v, i) => {
        const [x, y] = TILE[i];
        const active = on.includes(i);
        return `<rect x="${x}" y="${y}" width="38" height="38" rx="7" class="${active ? 'nm-rule-on' : 'nm-rule-off'}"/>` +
               `<text x="${x + 19}" y="${y + 27}" class="${active ? 'nm-rule-num-on' : 'nm-rule-num'}">${v}</text>`;
    }).join('');
    return `<svg viewBox="0 0 88 88" width="88" height="88" aria-hidden="true">${link}${tiles}</svg>`;
}

const NM_RULES = [
    ['ruleDiagonal',   [4, 5, 3, 4], [0, 3], '<rect x="30" y="30" width="28" height="28" rx="6" class="nm-rule-on"/>'],
    ['ruleHorizontal', [9, 1, 5, 3], [0, 1], '<rect x="30" y="3" width="28" height="38" class="nm-rule-on"/>'],
    ['ruleVertical',   [5, 7, 3, 7], [1, 3], '<rect x="47" y="30" width="38" height="28" class="nm-rule-on"/>'],
    // Line to line: the end of a row continues at the start of the next one.
    ['ruleLine',       [5, 8, 2, 3], [1, 2],
        '<rect x="74" y="13" width="14" height="18" rx="4" class="nm-rule-on"/>' +
        '<rect x="0" y="57" width="14" height="18" rx="4" class="nm-rule-on"/>'],
];

function setupRulesPopup() {
    const actions = document.querySelector('.nm-actions');
    if (!actions) return;
    const btn = document.createElement('button');
    btn.id = 'nm-rules-btn';
    btn.type = 'button';
    btn.textContent = 'ⓘ';
    btn.title = NM_TEXT.rulesButton;
    btn.setAttribute('aria-label', NM_TEXT.rulesButton);
    actions.appendChild(btn);

    const panel = document.createElement('div');
    panel.id = 'nm-rules';
    panel.className = 'nm-rules';
    panel.setAttribute('role', 'dialog');
    panel.hidden = true;
    panel.innerHTML =
        `<button type="button" class="nm-rules-close" aria-label="Close">✕</button>` +
        `<div class="nm-rules-title">${esc(NM_TEXT.rulesTitle)}</div>` +
        '<div class="nm-rules-grid">' +
        NM_RULES.map(([key, values, on, link]) =>
            `<figure>${ruleDiagram(values, on, link)}<figcaption>${esc(NM_TEXT[key])}</figcaption></figure>`).join('') +
        '</div>';
    document.body.appendChild(panel);

    const close = () => { panel.hidden = true; };
    btn.addEventListener('click', e => { e.stopPropagation(); panel.hidden = !panel.hidden; });
    panel.querySelector('.nm-rules-close').addEventListener('click', close);
    document.addEventListener('click', e => { if (!panel.contains(e.target)) close(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
}

// ── Entry point ────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    const boardEl = document.getElementById('nm-board');
    const permalinkMatch = window.location.pathname.match(/^\/numbers-match\/(\d{4}-\d{2}-\d{2})\/?$/);
    const liveToday      = await serverToday();
    const today          = permalinkMatch ? permalinkMatch[1] : liveToday;

    initDailyGame(today);

    document.getElementById('nm-daily-btn').addEventListener('click', () =>
        serverToday().then(initDailyGame));

    document.querySelectorAll('.nm-diff-btn').forEach(btn =>
        btn.addEventListener('click', () =>
            serverToday().then(today => initRandomGame(parseInt(btn.dataset.rows), today))));

    document.getElementById('nm-overlay-daily').addEventListener('click', () =>
        serverToday().then(initDailyGame));

    document.getElementById('nm-overlay-random').addEventListener('click', () =>
        serverToday().then(today => initRandomGame(G.diffRows || 4, today)));

    setupRulesPopup();
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
