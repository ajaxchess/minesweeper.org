'use strict';

const TMT_R_ADJ_COLORS = [
    '', '#1565c0', '#2e7d32', '#c62828',
    '#0d47a1', '#b71c1c', '#00695c', '#4a148c', '#424242',
];

let R = null;  // replay state
let rafId = null;
let playing = false;
let playbackSpeed = 1;
let currentTimeMs = 0;  // virtual elapsed ms in the game

function rNeighbors(r, c, rows, cols) {
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

function buildReplayState(data) {
    const { rows, cols, mines, bbbv, board_data } = data;
    const mineSet = new Set();
    for (const [r, c] of board_data.mines) mineSet.add(r * cols + c);

    const adj = new Int8Array(rows * cols);
    for (const [r, c] of board_data.mines)
        for (const [nr, nc] of rNeighbors(r, c, rows, cols)) {
            const ni = nr * cols + nc;
            if (!mineSet.has(ni)) adj[ni]++;
        }

    return {
        rows, cols, mines, bbbv,
        adj, mineSet,
        cells:        Array.from({ length: rows * cols }, () => ({ state: 'hidden' })),
        row_counts:   [...board_data.row_counts],
        col_counts:   [...board_data.col_counts],
        rowRemaining: [...board_data.row_counts],
        colRemaining: [...board_data.col_counts],
        log:          data.log,
        logPtr:       0,          // next unplayed log index
        durationMs:   data.time_ms || 0,
        outcome:      data.outcome,
        meta:         data,
    };
}

// ── Board simulation ──────────────────────────────────────────────────────────
function rFloodFill(startIdx) {
    const q = [startIdx];
    const seen = new Set();
    while (q.length) {
        const idx = q.pop();
        if (seen.has(idx)) continue;
        seen.add(idx);
        if (R.mineSet.has(idx)) continue;
        const cell = R.cells[idx];
        if (cell.state === 'revealed' || cell.state === 'flagged') continue;
        cell.state = 'revealed';
        if (R.adj[idx] === 0) {
            const r = Math.floor(idx / R.cols), c = idx % R.cols;
            for (const [nr, nc] of rNeighbors(r, c, R.rows, R.cols)) {
                const ni = nr * R.cols + nc;
                if (!seen.has(ni)) q.push(ni);
            }
        }
    }
}

function applyLogEntry([, type, r, c]) {
    const idx = r * R.cols + c;
    const cell = R.cells[idx];
    if (type === 'l') {
        if (cell.state !== 'hidden' && cell.state !== 'question') return;
        if (R.mineSet.has(idx)) { cell.state = 'exploded'; }
        else { rFloodFill(idx); }
    } else if (type === 'r') {
        if      (cell.state === 'hidden')   cell.state = 'flagged';
        else if (cell.state === 'flagged')  cell.state = 'question';
        else if (cell.state === 'question') cell.state = 'hidden';
    } else if (type === 'c') {
        const n = R.adj[idx];
        const nbs = rNeighbors(r, c, R.rows, R.cols);
        const flags = nbs.filter(([nr, nc]) => R.cells[nr * R.cols + nc].state === 'flagged').length;
        if (flags !== n) return;
        for (const [nr, nc] of nbs) {
            const ni = nr * R.cols + nc;
            const s = R.cells[ni].state;
            if (s !== 'hidden' && s !== 'question') continue;
            if (R.mineSet.has(ni)) R.cells[ni].state = 'exploded';
            else rFloodFill(ni);
        }
    }
}

// Rebuild board state up to targetMs by replaying from scratch
function rebuildUpTo(targetMs) {
    R.cells.forEach(c => { c.state = 'hidden'; });
    R.rowRemaining = [...R.row_counts];
    R.colRemaining = [...R.col_counts];
    R.logPtr = 0;

    for (let i = 0; i < R.log.length; i++) {
        if (R.log[i][0] > targetMs) break;
        applyLogEntry(R.log[i]);
        R.logPtr = i + 1;
    }
    recomputeRemaining();
}

function recomputeRemaining() {
    const rr = [...R.row_counts];
    const cr = [...R.col_counts];
    for (let i = 0; i < R.cells.length; i++) {
        if (R.cells[i].state === 'flagged') {
            rr[Math.floor(i / R.cols)]--;
            cr[i % R.cols]--;
        }
    }
    R.rowRemaining = rr;
    R.colRemaining = cr;
}

// ── Rendering ─────────────────────────────────────────────────────────────────
function renderCellEl(el, idx) {
    const cell = R.cells[idx];
    el.className = 'tmt-cell';
    el.textContent = '';
    el.style.color = '';
    switch (cell.state) {
        case 'hidden':   el.classList.add('tmt-hidden'); break;
        case 'flagged':  el.classList.add('tmt-flagged'); el.textContent = '🚩'; break;
        case 'question': el.classList.add('tmt-question'); el.textContent = '?'; break;
        case 'revealed': {
            el.classList.add('tmt-revealed');
            const n = R.adj[idx];
            if (n > 0) { el.textContent = n; el.style.color = TMT_R_ADJ_COLORS[n] || '#fff'; }
            break;
        }
        case 'exploded':     el.classList.add('tmt-exploded'); el.textContent = '💥'; break;
        case 'mine-revealed':el.classList.add('tmt-mine-revealed'); el.textContent = '💣'; break;
        case 'wrong-flag':   el.classList.add('tmt-wrong-flag'); el.textContent = '❌'; break;
    }
}

function renderFullBoard() {
    const grid = document.getElementById('tmt-grid');
    if (!grid) return;
    const cellSize = R.cols <= 10 ? 34 : R.cols <= 18 ? 30 : 24;
    grid.style.setProperty('--tmt-cols', R.cols);
    grid.style.setProperty('--tmt-cell-size', cellSize + 'px');
    grid.innerHTML = '';

    grid.appendChild(Object.assign(document.createElement('div'), { className: 'tmt-corner' }));
    for (let c = 0; c < R.cols; c++) {
        const el = document.createElement('div');
        el.className = 'tmt-col-hint';
        el.dataset.col = c;
        const rem = document.createElement('span');
        rem.className = 'tmt-remaining';
        rem.textContent = R.colRemaining[c];
        const tot = document.createElement('span');
        tot.className = 'tmt-total';
        tot.textContent = R.col_counts[c];
        el.append(rem, tot);
        if (R.colRemaining[c] === 0) el.classList.add('satisfied');
        grid.appendChild(el);
    }

    for (let r = 0; r < R.rows; r++) {
        const rowHint = document.createElement('div');
        rowHint.className = 'tmt-row-hint';
        rowHint.dataset.row = r;
        const rem = document.createElement('span');
        rem.className = 'tmt-remaining';
        rem.textContent = R.rowRemaining[r];
        const tot = document.createElement('span');
        tot.className = 'tmt-total';
        tot.textContent = R.row_counts[r];
        rowHint.append(rem, tot);
        if (R.rowRemaining[r] === 0) rowHint.classList.add('satisfied');
        grid.appendChild(rowHint);

        for (let c = 0; c < R.cols; c++) {
            const idx = r * R.cols + c;
            const el = document.createElement('div');
            el.className = 'tmt-cell';
            el.dataset.idx = idx;
            renderCellEl(el, idx);
            grid.appendChild(el);
        }
    }
}

function refreshCellEl(idx) {
    const el = document.querySelector(`.tmt-cell[data-idx="${idx}"]`);
    if (el) renderCellEl(el, idx);
}

function updateHintEls() {
    const grid = document.getElementById('tmt-grid');
    if (!grid) return;
    for (let r = 0; r < R.rows; r++) {
        const hint = grid.querySelector(`.tmt-row-hint[data-row="${r}"]`);
        if (!hint) continue;
        hint.querySelector('.tmt-remaining').textContent = R.rowRemaining[r];
        hint.classList.toggle('satisfied', R.rowRemaining[r] === 0);
    }
    for (let c = 0; c < R.cols; c++) {
        const hint = grid.querySelector(`.tmt-col-hint[data-col="${c}"]`);
        if (!hint) continue;
        hint.querySelector('.tmt-remaining').textContent = R.colRemaining[c];
        hint.classList.toggle('satisfied', R.colRemaining[c] === 0);
    }
}

// ── Timer display ─────────────────────────────────────────────────────────────
function fmtMs(ms) {
    const s = ms / 1000;
    const m = Math.floor(s / 60);
    const ss = (s % 60).toFixed(1);
    return m > 0 ? `${m}:${ss.padStart(4, '0')}` : `${ss}s`;
}

function updateTimerDisplay(ms) {
    const el = document.getElementById('tmt-r-timer');
    if (el) el.textContent = fmtMs(ms);
}

function updateScrubber(ms) {
    const sc = document.getElementById('tmt-r-scrubber');
    if (sc && R.durationMs > 0) sc.value = Math.round(ms / R.durationMs * 1000);
}

// ── Playback engine ───────────────────────────────────────────────────────────
let lastRafTime = null;

function playFrame(now) {
    if (!playing) return;
    if (lastRafTime != null) {
        const delta = (now - lastRafTime) * playbackSpeed;
        currentTimeMs = Math.min(currentTimeMs + delta, R.durationMs);
    }
    lastRafTime = now;

    // Apply all log entries up to currentTimeMs
    while (R.logPtr < R.log.length && R.log[R.logPtr][0] <= currentTimeMs) {
        const entry = R.log[R.logPtr];
        applyLogEntry(entry);
        R.logPtr++;

        // Re-render affected cells
        const [, type, r, c] = entry;
        const idx = r * R.cols + c;
        const needsFullRender = (type === 'c') ||
            (type === 'l' && !R.mineSet.has(idx) && R.adj[idx] === 0);
        if (needsFullRender) {
            for (let i = 0; i < R.cells.length; i++) refreshCellEl(i);
        } else {
            refreshCellEl(idx);
        }
        if (type === 'r') recomputeRemaining();
        updateHintEls();
    }

    updateTimerDisplay(currentTimeMs);
    updateScrubber(currentTimeMs);

    if (currentTimeMs >= R.durationMs) {
        // Reached end — show final state
        stopPlayback();
        showFinalState();
        return;
    }
    rafId = requestAnimationFrame(playFrame);
}

function showFinalState() {
    // If loss, reveal all mines
    if (R.outcome === 'loss') {
        R.cells.forEach((cell, idx) => {
            if (cell.state === 'exploded') return;
            if (R.mineSet.has(idx) && cell.state !== 'flagged') cell.state = 'mine-revealed';
            else if (!R.mineSet.has(idx) && cell.state === 'flagged') cell.state = 'wrong-flag';
        });
    }
    for (let i = 0; i < R.cells.length; i++) refreshCellEl(i);
    updateHintEls();
    setPlayBtn(false);
}

function startPlayback() {
    if (playing) return;
    if (currentTimeMs >= R.durationMs) {
        seekTo(0);
    }
    playing = true;
    lastRafTime = null;
    setPlayBtn(true);
    rafId = requestAnimationFrame(playFrame);
}

function stopPlayback() {
    playing = false;
    lastRafTime = null;
    if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
    setPlayBtn(false);
}

function togglePlayback() {
    if (playing) stopPlayback(); else startPlayback();
}

function setPlayBtn(isPlaying) {
    const btn = document.getElementById('tmt-r-play-btn');
    if (btn) btn.textContent = isPlaying ? '⏸ Pause' : '▶ Play';
}

function seekTo(ms) {
    stopPlayback();
    currentTimeMs = Math.max(0, Math.min(ms, R.durationMs));
    rebuildUpTo(currentTimeMs);
    // Re-render full board after seek
    for (let i = 0; i < R.cells.length; i++) refreshCellEl(i);
    updateHintEls();
    updateTimerDisplay(currentTimeMs);
    updateScrubber(currentTimeMs);
}

// ── Init ──────────────────────────────────────────────────────────────────────
async function initReplay(replayId) {
    const grid = document.getElementById('tmt-grid');
    if (grid) grid.innerHTML = '<div class="tmt-loading">Loading replay…</div>';

    let data;
    try {
        const resp = await fetch(`/api/tametsi/replay/${replayId}`);
        if (!resp.ok) throw new Error(resp.status);
        data = await resp.json();
    } catch (e) {
        if (grid) grid.innerHTML = '<div class="tmt-error">⚠️ Could not load replay.</div>';
        return;
    }

    if (!data.board_data) {
        if (grid) grid.innerHTML = '<div class="tmt-error">⚠️ Board data unavailable for this replay.</div>';
        return;
    }

    R = buildReplayState(data);
    renderFullBoard();
    updateTimerDisplay(0);

    // Populate stats
    const level = (data.mode || '').replace('tametsi-', '');
    const levLabel = level.charAt(0).toUpperCase() + level.slice(1);

    const titleEl = document.getElementById('tmt-r-title');
    if (titleEl) {
        const outcomeLabel = data.outcome === 'win' ? '✅ Win' : '💥 Loss';
        titleEl.textContent = `Tametsi ${levLabel} — ${outcomeLabel}`;
    }

    const totalMs = data.time_ms || 0;
    const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
    el('tmt-r-duration', fmtMs(totalMs));
    el('tmt-r-bbbv',     data.bbbv ?? '—');
    const totalClicks = (data.left_clicks || 0) + (data.right_clicks || 0) + (data.chord_clicks || 0);
    el('tmt-r-clicks',  totalClicks || '—');
    el('tmt-r-eff',     (data.bbbv && totalClicks) ? (data.bbbv / totalClicks * 100).toFixed(1) + '%' : '—');
    el('tmt-r-revealed', data.cells_revealed != null
        ? `${data.cells_revealed} / ${data.cells_total_safe}` : '—');

    const scrubber = document.getElementById('tmt-r-scrubber');
    if (scrubber) {
        scrubber.max = 1000;
        scrubber.value = 0;
        scrubber.addEventListener('input', () => {
            const ms = Math.round(parseInt(scrubber.value) / 1000 * R.durationMs);
            seekTo(ms);
        });
    }

    document.getElementById('tmt-r-play-btn')?.addEventListener('click', togglePlayback);
    document.getElementById('tmt-r-restart-btn')?.addEventListener('click', () => seekTo(0));

    const speedBtns = document.querySelectorAll('.tmt-r-speed-btn');
    speedBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            playbackSpeed = parseFloat(btn.dataset.speed);
            speedBtns.forEach(b => b.classList.toggle('active', b === btn));
        });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('tmt-grid');
    const replayId = grid?.dataset.replayId;
    if (replayId) initReplay(replayId);
});
