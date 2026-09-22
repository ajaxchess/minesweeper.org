"use strict";

// Reuse helpers from meowdoku.js (loaded before this file)
// RC, nb4, isLogicSolvable, boardHash, solveBoard must be in scope.

const GEN = {
    n: 8,
    regions: null,    // Int8Array, -1 = unassigned
    activeColor: 0,
    painting: false,
};

const RC_LIGHT = ['#f1948a','#f0a07a','#f9e79f','#abebc6','#a2d9ce','#aed6f1','#d2b4de','#f1a7d3','#d7ccc8','#b0bec5'];

function initGen(n) {
    GEN.n = n;
    GEN.regions = new Int8Array(n * n).fill(-1);
    GEN.activeColor = 0;
    renderGenBoard();
    renderColorPalette();
    updateStatus();
}

function renderColorPalette() {
    const palette = document.getElementById('mk-gen-palette');
    if (!palette) return;
    palette.innerHTML = '';
    for (let i = 0; i < GEN.n; i++) {
        const btn = document.createElement('button');
        btn.className = 'mk-gen-color-btn' + (i === GEN.activeColor ? ' active' : '');
        btn.dataset.color = i;
        btn.style.backgroundColor = RC[i];
        btn.style.color = RC_TEXT[i];
        btn.textContent = i + 1;
        btn.title = `Region ${i + 1}`;
        btn.addEventListener('click', () => {
            GEN.activeColor = i;
            document.querySelectorAll('.mk-gen-color-btn').forEach(b => b.classList.toggle('active', parseInt(b.dataset.color) === i));
        });
        palette.appendChild(btn);
    }
}

function renderGenBoard() {
    const grid = document.getElementById('mk-gen-grid');
    if (!grid) return;
    const n = GEN.n;
    grid.style.setProperty('--mk-n', n);
    grid.innerHTML = '';

    for (let i = 0; i < n * n; i++) {
        const el = document.createElement('div');
        el.className = 'mk-cell mk-gen-cell';
        el.dataset.idx = i;
        refreshGenCell(el, i);

        el.addEventListener('mousedown', e => { e.preventDefault(); GEN.painting = true; paintCell(i); });
        el.addEventListener('mouseover', () => { if (GEN.painting) paintCell(i); });
        el.addEventListener('touchstart', e => { e.preventDefault(); paintCell(i); }, {passive: false});
        el.addEventListener('touchmove', e => {
            e.preventDefault();
            const t = e.touches[0];
            const target = document.elementFromPoint(t.clientX, t.clientY);
            if (target && target.dataset.idx !== undefined) paintCell(parseInt(target.dataset.idx));
        }, {passive: false});

        grid.appendChild(el);
    }
}

function refreshGenCell(el, idx) {
    const reg = GEN.regions[idx];
    const n = GEN.n;
    el.style.backgroundColor = reg === -1 ? '#d0d0d0' : RC[reg];
    el.textContent = '';

    el.classList.remove('mk-bt','mk-bb','mk-bl','mk-br');
    if (reg !== -1) {
        const r = (idx/n)|0, c = idx%n;
        if (r===0     || GEN.regions[idx-n] !== reg) el.classList.add('mk-bt');
        if (r===n-1   || GEN.regions[idx+n] !== reg) el.classList.add('mk-bb');
        if (c===0     || GEN.regions[idx-1] !== reg) el.classList.add('mk-bl');
        if (c===n-1   || GEN.regions[idx+1] !== reg) el.classList.add('mk-br');
    }
}

function paintCell(idx) {
    if (GEN.regions[idx] === GEN.activeColor) {
        GEN.regions[idx] = -1;  // right-click or second tap = erase
    } else {
        GEN.regions[idx] = GEN.activeColor;
    }
    // Refresh this cell and neighbors (border logic depends on neighbors)
    const n = GEN.n;
    const r = (idx/n)|0, c = idx%n;
    const toRefresh = [idx];
    if (r>0)   toRefresh.push(idx-n);
    if (r<n-1) toRefresh.push(idx+n);
    if (c>0)   toRefresh.push(idx-1);
    if (c<n-1) toRefresh.push(idx+1);
    toRefresh.forEach(i => {
        const el = document.querySelector(`#mk-gen-grid .mk-cell[data-idx="${i}"]`);
        if (el) refreshGenCell(el, i);
    });
    updateStatus();
}

function updateStatus() {
    const n = GEN.n;
    const regions = GEN.regions;
    const status  = document.getElementById('mk-gen-status');
    const playBtn = document.getElementById('mk-gen-play-btn');
    const shareBtn = document.getElementById('mk-gen-share-btn');
    if (!status) return;

    // Count unassigned cells and check all N regions are used
    const unassigned = Array.from(regions).filter(r => r === -1).length;
    if (unassigned > 0) {
        status.textContent = `${unassigned} cell${unassigned > 1 ? 's' : ''} uncolored`;
        status.className = 'mk-gen-status pending';
        if (playBtn) playBtn.disabled = true;
        if (shareBtn) shareBtn.disabled = true;
        return;
    }

    const usedRegs = new Set(regions);
    const missingRegs = [];
    for (let i = 0; i < n; i++) if (!usedRegs.has(i)) missingRegs.push(i + 1);
    if (missingRegs.length) {
        status.textContent = `Region${missingRegs.length > 1 ? 's' : ''} ${missingRegs.join(', ')} unused`;
        status.className = 'mk-gen-status pending';
        if (playBtn) playBtn.disabled = true;
        if (shareBtn) shareBtn.disabled = true;
        return;
    }

    // Find solution
    const catCols = solveBoard(n, regions);
    if (!catCols) {
        status.textContent = '✗ No valid solution exists';
        status.className = 'mk-gen-status invalid';
        if (playBtn) playBtn.disabled = true;
        if (shareBtn) shareBtn.disabled = true;
        return;
    }

    if (!isLogicSolvable(n, regions, catCols)) {
        status.textContent = '⚠ Solvable by trial-and-error only (needs logical deducibility)';
        status.className = 'mk-gen-status warn';
        if (playBtn) playBtn.disabled = true;
        if (shareBtn) shareBtn.disabled = true;
        return;
    }

    status.textContent = '✓ Valid — logically solvable!';
    status.className = 'mk-gen-status valid';
    if (playBtn) playBtn.disabled = false;
    if (shareBtn) shareBtn.disabled = false;
}

function getShareUrl() {
    const hash = boardHash(GEN.regions, GEN.n);
    return `${location.origin}/meowdoku?board=${hash}`;
}

document.addEventListener('DOMContentLoaded', () => {
    document.addEventListener('mouseup', () => { GEN.painting = false; });

    const sizeSelect = document.getElementById('mk-gen-size');
    if (sizeSelect) {
        sizeSelect.addEventListener('change', () => initGen(parseInt(sizeSelect.value, 10)));
    }

    const clearBtn = document.getElementById('mk-gen-clear-btn');
    if (clearBtn) clearBtn.addEventListener('click', () => {
        GEN.regions.fill(-1);
        renderGenBoard();
        updateStatus();
    });

    const playBtn = document.getElementById('mk-gen-play-btn');
    if (playBtn) playBtn.addEventListener('click', () => {
        const url = getShareUrl();
        window.location.href = url;
    });

    const shareBtn = document.getElementById('mk-gen-share-btn');
    if (shareBtn) shareBtn.addEventListener('click', () => {
        const url = getShareUrl();
        if (navigator.clipboard) {
            navigator.clipboard.writeText(url).then(() => {
                shareBtn.textContent = '✓ Copied!';
                setTimeout(() => { shareBtn.textContent = '🔗 Copy Link'; }, 2000);
            });
        } else {
            prompt('Copy this link:', url);
        }
    });

    initGen(8);
});
