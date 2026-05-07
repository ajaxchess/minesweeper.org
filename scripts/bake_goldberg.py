"""
Generate static/js/goldberg_prebaked.js containing pre-computed Goldberg
polyhedron geometry.

Uses antiprism_python (pip install antiprism_python) for geodesic vertex
generation and scipy for convex-hull triangulation.

Run from the repo root:
    python scripts/bake_goldberg.py
"""

import json, math, os
import numpy as np
from scipy.spatial import ConvexHull
from anti_lib_progs.geodesic import make_grid, grid_to_points, get_icosahedron


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _norm(x, y, z):
    d = math.sqrt(x*x + y*y + z*z)
    return (x/d, y/d, z/d)


def _vert_key(v):
    return f"{v[0]:.9f},{v[1]:.9f},{v[2]:.9f}"


# ---------------------------------------------------------------------------
# Step 1 — geodesic sphere vertices via antiprism_python
# ---------------------------------------------------------------------------

def _build_geodesic_verts(a, b):
    """
    Generate unit-sphere vertices for the GP(a,b) geodesic sphere.

    Uses antiprism_python's make_grid / grid_to_points to place interior
    and edge vertices correctly for all three Goldberg-Coxeter classes, then
    projects onto the unit sphere and deduplicates.

    Returns a list of (x, y, z) tuples (unit sphere).
    """
    T = a * a + a * b + b * b

    verts_ico = []
    faces_ico = []
    get_icosahedron(verts_ico, faces_ico)

    grid = make_grid(T, a, b)

    # Start with the 12 icosahedron base vertices.
    raw_pts = []
    for v in verts_ico:
        raw_pts.append((v[0], v[1], v[2]))

    # Add interior / edge-owned grid points for each icosahedron face.
    for face in faces_ico:
        face_verts_3d = [verts_ico[face[i]] for i in range(3)]
        new_pts = grid_to_points(grid, T, False, face_verts_3d, face)
        for p in new_pts:
            n = p.unit()
            raw_pts.append((n[0], n[1], n[2]))

    # Project all points onto the unit sphere and deduplicate.
    key_to_idx = {}
    verts = []
    for p in raw_pts:
        v = _norm(p[0], p[1], p[2])
        k = _vert_key(v)
        if k not in key_to_idx:
            key_to_idx[k] = len(verts)
            verts.append(v)

    return verts


# ---------------------------------------------------------------------------
# Step 2 — triangulation via convex hull (scipy)
# ---------------------------------------------------------------------------

def _triangulate(verts):
    """
    Compute the triangulation of a convex point cloud on the unit sphere.

    scipy ConvexHull gives the Delaunay triangulation of the sphere surface.
    Returns a list of (i0, i1, i2) index triples with outward-facing normals.
    """
    pts = np.array(verts)
    hull = ConvexHull(pts)

    tris = []
    for simplex in hull.simplices:
        i0, i1, i2 = simplex
        # Ensure outward normal: centroid of face should point away from origin.
        cx = (pts[i0, 0] + pts[i1, 0] + pts[i2, 0]) / 3
        cy = (pts[i0, 1] + pts[i1, 1] + pts[i2, 1]) / 3
        cz = (pts[i0, 2] + pts[i1, 2] + pts[i2, 2]) / 3
        # Cross product (i1-i0) x (i2-i0)
        ax, ay, az = pts[i1, 0]-pts[i0, 0], pts[i1, 1]-pts[i0, 1], pts[i1, 2]-pts[i0, 2]
        bx, by, bz = pts[i2, 0]-pts[i0, 0], pts[i2, 1]-pts[i0, 1], pts[i2, 2]-pts[i0, 2]
        nx = ay*bz - az*by
        ny = az*bx - ax*bz
        nz = ax*by - ay*bx
        if nx*cx + ny*cy + nz*cz < 0:
            tris.append((i0, i2, i1))  # flip to outward
        else:
            tris.append((i0, i1, i2))

    return tris


# ---------------------------------------------------------------------------
# Step 3 — dual polyhedron (Goldberg faces) from geodesic triangulation
# ---------------------------------------------------------------------------

def _build_dual(verts, tris):
    """
    Build the dual of the geodesic sphere — the Goldberg polyhedron.

    For each geodesic vertex V:
      1. Collect all triangles containing V (the "fan").
      2. Sort fan triangles in cyclic angular order around V.
      3. Project each triangle's centroid to the unit sphere.
      4. Those ordered projected centroids = vertices of one Goldberg face.

    Returns (faces, adj):
      faces — list of { verts, centroid, isPentagon }
      adj   — list of lists of neighbour face indices
    """
    F = len(verts)
    fans = [[] for _ in range(F)]
    for tri in tris:
        fans[tri[0]].append(tri)
        fans[tri[1]].append(tri)
        fans[tri[2]].append(tri)

    def sort_fan(vi, fan):
        if not fan:
            return fan
        V = verts[vi]
        ref = [1.0, 0.0, 0.0]
        if abs(V[0]) > 0.9:
            ref = [0.0, 1.0, 0.0]
        dot = ref[0]*V[0] + ref[1]*V[1] + ref[2]*V[2]
        tx_raw = (ref[0]-dot*V[0], ref[1]-dot*V[1], ref[2]-dot*V[2])
        tx = _norm(*tx_raw)
        ty = (
            V[1]*tx[2] - V[2]*tx[1],
            V[2]*tx[0] - V[0]*tx[2],
            V[0]*tx[1] - V[1]*tx[0],
        )

        def centroid(tri):
            v0, v1, v2 = verts[tri[0]], verts[tri[1]], verts[tri[2]]
            return ((v0[0]+v1[0]+v2[0])/3, (v0[1]+v1[1]+v2[1])/3,
                    (v0[2]+v1[2]+v2[2])/3)

        def angle(tri):
            c = centroid(tri)
            dx, dy, dz = c[0]-V[0], c[1]-V[1], c[2]-V[2]
            return math.atan2(
                dx*ty[0]+dy*ty[1]+dz*ty[2],
                dx*tx[0]+dy*tx[1]+dz*tx[2],
            )

        return sorted(fan, key=angle)

    faces = []
    for vi in range(F):
        sorted_fan = sort_fan(vi, fans[vi])
        face_verts = []
        for tri in sorted_fan:
            v0, v1, v2 = verts[tri[0]], verts[tri[1]], verts[tri[2]]
            face_verts.append(_norm(
                (v0[0]+v1[0]+v2[0])/3,
                (v0[1]+v1[1]+v2[1])/3,
                (v0[2]+v1[2]+v2[2])/3,
            ))

        n = len(face_verts)
        cx = sum(v[0] for v in face_verts) / n
        cy = sum(v[1] for v in face_verts) / n
        cz = sum(v[2] for v in face_verts) / n
        centroid = _norm(cx, cy, cz)

        # Newell's method: ensure CCW winding when viewed from outside.
        if n >= 3:
            nx = ny = nz = 0.0
            for k in range(n):
                av = face_verts[k]
                bv = face_verts[(k+1) % n]
                ax, ay, az = av[0]-centroid[0], av[1]-centroid[1], av[2]-centroid[2]
                bx, by, bz = bv[0]-centroid[0], bv[1]-centroid[1], bv[2]-centroid[2]
                nx += ay*bz - az*by
                ny += az*bx - ax*bz
                nz += ax*by - ay*bx
            if nx*centroid[0] + ny*centroid[1] + nz*centroid[2] < 0:
                face_verts.reverse()

        faces.append({
            "verts":      [{"x": v[0], "y": v[1], "z": v[2]} for v in face_verts],
            "centroid":   {"x": centroid[0], "y": centroid[1], "z": centroid[2]},
            "isPentagon": n == 5,
        })

    # Edge-key adjacency — O(F · degree).
    edge_to_faces = {}
    for fi, face in enumerate(faces):
        fv = face["verts"]
        for k in range(len(fv)):
            ka = _vert_key((fv[k]["x"], fv[k]["y"], fv[k]["z"]))
            kb = _vert_key((fv[(k+1) % len(fv)]["x"],
                            fv[(k+1) % len(fv)]["y"],
                            fv[(k+1) % len(fv)]["z"]))
            ekey = (ka, kb) if ka < kb else (kb, ka)
            edge_to_faces.setdefault(ekey, []).append(fi)

    adj = [[] for _ in range(F)]
    for pair in edge_to_faces.values():
        if len(pair) == 2:
            adj[pair[0]].append(pair[1])
            adj[pair[1]].append(pair[0])

    return faces, adj


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def goldberg(a, b):
    """Return Goldberg polyhedron GP(a, b) geometry."""
    verts = _build_geodesic_verts(a, b)
    tris  = _triangulate(verts)
    faces, adj = _build_dual(verts, tris)
    T = a*a + a*b + b*b
    return {"faces": faces, "adj": adj, "T": T, "F": len(faces)}


def main():
    configs = [(1, 0), (1, 1), (2, 1), (5, 0)]
    prebaked = {}
    for a, b in configs:
        print(f"Baking GP({a},{b})…", end=" ", flush=True)
        data = goldberg(a, b)
        key = f"{a},{b}"
        prebaked[key] = data
        pentagons = sum(1 for f in data["faces"] if f["isPentagon"])
        print(f"F={data['F']}  pentagons={pentagons}")

    out_path = os.path.join(os.path.dirname(__file__), "..", "static", "js",
                            "goldberg_prebaked.js")
    out_path = os.path.normpath(out_path)

    js = "// Auto-generated by scripts/bake_goldberg.py — do not edit by hand.\n"
    js += "const GOLDBERG_PREBAKED = " + json.dumps(prebaked, separators=(",", ":")) + ";\n"

    with open(out_path, "w") as f:
        f.write(js)
    size_kb = os.path.getsize(out_path) / 1024
    print(f"Written {out_path}  ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
