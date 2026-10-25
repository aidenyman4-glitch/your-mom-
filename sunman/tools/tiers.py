"""Tier 1 and Tier 2 creatures, rebuilt as Blockbench mod-style models.

LOCUST — "It doesn't see you... but it knows you're there."
    2.4 blocks. Oversized TILTED head, blank black eyes and mouth, segmented insect limbs with
    proud blocky joints, a knuckled spine, long bony fingers. Greyscale, four tones.

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
from rig import (quat_from_euler_xyz, quat_mul, quat_norm, quat_rotate,  # noqa: E402
                 vsub)

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

    def extents(self, pose, axis=1):
        sol = self.solve(pose)
        lo, hi = 1e9, -1e9
        for bone, cubes in self.GEOMETRY.items():
            pos, q = sol[bone]
            for c in cubes:
                for p in self._cube_corners(c):
                    v = pos[axis] + quat_rotate(q, p)[axis]
                    lo, hi = min(lo, v), max(hi, v)
        return lo, hi

    def solve_grounded(self, pose):
        dy = -self.extents(pose)[0]
        return {b: ((p[0], p[1] + dy, p[2]), q)
                for b, (p, q) in self.solve(pose).items()}

    def model_height(self, pose=None):
        lo, hi = self.extents(pose if pose is not None else {})
        return hi - lo

    def cube_count(self):
        return sum(len(v) for v in self.GEOMETRY.values())


# ====================================================================== LOCUST
# 2.4 blocks, 16 px to the block. Door height: it fits where you fit.

def _locust():
    P = {}                       # pivots, absolute px
    G = {}                       # cubes, absolute px
    par = {"torso": "pelvis", "head": "torso",
           "arm_l": "torso", "fore_l": "arm_l", "arm_r": "torso", "fore_r": "arm_r",
           "leg_l": "pelvis", "shin_l": "leg_l", "leg_r": "pelvis", "shin_r": "leg_r"}

    P["pelvis"] = (0, 17, 0)
    G["pelvis"] = [
        C((-3, 15, -2), (6, 4, 4), "lc_mid", "plate"),
        C((-4, 16, -1.5), (8, 2, 3), "lc_joint", "joint"),          # hip sockets
    ]
    P["torso"] = (0, 18, 0)
    G["torso"] = [
        C((-2.5, 18, -2), (5, 4, 4), "lc_mid", "segment"),          # waist, pinched
        C((-3.5, 22, -2.5), (7, 4, 5), "lc_light", "ribs"),         # thorax
        C((-3, 26, -2), (6, 3, 4), "lc_mid", "plate"),              # collar
        C((-5, 26, -1.5), (2, 3, 3), "lc_joint", "joint"),          # shoulder sockets
        C((3, 26, -1.5), (2, 3, 3), "lc_joint", "joint"),
        C((-1, 29, -1), (2, 2, 2), "lc_dark", "neck"),              # thin neck
    ]
    for y in (18.5, 21, 23.5, 26):                                  # knuckled spine
        G["torso"].append(C((-1, y, -3), (2, 1.5, 1), "lc_joint", "knob"))

    # The oversized head. Its tilt — the single most recognisable thing about it — is now the
    # head bone's rest rotation instead of a rotation baked into every cube, so animation
    # turns the head about its own neck instead of about a skewed box.
    P["head"] = (0, 30.5, 0.5)
    G["head"] = [
        C((-5, 30.5, -4), (10, 9, 9), "lc_light", "skull"),
        C((-4, 39.5, -3), (8, 1, 7), "lc_mid", "plate"),            # cranial plate
        C((-4, 34.5, 5), (3, 2, 0.5), "lc_void", "void"),           # eyes: holes, not features
        C((1, 34.5, 5), (3, 2, 0.5), "lc_void", "void"),
        C((-2, 31.5, 5), (4, 1, 0.5), "lc_void", "void"),           # mouth
    ]

    for side, sg in (("l", 1), ("r", -1)):
        sx = 4.0 * sg
        P[f"arm_{side}"] = (sx, 27.5, 0)
        P[f"fore_{side}"] = (sx, 20.5, 0)
        P[f"leg_{side}"] = (2.0 * sg, 16.5, 0)
        P[f"shin_{side}"] = (2.0 * sg, 9, 0)
        arm = [C((-1, 20.5, -1), (2, 6.5, 2), "lc_mid", "segment")]
        fore = [
            C((-1.5, 19.5, -1.5), (3, 2, 3), "lc_joint", "joint"),  # elbow
            C((-1, 13, -1), (2, 6.5, 2), "lc_mid", "segment"),
            C((-1.5, 11, -1.5), (3, 2, 3), "lc_dark", "knuckle"),   # hand
        ]
        # long bony fingers, built for climbing and grabbing
        for i, fan in enumerate((-16.0, -5.0, 5.0, 16.0)):
            fore += finger((-1.0 + i * 0.67, 11.0, 0.0), fan, 9.0, (3.0, 3.5),
                           "lc_light", "lc_dark", width=0.75, depth=0.75)
        fore += finger((0.0, 11.5, 1.0), 0.0, -14.0, (2.0, 2.0), "lc_light", "lc_dark",
                       width=0.75, depth=0.75, splay=-30.0)                 # thumb
        leg = [C((-1, 9.5, -1), (2, 7, 2), "lc_mid", "segment")]
        shin = [
            C((-1.5, 8, -1.5), (3, 2, 3), "lc_joint", "joint"),     # knee
            C((-1, 2, -1), (2, 6, 2), "lc_mid", "segment"),
            C((-1.5, 0, -1.5), (3, 2, 3), "lc_dark", "knuckle"),    # ankle
            C((-1.5, 0, 1.5), (1, 1, 3), "lc_light", "claw"),       # toes
            C((0.5, 0, 1.5), (1, 1, 3), "lc_light", "claw"),
            C((-0.5, 0, -3), (1, 1, 1.5), "lc_light", "claw"),      # heel spur
        ]
        for key, cubes in ((f"arm_{side}", arm), (f"fore_{side}", fore),
                           (f"leg_{side}", leg), (f"shin_{side}", shin)):
            px, py, pz = P[key]
            moved = []
            for c in cubes:                                         # authored about x = 0
                m = dict(c)
                m["from"] = (c["from"][0] + abs(px), c["from"][1], c["from"][2])
                if "rot" in c:
                    m["origin"] = (c["origin"][0] + abs(px), c["origin"][1], c["origin"][2])
                moved.append(m if sg > 0 else mirror_cube(m))
            G[key] = moved

    rest = {
        "torso": (8.0, 0.0, 0.0),                       # it stands hunched
        "head": (-17.0, 4.0, 11.0),                     # the tilt (and the hunch undone)
        "arm_l": (-4.0, 0.0, 6.0), "arm_r": (-4.0, 0.0, -6.0),
        "fore_l": (-14.0, 0.0, -2.0), "fore_r": (-14.0, 0.0, 2.0),
        "leg_l": (-10.0, 0.0, 3.0), "leg_r": (-10.0, 0.0, -3.0),
        "shin_l": (16.0, 0.0, -2.0), "shin_r": (16.0, 0.0, 2.0),
    }
    return Creature("locust", P, par, G, rest=rest, height_hint=2.4,
                    display_scale=1.0, bb_px_per_block=16.0)


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
        C((-2, HEAD + 2.5, 4), (1, 1, 0.5), "dw_eye", "eye", emit=15),
        C((1, HEAD + 2.5, 4), (1, 1, 0.5), "dw_eye", "eye", emit=15),
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
                               (5.0, 5.0), "dw_pale", "dw_claw", width=0.75, depth=0.75)
            fore += finger((0.0, hy + 1.0, sz + 1.0), 0.0, -10.0, (3.0, 3.5),
                           "dw_pale", "dw_claw", width=0.75, depth=0.75, splay=-35.0)   # thumb
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
