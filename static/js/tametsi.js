'use strict';

// ── Adjacency number colours (standard minesweeper palette) ──────────────────
const TMT_ADJ_COLORS = [
    '',         // 0 — blank
    '#1565c0',  // 1 — blue
    '#2e7d32',  // 2 — green
    '#c62828',  // 3 — red
    '#0d47a1',  // 4 — dark blue
    '#b71c1c',  // 5 — dark red
    '#00695c',  // 6 — teal
    '#4a148c',  // 7 — purple
    '#424242',  // 8 — dark grey
];

// ── Game state ────────────────────────────────────────────────────────────────
let G = null;

// ── Helpers ───────────────────────────────────────────────────────────────────
function esc(s) {
    return String(s).replace(/[&<>"]/g,
        c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

function neighbors(r, c, rows, cols) {
    const out = [];
    for (let dr = -1; dr <= 1; dr++)
        for (let dc = -1; dc <= 1; dc++) {
            if (dr === 0 && dc === 0) continue;
            const nr = r + dr, nc = c + dc;
            if (nr >= 0 && nr < rows && nc >= 0 && nc < cols)
                out.push([nr, nc]);
        }
    return out;
}

// ── Board fetch ───────────────────────────────────────────────────────────────
async function fetchBoard(level, isDaily, hash) {
    let url;
    if (hash)         url = `/api/tametsi/board/${hash}`;
    else if (isDaily) url = `/api/tametsi/daily/${level}`;
    else              url = `/api/tametsi/random/${level}`;
    const r = await fetch(url);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
}

// ── State initialisation ──────────────────────────────────────────────────────
function makeState(data, level, isDaily) {
    const { board_hash, rows, cols, mines: numMines, bbbv, board_data } = data;

    // Build adjacency counts and mine set from board_data
    const mineSet = new Set();
    for (const [r, c] of board_data.mines) mineSet.add(r * cols + c);

    const adj = new Int8Array(rows * cols);
    for (const [r, c] of board_data.mines) {
        for (const [nr, nc] of neighbors(r, c, rows, cols)) {
            const ni = nr * cols + nc;
            if (!mineSet.has(ni)) adj[ni]++;
        }
    }

    return {
        board_hash, rows, cols,
        mines: numMines, bbbv,
        adj, mineSet,
        cells: Array.from({ length: rows * cols }, () => ({ state: 'hidden' })),
        row_counts:    [...board_data.row_counts],
        col_counts:    [...board_data.col_counts],
        rowRemaining:  [...board_data.row_counts],
        colRemaining:  [...board_data.col_counts],
        minesLeft:     numMines,
        started:       false,
        over:          false,
        won:           false,
        startTime:     null,
        elapsedMs:     0,
        timer:         null,
        level,
        isDaily,
    };
}

// ── Timer ─────────────────────────────────────────────────────────────────────
function startTimer() {
    if (G.timer) return;
    G.startTime = performance.now() - G.elapsedMs;
    G.timer = setInterval(() => {
        G.elapsedMs = performance.now() - G.startTime;
        const s = Math.floor(G.elapsedMs / 1000);
        const m = Math.floor(s / 60);
        const el = document.getElementById('tmt-timer');
        if (el) el.textContent = `${m}:${String(s % 60).padStart(2, '0')}`;
    }, 100);
}

function stopTimer() {
    clearInterval(G.timer);
    G.timer = null;
    if (G.startTime != null) G.elapsedMs = performance.now() - G.startTime;
}

// ── Hint updates ──────────────────────────────────────────────────────────────
function recomputeRemaining() {
    const rr = [...G.row_counts];
    const cr = [...G.col_counts];
    for (let i = 0; i < G.cells.length; i++) {
        if (G.cells[i].state === 'flagged') {
            rr[Math.floor(i / G.cols)]--;
            cr[i % G.cols]--;
        }
    }
    G.rowRemaining = rr;
    G.colRemaining = cr;
}

function updateHintEls() {
    const grid = document.getElementById('tmt-grid');
    if (!grid) return;
    for (let r = 0; r < G.rows; r++) {
        const hint = grid.querySelector(`.tmt-row-hint[data-row="${r}"]`);
        if (!hint) continue;
        hint.querySelector('.tmt-remaining').textContent = G.rowRemaining[r];
        hint.classList.toggle('satisfied', G.rowRemaining[r] === 0);
    }
    for (let c = 0; c < G.cols; c++) {
        const hint = grid.querySelector(`.tmt-col-hint[data-col="${c}"]`);
        if (!hint) continue;
        hint.querySelector('.tmt-remaining').textContent = G.colRemaining[c];
        hint.classList.toggle('satisfied', G.colRemaining[c] === 0);
    }
}

// ── Mine counter ──────────────────────────────────────────────────────────────
function updateMineCounter() {
    const flagged = G.cells.filter(c => c.state === 'flagged').length;
    G.minesLeft = G.mines - flagged;
    const el = document.getElementById('tmt-mines-left');
    if (el) el.textContent = G.minesLeft;
}

// ── Cell rendering ────────────────────────────────────────────────────────────
function renderCellEl(el, idx) {
    const cell = G.cells[idx];
    const r = Math.floor(idx / G.cols);
    const c = idx % G.cols;
    const isStart = (r === 0 && c === 0);

    el.className = 'tmt-cell';
    el.textContent = '';
    el.style.color = '';

    switch (cell.state) {
        case 'hidden':
            el.classList.add('tmt-hidden');
            if (isStart && !G.started) {
                el.classList.add('tmt-start-marker');
                el.textContent = '✕';
            }
            break;
        case 'flagged':
            el.classList.add('tmt-flagged');
            el.textContent = '🚩';
            break;
        case 'question':
            el.classList.add('tmt-question');
            el.textContent = '?';
            break;
        case 'revealed': {
            el.classList.add('tmt-revealed');
            const n = G.adj[idx];
            if (n > 0) {
                el.textContent = n;
                el.style.color = TMT_ADJ_COLORS[n] || '#fff';
            }
            break;
        }
        case 'exploded':
            el.classList.add('tmt-exploded');
            el.textContent = '💥';
            break;
        case 'mine-revealed':
            el.classList.add('tmt-mine-revealed');
            el.textContent = '💣';
            break;
        case 'wrong-flag':
            el.classList.add('tmt-wrong-flag');
            el.textContent = '❌';
            break;
    }
}

function refreshCell(idx) {
    const grid = document.getElementById('tmt-grid');
    const el = grid?.querySelector(`.tmt-cell[data-idx="${idx}"]`);
    if (el) renderCellEl(el, idx);
}

// ── Touch handler ─────────────────────────────────────────────────────────────
function addTouchHandlers(el, onTap, onLongPress) {
    let timer = null, moved = false, sx, sy;
    el.addEventListener('touchstart', e => {
        if (e.touches.length > 1) { clearTimeout(timer); timer = null; return; }
        e.preventDefault();
        moved = false;
        sx = e.touches[0].clientX; sy = e.touches[0].clientY;
        timer = setTimeout(() => { timer = null; if (!moved) onLongPress(); }, 500);
    }, { passive: false });
    el.addEventListener('touchmove', e => {
        if (!timer) return;
        if (Math.abs(e.touches[0].clientX - sx) > 10 ||
            Math.abs(e.touches[0].clientY - sy) > 10) {
            moved = true; clearTimeout(timer); timer = null;
        }
    }, { passive: true });
    el.addEventListener('touchend', e => {
        e.preventDefault();
        if (timer) { clearTimeout(timer); timer = null; if (!moved) onTap(); }
    }, { passive: false });
    el.addEventListener('touchcancel', () => { clearTimeout(timer); timer = null; });
}

// ── Board rendering ───────────────────────────────────────────────────────────
function renderBoard() {
    const grid = document.getElementById('tmt-grid');
    if (!grid) return;

    // Responsive cell size
    const cellSize = G.cols <= 10 ? 34 : G.cols <= 18 ? 30 : 24;
    grid.style.setProperty('--tmt-cols', G.cols);
    grid.style.setProperty('--tmt-cell-size', cellSize + 'px');
    grid.innerHTML = '';

    // Corner spacer
    grid.appendChild(Object.assign(document.createElement('div'), { className: 'tmt-corner' }));

    // Column hint headers
    for (let c = 0; c < G.cols; c++) {
        const el = document.createElement('div');
        el.className = 'tmt-col-hint';
        el.dataset.col = c;
        const rem = document.createElement('span');
        rem.className = 'tmt-remaining';
        rem.textContent = G.colRemaining[c];
        const tot = document.createElement('span');
        tot.className = 'tmt-total';
        tot.textContent = G.col_counts[c];
        el.append(rem, tot);
        if (G.colRemaining[c] === 0) el.classList.add('satisfied');
        grid.appendChild(el);
    }

    // Rows: hint + cells
    for (let r = 0; r < G.rows; r++) {
        // Row hint
        const rowHint = document.createElement('div');
        rowHint.className = 'tmt-row-hint';
        rowHint.dataset.row = r;
        const rem = document.createElement('span');
        rem.className = 'tmt-remaining';
        rem.textContent = G.rowRemaining[r];
        const tot = document.createElement('span');
        tot.className = 'tmt-total';
        tot.textContent = G.row_counts[r];
        rowHint.append(rem, tot);
        if (G.rowRemaining[r] === 0) rowHint.classList.add('satisfied');
        grid.appendChild(rowHint);

        // Cells
        for (let c = 0; c < G.cols; c++) {
            const idx = r * G.cols + c;
            const el = document.createElement('div');
            el.className = 'tmt-cell';
            el.dataset.idx = idx;
            renderCellEl(el, idx);
            el.addEventListener('click',       () => handleClick(idx));
            el.addEventListener('contextmenu', e => { e.preventDefault(); handleRightClick(idx); });
            addTouchHandlers(el, () => handleClick(idx), () => handleRightClick(idx));
            grid.appendChild(el);
        }
    }

    // Show start hint, hide play hint
    const startHint = document.getElementById('tmt-start-hint');
    const playHint  = document.getElementById('tmt-play-hint');
    if (startHint) startHint.style.display = '';
    if (playHint)  playHint.style.display  = 'none';
}

// ── Flood fill reveal ─────────────────────────────────────────────────────────
function floodFill(startIdx) {
    const q = [startIdx];
    const seen = new Set();
    while (q.length) {
        const idx = q.pop();
        if (seen.has(idx)) continue;
        seen.add(idx);
        if (G.mineSet.has(idx)) continue;
        const cell = G.cells[idx];
        if (cell.state === 'revealed' || cell.state === 'flagged') continue;
        cell.state = 'revealed';
        refreshCell(idx);
        if (G.adj[idx] === 0) {
            const r = Math.floor(idx / G.cols);
            const c = idx % G.cols;
            for (const [nr, nc] of neighbors(r, c, G.rows, G.cols)) {
                const ni = nr * G.cols + nc;
                if (!seen.has(ni)) q.push(ni);
            }
        }
    }
}

// ── Interaction ───────────────────────────────────────────────────────────────
function handleClick(idx) {
    if (G.over || G.won) return;
    const r = Math.floor(idx / G.cols);
    const c = idx % G.cols;
    const cell = G.cells[idx];

    if (!G.started) {
        // Only (0,0) is clickable before the game begins
        if (r !== 0 || c !== 0) return;
        G.started = true;
        startTimer();
        floodFill(0);

        // Flip instruction hints
        const startHint = document.getElementById('tmt-start-hint');
        const playHint  = document.getElementById('tmt-play-hint');
        if (startHint) startHint.style.display = 'none';
        if (playHint)  playHint.style.display  = '';

        checkWin();
        return;
    }

    if (cell.state !== 'hidden' && cell.state !== 'question') return;

    if (G.mineSet.has(idx)) {
        cell.state = 'exploded';
        G.over = true;
        stopTimer();
        refreshCell(idx);
        revealAllAfterLoss();
        showOverlay('lose');
        return;
    }

    floodFill(idx);
    checkWin();
}

function handleRightClick(idx) {
    if (G.over || G.won) return;
    const cell = G.cells[idx];
    if (cell.state === 'revealed') return;

    if      (cell.state === 'hidden')   cell.state = 'flagged';
    else if (cell.state === 'flagged')  cell.state = 'question';
    else                                cell.state = 'hidden';

    refreshCell(idx);
    recomputeRemaining();
    updateHintEls();
    updateMineCounter();
    if (G.started) checkWin();
}

function revealAllAfterLoss() {
    G.cells.forEach((cell, idx) => {
        if (cell.state === 'exploded') return;
        if (G.mineSet.has(idx) && cell.state !== 'flagged') {
            cell.state = 'mine-revealed';
            refreshCell(idx);
        } else if (!G.mineSet.has(idx) && cell.state === 'flagged') {
            cell.state = 'wrong-flag';
            refreshCell(idx);
        }
    });
}

// ── Win check ─────────────────────────────────────────────────────────────────
function checkWin() {
    const allSafe  = G.cells.every((cell, idx) => G.mineSet.has(idx) || cell.state === 'revealed');
    const allMines = G.cells.every((cell, idx) => !G.mineSet.has(idx) || cell.state === 'flagged');
    if (!allSafe && !allMines) return;

    G.won = true;
    stopTimer();

    // Auto-flag any remaining mines
    G.cells.forEach((cell, idx) => {
        if (G.mineSet.has(idx) && cell.state !== 'flagged') {
            cell.state = 'flagged';
            refreshCell(idx);
        }
    });
    recomputeRemaining();
    updateHintEls();
    updateMineCounter();
    showOverlay('win');
}

// ── Overlay ───────────────────────────────────────────────────────────────────
function showOverlay(type) {
    const ov = document.getElementById('tmt-overlay');
    if (!ov) return;
    ov.className = type;
    ov.style.display = 'flex';

    const title    = document.getElementById('tmt-overlay-title');
    const timeRow  = document.getElementById('tmt-overlay-time-row');
    const winTime  = document.getElementById('tmt-win-time');
    const form     = document.getElementById('tmt-score-form');
    const scoreMsg = document.getElementById('tmt-score-msg');

    if (type === 'win') {
        if (title) title.textContent = '🎉 Solved!';
        if (timeRow) timeRow.style.display = '';
        const ms = Math.round(G.elapsedMs);
        if (winTime) {
            const sTotal = ms / 1000;
            const m = Math.floor(sTotal / 60);
            const s = (sTotal % 60).toFixed(3);
            winTime.textContent = m > 0 ? `${m}:${s.padStart(6, '0')}` : `${s}s`;
        }

        // 3BV display
        const bbbvRow  = document.getElementById('tmt-win-bbbv-row');
        const bbbvEl   = document.getElementById('tmt-win-bbbv');
        const bbbvsEl  = document.getElementById('tmt-win-bbbvs');
        if (bbbvRow) {
            bbbvRow.style.display = '';
            if (bbbvEl) bbbvEl.textContent = G.bbbv ?? '—';
            if (bbbvsEl) {
                bbbvsEl.textContent = (G.bbbv && ms > 0)
                    ? (G.bbbv / (ms / 1000)).toFixed(3)
                    : '—';
            }
        }
        const username = document.getElementById('tmt-grid')?.dataset.username || '';
        if (username) {
            if (form) form.style.display = 'none';
            if (scoreMsg) { scoreMsg.style.display = ''; scoreMsg.textContent = 'Saving score…'; }
            saveScore(username, ms);
        } else {
            if (form) form.style.display = 'flex';
            if (scoreMsg) scoreMsg.style.display = 'none';
            const inp = document.getElementById('tmt-name-input');
            if (inp) inp.value = localStorage.getItem('tmt_name') || '';
        }
    } else {
        if (title) title.textContent = '💥 Mine hit!';
        if (timeRow) timeRow.style.display = 'none';
        const bbbvRow = document.getElementById('tmt-win-bbbv-row');
        if (bbbvRow) bbbvRow.style.display = 'none';
        if (form) form.style.display = 'none';
        if (scoreMsg) scoreMsg.style.display = 'none';
    }
}

// ── Share link / permalink ─────────────────────────────────────────────────────
function updatePermalink() {
    const row  = document.getElementById('tmt-permalink-row');
    const link = document.getElementById('tmt-permalink-link');
    if (!row || !link || !G) return;
    const path = `/tametsi/board/${G.board_hash}`;
    link.href        = path;
    link.textContent = `minesweeper.org${path}`;
    row.style.display = '';
}

// ── Score submission ──────────────────────────────────────────────────────────
async function saveScore(autoName, timeMs) {
    const inp      = document.getElementById('tmt-name-input');
    const btn      = document.getElementById('tmt-save-btn');
    const scoreMsg = document.getElementById('tmt-score-msg');
    const name     = autoName || inp?.value.trim();
    if (!name) { inp?.focus(); return; }

    if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }

    try {
        const r = await fetch('/api/tametsi/scores', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body:    JSON.stringify({
                board_hash: G.board_hash,
                level:      G.level,
                is_daily:   G.isDaily,
                name,
                time_ms:    Math.round(timeMs ?? G.elapsedMs),
                bbbv:       G.bbbv,
            }),
        });
        if (r.ok) {
            localStorage.setItem('tmt_name', name);
            if (btn) btn.textContent = '✓ Saved!';
            if (scoreMsg) { scoreMsg.style.display = ''; scoreMsg.textContent = `✅ Score saved for ${esc(name)}!`; }
            loadLeaderboard();
        } else {
            if (btn) { btn.disabled = false; btn.textContent = 'Error — retry'; }
            if (scoreMsg) { scoreMsg.style.display = ''; scoreMsg.textContent = '❌ Could not save score.'; }
        }
    } catch {
        if (btn) { btn.disabled = false; btn.textContent = 'Error — retry'; }
        if (scoreMsg) { scoreMsg.style.display = ''; scoreMsg.textContent = '❌ Network error.'; }
    }
}

// ── Leaderboard (F79-F) ───────────────────────────────────────────────────────
async function loadLeaderboard() {
    const section  = document.getElementById('tmt-lb-section');
    const content  = document.getElementById('tmt-lb-content');
    const title    = document.getElementById('tmt-lb-title');
    const subtitle = document.getElementById('tmt-lb-subtitle');
    if (!section || !content || !G) return;

    section.style.display = '';
    const lvlLabel = G.level.charAt(0).toUpperCase() + G.level.slice(1);

    if (G.isDaily) {
        if (title)    title.textContent    = `🏆 Today's Best — ${lvlLabel}`;
        if (subtitle) subtitle.textContent = new Date().toISOString().slice(0, 10);
    } else {
        if (title)    title.textContent    = `🏆 This Board's Best`;
        if (subtitle) subtitle.textContent = `${lvlLabel} · #${G.board_hash.slice(0, 8)}…`;
    }
    content.innerHTML = '<div class="lb-loading">Loading…</div>';

    const url = G.isDaily
        ? `/api/tametsi/leaderboard/${G.level}`
        : `/api/tametsi/leaderboard/board/${G.board_hash}`;

    try {
        const r = await fetch(url);
        if (!r.ok) throw new Error(r.status);
        const data = await r.json();
        if (!Array.isArray(data) || !data.length) {
            content.innerHTML = '<div class="lb-empty">No scores yet — be the first!</div>';
            return;
        }
        const medals = ['🥇', '🥈', '🥉'];
        const rows = data.map((s, i) => {
            const nameCell = s.profile_url
                ? `<a href="${esc(s.profile_url)}" class="lb-profile-link">${esc(s.name)}</a>`
                : esc(s.name);
            const ms = s.time_ms;
            const m  = Math.floor(ms / 60000);
            const timeStr = m > 0
                ? `${m}:${((ms % 60000) / 1000).toFixed(3).padStart(6, '0')}`
                : (ms / 1000).toFixed(3) + 's';
            const bbbvs = (s.bbbv && ms > 0) ? (s.bbbv / (ms / 1000)).toFixed(2) : '—';
            return `<tr class="${i < 3 ? 'top-' + (i + 1) : ''}">
                <td class="lb-rank">${medals[i] ?? i + 1}</td>
                <td class="lb-name">${nameCell}</td>
                <td class="lb-time">${timeStr}</td>
                <td class="lb-stat">${s.bbbv ?? '—'}</td>
                <td class="lb-stat">${bbbvs}</td>
            </tr>`;
        }).join('');
        content.innerHTML = `
            <div class="lb-table-wrap">
              <table class="lb-table">
                <thead><tr><th>#</th><th>Name</th><th>Time</th><th>3BV</th><th>3BV/s</th></tr></thead>
                <tbody>${rows}</tbody>
              </table>
            </div>`;
    } catch {
        content.innerHTML = '<div class="lb-empty">⚠️ Could not load scores.</div>';
    }
}

// ── Game initialisation ───────────────────────────────────────────────────────
async function initGame(level, isDaily, boardHash) {
    const grid = document.getElementById('tmt-grid');
    if (!grid) return;

    if (G?.timer) clearInterval(G.timer);
    G = null;

    const ov = document.getElementById('tmt-overlay');
    if (ov) { ov.style.display = 'none'; ov.className = ''; }

    grid.innerHTML = '<div class="tmt-loading">Loading…</div>';
    document.getElementById('tmt-timer').textContent     = '0:00';
    document.getElementById('tmt-mines-left').textContent = '—';

    // Sync UI labels
    const modeLabel = document.getElementById('tmt-mode-label');
    if (modeLabel) modeLabel.textContent = isDaily ? '📅 Daily' : '🎲 Random';

    document.querySelectorAll('.tmt-mode-btn').forEach(btn =>
        btn.classList.toggle('active', btn.dataset.mode === (isDaily ? 'daily' : 'random')));
    document.querySelectorAll('.tmt-diff-btn').forEach(btn =>
        btn.classList.toggle('active', btn.dataset.diff === level));

    const lbSection = document.getElementById('tmt-lb-section');
    if (lbSection) lbSection.style.display = 'none';

    try {
        const data = await fetchBoard(level, isDaily, boardHash || null);
        G = makeState(data, level, isDaily);
        renderBoard();
        updateMineCounter();
        updatePermalink();
        loadLeaderboard();
    } catch (e) {
        grid.innerHTML = `<div class="tmt-error">⚠️ Could not load board. <button onclick="initGame('${esc(level)}',${isDaily})">Retry</button></div>`;
    }
}

// ── Entry point ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('tmt-grid');
    if (!grid) return;

    const initialHash  = grid.dataset.initialHash || '';
    let currentLevel   = localStorage.getItem('tmt_level') || 'beginner';
    let currentMode    = localStorage.getItem('tmt_mode')  || 'daily';

    function playDaily(level) {
        currentLevel = level || currentLevel;
        currentMode  = 'daily';
        localStorage.setItem('tmt_level', currentLevel);
        localStorage.setItem('tmt_mode',  'daily');
        initGame(currentLevel, true, null);
    }

    function playRandom(level) {
        currentLevel = level || currentLevel;
        currentMode  = 'random';
        localStorage.setItem('tmt_level', currentLevel);
        localStorage.setItem('tmt_mode',  'random');
        initGame(currentLevel, false, null);
    }

    // Mode toggle buttons
    document.querySelectorAll('.tmt-mode-btn').forEach(btn =>
        btn.addEventListener('click', () =>
            btn.dataset.mode === 'daily' ? playDaily(currentLevel) : playRandom(currentLevel)));

    // Difficulty buttons
    document.querySelectorAll('.tmt-diff-btn').forEach(btn =>
        btn.addEventListener('click', () => {
            currentLevel = btn.dataset.diff;
            localStorage.setItem('tmt_level', currentLevel);
            currentMode === 'daily' ? playDaily(currentLevel) : playRandom(currentLevel);
        }));

    // Overlay buttons
    document.getElementById('tmt-overlay-retry')?.addEventListener('click', () => {
        if (G) initGame(G.level, G.isDaily, G.isDaily ? null : G.board_hash);
    });
    document.getElementById('tmt-overlay-daily')?.addEventListener('click',  () => playDaily(currentLevel));
    document.getElementById('tmt-overlay-random')?.addEventListener('click', () => playRandom(currentLevel));

    // Copy share link
    document.getElementById('tmt-copy-btn')?.addEventListener('click', () => {
        if (!G) return;
        const url = `https://minesweeper.org/tametsi/board/${G.board_hash}`;
        navigator.clipboard?.writeText(url).then(() => {
            const btn = document.getElementById('tmt-copy-btn');
            if (btn) { btn.textContent = '✓'; setTimeout(() => { btn.textContent = '📋'; }, 1500); }
        }).catch(() => {
            // Fallback: select the link text
            const link = document.getElementById('tmt-permalink-link');
            if (link) { const r = document.createRange(); r.selectNode(link); window.getSelection()?.removeAllRanges(); window.getSelection()?.addRange(r); }
        });
    });

    // Score form
    document.getElementById('tmt-save-btn')?.addEventListener('click', () => {
        if (G) saveScore(null, Math.round(G.elapsedMs));
    });
    document.getElementById('tmt-name-input')?.addEventListener('keydown', e => {
        if (e.key === 'Enter' && G) saveScore(null, Math.round(G.elapsedMs));
    });

    // Initial load
    if (initialHash) {
        initGame(currentLevel, false, initialHash);
    } else {
        currentMode === 'random' ? playRandom(currentLevel) : playDaily(currentLevel);
    }
});
