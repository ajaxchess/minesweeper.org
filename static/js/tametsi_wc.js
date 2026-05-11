'use strict';

// ── Adjacency colours (same palette as tametsi.js) ────────────────────────────
const WC_ADJ_COLORS = [
    '',         // 0 — blank
    '#1565c0',  // 1
    '#2e7d32',  // 2
    '#c62828',  // 3
    '#0d47a1',  // 4
    '#b71c1c',  // 5
    '#00695c',  // 6
    '#4a148c',  // 7
    '#424242',  // 8
];

function wcNeighbors(r, c, rows, cols) {
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

function wcBuildAdj(mineLayout, rows, cols) {
    const mineSet = new Set(mineLayout.map(([r, c]) => r * cols + c));
    const adj = new Int8Array(rows * cols);
    for (const [r, c] of mineLayout) {
        for (const [nr, nc] of wcNeighbors(r, c, rows, cols)) {
            const ni = nr * cols + nc;
            if (!mineSet.has(ni)) adj[ni]++;
        }
    }
    return { mineSet, adj };
}

// ── Touch handler ─────────────────────────────────────────────────────────────
function wcAddTouch(el, onTap, onLongPress) {
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

// ── Mount a single WC board ───────────────────────────────────────────────────
function wcMountBoard(wrap) {
    const country    = wrap.dataset.country;
    const difficulty = wrap.dataset.difficulty;
    const fanFlagImg = wrap.dataset.fanFlagImg;
    const primary    = wrap.dataset.primary;
    const secondary  = wrap.dataset.secondary;

    let board = JSON.parse(wrap.dataset.board);
    let { mineSet, adj } = wcBuildAdj(board.mine_layout, board.rows, board.cols);
    let busy = false;

    // ── DOM skeleton ──────────────────────────────────────────────────────────
    wrap.innerHTML = '';

    const uid = `wc-${difficulty}`;

    const zoneBar = document.createElement('div');
    zoneBar.className = 'wc-zone-bar';
    wrap.appendChild(zoneBar);

    const grid = document.createElement('div');
    grid.className = 'wc-tmt-grid';
    grid.id = `${uid}-grid`;
    wrap.appendChild(grid);

    const msgBanner = document.createElement('div');
    msgBanner.className = 'wc-msg-banner';
    msgBanner.id = `${uid}-msg`;
    msgBanner.style.display = 'none';
    wrap.appendChild(msgBanner);

    // ── Zone bar ──────────────────────────────────────────────────────────────
    function updateZoneBar() {
        const flagged = board.cells.filter(s => s === 'flagged').length;
        zoneBar.innerHTML = `
            <span class="wc-zone-chip" style="background:${primary};color:${contrastColor(primary)}">
                <span class="wc-zone-label">Primary</span>
                <span class="wc-zone-count" id="${uid}-pr">${board.primary_remaining}</span>
            </span>
            <span class="wc-zone-chip" style="background:${secondary};color:${contrastColor(secondary)}">
                <span class="wc-zone-label">Secondary</span>
                <span class="wc-zone-count" id="${uid}-sc">${board.secondary_remaining}</span>
            </span>
            <span class="wc-flag-count">${flagged} / ${board.mines} mines flagged</span>
        `;
    }

    function contrastColor(hex) {
        const r = parseInt(hex.slice(1,3), 16);
        const g = parseInt(hex.slice(3,5), 16);
        const b = parseInt(hex.slice(5,7), 16);
        return (r * 299 + g * 587 + b * 114) / 1000 >= 128 ? '#111' : '#fff';
    }

    // ── Cell rendering ────────────────────────────────────────────────────────
    function renderCell(el, idx) {
        const state = board.cells[idx];
        const r = Math.floor(idx / board.cols);
        const zoneColor = r < board.top_rows ? primary : secondary;
        const textColor = contrastColor(zoneColor);

        el.className = 'wc-cell';
        el.dataset.idx = idx;
        el.textContent = '';
        el.style.cssText = '';

        switch (state) {
            case 'hidden':
                el.classList.add('wc-cell-hidden');
                el.style.background = zoneColor;
                break;

            case 'flagged':
                el.classList.add('wc-cell-flagged');
                el.style.background = zoneColor;
                if (fanFlagImg) {
                    const img = document.createElement('img');
                    img.src = `https://flagcdn.com/w20/${fanFlagImg}.png`;
                    img.alt = '';
                    img.className = 'wc-flag-img';
                    el.appendChild(img);
                } else {
                    el.textContent = '🚩';
                }
                break;

            case 'revealed': {
                el.classList.add('wc-cell-revealed');
                const n = adj[idx];
                if (n > 0) {
                    el.textContent = n;
                    el.style.color = WC_ADJ_COLORS[n] || '#333';
                }
                break;
            }

            case 'exploded':
                el.classList.add('wc-cell-exploded');
                el.textContent = '💥';
                break;
        }
    }

    // ── Full board render ─────────────────────────────────────────────────────
    function renderBoard() {
        const { rows, cols } = board;
        const cellSize = cols <= 15 ? 30 : cols <= 20 ? 26 : 22;
        grid.style.setProperty('--wc-cols', cols);
        grid.style.setProperty('--wc-cell-size', cellSize + 'px');
        grid.innerHTML = '';

        // Corner spacer
        grid.appendChild(Object.assign(document.createElement('div'), { className: 'wc-corner' }));

        // Column hints
        for (let c = 0; c < cols; c++) {
            const el = document.createElement('div');
            el.className = 'wc-col-hint';
            el.dataset.col = c;
            const rem = document.createElement('span');
            rem.className = 'wc-h-rem';
            rem.textContent = board.col_remaining[c];
            const tot = document.createElement('span');
            tot.className = 'wc-h-tot';
            tot.textContent = board.col_counts[c];
            el.append(rem, tot);
            if (board.col_remaining[c] === 0) el.classList.add('wc-hint-sat');
            grid.appendChild(el);
            el.addEventListener('click', () => {
                const pinned = el.classList.toggle('wc-pinned');
                for (let row = 0; row < rows; row++) {
                    const cell = grid.querySelector(`.wc-cell[data-idx="${row * cols + c}"]`);
                    if (cell) cell.classList.toggle('wc-col-hl', pinned);
                }
            });
        }

        // Rows
        for (let r = 0; r < rows; r++) {
            const rowHint = document.createElement('div');
            rowHint.className = 'wc-row-hint';
            rowHint.dataset.row = r;
            const rem = document.createElement('span');
            rem.className = 'wc-h-rem';
            rem.textContent = board.row_remaining[r];
            const tot = document.createElement('span');
            tot.className = 'wc-h-tot';
            tot.textContent = board.row_counts[r];
            rowHint.append(rem, tot);
            if (board.row_remaining[r] === 0) rowHint.classList.add('wc-hint-sat');
            grid.appendChild(rowHint);
            rowHint.addEventListener('click', () => {
                const pinned = rowHint.classList.toggle('wc-pinned');
                for (let c = 0; c < cols; c++) {
                    const cell = grid.querySelector(`.wc-cell[data-idx="${r * cols + c}"]`);
                    if (cell) cell.classList.toggle('wc-row-hl', pinned);
                }
            });

            for (let c = 0; c < cols; c++) {
                const idx = r * cols + c;
                const el = document.createElement('div');
                el.dataset.idx = idx;
                renderCell(el, idx);
                el.addEventListener('click',       () => handleReveal(idx));
                el.addEventListener('contextmenu', e => { e.preventDefault(); handleFlag(idx); });
                wcAddTouch(el, () => handleReveal(idx), () => handleFlag(idx));
                grid.appendChild(el);
            }
        }

        updateZoneBar();
    }

    // ── Refresh board from API response ───────────────────────────────────────
    function applyBoardUpdate(data) {
        board = data;
        ({ mineSet, adj } = wcBuildAdj(board.mine_layout, board.rows, board.cols));

        for (let idx = 0; idx < board.rows * board.cols; idx++) {
            const el = grid.querySelector(`.wc-cell[data-idx="${idx}"]`);
            if (el) renderCell(el, idx);
        }

        for (let r = 0; r < board.rows; r++) {
            const hint = grid.querySelector(`.wc-row-hint[data-row="${r}"]`);
            if (!hint) continue;
            hint.querySelector('.wc-h-rem').textContent = board.row_remaining[r];
            hint.classList.toggle('wc-hint-sat', board.row_remaining[r] === 0);
        }
        for (let c = 0; c < board.cols; c++) {
            const hint = grid.querySelector(`.wc-col-hint[data-col="${c}"]`);
            if (!hint) continue;
            hint.querySelector('.wc-h-rem').textContent = board.col_remaining[c];
            hint.classList.toggle('wc-hint-sat', board.col_remaining[c] === 0);
        }

        updateZoneBar();
    }

    // ── Interaction ───────────────────────────────────────────────────────────
    async function handleReveal(idx) {
        if (busy || board.is_solved) return;
        if (board.cells[idx] !== 'hidden') return;
        busy = true;
        try {
            const res = await fetch(`/api/wc2026/board/${country}/${difficulty}/reveal`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ idx }),
            });
            if (!res.ok) return;
            const data = await res.json();
            applyBoardUpdate(data);
            if (data.hit_mine) {
                showMsg('💥 Oops — you clicked a mine! You can still flag the rest and solve.', 'wc-msg-warn');
            } else {
                checkAutoSolve();
            }
        } finally {
            busy = false;
        }
    }

    async function handleFlag(idx) {
        if (busy || board.is_solved) return;
        if (board.cells[idx] === 'revealed' || board.cells[idx] === 'exploded') return;
        busy = true;
        try {
            const res = await fetch(`/api/wc2026/board/${country}/${difficulty}/flag`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ idx }),
            });
            if (!res.ok) return;
            const data = await res.json();
            applyBoardUpdate(data);
            checkAutoSolve();
        } finally {
            busy = false;
        }
    }

    function checkAutoSolve() {
        if (board.primary_remaining === 0 &&
            board.secondary_remaining === 0 &&
            board.cells.filter(s => s === 'flagged').length === board.mines) {
            doSolve();
        }
    }

    async function doSolve() {
        const res = await fetch(`/api/wc2026/board/${country}/${difficulty}/solve`, {
            method: 'POST',
        });
        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            showMsg(`Could not submit solve: ${data.error || res.status}`, 'wc-msg-warn');
            return;
        }
        const data = await res.json();
        if (data.ok) showSolvedBanner(data);
    }

    function showSolvedBanner(result) {
        msgBanner.className = 'wc-msg-banner wc-msg-solved';
        msgBanner.innerHTML = `
            <div class="wc-solved-trophy">🏆</div>
            <div class="wc-solved-text">
                <strong>Board Solved!</strong><br>
                +${result.flags_correct} flags &nbsp;+${result.solve_bonus} bonus
                = <strong>${result.total_points} pts</strong> for your team
            </div>
        `;
        msgBanner.style.display = 'flex';
        board.is_solved = true;
    }

    function showMsg(text, cls) {
        msgBanner.className = `wc-msg-banner ${cls}`;
        msgBanner.textContent = text;
        msgBanner.style.display = '';
        setTimeout(() => { if (msgBanner.textContent === text) msgBanner.style.display = 'none'; }, 4000);
    }

    renderBoard();
}

// ── CSS injected once ─────────────────────────────────────────────────────────
(function injectStyles() {
    if (document.getElementById('wc-tmt-styles')) return;
    const s = document.createElement('style');
    s.id = 'wc-tmt-styles';
    s.textContent = `
.wc-zone-bar {
    display: flex;
    align-items: center;
    gap: .6rem;
    margin-bottom: .5rem;
    flex-wrap: wrap;
}
.wc-zone-chip {
    display: inline-flex;
    align-items: center;
    gap: .35rem;
    border-radius: 4px;
    padding: .2rem .5rem;
    font-size: .8rem;
    font-weight: 600;
    border: 1px solid rgba(0,0,0,.15);
}
.wc-zone-label { opacity: .8; font-weight: 400; }
.wc-zone-count { font-size: 1rem; }
.wc-flag-count { color: var(--text-dim); font-size: .85rem; }

.wc-tmt-grid {
    display: grid;
    grid-template-columns: auto repeat(var(--wc-cols), var(--wc-cell-size));
    gap: 1px;
    width: fit-content;
    max-width: 100%;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
}
.wc-corner { width: var(--wc-cell-size); height: var(--wc-cell-size); }
.wc-col-hint, .wc-row-hint {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-size: .65rem;
    line-height: 1.1;
    cursor: pointer;
    border-radius: 3px;
    padding: 1px;
    color: var(--text-dim);
    user-select: none;
}
.wc-col-hint { width: var(--wc-cell-size); min-height: var(--wc-cell-size); }
.wc-row-hint { min-width: var(--wc-cell-size); height: var(--wc-cell-size); }
.wc-h-rem { font-weight: 700; color: var(--text); }
.wc-h-tot { color: var(--text-dim); }
.wc-hint-sat .wc-h-rem { color: #4caf50; }
.wc-pinned { outline: 2px solid #f5c518; }
.wc-col-hl, .wc-row-hl { outline: 2px solid rgba(245,197,24,.5) !important; }

.wc-cell {
    width: var(--wc-cell-size);
    height: var(--wc-cell-size);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: .75rem;
    font-weight: 700;
    border-radius: 2px;
    cursor: pointer;
    user-select: none;
    box-sizing: border-box;
    border: 1px solid rgba(0,0,0,.15);
    transition: filter .1s;
    position: relative;
    overflow: hidden;
}
.wc-cell-hidden {
    /* dim zone color so white zones become clearly visible as unclicked */
    filter: brightness(0.82);
}
.wc-cell-hidden:hover  { filter: brightness(0.95); }
.wc-cell-hidden:active { filter: brightness(0.70); }
.wc-cell-revealed {
    /* neutral page color — always distinct from zone colors in all themes */
    background: var(--cell-rev, #c8c8c8);
    border-color: var(--border, #aaa);
    font-size: .8rem;
    cursor: default;
}
.wc-cell-flagged { cursor: default; }
.wc-flag-img {
    width: 70%;
    height: 70%;
    object-fit: contain;
    pointer-events: none;
}
.wc-cell-exploded {
    background: #c00 !important;
    border-color: #900 !important;
    font-size: 1rem;
}

.wc-msg-banner {
    margin-top: .6rem;
    padding: .6rem .9rem;
    border-radius: 6px;
    font-size: .9rem;
    align-items: center;
    gap: .6rem;
}
.wc-msg-warn {
    background: rgba(255,160,0,.15);
    border: 1px solid rgba(255,160,0,.4);
    color: var(--text);
}
.wc-msg-solved {
    background: rgba(0,180,0,.12);
    border: 1px solid rgba(0,180,0,.35);
    color: var(--text);
}
.wc-solved-trophy { font-size: 2rem; }
.wc-solved-text { line-height: 1.5; }
    `;
    document.head.appendChild(s);
}());

// ── Init all boards on page ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.wc-tmt-wrap').forEach(wcMountBoard);
});
