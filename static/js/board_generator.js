'use strict';

// ── State ─────────────────────────────────────────────────────────────────────
const BG = {
    rows:  9,
    cols:  9,
    mines: new Set(),
    mask:  new Set(),
};

// ── Hash encode ───────────────────────────────────────────────────────────────
function encodeHash(rows, cols, cells) {
    const n     = rows * cols;
    const bytes = new Uint8Array(Math.ceil(n / 8));
    for (const idx of cells) {
        bytes[idx >> 3] |= 1 << (idx & 7);
    }
    let bin = '';
    bytes.forEach(b => bin += String.fromCharCode(b));
    return btoa(bin);
}

// ── Topology neighbor functions ───────────────────────────────────────────────
function stdNeighbors(r, c, rows, cols) {
    const out = [];
    for (let dr = -1; dr <= 1; dr++)
        for (let dc = -1; dc <= 1; dc++) {
            if (dr === 0 && dc === 0) continue;
            const nr = r + dr, nc = c + dc;
            if (nr >= 0 && nr < rows && nc >= 0 && nc < cols) out.push([nr, nc]);
        }
    return out;
}

function cylNeighbors(r, c, rows, cols) {
    const out = [];
    for (let dr = -1; dr <= 1; dr++)
        for (let dc = -1; dc <= 1; dc++) {
            if (dr === 0 && dc === 0) continue;
            const nr = r + dr, nc = (c + dc + cols) % cols;
            if (nr >= 0 && nr < rows) out.push([nr, nc]);
        }
    return out;
}

function torNeighbors(r, c, rows, cols) {
    const out = [];
    for (let dr = -1; dr <= 1; dr++)
        for (let dc = -1; dc <= 1; dc++) {
            if (dr === 0 && dc === 0) continue;
            const nr = (r + dr + rows) % rows, nc = (c + dc + cols) % cols;
            out.push([nr, nc]);
        }
    return out;
}

// ── Board + 3BV ───────────────────────────────────────────────────────────────
function buildBoard(rows, cols, mines, neighborFn) {
    const board = Array.from({ length: rows }, () => Array(cols).fill(0));
    for (const idx of mines) {
        const r = Math.floor(idx / cols), c = idx % cols;
        board[r][c] = -1;
        neighborFn(r, c, rows, cols).forEach(([nr, nc]) => {
            if (board[nr][nc] !== -1) board[nr][nc]++;
        });
    }
    return board;
}

function calc3BV(board, rows, cols, mines, neighborFn) {
    const n       = rows * cols;
    const covered = new Uint8Array(n);
    let   bbbv    = 0;

    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            const idx = r * cols + c;
            if (board[r][c] !== 0 || covered[idx] || mines.has(idx)) continue;
            bbbv++;
            const queue = [[r, c]];
            covered[idx] = 1;
            while (queue.length) {
                const [cr, cc] = queue.shift();
                for (const [nr, nc] of neighborFn(cr, cc, rows, cols)) {
                    const ni = nr * cols + nc;
                    if (covered[ni] || mines.has(ni)) continue;
                    covered[ni] = 1;
                    if (board[nr][nc] === 0) queue.push([nr, nc]);
                }
            }
        }
    }
    for (let i = 0; i < n; i++) {
        const r = Math.floor(i / cols), c = i % cols;
        if (board[r][c] > 0 && !covered[i]) bbbv++;
    }
    return bbbv;
}

// ── Update stats panel ────────────────────────────────────────────────────────
function updateStats() {
    const { rows, cols, mines, mask } = BG;
    const mineCount = mines.size;
    document.getElementById('bg-mine-count').textContent = mineCount;

    // Show/hide mask section
    const maskWrap = document.getElementById('bg-mask-wrap');
    if (maskWrap) maskWrap.style.display = mineCount > 0 ? 'block' : 'none';

    if (mineCount > 0) {
        const hash = encodeHash(rows, cols, mines);
        document.getElementById('bg-hash').textContent = hash;

        const stdBoard = buildBoard(rows, cols, mines, stdNeighbors);
        const cylBoard = buildBoard(rows, cols, mines, cylNeighbors);
        const torBoard = buildBoard(rows, cols, mines, torNeighbors);

        document.getElementById('bg-3bv-std').textContent =
            calc3BV(stdBoard, rows, cols, mines, stdNeighbors);
        document.getElementById('bg-3bv-cyl').textContent =
            calc3BV(cylBoard, rows, cols, mines, cylNeighbors);
        document.getElementById('bg-3bv-tor').textContent =
            calc3BV(torBoard, rows, cols, mines, torNeighbors);

        const enc       = encodeURIComponent(hash);
        const maskHash  = mask.size > 0 ? encodeHash(rows, cols, mask) : null;
        const replayUrl = `/variants/replay/?rows=${rows}&cols=${cols}&mines=${mineCount}&hash=${enc}`;
        const mosaicUrl = `/mosaic/custom/?rows=${rows}&cols=${cols}&hash=${enc}` +
                          (maskHash ? `&mask=${encodeURIComponent(maskHash)}` : '');

        const replayLink = document.getElementById('bg-replay-link');
        replayLink.href        = replayUrl;
        replayLink.textContent = replayUrl;

        const mosaicLink = document.getElementById('bg-mosaic-link');
        mosaicLink.href        = mosaicUrl;
        mosaicLink.textContent = mosaicUrl;

        document.getElementById('bg-urls').style.display = 'block';

        // Update mask stats
        document.getElementById('bg-mask-count').textContent = mask.size;
        const maskHashSection = document.getElementById('bg-mask-hash-section');
        if (maskHashSection) {
            maskHashSection.style.display = mask.size > 0 ? 'block' : 'none';
            if (mask.size > 0) {
                document.getElementById('bg-mask-hash').textContent = maskHash;
            }
        }
    } else {
        document.getElementById('bg-hash').textContent = '(place mines to generate)';
        document.getElementById('bg-3bv-std').textContent = '—';
        document.getElementById('bg-3bv-cyl').textContent = '—';
        document.getElementById('bg-3bv-tor').textContent = '—';
        document.getElementById('bg-urls').style.display = 'none';
    }
}

// ── Render mine grid ───────────────────────────────────────────────────────────
function renderGrid() {
    const { rows, cols, mines } = BG;
    const grid = document.getElementById('bg-grid');
    grid.style.gridTemplateColumns = `repeat(${cols}, 34px)`;
    grid.innerHTML = '';

    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            const idx  = r * cols + c;
            const cell = document.createElement('div');
            cell.className   = 'bg-cell' + (mines.has(idx) ? ' bg-mine' : '');
            cell.dataset.idx = idx;
            cell.textContent = mines.has(idx) ? '💣' : '';
            cell.addEventListener('click', () => toggleMine(idx));
            grid.appendChild(cell);
        }
    }
    updateStats();
    renderMaskGrid();
}

function toggleMine(idx) {
    if (BG.mines.has(idx)) {
        BG.mines.delete(idx);
    } else {
        BG.mines.add(idx);
        BG.mask.delete(idx); // mine cells cannot be masked
    }
    const cell = document.querySelector(`#bg-grid .bg-cell[data-idx="${idx}"]`);
    if (cell) {
        cell.classList.toggle('bg-mine', BG.mines.has(idx));
        cell.textContent = BG.mines.has(idx) ? '💣' : '';
    }
    updateStats();
    renderMaskGrid();
}

// ── Render mask grid ───────────────────────────────────────────────────────────
function renderMaskGrid() {
    const { rows, cols, mines, mask } = BG;
    const grid = document.getElementById('bg-mask-grid');
    if (!grid) return;

    grid.style.gridTemplateColumns = `repeat(${cols}, 34px)`;
    grid.innerHTML = '';

    if (mines.size === 0) return;

    // Use standard topology to compute mosaic numbers
    const board = buildBoard(rows, cols, mines, stdNeighbors);

    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            const idx  = r * cols + c;
            const cell = document.createElement('div');
            cell.dataset.idx = idx;

            if (mines.has(idx)) {
                cell.className   = 'bg-cell bg-mine';
                cell.textContent = '💣';
            } else {
                const num    = board[r][c]; // mosaic neighbor count (0–8)
                const masked = mask.has(idx);
                cell.className   = 'bg-cell bg-mask-cell' + (masked ? ' bg-masked' : '');
                cell.textContent = String(num);
                cell.addEventListener('click', () => toggleMask(idx));
            }
            grid.appendChild(cell);
        }
    }
}

function toggleMask(idx) {
    if (BG.mines.has(idx)) return;
    if (BG.mask.has(idx)) BG.mask.delete(idx);
    else                   BG.mask.add(idx);
    renderMaskGrid();
    updateStats();
}

function clearMask() {
    BG.mask = new Set();
    renderMaskGrid();
    updateStats();
}

// ── Apply size ────────────────────────────────────────────────────────────────
function applySize() {
    const rows = parseInt(document.getElementById('bg-rows').value) || 9;
    const cols = parseInt(document.getElementById('bg-cols').value) || 9;
    BG.rows  = Math.max(2, Math.min(30, rows));
    BG.cols  = Math.max(2, Math.min(50, cols));
    BG.mines = new Set();
    BG.mask  = new Set();
    renderGrid();
}

function clearBoard() {
    BG.mines = new Set();
    BG.mask  = new Set();
    renderGrid();
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('bg-apply').addEventListener('click', applySize);
    document.getElementById('bg-clear').addEventListener('click', clearBoard);
    document.getElementById('bg-mask-clear')?.addEventListener('click', clearMask);
    document.getElementById('bg-rows').addEventListener('keydown', e => { if (e.key === 'Enter') applySize(); });
    document.getElementById('bg-cols').addEventListener('keydown', e => { if (e.key === 'Enter') applySize(); });
    renderGrid();
});
