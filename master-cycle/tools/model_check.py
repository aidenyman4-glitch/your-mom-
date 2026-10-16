"""Geometry checks for Minecraft block/item model JSON.

z-fighting happens when two faces that point the same way lie in the same
plane and overlap: the GPU can't decide which one is in front, so they flicker.
`zfight_pairs` finds every such pair (rotated elements included) by putting
each face in world space, grouping faces by plane, and intersecting the
overlapping quads in 2D.
"""

import math

import numpy as np

# Face corners per direction (same layout as Minecraft's FaceBakery).
_CORNERS = {
    "north": lambda f, t: [(t[0], t[1], f[2]), (f[0], t[1], f[2]), (f[0], f[1], f[2]), (t[0], f[1], f[2])],
    "south": lambda f, t: [(f[0], t[1], t[2]), (t[0], t[1], t[2]), (t[0], f[1], t[2]), (f[0], f[1], t[2])],
    "west": lambda f, t: [(f[0], t[1], f[2]), (f[0], t[1], t[2]), (f[0], f[1], t[2]), (f[0], f[1], f[2])],
    "east": lambda f, t: [(t[0], t[1], t[2]), (t[0], t[1], f[2]), (t[0], f[1], f[2]), (t[0], f[1], t[2])],
    "up": lambda f, t: [(f[0], t[1], f[2]), (t[0], t[1], f[2]), (t[0], t[1], t[2]), (f[0], t[1], t[2])],
    "down": lambda f, t: [(f[0], f[1], t[2]), (t[0], f[1], t[2]), (t[0], f[1], f[2]), (f[0], f[1], f[2])],
}
_NORMALS = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0),
            "east": (1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}


def _rot(axis, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def element_faces(el):
    """Yield (face_name, corners[4x3], unit_normal) in model space."""
    R, origin = np.eye(3), np.zeros(3)
    r = el.get("rotation")
    if r:
        origin = np.array(r["origin"], float)
        if "axis" in r:
            R = _rot(r["axis"], r["angle"])
        for ax in ("x", "y", "z"):
            if ax in r:
                R = R @ _rot(ax, r[ax])
    for face in el["faces"]:
        pts = np.array(_CORNERS[face](el["from"], el["to"]), float)
        pts = (pts - origin) @ R.T + origin
        yield face, pts, R @ np.array(_NORMALS[face], float)


def _clip(subject, clipper):
    """Sutherland-Hodgman: intersection of two convex CCW polygons (2D)."""
    out = subject
    for i in range(len(clipper)):
        a, b = clipper[i], clipper[(i + 1) % len(clipper)]
        inp, out = out, []
        if not inp:
            break

        def inside(p):
            return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= -1e-9

        def cross_pt(p, q):
            x1, y1, x2, y2 = a[0], a[1], b[0], b[1]
            x3, y3, x4, y4 = p[0], p[1], q[0], q[1]
            den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
            t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
            return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

        for j in range(len(inp)):
            p, q = inp[j], inp[(j + 1) % len(inp)]
            if inside(q):
                if not inside(p):
                    out.append(cross_pt(p, q))
                out.append(q)
            elif inside(p):
                out.append(cross_pt(p, q))
    return out


def _area(poly):
    return 0.5 * abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                         for i in range(len(poly))))


def _ccw(poly):
    s = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
            for i in range(len(poly)))
    return poly if s > 0 else poly[::-1]


def zfight_pairs(model, plane_eps=1e-3, min_area=1e-3):
    """Return [(name_a, face_a, name_b, face_b, overlap_area)] for every pair of
    same-facing coplanar faces that overlap."""
    faces = []
    for idx, el in enumerate(model.get("elements", [])):
        name = el.get("name", f"#{idx}")
        for face, pts, n in element_faces(el):
            faces.append((name, face, pts, n, float(n @ pts[0])))
    hits = []
    for i in range(len(faces)):
        na, fa, pa, nrm_a, da = faces[i]
        for j in range(i + 1, len(faces)):
            nb, fb, pb, nrm_b, db = faces[j]
            if nrm_a @ nrm_b < 0.9999 or abs(da - db) > plane_eps:
                continue
            # project both quads onto the shared plane
            u = pa[1] - pa[0]
            u /= np.linalg.norm(u)
            v = np.cross(nrm_a, u)
            A = _ccw([(float(p @ u), float(p @ v)) for p in pa])
            B = _ccw([(float(p @ u), float(p @ v)) for p in pb])
            inter = _clip(A, B)
            if len(inter) >= 3:
                area = _area(inter)
                if area > min_area:
                    hits.append((na, fa, nb, fb, area))
    return hits
