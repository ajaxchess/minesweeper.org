# F55 Globesweeper — Implementation Plan

This document breaks F55 (Globesweeper) into discrete implementation subtasks.
The feature spec lives in Features.md under F55.

## Status of existing work

| Asset | Status |
|---|---|
| Routes in `main.py` | ✓ Done |
| `GlobesweeperScore` model in `database_template.py` | ✓ Done |
| `templates/globesweeper.html` | ✓ Done (HTML shell, data attrs, canvas, custom form) |
| `templates/globesweeper_leaderboard.html` | ✓ Done |
| `static/js/vendor/three.min.js` | ✓ Done |
| `static/js/goldberg.js` (G1a: icosahedron + subdivision) | ✗ Not started |
| `static/js/goldberg.js` (G1b: dual + adjacency) | ✗ Not started |
| `static/js/goldberg.js` (G1c: canonical index + export + tests) | ✗ Not started |
| `static/js/globesweeper.js` | ✗ Not started |
| CSS `--glob-*` skin variables | ✗ Not started |
| Score submission form (post-win) | ✗ Not started |
| Globesweeper in nav mega-menu (`base.html`) | ✗ Not started |
| Sitemap entries | ✗ Not started |

---

## Subtask G1a — goldberg.js: Icosahedron base + geodesic subdivision

**File:** `static/js/goldberg.js` (partial — scaffold + first two steps)
**Depends on:** nothing
**Output contract:** a module-level function `subdivide(a, b)` that returns
an array of triangular faces `{ v0, v1, v2 }` where each vertex is a
unit-sphere `{x, y, z}`. No exports yet — G1b consumes this internally.

### What to implement

**Icosahedron base**
Define the 12 vertices of a unit icosahedron using the golden-ratio formula
and the 20 triangular faces as index triples. (These are constants at the
top of the file.)

**Step 1 — Subdivide each icosahedron triangle**
For each of the 20 triangular faces with vertices `[P0, P1, P2]`, place
subdivision vertices using the Goldberg-Coxeter `(a, b)` lattice:
- Class I (`b = 0`): simple grid subdivision, `T = a²`
- Class II (`a = b`): rotated grid, `T = 3a²`
- Class III (general): skewed grid, `T = a² + ab + b²`

For each sub-triangle, compute barycentric coordinates `(u, v, w)` with
`u + v + w = 1` and interpolate: `P = u*P0 + v*P1 + w*P2`. Project each
resulting vertex onto the unit sphere (normalise to length 1).

**Step 2 — Merge duplicate vertices**
Shared icosahedron edges produce duplicate vertices. Merge any two vertices
within `ε = 1e-9` of each other using a string-keyed map
(`"${x.toFixed(9)},${y.toFixed(9)},${z.toFixed(9)}"` → canonical index).
Re-map each triangle's vertex indices to canonical indices.

Return value of `subdivide(a, b)`:
```js
{
    verts: [{x, y, z}, ...],   // unique unit-sphere vertices
    tris:  [{i0, i1, i2}, ...]  // triangles as index triples into verts
}
```

### Acceptance criteria
- `subdivide(1, 0)` → 12 verts, 20 tris (bare icosahedron, T=1)
- `subdivide(2, 0)` → T=4, so 20*4=80 tris, 42 verts
- `subdivide(1, 1)` → T=3, so 20*3=60 tris, 32 verts
- Every vertex has unit length (≤ 1e-9 error from 1.0)
- No duplicate vertices (all pairwise distances > 1e-9)

### Testing
No test file yet — acceptance criteria are verified manually in the browser
console (`subdivide(2,0).tris.length === 80`) before G1c writes the test file.

---

## Subtask G1b — goldberg.js: Dual polyhedron + adjacency

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

## Subtask G1c — goldberg.js: Canonical indexing, export, cache, tests

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

### Acceptance criteria
- `goldberg(1, 0)` → F=12, all pentagons, every face has 5 neighbours
- `goldberg(1, 1)` → F=32, 12 pentagons + 20 hexagons
- `goldberg(2, 1)` → F=72
- `goldberg(5, 0)` → F=252
- Each face in `adj` is bidirectionally consistent
- Canonical indices are stable: two calls with the same `(a, b)` return
  identical index assignments (test by calling twice and comparing)

### Testing
Write `src/__tests__/goldberg.test.js` covering all four board sizes above
plus the stability check. Run with `npx jest`.

---

## Subtask G2 — globesweeper.js Part 1: Three.js scene and rendering

**File:** `static/js/globesweeper.js`
**Depends on:** G1 (goldberg.js), Three.js vendor
**Scope:** scene setup, face meshes, rotation, raycasting, sprite overlays

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

### Globe mesh construction

For each Goldberg face `i`:
1. Project verts to unit sphere, scale to 0.98.
2. Fan-triangulate: `[centroid_at_0.98, verts[j], verts[j+1]]` for each edge.
3. Build `THREE.BufferGeometry` from the triangles.
4. Create `THREE.MeshLambertMaterial({ color: HIDDEN_COLOR, side: THREE.FrontSide })`.
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

Called whenever face state changes:
- Set `faceMeshes[idx].material.color` based on state.
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

## Subtask G3 — globesweeper.js Part 2: game logic

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

## Subtask G4 — CSS skin variables

**File:** `static/css/style.css`
**Depends on:** nothing
**Scope:** add `--glob-*` CSS variables to each skin block

### Default (dark skin) — add to `:root` or `.skin-dark`

```css
--glob-hidden:         #2a3a5c;
--glob-hidden-border:  #3a5278;
--glob-rev:            #111b2a;
--glob-mine:           #7a0000;
--glob-detonated:      #c00000;
```

### Each additional skin

Add a `--glob-*` override block inside each existing skin's CSS rule.
Match the visual language of that skin (light skin → lighter background,
etc.). At minimum ensure `--glob-hidden` and `--glob-rev` have sufficient
contrast for the number sprites.

---

## Subtask G5 — Score submission (post-win)

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

## Subtask G6 — Nav mega-menu and sitemap

**Files:** `templates/base.html`, `templates/sitemap.xml`
**Depends on:** nothing
**Scope:** surface Globesweeper in navigation and search indexing

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

## Recommended implementation order

```
G1a goldberg.js — icosahedron base + geodesic subdivision   ← start here
G1b goldberg.js — dual polyhedron + adjacency               ← same file, next step
G1c goldberg.js — canonical indexing + export + tests       ← completes the module
G2  scene & rendering    ← stub game logic to verify mesh looks right
G3  game logic           ← complete the JS; full playable game
G4  CSS variables        ← can be done anytime, needed before G2 ships
G5  score submission     ← add after G3; needs game to be complete
G6  nav + sitemap        ← final step before launch
```

G4 and G6 are independent of the JS work and can be parallelised with G1/G2/G3.
G1a → G1b → G1c must be sequential (each builds on the previous in the same file).

---

## Commit convention

Use `F55` prefix on all commits:

```
F55 G1a Add goldberg.js — icosahedron base and geodesic subdivision
F55 G1b Add goldberg.js — dual polyhedron construction and adjacency
F55 G1c Add goldberg.js — canonical indexing, export, cache, and tests
F55 G2 Add globesweeper.js — Three.js scene and rendering
F55 G3 Add globesweeper.js — game logic (state, mines, flood-fill, hash)
F55 G4 Add --glob-* CSS variables for all skins
F55 G5 Wire score submission form in globesweeper.html
F55 G6 Add Globesweeper to nav mega-menu and sitemap
```

---

## Open questions / risks

| Item | Note |
|---|---|
| Class III (a≠b, b≠0) subdivision | Most complex math — Class I and II should work first; validate with T=7 (GP(2,1)) |
| OrbitControls bundling | three.min.js r165 does not include OrbitControls; implement manual quaternion drag instead |
| Mobile touch performance | 252 meshes (expert) may be slow on low-end phones; defer BufferGeometry merge to future |
| Score submission auth | Guests submit with `display_name`; logged-in users use session email — match pattern in cylinder/toroid |
| No-guess mode | Explicitly deferred per spec; do not implement in this feature |
