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

function strSeed(s) {
    let h = 0x811c9dc5;
    for (let i = 0; i < s.length; i++) {
        h ^= s.charCodeAt(i);
        h = Math.imul(h, 0x01000193) >>> 0;
    }
    return h;
}

// ── Difficulty presets ────────────────────────────────────────────────────────
const DIFFICULTIES = {
    beginner:     { rows: 8,  cols: 8,  mines: 16 },
    intermediate: { rows: 10, cols: 10, mines: 35 },
    expert:       { rows: 15, cols: 15, mines: 75 },
};

// ── Game state ────────────────────────────────────────────────────────────────
let G = {
    rows: 8, cols: 8, mines: 16,
    mineSet:    new Set(),
    cells:      [],   // { isMine: bool, state: 'hidden'|'revealed'|'flagged'|'question'|'exploded'|'mine-revealed'|'wrong-flag' }
    rowClues:   [],   // rowClues[r] = [3, 1, 2]
    colClues:   [],   // colClues[c] = [2, 1]
    minesLeft:  0,
    startTime:  null,
    elapsed:    0,
    timer:      null,
    won:        false,
    over:       false,
    isPOTD:     true,
    puzzleId:   '',
    difficulty: 'beginner',
};

// ── Puzzle generation ─────────────────────────────────────────────────────────
function generatePuzzle(seedStr, difficulty) {
    const { rows, cols, mines } = DIFFICULTIES[difficulty];
    const rng = mulberry32(strSeed(seedStr + ':' + difficulty));

    // Fisher-Yates shuffle
    const idx = Array.from({ length: rows * cols }, (_, i) => i);
    for (let i = idx.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [idx[i], idx[j]] = [idx[j], idx[i]];
    }
    const mineSet = new Set(idx.slice(0, mines));

    const cells = Array.from({ length: rows * cols }, (_, i) => ({
        isMine: mineSet.has(i),
        state:  'hidden',
    }));

    // Row clues
    const rowClues = [];
    for (let r = 0; r < rows; r++) {
        const groups = [];
        let run = 0;
        for (let c = 0; c < cols; c++) {
            if (mineSet.has(r * cols + c)) {
                run++;
            } else {
                if (run) { groups.push(run); run = 0; }
            }
        }
        if (run) groups.push(run);
        rowClues.push(groups.length ? groups : [0]);
    }

    // Column clues
    const colClues = [];
    for (let c = 0; c < cols; c++) {
        const groups = [];
        let run = 0;
        for (let r = 0; r < rows; r++) {
            if (mineSet.has(r * cols + c)) {
                run++;
            } else {
                if (run) { groups.push(run); run = 0; }
            }
        }
        if (run) groups.push(run);
        colClues.push(groups.length ? groups : [0]);
    }

    return { rows, cols, mines, mineSet, cells, rowClues, colClues };
}

// ── Timer ─────────────────────────────────────────────────────────────────────
function startTimer() {
    if (G.timer) return;
    G.startTime = Date.now() - G.elapsed * 1000;
    G.timer = setInterval(() => {
        G.elapsed = Math.floor((Date.now() - G.startTime) / 1000);
        document.getElementById('nn-timer').textContent = fmtTime(G.elapsed);
    }, 500);
}

function stopTimer() {
    clearInterval(G.timer);
    G.timer = null;
    if (G.startTime) G.elapsed = Math.floor((Date.now() - G.startTime) / 1000);
}

function fmtTime(s) {
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

// ── Mine emoji (skin-aware) ───────────────────────────────────────────────────
function getMineEmoji() {
    const skin = document.documentElement.dataset.skin;
    if (skin === 'tentaizu')                          return '⭐';
    if (skin === 'flower' || skin === 'flower-light') return '🌸';
    return '💣';
}

// ── Rendering ─────────────────────────────────────────────────────────────────
function renderBoard() {
    const grid = document.getElementById('nn-grid');
    grid.style.setProperty('--nn-cols', G.cols);
    grid.innerHTML = '';

    // Top-left corner spacer
    const corner = document.createElement('div');
    corner.className = 'nn-corner';
    grid.appendChild(corner);

    // Column clue header cells
    for (let c = 0; c < G.cols; c++) {
        const el = document.createElement('div');
        el.className = 'nn-col-clue';
        el.dataset.col = c;
        G.colClues[c].forEach(n => {
            const span = document.createElement('span');
            span.textContent = n === 0 ? '—' : n;
            el.appendChild(span);
        });
        grid.appendChild(el);
    }

    // Game rows
    for (let r = 0; r < G.rows; r++) {
        // Row clue
        const rowClueEl = document.createElement('div');
        rowClueEl.className = 'nn-row-clue';
        rowClueEl.dataset.row = r;
        G.rowClues[r].forEach(n => {
            const span = document.createElement('span');
            span.textContent = n === 0 ? '—' : n;
            rowClueEl.appendChild(span);
        });
        grid.appendChild(rowClueEl);

        // Cells
        for (let c = 0; c < G.cols; c++) {
            const idx = r * G.cols + c;
            const el = document.createElement('div');
            el.className = 'nn-cell';
            el.dataset.idx = idx;
            applyCell(el, G.cells[idx]);
            el.addEventListener('click', () => handleClick(idx));
            el.addEventListener('contextmenu', e => { e.preventDefault(); handleRightClick(idx); });
            grid.appendChild(el);
        }
    }
}

function applyCell(el, cell) {
    el.className = 'nn-cell';
    el.textContent = '';
    el.style.color = '';

    switch (cell.state) {
        case 'hidden':
            el.classList.add('nn-hidden');
            break;
        case 'revealed':
            el.classList.add('nn-revealed');
            el.textContent = '✓';
            break;
        case 'flagged':
            el.classList.add('nn-hidden', 'nn-flagged');
            el.textContent = getMineEmoji();
            break;
        case 'question':
            el.classList.add('nn-hidden', 'nn-question');
            el.textContent = '?';
            break;
        case 'exploded':
            el.classList.add('nn-exploded');
            el.textContent = '💥';
            break;
        case 'mine-revealed':
            el.classList.add('nn-mine-revealed');
            el.textContent = getMineEmoji();
            break;
        case 'wrong-flag':
            el.classList.add('nn-wrong-flag');
            el.textContent = '❌';
            break;
    }
}

function refreshCell(idx) {
    const el = document.querySelector(`#nn-grid [data-idx="${idx}"]`);
    if (el) applyCell(el, G.cells[idx]);
}

// ── Interaction ───────────────────────────────────────────────────────────────
function handleClick(idx) {
    if (G.over || G.won) return;
    const cell = G.cells[idx];
    if (cell.state !== 'hidden' && cell.state !== 'question') return;

    if (!G.startTime) startTimer();

    if (cell.isMine) {
        cell.state = 'exploded';
        G.over = true;
        stopTimer();
        refreshCell(idx);
        revealAllAfterLoss();
        showLoseOverlay();
        return;
    }

    cell.state = 'revealed';
    refreshCell(idx);
    updateMineCounter();
    checkWin();
}

function handleRightClick(idx) {
    if (G.over || G.won) return;
    const cell = G.cells[idx];
    if (cell.state === 'revealed') return;

    if (!G.startTime) startTimer();

    if      (cell.state === 'hidden')   cell.state = 'flagged';
    else if (cell.state === 'flagged')  cell.state = 'question';
    else                                cell.state = 'hidden';

    refreshCell(idx);
    updateMineCounter();
    checkWin();
}

function revealAllAfterLoss() {
    G.cells.forEach((cell, idx) => {
        if (cell.state === 'exploded') return;
        if (cell.isMine && cell.state !== 'flagged') {
            cell.state = 'mine-revealed';
            refreshCell(idx);
        } else if (!cell.isMine && cell.state === 'flagged') {
            cell.state = 'wrong-flag';
            refreshCell(idx);
        }
    });
}

// ── Mine counter ──────────────────────────────────────────────────────────────
function updateMineCounter() {
    const flagged = G.cells.filter(c => c.state === 'flagged').length;
    G.minesLeft = G.mines - flagged;
    document.getElementById('nn-mines-left').textContent = G.minesLeft;
}

// ── Win check ─────────────────────────────────────────────────────────────────
function checkWin() {
    const allSafeRevealed = G.cells.every(c => c.isMine || c.state === 'revealed');
    if (!allSafeRevealed) return;

    G.won = true;
    stopTimer();

    // Auto-flag remaining mines
    G.cells.forEach((cell, idx) => {
        if (cell.isMine && cell.state !== 'flagged') {
            cell.state = 'flagged';
            refreshCell(idx);
        }
    });
    updateMineCounter();

    if (G.isPOTD && typeof window.questsHook === 'function') window.questsHook('nonosweeper_solved');
    showWinOverlay();
}

// ── Overlays ──────────────────────────────────────────────────────────────────
function showWinOverlay() {
    const ov = document.getElementById('nn-overlay');
    ov.className = 'win';
    ov.style.display = 'flex';

    document.getElementById('nn-overlay-title').textContent = '🎉 Solved!';
    document.getElementById('nn-overlay-time-row').style.display = '';
    document.getElementById('nn-win-time').textContent = fmtTime(G.elapsed);

    const form     = document.getElementById('nn-score-form');
    const scoreMsg = document.getElementById('nn-score-msg');
    const username = document.getElementById('nn-grid').dataset.username || '';

    if (G.isPOTD) {
        if (username) {
            form.style.display = 'none';
            scoreMsg.style.display = '';
            scoreMsg.textContent = 'Saving score…';
            saveScore(username);
        } else {
            form.style.display = 'flex';
            scoreMsg.style.display = 'none';
            document.getElementById('nn-name-input').value = localStorage.getItem('nn_name') || '';
            const btn = document.getElementById('nn-save-btn');
            btn.disabled = false;
            btn.textContent = 'Save Score';
        }
    } else {
        form.style.display = 'none';
        scoreMsg.style.display = 'none';
    }
}

function showLoseOverlay() {
    const ov = document.getElementById('nn-overlay');
    ov.className = 'lose';
    ov.style.display = 'flex';

    document.getElementById('nn-overlay-title').textContent = '💥 Mine hit!';
    document.getElementById('nn-overlay-time-row').style.display = 'none';
    document.getElementById('nn-score-form').style.display = 'none';
    document.getElementById('nn-score-msg').style.display = 'none';
}

// ── Score submission ──────────────────────────────────────────────────────────
async function saveScore(autoName = null) {
    const inp      = document.getElementById('nn-name-input');
    const btn      = document.getElementById('nn-save-btn');
    const scoreMsg = document.getElementById('nn-score-msg');
    const name     = autoName || inp?.value.trim();
    if (!name) { inp?.focus(); return; }

    if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }

    try {
        const r = await fetch('/api/nonosweeper-scores', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body:    JSON.stringify({
                name,
                puzzle_date: G.puzzleId,
                difficulty:  G.difficulty,
                time_secs:   Math.max(1, G.elapsed),
            }),
        });
        if (r.ok) {
            localStorage.setItem('nn_name', name);
            if (btn) btn.textContent = '✓ Saved!';
            scoreMsg.style.display = '';
            scoreMsg.textContent = `✅ Score saved for ${esc(name)}!`;
            loadLeaderboard();
        } else {
            if (btn) { btn.textContent = 'Error — retry'; btn.disabled = false; }
            scoreMsg.style.display = '';
            scoreMsg.textContent = '❌ Could not save score.';
        }
    } catch {
        if (btn) { btn.textContent = 'Error — retry'; btn.disabled = false; }
        scoreMsg.style.display = '';
        scoreMsg.textContent = '❌ Network error.';
    }
}

// ── Leaderboard ───────────────────────────────────────────────────────────────
async function loadLeaderboard() {
    if (!G.isPOTD) return;
    const el = document.getElementById('nn-lb-content');
    el.innerHTML = '<div class="lb-loading">Loading…</div>';

    try {
        const r    = await fetch(`/api/nonosweeper-scores/${G.puzzleId}?difficulty=${G.difficulty}`);
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
    const prevEl = document.getElementById('nn-prev-days');
    if (prevEl) {
        const links = [];
        for (let i = 1; i <= 7; i++) {
            const d   = new Date(Date.now() - i * 86400000);
            const iso = d.toISOString().slice(0, 10);
            const lbl = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
            links.push(`<a href="/nonosweeper/${iso}" class="nn-prev-day-link">${lbl}</a>`);
        }
        prevEl.innerHTML = `<span class="nn-prev-days-label">Previous puzzles:</span> ${links.join('')}`;
    }
}

function updatePermalinkAndTitle(seedStr, isPOTD) {
    const realToday = document.getElementById('nn-grid').dataset.realToday;
    const lbTitle   = document.getElementById('nn-lb-title');
    const permRow   = document.getElementById('nn-permalink-row');
    const permLink  = document.getElementById('nn-permalink-link');

    if (isPOTD) {
        if (lbTitle) lbTitle.textContent = seedStr === realToday
            ? '🏆 Today\'s Best Times'
            : `🏆 Best Times — ${seedStr}`;
        if (permRow && permLink) {
            permLink.href        = `/nonosweeper/${seedStr}`;
            permLink.textContent = `minesweeper.org/nonosweeper/${seedStr}`;
            permRow.style.display = 'block';
        }
    } else {
        if (permRow) permRow.style.display = 'none';
    }
}

function esc(s) {
    return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}

// ── Game init ─────────────────────────────────────────────────────────────────
function initGame(seedStr, isPOTD, difficulty) {
    clearInterval(G.timer);

    const puzzle = generatePuzzle(seedStr, difficulty);
    G = {
        ...puzzle,
        minesLeft:  puzzle.mines,
        startTime:  null,
        elapsed:    0,
        timer:      null,
        won:        false,
        over:       false,
        isPOTD,
        puzzleId:   seedStr,
        difficulty,
    };

    const ov = document.getElementById('nn-overlay');
    ov.style.display = 'none';
    ov.className     = '';

    document.getElementById('nn-timer').textContent      = '0:00';
    document.getElementById('nn-mines-left').textContent = G.mines;
    document.getElementById('nn-mode-label').textContent =
        isPOTD ? '📅 Puzzle of the Day' : '🎲 Random Puzzle';

    document.querySelectorAll('.nn-diff-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.diff === difficulty);
    });

    const lb = document.getElementById('nn-lb-section');
    lb.style.display = isPOTD ? 'block' : 'none';

    updatePermalinkAndTitle(seedStr, isPOTD);
    renderBoard();
    if (isPOTD) loadLeaderboard();
}

// ── Entry point ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const grid      = document.getElementById('nn-grid');
    const today     = grid.dataset.today;
    const realToday = grid.dataset.realToday;

    let currentDiff = localStorage.getItem('nn_difficulty') || 'beginner';

    function playPOTD(diff) {
        currentDiff = diff || currentDiff;
        localStorage.setItem('nn_difficulty', currentDiff);
        initGame(today, true, currentDiff);
    }

    function playRandom() {
        initGame(Date.now().toString(36) + Math.random().toString(36).slice(2, 6), false, currentDiff);
    }

    document.querySelectorAll('.nn-diff-btn').forEach(btn => {
        btn.addEventListener('click', () => playPOTD(btn.dataset.diff));
    });

    document.getElementById('nn-potd-btn').addEventListener('click', () => {
        initGame(realToday, true, currentDiff);
    });
    document.getElementById('nn-random-btn').addEventListener('click', playRandom);
    document.getElementById('nn-overlay-potd').addEventListener('click', () => {
        initGame(realToday, true, currentDiff);
    });
    document.getElementById('nn-overlay-random').addEventListener('click', playRandom);
    document.getElementById('nn-overlay-retry').addEventListener('click', () => {
        initGame(G.puzzleId, G.isPOTD, G.difficulty);
    });

    document.getElementById('nn-save-btn').addEventListener('click', () => saveScore());
    document.getElementById('nn-name-input').addEventListener('keydown', e => {
        if (e.key === 'Enter') saveScore();
    });

    playPOTD();
});
