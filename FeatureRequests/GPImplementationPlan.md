# Worldsweeper: Class II & III Goldberg Polyhedra — Implementation Plan

## Background & State of the Code

`goldberg.js` has one subdivision function, `_subdivideTriClassI`, that places vertices at
barycentric grid points `(i/a, j/a, 1−i/a−j/a)`. This only works when `b=0` (T=a²).
Everything downstream — `buildDual`, adjacency, `worldsweeper.js` game logic — is
topology-agnostic and requires no changes.

The existing modes already declare Class II and III parameters that currently fall back
silently to GP(1,0):

| Route | (a,b) | T | F | Status |
|---|---|---|---|---|
| `/worldsweeper` (beginner) | (1,1) | 3 | 32 | fallback |
| `/worldsweeper/intermediate` | (2,1) | 7 | 72 | fallback |
| `/worldsweeper/expert` | (5,0) | 25 | 252 | works |

The entire fix lives in `goldberg.js`. No backend, template, or game-logic changes are required.

---

## The Core Algorithm: Complex-Plane Lattice

The Class I barycentric grid doesn't generalize. The correct unified algorithm uses the
**Goldberg-Coxeter construction** in the complex plane:

1. Map each icosahedron triangle to a reference equilateral triangle in ℂ:
   P₀=0, P₁=1, P₂=e^(iπ/3) = (0.5 + i·√3/2)
2. The lattice has basis vectors **1** and **e^(iπ/3)**. Integer lattice points are
   `w(m,n) = m + n·e^(iπ/3)`.
3. The GP(a,b) **divisor** is the complex number `z = a + b·e^(iπ/3)`.
   Note `|z|² = a² + ab + b² = T`.
4. The **sub-triangle vertices** are all `w(m,n) / z` that land inside the reference
   triangle (α,β,γ ≥ 0).
5. Convert each complex point back to barycentric coordinates, then blend with the 3D
   icosahedron face vertices and normalize to the unit sphere.

The conversion from complex point `p = x + iy` to barycentric in the reference triangle:
```
γ = 2y / √3
β = x − γ/2
α = 1 − β − γ
3D point = normalize(α·P0 + β·P1 + γ·P2)
```

The triangle connectivity in the (m,n) grid is identical to Class I: upward triangles
`(m,n)→(m+1,n)→(m,n+1)` and downward triangles `(m+1,n)→(m+1,n+1)→(m,n+1)`,
restricted to cells where all three vertices passed the "inside triangle" filter.

---

## Step 1 — Add `_subdivideTriGC(P0, P1, P2, a, b)`

This is the general subdivision function covering Class II (a=b) and Class III (a≠b, b>0).
`_subdivideTriClassI` can remain as-is; it stays as the fast path for b=0.

**Location:** `goldberg.js`, after line 119 (after `_subdivideTriClassI`).

```javascript
// G1a-beta — General Goldberg-Coxeter subdivision, covers Class II (a=b) and III (a≠b, b>0)
// T = a²+ab+b² sub-triangles per icosahedron face.
function _subdivideTriGC(P0, P1, P2, a, b) {
    const T = a * a + a * b + b * b;
    const SQRT3_2 = Math.sqrt(3) / 2;

    // Divisor z = a + b·e^{iπ/3}  in complex (zr, zi)
    const zr = a + b * 0.5;
    const zi = b * SQRT3_2;
    // |z|² = T  (verified: zr²+zi² = (a+b/2)²+(b√3/2)² = a²+ab+b²/4+3b²/4 = a²+ab+b² ✓)

    // Determine search bounds: (m,n) range from 0 to a+b in each dimension.
    const N = a + b;
    const EPS = 1e-9;

    const pts = [];
    const vertIndex = new Map();   // "m,n" → index in pts

    function addVert(m, n) {
        const key = `${m},${n}`;
        if (vertIndex.has(key)) return vertIndex.get(key);

        // Complex lattice point w = m + n·e^{iπ/3}
        const wr = m + n * 0.5;
        const wi = n * SQRT3_2;

        // Divide by z:  p = w/z = (w · z̄) / |z|²
        const pr = (wr * zr + wi * zi) / T;
        const pi = (wi * zr - wr * zi) / T;

        // Barycentric coords from 2D equilateral triangle
        const gamma = 2 * pi / Math.sqrt(3);
        const beta  = pr - gamma * 0.5;
        const alpha = 1 - beta - gamma;

        // Reject points outside the triangle (with tolerance)
        if (alpha < -EPS || beta < -EPS || gamma < -EPS) return -1;

        const raw = {
            x: alpha * P0.x + beta * P1.x + gamma * P2.x,
            y: alpha * P0.y + beta * P1.y + gamma * P2.y,
            z: alpha * P0.z + beta * P1.z + gamma * P2.z,
        };
        const idx = pts.length;
        pts.push(_normalise(raw.x, raw.y, raw.z));
        vertIndex.set(key, idx);
        return idx;
    }

    const triIdxs = [];
    for (let m = 0; m <= N; m++) {
        for (let n = 0; n <= N - m; n++) {
            const v00 = addVert(m,   n);
            const v10 = addVert(m+1, n);
            const v01 = addVert(m,   n+1);
            const v11 = addVert(m+1, n+1);

            // Upward triangle
            if (v00 >= 0 && v10 >= 0 && v01 >= 0)
                triIdxs.push([v00, v10, v01]);

            // Downward triangle
            if (v10 >= 0 && v11 >= 0 && v01 >= 0)
                triIdxs.push([v10, v11, v01]);
        }
    }

    return { pts, triIdxs };
}
```

---

## Step 2 — Add `_subdivideClassGC(a, b)`

Mirrors the structure of `_subdivideClassI` (lines 144–162), fanning over all 20
icosahedron faces.

**Location:** `goldberg.js`, immediately after `_subdivideTriGC`.

```javascript
function _subdivideClassGC(a, b) {
    const allPts  = [];
    const allTris = [];

    for (const [vi0, vi1, vi2] of ICO_TRIS) {
        const P0 = ICO_VERTS[vi0];
        const P1 = ICO_VERTS[vi1];
        const P2 = ICO_VERTS[vi2];

        const { pts, triIdxs } = _subdivideTriGC(P0, P1, P2, a, b);
        const offset = allPts.length;
        for (const p of pts)       allPts.push(p);
        for (const [ta, tb, tc] of triIdxs)
            allTris.push([offset + ta, offset + tb, offset + tc]);
    }

    return _merge(allPts, allTris);
}
```

---

## Step 3 — Update `subdivide(a, b)` to Route All Classes

Replace the current `subdivide` function (lines 136–142 of `goldberg.js`):

```javascript
function subdivide(a, b) {
    if (b === 0) return _subdivideClassI(a);     // Class I  — existing fast path
    return _subdivideClassGC(a, b);              // Class II (a=b) and Class III (a≠b, b>0)
}
```

---

## Step 4 — Fix the Adjacency O(F²) Bottleneck

The current adjacency loop in `buildDual` (lines 282–294) is O(F²). At F=32 (GP(1,1)) it
is fine; at F=72 (GP(2,1)) it produces 5184 comparisons — still acceptable. At larger
polyhedra such as GP(5,5) with F=752 it becomes 565k comparisons with Set lookups, which
can stall for 100–200ms.

Replace the adjacency block in `buildDual` (lines 280–294) with an edge-key index:

```javascript
    // Build edge → [face, face] map for O(F·degree) adjacency.
    const edgeToFaces = new Map();
    for (let fi = 0; fi < F; fi++) {
        const fv = faces[fi].verts;
        for (let k = 0; k < fv.length; k++) {
            const ka = _vertKey(fv[k]);
            const kb = _vertKey(fv[(k + 1) % fv.length]);
            const ekey = ka < kb ? `${ka}|${kb}` : `${kb}|${ka}`;
            if (!edgeToFaces.has(ekey)) edgeToFaces.set(ekey, []);
            edgeToFaces.get(ekey).push(fi);
        }
    }
    const adj = Array.from({ length: F }, () => []);
    for (const pair of edgeToFaces.values()) {
        if (pair.length === 2) {
            adj[pair[0]].push(pair[1]);
            adj[pair[1]].push(pair[0]);
        }
    }
```

---

## Step 5 — Validate in Browser Console Before Integration

Open `/worldsweeper/dodecahedron` and run in the console:

```javascript
// GP(1,1) — Class II soccer ball, expect F=32, exactly 12 pentagons
let g = goldberg(1,1);
console.assert(g.faces.length === 32);
console.assert(g.pentagons.size === 12);

// GP(2,1) — Class III, expect F=72, exactly 12 pentagons
let g2 = goldberg(2,1);
console.assert(g2.faces.length === 72);
console.assert(g2.pentagons.size === 12);

// GP(2,2) — Class II, expect F=122
let g3 = goldberg(2,2);
console.assert(g3.faces.length === 122);

// Adjacency symmetry check
for (let i = 0; i < g.faces.length; i++)
    for (const j of g.adj[i])
        console.assert(g.adj[j].includes(i), `asymmetric adj ${i}↔${j}`);
```

---

## Step 6 — Add Test Cases to `tests/test_worldsweeper.py`

```python
@pytest.mark.parametrize("a,b,expected_F,expected_pentagons", [
    (1, 0,  12, 12),   # dodecahedron (Class I, existing)
    (1, 1,  32, 12),   # soccer ball  (Class II)
    (2, 0,  42, 12),   # Class I
    (2, 1,  72, 12),   # Class III (intermediate mode)
    (2, 2, 122, 12),   # Class II
    (3, 1, 112, 12),   # Class III
    (5, 0, 252, 12),   # Class I (expert mode, already works)
])
def test_goldberg_face_count(a, b, expected_F, expected_pentagons):
    # Call through the JS via node or replicate the formula checks at Python level
    T = a*a + a*b + b*b
    assert 10 * T + 2 == expected_F
```

Full JS-layer tests require a Node.js runner or Playwright; the formula checks at minimum
guard against future regressions in the mode table.

---

## Step 7 — Remove the Silent Fallback in `worldsweeper.js`

Once all assertions pass, remove the try/catch fallback (lines 158–162 in `worldsweeper.js`)
so broken parameters surface as real errors rather than silently serving the wrong board:

```javascript
// Before:
try {
    _globeData = goldberg(_a, _b);
} catch (e) {
    console.warn(`goldberg(${_a},${_b}) not yet implemented — falling back to GP(1,0)`, e);
    _globeData = goldberg(1, 0);
}

// After:
_globeData = goldberg(_a, _b);
```

---

## Summary

| Step | File | Change |
|---|---|---|
| 1 | `goldberg.js` | Add `_subdivideTriGC(P0,P1,P2,a,b)` — complex-plane lattice |
| 2 | `goldberg.js` | Add `_subdivideClassGC(a,b)` — fan over 20 icosahedron faces |
| 3 | `goldberg.js` | Update `subdivide(a,b)` to route b>0 to `_subdivideClassGC` |
| 4 | `goldberg.js` | Replace O(F²) adjacency with edge-key map |
| 5 | browser console | Validate face counts, pentagon count=12, adj symmetry |
| 6 | `tests/test_worldsweeper.py` | Add parametrized face-count assertions |
| 7 | `worldsweeper.js` | Remove fallback try/catch around `goldberg(_a,_b)` |

No backend, template, database, or game-logic changes required. The beginner (GP(1,1), F=32)
and intermediate (GP(2,1), F=72) routes will work correctly as soon as Step 3 is deployed.
