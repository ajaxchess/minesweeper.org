/**
 * cubesweeper.js — F73
 *
 * Minesweeper on a rotating 3D cube. Six N×N faces, full 8-connectivity
 * extended across face boundaries via the edge-crossing table.
 *
 * Face indices:  0=Front(+Z)  1=Back(-Z)  2=Right(+X)
 *                3=Left(-X)   4=Top(+Y)   5=Bottom(-Y)
 *
 * Depends on: vendor/three.min.js (THREE in global scope)
 */

'use strict';

// ---------------------------------------------------------------------------
// Cell-state constants
// ---------------------------------------------------------------------------

const CS_HIDDEN    = 0;
const CS_REVEALED  = 1;
const CS_FLAGGED   = 2;
const CS_QUESTION  = 3;
const CS_MINE      = 4;
const CS_DETONATED = 5;

// ---------------------------------------------------------------------------
// Color helpers — mirrors worldsweeper.js pattern
// ---------------------------------------------------------------------------

const _CS_COLOR_FALLBACK = {
    '--glob-hidden':        '#06101e',   // near-black navy
    '--glob-hidden-border': '#020609',   // near-black for cell gaps
    '--glob-rev':           '#f5f8ff',   // near-white — maximum contrast against hidden
    '--glob-mine':          '#cc2222',
    '--glob-detonated':     '#ff0000',
};

function _cssCube(varName) {
    const el = document.getElementById('cube-wrap') || document.documentElement;
    const v  = getComputedStyle(el).getPropertyValue(varName).trim();
    return v || _CS_COLOR_FALLBACK[varName];
}

const _CS_NUM_COLORS = ['', '#1976D2', '#388E3C', '#D32F2F', '#7B1FA2',
                            '#F57F17', '#00838F', '#212121', '#757575'];

// ---------------------------------------------------------------------------
// Module-level state
// ---------------------------------------------------------------------------

let _renderer, _camera, _scene, _cubeGroup, _raycaster;
let _cellMeshes = [];   // THREE.Mesh[6*N*N]
let _sprites    = [];   // THREE.Sprite|null[6*N*N]
let _adj        = null; // Uint32Array[][6*N*N] — precomputed neighbour IDs

let _N         = 9;    // grid size (cells per face edge)
let _mineCount = 60;

let cellState  = null;  // Uint8Array[6*N*N]
let adjCount   = null;  // Uint8Array[6*N*N]
let mineSet    = null;  // Set<number>
let gameOver   = false;
let firstClick = true;
let _leftClicks = 0;
let _csBbbv       = 0;   // 3BV of the current board (computed after mines placed)
let _timerHandle  = null;
let _startTime    = 0;
let _finalTimeMs  = 0;
let _noGuess      = false;

// Drag tracking
const _csDrag = { active: false, lastX: 0, lastY: 0, travelSq: 0 };

// Flag mode & far-numbers (same as worldsweeper)
let _csFlagMode      = false;
let _csHideFarNums   = true;
let _csTmpVec        = null;

// Camera pulse
let _csPulse = null;

// ---------------------------------------------------------------------------
// Cell ID encoding  (face * N² + row * N + col)
// ---------------------------------------------------------------------------

function _cid(f, r, c)  { return f * _N * _N + r * _N + c; }
function _face(id)       { return (id / (_N * _N)) | 0; }
function _row(id)        { return ((id % (_N * _N)) / _N) | 0; }
function _col(id)        { return id % _N; }

// ---------------------------------------------------------------------------
// Edge-crossing table
// ---------------------------------------------------------------------------
// crossEdge(face, vr, vc, N) — map one virtual out-of-bounds coordinate.
// Exactly ONE of vr, vc should be out of [0..N-1] when called directly.
// For corner diagonals (both out), see buildNeighbours().

function _crossEdge(face, vr, vc, N) {
    const last = N - 1;
    switch (face) {
        case 0: // Front (+Z)
            if (vr <  0)  return [4, 0,        vc];   // → Top    row 0    (z≈+1 edge)
            if (vr >= N)  return [5, last,      vc];   // → Bottom row last (z≈+1 edge)
            if (vc >= N)  return [2, vr,         0];   // → Right  col 0
            if (vc <  0)  return [3, vr,      last];   // → Left   col last
            break;
        case 1: // Back (-Z)
            if (vr <  0)  return [4, last, last-vc];   // → Top    row last (z≈-1 edge)
            if (vr >= N)  return [5, 0,    last-vc];   // → Bottom row 0    (z≈-1 edge)
            if (vc >= N)  return [3, vr,         0];   // → Left   col 0
            if (vc <  0)  return [2, vr,      last];   // → Right  col last
            break;
        case 2: // Right (+X)
            if (vr <  0)  return [4, vc,      last];   // → Top    col last (x≈+1 edge)
            if (vr >= N)  return [5, last-vc, last];   // → Bottom col last (x≈+1 edge)
            if (vc >= N)  return [1, vr,         0];   // → Back   col 0
            if (vc <  0)  return [0, vr,      last];   // → Front  col last
            break;
        case 3: // Left (-X)
            if (vr <  0)  return [4, last-vc,    0];   // → Top    col 0    (x≈-1 edge)
            if (vr >= N)  return [5, vc,          0];  // → Bottom col 0    (x≈-1 edge)
            if (vc >= N)  return [0, vr,          0];  // → Front  col 0
            if (vc <  0)  return [1, vr,      last];   // → Back   col last
            break;
        case 4: // Top (+Y)
            if (vr <  0)  return [0, 0,          vc];  // → Front  row 0 (z≈+1 edge)
            if (vr >= N)  return [1, 0,     last-vc];  // → Back   row 0 (z≈-1 edge)
            if (vc >= N)  return [2, 0,          vr];  // → Right  row 0 (x≈+1 edge)
            if (vc <  0)  return [3, 0,     last-vr];  // → Left   row 0 (x≈-1 edge)
            break;
        case 5: // Bottom (-Y)
            if (vr <  0)  return [1, last, last-vc];   // → Back   row last (z≈-1 edge)
            if (vr >= N)  return [0, last,       vc];  // → Front  row last (z≈+1 edge)
            if (vc >= N)  return [2, last, last-vr];   // → Right  row last (x≈+1 edge)
            if (vc <  0)  return [3, last,       vr];  // → Left   row last (x≈-1 edge)
            break;
    }
    return null;
}

// ---------------------------------------------------------------------------
// Build adjacency list for all 6*N*N cells
// ---------------------------------------------------------------------------

function _buildNeighbours(N) {
    const TOTAL = 6 * N * N;
    const adj   = new Array(TOTAL);

    for (let f = 0; f < 6; f++) {
        for (let r = 0; r < N; r++) {
            for (let c = 0; c < N; c++) {
                const id    = f * N * N + r * N + c;
                const nbSet = new Set();

                for (let dr = -1; dr <= 1; dr++) {
                    for (let dc = -1; dc <= 1; dc++) {
                        if (dr === 0 && dc === 0) continue;
                        const vr = r + dr;
                        const vc = c + dc;
                        const outR = vr < 0 || vr >= N;
                        const outC = vc < 0 || vc >= N;

                        let tf = f, nr = vr, nc = vc;

                        if (outR && outC) {
                            // Corner diagonal: cross NS edge first, then apply EW offset
                            const step1 = _crossEdge(f, vr, c, N);
                            if (!step1) continue;
                            [tf, nr, nc] = step1;
                            const vc2 = nc + dc;
                            if (vc2 < 0 || vc2 >= N) {
                                const step2 = _crossEdge(tf, nr, vc2, N);
                                if (!step2) continue;
                                [tf, nr, nc] = step2;
                            } else {
                                nc = vc2;
                            }
                        } else if (outR || outC) {
                            const res = _crossEdge(f, vr, vc, N);
                            if (!res) continue;
                            [tf, nr, nc] = res;
                        }

                        if (nr < 0 || nr >= N || nc < 0 || nc >= N) continue;
                        nbSet.add(tf * N * N + nr * N + nc);
                    }
                }

                adj[id] = new Uint32Array(nbSet);
            }
        }
    }
    return adj;
}

// ---------------------------------------------------------------------------
// 3D cell-centre position for a given (face, row, col)
// Cube occupies [-1, 1]³; cells have centres at -(N-1)/N … +(N-1)/N
// ---------------------------------------------------------------------------

function _cellCentre(f, r, c) {
    // u = col mapped to (-1 + 1/N) … (1 - 1/N)
    // v = row mapped to (-1 + 1/N) … (1 - 1/N)  (positive = away from top)
    const u = -1 + (2 * c + 1) / _N;
    const v =  1 - (2 * r + 1) / _N;
    switch (f) {
        case 0: return new THREE.Vector3(u,  v,  1);    // Front: x=u, y=v, z=+1
        case 1: return new THREE.Vector3(-u, v, -1);    // Back:  x=-u,y=v, z=-1
        case 2: return new THREE.Vector3(1,  v, -u);    // Right: x=+1,y=v, z=-u
        case 3: return new THREE.Vector3(-1, v,  u);    // Left:  x=-1,y=v, z=+u
        case 4: return new THREE.Vector3(u,  1,  v);    // Top:   x=u, y=+1,z=v
        case 5: return new THREE.Vector3(u, -1, -v);    // Bottom:x=u, y=-1,z=-v
    }
}

// Outward unit normal for each face
const _FACE_NORMALS = [
    new THREE.Vector3( 0,  0,  1),  // Front
    new THREE.Vector3( 0,  0, -1),  // Back
    new THREE.Vector3( 1,  0,  0),  // Right
    new THREE.Vector3(-1,  0,  0),  // Left
    new THREE.Vector3( 0,  1,  0),  // Top
    new THREE.Vector3( 0, -1,  0),  // Bottom
];

// Local tangent axes for each face (right=col, up=−row)
const _FACE_RIGHT = [
    new THREE.Vector3(1,0,0), new THREE.Vector3(-1,0,0),
    new THREE.Vector3(0,0,-1), new THREE.Vector3(0,0,1),
    new THREE.Vector3(1,0,0), new THREE.Vector3(1,0,0),
];
const _FACE_UP = [
    new THREE.Vector3(0,1,0), new THREE.Vector3(0,1,0),
    new THREE.Vector3(0,1,0), new THREE.Vector3(0,1,0),
    new THREE.Vector3(0,0,-1), new THREE.Vector3(0,0,1),  // swapped: right×up must equal outward normal
];

// ---------------------------------------------------------------------------
// Build cell meshes — one quad per cell, six grid-line objects
// ---------------------------------------------------------------------------

function _buildCellMeshes() {
    _cellMeshes = [];
    _cubeGroup.clear();

    const TOTAL   = 6 * _N * _N;
    const halfCell = 1 / _N;          // half cell width (cell = 2/N wide)
    const INSET    = 0.90;             // cosmetic gap between cells

    for (let id = 0; id < TOTAL; id++) {
        const f = _face(id), r = _row(id), c = _col(id);
        const centre = _cellCentre(f, r, c);
        const normal = _FACE_NORMALS[f];
        const right  = _FACE_RIGHT[f];
        const up     = _FACE_UP[f];

        // Four corners of the cell quad
        const hw = halfCell * INSET;
        const p0 = centre.clone().addScaledVector(right, -hw).addScaledVector(up, -hw);
        const p1 = centre.clone().addScaledVector(right,  hw).addScaledVector(up, -hw);
        const p2 = centre.clone().addScaledVector(right,  hw).addScaledVector(up,  hw);
        const p3 = centre.clone().addScaledVector(right, -hw).addScaledVector(up,  hw);

        const positions = new Float32Array([
            p0.x, p0.y, p0.z,
            p1.x, p1.y, p1.z,
            p2.x, p2.y, p2.z,
            p0.x, p0.y, p0.z,
            p2.x, p2.y, p2.z,
            p3.x, p3.y, p3.z,
        ]);
        const normals = new Float32Array(18);
        for (let i = 0; i < 6; i++) {
            normals[i*3]   = normal.x;
            normals[i*3+1] = normal.y;
            normals[i*3+2] = normal.z;
        }

        const geo = new THREE.BufferGeometry();
        geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geo.setAttribute('normal',   new THREE.BufferAttribute(normals,   3));

        const mat  = new THREE.MeshPhongMaterial({
            color:     _cssCube('--glob-hidden'),
            specular:  new THREE.Color(0x4488cc),
            shininess: 80,
            side:      THREE.FrontSide,
        });
        const mesh = new THREE.Mesh(geo, mat);
        mesh.userData.cellId = id;
        _cubeGroup.add(mesh);
        _cellMeshes.push(mesh);
    }

    // Draw cell borders: one LINE_STRIP per face for the grid lines
    for (let f = 0; f < 6; f++) {
        const lineVerts = [];
        const normal = _FACE_NORMALS[f];
        const right  = _FACE_RIGHT[f];
        const up     = _FACE_UP[f];
        const NUDGE  = 1.002;  // push border slightly above tiles

        // Horizontal lines (r = 0..N)
        for (let row = 0; row <= _N; row++) {
            const y = -1 + (2 * row) / _N;
            const xStart = -1, xEnd = 1;
            const sCentre = new THREE.Vector3().copy(normal).multiplyScalar(NUDGE);
            sCentre.addScaledVector(up, y);
            const eStart = sCentre.clone().addScaledVector(right, xStart);
            const eEnd   = sCentre.clone().addScaledVector(right, xEnd);
            lineVerts.push(eStart.x, eStart.y, eStart.z, eEnd.x, eEnd.y, eEnd.z);
        }
        // Vertical lines (c = 0..N)
        for (let col = 0; col <= _N; col++) {
            const x = -1 + (2 * col) / _N;
            const yStart = -1, yEnd = 1;
            const sCentre = new THREE.Vector3().copy(normal).multiplyScalar(NUDGE);
            sCentre.addScaledVector(right, x);
            const eStart = sCentre.clone().addScaledVector(up, yStart);
            const eEnd   = sCentre.clone().addScaledVector(up, yEnd);
            lineVerts.push(eStart.x, eStart.y, eStart.z, eEnd.x, eEnd.y, eEnd.z);
        }

        const lineGeo = new THREE.BufferGeometry();
        lineGeo.setAttribute('position', new THREE.Float32BufferAttribute(lineVerts, 3));
        _cubeGroup.add(new THREE.LineSegments(lineGeo,
            new THREE.LineBasicMaterial({ color: _cssCube('--glob-hidden-border') })
        ));
    }
}

// ---------------------------------------------------------------------------
// Sprite overlays — mirrors worldsweeper.js
// ---------------------------------------------------------------------------

function _csMakeSprite(text, color, size, bgColor, faceIndex) {
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
        side:        THREE.FrontSide,
    });
    const geo  = new THREE.PlaneGeometry(size, size);
    const mesh = new THREE.Mesh(geo, mat);
    // Orient the plane co-planar with its cube face using the face's
    // right/up/normal basis vectors (PlaneGeometry default: +X=right, +Y=up, +Z=normal)
    const rotMatrix = new THREE.Matrix4().makeBasis(
        _FACE_RIGHT[faceIndex],
        _FACE_UP[faceIndex],
        _FACE_NORMALS[faceIndex]
    );
    mesh.quaternion.setFromRotationMatrix(rotMatrix);
    return mesh;
}

function _csClearSprite(id) {
    if (!_sprites[id]) return;
    _cubeGroup.remove(_sprites[id]);
    _sprites[id].geometry.dispose();
    _sprites[id].material.map.dispose();
    _sprites[id].material.dispose();
    _sprites[id] = null;
}

function _csPlaceSprite(id, text, color, bgColor) {
    _csClearSprite(id);
    const f      = _face(id);
    const centre = _cellCentre(f, _row(id), _col(id));
    const size   = 2.2 / _N;
    const mesh   = _csMakeSprite(text, color, size, bgColor, f);
    // Offset slightly outward along the face normal so the plane clears the cell surface
    mesh.position.copy(centre).addScaledVector(_FACE_NORMALS[f], 0.02);
    _cubeGroup.add(mesh);
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
    _csClearSprite(id);

    const mineEmoji = (typeof getMineEmoji === 'function') ? getMineEmoji() : '💣';
    const flagEmoji = (typeof getFlagEmoji === 'function') ? getFlagEmoji() : '🚩';

    switch (state) {
        case CS_HIDDEN:
            mesh.material.color.set(_cssCube('--glob-hidden'));
            break;
        case CS_REVEALED:
            mesh.material.color.set(_cssCube('--glob-rev'));
            if (adjCount && adjCount[id] > 0) {
                _csPlaceSprite(id, String(adjCount[id]),
                    _CS_NUM_COLORS[adjCount[id]] || '#ffffff');
            }
            break;
        case CS_FLAGGED:
            mesh.material.color.set(_cssCube('--glob-hidden'));
            _csPlaceSprite(id, flagEmoji, '#ffffff', 'rgba(255,255,255,0.85)');
            break;
        case CS_QUESTION:
            mesh.material.color.set(_cssCube('--glob-hidden'));
            _csPlaceSprite(id, '?', '#333333', 'rgba(255,221,68,0.9)');
            break;
        case CS_MINE:
            mesh.material.color.set(_cssCube('--glob-mine'));
            _csPlaceSprite(id, mineEmoji, '#ffffff');
            break;
        case CS_DETONATED:
            mesh.material.color.set(_cssCube('--glob-detonated'));
            _csPlaceSprite(id, mineEmoji, '#ffffff');
            break;
    }
}

// ---------------------------------------------------------------------------
// Game logic
// ---------------------------------------------------------------------------

function _csInitGameState() {
    const TOTAL = 6 * _N * _N;
    cellState.fill(CS_HIDDEN);
    adjCount.fill(0);
    mineSet    = new Set();
    gameOver   = false;
    firstClick = true;
    _leftClicks = 0;
    _csBbbv     = 0;
    _csStopTimer();
    document.getElementById('cs-elapsed').textContent = '0.00';
    document.getElementById('cs-mines-remaining').textContent = String(_mineCount);
    const pctEl = document.getElementById('cs-pct');
    if (pctEl) pctEl.textContent = '0';
    document.getElementById('cube-overlay').style.display = 'none';
    document.getElementById('cs-score-form').style.display = 'none';
    for (let i = 0; i < TOTAL; i++) updateCellVisual(i);
}

function _csGenerateMines(TOTAL, count, safeId) {
    const pool  = Array.from({ length: TOTAL }, (_, i) => i).filter(i => i !== safeId);
    const mines = new Set();
    for (let i = 0; i < count; i++) {
        const j = i + Math.floor(Math.random() * (pool.length - i));
        [pool[i], pool[j]] = [pool[j], pool[i]];
        mines.add(pool[i]);
    }
    return mines;
}

function _csComputeAdj(mines) {
    adjCount.fill(0);
    for (const m of mines) {
        for (const nb of _adj[m]) adjCount[nb]++;
    }
}

// ---------------------------------------------------------------------------
// No-Guess solver (constraint propagation)
// ---------------------------------------------------------------------------

function _csIsSolvable(mines, adjCounts, safeId, TOTAL) {
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

function _csGenerateMinesNoGuess(safeId, TOTAL) {
    for (let attempt = 0; attempt < 200; attempt++) {
        const mines     = _csGenerateMines(TOTAL, _mineCount, safeId);
        const localAdj  = new Uint8Array(TOTAL);
        for (const m of mines) for (const nb of _adj[m]) localAdj[nb]++;
        if (_csIsSolvable(mines, localAdj, safeId, TOTAL)) return mines;
    }
    return _csGenerateMines(TOTAL, _mineCount, safeId); // fallback
}

// ---------------------------------------------------------------------------
// Reveal (BFS flood-fill)
// ---------------------------------------------------------------------------

function revealCell(id) {
    if (gameOver || cellState[id] !== CS_HIDDEN) return;
    const TOTAL = 6 * _N * _N;

    if (firstClick) {
        firstClick = false;
        if (_noGuess) {
            mineSet = _csGenerateMinesNoGuess(id, TOTAL);
        } else {
            mineSet = _csGenerateMines(TOTAL, _mineCount, id);
        }
        _csComputeAdj(mineSet);
        _csBbbv = _csCompute3BV(TOTAL);
        _csStartTimer();
    }

    if (mineSet.has(id)) {
        cellState[id] = CS_DETONATED;
        for (const m of mineSet) {
            if (cellState[m] === CS_HIDDEN) cellState[m] = CS_MINE;
            updateCellVisual(m);
        }
        updateCellVisual(id);
        _csTriggerGameOver(false);
        return;
    }

    const queue = [id];
    cellState[id] = CS_REVEALED;
    updateCellVisual(id);
    if (adjCount[id] === 0) {
        while (queue.length) {
            const cur = queue.shift();
            for (const nb of _adj[cur]) {
                if (cellState[nb] !== CS_HIDDEN || mineSet.has(nb)) continue;
                cellState[nb] = CS_REVEALED;
                updateCellVisual(nb);
                if (adjCount[nb] === 0) queue.push(nb);
            }
        }
    }
    _csUpdatePctCleared();
    _csCheckWin();
}

// ---------------------------------------------------------------------------
// Flag cycling
// ---------------------------------------------------------------------------

function cycleFlagCell(id) {
    if (gameOver) return;
    const s = cellState[id];
    if (s === CS_REVEALED) return;
    if      (s === CS_HIDDEN)   cellState[id] = CS_FLAGGED;
    else if (s === CS_FLAGGED)  cellState[id] = CS_QUESTION;
    else if (s === CS_QUESTION) cellState[id] = CS_HIDDEN;
    updateCellVisual(id);
    _csUpdateMineCounter();
}

function _csUpdateMineCounter() {
    const flagged = cellState.reduce((n, s) => n + (s === CS_FLAGGED ? 1 : 0), 0);
    document.getElementById('cs-mines-remaining').textContent = String(_mineCount - flagged);
}

// ---------------------------------------------------------------------------
// 3BV and percentage cleared
// ---------------------------------------------------------------------------

function _csCompute3BV(TOTAL) {
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

function _csUpdatePctCleared() {
    const TOTAL = 6 * _N * _N;
    const safe = TOTAL - _mineCount;
    if (safe <= 0) return;
    let revealed = 0;
    for (let i = 0; i < TOTAL; i++) {
        if (cellState[i] === CS_REVEALED) revealed++;
    }
    const pct = Math.floor(revealed / safe * 100);
    const el = document.getElementById('cs-pct');
    if (el) el.textContent = pct;
}

// ---------------------------------------------------------------------------
// Win / loss
// ---------------------------------------------------------------------------

function _csCheckWin() {
    const TOTAL = 6 * _N * _N;
    let revealed = 0;
    for (let i = 0; i < TOTAL; i++) if (cellState[i] === CS_REVEALED) revealed++;
    if (revealed === TOTAL - _mineCount) _csTriggerGameOver(true);
}

function _csTriggerGameOver(won) {
    gameOver     = true;
    _finalTimeMs = Math.round(performance.now() - _startTime);
    _csStopTimer();
    _csTriggerPulse();
    document.getElementById('cs-overlay-msg').textContent = won ? '🎉 You win!' : '💥 Game over!';
    const overlay = document.getElementById('cube-overlay');
    overlay.style.display      = 'flex';
    overlay.style.flexDirection = 'column';
    if (won) _csShowScoreForm();
}

// ---------------------------------------------------------------------------
// Score submission
// ---------------------------------------------------------------------------

function _csShowScoreForm() {
    const form    = document.getElementById('cs-score-form');
    if (!form) return;
    const wrapper  = document.querySelector('.game-wrapper');
    const username = wrapper ? (wrapper.dataset.username || '') : '';

    form.style.display = 'block';
    form.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    if (username) {
        // Logged-in via Google — auto-submit immediately
        form.innerHTML = '<p style="color:var(--text-dim);">Saving score…</p>';
        _csSubmitScore(username).then(ok => {
            form.innerHTML = ok
                ? '<p style="color:#6fcf97;">Score saved! ' +
                  '<a href="/cubesweeper/leaderboard" style="color:#53d8fb;">View leaderboard →</a></p>'
                : '<p style="color:#e57373;">Error saving score — please try again.</p>';
        });
        return;
    }

    document.getElementById('cs-score-msg').textContent = '';
    const saved = localStorage.getItem('cubesweeper_name');
    if (saved) document.getElementById('cs-score-name').value = saved;

    document.getElementById('cs-score-submit').onclick = async () => {
        const name = document.getElementById('cs-score-name').value.trim();
        if (!name) { document.getElementById('cs-score-msg').textContent = 'Please enter your name.'; return; }
        localStorage.setItem('cubesweeper_name', name);
        document.getElementById('cs-score-submit').disabled = true;
        document.getElementById('cs-score-msg').textContent = 'Saving…';
        const ok = await _csSubmitScore(name);
        document.getElementById('cs-score-submit').disabled = false;
        if (ok) {
            document.getElementById('cs-score-form').innerHTML =
                '<p style="color:#6fcf97;">Score saved! ' +
                '<a href="/cubesweeper/leaderboard" style="color:#53d8fb;">View leaderboard →</a></p>';
        } else {
            document.getElementById('cs-score-msg').textContent = 'Error saving score — please try again.';
        }
    };
}

async function _csSubmitScore(name) {
    const wrapper  = document.querySelector('.game-wrapper');
    const mode     = wrapper ? wrapper.dataset.mode : 'beginner';
    const TOTAL    = 6 * _N * _N;
    try {
        const r = await fetch('/api/cubesweeper-scores', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body: JSON.stringify({
                name,
                cube_mode:   mode,
                grid_size:   _N,
                time_ms:     _finalTimeMs,
                mines:       _mineCount,
                no_guess:    _noGuess,
                bbbv:        _csBbbv || undefined,
                left_clicks: _leftClicks || undefined,
                board_hash:  _csBoardToHash(mineSet, TOTAL),
            }),
        });
        return r.ok;
    } catch { return false; }
}

function _csBoardToHash(mines, TOTAL) {
    const bytes = new Uint8Array(Math.ceil(TOTAL / 8));
    for (const i of mines) bytes[i >> 3] |= 1 << (i & 7);
    return btoa(String.fromCharCode(...bytes))
        .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

// ---------------------------------------------------------------------------
// Reset
// ---------------------------------------------------------------------------

function resetCube() {
    _csInitGameState();
}

// ---------------------------------------------------------------------------
// Face click dispatch
// ---------------------------------------------------------------------------

function cellClicked(id, button) {
    if (button === 2 || _csFlagMode) {
        cycleFlagCell(id);
    } else {
        _leftClicks++;
        revealCell(id);
    }
}

// ---------------------------------------------------------------------------
// Timer
// ---------------------------------------------------------------------------

function _csStartTimer() {
    _startTime = performance.now();
    _timerHandle = setInterval(() => {
        const s = ((performance.now() - _startTime) / 1000).toFixed(2);
        document.getElementById('cs-elapsed').textContent = s;
    }, 100);
}

function _csStopTimer() {
    clearInterval(_timerHandle);
    _timerHandle = null;
}

// ---------------------------------------------------------------------------
// Camera pulse
// ---------------------------------------------------------------------------

function _csTriggerPulse() {
    _csPulse = { t0: performance.now(), baseZ: 4.5, peakZ: 4.7, dur: 300 };
}

// ---------------------------------------------------------------------------
// Background selector — cubesweeper uses its own cs_bg key
// ---------------------------------------------------------------------------

const _CS_BACKGROUNDS = {
    sky:    'linear-gradient(150deg, #96b8d8 0%, #4a6a90 100%)',
    orange: 'radial-gradient(ellipse at center, #c87941 0%, #7a3d10 100%)',
    galaxy: 'url(/static/img/milkyway_bg.jpg) center/cover no-repeat',
};

function _csApplyBackground(wrap) {
    const key = localStorage.getItem('cs_bg') || 'sky';
    wrap.style.background = _CS_BACKGROUNDS[key] || _CS_BACKGROUNDS.sky;
    document.querySelectorAll('.ws-bg-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.bg === key);
    });
    const credit = document.getElementById('ws-galaxy-credit');
    if (credit) credit.style.display = key === 'galaxy' ? '' : 'none';
}

// ---------------------------------------------------------------------------
// Button state helpers
// ---------------------------------------------------------------------------

function _csUpdateFlagBtn() {
    const btn = document.getElementById('cs-flag-btn');
    if (!btn) return;
    btn.classList.toggle('active', _csFlagMode);
    btn.title = _csFlagMode
        ? 'Flag mode ON — clicks place/cycle flags'
        : 'Flag mode OFF — clicks reveal cells';
}

function _csUpdateFarNumsBtn() {
    const btn = document.getElementById('cs-farnums-btn');
    if (!btn) return;
    btn.classList.toggle('active', _csHideFarNums);
    btn.title = _csHideFarNums
        ? 'Far-side numbers hidden — click to show all'
        : 'Click to hide numbers on the back of the cube';
}

function _csUpdateNoGuessBtn() {
    const btn = document.getElementById('cs-noguess-btn');
    if (!btn) return;
    btn.classList.toggle('active', _noGuess);
    btn.querySelector('#cs-noguess-state').textContent = _noGuess ? 'On' : 'Off';
}

// ---------------------------------------------------------------------------
// Drag rotation + click detection — mirrors worldsweeper
// ---------------------------------------------------------------------------

function _csAttachEvents(canvas) {
    let _longPress = null;

    canvas.addEventListener('pointerdown', e => {
        _csDrag.active   = true;
        _csDrag.lastX    = e.clientX;
        _csDrag.lastY    = e.clientY;
        _csDrag.travelSq = 0;
        canvas.setPointerCapture(e.pointerId);
        if (e.pointerType === 'touch') {
            _longPress = setTimeout(() => {
                _longPress = null;
                if (_csDrag.travelSq < 36) _csDoRaycast(e, 2);
            }, 500);
        }
    });

    canvas.addEventListener('pointermove', e => {
        if (!_csDrag.active) return;
        const dx = e.clientX - _csDrag.lastX;
        const dy = e.clientY - _csDrag.lastY;
        _csDrag.travelSq += dx * dx + dy * dy;
        _csDrag.lastX = e.clientX;
        _csDrag.lastY = e.clientY;
        if (_csDrag.travelSq > 4 && _longPress) { clearTimeout(_longPress); _longPress = null; }
        const len = Math.sqrt(dx * dx + dy * dy);
        if (len < 0.001) return;
        const axis = new THREE.Vector3(dy / len, dx / len, 0);
        const q    = new THREE.Quaternion().setFromAxisAngle(axis, len * 0.005);
        _cubeGroup.quaternion.premultiply(q);
    });

    canvas.addEventListener('pointerup', e => {
        if (_longPress) { clearTimeout(_longPress); _longPress = null; }
        if (_csDrag.active && _csDrag.travelSq < 36) _csDoRaycast(e, e.button);
        _csDrag.active = false;
    });

    canvas.addEventListener('contextmenu', e => e.preventDefault());
}

function _csDoRaycast(e, button) {
    const rect  = _renderer.domElement.getBoundingClientRect();
    const mouse = new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width)  *  2 - 1,
        ((e.clientY - rect.top)  / rect.height) * -2 + 1,
    );
    _raycaster.setFromCamera(mouse, _camera);
    const hits = _raycaster.intersectObjects(_cellMeshes);
    if (hits.length) cellClicked(hits[0].object.userData.cellId, button);
}

// ---------------------------------------------------------------------------
// Render loop
// ---------------------------------------------------------------------------

function _csAnimate() {
    requestAnimationFrame(_csAnimate);

    if (_csPulse) {
        const t = (performance.now() - _csPulse.t0) / _csPulse.dur;
        if (t >= 1) {
            _camera.position.z = _csPulse.baseZ;
            _csPulse = null;
        } else {
            const frac = t < 0.5 ? t * 2 : (1 - t) * 2;
            _camera.position.z = _csPulse.baseZ + (_csPulse.peakZ - _csPulse.baseZ) * frac;
        }
    }

    // Hide far-side sprites (numbers, flags, question marks)
    if (_csHideFarNums && _cubeGroup && _csTmpVec) {
        const q = _cubeGroup.quaternion;
        const TOTAL = 6 * _N * _N;
        for (let id = 0; id < TOTAL; id++) {
            const spr = _sprites[id];
            if (!spr) continue;
            const centre = _cellCentre(_face(id), _row(id), _col(id));
            _csTmpVec.set(centre.x, centre.y, centre.z).applyQuaternion(q);
            spr.visible = _csTmpVec.z > 0;
        }
    }

    _renderer.render(_scene, _camera);
}

// ---------------------------------------------------------------------------
// initCube — called by the page
// ---------------------------------------------------------------------------

function initCube() {
    const wrap   = document.getElementById('cube-wrap');
    const canvas = document.getElementById('cube-canvas');
    if (!wrap || !canvas) return;

    const wrapper = document.querySelector('.game-wrapper');
    _N         = wrapper ? (parseInt(wrapper.dataset.gridSize, 10) || 9) : 9;
    _mineCount = wrapper ? (parseInt(wrapper.dataset.mines,    10) || 60) : 60;

    const TOTAL = 6 * _N * _N;
    cellState = new Uint8Array(TOTAL);
    adjCount  = new Uint8Array(TOTAL);
    mineSet   = new Set();
    _sprites  = new Array(TOTAL).fill(null);
    _cellMeshes = [];

    // Precompute adjacency
    _adj = _buildNeighbours(_N);

    // Renderer
    _renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    _renderer.setPixelRatio(window.devicePixelRatio);
    _renderer.setSize(wrap.clientWidth, wrap.clientHeight);
    _renderer.setClearColor(0x000000, 0);

    // Camera
    _camera = new THREE.PerspectiveCamera(45, wrap.clientWidth / wrap.clientHeight, 0.1, 100);
    _camera.position.set(0, 0, 4.5);

    // Scene — stronger directional light from upper-left gives clear 3-face shading
    _scene = new THREE.Scene();
    _scene.add(new THREE.AmbientLight(0xffffff, 0.4));
    const dir = new THREE.DirectionalLight(0xffffff, 1.2);
    dir.position.set(-4, 8, 5);
    _scene.add(dir);

    _cubeGroup = new THREE.Group();
    _scene.add(_cubeGroup);
    _raycaster = new THREE.Raycaster();

    // Slightly tilt the cube so all 3 visible faces are apparent on load
    _cubeGroup.rotation.x = 0.4;
    _cubeGroup.rotation.y = 0.6;
    _cubeGroup.quaternion.setFromEuler(_cubeGroup.rotation);

    // Background
    _csApplyBackground(wrap);
    document.querySelectorAll('.ws-bg-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            localStorage.setItem('cs_bg', btn.dataset.bg);
            _csApplyBackground(wrap);
        });
    });

    // Far-nums toggle
    _csTmpVec      = new THREE.Vector3();
    _csHideFarNums = localStorage.getItem('cs_farnums') !== '0';
    _csUpdateFarNumsBtn();
    document.getElementById('cs-farnums-btn')?.addEventListener('click', () => {
        _csHideFarNums = !_csHideFarNums;
        localStorage.setItem('cs_farnums', _csHideFarNums ? '1' : '0');
        if (!_csHideFarNums) {
            for (let i = 0; i < TOTAL; i++) if (_sprites[i]) _sprites[i].visible = true;
        }
        _csUpdateFarNumsBtn();
    });

    // Flag mode toggle
    _csFlagMode = localStorage.getItem('cs_flagmode') === '1';
    _csUpdateFlagBtn();
    document.getElementById('cs-flag-btn')?.addEventListener('click', () => {
        _csFlagMode = !_csFlagMode;
        localStorage.setItem('cs_flagmode', _csFlagMode ? '1' : '0');
        _csUpdateFlagBtn();
    });

    // No-Guess toggle (beginner/intermediate only — expert hides the button via template)
    const mode = wrapper ? wrapper.dataset.mode : 'beginner';
    _noGuess = (mode !== 'expert' && mode !== 'custom')
        && localStorage.getItem('cs_noguess') === '1';
    _csUpdateNoGuessBtn();
    document.getElementById('cs-noguess-btn')?.addEventListener('click', () => {
        _noGuess = !_noGuess;
        localStorage.setItem('cs_noguess', _noGuess ? '1' : '0');
        _csUpdateNoGuessBtn();
        resetCube();
    });

    // Build meshes
    _buildCellMeshes();

    // Events
    _csAttachEvents(canvas);

    // Resize
    window.addEventListener('resize', () => {
        const w = wrap.clientWidth, h = wrap.clientHeight;
        _renderer.setSize(w, h);
        _camera.aspect = w / h;
        _camera.updateProjectionMatrix();
    });

    // Reset buttons
    document.getElementById('cs-reset-btn')?.addEventListener('click', resetCube);
    document.getElementById('cs-overlay-reset')?.addEventListener('click', resetCube);

    // Custom mode
    if (mode === 'custom') _csSetupCustom();

    // Initial state
    _csInitGameState();

    // Start render loop
    _csAnimate();
}

// ---------------------------------------------------------------------------
// Custom board setup
// ---------------------------------------------------------------------------

function _csSetupCustom() {
    const sizeInput = document.getElementById('cs-size-input');
    const mineInput = document.getElementById('cs-mine-input');
    const playBtn   = document.getElementById('cs-custom-play-btn');
    const infoEl    = document.getElementById('cs-face-info');

    function updateInfo() {
        const n = parseInt(sizeInput?.value, 10) || 9;
        const total = 6 * n * n;
        const maxMines = Math.floor(total * 0.9);
        if (mineInput) mineInput.max = maxMines;
        if (infoEl) infoEl.textContent =
            `${n}×${n} per face — ${total} total cells, max ${maxMines} mines`;
    }

    sizeInput?.addEventListener('input', updateInfo);
    updateInfo();

    playBtn?.addEventListener('click', () => {
        const n = Math.min(100, Math.max(1, parseInt(sizeInput?.value, 10) || 9));
        const total = 6 * n * n;
        const maxM  = Math.floor(total * 0.9);
        const m = Math.min(maxM, Math.max(1, parseInt(mineInput?.value, 10) || 10));

        _N = n;
        _mineCount = m;
        const wrapper = document.querySelector('.game-wrapper');
        if (wrapper) { wrapper.dataset.gridSize = n; wrapper.dataset.mines = m; }

        const TOTAL2 = 6 * n * n;
        cellState = new Uint8Array(TOTAL2);
        adjCount  = new Uint8Array(TOTAL2);
        mineSet   = new Set();
        _sprites  = new Array(TOTAL2).fill(null);
        _adj      = _buildNeighbours(n);
        _buildCellMeshes();
        _csInitGameState();
    });
}
