# F55 Globesweeper — Implementation Plan

This document breaks F55 (Globesweeper) into discrete implementation subtasks
organised across two phases.

**Phase 1** delivers a fully playable game on the 32-face GP(1,1) soccer-ball
board (the truncated icosahedron). The entire stack — geometry, rendering, game
logic, Classic skin, scoring — is validated on one fixed board before any
generalisation work begins.

**Phase 2** extends the working game to support selectable GP(a,b) board sizes
via a T-selector UI, implements the remaining subdivision classes (I and III),
and adds the Earth visual skin with texture assets.

The feature spec lives in Features.md under F55.

## Status of existing work

| Asset | Status |
|---|---|
| Routes in `main.py` | ✓ Done |
| `GlobesweeperScore` model in `database_template.py` | ✓ Done |
| `templates/globesweeper.html` | ✓ Done (HTML shell, data attrs, canvas, custom form) |
| `templates/globesweeper_leaderboard.html` | ✓ Done |
| `static/js/vendor/three.min.js` | ✓ Done |
| Asset | Phase | Status |
|---|---|---|
| Routes in `main.py` | — | ✓ Done |
| `GlobesweeperScore` model in `database_template.py` | — | ✓ Done |
| `templates/globesweeper.html` | — | ✓ Done (HTML shell, data attrs, canvas, custom form) |
| `templates/globesweeper_leaderboard.html` | — | ✓ Done |
| `static/js/vendor/three.min.js` | — | ✓ Done |
| `static/js/goldberg.js` (G1a-alpha: icosahedron base + Class I → dodecahedron) | 1 | ✗ Not started |
| `static/js/goldberg.js` (G1a-beta: Class II subdivision → soccer ball GP(1,1)) | 1 | ✗ Not started |
| `static/js/goldberg.js` (G1b: dual + adjacency) | 1 | ✗ Not started |
| `static/js/goldberg.js` (G1c: export + GP(1,1) tests) | 1 | ✗ Not started |
| `static/js/globesweeper.js` (G2: Classic skin, hardcoded GP(1,0)) | 1 | ✓ Done |
| `static/js/globesweeper.js` (G3: game logic) | 1 | ✓ Done |
| CSS `--glob-*` variables, Classic theme | 1 | ✗ Not started |
| Score submission form (post-win) | 1 | ✗ Not started |
| Globesweeper in nav mega-menu (`base.html`) | 1 | ✗ Not started |
| Sitemap entry (`/globesweeper`) | 1 | ✗ Not started |
| `static/js/goldberg.js` (Class I + III generalisation + full tests) | 2 | ✗ Not started |
| T-selector UI + dynamic `goldberg(a,b)` | 2 | ✗ Not started |
| Earth skin (textured sphere + starfield) | 2 | ✗ Not started |
| CSS Earth theme (`[data-glob-skin="earth"]`) | 2 | ✗ Not started |
| `static/img/earth.jpg` (equirectangular world map) | 2 | ✗ Not started |
| `static/img/milkyway.jpg` (starfield background) | 2 | ✗ Not started |
| Remaining sitemap entries (intermediate/expert/custom/leaderboard) | 2 | ✗ Not started |

---

## Visual themes (concept art reference)

Two concept art screenshots live in `screenshots/`:

| File | Theme name | Hidden tiles | Revealed tiles | Background |
|---|---|---|---|---|
| `GlobesweeperWithWhiteReveal.png` | **Classic** | Dark metallic gray, orange-gold border | Plain white | Warm orange radial gradient |
| `GlobesweeperWithGlobeReveal.png` | **Earth** | Warm orange, darker border | Earth map texture shows through | Milky Way / deep space starfield |

The active theme is controlled by a `data-glob-skin` attribute on the canvas wrapper
(`"classic"` or `"earth"`). The default is `"classic"`. A skin picker can be added to
the custom board form later.

### Required texture assets (source before G2 ships)

| File | Spec | Source suggestion |
|---|---|---|
| `static/img/earth.jpg` | Equirectangular, ≥ 4096×2048, RGB | NASA Blue Marble (public domain) |
| `static/img/milkyway.jpg` | Any aspect ratio, ≥ 2048 wide | NASA/ESA Milky Way panorama (public domain) |

---

---

## Phase 1 — GP(1,1) Proof of Concept (soccer ball, F=32)

**Goal:** Ship a fully playable Globesweeper on the 32-face truncated icosahedron.
Review the concept — feel, performance, visual polish — before generalising.

| Restriction | Phase 1 decision |
|---|---|
| Board geometry | GP(1,1) only — `goldberg(1,1)` hardcoded in globesweeper.js |
| Subdivision classes | Class II (a=b) only — sufficient for GP(1,1) |
| Visual skin | Classic only — no Earth skin, no texture assets required |
| Score modes | beginner / intermediate / expert by mine count on F=32 |
| Nav / sitemap | `/globesweeper` route only; one sitemap URL |

---

## Phase 1 — Subtask G1a — goldberg.js: Icosahedron base + geodesic subdivision

G1a is split into three incremental sub-tasks so each can be reviewed independently:

| Sub-task | Class | GP | F | Status |
|---|---|---|---|---|
| G1a-alpha | I (b=0) | GP(1,0) | 12 (dodecahedron) | ✗ Not started |
| G1a-beta  | II (a=b) | GP(1,1) | 32 (soccer ball) | ✗ Not started |
| G1a-gamma | III (general) | GP(a,b) | any | Deferred to Phase 2 |

---

### G1a-alpha — Class I subdivision → dodecahedron (GP(1,0), F=12)

**File:** `static/js/goldberg.js` (create file; scaffold + Class I only)
**Depends on:** nothing
**Goal:** Produce the dual of the un-subdivided icosahedron — a dodecahedron with
12 pentagonal faces — as a smoke-test that the base icosahedron and dual-building
pipeline are correct before subdivision is added.

**Icosahedron base**
Define the 12 vertices of a unit icosahedron using the golden-ratio formula
and the 20 triangular faces as index triples. These are constants at the top
of the file and are shared by all sub-tasks.

**Step 1 — Class I subdivision (b=0)**
For `a=1, b=0` (T=1) no sub-division is needed — each icosahedron triangle maps
directly to itself. Implement the general Class I loop anyway so `a=2` works too:
subdivide each face into `a²` sub-triangles using a barycentric grid on `(u, v)`:
```
for i in 0..a, j in 0..a-i:
    u = i/a, v = j/a, w = 1 - u - v
    P = u*P0 + v*P1 + w*P2  →  normalise to unit sphere
```
Emit two triangles per grid cell where both fit inside the face.

**Step 2 — Merge duplicate vertices**
Shared icosahedron edges produce duplicate vertices. Merge any two vertices
within `ε = 1e-9` of each other using a string-keyed map
(`"${x.toFixed(9)},${y.toFixed(9)},${z.toFixed(9)}"` → canonical index).
Re-map each triangle's vertex indices to canonical indices.

Return value of internal `subdivide(a, b)`:
```js
{
    verts: [{x, y, z}, ...],   // unique unit-sphere vertices
    tris:  [{i0, i1, i2}, ...]  // triangles as index triples into verts
}
```

**Step 3 — Build dual (dodecahedron faces)**
For each unique vertex `V` in `verts`, collect all triangles containing it (the
fan), sort the fan triangles in cyclic angular order around `V`, compute each
triangle's centroid projected to unit sphere, and emit those ordered centroids
as the vertices of one Goldberg face. Valence 5 → pentagon (all faces for GP(1,0)).

**Acceptance criteria (G1a-alpha)**
- `subdivide(1, 0)` → 12 verts, 20 tris (no subdivision)
- `buildDual(...)` on GP(1,0) output → 12 faces, all pentagons, each with 5 neighbours
- Every vertex has unit length (≤ 1e-9 error from 1.0)
- No duplicate vertices (all pairwise distances > 1e-9)
- Adjacency symmetric: `j ∈ adj[i]` iff `i ∈ adj[j]`

**Console test:**
```js
const {verts,tris} = subdivide(1,0);
console.assert(verts.length === 12 && tris.length === 20);
const {faces,adj} = buildDual(verts,tris);
console.assert(faces.length === 12 && faces.every(f => f.isPentagon));
```

---

### G1a-beta — Class II subdivision → soccer ball (GP(1,1), F=32)

**File:** `static/js/goldberg.js` (extends G1a-alpha)
**Depends on:** G1a-alpha (same file)
**Goal:** Extend `subdivide` to handle Class II (`a = b`) and verify the full
32-face truncated icosahedron used by the game.

**Step 1 — Class II subdivision (a=b)**
For `a=b=1` (T=3) each icosahedron triangle is split into 3 sub-triangles.
The general Class II pattern for parameter `n = a`:
- Divide each edge into `2n` segments using the hexagonal lattice rotated 30°.
- The canonical approach: generate barycentric coordinates for the `T = 3n²`
  sub-triangles using the skewed `(s, t)` lattice with `s + t ≤ 2n`:
  ```
  for s in 0..2n, t in 0..2n-s (step by 1):
      emit sub-triangles at (s,t), (s+1,t), (s,t+1) mapped through:
      u = (2s - t) / (3n),  v = (2t - s) / (3n),  w = 1 - u - v
      (only emit when u,v,w ≥ 0)
  ```
  Project each vertex to the unit sphere. Merge duplicates as in G1a-alpha.

**Acceptance criteria (G1a-beta)**
- `subdivide(1, 1)` → T=3, so 20×3=60 tris, 32 verts
- `buildDual(...)` on GP(1,1) output → 32 faces: 12 pentagons + 20 hexagons
- Pentagon faces have 5 neighbours, hexagons have 6
- All adjacency symmetric

**Console test:**
```js
const {verts,tris} = subdivide(1,1);
console.assert(verts.length === 32 && tris.length === 60);
const {faces,adj} = buildDual(verts,tris);
console.assert(faces.length === 32);
console.assert(faces.filter(f => f.isPentagon).length === 12);
```

---

### G1a-gamma — Class III (general) — Deferred to Phase 2

Class III handles the skewed case where `a ≠ b` and `b ≠ 0`. Deferred until
Phase 2 after the GP(1,1) game is reviewed.

Phase 2 will add:
- `subdivide(2, 1)` → T=7, 140 tris (Class III)
- `subdivide(2, 0)` → T=4, 80 tris, 42 verts (Class I, larger board)
- Full test suite in `src/__tests__/goldberg.test.js`

---

## Phase 1 — Subtask G1b — goldberg.js: Dual polyhedron + adjacency

**File:** `static/js/goldberg.js` (continues from G1a)
**Depends on:** G1a (`subdivide` function in the same file)
**Output contract:** a module-level function `buildDual(verts, tris)` that
returns `{ faces, adj }` — the Goldberg polygon faces and their adjacency.

### What to implement

**Step 3 — Build the dual (= Goldberg polyhedron)**
For each unique vertex `V` (index `vi`) in `verts`:
  1. Collect all triangles that contain `vi` — this is the fan.
  2. Sort fan triangles in angular order around `V`:
     - Pick any fan triangle as start.
     - Greedily append the next triangle that shares an edge with the
       previous one (shared edge = two vertices in common, one of which is `vi`).
     - This gives a cyclic ordering of the fan.
  3. Compute each fan triangle's centroid and project to the unit sphere.
  4. The ordered list of projected centroids = vertices of one Goldberg face.
  5. Valence 5 vertex → pentagon; valence 6 → hexagon.

Each Goldberg face:
```js
{ verts: [{x,y,z}, ...], centroid: {x,y,z}, isPentagon: bool }
```
(centroid = average of the Goldberg face vertices, projected to unit sphere)

**Step 4 — Compute adjacency**
Two Goldberg faces `i` and `j` are neighbours iff their vertex arrays share
exactly 2 consecutive vertices (cyclically). Because each Goldberg face vertex
is a geodesic triangle centroid, the key insight is: two Goldberg faces share
an edge iff they were built from two geodesic triangles that share an edge,
and those triangles each contain the same pair of adjacent vertices around
`vi` and `vj`. A simpler implementation:

For each pair of Goldberg faces, check if they share ≥ 2 vertices within
ε = 1e-9. Mark as neighbours. Because F is at most 252 (for the largest
supported board) this O(F²) check is acceptable.

Return value of `buildDual(verts, tris)`:
```js
{ faces: [...], adj: [[neighbourIdx, ...], ...] }
```

### Acceptance criteria
- `buildDual` on `subdivide(1,0)` output → 12 faces, all pentagons, each has 5 neighbours
- `buildDual` on `subdivide(1,1)` output → 32 faces, 12 pentagons + 20 hexagons
- `adj` is symmetric: if `j ∈ adj[i]` then `i ∈ adj[j]`
- Pentagon faces each have exactly 5 neighbours; hexagons have 6

---

## Phase 1 — Subtask G1c — goldberg.js: Canonical indexing, export, cache, tests

**File:** `static/js/goldberg.js` (final pass) + `src/__tests__/goldberg.test.js`
**Depends on:** G1a + G1b (all steps in same file)
**Exported API:** `goldberg(a, b)` → `{ faces, adj, T, F, pentagons }`

### What to implement

**Step 5 — Canonical face indexing**
Sort all `F` face centroids lexicographically by `(x, y, z)` rounded to
6 decimal places. Assign 0-based indices in that order. Re-index `adj`
to match the sorted order. This ensures a deterministic ordering for
`boardToHash`.

**Step 6 — Export + cache**
```js
const _cache = new Map();

export function goldberg(a, b) {
    const key = `${a},${b}`;
    if (_cache.has(key)) return _cache.get(key);

    const { verts, tris } = subdivide(a, b);
    const { faces, adj }  = buildDual(verts, tris);
    // ... canonical sort, re-index adj ...
    const T = a*a + a*b + b*b;
    const F = 10*T + 2;
    const pentagons = new Set(faces.map((f, i) => f.isPentagon ? i : -1).filter(i => i >= 0));
    const result = { faces, adj, T, F, pentagons };
    _cache.set(key, result);
    return result;
}
```

### Acceptance criteria (Phase 1 — GP(1,1) only)
- `goldberg(1, 1)` → F=32, 12 pentagons + 20 hexagons  ← **must pass in Phase 1**
- Each face in `adj` is bidirectionally consistent
- Canonical indices are stable: two calls with `(1, 1)` return identical assignments

Phase 2 will add:
- `goldberg(1, 0)` → F=12, all pentagons, every face has 5 neighbours
- `goldberg(2, 1)` → F=72
- `goldberg(5, 0)` → F=252

### Testing
Write `src/__tests__/goldberg.test.js` covering the GP(1,1) case + stability check.
Phase 2 expands this to all board sizes. Run with `npx jest`.

---

## Phase 1 — Subtask G2 — globesweeper.js Part 1: Three.js scene and rendering

**File:** `static/js/globesweeper.js`
**Depends on:** G1 (goldberg.js), Three.js vendor
**Scope:** scene setup, face meshes, rotation, raycasting, sprite overlays
**Phase 1 restriction:** Classic skin only. Hardcode `goldberg(1,1)` — no T-selector.
Earth skin (inner textured sphere + starfield background) is deferred to Phase 2.

### Scene setup (called by `initGlobe`)

```
WebGLRenderer — antialias: true, alpha: true
  attach to #globe-canvas
  size = container clientWidth × clientHeight
  resize on window resize

PerspectiveCamera — FOV 45°, near 0.1, far 100
  position (0, 0, 3.5), lookAt origin

AmbientLight   (0xffffff, 0.6)
DirectionalLight (0xffffff, 0.8) at (5, 5, 5)

globeGroup = THREE.Group()  ← all face meshes go here
scene.add(globeGroup)
```

Read CSS variables at init time via `getComputedStyle(document.documentElement)`:
```
--glob-hidden, --glob-hidden-border, --glob-rev,
--glob-mine, --glob-detonated
```

Read `data-glob-skin` from the canvas wrapper element to determine the active theme
(`"classic"` or `"earth"`). Store as `const skin`.

**Scene background (skin-dependent)**

- Classic skin: set CSS `background` on the canvas container to a warm orange radial
  gradient (`radial-gradient(ellipse at center, #c87941 0%, #7a3d10 100%)`). Leave
  `renderer.setClearColor(0x000000, 0)` (transparent) so the CSS shows through.
- Earth skin: load `static/img/milkyway.jpg` via `THREE.TextureLoader` and assign to
  `scene.background`. No CSS gradient needed.

### Globe mesh construction

**Earth skin only — inner textured sphere**

Before building face meshes, add a base sphere that the revealed tiles expose:
```js
if (skin === 'earth') {
    const earthTex = new THREE.TextureLoader().load('/static/img/earth.jpg')
    const earthGeo = new THREE.SphereGeometry(0.97, 64, 32)
    const earthMat = new THREE.MeshLambertMaterial({ map: earthTex })
    globeGroup.add(new THREE.Mesh(earthGeo, earthMat))
}
```
Radius 0.97 sits just inside the tile layer at 0.98. UV mapping is automatic
on `SphereGeometry`.

**Face tile meshes (both skins)**

For each Goldberg face `i`:
1. Project verts to unit sphere, scale to 0.98.
2. Fan-triangulate: `[centroid_at_0.98, verts[j], verts[j+1]]` for each edge.
3. Build `THREE.BufferGeometry` from the triangles.
4. Create `THREE.MeshPhongMaterial({ color: HIDDEN_COLOR, shininess: 60, side: THREE.FrontSide })`.
   (Phong instead of Lambert gives the beveled highlight visible in concept art.)
5. Create `THREE.Mesh(geometry, material)`.
6. Add to `globeGroup`. Store in `faceMeshes[i]`.

Border lines: for each face edge, create a `THREE.Line` at radius 1.001
using `--glob-hidden-border` color. Add to `globeGroup`.

### Rotation (drag)

Track `pointerdown` → `pointermove` → `pointerup` on the canvas.
- On `pointermove` while dragging: compute delta `(dx, dy)`.
  Apply rotation to `globeGroup` as quaternion:
  ```
  axis = normalize(dy, dx, 0)   // perpendicular to drag direction
  angle = sqrt(dx²+dy²) * sensitivity
  globeGroup.quaternion.premultiply(new THREE.Quaternion().setFromAxisAngle(axis, angle))
  ```
- Track total pointer travel. If < 6 px at `pointerup`, treat as a click.

### Face picking (raycasting)

On click:
```js
raycaster.setFromCamera(normalizedMouse, camera)
const hits = raycaster.intersectObjects(faceMeshes)
if (hits.length) faceClicked(hits[0].object.userData.faceIdx, button)
```
- Left click / tap → `revealFace(idx)`
- Right click / long press (500 ms timer) → `cycleFlagFace(idx)`

### Sprite overlays (numbers, mines, flags)

Use `THREE.Sprite` with a `Canvas2D` texture:
- Pool of sprites reused across face updates.
- `makeSprite(text, color, size)` → draws text onto an offscreen canvas →
  `THREE.CanvasTexture` → `THREE.SpriteMaterial` → `THREE.Sprite`.
- Position sprite at `face.centroid * 1.02` (slightly above surface).
- Scale sprite to face size (approx `0.22` for hexagons, `0.18` for pentagons).

Number colors: use `NUM_COLORS_*` from `minesweeper.js` (import or duplicate).
Mine emoji: `getMineEmoji()` from `minesweeper.js`.
Flag emoji: `getFlagEmoji()` from `minesweeper.js`.

### updateFaceVisual(idx)

Called whenever face state changes.

**Classic skin:**
- Set `faceMeshes[idx].material.color` based on state (HIDDEN → `--glob-hidden`,
  REVEALED → `--glob-rev`, MINE → `--glob-mine`, DETONATED → `--glob-detonated`).
- `faceMeshes[idx].visible = true` always.

**Earth skin:**
- If state is REVEALED (and not a mine): set `faceMeshes[idx].visible = false`
  so the inner Earth sphere shows through. Do not recolor.
- All other states (HIDDEN, FLAGGED, QUESTION, MINE, DETONATED): keep
  `faceMeshes[idx].visible = true` and set material color normally.

**Both skins:**
- Remove existing sprite for `idx` if any.
- If REVEALED and `adjCount[idx] > 0`: add number sprite.
- If FLAGGED: add flag sprite.
- If QUESTION: add `?` sprite.
- If MINE or DETONATED: add mine sprite.

### Render loop

```js
function animate() {
    requestAnimationFrame(animate)
    renderer.render(scene, camera)
}
animate()
```

Win/loss: brief camera pulse — tween `camera.position.z` 3.5 → 3.675 → 3.5
over 300 ms using linear interpolation in the render loop.

---

## Phase 1 — Subtask G3 — globesweeper.js Part 2: game logic

**File:** `static/js/globesweeper.js` (same file, continues from G2)
**Depends on:** G1 (goldberg.js output)
**Scope:** state machine, mine generation, reveal, hash, win/loss, timer

### Constants

```js
const HIDDEN    = 0;
const REVEALED  = 1;
const FLAGGED   = 2;
const QUESTION  = 3;
const MINE      = 4;
const DETONATED = 5;
```

### State

```js
let faceState   // Uint8Array[F]  — per-face state
let mineSet     // Set<number>
let adjCount    // Uint8Array[F]  — mine neighbour count per face
let gameOver    // bool
let firstClick  // bool — true until first reveal
let startTime   // performance.now() when first click
let timerHandle // setInterval id
```

### generateMines(faces, adj, count, safeIdx)

```js
function generateMines(F, count, safeIdx) {
    const pool = [...Array(F).keys()].filter(i => i !== safeIdx)
    // Fisher-Yates partial shuffle to pick `count` indices
    const mines = new Set()
    for (let i = 0; i < count; i++) {
        const j = i + Math.floor(Math.random() * (pool.length - i))
        ;[pool[i], pool[j]] = [pool[j], pool[i]]
        mines.add(pool[i])
    }
    return mines
}
```

### Pre-compute adjCount

```js
adjCount = new Uint8Array(F)
for (const m of mineSet)
    for (const nb of adj[m])
        adjCount[nb]++
```

### revealFace(idx)

```js
function revealFace(idx) {
    if (gameOver || faceState[idx] !== HIDDEN) return

    if (firstClick) {
        firstClick = false
        mineSet = generateMines(F, mineCount, idx)
        // recompute adjCount
        startTimer()
    }

    if (mineSet.has(idx)) {
        faceState[idx] = DETONATED
        // reveal all mines
        for (const m of mineSet) {
            if (faceState[m] === HIDDEN) faceState[m] = MINE
            updateFaceVisual(m)
        }
        updateFaceVisual(idx)
        triggerGameOver(false)
        return
    }

    // BFS flood-fill for zeros
    const queue = [idx]
    faceState[idx] = REVEALED
    updateFaceVisual(idx)
    if (adjCount[idx] === 0) {
        while (queue.length) {
            const cur = queue.shift()
            for (const nb of adj[cur]) {
                if (faceState[nb] !== HIDDEN || mineSet.has(nb)) continue
                faceState[nb] = REVEALED
                updateFaceVisual(nb)
                if (adjCount[nb] === 0) queue.push(nb)
            }
        }
    }
    checkWin()
}
```

### cycleFlagFace(idx)

Cycles `HIDDEN → FLAGGED → QUESTION → HIDDEN`.
Updates mine-counter display (`--mines-remaining`).

### checkWin

Win condition: every non-mine face is REVEALED.
```js
function checkWin() {
    const revealedCount = faceState.filter(s => s === REVEALED).length
    if (revealedCount === F - mineCount) triggerGameOver(true)
}
```

### boardToHash / hashToBoard

```js
function boardToHash(mineSet, F) {
    const bytes = new Uint8Array(Math.ceil(F / 8))
    for (const i of mineSet) bytes[i >> 3] |= 1 << (i & 7)
    return btoa(String.fromCharCode(...bytes))
        .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function hashToBoard(hash, F) {
    const b64 = hash.replace(/-/g, '+').replace(/_/g, '/')
    const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0))
    const mines = new Set()
    for (let i = 0; i < F; i++)
        if (bytes[i >> 3] & (1 << (i & 7))) mines.add(i)
    return mines
}
```

### Timer

```js
function startTimer() {
    startTime = performance.now()
    timerHandle = setInterval(() => {
        const s = ((performance.now() - startTime) / 1000).toFixed(2)
        document.getElementById('elapsed').textContent = s
    }, 100)
}
function stopTimer() { clearInterval(timerHandle) }
```

### Win/loss overlay

```js
function triggerGameOver(won) {
    gameOver = true
    stopTimer()
    const overlay = document.getElementById('globe-overlay')
    document.getElementById('overlay-msg').textContent =
        won ? '🎉 You win!' : '💥 Game over!'
    overlay.style.display = 'flex'
    pulseCameraAnimation()
    if (won) showScoreForm()
}
```

### initGlobe(a, b, mineCount, canvasId)

Orchestrates all of the above:
1. Call `goldberg(a, b)` to get geometry.
2. Initialise Three.js scene (G2).
3. Build face meshes (G2).
4. Reset game state.
5. Attach pointer event listeners.
6. Start render loop.

Reset button (`#reset-btn`) calls `resetGame()` which clears state and re-runs
mine generation setup (keeping geometry).

---

## Phase 1 — Subtask G4 — CSS skin variables (Classic theme only)

**File:** `static/css/style.css`
**Depends on:** nothing
**Scope:** add `--glob-*` CSS variables to each site skin block, and define the
two globe-specific visual themes (Classic and Earth) driven by `data-glob-skin`.
**Phase 1 restriction:** Implement Classic theme CSS variables only. The
`[data-glob-skin="earth"]` block and texture assets are deferred to Phase 2.

### Site skin CSS variables — add to each existing skin block

These drive face colors for the Classic globe theme. Add to `:root` / `.skin-dark`
and override in each other skin:

```css
--glob-hidden:         #2a3a5c;
--glob-hidden-border:  #3a5278;
--glob-rev:            #e8e8e8;   /* white-ish for Classic reveal */
--glob-mine:           #7a0000;
--glob-detonated:      #c00000;
```

Add `--glob-*` override blocks in each existing skin (light, etc.).
At minimum ensure `--glob-hidden` and `--glob-rev` have sufficient contrast
for the number sprites.

### Globe theme overrides — driven by `data-glob-skin` on the canvas wrapper

These override the face colors for the Earth theme and set the canvas background
for Classic. Add after the site skin blocks:

```css
/* Classic theme — warm orange background applied via JS (radial gradient) */
[data-glob-skin="classic"] {
    --glob-hidden:        #4a4a4a;   /* dark metallic gray */
    --glob-hidden-border: #c8892a;   /* orange-gold border (concept art) */
    --glob-rev:           #e8e8e8;   /* plain white reveal */
    --glob-mine:          #7a0000;
    --glob-detonated:     #c00000;
}

/* Earth theme — Milky Way background set via scene.background in JS */
[data-glob-skin="earth"] {
    --glob-hidden:        #c87020;   /* warm orange tiles (concept art) */
    --glob-hidden-border: #7a4010;   /* darker orange border */
    /* --glob-rev not used in Earth skin — face mesh is hidden on reveal */
    --glob-mine:          #7a0000;
    --glob-detonated:     #c00000;
}
```

The `globesweeper.html` template sets `data-glob-skin` on the canvas wrapper.
Default is `"classic"`. A skin toggle (button or select) can be added to the
custom board form in a later pass.

---

## Phase 1 — Subtask G5 — Score submission (post-win)

**File:** `templates/globesweeper.html`
**Depends on:** G3 (game logic exposes `finalTimeMs`, `boardHash`)
**Scope:** add a score submission form that appears in the win overlay

### Form HTML

Add inside `#globe-overlay` (below the Play Again button):

```html
<div id="score-form" style="display:none;margin-top:1rem;text-align:center;">
  <input id="score-name" type="text" maxlength="32" placeholder="Your name"
         style="padding:0.4rem;border-radius:4px;border:1px solid var(--border);">
  <button id="score-submit" class="btn" style="margin-left:0.5rem;">Submit</button>
  <p id="score-msg" style="font-size:0.85rem;margin-top:0.5rem;"></p>
</div>
```

### Submission JS (in globesweeper.js)

```js
async function submitScore(name) {
    const payload = {
        name,
        time_ms:    Math.round(performance.now() - startTime),
        glob_mode:  mode,          // 'beginner'|'intermediate'|'expert'|'custom'
        t_param:    T,
        face_count: F,
        mines:      mineCount,
        board_hash: boardToHash(mineSet, F),
    }
    const r = await fetch('/api/globesweeper-scores', {
        method:  'POST',
        headers: {'Content-Type': 'application/json'},
        body:    JSON.stringify(payload),
    })
    return r.ok
}
```

Pre-fill name from localStorage (`globesweeper_name`) if available.
On success: show "Score saved! View leaderboard →" with link.
On error: show error message, allow retry.

---

## Phase 1 — Subtask G6 — Nav mega-menu and sitemap

**Files:** `templates/base.html`, `templates/sitemap.xml`
**Depends on:** nothing
**Scope:** surface Globesweeper in navigation and search indexing
**Phase 1 restriction:** Add `/globesweeper` to the nav and one sitemap entry only.
The intermediate/expert/custom/leaderboard URLs are added in Phase 2 once those
routes are driven by the T-selector.

### base.html

Locate the Variants group in the mega-menu (look for Hexsweeper or
Cylinder for the insertion point). Add a Globesweeper card:

```html
<a class="mega-card" href="/globesweeper"
   {% if mode == 'beginner' or mode == 'intermediate' or mode == 'expert' or mode == 'custom' %}
   aria-current="page"{% endif %}>
  <span class="mega-icon">🌍</span>
  <span class="mega-title">Globesweeper</span>
  <span class="mega-desc">Minesweeper on a rotating 3D globe</span>
</a>
```

Active state: `mode` is set to `'beginner'`, `'intermediate'`, `'expert'`,
or `'custom'` by the routes in `main.py` — use those values for `aria-current`.

### sitemap.xml

Add the five Globesweeper URLs with weekly changefreq and priority 0.7:

```xml
<url><loc>https://minesweeper.org/globesweeper</loc>
     <changefreq>weekly</changefreq><priority>0.7</priority></url>
<url><loc>https://minesweeper.org/globesweeper/intermediate</loc>
     <changefreq>weekly</changefreq><priority>0.6</priority></url>
<url><loc>https://minesweeper.org/globesweeper/expert</loc>
     <changefreq>weekly</changefreq><priority>0.6</priority></url>
<url><loc>https://minesweeper.org/globesweeper/custom</loc>
     <changefreq>weekly</changefreq><priority>0.5</priority></url>
<url><loc>https://minesweeper.org/globesweeper/leaderboard</loc>
     <changefreq>daily</changefreq><priority>0.5</priority></url>
```

---

---

## Phase 2 — General Goldberg Polyhedra (multiple board sizes + Earth skin)

**Goal:** Extend the Phase 1 game to support selectable GP(a,b) board sizes,
all three subdivision classes, and the Earth visual theme.

**Prerequisites:** Phase 1 shipped and concept approved.

---

## Phase 2 — Extension G1 — goldberg.js: Generalise to all subdivision classes

**File:** `static/js/goldberg.js` (extend existing file)
**Depends on:** Phase 1 G1a/G1b/G1c

Extend `subdivide(a, b)` to handle:

- **Class I (`b = 0`):** straightforward frequency subdivision of each triangle
  into `a²` sub-triangles along a regular grid.
- **Class III (general `a ≠ b`, `b ≠ 0`):** skewed Goldberg-Coxeter lattice;
  most complex — implement after Class I is verified.

The barycentric interpolation loop from Phase 1 already handles all classes
in principle; the difference is how the lattice points `(i, j)` are enumerated
for each `(a, b)`. Verify Class III with GP(2,1) → T=7, F=72.

### Extended acceptance criteria
- `goldberg(1, 0)` → F=12, all pentagons, each with 5 neighbours (Class I)
- `goldberg(2, 0)` → F=42 (Class I)
- `goldberg(5, 0)` → F=252 (Class I — largest supported board)
- `goldberg(2, 1)` → F=72 (Class III)
- All existing GP(1,1) tests continue to pass
- `npx jest` passes all cases in `src/__tests__/goldberg.test.js`

---

## Phase 2 — Extension G2 — T-selector UI + dynamic board sizes

**Files:** `static/js/globesweeper.js`, `templates/globesweeper.html`
**Depends on:** Phase 2 G1

### T-selector in globesweeper.html

The custom board form already has a T-select dropdown (from the existing HTML
shell). Wire the predefined options to named modes:

| Mode | GP(a,b) | T | F | Suggested mines |
|---|---|---|---|---|
| Beginner | GP(1,1) | 3 | 32 | 5 |
| Intermediate | GP(2,0) | 4 | 42 | 10 |
| Expert | GP(5,0) | 25 | 252 | 50 |
| Custom | user-entered a,b | — | — | user-entered |

### globesweeper.js changes

Replace the hardcoded `goldberg(1,1)` call with:
```js
const { faces, adj, T, F, pentagons } = goldberg(a, b)
```
where `a` and `b` are read from the T-selector or URL parameters (matching the
existing `data-a` and `data-b` attributes on the template).

Tear down and rebuild the Three.js scene on board change (dispose all geometries
and materials to avoid GPU memory leaks).

### Earth skin (deferred from Phase 1 G2)

Once Phase 1 is reviewed and the concept is approved, implement the Earth skin
additions documented in Phase 1 G2:
- Milky Way `scene.background` texture
- Inner `SphereGeometry` at radius 0.97 with equirectangular Earth texture
- `visible = false` on reveal instead of recolor
- `data-glob-skin` switching

---

## Phase 2 — Extension G4 — Earth skin CSS + texture assets

**Files:** `static/css/style.css`, `static/img/earth.jpg`, `static/img/milkyway.jpg`
**Depends on:** Phase 2 G2 (Earth skin)

Source texture assets (see Visual themes section for specs and licensing notes).
Add the `[data-glob-skin="earth"]` CSS block documented in Phase 1 G4.

---

## Phase 2 — Extension G6 — Full nav and sitemap

**Files:** `templates/base.html`, `templates/sitemap.xml`
**Depends on:** Phase 2 G2 (dynamic board sizes)

Add the remaining sitemap URLs once the routes are live:
```xml
<url><loc>https://minesweeper.org/globesweeper/intermediate</loc>
     <changefreq>weekly</changefreq><priority>0.6</priority></url>
<url><loc>https://minesweeper.org/globesweeper/expert</loc>
     <changefreq>weekly</changefreq><priority>0.6</priority></url>
<url><loc>https://minesweeper.org/globesweeper/custom</loc>
     <changefreq>weekly</changefreq><priority>0.5</priority></url>
<url><loc>https://minesweeper.org/globesweeper/leaderboard</loc>
     <changefreq>daily</changefreq><priority>0.5</priority></url>
```

---

## Recommended implementation order

### Phase 1

```
G4  Classic CSS variables     ← independent; do first or in parallel
G1a goldberg.js — icosahedron + Class II subdivision (GP(1,1) only)
G1b goldberg.js — dual polyhedron + adjacency
G1c goldberg.js — export, cache, GP(1,1) test
G2  globesweeper.js — Three.js scene, Classic skin, hardcoded goldberg(1,1)
G3  globesweeper.js — game logic
G5  score submission form
G6  nav (one entry) + one sitemap URL
```

→ **Review Phase 1. If concept is approved, proceed to Phase 2.**

### Phase 2

```
[asset]  Source earth.jpg + milkyway.jpg → static/img/
G1 ext  goldberg.js — Class I (b=0) + Class III (general); expand tests
G2 ext  T-selector UI; dynamic goldberg(a,b); Earth skin
G4 ext  Earth skin CSS + data-glob-skin block
G6 ext  Remaining sitemap URLs + leaderboard modes
```

G4 (Classic) and Phase 1 G6 are always independent and can be parallelised
with G1a/G1b/G1c. G1a → G1b → G1c must be sequential.

---

## Commit convention

Use `F55` prefix on all commits:

```
// Phase 1
F55 G1a Add goldberg.js — icosahedron base and Class II subdivision
F55 G1b Add goldberg.js — dual polyhedron construction and adjacency
F55 G1c Add goldberg.js — GP(1,1) canonical indexing, export, cache, and tests
F55 G2 Add globesweeper.js — Three.js scene and rendering, Classic skin, GP(1,1)
F55 G3 Add globesweeper.js — game logic (state, mines, flood-fill, hash)
F55 G4 Add --glob-* CSS variables, Classic theme
F55 G5 Wire score submission form in globesweeper.html
F55 G6 Add Globesweeper to nav mega-menu and sitemap

// Phase 2
F55 G1 Extend goldberg.js — Class I and Class III subdivision, full test suite
F55 G2 Add T-selector and dynamic board sizes to globesweeper.js
F55 G2 Add Earth skin — textured sphere, starfield background, face-hide on reveal
F55 G4 Add Earth skin CSS variables and data-glob-skin block
F55 G6 Add remaining Globesweeper sitemap URLs
F55 Add earth.jpg and milkyway.jpg texture assets
```

---

## Open questions / risks

| Item | Phase | Note |
|---|---|---|
| Class III (a≠b, b≠0) subdivision | 2 | Deferred from Phase 1; validate with GP(2,1) → T=7 first |
| OrbitControls bundling | 1 | three.min.js r165 has no OrbitControls; use manual quaternion drag |
| Mobile touch performance | 1 | 32 faces is fine; 252 (Phase 2 expert) may need BufferGeometry merge |
| Score submission auth | 1 | Guests use `display_name`; logged-in users use session email — match cylinder/toroid pattern |
| No-guess mode | both | Explicitly deferred; do not implement in this feature |
| Earth texture UV alignment | 2 | SphereGeometry UV is automatic; verify poles visually, adjust offset if needed |
| Texture asset licensing | 2 | NASA Blue Marble + ESA Milky Way are public domain — confirm before committing |
| Earth skin raycasting on hidden face | 2 | `visible = false` makes raycaster skip the mesh; detect clicks via board state + pointer position instead |
