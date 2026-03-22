'use strict';

// ── Neighbor functions ────────────────────────────────────────────────────────
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

// ── 3BV calculation ───────────────────────────────────────────────────────────
function buildBoard(rows, cols, mineSet, neighborFn) {
    const board = Array.from({ length: rows }, () => Array(cols).fill(0));
    for (const idx of mineSet) {
        const r = Math.floor(idx / cols), c = idx % cols;
        board[r][c] = -1;
        neighborFn(r, c, rows, cols).forEach(([nr, nc]) => {
            if (board[nr][nc] !== -1) board[nr][nc]++;
        });
    }
    return board;
}

function calc3BV(board, rows, cols, mineSet, neighborFn) {
    const n       = rows * cols;
    const covered = new Uint8Array(n);
    let   bbbv    = 0;

    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            const idx = r * cols + c;
            if (board[r][c] !== 0 || covered[idx] || mineSet.has(idx)) continue;
            bbbv++;
            const queue = [[r, c]];
            covered[idx] = 1;
            while (queue.length) {
                const [cr, cc] = queue.shift();
                for (const [nr, nc] of neighborFn(cr, cc, rows, cols)) {
                    const ni = nr * cols + nc;
                    if (covered[ni] || mineSet.has(ni)) continue;
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

// ── Random mine placement (partial Fisher-Yates) ──────────────────────────────
function randomMineSet(n, mines) {
    const arr = Uint32Array.from({ length: n }, (_, i) => i);
    for (let i = 0; i < mines; i++) {
        const j = i + Math.floor(Math.random() * (n - i));
        const t = arr[i]; arr[i] = arr[j]; arr[j] = t;
    }
    return new Set(arr.slice(0, mines));
}

// ── Chart instance ────────────────────────────────────────────────────────────
let chart = null;

function initChart() {
    const ctx = document.getElementById('bbbv-chart').getContext('2d');
    chart = new Chart(ctx, {
        type: 'line',
        data: { labels: [], datasets: [] },
        options: {
            responsive: true,
            animation: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        title: items => `${items[0].label} mines`,
                        label: item => ` ${item.dataset.label}: ${item.parsed.y}`,
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Mine count' },
                    ticks: { maxTicksLimit: 20 },
                },
                y: {
                    title: { display: true, text: 'Max 3BV' },
                    beginAtZero: true,
                }
            }
        }
    });
}

// ── Dataset colours ───────────────────────────────────────────────────────────
const DATASET_STYLES = {
    std:    { label: 'Standard',       borderColor: '#1976D2', backgroundColor: 'rgba(25,118,210,0.1)' },
    cyl:    { label: 'Cylinder',       borderColor: '#388E3C', backgroundColor: 'rgba(56,142,60,0.1)' },
    tor:    { label: 'Toroid',         borderColor: '#F57C00', backgroundColor: 'rgba(245,124,0,0.1)' },
    theory: { label: 'Theoretical max', borderColor: '#9E9E9E', backgroundColor: 'transparent',
              borderDash: [5, 4], pointRadius: 0 },
};

// ── Main calculation ──────────────────────────────────────────────────────────
let running = false;

async function runCalculation() {
    if (running) return;

    const rows    = Math.max(3, Math.min(30, parseInt(document.getElementById('calc-rows').value) || 9));
    const cols    = Math.max(3, Math.min(50, parseInt(document.getElementById('calc-cols').value) || 9));
    const samples = parseInt(document.getElementById('calc-samples').value) || 100;
    const n       = rows * cols;
    const maxMines = n - 1;

    const showStd    = document.getElementById('tog-std').checked;
    const showCyl    = document.getElementById('tog-cyl').checked;
    const showTor    = document.getElementById('tog-tor').checked;
    const showTheory = document.getElementById('tog-theory').checked;

    if (!showStd && !showCyl && !showTor && !showTheory) {
        document.getElementById('calc-hint').textContent = 'Select at least one topology.';
        return;
    }

    running = true;
    document.getElementById('calc-run').disabled = true;
    document.getElementById('calc-hint').textContent = '';

    const progressWrap  = document.getElementById('calc-progress-wrap');
    const progressBar   = document.getElementById('calc-progress-bar');
    const progressLabel = document.getElementById('calc-progress-label');
    progressWrap.style.display = 'flex';
    progressBar.style.width = '0%';

    // Build results arrays
    const labels     = [];
    const stdData    = showStd    ? [] : null;
    const cylData    = showCyl    ? [] : null;
    const torData    = showTor    ? [] : null;
    const theoryData = showTheory ? [] : null;

    const neighborFns = [];
    if (showStd) neighborFns.push({ key: 'std', fn: stdNeighbors, data: stdData });
    if (showCyl) neighborFns.push({ key: 'cyl', fn: cylNeighbors, data: cylData });
    if (showTor) neighborFns.push({ key: 'tor', fn: torNeighbors, data: torData });

    // Chunk size: process several mine counts per animation frame
    const CHUNK = Math.max(1, Math.floor(300 / (samples * neighborFns.length / n)));

    let m = 1;
    function processChunk() {
        const end = Math.min(m + CHUNK, maxMines + 1);
        for (; m < end; m++) {
            labels.push(m);
            if (theoryData) theoryData.push(n - m);

            for (const { fn, data } of neighborFns) {
                let maxBBBV = 0;
                for (let s = 0; s < samples; s++) {
                    const mineSet = randomMineSet(n, m);
                    const board   = buildBoard(rows, cols, mineSet, fn);
                    maxBBBV = Math.max(maxBBBV, calc3BV(board, rows, cols, mineSet, fn));
                }
                data.push(maxBBBV);
            }
        }

        const pct = Math.round((m - 1) / maxMines * 100);
        progressBar.style.width = pct + '%';
        progressLabel.textContent = pct + '%';

        if (m <= maxMines) {
            requestAnimationFrame(processChunk);
        } else {
            finishChart(labels, stdData, cylData, torData, theoryData);
        }
    }

    requestAnimationFrame(processChunk);
}

function finishChart(labels, stdData, cylData, torData, theoryData) {
    const datasets = [];
    if (stdData)    datasets.push({ ...DATASET_STYLES.std,    data: stdData,    fill: false, tension: 0.3 });
    if (cylData)    datasets.push({ ...DATASET_STYLES.cyl,    data: cylData,    fill: false, tension: 0.3 });
    if (torData)    datasets.push({ ...DATASET_STYLES.tor,    data: torData,    fill: false, tension: 0.3 });
    if (theoryData) datasets.push({ ...DATASET_STYLES.theory, data: theoryData, fill: false, tension: 0 });

    chart.data.labels   = labels;
    chart.data.datasets = datasets;
    chart.update();

    document.getElementById('calc-progress-wrap').style.display = 'none';
    document.getElementById('calc-run').disabled = false;
    document.getElementById('calc-hint').textContent =
        `Computed for ${labels.length} mine counts on a ${document.getElementById('calc-rows').value}×${document.getElementById('calc-cols').value} board.`;
    running = false;
}

// ── Toggle visibility without recomputing ─────────────────────────────────────
function updateChartVisibility() {
    if (!chart || !chart.data.datasets.length) return;
    const checks = {
        'Standard':        document.getElementById('tog-std').checked,
        'Cylinder':        document.getElementById('tog-cyl').checked,
        'Toroid':          document.getElementById('tog-tor').checked,
        'Theoretical max': document.getElementById('tog-theory').checked,
    };
    chart.data.datasets.forEach(ds => {
        ds.hidden = checks[ds.label] === false;
    });
    chart.update();
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initChart();

    document.getElementById('calc-run').addEventListener('click', runCalculation);
    document.getElementById('calc-rows').addEventListener('keydown', e => { if (e.key === 'Enter') runCalculation(); });
    document.getElementById('calc-cols').addEventListener('keydown', e => { if (e.key === 'Enter') runCalculation(); });

    ['tog-std', 'tog-cyl', 'tog-tor', 'tog-theory'].forEach(id => {
        document.getElementById(id).addEventListener('change', updateChartVisibility);
    });

    document.getElementById('sample-count-label').textContent =
        document.getElementById('calc-samples').value;
    document.getElementById('calc-samples').addEventListener('change', () => {
        document.getElementById('sample-count-label').textContent =
            document.getElementById('calc-samples').value;
    });
});
