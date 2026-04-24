/**
 * mobiussweeper.js — F74
 *
 * Minesweeper on a rotating 3D Möbius strip. Tiles cover the parametric
 * surface. The Möbius topology means traversing the full length of the strip
 * returns you to the starting row with the row index flipped — the seam
 * adjacency rule is:
 *   crossing col = -1  →  (W-1-r, L-1)
 *   crossing col = L   →  (W-1-r, 0)
 * Row boundaries are the physical strip edges (no wrap).
 *
 * Depends on: vendor/three.min.js (THREE in global scope)
 */

'use strict';

// ---------------------------------------------------------------------------
// Cell-state constants (shared with worldsweeper/cubesweeper pattern)
// ---------------------------------------------------------------------------

const MS_HIDDEN    = 0;
const MS_REVEALED  = 1;
const MS_FLAGGED   = 2;
const MS_QUESTION  = 3;
const MS_MINE      = 4;
const MS_DETONATED = 5;

// ---------------------------------------------------------------------------
// Color helpers
// ---------------------------------------------------------------------------

const _MS_COLOR_FALLBACK = {
    '--glob-hidden':        '#06101e',
    '--glob-hidden-border': '#020609',
    '--glob-rev':           '#f5f8ff',
    '--glob-mine':          '#cc2222',
    '--glob-detonated':     '#ff0000',
};

function _cssMobius(varName) {
    const el = document.getElementById('mobius-wrap') || document.documentElement;
    const v  = getComputedStyle(el).getPropertyValue(varName).trim();
    return v || _MS_COLOR_FALLBACK[varName];
}

const _MS_NUM_COLORS = ['', '#1976D2', '#388E3C', '#D32F2F', '#7B1FA2',
                            '#F57F17', '#00838F', '#212121', '#757575'];

// ---------------------------------------------------------------------------
// Module-level state
// ---------------------------------------------------------------------------

let _renderer, _camera, _scene, _mobiusGroup, _raycaster;
let _cellMeshes = [];   // THREE.Mesh[W*L]
let _sprites    = [];   // THREE.Mesh|null[W*L]
let _adj        = null; // Uint32Array[][W*L] — precomputed neighbour IDs
let _cellNormals = [];  // THREE.Vector3[W*L] — outward surface normal per cell

let _W         = 4;    // strip width (rows across the strip)
let _L         = 40;   // strip length (cols around the loop)
let _mineCount = 16;

// Möbius parametric constants
const _MS_R = 2.5;   // radius from centre to strip mid-line
const _MS_H = 0.8;   // half-width of the strip

let cellState  = null;  // Uint8Array[W*L]
let adjCount   = null;  // Uint8Array[W*L]
let mineSet    = null;  // Set<number>
let gameOver   = false;
let firstClick = true;
let _leftClicks    = 0;
let _msBbbv        = 0;
let _msChordClicks  = 0;
let _msLastClickId  = -1;
let _msLastClickTime = 0;
let _timerHandle  = null;
let _startTime    = 0;
let _finalTimeMs  = 0;
let _noGuess      = false;

// Drag tracking
const _msDrag = { active: false, lastX: 0, lastY: 0, travelSq: 0 };

// Flag mode & far-numbers
let _msFlagMode    = false;
let _msHideFarNums = false;
let _msTmpVec      = null;

// Camera pulse
let _msPulse = null;

// ---------------------------------------------------------------------------
// Cell ID encoding  (row * L + col)
// ---------------------------------------------------------------------------

function _mid(r, c)  { return r * _L + c; }
function _mrow(id)   { return (id / _L) | 0; }
function _mcol(id)   { return id % _L; }

// ---------------------------------------------------------------------------
// Möbius adjacency — the single twist rule
// ---------------------------------------------------------------------------

function _mobiusNeighbour(r, c, dr, dc) {
    let nr = r + dr;
    let nc = c + dc;
    if (nc < 0)   { nc = _L - 1; nr = (_W - 1) - nr; }   // Möbius twist
    if (nc >= _L) { nc = 0;      nr = (_W - 1) - nr; }   // Möbius twist
    if (nr < 0 || nr >= _W) return null;                  // strip edge
    return [nr, nc];
}

function _buildMobiusNeighbours(W, L) {
    const TOTAL = W * L;
    const adj   = new Array(TOTAL);
    for (let r = 0; r < W; r++) {
        for (let c = 0; c < L; c++) {
            const id   = r * L + c;
            const nbSet = new Set();
            for (let dr = -1; dr <= 1; dr++) {
                for (let dc = -1; dc <= 1; dc++) {
                    if (dr === 0 && dc === 0) continue;
                    // Two-step for diagonals that cross the seam twice
                    // (can't happen on strip — only col wraps, not row)
                    const res = _mobiusNeighbour(r, c, dr, dc);
                    if (res) nbSet.add(res[0] * L + res[1]);
                }
            }
            adj[id] = new Uint32Array(nbSet);
        }
    }
    return adj;
}

// ---------------------------------------------------------------------------
// Möbius parametric surface
// ---------------------------------------------------------------------------

function _mobiusPoint(r, c, W, L, R, H) {
    // t: angle around the loop (0..2π)
    // s: position across width (-H..+H), cell centre at midpoint of row band
    const t = ((c + 0.5) / L) * 2 * Math.PI;
    const s = -H + (2 * r + 1) / W * H;
    const x = (R + s * Math.cos(t / 2)) * Math.cos(t);
    const y = (R + s * Math.cos(t / 2)) * Math.sin(t);
    const z =  s * Math.sin(t / 2);
    return new THREE.Vector3(x, y, z);
}

function _mobiusPointRaw(t, s, R, H) {
    const x = (R + s * Math.cos(t / 2)) * Math.cos(t);
    const y = (R + s * Math.cos(t / 2)) * Math.sin(t);
    const z =  s * Math.sin(t / 2);
    return new THREE.Vector3(x, y, z);
}

function _mobiusNormal(r, c, W, L, R, H) {
    const EPS = 1e-4;
    const t   = ((c + 0.5) / L) * 2 * Math.PI;
    const s   = -H + (2 * r + 1) / W * H;
    const dt  = EPS;
    const ds  = EPS;
    const p   = _mobiusPointRaw(t,    s,    R, H);
    const pt  = _mobiusPointRaw(t+dt, s,    R, H);
    const ps  = _mobiusPointRaw(t,    s+ds, R, H);
    const dPdt = new THREE.Vector3().subVectors(pt, p).multiplyScalar(1 / dt);
    const dPds = new THREE.Vector3().subVectors(ps, p).multiplyScalar(1 / ds);
    return new THREE.Vector3().crossVectors(dPdt, dPds).normalize();
}

// ---------------------------------------------------------------------------
// Build cell meshes — one quad per cell, plus grid lines
// ---------------------------------------------------------------------------

function _buildMobiusCellMeshes() {
    _cellMeshes = [];
    _cellNormals = [];
    _mobiusGroup.clear();

    const TOTAL = _W * _L;
    const INSET = 0.93;  // slight gap between cells for visual clarity

    for (let r = 0; r < _W; r++) {
        for (let c = 0; c < _L; c++) {
            const id = _mid(r, c);

            // Four corners of this cell in parameter space:
            // (r, c), (r+1, c), (r+1, c+1), (r, c+1)
            const t0 = (c     / _L) * 2 * Math.PI;
            const t1 = ((c+1) / _L) * 2 * Math.PI;
            const s0 = -_MS_H + (r     / _W) * 2 * _MS_H;
            const s1 = -_MS_H + ((r+1) / _W) * 2 * _MS_H;

            // Compute inset corners using INSET factor around cell centre
            const tMid = (t0 + t1) / 2;
            const sMid = (s0 + s1) / 2;
            const hw_t = (t1 - t0) / 2 * INSET;
            const hw_s = (s1 - s0) / 2 * INSET;

            const p00 = _mobiusPointRaw(tMid - hw_t, sMid - hw_s, _MS_R, _MS_H);
            const p10 = _mobiusPointRaw(tMid + hw_t, sMid - hw_s, _MS_R, _MS_H);
            const p11 = _mobiusPointRaw(tMid + hw_t, sMid + hw_s, _MS_R, _MS_H);
            const p01 = _mobiusPointRaw(tMid - hw_t, sMid + hw_s, _MS_R, _MS_H);

            const positions = new Float32Array([
                p00.x, p00.y, p00.z,
                p10.x, p10.y, p10.z,
                p11.x, p11.y, p11.z,
                p00.x, p00.y, p00.z,
                p11.x, p11.y, p11.z,
                p01.x, p01.y, p01.z,
            ]);

            const norm = _mobiusNormal(r, c, _W, _L, _MS_R, _MS_H);
            _cellNormals[id] = norm;
            const normals = new Float32Array(18);
            for (let i = 0; i < 6; i++) {
                normals[i*3]   = norm.x;
                normals[i*3+1] = norm.y;
                normals[i*3+2] = norm.z;
            }

            const geo = new THREE.BufferGeometry();
            geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            geo.setAttribute('normal',   new THREE.BufferAttribute(normals,   3));

            const mat = new THREE.MeshPhongMaterial({
                color:     _cssMobius('--glob-hidden'),
                specular:  new THREE.Color(0x4488cc),
                shininess: 80,
                side:      THREE.DoubleSide,  // strip has only one side topologically
            });
            const mesh = new THREE.Mesh(geo, mat);
            mesh.userData.cellId = id;
            _mobiusGroup.add(mesh);
            _cellMeshes.push(mesh);
        }
    }

    // Grid lines — draw thin line strips along the strip
    const lineVerts = [];
    for (let r = 0; r <= _W; r++) {
        for (let c = 0; c < _L; c++) {
            const t0 = (c     / _L) * 2 * Math.PI;
            const t1 = ((c+1) / _L) * 2 * Math.PI;
            const s  = -_MS_H + (r / _W) * 2 * _MS_H;
            const p0 = _mobiusPointRaw(t0, s, _MS_R, _MS_H);
            const p1 = _mobiusPointRaw(t1, s, _MS_R, _MS_H);
            lineVerts.push(p0.x, p0.y, p0.z, p1.x, p1.y, p1.z);
        }
    }
    for (let c = 0; c <= _L; c++) {
        const t = (c / _L) * 2 * Math.PI;
        for (let r = 0; r < _W; r++) {
            const s0 = -_MS_H + (r     / _W) * 2 * _MS_H;
            const s1 = -_MS_H + ((r+1) / _W) * 2 * _MS_H;
            const p0 = _mobiusPointRaw(t, s0, _MS_R, _MS_H);
            const p1 = _mobiusPointRaw(t, s1, _MS_R, _MS_H);
            lineVerts.push(p0.x, p0.y, p0.z, p1.x, p1.y, p1.z);
        }
    }
    const lineGeo = new THREE.BufferGeometry();
    lineGeo.setAttribute('position', new THREE.Float32BufferAttribute(lineVerts, 3));
    _mobiusGroup.add(new THREE.LineSegments(lineGeo,
        new THREE.LineBasicMaterial({ color: _cssMobius('--glob-hidden-border') })
    ));
}

// ---------------------------------------------------------------------------
// Sprite overlays
// ---------------------------------------------------------------------------

function _msMakeSprite(text, color, size, bgColor, cellId) {
    const c   = document.createElement('canvas');
    c.width   = c.height = 128;
    const ctx = c.getContext('2d');
    ctx.clearRect(0, 0, 128, 128);
    if (bgColor) {
        ctx.beginPath();
        ctx.arc(64, 64, 54, 0, Math.PI * 2);
        ctx.fillStyle = bgColor;
        ctx.fill();
    }
    ctx.font         = 'bold 80px sans-serif';
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle    = color;
    ctx.fillText(text, 64, 64);

    const mat = new THREE.MeshBasicMaterial({
        map:         new THREE.CanvasTexture(c),
        transparent: true,
        depthTest:   false,
        side:        THREE.DoubleSide,
    });
    const geo  = new THREE.PlaneGeometry(size, size);
    const mesh = new THREE.Mesh(geo, mat);

    // Orient the sprite tangent to the Möbius surface using the cell normal
    // right = ∂P/∂t direction, up = ∂P/∂s direction
    const r = _mrow(cellId), c2 = _mcol(cellId);
    const EPS = 1e-4;
    const t  = ((c2 + 0.5) / _L) * 2 * Math.PI;
    const s  = -_MS_H + (2 * r + 1) / _W * _MS_H;
    const p  = _mobiusPointRaw(t,     s,     _MS_R, _MS_H);
    const pt = _mobiusPointRaw(t+EPS, s,     _MS_R, _MS_H);
    const ps = _mobiusPointRaw(t,     s+EPS, _MS_R, _MS_H);
    const right  = new THREE.Vector3().subVectors(pt, p).normalize();
    const up     = new THREE.Vector3().subVectors(ps, p).normalize();
    const normal = _cellNormals[cellId];
    const rotMatrix = new THREE.Matrix4().makeBasis(right, up, normal);
    mesh.quaternion.setFromRotationMatrix(rotMatrix);
    return mesh;
}

function _msClearSprite(id) {
    if (!_sprites[id]) return;
    _mobiusGroup.remove(_sprites[id]);
    _sprites[id].geometry.dispose();
    _sprites[id].material.map.dispose();
    _sprites[id].material.dispose();
    _sprites[id] = null;
}

function _msPlaceSprite(id, text, color, bgColor) {
    _msClearSprite(id);
    const r    = _mrow(id), c = _mcol(id);
    const size = (_MS_H * 2 / _W) * 1.1;
    const mesh = _msMakeSprite(text, color, size, bgColor, id);
    const centre = _mobiusPoint(r, c, _W, _L, _MS_R, _MS_H);
    const norm   = _cellNormals[id];
    mesh.position.copy(centre).addScaledVector(norm, 0.04);
    _mobiusGroup.add(mesh);
    _sprites[id] = mesh;
}

// ---------------------------------------------------------------------------
// updateCellVisual
// ---------------------------------------------------------------------------

function updateCellVisual(id) {
    if (!cellState || !_cellMeshes[id]) return;
    const state = cellState[id];
    const mesh  = _cellMeshes[id];
    mesh.visible = true;
    _msClearSprite(id);

    const mineEmoji = (typeof getMineEmoji === 'function') ? getMineEmoji() : '💣';
    const flagEmoji = (typeof getFlagEmoji === 'function') ? getFlagEmoji() : '🚩';

    switch (state) {
        case MS_HIDDEN:
            mesh.material.color.set(_cssMobius('--glob-hidden'));
            break;
        case MS_REVEALED:
            mesh.material.color.set(_cssMobius('--glob-rev'));
            if (adjCount && adjCount[id] > 0) {
                _msPlaceSprite(id, String(adjCount[id]),
                    _MS_NUM_COLORS[adjCount[id]] || '#ffffff');
            }
            break;
        case MS_FLAGGED:
            mesh.material.color.set(_cssMobius('--glob-hidden'));
            _msPlaceSprite(id, flagEmoji, '#ffffff', 'rgba(255,255,255,0.85)');
            break;
        case MS_QUESTION:
            mesh.material.color.set(_cssMobius('--glob-hidden'));
            _msPlaceSprite(id, '?', '#333333', 'rgba(255,221,68,0.9)');
            break;
        case MS_MINE:
            mesh.material.color.set(_cssMobius('--glob-mine'));
            _msPlaceSprite(id, mineEmoji, '#ffffff');
            break;
        case MS_DETONATED:
            mesh.material.color.set(_cssMobius('--glob-detonated'));
            _msPlaceSprite(id, mineEmoji, '#ffffff');
            break;
    }
}

// ---------------------------------------------------------------------------
// Game logic
// ---------------------------------------------------------------------------

function _msInitGameState() {
    const TOTAL = _W * _L;
    cellState.fill(MS_HIDDEN);
    adjCount.fill(0);
    mineSet    = new Set();
    gameOver   = false;
    firstClick = true;
    _leftClicks     = 0;
    _msChordClicks  = 0;
    _msLastClickId  = -1;
    _msLastClickTime = 0;
    _msBbbv         = 0;
    _msStopTimer();
    document.getElementById('ms-elapsed').textContent = '0.00';
    document.getElementById('ms-mines-remaining').textContent = String(_mineCount);
    const pctEl = document.getElementById('ms-pct');
    if (pctEl) pctEl.textContent = '0';
    document.getElementById('mobius-overlay').style.display = 'none';
    document.getElementById('ms-score-form').style.display = 'none';
    for (let i = 0; i < TOTAL; i++) updateCellVisual(i);
}

function _msGenerateMines(TOTAL, count, safeId) {
    const pool  = Array.from({ length: TOTAL }, (_, i) => i).filter(i => i !== safeId);
    const mines = new Set();
    for (let i = 0; i < count; i++) {
        const j = i + Math.floor(Math.random() * (pool.length - i));
        [pool[i], pool[j]] = [pool[j], pool[i]];
        mines.add(pool[i]);
    }
    return mines;
}

function _msComputeAdj(mines) {
    adjCount.fill(0);
    for (const m of mines) {
        for (const nb of _adj[m]) adjCount[nb]++;
    }
}

// ---------------------------------------------------------------------------
// No-Guess solver (same constraint propagation as cubesweeper)
// ---------------------------------------------------------------------------

function _msIsSolvable(mines, adjCounts, safeId, TOTAL) {
    const revealed  = new Uint8Array(TOTAL);
    const knownMine = new Uint8Array(TOTAL);

    function bfsReveal(startId) {
        const q = [startId];
        while (q.length) {
            const id = q.pop();
            if (revealed[id] || mines.has(id)) continue;
            revealed[id] = 1;
            if (adjCounts[id] === 0) {
                for (const nb of _adj[id]) {
                    if (!revealed[nb] && !mines.has(nb)) q.push(nb);
                }
            }
        }
    }

    bfsReveal(safeId);

    let changed = true;
    while (changed) {
        changed = false;
        for (let id = 0; id < TOTAL; id++) {
            if (!revealed[id] || mines.has(id)) continue;
            const cnt    = adjCounts[id];
            const nbs    = _adj[id];
            const hidden = [];
            let   flags  = 0;
            for (const nb of nbs) {
                if      (knownMine[nb])  flags++;
                else if (!revealed[nb])  hidden.push(nb);
            }
            if (cnt === flags && hidden.length > 0) {
                for (const nb of hidden) {
                    if (!revealed[nb]) { bfsReveal(nb); changed = true; }
                }
            } else if (cnt - flags === hidden.length && hidden.length > 0) {
                for (const nb of hidden) {
                    if (!knownMine[nb]) { knownMine[nb] = 1; changed = true; }
                }
            }
        }
    }
    for (let id = 0; id < TOTAL; id++) {
        if (!mines.has(id) && !revealed[id]) return false;
    }
    return true;
}

function _msGenerateMinesNoGuess(safeId, TOTAL) {
    for (let attempt = 0; attempt < 200; attempt++) {
        const mines    = _msGenerateMines(TOTAL, _mineCount, safeId);
        const localAdj = new Uint8Array(TOTAL);
        for (const m of mines) for (const nb of _adj[m]) localAdj[nb]++;
        if (_msIsSolvable(mines, localAdj, safeId, TOTAL)) return mines;
    }
    return _msGenerateMines(TOTAL, _mineCount, safeId);
}

// ---------------------------------------------------------------------------
// Reveal (BFS flood-fill)
// ---------------------------------------------------------------------------

function revealCell(id) {
    if (gameOver || cellState[id] !== MS_HIDDEN) return;
    const TOTAL = _W * _L;

    if (firstClick) {
        firstClick = false;
        if (_noGuess) {
            mineSet = _msGenerateMinesNoGuess(id, TOTAL);
        } else {
            mineSet = _msGenerateMines(TOTAL, _mineCount, id);
        }
        _msComputeAdj(mineSet);
        _msBbbv = _msCompute3BV(TOTAL);
        _msStartTimer();
    }

    if (mineSet.has(id)) {
        cellState[id] = MS_DETONATED;
        for (const m of mineSet) {
            if (cellState[m] === MS_HIDDEN) cellState[m] = MS_MINE;
            updateCellVisual(m);
        }
        updateCellVisual(id);
        _msTriggerGameOver(false);
        return;
    }

    const queue = [id];
    cellState[id] = MS_REVEALED;
    updateCellVisual(id);
    if (adjCount[id] === 0) {
        while (queue.length) {
            const cur = queue.shift();
            for (const nb of _adj[cur]) {
                if (cellState[nb] !== MS_HIDDEN || mineSet.has(nb)) continue;
                cellState[nb] = MS_REVEALED;
                updateCellVisual(nb);
                if (adjCount[nb] === 0) queue.push(nb);
            }
        }
    }
    _msUpdatePctCleared();
    _msCheckWin();
}

// ---------------------------------------------------------------------------
// Flag cycling
// ---------------------------------------------------------------------------

function cycleFlagCell(id) {
    if (gameOver) return;
    const s = cellState[id];
    if (s === MS_REVEALED) return;
    if      (s === MS_HIDDEN)   cellState[id] = MS_FLAGGED;
    else if (s === MS_FLAGGED)  cellState[id] = MS_QUESTION;
    else if (s === MS_QUESTION) cellState[id] = MS_HIDDEN;
    updateCellVisual(id);
    _msUpdateMineCounter();
}

function chordMsCell(id) {
    if (gameOver || cellState[id] !== MS_REVEALED || adjCount[id] <= 0) return;
    const flags = _adj[id].filter(nb => cellState[nb] === MS_FLAGGED).length;
    if (flags === adjCount[id]) {
        _msChordClicks++;
        _adj[id].forEach(nb => revealCell(nb));
    }
}

function _msUpdateMineCounter() {
    const flagged = cellState.reduce((n, s) => n + (s === MS_FLAGGED ? 1 : 0), 0);
    document.getElementById('ms-mines-remaining').textContent = String(_mineCount - flagged);
}

// ---------------------------------------------------------------------------
// 3BV and percentage cleared
// ---------------------------------------------------------------------------

function _msCompute3BV(TOTAL) {
    const visited = new Uint8Array(TOTAL);
    let openings = 0;
    for (let start = 0; start < TOTAL; start++) {
        if (mineSet.has(start) || visited[start] || adjCount[start] !== 0) continue;
        openings++;
        const queue = [start];
        visited[start] = 1;
        while (queue.length) {
            const cur = queue.shift();
            for (const nb of _adj[cur]) {
                if (mineSet.has(nb) || visited[nb]) continue;
                visited[nb] = 1;
                if (adjCount[nb] === 0) queue.push(nb);
            }
        }
    }
    let isolated = 0;
    for (let i = 0; i < TOTAL; i++) {
        if (!mineSet.has(i) && !visited[i]) isolated++;
    }
    return openings + isolated;
}

function _msUpdatePctCleared() {
    const TOTAL = _W * _L;
    const safe  = TOTAL - _mineCount;
    if (safe <= 0) return;
    let revealed = 0;
    for (let i = 0; i < TOTAL; i++) {
        if (cellState[i] === MS_REVEALED) revealed++;
    }
    const pct = Math.floor(revealed / safe * 100);
    const el = document.getElementById('ms-pct');
    if (el) el.textContent = pct;
}

// ---------------------------------------------------------------------------
// Win / loss
// ---------------------------------------------------------------------------

function _msCheckWin() {
    const TOTAL = _W * _L;
    let revealed = 0;
    for (let i = 0; i < TOTAL; i++) if (cellState[i] === MS_REVEALED) revealed++;
    if (revealed === TOTAL - _mineCount) _msTriggerGameOver(true);
}

function _msTriggerGameOver(won) {
    gameOver     = true;
    _finalTimeMs = Math.round(performance.now() - _startTime);
    _msStopTimer();
    _msTriggerPulse();
    document.getElementById('ms-overlay-msg').textContent = won ? '🎉 You win!' : '💥 Game over!';
    const overlay = document.getElementById('mobius-overlay');
    overlay.style.display      = 'flex';
    overlay.style.flexDirection = 'column';
    if (won) _msShowScoreForm();
}

// ---------------------------------------------------------------------------
// Score submission
// ---------------------------------------------------------------------------

function _msShowScoreForm() {
    const form    = document.getElementById('ms-score-form');
    if (!form) return;
    const wrapper  = document.querySelector('.game-wrapper');
    const username = wrapper ? (wrapper.dataset.username || '') : '';

    form.style.display = 'block';
    form.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    if (username) {
        form.innerHTML = '<p style="color:var(--text-dim);">Saving score…</p>';
        _msSubmitScore(username).then(ok => {
            form.innerHTML = ok
                ? '<p style="color:#6fcf97;">Score saved! ' +
                  '<a href="/mobiussweeper/leaderboard" style="color:#53d8fb;">View leaderboard →</a></p>'
                : '<p style="color:#e57373;">Error saving score — please try again.</p>';
        });
        return;
    }

    document.getElementById('ms-score-msg').textContent = '';
    const saved = localStorage.getItem('mobiussweeper_name');
    if (saved) document.getElementById('ms-score-name').value = saved;

    document.getElementById('ms-score-submit').onclick = async () => {
        const name = document.getElementById('ms-score-name').value.trim();
        if (!name) { document.getElementById('ms-score-msg').textContent = 'Please enter your name.'; return; }
        localStorage.setItem('mobiussweeper_name', name);
        document.getElementById('ms-score-submit').disabled = true;
        document.getElementById('ms-score-msg').textContent = 'Saving…';
        const ok = await _msSubmitScore(name);
        document.getElementById('ms-score-submit').disabled = false;
        if (ok) {
            document.getElementById('ms-score-form').innerHTML =
                '<p style="color:#6fcf97;">Score saved! ' +
                '<a href="/mobiussweeper/leaderboard" style="color:#53d8fb;">View leaderboard →</a></p>';
        } else {
            document.getElementById('ms-score-msg').textContent = 'Error saving score — please try again.';
        }
    };
}

async function _msSubmitScore(name) {
    const wrapper = document.querySelector('.game-wrapper');
    const mode    = wrapper ? wrapper.dataset.mode : 'beginner';
    const TOTAL   = _W * _L;
    try {
        const r = await fetch('/api/mobiussweeper-scores', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body: JSON.stringify({
                name,
                mobius_mode: mode,
                width:       _W,
                length:      _L,
                time_ms:     _finalTimeMs,
                mines:       _mineCount,
                no_guess:    _noGuess,
                bbbv:        _msBbbv || undefined,
                left_clicks:  _leftClicks || undefined,
                chord_clicks: _msChordClicks || undefined,
                board_hash:   _msBoardToHash(mineSet, TOTAL),
            }),
        });
        return r.ok;
    } catch { return false; }
}

function _msBoardToHash(mines, TOTAL) {
    const bytes = new Uint8Array(Math.ceil(TOTAL / 8));
    for (const i of mines) bytes[i >> 3] |= 1 << (i & 7);
    return btoa(String.fromCharCode(...bytes))
        .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

// ---------------------------------------------------------------------------
// Reset
// ---------------------------------------------------------------------------

function resetMobius() {
    _msInitGameState();
}

// ---------------------------------------------------------------------------
// Click dispatch
// ---------------------------------------------------------------------------

function cellClicked(id, button) {
    if (button === 2 || _msFlagMode) {
        cycleFlagCell(id);
    } else {
        _leftClicks++;
        revealCell(id);
    }
}

// ---------------------------------------------------------------------------
// Timer
// ---------------------------------------------------------------------------

function _msStartTimer() {
    _startTime = performance.now();
    _timerHandle = setInterval(() => {
        const s = ((performance.now() - _startTime) / 1000).toFixed(2);
        document.getElementById('ms-elapsed').textContent = s;
    }, 100);
}

function _msStopTimer() {
    clearInterval(_timerHandle);
    _timerHandle = null;
}

// ---------------------------------------------------------------------------
// Camera pulse
// ---------------------------------------------------------------------------

function _msTriggerPulse() {
    _msPulse = { t0: performance.now(), baseZ: 6.5, peakZ: 6.8, dur: 300 };
}

// ---------------------------------------------------------------------------
// Background selector
// ---------------------------------------------------------------------------

const _MS_BACKGROUNDS = {
    sky:    'linear-gradient(150deg, #96b8d8 0%, #4a6a90 100%)',
    orange: 'radial-gradient(ellipse at center, #c87941 0%, #7a3d10 100%)',
    galaxy: 'url(/static/img/milkyway_bg.jpg) center/cover no-repeat',
};

function _msApplyBackground(wrap) {
    const key = localStorage.getItem('ms_bg') || 'sky';
    wrap.style.background = _MS_BACKGROUNDS[key] || _MS_BACKGROUNDS.sky;
    document.querySelectorAll('.ws-bg-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.bg === key);
    });
    const credit = document.getElementById('ws-galaxy-credit');
    if (credit) credit.style.display = key === 'galaxy' ? '' : 'none';
}

// ---------------------------------------------------------------------------
// Button state helpers
// ---------------------------------------------------------------------------

function _msUpdateFlagBtn() {
    const btn = document.getElementById('ms-flag-btn');
    if (!btn) return;
    btn.classList.toggle('active', _msFlagMode);
    btn.title = _msFlagMode
        ? 'Flag mode ON — clicks place/cycle flags'
        : 'Flag mode OFF — clicks reveal cells';
}

function _msUpdateFarNumsBtn() {
    const btn = document.getElementById('ms-farnums-btn');
    if (!btn) return;
    btn.classList.toggle('active', _msHideFarNums);
    btn.title = _msHideFarNums
        ? 'Far-side numbers hidden — click to show all (both sides are one surface)'
        : 'Click to hide numbers whose tile normal faces away from camera';
}

function _msUpdateNoGuessBtn() {
    const btn = document.getElementById('ms-noguess-btn');
    if (!btn) return;
    btn.classList.toggle('active', _noGuess);
    btn.querySelector('#ms-noguess-state').textContent = _noGuess ? 'On' : 'Off';
}

// ---------------------------------------------------------------------------
// Drag rotation + click detection
// ---------------------------------------------------------------------------

function _msAttachEvents(canvas) {
    let _longPress = null;

    canvas.addEventListener('pointerdown', e => {
        _msDrag.active   = true;
        _msDrag.lastX    = e.clientX;
        _msDrag.lastY    = e.clientY;
        _msDrag.travelSq = 0;
        canvas.setPointerCapture(e.pointerId);
        if (e.pointerType === 'touch') {
            _longPress = setTimeout(() => {
                _longPress = null;
                if (_msDrag.travelSq < 36) _msDoRaycast(e, 2);
            }, 500);
        }
    });

    canvas.addEventListener('pointermove', e => {
        if (!_msDrag.active) return;
        const dx = e.clientX - _msDrag.lastX;
        const dy = e.clientY - _msDrag.lastY;
        _msDrag.travelSq += dx * dx + dy * dy;
        _msDrag.lastX = e.clientX;
        _msDrag.lastY = e.clientY;
        if (_msDrag.travelSq > 4 && _longPress) { clearTimeout(_longPress); _longPress = null; }
        const len = Math.sqrt(dx * dx + dy * dy);
        if (len < 0.001) return;
        const axis = new THREE.Vector3(dy / len, dx / len, 0);
        const q    = new THREE.Quaternion().setFromAxisAngle(axis, len * 0.005);
        _mobiusGroup.quaternion.premultiply(q);
    });

    canvas.addEventListener('pointerup', e => {
        if (_longPress) { clearTimeout(_longPress); _longPress = null; }
        if (_msDrag.active && _msDrag.travelSq < 36) _msDoRaycast(e, e.button);
        _msDrag.active = false;
    });

    canvas.addEventListener('contextmenu', e => e.preventDefault());
}

function _msDoRaycast(e, button) {
    const rect  = _renderer.domElement.getBoundingClientRect();
    const mouse = new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width)  *  2 - 1,
        ((e.clientY - rect.top)  / rect.height) * -2 + 1,
    );
    _raycaster.setFromCamera(mouse, _camera);
    const hits = _raycaster.intersectObjects(_cellMeshes);
    if (!hits.length) return;
    const id = hits[0].object.userData.cellId;
    if (button === 0 && !_msFlagMode) {
        const now = Date.now();
        if (id === _msLastClickId && now - _msLastClickTime < 300) {
            _msLastClickId   = -1;
            _msLastClickTime = 0;
            chordMsCell(id);
            return;
        }
        _msLastClickId   = id;
        _msLastClickTime = now;
    }
    cellClicked(id, button);
}

// ---------------------------------------------------------------------------
// Render loop
// ---------------------------------------------------------------------------

function _msAnimate() {
    requestAnimationFrame(_msAnimate);

    if (_msPulse) {
        const t = (performance.now() - _msPulse.t0) / _msPulse.dur;
        if (t >= 1) {
            _camera.position.z = _msPulse.baseZ;
            _msPulse = null;
        } else {
            const frac = t < 0.5 ? t * 2 : (1 - t) * 2;
            _camera.position.z = _msPulse.baseZ + (_msPulse.peakZ - _msPulse.baseZ) * frac;
        }
    }

    // Hide sprites on cells whose normals face away from the camera
    if (_msHideFarNums && _mobiusGroup && _msTmpVec) {
        const q = _mobiusGroup.quaternion;
        const TOTAL = _W * _L;
        for (let id = 0; id < TOTAL; id++) {
            const spr = _sprites[id];
            if (!spr) continue;
            const n = _cellNormals[id];
            _msTmpVec.set(n.x, n.y, n.z).applyQuaternion(q);
            spr.visible = _msTmpVec.z > 0;
        }
    }

    _renderer.render(_scene, _camera);
}

// ---------------------------------------------------------------------------
// initMobius — called by the page
// ---------------------------------------------------------------------------

function initMobius() {
    const wrap   = document.getElementById('mobius-wrap');
    const canvas = document.getElementById('mobius-canvas');
    if (!wrap || !canvas) return;

    const wrapper = document.querySelector('.game-wrapper');
    _W         = wrapper ? (parseInt(wrapper.dataset.width,  10) || 4)  : 4;
    _L         = wrapper ? (parseInt(wrapper.dataset.length, 10) || 40) : 40;
    _mineCount = wrapper ? (parseInt(wrapper.dataset.mines,  10) || 16) : 16;

    const TOTAL = _W * _L;
    cellState = new Uint8Array(TOTAL);
    adjCount  = new Uint8Array(TOTAL);
    mineSet   = new Set();
    _sprites  = new Array(TOTAL).fill(null);
    _cellMeshes  = [];
    _cellNormals = [];

    // Precompute Möbius adjacency
    _adj = _buildMobiusNeighbours(_W, _L);

    // Renderer
    _renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    _renderer.setPixelRatio(window.devicePixelRatio);
    _renderer.setSize(wrap.clientWidth, wrap.clientHeight);
    _renderer.setClearColor(0x000000, 0);

    // Camera — strip is wider than cube so pull back a bit more
    _camera = new THREE.PerspectiveCamera(45, wrap.clientWidth / wrap.clientHeight, 0.1, 100);
    _camera.position.set(0, 0, 6.5);

    // Scene
    _scene = new THREE.Scene();
    _scene.add(new THREE.AmbientLight(0xffffff, 0.5));
    const dir = new THREE.DirectionalLight(0xffffff, 1.2);
    dir.position.set(-4, 8, 5);
    _scene.add(dir);

    _mobiusGroup = new THREE.Group();
    _scene.add(_mobiusGroup);
    _raycaster = new THREE.Raycaster();

    // Initial tilt so the strip is interesting on load
    _mobiusGroup.rotation.x = 0.3;
    _mobiusGroup.rotation.y = 0.5;
    _mobiusGroup.quaternion.setFromEuler(_mobiusGroup.rotation);

    // Background
    _msApplyBackground(wrap);
    document.querySelectorAll('.ws-bg-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            localStorage.setItem('ms_bg', btn.dataset.bg);
            _msApplyBackground(wrap);
        });
    });

    // Far-nums toggle
    _msTmpVec      = new THREE.Vector3();
    _msHideFarNums = localStorage.getItem('ms_farnums') === '1';
    _msUpdateFarNumsBtn();
    document.getElementById('ms-farnums-btn')?.addEventListener('click', () => {
        _msHideFarNums = !_msHideFarNums;
        localStorage.setItem('ms_farnums', _msHideFarNums ? '1' : '0');
        if (!_msHideFarNums) {
            for (let i = 0; i < TOTAL; i++) if (_sprites[i]) _sprites[i].visible = true;
        }
        _msUpdateFarNumsBtn();
    });

    // Flag mode toggle
    _msFlagMode = localStorage.getItem('ms_flagmode') === '1';
    _msUpdateFlagBtn();
    document.getElementById('ms-flag-btn')?.addEventListener('click', () => {
        _msFlagMode = !_msFlagMode;
        localStorage.setItem('ms_flagmode', _msFlagMode ? '1' : '0');
        _msUpdateFlagBtn();
    });

    // No-Guess toggle
    const mode = wrapper ? wrapper.dataset.mode : 'beginner';
    _noGuess = (mode !== 'expert')
        && localStorage.getItem('ms_noguess') === '1';
    _msUpdateNoGuessBtn();
    document.getElementById('ms-noguess-btn')?.addEventListener('click', () => {
        _noGuess = !_noGuess;
        localStorage.setItem('ms_noguess', _noGuess ? '1' : '0');
        _msUpdateNoGuessBtn();
        resetMobius();
    });

    // Build meshes
    _buildMobiusCellMeshes();

    // Events
    _msAttachEvents(canvas);

    // Resize
    window.addEventListener('resize', () => {
        const w = wrap.clientWidth, h = wrap.clientHeight;
        _renderer.setSize(w, h);
        _camera.aspect = w / h;
        _camera.updateProjectionMatrix();
    });

    // Reset buttons
    document.getElementById('ms-reset-btn')?.addEventListener('click', resetMobius);
    document.getElementById('ms-overlay-reset')?.addEventListener('click', resetMobius);

    // Initial state
    _msInitGameState();

    // Start render loop
    _msAnimate();
}
