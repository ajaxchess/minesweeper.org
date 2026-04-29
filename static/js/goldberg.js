/**
 * goldberg.js — Goldberg polyhedron geometry for Worldsweeper
 *
 * Build status:
 *   G1a-alpha  Class I (b=0)  → dodecahedron GP(1,0), F=12   ✓
 *   G1a-beta   Class II (a=b) → soccer ball  GP(1,1), F=32   pending
 *   G1a-gamma  Class III      → general GP(a,b)               deferred Phase 2
 */

// ---------------------------------------------------------------------------
// Icosahedron base geometry (shared by all subdivision classes)
// ---------------------------------------------------------------------------

const PHI = (1 + Math.sqrt(5)) / 2;   // golden ratio ≈ 1.618

// 12 vertices of a unit icosahedron.  Each row is [x, y, z] before normalisation.
const _RAW_VERTS = [
    [ 0,  1,  PHI], [ 0, -1,  PHI], [ 0,  1, -PHI], [ 0, -1, -PHI],
    [ 1,  PHI,  0], [-1,  PHI,  0], [ 1, -PHI,  0], [-1, -PHI,  0],
    [ PHI,  0,  1], [-PHI,  0,  1], [ PHI,  0, -1], [-PHI,  0, -1],
];

function _normalise(x, y, z) {
    const len = Math.sqrt(x * x + y * y + z * z);
    return { x: x / len, y: y / len, z: z / len };
}

// Icosahedron vertices projected onto the unit sphere.
const ICO_VERTS = _RAW_VERTS.map(([x, y, z]) => _normalise(x, y, z));

// 20 triangular faces as index triples (outward-consistent winding).
const ICO_TRIS = [
    [0,  1,  8], [0,  8,  4], [0,  4,  5], [0,  5,  9], [0,  9,  1],
    [1,  6,  8], [8,  6, 10], [8, 10,  4], [4, 10,  2], [4,  2,  5],
    [5,  2, 11], [5, 11,  9], [9, 11,  7], [9,  7,  1], [1,  7,  6],
    [3,  6,  7], [3,  7, 11], [3, 11,  2], [3,  2, 10], [3, 10,  6],
];

// ---------------------------------------------------------------------------
// Vertex deduplication helpers
// ---------------------------------------------------------------------------

function _vertKey(v) {
    return `${v.x.toFixed(9)},${v.y.toFixed(9)},${v.z.toFixed(9)}`;
}

/**
 * Given a flat array of {x,y,z} vertices (possibly with duplicates) and a
 * parallel array of index triples, return deduplicated {verts, tris}.
 */
function _merge(rawVerts, rawTris) {
    const keyToIdx = new Map();
    const verts = [];

    function canonical(v) {
        const k = _vertKey(v);
        if (!keyToIdx.has(k)) {
            keyToIdx.set(k, verts.length);
            verts.push(v);
        }
        return keyToIdx.get(k);
    }

    const tris = rawTris.map(([a, b, c]) => ({
        i0: canonical(rawVerts[a]),
        i1: canonical(rawVerts[b]),
        i2: canonical(rawVerts[c]),
    }));

    return { verts, tris };
}

// ---------------------------------------------------------------------------
// G1a-alpha — Class I subdivision  (b = 0,  T = a²)
// ---------------------------------------------------------------------------

/**
 * Subdivide a single icosahedron triangle [P0, P1, P2] into a² sub-triangles
 * using a uniform barycentric grid (Class I, b=0).
 *
 * Returns arrays of raw vertices and index triples local to this triangle.
 */
function _subdivideTriClassI(P0, P1, P2, a) {
    // Build an (a+1)×(a+1) grid of barycentric vertices where u+v+w = 1,
    // u = i/a,  v = j/a,  w = 1 - u - v,   0 ≤ j ≤ i ≤ a  is wrong —
    // we need the triangular grid: i ≥ 0, j ≥ 0, i+j ≤ a.
    const pts = [];
    const idx = [];   // idx[i][j] = index into pts

    for (let i = 0; i <= a; i++) {
        idx.push([]);
        for (let j = 0; j <= a - i; j++) {
            const u = i / a;
            const v = j / a;
            const w = 1 - u - v;
            const raw = {
                x: u * P0.x + v * P1.x + w * P2.x,
                y: u * P0.y + v * P1.y + w * P2.y,
                z: u * P0.z + v * P1.z + w * P2.z,
            };
            idx[i].push(pts.length);
            pts.push(_normalise(raw.x, raw.y, raw.z));
        }
    }

    const triIdxs = [];
    for (let i = 0; i < a; i++) {
        for (let j = 0; j < a - i; j++) {
            // Upward triangle
            triIdxs.push([idx[i][j], idx[i + 1][j], idx[i][j + 1]]);
            // Downward triangle (only when it fits)
            if (j + 1 <= a - i - 1) {
                triIdxs.push([idx[i + 1][j], idx[i + 1][j + 1], idx[i][j + 1]]);
            }
        }
    }

    return { pts, triIdxs };
}

// ---------------------------------------------------------------------------
// G1a-beta — General Goldberg-Coxeter subdivision  (Class II a=b, Class III a≠b)
// ---------------------------------------------------------------------------

/**
 * Subdivide a single icosahedron triangle [P0, P1, P2] into T = a²+ab+b²
 * sub-triangles using the Goldberg-Coxeter complex-plane lattice.
 *
 * Algorithm:
 *   1. Map the reference equilateral triangle to ℂ: P₀=0, P₁=1, P₂=e^{iπ/3}.
 *   2. Integer lattice points w(m,n) = m + n·e^{iπ/3}.
 *   3. Divide by the GP(a,b) divisor z = a + b·e^{iπ/3}  (|z|² = T).
 *   4. Keep only points p = w/z whose barycentric coords (α,β,γ) are all ≥ 0.
 *   5. Map (α,β,γ) back to 3-D and normalise to the unit sphere.
 *
 * Returns arrays of raw vertices and index triples local to this triangle.
 */
function _subdivideTriGC(P0, P1, P2, a, b) {
    const T = a * a + a * b + b * b;
    const SQRT3_2 = Math.sqrt(3) / 2;

    // Divisor z = a + b·e^{iπ/3} in complex components (zr, zi).
    // |z|² = (a + b/2)² + (b√3/2)² = a² + ab + b² = T  ✓
    const zr = a + b * 0.5;
    const zi = b * SQRT3_2;

    const N   = a + b;   // search bound: (m,n) each range 0 … N
    const EPS = 1e-9;

    const pts       = [];
    const vertIndex = new Map();   // "m,n" → index in pts

    function addVert(m, n) {
        const key = `${m},${n}`;
        if (vertIndex.has(key)) return vertIndex.get(key);

        // Complex lattice point w = m + n·e^{iπ/3}
        const wr = m + n * 0.5;
        const wi = n * SQRT3_2;

        // p = w / z  using conjugate division:  p = (w · z̄) / |z|²
        const pr = (wr * zr + wi * zi) / T;
        const pi = (wi * zr - wr * zi) / T;

        // Barycentric coords from the 2-D reference equilateral triangle
        // (P₀=0, P₁=1, P₂=(0.5, √3/2)):
        //   γ = 2·Im(p) / √3,   β = Re(p) − γ/2,   α = 1 − β − γ
        const gamma = 2 * pi / Math.sqrt(3);
        const beta  = pr - gamma * 0.5;
        const alpha = 1 - beta - gamma;

        // Reject lattice points that fall outside the triangle.
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

    // Emit upward and downward triangles for every cell in the (m,n) grid.
    // Cells that map outside the icosahedron face are silently skipped because
    // addVert returns -1 for out-of-triangle lattice points.
    const triIdxs = [];
    for (let m = 0; m <= N; m++) {
        for (let n = 0; n <= N - m; n++) {
            const v00 = addVert(m,     n);
            const v10 = addVert(m + 1, n);
            const v01 = addVert(m,     n + 1);
            const v11 = addVert(m + 1, n + 1);

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

/**
 * Apply _subdivideTriGC over all 20 icosahedron faces and merge duplicates.
 * Mirrors _subdivideClassI but uses the GC lattice for b > 0.
 */
function _subdivideClassGC(a, b) {
    const allPts  = [];
    const allTris = [];

    for (const [vi0, vi1, vi2] of ICO_TRIS) {
        const P0 = ICO_VERTS[vi0];
        const P1 = ICO_VERTS[vi1];
        const P2 = ICO_VERTS[vi2];

        const { pts, triIdxs } = _subdivideTriGC(P0, P1, P2, a, b);
        const offset = allPts.length;
        for (const p of pts)            allPts.push(p);
        for (const [ta, tb, tc] of triIdxs)
            allTris.push([offset + ta, offset + tb, offset + tc]);
    }

    return _merge(allPts, allTris);
}

// ---------------------------------------------------------------------------
// Public: subdivide(a, b) — entry point for G1b's buildDual
// ---------------------------------------------------------------------------

/**
 * Geodesic subdivision of the icosahedron.
 *
 *   Class I   (b=0):        subdivide(a, 0)   T = a²
 *   Class II  (a=b):        subdivide(n, n)   T = 3n²
 *   Class III (a≠b, b>0):   subdivide(a, b)   T = a²+ab+b²
 *
 * @param {number} a
 * @param {number} b
 * @returns {{ verts: {x,y,z}[], tris: {i0,i1,i2}[] }}
 */
function subdivide(a, b) {
    if (b === 0) return _subdivideClassI(a);   // Class I  — existing fast path
    return _subdivideClassGC(a, b);            // Class II (a=b) and Class III (a≠b, b>0)
}

function _subdivideClassI(a) {
    const allPts = [];
    const allTris = [];

    for (const [vi0, vi1, vi2] of ICO_TRIS) {
        const P0 = ICO_VERTS[vi0];
        const P1 = ICO_VERTS[vi1];
        const P2 = ICO_VERTS[vi2];

        const { pts, triIdxs } = _subdivideTriClassI(P0, P1, P2, a);
        const offset = allPts.length;
        for (const p of pts) allPts.push(p);
        for (const [ta, tb, tc] of triIdxs) {
            allTris.push([offset + ta, offset + tb, offset + tc]);
        }
    }

    return _merge(allPts, allTris);
}

// ---------------------------------------------------------------------------
// G1a-alpha — Dual polyhedron (Goldberg faces from geodesic vertices)
// ---------------------------------------------------------------------------

/**
 * Build the dual of the geodesic sphere — the Goldberg polyhedron.
 *
 * For each unique vertex V in the geodesic sphere:
 *   1. Collect all triangles containing V (the "fan").
 *   2. Sort fan triangles in cyclic angular order around V.
 *   3. Project each triangle's centroid to the unit sphere.
 *   4. Those ordered projected centroids = vertices of one Goldberg face.
 *
 * @param {{ verts: {x,y,z}[], tris: {i0,i1,i2}[] }} geo
 * @returns {{ faces: GoldbergFace[], adj: number[][] }}
 *
 * GoldbergFace = { verts: {x,y,z}[], centroid: {x,y,z}, isPentagon: boolean }
 */
function buildDual({ verts, tris }) {
    const F = verts.length;   // number of Goldberg faces = number of geodesic vertices

    // 1. For each geodesic vertex, collect its fan of triangles.
    const fans = Array.from({ length: F }, () => []);
    for (const tri of tris) {
        fans[tri.i0].push(tri);
        fans[tri.i1].push(tri);
        fans[tri.i2].push(tri);
    }

    // 2. Sort each fan in cyclic angular order around its centre vertex.
    function sortFan(vi, fan) {
        if (fan.length === 0) return fan;
        const V = verts[vi];

        // Build a local 2-D tangent frame at V.
        // Choose an arbitrary vector not parallel to V.
        const ref = { x: 1, y: 0, z: 0 };
        if (Math.abs(V.x) > 0.9) { ref.x = 0; ref.y = 1; }

        // tangentX = normalise(ref - (ref·V)V)
        const dot = ref.x * V.x + ref.y * V.y + ref.z * V.z;
        const tx = _normalise(ref.x - dot * V.x, ref.y - dot * V.y, ref.z - dot * V.z);
        // tangentY = V × tangentX
        const ty = {
            x: V.y * tx.z - V.z * tx.y,
            y: V.z * tx.x - V.x * tx.z,
            z: V.x * tx.y - V.y * tx.x,
        };

        function centroid(tri) {
            const v0 = verts[tri.i0], v1 = verts[tri.i1], v2 = verts[tri.i2];
            return {
                x: (v0.x + v1.x + v2.x) / 3,
                y: (v0.y + v1.y + v2.y) / 3,
                z: (v0.z + v1.z + v2.z) / 3,
            };
        }

        function angle(tri) {
            const c = centroid(tri);
            const dx = c.x - V.x, dy = c.y - V.y, dz = c.z - V.z;
            return Math.atan2(
                dx * ty.x + dy * ty.y + dz * ty.z,
                dx * tx.x + dy * tx.y + dz * tx.z,
            );
        }

        return [...fan].sort((a, b) => angle(a) - angle(b));
    }

    // 3. Build Goldberg faces.
    const faces = [];
    for (let vi = 0; vi < F; vi++) {
        const sorted = sortFan(vi, fans[vi]);
        const faceVerts = sorted.map(tri => {
            const v0 = verts[tri.i0], v1 = verts[tri.i1], v2 = verts[tri.i2];
            return _normalise(
                (v0.x + v1.x + v2.x) / 3,
                (v0.y + v1.y + v2.y) / 3,
                (v0.z + v1.z + v2.z) / 3,
            );
        });

        // Centroid of this Goldberg face.
        let cx = 0, cy = 0, cz = 0;
        for (const fv of faceVerts) { cx += fv.x; cy += fv.y; cz += fv.z; }
        const n = faceVerts.length;
        const centroid = _normalise(cx / n, cy / n, cz / n);

        // Ensure CCW winding when viewed from outside.
        // sortFan produces CW order for ~half the icosahedron vertices (those
        // whose tangent frame ty = V × tx ends up pointing "right" in screen
        // space rather than "up"), causing Three.js FrontSide to cull those
        // faces as back-facing — visible as rectangular holes at the poles.
        //
        // Use Newell's method (sum cross products of all edges from centroid)
        // instead of sampling just the first three vertices.  The 3-vertex
        // approach produces a near-zero cross product when those three vertices
        // happen to be nearly collinear (common in GP(5,0) hexagons), making
        // the inward/outward check numerically unreliable.
        if (faceVerts.length >= 3) {
            let nx = 0, ny = 0, nz = 0;
            for (let k = 0; k < faceVerts.length; k++) {
                const a = faceVerts[k];
                const b = faceVerts[(k + 1) % faceVerts.length];
                const ax = a.x - centroid.x, ay = a.y - centroid.y, az = a.z - centroid.z;
                const bx = b.x - centroid.x, by = b.y - centroid.y, bz = b.z - centroid.z;
                nx += ay * bz - az * by;
                ny += az * bx - ax * bz;
                nz += ax * by - ay * bx;
            }
            if (nx * centroid.x + ny * centroid.y + nz * centroid.z < 0) {
                faceVerts.reverse();
            }
        }

        faces.push({
            verts: faceVerts,
            centroid,
            isPentagon: faceVerts.length === 5,
        });
    }

    // 4. Compute adjacency via shared edges — O(F·degree) with an edge-key map.
    // Two Goldberg faces are neighbours iff they share exactly one edge (2 vertices).
    // The previous O(F²) set-intersection loop stalls for large polyhedra (e.g. F=752).
    const edgeToFaces = new Map();
    for (let fi = 0; fi < F; fi++) {
        const fv = faces[fi].verts;
        for (let k = 0; k < fv.length; k++) {
            const ka   = _vertKey(fv[k]);
            const kb   = _vertKey(fv[(k + 1) % fv.length]);
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

    return { faces, adj };
}

// ---------------------------------------------------------------------------
// Exported public API (G1c will add canonical indexing + caching)
// ---------------------------------------------------------------------------

/**
 * Return the Goldberg polyhedron GP(a, b).
 * Phase 1 only: b must be 0 (Class I) until G1a-beta is merged.
 *
 * @returns {{ faces, adj, T, F, pentagons }}
 */
function goldberg(a, b) {
    const geo = subdivide(a, b);
    const { faces, adj } = buildDual(geo);
    const T = a * a + a * b + b * b;
    const F = 10 * T + 2;
    const pentagons = new Set(
        faces.map((f, i) => (f.isPentagon ? i : -1)).filter(i => i >= 0)
    );
    return { faces, adj, T, F: faces.length, pentagons };
}
