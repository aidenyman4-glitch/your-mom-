"""The Sun Man rig, reconstructed after the project folder was lost.

Two survivors made this possible:

  * the SKELETON — all 29 bones with parents and pivots in v5's native pixels — was printed to
    the session transcript when the v5 geometry was first inspected, and is transcribed below.
  * the GEOMETRY — every bone's cubes — survives inside the installed resource pack, as the
    28 vanilla item models under `assets/sunman/models/item/part/`.

Those models store cubes in MODEL pixels with the bone pivot at (8,8,8) and were emitted at
16/12 px per block, so a model coordinate converts back to blocks as `(px - 8) * 0.75`.

Face colour is sampled straight from the surviving atlas through each face's UV rect, which is
more faithful than the material table that was lost with the generators.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "resourcepack" / "assets" / "sunman"
PARTS = PACK / "models" / "item" / "part"
ATLAS = PACK / "textures" / "entity" / "sun_man.png"

PX_PER_RU = 16.0 / 12.0
DISPLAY_SCALE = 12.0
MODEL_TO_RU = 1.0 / PX_PER_RU          # 0.75

# ---------------------------------------------------------------- skeleton
# (bone, parent, pivot in v5 pixels). 16 px = 1 block.
_SKELETON = [
    ("root", None, (0.0, 0.672, 0.0)),
    ("pelvis", "root", (0.0, 397.152, 0.0)),
    ("torso", "pelvis", (0.0, 484.512, 6.72)),
    ("upper_torso", "torso", (0.0, 706.272, 53.76)),
    ("neck", "upper_torso", (0.0, 874.272, 127.68)),
    ("head", "neck", (0.0, 1042.272, 188.16)),
    ("sun_rays", "head", (0.0, 1042.272, 188.16)),
    ("left_upper_arm", "upper_torso", (110.0, 679.392, 26.88)),
    ("left_forearm", "left_upper_arm", (116.72, 578.592, 28.224)),
    ("left_hand", "left_forearm", (119.408, 444.192, 28.896)),
    ("left_fingers", "left_hand", (119.408, 420.672, 30.24)),
    ("right_upper_arm", "upper_torso", (-110.0, 679.392, 26.88)),
    ("right_forearm", "right_upper_arm", (-116.72, 578.592, 28.224)),
    ("right_hand", "right_forearm", (-119.408, 444.192, 28.896)),
    ("right_fingers", "right_hand", (-119.408, 420.672, 30.24)),
    ("left_thigh", "pelvis", (22.848, 383.712, -3.36)),
    ("left_shin", "left_thigh", (34.944, 245.952, -4.032)),
    ("left_foot", "left_shin", (43.008, 24.192, -1.344)),
    ("right_thigh", "pelvis", (-22.848, 383.712, -3.36)),
    ("right_shin", "right_thigh", (-34.944, 245.952, -4.032)),
    ("right_foot", "right_shin", (-43.008, 24.192, -1.344)),
    ("left_lower_upper_arm", "torso", (105.0, 543.392, 52.88)),
    ("left_lower_forearm", "left_lower_upper_arm", (111.72, 442.592, 54.224)),
    ("left_lower_hand", "left_lower_forearm", (114.408, 308.192, 54.896)),
    ("left_lower_fingers", "left_lower_hand", (114.408, 284.672, 56.24)),
    ("right_lower_upper_arm", "torso", (-105.0, 543.392, 52.88)),
    ("right_lower_forearm", "right_lower_upper_arm", (-111.72, 442.592, 54.224)),
    ("right_lower_hand", "right_lower_forearm", (-114.408, 308.192, 54.896)),
    ("right_lower_fingers", "right_lower_hand", (-114.408, 284.672, 56.24)),
]

J = {name: (p[0] / 16.0, p[1] / 16.0, p[2] / 16.0) for name, _, p in _SKELETON}
PARENT = {name: parent for name, parent, _ in _SKELETON}
BONE_ORDER = [name for name, _, _ in _SKELETON]

# ---------------------------------------------------------------- maths

def quat_mul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return (w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2)


def quat_conj(q):
    return (q[0], -q[1], -q[2], -q[3])


def quat_norm(q):
    n = math.sqrt(sum(c * c for c in q))
    return tuple(c / n for c in q) if n > 1e-12 else (1.0, 0.0, 0.0, 0.0)


def quat_axis(axis, deg):
    l = math.sqrt(sum(c * c for c in axis)) or 1.0
    ax = [c / l for c in axis]
    h = math.radians(deg) / 2
    s = math.sin(h)
    return (math.cos(h), ax[0] * s, ax[1] * s, ax[2] * s)


def quat_euler(rx, ry, rz):
    return quat_mul(quat_axis((0, 0, 1), rz),
                    quat_mul(quat_axis((0, 1, 0), ry), quat_axis((1, 0, 0), rx)))


def quat_rotate(q, v):
    r = quat_mul(quat_mul(q, (0.0, v[0], v[1], v[2])), quat_conj(q))
    return (r[1], r[2], r[3])


# ---------------------------------------------------------------- geometry

def _atlas_colours():
    from PIL import Image
    im = Image.open(ATLAS).convert("RGBA")
    W, H = im.size
    px = im.load()

    def sample(uv):
        x0, y0, x1, y1 = [v / 16.0 for v in uv]
        x0, x1 = sorted((x0 * W, x1 * W))
        y0, y1 = sorted((y0 * H, y1 * H))
        xs = range(max(0, int(x0)), min(W, max(int(x0) + 1, int(x1))))
        ys = range(max(0, int(y0)), min(H, max(int(y0) + 1, int(y1))))
        tot = [0, 0, 0]
        n = 0
        for y in ys:
            for x in xs:
                r, g, b, a = px[x, y]
                if a < 8:
                    continue
                tot[0] += r; tot[1] += g; tot[2] += b
                n += 1
        if not n:
            return None            # fully transparent: the face-art cutout
        return tuple(c // n for c in tot)
    return sample


def _load_geometry():
    sample = _atlas_colours()
    geo = {}
    for f in sorted(PARTS.glob("*.json")):
        model = json.loads(f.read_text())
        cubes = []
        for el in model.get("elements", []):
            frm = [(c - 8.0) * MODEL_TO_RU for c in el["from"]]
            to = [(c - 8.0) * MODEL_TO_RU for c in el["to"]]
            size = [to[i] - frm[i] for i in range(3)]
            faces = {}
            face_art = False
            for d, face in (el.get("faces") or {}).items():
                uv = face.get("uv", [0, 0, 16, 16])
                # The starburst sprite maps the whole (256,256)-(512,512) atlas quadrant. It is
                # a transparent cutout, so averaging its pixels returns a flat near-white and
                # the face paints as a blank square — it has to be drawn as the real art.
                if [round(v, 2) for v in uv] == [8.0, 8.0, 16.0, 16.0]:
                    face_art = True
                    faces[d] = None
                else:
                    faces[d] = sample(uv)
            cube = {"from": frm, "size": size, "faces": faces,
                    "emit": el.get("light_emission", 0)}
            if face_art:
                cube["face_art"] = True
            rot = el.get("rotation")
            if rot:
                cube["rotation"] = {
                    "origin": [(c - 8.0) * MODEL_TO_RU for c in rot.get("origin", [8, 8, 8])],
                    "x": rot.get("x", 0.0), "y": rot.get("y", 0.0), "z": rot.get("z", 0.0)}
            cubes.append(cube)
        if cubes:
            geo[f.stem] = cubes
    return geo


GEOMETRY = _load_geometry()


def _zero():
    return {b: (0.0, 0.0, 0.0) for b in BONE_ORDER}


# ---------------------------------------------------------------- forward kinematics

def solve(pose):
    """World (position, quaternion) per bone. `pose[bone]` is a rotation triple, or a
    {"rotation", "position"} dict as `keyframes.Clip.sample` returns (position in blocks,
    in the parent's frame — a Blockbench position keyframe)."""
    out = {}
    for bone in BONE_ORDER:
        parent = PARENT.get(bone)
        entry = pose.get(bone)
        if isinstance(entry, dict):
            rot = entry.get("rotation", (0.0, 0.0, 0.0))
            move = entry.get("position", (0.0, 0.0, 0.0))
        else:
            rot = entry or (0.0, 0.0, 0.0)
            move = (0.0, 0.0, 0.0)
        q = quat_euler(*rot)
        if parent is None or parent not in out:
            out[bone] = (tuple(J[bone][i] + move[i] for i in range(3)), quat_norm(q))
            continue
        ppos, pq = out[parent]
        off = tuple(J[bone][i] - J[parent][i] + move[i] for i in range(3))
        out[bone] = (tuple(ppos[i] + quat_rotate(pq, off)[i] for i in range(3)),
                     quat_norm(quat_mul(pq, q)))
    return out


# ---------------------------------------------------------------- matrices
# Bone SCALE keys need more than a quaternion: three.js (and so Blockbench and GeckoLib)
# scales a bone in its own frame and every child inherits it. `solve_m` carries a full 3x3
# matrix per bone for that; `solve` keeps returning rotations for the callers that only aim.

def mat_from_quat(q):
    w, x, y, z = q
    return ((1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)),
            (2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)),
            (2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)))


def mat_mul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def mat_vec(m, v):
    return tuple(m[i][0] * v[0] + m[i][1] * v[1] + m[i][2] * v[2] for i in range(3))


def mat_scale(m, s):
    return tuple(tuple(m[i][j] * s[j] for j in range(3)) for i in range(3))


def channels(entry):
    """(rotation, position, scale) from a pose entry: a rotation triple or a channel dict."""
    if isinstance(entry, dict):
        return (entry.get("rotation", (0.0, 0.0, 0.0)), entry.get("position", (0.0, 0.0, 0.0)),
                entry.get("scale", (1.0, 1.0, 1.0)))
    return (entry or (0.0, 0.0, 0.0)), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)


def fk_matrices(order, parent_of, joints, pose, rest=None):
    """World (position, 3x3 matrix) per bone: rest + keyed rotation, position and scale."""
    out = {}
    for bone in order:
        rot, move, scl = channels(pose.get(bone))
        r0 = (rest or {}).get(bone, (0.0, 0.0, 0.0))
        local = mat_scale(mat_from_quat(quat_norm(quat_euler(r0[0] + rot[0], r0[1] + rot[1],
                                                              r0[2] + rot[2]))), scl)
        parent = parent_of.get(bone)
        if parent is None or parent not in out:
            out[bone] = (tuple(joints[bone][i] + move[i] for i in range(3)), local)
            continue
        ppos, pm = out[parent]
        off = tuple(joints[bone][i] - joints[parent][i] + move[i] for i in range(3))
        out[bone] = (tuple(ppos[i] + mat_vec(pm, off)[i] for i in range(3)), mat_mul(pm, local))
    return out


def solve_m(pose):
    return fk_matrices(BONE_ORDER, PARENT, J, pose)


def cube_corners(cube):
    fx, fy, fz = cube["from"]
    w, h, d = cube["size"]
    pts = [(fx + dx, fy + dy, fz + dz)
           for dx in (0, w) for dy in (0, h) for dz in (0, d)]
    rot = cube.get("rotation")
    if rot:
        o = rot["origin"]
        rq = quat_euler(rot["x"], rot["y"], rot["z"])
        pts = [tuple(o[i] + quat_rotate(rq, (p[0] - o[0], p[1] - o[1], p[2] - o[2]))[i]
                     for i in range(3)) for p in pts]
    return pts


def extents(pose):
    sol = solve_m(pose)
    lo, hi = 1e9, -1e9
    for bone, cubes in GEOMETRY.items():
        pos, m = sol[bone]
        for c in cubes:
            for p in cube_corners(c):
                y = pos[1] + mat_vec(m, p)[1]
                lo, hi = min(lo, y), max(hi, y)
    return lo, hi


def solve_grounded(pose):
    dy = -extents(pose)[0]
    return {b: ((p[0], p[1] + dy, p[2]), q) for b, (p, q) in solve(pose).items()}


def solve_grounded_m(pose):
    dy = -extents(pose)[0]
    return {b: ((p[0], p[1] + dy, p[2]), m) for b, (p, m) in solve_m(pose).items()}


def model_height(pose=None):
    lo, hi = extents(pose if pose is not None else _zero())
    return hi - lo


if __name__ == "__main__":
    print("bones   ", len(BONE_ORDER))
    print("geometry", len(GEOMETRY), "bones carry",
          sum(len(c) for c in GEOMETRY.values()), "cubes")
    print("height  ", round(model_height(), 2), "blocks")
    missing = [b for b in BONE_ORDER if b not in GEOMETRY and b != "root"]
    print("no cubes", missing)


# ---------------------------------------------------------------- compatibility
# The recovered generators (tiers.py, export_*.py) import these spellings. The euler order
# is identical to quat_euler above — Z * (Y * X) — so this is an alias, not a conversion.
quat_from_euler_xyz = quat_euler


def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
