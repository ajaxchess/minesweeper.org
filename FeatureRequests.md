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
| `static/js/goldberg.js` | ✗ Not started |
| `static/js/globesweeper.js` | ✗ Not started |
| CSS `--glob-*` skin variables | ✗ Not started |
| Score submission form (post-win) | ✗ Not started |
| Globesweeper in nav mega-menu (`base.html`) | ✗ Not started |
| Sitemap entries | ✗ Not started |

---

## Subtask G1 — goldberg.js: Goldberg polyhedron geometry generator

**File:** `static/js/goldberg.js`
**Depends on:** nothing
**Exported API:** `goldberg(a, b)` → `{ faces, adj, T, F, pentagons }`

### What to implement

**Icosahedron base**
Define the 12 vertices of a unit icosahedron using the golden-ratio formula
and the 20 triangular faces as index triples.

**Step 1 — Subdivide each icosahedron triangle**
For each of the 20 triangular faces with vertices `[P0, P1, P2]`, place
subdivision vertices using the Goldberg-Coxeter `(a, b)` lattice. The
subdivision pattern differs by class:
- Class I (`b = 0`): simple grid subdivision, `T = a²`
- Class II (`a = b`): rotated grid, `T = 3a²`
- Class III (general): skewed grid, `T = a² + ab + b²`

For each sub-triangle, compute barycentric coordinates and interpolate between
`P0`, `P1`, `P2`. Project each resulting vertex onto the unit sphere (normalise).

**Step 2 — Merge duplicate vertices**
Shared icosahedron edges produce duplicate vertices. Merge any two vertices
within `ε = 1e-9` of each other. Build a canonical vertex list and re-map
face indices.

**Step 3 — Build the dual (= Goldberg polyhedron)**
For each unique vertex `V` of the geodesic sphere:
  1. Collect the fan of triangular faces that contain `V`.
  2. Sort fan faces in angular order around `V` (use cross-product winding).
  3. The centroid of each fan triangle (projected to unit sphere) becomes a
     Goldberg face vertex.
  4. Valence 5 vertices become pentagons; valence 6 → hexagons.

Each Goldberg face = ordered array of unit-sphere `{x, y, z}` vertices
plus a centroid.

**Step 4 — Compute adjacency**
Two Goldberg faces are neighbours iff their vertex lists share exactly 2
consecutive vertices (modulo cyclic order). Build `adj[i]` = array of
neighbour indices.

**Step 5 — Canonical face indexing**
Sort all `F` face centroids lexicographically by `(x, y, z)` rounded to
6 decimal places. Assign 0-based indices in that order. This ensures a
deterministic, seed-independent canonical ordering for `boardToHash`.

**Step 6 — Export**
```js
export function goldberg(a, b) {
    // returns { faces, adj, T, F, pentagons }
    // faces[i]   = { verts: [{x,y,z}], centroid: {x,y,z}, isPentagon: bool }
    // adj[i]     = number[]  (neighbour indices)
    // T          = a*a + a*b + b*b
    // F          = 10*T + 2
    // pentagons  = Set<number>  (the 12 pentagon face indices)
}
```

**Cache:** wrap the result in a module-level `Map` keyed on `"${a},${b}"` so
repeated calls (reset game) don't recompute.

### Acceptance criteria
- `goldberg(1, 0)` → F=12, all pentagons, every face has 5 neighbours
- `goldberg(1, 1)` → F=32, 12 pentagons + 20 hexagons
- `goldberg(2, 1)` → F=72
- `goldberg(5, 0)` → F=252
- Each face in `adj` is bidirectionally consistent
- Canonical indices are stable across two calls with the same `(a, b)`

### Testing
Write `src/__tests__/goldberg.test.js` covering the four cases above.
Run with `npx jest` (or however the project runs tests).

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
G1 goldberg.js          ← foundation; test in isolation first
G2 scene & rendering    ← can stub game logic to verify mesh looks right
G3 game logic           ← complete the JS; full playable game
G4 CSS variables        ← can be done anytime, needed before G2 ships
G5 score submission     ← add after G3; needs game to be complete
G6 nav + sitemap        ← final step before launch
```

G4 and G6 are independent of the JS work and can be parallelised with G1/G2/G3.

---

## Commit convention

Use `F55` prefix on all commits:

```
F55 G1 Add goldberg.js — Goldberg polyhedron geometry generator
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
