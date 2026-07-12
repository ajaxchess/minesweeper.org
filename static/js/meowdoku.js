"use strict";

// ── RNG (same as tentaizu.js) ─────────────────────────────────────────────────
function mulberry32(a) {
    return function () {
        a = 1831565813 + (a |= 0) | 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = t + Math.imul(t ^ (t >>> 7), 61 | t) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}
function strSeed(s) {
    let h = 2166136261;
    for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
    return h;
}

// ── Region palette (10 colors, one per possible region) ───────────────────────
const RC = ['#c0392b','#d35400','#c9a227','#27ae60','#16a085','#2980b9','#8e44ad','#c0185e','#795548','#546e7a'];
const RC_TEXT = ['#fff','#fff','#222','#fff','#fff','#fff','#fff','#fff','#fff','#fff'];

// ── Grid helpers ──────────────────────────────────────────────────────────────
function nb4(idx, n) {
    const r = (idx / n) | 0, c = idx % n, res = [];
    if (r > 0)     res.push(idx - n);
    if (r < n - 1) res.push(idx + n);
    if (c > 0)     res.push(idx - 1);
    if (c < n - 1) res.push(idx + 1);
    return res;
}
function shuffleArr(arr, rng) {
    for (let i = arr.length - 1; i > 0; i--) {
        const j = (rng() * (i + 1)) | 0;
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
}

// ── Puzzle generation ─────────────────────────────────────────────────────────
function genPlacement(n, rng) {
    const cols = [], used = new Set();
    function bt(row) {
        if (row === n) return true;
        const order = shuffleArr(Array.from({length: n}, (_, i) => i), rng);
        for (const c of order) {
            if (used.has(c)) continue;
            if (row > 0 && Math.abs(cols[row - 1] - c) <= 1) continue;
            cols.push(c); used.add(c);
            if (bt(row + 1)) return true;
            cols.pop(); used.delete(c);
        }
        return false;
    }
    return bt(0) ? cols : null;
}

function genRegions(n, catCols, rng) {
    const total = n * n;
    const grid = new Int8Array(total).fill(-1);
    for (let r = 0; r < n; r++) grid[r * n + catCols[r]] = r;

    // BFS flood-fill seeded from cat positions
    const visited = new Uint8Array(total);
    for (let r = 0; r < n; r++) visited[r * n + catCols[r]] = 1;

    const frontier = [];
    for (let r = 0; r < n; r++) {
        const seed = r * n + catCols[r];
        for (const nb of nb4(seed, n)) if (!visited[nb]) frontier.push(seed * total + nb);
    }
    shuffleArr(frontier, rng);

    let fi = 0;
    while (fi < frontier.length) {
        const entry = frontier[fi++];
        const parent = (entry / total) | 0;
        const cell   = entry % total;
        if (visited[cell]) continue;
        visited[cell] = 1;
        grid[cell] = grid[parent];
        for (const nb of nb4(cell, n)) {
            if (!visited[nb]) frontier.push(cell * total + nb);
        }
    }

    // Safety: assign any remaining cells to an adjacent region
    let changed = true;
    while (changed) {
        changed = false;
        for (let i = 0; i < total; i++) {
            if (grid[i] !== -1) continue;
            for (const nb of nb4(i, n)) {
                if (grid[nb] !== -1) { grid[i] = grid[nb]; changed = true; break; }
            }
        }
    }
    return grid;
}

function isLogicSolvable(n, regions, catCols) {
    const possible = new Uint8Array(n * n).fill(1);
    const pR = new Set(), pC = new Set(), pReg = new Set();

    function elim(r, c) {
        if (r >= 0 && r < n && c >= 0 && c < n) possible[r * n + c] = 0;
    }
    function place(r, c) {
        pR.add(r); pC.add(c); pReg.add(regions[r * n + c]);
        for (let j = 0; j < n; j++) elim(r, j);
        for (let i = 0; i < n; i++) elim(i, c);
        for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (regions[i*n+j] === regions[r*n+c]) elim(i,j);
        for (let dr = -1; dr <= 1; dr++) for (let dc = -1; dc <= 1; dc++) elim(r+dr, c+dc);
    }

    let progress = true;
    while (progress && pReg.size < n) {
        progress = false;
        for (let reg = 0; reg < n; reg++) {
            if (pReg.has(reg)) continue;
            const cells = [];
            for (let i = 0; i < n; i++) for (let j = 0; j < n; j++)
                if (regions[i*n+j] === reg && possible[i*n+j]) cells.push([i,j]);
            if (cells.length === 0) return false;
            if (cells.length === 1) { place(cells[0][0], cells[0][1]); progress = true; }
        }
        for (let i = 0; i < n; i++) {
            if (pR.has(i)) continue;
            const cells = [];
            for (let j = 0; j < n; j++) if (possible[i*n+j]) cells.push([i,j]);
            if (cells.length === 0) return false;
            if (cells.length === 1) { place(cells[0][0], cells[0][1]); progress = true; }
        }
        for (let j = 0; j < n; j++) {
            if (pC.has(j)) continue;
            const cells = [];
            for (let i = 0; i < n; i++) if (possible[i*n+j]) cells.push([i,j]);
            if (cells.length === 0) return false;
            if (cells.length === 1) { place(cells[0][0], cells[0][1]); progress = true; }
        }
    }
    return pReg.size === n;
}

function generatePuzzle(dateStr, size) {
    const base = strSeed(dateStr + '-' + size);
    for (let attempt = 0; attempt < 500; attempt++) {
        const rng = mulberry32((base + attempt * 31337) >>> 0);
        const catCols = genPlacement(size, rng);
        if (!catCols) continue;
        const regions = genRegions(size, catCols, rng);
        if (Array.from(regions).includes(-1)) continue;
        if (isLogicSolvable(size, regions, catCols)) return {regions, catCols};
    }
    // Fallback (should not be reached for sizes ≤10)
    const rng0 = mulberry32(base);
    const catCols = genPlacement(size, rng0) || Array.from({length: size}, (_, i) => i);
    return {regions: genRegions(size, catCols, rng0), catCols};
}

// ── Board hash (nibble-packed base64url) ──────────────────────────────────────
function boardHash(regions, n) {
    const bytes = new Uint8Array(1 + Math.ceil(regions.length / 2));
    bytes[0] = n;
    for (let i = 0; i < regions.length; i += 2)
        bytes[1 + (i >> 1)] = ((regions[i] & 0xf) << 4) | (i + 1 < regions.length ? regions[i + 1] & 0xf : 0);
    return btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

function decodeBoard(hash) {
    try {
        const padded = hash.replace(/-/g, '+').replace(/_/g, '/');
        const pad = (4 - padded.length % 4) % 4;
        const bytes = Uint8Array.from(atob(padded + '==='.slice(0, pad)), c => c.charCodeAt(0));
        const n = bytes[0];
        if (n < 4 || n > 10) return null;
        const regions = new Int8Array(n * n);
        for (let i = 0; i < regions.length; i++)
            regions[i] = i % 2 === 0 ? (bytes[1 + (i >> 1)] >> 4) & 0xf : bytes[1 + (i >> 1)] & 0xf;
        return {n, regions};
    } catch {
        return null;
    }
}

// Solve a board by backtracking — returns catCols or null
function solveBoard(n, regions) {
    const cols = new Array(n).fill(-1);
    const usedC = new Set(), usedReg = new Set();
    function bt(row) {
        if (row === n) return true;
        for (let c = 0; c < n; c++) {
            if (usedC.has(c)) continue;
            if (row > 0 && Math.abs(cols[row - 1] - c) <= 1) continue;
            const reg = regions[row * n + c];
            if (usedReg.has(reg)) continue;
            cols[row] = c; usedC.add(c); usedReg.add(reg);
            if (bt(row + 1)) return true;
            cols[row] = -1; usedC.delete(c); usedReg.delete(reg);
        }
        return false;
    }
    return bt(0) ? cols : null;
}

// ── State ─────────────────────────────────────────────────────────────────────
const G = {
    n: 8,
    regions: null,
    catCols: null,
    marks: null,        // 0=empty 1=x 2=cat
    solved: false,
    elapsed: 0,
    startTime: null,
    timer: null,
    puzzleId: '',
    isDaily: true,
    boardHashStr: '',
    mode: 'x',          // 'x'→cycle empty→X→cat; 'cat'→cycle empty→cat→X
};

// CYCLE_X[current] = next;  CYCLE_CAT[current] = next
const CYCLE_X   = [1, 2, 0];   // empty→X→cat→empty
const CYCLE_CAT = [2, 0, 1];   // empty→cat→X→empty  (tap-once lands on cat)

// ── Timer ─────────────────────────────────────────────────────────────────────
function startTimer() {
    if (G.timer) return;
    G.startTime = Date.now() - G.elapsed * 1000;
    G.timer = setInterval(() => {
        G.elapsed = Math.floor((Date.now() - G.startTime) / 1000);
        const el = document.getElementById('mk-timer');
        if (el) el.textContent = fmtTime(G.elapsed);
    }, 500);
}
function stopTimer() {
    clearInterval(G.timer); G.timer = null;
    if (G.startTime) G.elapsed = Math.floor((Date.now() - G.startTime) / 1000);
}
function fmtTime(s) { return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; }

// ── Rendering ─────────────────────────────────────────────────────────────────
function renderBoard() {
    const grid = document.getElementById('mk-grid');
    if (!grid) return;
    const n = G.n;
    grid.style.setProperty('--mk-n', n);
    grid.innerHTML = '';

    for (let i = 0; i < n * n; i++) {
        const r = (i / n) | 0, c = i % n;
        const reg = G.regions[i];
        const el = document.createElement('div');
        el.className = 'mk-cell';
        el.dataset.idx = i;
        el.style.backgroundColor = RC[reg];

        // Thick region borders
        if (r === 0    || G.regions[i - n] !== reg) el.classList.add('mk-bt');
        if (r === n-1  || G.regions[i + n] !== reg) el.classList.add('mk-bb');
        if (c === 0    || G.regions[i - 1] !== reg) el.classList.add('mk-bl');
        if (c === n-1  || G.regions[i + 1] !== reg) el.classList.add('mk-br');

        el.addEventListener('click', () => handleClick(i));
        el.addEventListener('contextmenu', e => { e.preventDefault(); handleRightClick(i); });
        grid.appendChild(el);
    }
    refreshAll();
}

function refreshAll() {
    const conflicts = getConflicts();
    for (let i = 0; i < G.n * G.n; i++) refreshCell(i, conflicts);
}

function refreshCell(idx, conflicts) {
    const el = document.querySelector(`#mk-grid .mk-cell[data-idx="${idx}"]`);
    if (!el) return;
    const m = G.marks[idx];
    el.classList.remove('mk-mark-x', 'mk-mark-cat', 'mk-conflict');
    el.textContent = '';
    if (m === 1) { el.classList.add('mk-mark-x'); el.textContent = '✕'; }
    else if (m === 2) {
        el.classList.add('mk-mark-cat');
        el.textContent = '🐱';
        if (conflicts && conflicts.has(idx)) el.classList.add('mk-conflict');
    }
}

function getConflicts() {
    const n = G.n;
    const cats = [];
    for (let i = 0; i < n * n; i++) if (G.marks[i] === 2) cats.push(i);
    const bad = new Set();
    for (let a = 0; a < cats.length; a++) {
        for (let b = a + 1; b < cats.length; b++) {
            const ai = cats[a], bi = cats[b];
            const ar = (ai/n)|0, ac = ai%n, br = (bi/n)|0, bc = bi%n;
            if (ar===br || ac===bc || G.regions[ai]===G.regions[bi] ||
                (Math.abs(ar-br)<=1 && Math.abs(ac-bc)<=1)) {
                bad.add(ai); bad.add(bi);
            }
        }
    }
    return bad;
}

function updateCatCounter() {
    const el = document.getElementById('mk-cat-count');
    if (!el) return;
    const placed = Array.from(G.marks).filter(m => m === 2).length;
    el.textContent = placed;
}

// ── Interaction ───────────────────────────────────────────────────────────────
function handleClick(idx) {
    if (G.solved) return;
    if (!G.startTime) startTimer();
    const cur = G.marks[idx];
    G.marks[idx] = G.mode === 'x' ? CYCLE_X[cur] : CYCLE_CAT[cur];
    refreshCell(idx, getConflicts());
    updateCatCounter();
    checkWin();
}

function handleRightClick(idx) {
    if (G.solved) return;
    if (!G.startTime) startTimer();
    G.marks[idx] = G.marks[idx] === 2 ? 0 : 2;
    refreshCell(idx, getConflicts());
    updateCatCounter();
    checkWin();
}

function toggleMode() {
    G.mode = G.mode === 'x' ? 'cat' : 'x';
    const btn = document.getElementById('mk-mode-toggle');
    if (!btn) return;
    btn.textContent = G.mode === 'x' ? '✕ X-mode' : '🐱 Cat-mode';
    btn.classList.toggle('mk-mode-cat', G.mode === 'cat');
}

// ── Win detection ─────────────────────────────────────────────────────────────
function checkWin() {
    const n = G.n;
    const cats = [];
    for (let i = 0; i < n * n; i++) if (G.marks[i] === 2) cats.push(i);
    if (cats.length !== n) return;

    // Every region must have exactly one cat
    const regCats = new Set(cats.map(i => G.regions[i]));
    if (regCats.size !== n) return;

    // No conflicts
    if (getConflicts().size > 0) return;

    // All cats match the solution
    for (const ci of cats) {
        const r = (ci / n) | 0, c = ci % n;
        if (G.catCols[r] !== c) return;
    }

    G.solved = true;
    stopTimer();
    if (G.isDaily && typeof window.questsHook === 'function') window.questsHook('meowdoku_solved');
    showWinOverlay();
}

function showWinOverlay() {
    const overlay = document.getElementById('mk-overlay');
    if (!overlay) return;
    overlay.style.display = 'flex';
    document.getElementById('mk-win-time').textContent = fmtTime(G.elapsed);

    const form = document.getElementById('mk-score-form');
    const username = document.getElementById('mk-board').dataset.username || '';
    if (G.isDaily) {
        if (username) {
            form.style.display = 'none';
            const msg = document.createElement('div');
            msg.id = 'mk-score-msg'; msg.className = 'mk-score-msg';
            msg.textContent = 'Saving score…';
            overlay.insertBefore(msg, overlay.querySelector('.mk-overlay-btns'));
            saveScore(username);
        } else {
            form.style.display = 'flex';
            const nameInput = document.getElementById('mk-name-input');
            nameInput.value = localStorage.getItem('mk_name') || '';
            const saveBtn = document.getElementById('mk-save-btn');
            saveBtn.disabled = false;
            saveBtn.textContent = 'Save Score';
        }
    } else {
        form.style.display = 'none';
    }
}

async function saveScore(nameOverride) {
    const nameInput = document.getElementById('mk-name-input');
    const saveBtn   = document.getElementById('mk-save-btn');
    const name = nameOverride || nameInput?.value.trim();
    if (!name) { nameInput?.focus(); return; }

    if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Saving…'; }
    try {
        const resp = await fetch('/api/meowdoku-scores', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
            body: JSON.stringify({
                name,
                puzzle_date: G.puzzleId,
                grid_size:   G.n,
                time_secs:   Math.max(1, G.elapsed),
                board_hash:  G.boardHashStr,
            }),
        });
        if (resp.ok) {
            localStorage.setItem('mk_name', name);
            if (saveBtn) saveBtn.textContent = '✓ Saved!';
            const msg = document.getElementById('mk-score-msg');
            if (msg) msg.textContent = `✅ Score saved for ${name}!`;
            loadLeaderboard();
        } else {
            if (saveBtn) { saveBtn.textContent = 'Error — retry'; saveBtn.disabled = false; }
        }
    } catch {
        if (saveBtn) { saveBtn.textContent = 'Error — retry'; saveBtn.disabled = false; }
    }
}

// ── Leaderboard ───────────────────────────────────────────────────────────────
async function loadLeaderboard() {
    if (!G.isDaily) return;
    const section = document.getElementById('mk-lb-section');
    const content = document.getElementById('mk-lb-content');
    if (!section || !content) return;
    section.style.display = 'block';

    const title = document.getElementById('mk-lb-title');
    const realToday = document.getElementById('mk-board').dataset.realToday;
    if (title) title.textContent = G.puzzleId === realToday
        ? `🏆 Today's Best — ${G.n}×${G.n}`
        : `🏆 Best Times — ${G.puzzleId} (${G.n}×${G.n})`;

    content.innerHTML = '<div class="lb-loading">Loading…</div>';
    try {
        const r = await fetch(`/api/meowdoku-scores/${G.puzzleId}?size=${G.n}`);
        const data = await r.json();
        if (!data.length) { content.innerHTML = '<div class="lb-empty">No scores yet — be the first!</div>'; return; }
        const rows = data.map((e, i) => `
            <tr class="${i % 2 ? 'lb-even' : ''}">
                <td class="lb-rank">${i + 1}</td>
                <td class="lb-name">${e.profile_url
                    ? `<a href="${esc(e.profile_url)}" class="lb-profile-link">${esc(e.name)}</a>`
                    : esc(e.name)}</td>
                <td class="lb-time">${fmtTime(e.time_secs)}</td>
            </tr>`).join('');
        content.innerHTML = `<div class="lb-table-wrap"><table class="lb-table">
            <thead><tr><th>#</th><th>Name</th><th>Time</th></tr></thead>
            <tbody>${rows}</tbody></table></div>`;
    } catch {
        content.innerHTML = '<div class="lb-empty">⚠️ Could not load scores.</div>';
    }

    // Previous day links
    const prev = document.getElementById('mk-prev-days');
    if (prev) {
        const links = [];
        for (let d = 1; d <= 7; d++) {
            const dt = new Date(Date.now() - 86400000 * d);
            const iso = dt.toISOString().slice(0, 10);
            const label = dt.toLocaleDateString(undefined, {month: 'short', day: 'numeric'});
            links.push(`<a href="/meowdoku?date=${iso}&size=${G.n}" class="tz-prev-day-link">${label}</a>`);
        }
        prev.innerHTML = `<span class="tz-prev-days-label">Previous puzzles:</span> ${links.join('')}`;
    }
}

function esc(s) {
    return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}

// ── Init ──────────────────────────────────────────────────────────────────────
function initGame(dateStr, size, isDaily, customBoardHash) {
    clearInterval(G.timer);
    G.n       = size;
    G.solved  = false;
    G.elapsed = 0;
    G.startTime = null;
    G.timer   = null;
    G.puzzleId = dateStr;
    G.isDaily = isDaily;
    G.mode    = 'x';

    if (customBoardHash) {
        const decoded = decodeBoard(customBoardHash);
        if (decoded) {
            G.n = decoded.n;
            G.regions = decoded.regions;
            G.catCols = solveBoard(G.n, G.regions);
            G.boardHashStr = customBoardHash;
        } else {
            customBoardHash = null;
        }
    }

    if (!customBoardHash) {
        const puzzle = generatePuzzle(dateStr, size);
        G.regions = puzzle.regions;
        G.catCols = puzzle.catCols;
        G.boardHashStr = boardHash(G.regions, G.n);
    }

    G.marks = new Uint8Array(G.n * G.n);

    // UI resets
    const overlay = document.getElementById('mk-overlay');
    if (overlay) overlay.style.display = 'none';
    const timer = document.getElementById('mk-timer');
    if (timer) timer.textContent = '0:00';
    const modeBtn = document.getElementById('mk-mode-toggle');
    if (modeBtn) { modeBtn.textContent = '✕ X-mode'; modeBtn.classList.remove('mk-mode-cat'); }
    const lbSection = document.getElementById('mk-lb-section');
    if (lbSection) lbSection.style.display = isDaily ? 'block' : 'none';

    renderBoard();
    updateCatCounter();
    if (isDaily) loadLeaderboard();
}

document.addEventListener('DOMContentLoaded', () => {
    const board = document.getElementById('mk-board');
    if (!board) return;

    const today      = board.dataset.today;
    const realToday  = board.dataset.realToday;
    const sizeParsed = parseInt(board.dataset.size, 10) || 8;
    const customHash = board.dataset.customBoard || '';

    initGame(today, sizeParsed, !customHash, customHash || null);

    // Size buttons
    document.querySelectorAll('.mk-size-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const sz = parseInt(btn.dataset.size, 10);
            document.querySelectorAll('.mk-size-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const newUrl = new URL(window.location.href);
            newUrl.searchParams.set('size', sz);
            newUrl.searchParams.delete('date');
            window.history.pushState({}, '', newUrl.toString());
            initGame(realToday, sz, true, null);
        });
    });

    // Mark the active size button
    document.querySelectorAll('.mk-size-btn').forEach(b => {
        if (parseInt(b.dataset.size, 10) === sizeParsed) b.classList.add('active');
    });

    document.getElementById('mk-mode-toggle')?.addEventListener('click', toggleMode);
    document.getElementById('mk-save-btn')?.addEventListener('click', () => saveScore(null));
    document.getElementById('mk-name-input')?.addEventListener('keydown', e => { if (e.key === 'Enter') saveScore(null); });
    document.getElementById('mk-overlay-replay')?.addEventListener('click', () => initGame(realToday, G.n, true, null));
});
