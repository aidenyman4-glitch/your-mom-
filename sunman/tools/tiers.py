"""Tier 1 and Tier 2 creatures, rebuilt as Blockbench mod-style models.

LOCUST — "It doesn't see you... but it knows you're there."
    2.7 blocks. A puppet: a small pale mask of a face in a mass of long black hair, on a neck far
    too long, over a body that is all ribs; pale jointed limbs bound at every joint with black
    string, needles for fingers, and legs that taper to points instead of feet.

DARK WALKER — "It does not hurry, because it does not need to."
    7.3 blocks. A wide flat brim over a low crown, a small narrow head pushed forward on a long
    neck, two lit eyes in the shadow of the brim, a stooped torso with the shoulders wider than
    the hips, six jointed arms in three tiers that fan out and hang to the knee, each ending in
    four long two-knuckled fingers, and legs that are more than half of it.

Both are authored on a true pixel grid — 16 px to the block, 1 texel per pixel, every cube a
whole number of pixels — the way a mob is built in Blockbench for a mod. Geometry is written
in absolute rest-space pixels (easy to read against the references) and converted to the
bone-relative blocks the rest of the toolchain uses.

THE RIG. A bone is an entity in the datapack, so the counts stay at the handoff's budget —
Locust 11, Dark Walker 21 — but the joints moved to where an animator needs them. The old
rigs split each limb at the wrist and the ankle, which left every arm and leg one rigid stick
from the shoulder or hip: no knees, no elbows, nothing a walk cycle can bend. Now each limb
breaks at the ELBOW and the KNEE, and the hand and foot ride on the lower segment.

REST POSE. The limbs are built hanging straight down (so a bone's local axes run along it)
and posed by the bones' rest rotations: the arms fan out and bend at the elbow, the knees
soften, the neck pushes the head forward. That is a Blockbench group rotation, it is a bone
`rotation` in Bedrock geometry, and keyframes ADD to it — Euler angles summed, as Blockbench
and GeckoLib both do — so `solve` here does the same.

Axes match the Sun Man rig: +X = the creature's LEFT, +Y = up, +Z = FORWARD.
"""
from rig import (fk_matrices, mat_vec, quat_from_euler_xyz, quat_mul,  # noqa: E402
                 quat_norm, quat_rotate, vsub)

PX = 1.0 / 16.0                 # one Blockbench pixel at true scale, in blocks


# ---------------------------------------------------------------- authoring helpers

def C(frm, size, mat, paint=None, rot=None, origin=None, emit=0):
    """A cube in absolute rest-space pixels."""
    c = {"from": tuple(float(v) for v in frm), "size": tuple(float(v) for v in size),
         "mat": mat}
    if paint:
        c["paint"] = paint
    if rot and any(rot):
        c["rot"] = tuple(float(v) for v in rot)
        c["origin"] = tuple(float(v) for v in origin)
    if emit:
        c["emit"] = emit
    return c


def _euler_q(x, y, z):
    return quat_from_euler_xyz(x, y, z)


def finger(base, fan, curl, segs, mat, tip_mat, width=1.0, depth=1.0, splay=0.0):
    """A jointed finger hanging from `base` (absolute px).

    Each segment is its own cube rotated about its own knuckle, so a finger can bow without a
    bone per knuckle — the knuckles are free, the bones are not. `fan` spreads it sideways
    (Z), `curl` bends it forward (X, negative = toward +Z) and grows by `curl` again at every
    knuckle, `splay` tips it forward/back before the fan.
    """
    out = []
    o = tuple(base)
    acc = 0.0
    for i, length in enumerate(segs):
        acc += curl if i else curl * 0.5
        rx, rz = splay + acc, fan
        frm = (o[0] - width / 2, o[1] - length, o[2] - depth / 2)
        out.append(C(frm, (width, length, depth), tip_mat if i == len(segs) - 1 else mat,
                     paint="claw" if i == len(segs) - 1 else "bone",
                     rot=(rx, 0.0, rz), origin=o))
        d = quat_rotate(_euler_q(rx, 0.0, rz), (0.0, -length, 0.0))
        o = (o[0] + d[0], o[1] + d[1], o[2] + d[2])
    return out


def mirror_cube(c):
    """The same cube on the other side of the creature (x -> -x)."""
    m = dict(c)
    fx, fy, fz = c["from"]
    w, h, d = c["size"]
    m["from"] = (-(fx + w), fy, fz)
    if "rot" in c:
        rx, ry, rz = c["rot"]
        m["rot"] = (rx, -ry, -rz)
        ox, oy, oz = c["origin"]
        m["origin"] = (-ox, oy, oz)
    return m


# ---------------------------------------------------------------- the creature

class Creature:
    """A small authored rig exposing the interface the exporters and renderers use."""

    def __init__(self, name, pivots_px, parents, cubes_px, rest=None, height_hint=0.0,
                 display_scale=1.0, bb_px_per_block=16.0):
        self.name = name
        self.parents = dict(parents)
        self.REST = {b: tuple(r) for b, r in (rest or {}).items()}
        self.height_hint = height_hint
        # Blockbench is authored at true scale; the per-bone ITEM models are written at
        # 16/display_scale px per block and the item_display scale undoes it, which keeps
        # every element inside the [-16, 32] box Blockbench will open in Java format.
        self.BB_PX_PER_BLOCK = bb_px_per_block
        self.DISPLAY_SCALE = display_scale
        self.PX_PER_RU = 16.0 / display_scale

        self.J = {b: tuple(v * PX for v in p) for b, p in pivots_px.items()}
        self.J_PX = {b: tuple(p) for b, p in pivots_px.items()}

        order, seen = [], set()

        def visit(n):
            if n in seen:
                return
            p = self.parents.get(n)
            if p:
                visit(p)
            seen.add(n)
            order.append(n)

        for n in pivots_px:
            visit(n)
        self.BONE_ORDER = order
        self.BONES = {n: (self.parents.get(n), n, None, (0.0, -1.0, 0.0)) for n in order}

        # bone-relative cubes, in blocks (what the exporters and the renderer consume)
        self.CUBES_PX = cubes_px
        self.GEOMETRY = {}
        for bone, cubes in cubes_px.items():
            pv = pivots_px[bone]
            out = []
            for c in cubes:
                r = {"from": [(c["from"][i] - pv[i]) * PX for i in range(3)],
                     "size": [c["size"][i] * PX for i in range(3)],
                     "mat": c["mat"], "paint": c.get("paint"), "emit": c.get("emit", 0)}
                if "rot" in c:
                    r["rotation"] = {"origin": [(c["origin"][i] - pv[i]) * PX for i in range(3)],
                                     "x": c["rot"][0], "y": c["rot"][1], "z": c["rot"][2]}
                out.append(r)
            self.GEOMETRY[bone] = out
        self.LIGHT_EMISSION = {b: 15 for b, cs in cubes_px.items() if any(c.get("emit") for c in cs)}

    # ------------------------------------------------------------- kinematics
    def _zero(self):
        return {b: (0.0, 0.0, 0.0) for b in self.BONE_ORDER}

    def rest_rotation(self, bone):
        return quat_norm(_euler_q(*self.REST.get(bone, (0.0, 0.0, 0.0))))

    def solve(self, pose):
        """World (position, quaternion) per bone. `pose[bone]` is a rotation triple or a
        {"rotation", "position"} dict as `keyframes.Clip.sample` returns; position in blocks,
        in the parent's frame, like a Blockbench position keyframe."""
        out = {}
        for bone in self.BONE_ORDER:
            entry = pose.get(bone)
            if isinstance(entry, dict):
                rot = entry.get("rotation", (0.0, 0.0, 0.0))
                off = entry.get("position", (0.0, 0.0, 0.0))
            else:
                rot = entry or (0.0, 0.0, 0.0)
                off = (0.0, 0.0, 0.0)
            rest = self.REST.get(bone, (0.0, 0.0, 0.0))
            q = _euler_q(rest[0] + rot[0], rest[1] + rot[1], rest[2] + rot[2])
            parent = self.parents.get(bone)
            if parent is None or parent not in out:
                out[bone] = (tuple(self.J[bone][i] + off[i] for i in range(3)), quat_norm(q))
                continue
            p_pos, p_q = out[parent]
            rel = vsub(self.J[bone], self.J[parent])
            rel = (rel[0] + off[0], rel[1] + off[1], rel[2] + off[2])
            out[bone] = (tuple(a + b for a, b in zip(p_pos, quat_rotate(p_q, rel))),
                         quat_norm(quat_mul(p_q, q)))
        return out

    def _cube_corners(self, cube):
        fx, fy, fz = cube["from"]
        w, h, d = cube["size"]
        pts = [(fx + dx, fy + dy, fz + dz)
               for dx in (0, w) for dy in (0, h) for dz in (0, d)]
        rot = cube.get("rotation")
        if rot:
            o = rot["origin"]
            rq = _euler_q(rot.get("x", 0.0), rot.get("y", 0.0), rot.get("z", 0.0))
            pts = [tuple(a + b for a, b in
                         zip(o, quat_rotate(rq, (p[0] - o[0], p[1] - o[1], p[2] - o[2]))))
                   for p in pts]
        return pts

    def solve_m(self, pose):
        """World (position, 3x3 matrix) per bone — rest, rotation, position AND scale keys."""
        return fk_matrices(self.BONE_ORDER, self.parents, self.J, pose, self.REST)

    def extents(self, pose, axis=1):
        sol = self.solve_m(pose)
        lo, hi = 1e9, -1e9
        for bone, cubes in self.GEOMETRY.items():
            pos, m = sol[bone]
            for c in cubes:
                for p in self._cube_corners(c):
                    v = pos[axis] + mat_vec(m, p)[axis]
                    lo, hi = min(lo, v), max(hi, v)
        return lo, hi

    def solve_grounded(self, pose):
        dy = -self.extents(pose)[0]
        return {b: ((p[0], p[1] + dy, p[2]), q)
                for b, (p, q) in self.solve(pose).items()}

    def solve_grounded_m(self, pose):
        dy = -self.extents(pose)[0]
        return {b: ((p[0], p[1] + dy, p[2]), m)
                for b, (p, m) in self.solve_m(pose).items()}

    def model_height(self, pose=None):
        lo, hi = self.extents(pose if pose is not None else {})
        return hi - lo

    def cube_count(self):
        return sum(len(v) for v in self.GEOMETRY.values())


# ====================================================================== LOCUST
# Built to Aiden's references (sunman/docs/references/locust/): an ink sheet and a photo of a
# puppet — pale jointed limbs bound at every joint with black string, a pale chest over a
# black ribbed waist, black ragged hips like torn shorts, legs that taper to stakes instead of
# feet, and arms that do not end in hands at all but run on into long black blades that reach
# the floor — and two frames of it in the corner of a papered room: a pale long-nosed MASK of
# a face in a mass of curling black hair, on a black neck far too long.
#
# The proportions are the sheet's: legs over half its height, the torso the shortest part,
# shoulders three quarters of the way up, and the blades splayed so arms and legs make one
# tall narrow tent. It keeps the budget of 11 bones: the neck rides the HEAD bone, pivoting
# at its base on the shoulders, so the whole stalk cranes, droops and snaps round as one.

def hang(base, length, rot, mat="lc_hair", paint="strand", width=0.5, depth=0.5):
    """A strand hanging from `base`, swung about its root by `rot` (degrees)."""
    return C((base[0] - width / 2, base[1] - length, base[2] - depth / 2), (width, length, depth),
             mat, paint, rot=rot, origin=base)


def chain(base, segs, start, step, mat, paint, tip_paint=None):
    """Segments hanging end to end from `base`, each rotated about its own root.

    `segs` is (length, width) per segment; `start` is the first segment's (x, z) swing and
    `step` is added again at every joint, so a chain can bow into a blade or wind into a
    curl without a bone per joint."""
    out, o = [], tuple(base)
    rx, rz = start
    for i, (length, width) in enumerate(segs):
        if i:
            rx, rz = rx + step[0], rz + step[1]
        last = i == len(segs) - 1
        out.append(C((o[0] - width / 2, o[1] - length, o[2] - width / 2), (width, length, width),
                     mat, tip_paint if (last and tip_paint) else paint, rot=(rx, 0.0, rz), origin=o))
        d = quat_rotate(_euler_q(rx, 0.0, rz), (0.0, -length, 0.0))
        o = (o[0] + d[0], o[1] + d[1], o[2] + d[2])
    return out


def _locust():
    P, G = {}, {}
    par = {"torso": "pelvis", "head": "torso",
           "arm_l": "torso", "fore_l": "arm_l", "arm_r": "torso", "fore_r": "arm_r",
           "leg_l": "pelvis", "shin_l": "leg_l", "leg_r": "pelvis", "shin_r": "leg_r"}
    HIP, KNEE, SHOULDER = 27.0, 14.0, 39.0

    P["pelvis"] = (0, HIP + 0.5, 0)
    G["pelvis"] = [C((-2.5, HIP - 1.5, -1.6), (5, 3.5, 3.2), "lc_rag", "rag")]   # torn black shorts
    for x, z, h in ((-0.5, 1.6, 2.5), (1.25, 1.6, 1.5), (-1.0, -2.1, 2.0), (2.5, -0.5, 1.75)):
        G["pelvis"].append(C((x, HIP - 1.5 - h, z), (1, h, 0.5) if abs(z) > 1 else (0.5, h, 1),
                             "lc_rag", "rag"))                                 # the hem hangs in rags

    T = HIP + 1.5
    P["torso"] = (0, T, 0)
    G["torso"] = [
        C((-1.0, T, -0.9), (2, 4.5, 1.8), "lc_skin", "waist"),            # black, ribbed, snappable
        C((-2.1, T + 4.5, -1.4), (4.2, 1.5, 2.8), "lc_wrap", "wrap"),     # bound under the chest
        C((-2.25, T + 5.0, -1.25), (4.5, 4.5, 2.5), "lc_flesh", "ribcage"),
        C((-1.9, T + 5.75, 1.25), (1.5, 1.75, 0.5), "lc_flesh", "chest"),  # the sagging pale chest
        C((0.4, T + 5.75, 1.25), (1.5, 1.75, 0.5), "lc_flesh", "chest"),
        C((-3.0, T + 9.5, -1.0), (6, 1, 2), "lc_flesh", "yoke"),
        C((-0.6, T + 10.5, -0.6), (1.2, 0.75, 1.2), "lc_skin", "neck"),
    ]
    for y, z in ((T + 0.5, -1.4), (T + 2.0, -1.4), (T + 3.5, -1.4), (T + 6.0, -1.75), (T + 7.5, -1.75)):
        G["torso"].append(C((-0.5, y, z), (1, 1, 0.5), "lc_bone", "knob"))   # the knuckled spine

    # head: the neck, the skull, the mask, the nose and the hair, all on one bone at the neck's base
    NB = T + 11.0
    P["head"] = (0, NB, 0)
    H = NB + 5.5                                                           # the top of the neck
    G["head"] = [
        C((-0.5, NB - 0.5, -0.5), (1, 6, 1), "lc_skin", "neck"),           # black and far too long
        C((-1.75, H, -1.75), (3.5, 5, 3.5), "lc_skin", "skull"),
        C((-1.5, H - 0.5, 1.75), (3, 5.5, 0.5), "lc_mask", "mask"),        # the face is a mask
        C((-0.5, H + 1.5, 2.25), (1, 2, 0.75), "lc_mask", "nose"),         # with a long nose
        C((-3.0, H + 4.5, -2.6), (6, 2.25, 5.1), "lc_hair", "hair"),        # crown, over the brow
        C((-2.25, H + 6.75, -2.0), (4.5, 1, 4), "lc_hair", "hair"),
        C((1.75, H - 1.0, -2.25), (1.5, 5.75, 4), "lc_hair", "hair"),      # both sides of the face
        C((-3.25, H - 1.0, -2.25), (1.5, 5.75, 4), "lc_hair", "hair"),
        C((3.25, H + 1.0, -1.75), (1, 4.25, 3), "lc_hair", "hair"),        # and wider again
        C((-4.25, H + 0.5, -2.0), (1, 4.5, 3.25), "lc_hair", "hair"),
        C((-2.5, H - 2.0, -2.75), (5, 7.5, 1), "lc_hair", "hair"),         # down the back
    ]
    # curls: wire-stiff loops standing off the mass, the way the sheet's hair coils
    seg = [(1.5, 0.5)] * 5
    for base, start, step in (
            ((1.5, H + 6.5, 0.5), (0, 150), (0, 60)), ((-1.0, H + 7.0, -0.5), (10, -160), (0, -55)),
            ((2.75, H + 4.5, 1.0), (-20, 120), (0, 65)), ((-2.75, H + 5.0, 0.5), (-10, -125), (0, -60)),
            ((3.5, H + 2.5, -0.5), (0, 100), (25, 55)), ((-3.75, H + 2.0, -1.0), (0, -95), (-20, -60)),
            ((0.5, H + 6.0, -2.25), (-150, 20), (-50, 0))):
        G["head"] += chain(base, seg, start, step, "lc_hair", "strand")
    # long strands falling over the shoulders and down the chest, uneven on purpose
    for base, length, rot in (
            ((2.6, H + 1.0, 1.0), 9.0, (6, 0, 9)), ((2.4, H + 2.5, -1.2), 12.0, (-5, 0, 5)),
            ((1.2, H - 0.5, -2.6), 10.0, (-10, 0, 2)), ((3.2, H + 1.5, 0.0), 7.0, (2, 0, 16)),
            ((-2.6, H + 0.5, 1.1), 11.0, (5, 0, -6)), ((-2.5, H + 2.0, -1.3), 8.5, (-7, 0, -4)),
            ((-1.0, H - 1.0, -2.7), 12.5, (-12, 0, -3)), ((-3.6, H + 1.0, 0.2), 6.0, (0, 0, -18))):
        G["head"].append(hang(base, length, rot))

    for side, sg in (("l", 1), ("r", -1)):
        sx, lx = 4.0, 1.6
        E = SHOULDER - 9
        P[f"arm_{side}"] = (sg * sx, SHOULDER, 0)
        P[f"fore_{side}"] = (sg * sx, E, 0)
        P[f"leg_{side}"] = (sg * lx, HIP, 0)
        P[f"shin_{side}"] = (sg * lx, KNEE, 0)
        arm = [
            C((-1, SHOULDER - 1, -1), (2, 2, 2), "lc_bone", "ball"),           # a doll's ball joint
            C((-0.9, SHOULDER - 2, -0.9), (1.8, 1, 1.8), "lc_wrap", "wrap"),
            C((-0.75, E + 1.75, -0.75), (1.5, SHOULDER - 2 - E - 1.75, 1.5), "lc_bone", "bone"),
            C((-0.9, E + 1.0, -0.9), (1.8, 0.75, 1.8), "lc_wrap", "wrap"),
        ]
        fore = [
            C((-1, E - 1, -1), (2, 1.5, 2), "lc_wrap", "wrap"),                 # bound elbow
            C((-0.75, E - 6, -0.75), (1.5, 5, 1.5), "lc_bone", "bone"),
            C((-0.85, E - 5.25, -0.85), (1.7, 2.0, 1.7), "lc_wrap", "wrap"),    # wound tight
            C((-0.9, E - 7.5, -0.9), (1.8, 1.5, 1.8), "lc_wrap", "wrap"),       # bound wrist
        ]
        # no hand: the arm runs on into a black blade that bows outward and reaches the floor
        fore += chain((0.0, E - 7.5, 0.0), [(4.5, 1.0), (5.0, 0.75), (5.5, 0.5), (5.0, 0.5)],
                      (0.0, 2.0), (0.0, 2.5), "lc_needle", "blade", tip_paint="point")
        fore.append(hang((0.6, E - 7.0, 0.4), 6.5, (4, 0, -6), "lc_wrap", "strand"))  # loose string
        leg = [
            C((-1.4, HIP - 4.5, -1.4), (2.8, 4, 2.8), "lc_rag", "rag"),         # the torn hem
            C((-1, KNEE + 1, -1), (2, HIP - 4.5 - KNEE - 1, 2), "lc_bone", "bone"),
        ]
        shin = [
            C((-1.25, KNEE - 1, -1.25), (2.5, 2, 2.5), "lc_wrap", "wrap"),       # bound knee
            C((-1, 8.5, -1), (2, KNEE - 1 - 8.5, 2), "lc_bone", "bone"),
            C((-0.75, 5, -0.75), (1.5, 3.5, 1.5), "lc_bone", "bone"),           # tapering to a stake
            C((-0.85, 4, -0.85), (1.7, 1.25, 1.7), "lc_wrap", "wrap"),
            C((-0.5, 1.5, -0.5), (1, 2.5, 1), "lc_bone", "bone"),
            C((-0.25, 0.0, -0.25), (0.5, 1.5, 0.5), "lc_bone", "point"),        # no foot: a point
        ]
        for key, cubes, ox in ((f"arm_{side}", arm, sx), (f"fore_{side}", fore, sx),
                               (f"leg_{side}", leg, lx), (f"shin_{side}", shin, lx)):
            moved = []
            for c in cubes:                                         # authored about x = 0
                m = dict(c)
                m["from"] = (c["from"][0] + ox, c["from"][1], c["from"][2])
                if "rot" in c:
                    m["origin"] = (c["origin"][0] + ox, c["origin"][1], c["origin"][2])
                moved.append(m if sg > 0 else mirror_cube(m))
            G[key] = moved

    rest = {
        "torso": (3.0, 0.0, 0.0),                       # held up stiff, barely stooped
        "head": (-2.0, 4.0, 8.0),                       # the mask tips over on its stalk
        "arm_l": (0.0, 0.0, 8.0), "arm_r": (0.0, 0.0, -8.0),    # splayed: the blades make a tent
        "fore_l": (-3.0, 0.0, 2.0), "fore_r": (-3.0, 0.0, -2.0),
        "leg_l": (-2.0, 0.0, 1.5), "leg_r": (-2.0, 0.0, -1.5),
        "shin_l": (3.0, 0.0, -1.0), "shin_r": (3.0, 0.0, 1.0),
    }
    # display_scale 1.5: the blades put the forearm's tip 28 px from the elbow, past what one
    # item model can hold at true scale
    return Creature("locust", P, par, G, rest=rest, height_hint=3.3,
                    display_scale=1.5, bb_px_per_block=16.0)


# ================================================================= DARK WALKER
# Built from Aiden's five references: a hilltop silhouette, an ink drawing on pink paper, two
# frames of something standing in a road at night with lit eyes, and one of it reaching over a
# fence at a house. All five agree on the proportion — legs more than half of it, the body the
# smallest part — and on a wide flat brim, a small head, lit eyes, and arms that hang to the
# knee. The ink drawing and the hilltop both show SIX arms, fanned, with long fingers; the road
# frames show the knees bending as it steps.

def _dark_walker():
    P, G = {}, {}
    par = {"torso": "pelvis", "neck": "torso", "head": "neck", "hat": "head"}

    HIP, KNEE = 68.0, 35.0
    P["pelvis"] = (0, HIP, 0)
    G["pelvis"] = [
        C((-4.5, HIP - 4, -2.5), (9, 6, 5), "dw_dark", "pelvis"),
        C((-5, HIP + 1, -2), (10, 1, 4), "dw_pale", "ridge"),       # the crest of the hip bones
    ]

    # A torso you could close a hand around: a pinched waist, a stooped chest, and shoulders
    # wider than the hips — the ink drawing's long coat-hanger silhouette.
    P["torso"] = (0, HIP + 1, 0)
    T = HIP + 1
    G["torso"] = [
        C((-3, T, -2), (6, 9, 4), "dw_skin", "waist"),
        C((-4, T + 9, -2), (8, 8, 5), "dw_skin", "ribs"),
        C((-5, T + 17, -1.5), (10, 7, 5), "dw_skin", "chest"),
        C((-8.5, T + 23, -1.5), (17, 3, 5), "dw_dark", "yoke"),     # the shoulder yoke
        C((-2, T + 26, 0), (4, 2, 3), "dw_dark", "collar"),
    ]
    for i, y in enumerate((T + 2, T + 6, T + 11, T + 15, T + 20)):  # spine knuckles
        z = -3.0 if i < 2 else -3.0 + 0.5 * (i - 1)
        G["torso"].append(C((-1, y, z), (2, 1.5, 1), "dw_pale", "knob"))

    NECK = T + 27
    P["neck"] = (0, NECK, 1.5)
    G["neck"] = [C((-1, NECK - 1, 0.5), (2, 9, 2), "dw_skin", "neck")]

    HEAD = NECK + 7
    P["head"] = (0, HEAD, 1.5)
    G["head"] = [
        C((-2.5, HEAD, -1), (5, 7, 5), "dw_skin", "face"),
        C((-2, HEAD - 2, 0), (4, 2, 3.5), "dw_skin", "jaw"),
        C((-3, HEAD + 4, 3.5), (6, 1, 1), "dw_dark", "brow"),       # the brow that shades them
        # The eyes. Proud of the face and lit, because in three of the five references the
        # eyes are the only thing in the frame that is not a silhouette.
        C((-2, HEAD + 3.0, 4), (1, 0.5, 0.5), "dw_eye", "eye", emit=15),   # narrow, lit slits
        C((1, HEAD + 3.0, 4), (1, 0.5, 0.5), "dw_eye", "eye", emit=15),
    ]

    # The hat. Wide and flat — the brim is twice the shoulder width and the first thing you
    # identify at any distance — over a LOW crown that steps in to a blunt point, the way the
    # hilltop silhouette reads.
    HAT = HEAD + 6
    P["hat"] = (0, HAT, 1.5)
    # the brim is round, the mod way: a stepped disc of plates that never overlap, so
    # nothing is coplanar and nothing z-fights. A single square plate read as a
    # mortarboard the moment the head tipped.
    hz = 1.5
    brim = [((-10, 10), (-10, 10)),
            ((-7, 7), (10, 15)), ((-7, 7), (-15, -10)),
            ((10, 15), (-7, 7)), ((-15, -10), (-7, 7))]
    for sx in (1, -1):
        for sz in (1, -1):
            for (a, b), (c, d) in (((7, 10), (10, 13)), ((10, 13), (7, 10)), ((10, 12), (10, 12))):
                x0, x1 = sorted((sx * a, sx * b))
                z0, z1 = sorted((sz * c, sz * d))
                brim.append(((x0, x1), (z0, z1)))
    G["hat"] = [C((x0, HAT, hz + z0), (x1 - x0, 1, z1 - z0), "dw_hat", "brim")
                for (x0, x1), (z0, z1) in brim]
    G["hat"] += [
        C((-5.5, HAT + 1, -4), (11, 3, 11), "dw_hat", "crown"),
        C((-6, HAT + 1, -4.5), (12, 1.5, 12), "dw_band", "band"),
        C((-4.5, HAT + 4, -3), (9, 2, 9), "dw_hat", "crown"),
        C((-3.5, HAT + 6, -2), (7, 1, 7), "dw_hat", "crown"),
        C((-2, HAT + 7, -0.5), (4, 1, 4), "dw_hat", "crown"),
    ]

    # Six arms in three tiers. Each tier sits a little lower, a little further back and a
    # little narrower than the one above, and is a pixel shorter, so the six never read as
    # one part repeated.
    TIERS = ((1, 8.0, T + 25.0, 1.0, 26.0, 24.0),
             (2, 7.0, T + 22.5, 0.0, 25.0, 24.0),
             (3, 6.0, T + 20.0, -1.0, 24.0, 23.0))
    for n, sx, sy, sz, upper, lower in TIERS:
        for side, sg in (("l", 1), ("r", -1)):
            P[f"arm_{side}{n}"] = (sg * sx, sy, sz)
            P[f"fore_{side}{n}"] = (sg * sx, sy - upper, sz)
            par[f"arm_{side}{n}"] = "torso"
            par[f"fore_{side}{n}"] = f"arm_{side}{n}"
            # authored for the LEFT side about the limb's own axis, then placed / mirrored
            arm = [
                C((-1.5, sy - 2.5, sz - 1.5), (3, 3, 3), "dw_pale", "joint"),        # shoulder
                C((-1, sy - upper + 1, sz - 1), (2, upper - 3, 2), "dw_skin", "limb"),
            ]
            ey = sy - upper
            fore = [
                C((-1.5, ey - 1.5, sz - 1.5), (3, 3, 3), "dw_pale", "joint"),        # elbow
                C((-1, ey - lower, sz - 1), (2, lower - 1.5, 2), "dw_skin", "limb"),
                C((-1.5, ey - lower - 3, sz - 1), (3, 3, 2), "dw_dark", "palm"),
            ]
            hy = ey - lower - 3
            for i, fan in enumerate((-15.0, -5.0, 5.0, 15.0)):
                fore += finger((-1.125 + i * 0.75, hy + 0.3, sz), fan, -7.0 - 2.0 * n,
                               (5.0, 5.0), "dw_pale", "dw_claw", width=0.5, depth=0.5)
            fore += finger((0.0, hy + 1.0, sz + 1.0), 0.0, -10.0, (3.0, 3.5),
                           "dw_pale", "dw_claw", width=0.5, depth=0.5, splay=-35.0)     # thumb
            for key, cubes in ((f"arm_{side}{n}", arm), (f"fore_{side}{n}", fore)):
                moved = []
                for c in cubes:
                    m = dict(c)
                    m["from"] = (c["from"][0] + sx, c["from"][1], c["from"][2])
                    if "rot" in c:
                        m["origin"] = (c["origin"][0] + sx, c["origin"][1], c["origin"][2])
                    moved.append(m if sg > 0 else mirror_cube(m))
                G[key] = moved

    for side, sg in (("l", 1), ("r", -1)):
        lx = 3.0
        P[f"leg_{side}"] = (sg * lx, HIP - 1, 0)
        P[f"shin_{side}"] = (sg * lx, KNEE, 0)
        par[f"leg_{side}"] = "pelvis"
        par[f"shin_{side}"] = f"leg_{side}"
        leg = [
            C((-1.5, KNEE + 15, -1.5), (3, HIP - 1 - KNEE - 15, 3), "dw_skin", "thigh"),
            C((-1, KNEE + 1, -1), (2, 14, 2), "dw_skin", "limb"),
        ]
        shin = [
            C((-1.5, KNEE - 1.5, -1.5), (3, 3, 3), "dw_pale", "joint"),             # knee
            C((-1, 2, -1), (2, KNEE - 3.5, 2), "dw_skin", "limb"),
            C((-1.5, 0, -2), (3, 2, 3), "dw_dark", "heel"),
            C((-1, 0, 1), (2, 1, 4), "dw_dark", "foot"),
            C((-0.5, 0, 5), (1, 1, 2), "dw_claw", "claw"),                          # the toe nail
        ]
        for key, cubes in ((f"leg_{side}", leg), (f"shin_{side}", shin)):
            moved = []
            for c in cubes:
                m = dict(c)
                m["from"] = (c["from"][0] + lx, c["from"][1], c["from"][2])
                moved.append(m if sg > 0 else mirror_cube(m))
            G[key] = moved

    rest = {
        "torso": (7.0, 0.0, 0.0),                     # the stoop
        "neck": (16.0, 0.0, 0.0),                     # pushes the head out over its chest
        "head": (-21.0, 0.0, 0.0),                    # ...and keeps the face level
        "hat": (3.0, 0.0, -2.0),                      # worn, not placed
        "leg_l": (-3.0, 0.0, 2.0), "leg_r": (-3.0, 0.0, -2.0),
        "shin_l": (6.0, 0.0, -1.0), "shin_r": (6.0, 0.0, 1.0),
    }
    # the fan: tier 1 out widest and a little forward, tier 3 tucked in and back; each
    # forearm bends back toward the vertical and a little forward, so the hands hang
    # (the pitch also undoes the torso's stoop, or the arms would hang behind it)
    for n, splay, pitch, bend in ((1, 30.0, -12.0, 18.0), (2, 22.0, -6.0, 13.0), (3, 15.0, 1.0, 9.0)):
        for side, sg in (("l", 1), ("r", -1)):
            rest[f"arm_{side}{n}"] = (pitch, 0.0, sg * splay)
            rest[f"fore_{side}{n}"] = (-12.0, 0.0, -sg * bend)
    return Creature("dark_walker", P, par, G, rest=rest, height_hint=7.3,
                    display_scale=3.0, bb_px_per_block=16.0)


LOCUST = _locust()
DARK_WALKER = _dark_walker()
TIERS = {"locust": LOCUST, "dark_walker": DARK_WALKER}


if __name__ == "__main__":
    for key, c in TIERS.items():
        far = max(max(abs(v) for v in p) * c.PX_PER_RU
                  for cubes in c.GEOMETRY.values() for cu in cubes
                  for p in c._cube_corners(cu))
        lo, hi = c.extents({})
        print(f"{key:12s} bones={len(c.BONE_ORDER):2d} cubes={c.cube_count():3d} "
              f"height={hi - lo:.2f} blocks (spec {c.height_hint}) "
              f"width={c.extents({}, 0)[1] - c.extents({}, 0)[0]:.2f}  "
              f"item model furthest {far:.1f}px from pivot")
