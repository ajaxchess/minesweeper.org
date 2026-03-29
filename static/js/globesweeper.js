/**
 * globesweeper.js
 *
 * G2 — Three.js scene, face meshes, drag rotation, raycasting, sprite overlays.
 * G3 — Game logic: state machine, mine generation, BFS reveal, hash, win/loss, timer.
 *
 * Phase 1: Classic skin only. Hardcoded goldberg(1,0) until G1a-beta ships GP(1,1).
 * Depends on: goldberg.js (goldberg fn in global scope), THREE (vendor/three.min.js).
 */

'use strict';

// ---------------------------------------------------------------------------
// Face-state constants  (G3 uses these; defined here for updateFaceVisual)
// ---------------------------------------------------------------------------

const HIDDEN    = 0;
const REVEALED  = 1;
const FLAGGED   = 2;
const QUESTION  = 3;
const MINE      = 4;
const DETONATED = 5;

// ---------------------------------------------------------------------------
// Color fallbacks — overridden by CSS --glob-* variables when G4 lands
// ---------------------------------------------------------------------------

const _COLOR_FALLBACK = {
    '--glob-hidden':        '#4a4a4a',
    '--glob-hidden-border': '#c8892a',
    '--glob-rev':           '#e8e8e8',
    '--glob-mine':          '#cc2222',
    '--glob-detonated':     '#ff0000',
};

function _css(varName) {
    // Read from #globe-wrap so [data-glob-skin] overrides on that element take effect.
    const el = document.getElementById('globe-wrap') || document.documentElement;
    const v  = getComputedStyle(el).getPropertyValue(varName).trim();
    return v || _COLOR_FALLBACK[varName];
}

// Number label colors (mirrors NUM_COLORS_DARK from minesweeper.js)
const _NUM_COLORS = ['', '#1976D2', '#388E3C', '#D32F2F', '#7B1FA2',
                         '#F57F17', '#00838F', '#212121', '#757575'];

// ---------------------------------------------------------------------------
// Module-level scene state
// ---------------------------------------------------------------------------

let _renderer, _camera, _scene, _globeGroup, _raycaster;
let _faceMeshes = [];   // THREE.Mesh[F]
let _sprites    = [];   // THREE.Sprite|null[F]
let _globeData  = null; // { faces, adj, T, F, pentagons }

// Shared game state — allocated in initGlobe, managed by G3
let faceState  = null;  // Uint8Array[F]  — per-face enum (HIDDEN … DETONATED)
let adjCount   = null;  // Uint8Array[F]  — mine-neighbour count per face
let mineSet    = null;  // Set<number>    — face indices that hold mines
let gameOver   = false;
let firstClick = true;
let _mineCount = 0;     // target mine count, read from data-mines
let _timerHandle = null;
let _startTime   = 0;

// Drag tracking
const _drag = { active: false, lastX: 0, lastY: 0, travelSq: 0 };

// Camera pulse
let _pulse = null;

// ---------------------------------------------------------------------------
// initGlobe — called once by the page after DOM is ready
// ---------------------------------------------------------------------------

function initGlobe() {
    const wrap   = document.getElementById('globe-wrap');
    const canvas = document.getElementById('globe-canvas');
    if (!wrap || !canvas) return;

    // ── Geometry ────────────────────────────────────────────────────────────
    // Phase 1: GP(1,0) = 12-face dodecahedron (Class I, available from G1a-alpha).
    // Switch to goldberg(1,1) once G1a-beta is merged.
    _globeData = goldberg(1, 0);
    const F = _globeData.faces.length;

    // Read mine count from template data attribute
    const wrapper = document.querySelector('.game-wrapper');
    _mineCount = wrapper ? (parseInt(wrapper.dataset.mines, 10) || 4) : 4;

    faceState = new Uint8Array(F);   // all HIDDEN at start
    adjCount  = new Uint8Array(F);
    mineSet   = new Set();
    _sprites  = new Array(F).fill(null);

    // ── Renderer ────────────────────────────────────────────────────────────
    _renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    _renderer.setPixelRatio(window.devicePixelRatio);
    _renderer.setSize(wrap.clientWidth, wrap.clientHeight);
    _renderer.setClearColor(0x000000, 0);

    // ── Camera ──────────────────────────────────────────────────────────────
    _camera = new THREE.PerspectiveCamera(45, wrap.clientWidth / wrap.clientHeight, 0.1, 100);
    _camera.position.set(0, 0, 3.5);

    // ── Scene ───────────────────────────────────────────────────────────────
    _scene = new THREE.Scene();
    _scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const dir = new THREE.DirectionalLight(0xffffff, 0.8);
    dir.position.set(5, 5, 5);
    _scene.add(dir);

    _globeGroup = new THREE.Group();
    _scene.add(_globeGroup);
    _raycaster = new THREE.Raycaster();

    // ── Classic skin background (CSS visible through transparent renderer) ──
    wrap.style.background = 'radial-gradient(ellipse at center, #c87941 0%, #7a3d10 100%)';

    // ── Build face tile meshes + border lines ────────────────────────────────
    _buildFaceMeshes(_globeData.faces);

    // ── Input events ────────────────────────────────────────────────────────
    _attachEvents(canvas);

    // ── Resize handler ───────────────────────────────────────────────────────
    window.addEventListener('resize', () => {
        const w = wrap.clientWidth, h = wrap.clientHeight;
        _renderer.setSize(w, h);
        _camera.aspect = w / h;
        _camera.updateProjectionMatrix();
    });

    // ── Reset button ────────────────────────────────────────────────────────
    document.getElementById('reset-btn')?.addEventListener('click', resetGame);
    document.getElementById('overlay-reset')?.addEventListener('click', resetGame);

    // ── Initial game state ──────────────────────────────────────────────────
    _initGameState();

    // ── Start render loop ───────────────────────────────────────────────────
    _animate();
}

// ---------------------------------------------------------------------------
// _buildFaceMeshes — create one Mesh + one Line per Goldberg face
// ---------------------------------------------------------------------------

function _buildFaceMeshes(faces) {
    _faceMeshes = [];

    const TILE_R = 0.98;    // face polygon sits at this radius
    const EDGE_R = 1.001;   // border line sits just above tiles

    for (let i = 0; i < faces.length; i++) {
        const face = faces[i];

        // Scale face vertices and centroid to TILE_R
        const fv = face.verts.map(v =>
            new THREE.Vector3(v.x * TILE_R, v.y * TILE_R, v.z * TILE_R)
        );
        const fc = new THREE.Vector3(
            face.centroid.x * TILE_R,
            face.centroid.y * TILE_R,
            face.centroid.z * TILE_R,
        );

        // Fan-triangulate: (centroid, edge[j], edge[j+1]) for each edge
        const pos = [];
        for (let j = 0; j < fv.length; j++) {
            const a = fv[j];
            const b = fv[(j + 1) % fv.length];
            pos.push(fc.x, fc.y, fc.z);
            pos.push(a.x,  a.y,  a.z);
            pos.push(b.x,  b.y,  b.z);
        }

        const geo = new THREE.BufferGeometry();
        geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
        geo.computeVertexNormals();

        const mat = new THREE.MeshPhongMaterial({
            color:     _css('--glob-hidden'),
            shininess: 60,
            side:      THREE.FrontSide,
        });

        const mesh = new THREE.Mesh(geo, mat);
        mesh.userData.faceIdx = i;
        _globeGroup.add(mesh);
        _faceMeshes.push(mesh);

        // Closed border line at EDGE_R
        const linePos = [];
        for (let j = 0; j <= fv.length; j++) {
            const v = face.verts[j % fv.length];
            linePos.push(v.x * EDGE_R, v.y * EDGE_R, v.z * EDGE_R);
        }
        const lineGeo = new THREE.BufferGeometry();
        lineGeo.setAttribute('position', new THREE.Float32BufferAttribute(linePos, 3));
        _globeGroup.add(new THREE.Line(lineGeo,
            new THREE.LineBasicMaterial({ color: _css('--glob-hidden-border') })
        ));
    }
}

// ---------------------------------------------------------------------------
// Drag rotation + click detection
// ---------------------------------------------------------------------------

function _attachEvents(canvas) {
    let _longPress = null;

    canvas.addEventListener('pointerdown', e => {
        _drag.active   = true;
        _drag.lastX    = e.clientX;
        _drag.lastY    = e.clientY;
        _drag.travelSq = 0;
        canvas.setPointerCapture(e.pointerId);

        // Touch long-press → flag (right-click equivalent)
        if (e.pointerType === 'touch') {
            _longPress = setTimeout(() => {
                _longPress = null;
                if (_drag.travelSq < 36) _doRaycast(e, 2);
            }, 500);
        }
    });

    canvas.addEventListener('pointermove', e => {
        if (!_drag.active) return;
        const dx = e.clientX - _drag.lastX;
        const dy = e.clientY - _drag.lastY;
        _drag.travelSq += dx * dx + dy * dy;
        _drag.lastX = e.clientX;
        _drag.lastY = e.clientY;

        if (_drag.travelSq > 4 && _longPress) {
            clearTimeout(_longPress);
            _longPress = null;
        }

        const len = Math.sqrt(dx * dx + dy * dy);
        if (len < 0.001) return;
        const axis  = new THREE.Vector3(dy / len, dx / len, 0);
        const q     = new THREE.Quaternion().setFromAxisAngle(axis, len * 0.005);
        _globeGroup.quaternion.premultiply(q);
    });

    canvas.addEventListener('pointerup', e => {
        if (_longPress) { clearTimeout(_longPress); _longPress = null; }
        if (_drag.active && _drag.travelSq < 36) _doRaycast(e, e.button);
        _drag.active = false;
    });

    // Suppress browser context menu on right-click
    canvas.addEventListener('contextmenu', e => e.preventDefault());
}

function _doRaycast(e, button) {
    const rect  = _renderer.domElement.getBoundingClientRect();
    const mouse = new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width)  *  2 - 1,
        ((e.clientY - rect.top)  / rect.height) * -2 + 1,
    );
    _raycaster.setFromCamera(mouse, _camera);
    const hits = _raycaster.intersectObjects(_faceMeshes);
    if (hits.length) faceClicked(hits[0].object.userData.faceIdx, button);
}

// ---------------------------------------------------------------------------
// Sprite overlays — number labels, flags, mines
// ---------------------------------------------------------------------------

function _makeSprite(text, color, size) {
    const c   = document.createElement('canvas');
    c.width   = c.height = 128;
    const ctx = c.getContext('2d');
    ctx.clearRect(0, 0, 128, 128);
    ctx.font         = 'bold 80px sans-serif';
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle    = color;
    ctx.fillText(text, 64, 64);
    const mat = new THREE.SpriteMaterial({
        map: new THREE.CanvasTexture(c),
        transparent: true,
        depthTest:   false,
    });
    const spr = new THREE.Sprite(mat);
    spr.scale.set(size, size, 1);
    return spr;
}

function _clearSprite(idx) {
    if (!_sprites[idx]) return;
    _globeGroup.remove(_sprites[idx]);
    _sprites[idx].material.map.dispose();
    _sprites[idx].material.dispose();
    _sprites[idx] = null;
}

function _placeSprite(idx, text, color) {
    _clearSprite(idx);
    const face = _globeData.faces[idx];
    const size = face.isPentagon ? 0.18 : 0.22;
    const spr  = _makeSprite(text, color, size);
    const c    = face.centroid;
    spr.position.set(c.x * 1.02, c.y * 1.02, c.z * 1.02);
    _globeGroup.add(spr);
    _sprites[idx] = spr;
}

// ---------------------------------------------------------------------------
// updateFaceVisual — called by G3 on every face-state change
// ---------------------------------------------------------------------------

function updateFaceVisual(idx) {
    if (!faceState || !_faceMeshes[idx]) return;

    const state = faceState[idx];
    const mesh  = _faceMeshes[idx];

    // Classic skin: tile always visible; recolor by state
    mesh.visible = true;
    _clearSprite(idx);

    const mineEmoji = (typeof getMineEmoji === 'function') ? getMineEmoji() : '💣';
    const flagEmoji = (typeof getFlagEmoji === 'function') ? getFlagEmoji() : '🚩';

    switch (state) {
        case HIDDEN:
            mesh.material.color.set(_css('--glob-hidden'));
            break;

        case REVEALED:
            mesh.material.color.set(_css('--glob-rev'));
            if (adjCount && adjCount[idx] > 0) {
                _placeSprite(idx, String(adjCount[idx]),
                    _NUM_COLORS[adjCount[idx]] || '#ffffff');
            }
            break;

        case FLAGGED:
            mesh.material.color.set(_css('--glob-hidden'));
            _placeSprite(idx, flagEmoji, '#ffffff');
            break;

        case QUESTION:
            mesh.material.color.set(_css('--glob-hidden'));
            _placeSprite(idx, '?', '#ffdd44');
            break;

        case MINE:
            mesh.material.color.set(_css('--glob-mine'));
            _placeSprite(idx, mineEmoji, '#ffffff');
            break;

        case DETONATED:
            mesh.material.color.set(_css('--glob-detonated'));
            _placeSprite(idx, mineEmoji, '#ffffff');
            break;
    }
}

// ---------------------------------------------------------------------------
// G3 — Game logic
// ---------------------------------------------------------------------------

// ── Internal state helpers ──────────────────────────────────────────────────

function _initGameState() {
    const F = _globeData.faces.length;
    faceState.fill(HIDDEN);
    adjCount.fill(0);
    mineSet    = new Set();
    gameOver   = false;
    firstClick = true;
    _stopTimer();
    document.getElementById('elapsed').textContent = '0.00';
    document.getElementById('mines-remaining').textContent = String(_mineCount);
    document.getElementById('globe-overlay').style.display = 'none';
    for (let i = 0; i < F; i++) updateFaceVisual(i);
}

// ── Mine generation — Fisher-Yates partial shuffle ──────────────────────────

function _generateMines(F, count, safeIdx) {
    const pool = Array.from({ length: F }, (_, i) => i).filter(i => i !== safeIdx);
    const mines = new Set();
    for (let i = 0; i < count; i++) {
        const j = i + Math.floor(Math.random() * (pool.length - i));
        [pool[i], pool[j]] = [pool[j], pool[i]];
        mines.add(pool[i]);
    }
    return mines;
}

function _computeAdjCount() {
    const adj = _globeData.adj;
    adjCount.fill(0);
    for (const m of mineSet) {
        for (const nb of adj[m]) adjCount[nb]++;
    }
}

// ── Reveal ──────────────────────────────────────────────────────────────────

function revealFace(idx) {
    if (gameOver || faceState[idx] !== HIDDEN) return;

    if (firstClick) {
        firstClick = false;
        mineSet = _generateMines(_globeData.faces.length, _mineCount, idx);
        _computeAdjCount();
        _startTimer();
    }

    const adj = _globeData.adj;

    if (mineSet.has(idx)) {
        faceState[idx] = DETONATED;
        for (const m of mineSet) {
            if (faceState[m] === HIDDEN) faceState[m] = MINE;
            updateFaceVisual(m);
        }
        updateFaceVisual(idx);
        _triggerGameOver(false);
        return;
    }

    // BFS flood-fill for zero-adjacency cells
    const queue = [idx];
    faceState[idx] = REVEALED;
    updateFaceVisual(idx);
    if (adjCount[idx] === 0) {
        while (queue.length) {
            const cur = queue.shift();
            for (const nb of adj[cur]) {
                if (faceState[nb] !== HIDDEN || mineSet.has(nb)) continue;
                faceState[nb] = REVEALED;
                updateFaceVisual(nb);
                if (adjCount[nb] === 0) queue.push(nb);
            }
        }
    }
    _checkWin();
}

// ── Flag cycling ─────────────────────────────────────────────────────────────

function cycleFlagFace(idx) {
    if (gameOver) return;
    const s = faceState[idx];
    if (s === REVEALED) return;  // can't flag a revealed cell

    if (s === HIDDEN) {
        faceState[idx] = FLAGGED;
    } else if (s === FLAGGED) {
        faceState[idx] = QUESTION;
    } else if (s === QUESTION) {
        faceState[idx] = HIDDEN;
    }
    updateFaceVisual(idx);
    _updateMineCounter();
}

function _updateMineCounter() {
    const flagged = faceState.reduce((n, s) => n + (s === FLAGGED ? 1 : 0), 0);
    document.getElementById('mines-remaining').textContent = String(_mineCount - flagged);
}

// ── Win check ────────────────────────────────────────────────────────────────

function _checkWin() {
    const F = _globeData.faces.length;
    let revealed = 0;
    for (let i = 0; i < F; i++) if (faceState[i] === REVEALED) revealed++;
    if (revealed === F - _mineCount) _triggerGameOver(true);
}

// ── Win / loss overlay ────────────────────────────────────────────────────────

function _triggerGameOver(won) {
    gameOver = true;
    _stopTimer();
    triggerPulse();
    document.getElementById('overlay-msg').textContent = won ? '🎉 You win!' : '💥 Game over!';
    document.getElementById('globe-overlay').style.display = 'flex';
    if (won) _showScoreForm();
}

function _showScoreForm() {
    // G5 will implement score submission here.
}

// ── Reset ─────────────────────────────────────────────────────────────────────

function resetGame() {
    _initGameState();
}

// ── Entry point for clicks ────────────────────────────────────────────────────

function faceClicked(idx, button) {
    if (button === 2) {
        cycleFlagFace(idx);
    } else {
        revealFace(idx);
    }
}

// ── Board hash ────────────────────────────────────────────────────────────────

function boardToHash(mines, F) {
    const bytes = new Uint8Array(Math.ceil(F / 8));
    for (const i of mines) bytes[i >> 3] |= 1 << (i & 7);
    return btoa(String.fromCharCode(...bytes))
        .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function hashToBoard(hash, F) {
    const b64   = hash.replace(/-/g, '+').replace(/_/g, '/');
    const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
    const mines = new Set();
    for (let i = 0; i < F; i++) {
        if (bytes[i >> 3] & (1 << (i & 7))) mines.add(i);
    }
    return mines;
}

// ── Timer ─────────────────────────────────────────────────────────────────────

function _startTimer() {
    _startTime = performance.now();
    _timerHandle = setInterval(() => {
        const s = ((performance.now() - _startTime) / 1000).toFixed(2);
        document.getElementById('elapsed').textContent = s;
    }, 100);
}

function _stopTimer() {
    clearInterval(_timerHandle);
    _timerHandle = null;
}

// ---------------------------------------------------------------------------
// triggerPulse — brief camera zoom on win/loss
// ---------------------------------------------------------------------------

function triggerPulse() {
    _pulse = { t0: performance.now(), baseZ: 3.5, peakZ: 3.675, dur: 300 };
}

// ---------------------------------------------------------------------------
// Render loop
// ---------------------------------------------------------------------------

function _animate() {
    requestAnimationFrame(_animate);

    if (_pulse) {
        const t = (performance.now() - _pulse.t0) / _pulse.dur;
        if (t >= 1) {
            _camera.position.z = _pulse.baseZ;
            _pulse = null;
        } else {
            const frac = t < 0.5 ? t * 2 : (1 - t) * 2;
            _camera.position.z = _pulse.baseZ + (_pulse.peakZ - _pulse.baseZ) * frac;
        }
    }

    _renderer.render(_scene, _camera);
}
