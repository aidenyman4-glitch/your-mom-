"""Tier 1 and Tier 2 creatures, built to the character sheets.

LOCUST — "It doesn't see you... but it knows you're there."
    Tall and thin, 2.4 blocks. Oversized TILTED head, blank black eyes and mouth, segmented
    insect-like limbs with exposed blocky joints, a segmented spine, and long bony fingers
    built for climbing and grabbing. Greyscale, four tones.

DARK WALKER — "It does not hurry, because it does not need to."
    7.4 blocks. Wide-brimmed hat, a small head under it with two lit eyes, six tendril arms
    hanging in three tiers, and legs that are most of its height. Near-black.

The Locust is authored at 16 px = 1 block (display scale 1.0). The Dark Walker is authored
at 16/3 px per block (display scale 3.0), because a 4-block leg at 16 px/block would put the
element 65 px from its pivot — legal in 26.3, which dropped the [-16, 32] bound, but outside
what Blockbench will open for hand-editing.

Axes match the Sun Man rig: +X = the creature's LEFT, +Y = up, +Z = FORWARD.
"""
import math

PX_PER_RU = 16.0
DISPLAY_SCALE = 16.0 / PX_PER_RU      # = 1.0

from rig import (quat_from_euler_xyz, quat_mul, quat_norm, quat_rotate,  # noqa: E402
                 vsub)


def _box(x, y, z, w, h, d, mat, **kw):
    c = {"from": [x, y, z], "size": [w, h, d], "mat": mat}
    c.update(kw)
    return c


class Creature:
    """A small authored rig exposing the interface the exporters use."""

    def __init__(self, name, joints, parents, geometry, anims,
                 light=None, billboard=None, height_hint=0.0, display_scale=1.0):
        self.name = name
        self.J = joints
        self.GEOMETRY = geometry
        self.ANIMATIONS = anims
        self.LIGHT_EMISSION = light or {}
        self.BILLBOARD = billboard or {}
        # px per block in the emitted model, and the item_display scale that undoes it
        self.DISPLAY_SCALE = display_scale
        self.PX_PER_RU = 16.0 / display_scale
        self.height_hint = height_hint

        order, seen = [], set()

        def visit(n):
            if n in seen:
                return
            p = parents.get(n)
            if p:
                visit(p)
            seen.add(n)
            order.append(n)

        for n in joints:
            visit(n)
        self.BONE_ORDER = order
        self.BONES = {n: (parents.get(n), n, None, (0.0, -1.0, 0.0)) for n in order}

    def _zero(self):
        return {b: (0.0, 0.0, 0.0) for b in self.BONE_ORDER}

    def solve(self, pose):
        out = {}
        for bone in self.BONE_ORDER:
            parent = self.BONES[bone][0]
            q = quat_from_euler_xyz(*pose.get(bone, (0.0, 0.0, 0.0)))
            if parent is None or parent not in out:
                out[bone] = (self.J[bone], quat_norm(q))
                continue
            p_pos, p_q = out[parent]
            off = vsub(self.J[bone], self.J[parent])
            out[bone] = (tuple(a + b for a, b in zip(p_pos, quat_rotate(p_q, off))),
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
            rq = quat_from_euler_xyz(rot.get("x", 0.0), rot.get("y", 0.0), rot.get("z", 0.0))
            pts = [tuple(a + b for a, b in
                         zip(o, quat_rotate(rq, (p[0] - o[0], p[1] - o[1], p[2] - o[2]))))
                   for p in pts]
        return pts

    def extents(self, pose):
        sol = self.solve(pose)
        lo, hi = 1e9, -1e9
        for bone, cubes in self.GEOMETRY.items():
            pos, q = sol[bone]
            for c in cubes:
                for p in self._cube_corners(c):
                    y = pos[1] + quat_rotate(q, p)[1]
                    lo, hi = min(lo, y), max(hi, y)
        return lo, hi

    def solve_grounded(self, pose):
        dy = -self.extents(pose)[0]
        return {b: ((p[0], p[1] + dy, p[2]), q)
                for b, (p, q) in self.solve(pose).items()}

    def model_height(self, pose=None):
        lo, hi = self.extents(pose if pose is not None else self._zero())
        return hi - lo

    def rest_rotation(self, bone):
        return (1.0, 0.0, 0.0, 0.0)


# ---------------------------------------------------------------- shared builders

def segmented_limb(length, w0, w1, mat, mat_joint, segs=3, knob=1.5, bow=0.0):
    """A limb of `segs` tapering sections with a proud joint knob between each.

    Exposed blocky joints are the Locust's defining limb feature, and they carry the Dark
    Walker's tendrils too — six identical smooth arms would read as cloth on a frame.
    """
    out = []
    step = length / segs
    for i in range(segs):
        t0, t1 = i / segs, (i + 1) / segs
        w = w0 + (w1 - w0) * (t0 + t1) / 2
        zc = bow * math.sin(math.pi * (t0 + t1) / 2)
        out.append(_box(-w / 2, -step * (i + 1), zc - w / 2, w, step, w, mat))
        if i < segs - 1:
            k = w * knob
            out.append(_box(-k / 2, -step * (i + 1) - k * 0.22, zc - k / 2,
                            k, k * 0.44, k, mat_joint))
    return out


def hollow_face(w, h, d, mat, mat_void, eye_w, eye_h, eye_gap, mouth_w, mouth_h,
                eye_y, mouth_y, rot=None):
    """A blocky head with eyes and a mouth as proud black plates.

    Both sheets specify hollow black eyes AND a hollow mouth with no expression, so the
    features are separate cubes sitting just proud of the face rather than painted on — they
    stay readable at any light level, which a texture alone does not.
    """
    r = {"rotation": rot} if rot else {}
    cubes = [_box(-w / 2, -h * 0.25, -d / 2, w, h, d, mat, **r)]
    zf = d / 2 - 0.004
    cubes.append(_box(-eye_gap / 2 - eye_w, eye_y, zf, eye_w, eye_h, 0.05, mat_void, **r))
    cubes.append(_box(eye_gap / 2, eye_y, zf, eye_w, eye_h, 0.05, mat_void, **r))
    cubes.append(_box(-mouth_w / 2, mouth_y, zf, mouth_w, mouth_h, 0.05, mat_void, **r))
    return cubes


# ====================================================================== LOCUST
# 2.4 blocks. Tall and thin, oversized tilted head, segmented insect limbs, long bony fingers,
# exposed joints and a segmented spine. "Flexible but fragile."

def _locust():
    J = {
        "pelvis":   (0.00, 1.02,  0.00),
        "torso":    (0.00, 1.10,  0.00),
        "head":     (0.00, 1.84,  0.02),
        "arm_l":    (0.26, 1.58, -0.01),
        "arm_r":   (-0.26, 1.58, -0.01),
        "hand_l":   (0.30, 0.74, -0.01),
        "hand_r":  (-0.30, 0.74, -0.01),
        "leg_l":    (0.15, 1.02,  0.00),
        "leg_r":   (-0.15, 1.02,  0.00),
        "foot_l":   (0.15, 0.10,  0.00),
        "foot_r":  (-0.15, 0.10,  0.00),
    }
    P = {"torso": "pelvis", "head": "torso",
         "arm_l": "torso", "arm_r": "torso", "hand_l": "arm_l", "hand_r": "arm_r",
         "leg_l": "pelvis", "leg_r": "pelvis", "foot_l": "leg_l", "foot_r": "leg_r"}

    G = {}
    G["pelvis"] = [
        _box(-0.17, -0.12, -0.11, 0.34, 0.22, 0.22, "lc_mid"),
        _box(-0.20, -0.04, -0.09, 0.40, 0.08, 0.18, "lc_joint"),
    ]
    G["torso"] = [
        _box(-0.19, 0.00, -0.12, 0.38, 0.26, 0.24, "lc_mid"),
        _box(-0.21, 0.26, -0.13, 0.42, 0.22, 0.26, "lc_light"),
        _box(-0.19, 0.48, -0.12, 0.38, 0.18, 0.24, "lc_mid"),
        # exposed segmented spine — called out on the sheet's back detail
        _box(-0.07, 0.04, -0.17, 0.14, 0.07, 0.07, "lc_joint"),
        _box(-0.07, 0.17, -0.17, 0.14, 0.07, 0.07, "lc_joint"),
        _box(-0.07, 0.30, -0.18, 0.14, 0.07, 0.07, "lc_joint"),
        _box(-0.07, 0.43, -0.17, 0.14, 0.07, 0.07, "lc_joint"),
        _box(-0.07, 0.55, -0.16, 0.14, 0.07, 0.07, "lc_joint"),
        # shoulder sockets
        _box(-0.33, 0.40, -0.10, 0.14, 0.17, 0.20, "lc_joint"),
        _box(0.19, 0.40, -0.10, 0.14, 0.17, 0.20, "lc_joint"),
        _box(-0.07, 0.64, -0.06, 0.14, 0.10, 0.12, "lc_dark"),      # thin neck
    ]
    # oversized head, tilted on two axes — the single most recognisable feature
    TILT = {"origin": [0.0, 0.0, 0.0], "x": -9.0, "y": 4.0, "z": 11.0}
    G["head"] = hollow_face(0.62, 0.58, 0.56, "lc_light", "lc_void",
                            eye_w=0.17, eye_h=0.15, eye_gap=0.10,
                            mouth_w=0.22, mouth_h=0.08,
                            eye_y=0.16, mouth_y=-0.09, rot=TILT)
    G["head"].append(_box(-0.26, 0.32, -0.22, 0.52, 0.06, 0.44, "lc_mid", rotation=TILT))

    for side, sg in (("l", 1), ("r", -1)):
        G[f"arm_{side}"] = segmented_limb(0.84, 0.13, 0.10, "lc_mid", "lc_joint",
                                          segs=3, knob=1.7, bow=0.02)
        # long bony fingers, built for climbing and grabbing
        fing = [_box(-0.09, -0.10, -0.07, 0.18, 0.10, 0.14, "lc_dark")]
        for i in range(4):
            f = (i / 3.0) - 0.5
            fing.append(_box(-0.028 + f * 0.11, -0.40, -0.028 + abs(f) * 0.05,
                             0.056, 0.30, 0.056, "lc_light",
                             rotation={"origin": [f * 0.11, -0.10, 0.0],
                                       "x": 8.0 + abs(f) * 14, "y": 0.0, "z": f * 30.0}))
        fing.append(_box(-0.028 - sg * 0.10, -0.30, -0.09, 0.056, 0.20, 0.056, "lc_light",
                         rotation={"origin": [-sg * 0.10, -0.10, 0.0],
                                   "x": -26.0, "y": 0.0, "z": sg * 20.0}))
        G[f"hand_{side}"] = fing

        G[f"leg_{side}"] = segmented_limb(0.92, 0.15, 0.11, "lc_mid", "lc_joint",
                                          segs=3, knob=1.6, bow=-0.02)
        G[f"foot_{side}"] = [
            _box(-0.09, -0.10, -0.10, 0.18, 0.10, 0.20, "lc_dark"),
            _box(-0.07, -0.10, 0.08, 0.05, 0.06, 0.20, "lc_light"),
            _box(0.02, -0.10, 0.08, 0.05, 0.06, 0.20, "lc_light"),
            _box(-0.03, -0.10, -0.26, 0.06, 0.06, 0.18, "lc_light"),
        ]

    def frozen(phase):
        return {}

    def twitch(phase):
        j = math.sin(phase * math.tau * 3.0)
        return {"head": (1.8 * j, 4.0 * math.sin(phase * math.tau * 2.0), 1.4 * j),
                "torso": (0.8 * j, 1.2 * j, 0.0)}

    def stalk(phase):
        """Moves unnaturally — the arm swing is deliberately off-rhythm against the stride."""
        p = {}
        for side, off in (("l", 0.0), ("r", 0.5)):
            a = (phase + off) * math.tau
            p[f"leg_{side}"] = (34.0 * math.sin(a), 0.0, 0.0)
            p[f"foot_{side}"] = (-14.0 * math.sin(a), 0.0, 0.0)
            b = (phase + off + 0.18) * math.tau
            p[f"arm_{side}"] = (-26.0 * math.sin(b), 0.0, 0.0)
            p[f"hand_{side}"] = (18.0 + 12.0 * math.sin(b), 0.0, 0.0)
        p["torso"] = (5.0, 7.0 * math.sin(phase * math.tau), 0.0)
        p["head"] = (-6.0, -9.0 * math.sin(phase * math.tau), 0.0)
        return p

    def rear(phase):
        return {
            "torso": (-28.0, 0.0, 0.0), "head": (20.0, 0.0, 0.0),
            "arm_l": (-96.0, 0.0, 26.0), "arm_r": (-96.0, 0.0, -26.0),
            "hand_l": (-30.0, 0.0, 0.0), "hand_r": (-30.0, 0.0, 0.0),
            "leg_l": (16.0, 0.0, 0.0), "leg_r": (16.0, 0.0, 0.0),
        }

    def climb(phase):
        """On a wall, all four limbs splayed — the sheet's action poses."""
        p = {"torso": (62.0, 0.0, 0.0), "head": (-46.0, 0.0, 0.0)}
        for side, sg, off in (("l", 1, 0.0), ("r", -1, 0.5)):
            s = math.sin((phase + off) * math.tau)
            p[f"arm_{side}"] = (-74.0 + 24.0 * s, 0.0, sg * 34.0)
            p[f"hand_{side}"] = (-24.0, 0.0, 0.0)
            p[f"leg_{side}"] = (46.0 - 22.0 * s, 0.0, sg * 26.0)
            p[f"foot_{side}"] = (-20.0, 0.0, 0.0)
        return p

    anims = {"frozen": (frozen, 2), "twitch": (twitch, 8),
             "stalk": (stalk, 8), "rear": (rear, 2), "climb": (climb, 8)}
    return Creature("locust", J, P, G, anims, height_hint=2.4)


# ================================================================= DARK WALKER
# Tier 2. Built from five references Aiden supplied: a hilltop silhouette, an ink drawing on
# pink paper, two frames of something standing in a road at night with lit eyes, and one of
# it looking over a fence at a house. What all five share is the proportion — the legs are
# most of the creature — plus a wide flat brim and tendril arms in the two that show detail,
# and lit eyes in the three shot at night. So it gets all of it.
#
# It is deliberately the OUTDOOR tier. The Locust is found standing inside houses at door
# height; this one is 7.4 blocks and cannot follow you through a door. It is what is in the
# road, on the ridge, over the fence.

def _dark_walker():
    SH = 5.71                                   # shoulder height; the arms hang in tiers
    J = {
        "pelvis": (0.00, 4.39, 0.00),
        "torso":  (0.00, 4.39, 0.00),
        "neck":   (0.00, 5.85, 0.02),
        "head":   (0.00, 6.19, 0.02),
        "hat":    (0.00, 6.47, 0.00),
    }
    P = {"torso": "pelvis", "neck": "torso", "head": "neck", "hat": "head"}

    TIERS_Y = ((1, 0.345, SH, -0.02), (2, 0.300, SH - 0.23, -0.06), (3, 0.250, SH - 0.46, -0.10))
    for n, x, y, z in TIERS_Y:
        for side, sg in (("l", 1), ("r", -1)):
            J[f"arm_{side}{n}"] = (sg * x, y, z)
            J[f"tip_{side}{n}"] = (sg * (x + 0.05), y - 2.86, z + 0.04)
            P[f"arm_{side}{n}"] = "torso"
            P[f"tip_{side}{n}"] = f"arm_{side}{n}"
    for side, sg in (("l", 1), ("r", -1)):
        J[f"leg_{side}"] = (sg * 0.19, 4.35, 0.00)
        J[f"foot_{side}"] = (sg * 0.19, 0.13, -0.02)
        P[f"leg_{side}"] = "pelvis"
        P[f"foot_{side}"] = f"leg_{side}"

    G = {}
    G["pelvis"] = [
        _box(-0.17, -0.10, -0.11, 0.34, 0.22, 0.22, "dw_dark"),
        _box(-0.20, -0.02, -0.09, 0.40, 0.07, 0.18, "dw_mid"),
    ]
    # A torso you could close a hand around. In every reference the body is the smallest
    # part of the creature; the silhouette is legs, arms and hat.
    G["torso"] = [
        _box(-0.17, 0.00, -0.11, 0.34, 0.46, 0.22, "dw_dark"),
        _box(-0.19, 0.46, -0.12, 0.38, 0.56, 0.24, "dw_dark"),
        _box(-0.21, 1.00, -0.13, 0.42, 0.30, 0.26, "dw_dark"),
        _box(-0.44, 1.14, -0.10, 0.88, 0.14, 0.20, "dw_mid"),        # the shoulder yoke
        _box(-0.07, 1.30, -0.05, 0.14, 0.18, 0.10, "dw_dark"),       # neck root
    ]
    for i in range(5):                                                # a faint rib banding
        G["torso"].append(_box(-0.18, 0.08 + i * 0.21, -0.125, 0.36, 0.035, 0.25, "dw_mid"))

    G["neck"] = [_box(-0.055, 0.00, -0.055, 0.11, 0.34, 0.11, "dw_dark")]

    G["head"] = [
        _box(-0.19, 0.00, -0.17, 0.38, 0.30, 0.34, "dw_dark"),
        _box(-0.15, 0.30, -0.14, 0.30, 0.06, 0.28, "dw_dark"),
        # the eyes. Proud of the face and lit, because in three of the five references the
        # eyes are the only thing in the frame that is not a silhouette.
        _box(-0.145, 0.145, 0.165, 0.10, 0.055, 0.03, "dw_eye", emit=15),
        _box(0.045, 0.145, 0.165, 0.10, 0.055, 0.03, "dw_eye", emit=15),
    ]

    # The hat. Tipped a few degrees so it reads as worn rather than placed, and wide enough
    # that the brim is the first thing you identify at any distance.
    TIP = {"origin": [0.0, 0.0, 0.0], "x": 4.0, "y": 0.0, "z": -3.0}
    G["hat"] = [_box(-0.93, 0.00, -0.93, 1.86, 0.055, 1.86, "dw_hat", rotation=TIP),
                _box(-0.86, 0.055, -0.86, 1.72, 0.03, 1.72, "dw_mid", rotation=TIP)]
    for i, (w, h) in enumerate(((0.30, 0.26), (0.26, 0.24), (0.21, 0.22), (0.17, 0.14))):
        y = 0.055 + sum(k for _, k in ((0.30, 0.26), (0.26, 0.24), (0.21, 0.22))[:i])
        G["hat"].append(_box(-w, y, -w, w * 2, h, w * 2, "dw_hat", rotation=TIP))

    for n, _x, _y, _z in TIERS_Y:
        for side, sg in (("l", 1), ("r", -1)):
            # Each tendril is a touch longer and thinner than the one above it, and bows
            # outward a little, so six arms hanging together never read as a repeated part.
            G[f"arm_{side}{n}"] = segmented_limb(2.86 + n * 0.06, 0.125 - n * 0.012,
                                                 0.055, "dw_dark", "dw_pale",
                                                 segs=4, knob=1.35, bow=sg * 0.03 * n)
            # the splayed cluster at the tip
            tip = [_box(-0.05, -0.08, -0.05, 0.10, 0.08, 0.10, "dw_pale")]
            for k in range(5):
                f = (k / 4.0) - 0.5
                tip.append(_box(-0.018 + f * 0.085, -0.52, -0.018 + abs(f) * 0.04,
                                0.036, 0.46, 0.036, "dw_dark",
                                rotation={"origin": [f * 0.085, -0.08, 0.0],
                                          "x": 6.0 + abs(f) * 18, "y": 0.0, "z": f * 34.0}))
            G[f"tip_{side}{n}"] = tip

    for side, sg in (("l", 1), ("r", -1)):
        G[f"leg_{side}"] = segmented_limb(4.22, 0.185, 0.085, "dw_dark", "dw_pale",
                                          segs=3, knob=1.45, bow=-0.05)
        G[f"foot_{side}"] = [
            _box(-0.065, -0.11, -0.10, 0.13, 0.11, 0.30, "dw_dark"),
            _box(-0.05, -0.11, 0.18, 0.10, 0.06, 0.16, "dw_pale"),
        ]

    def still(phase):
        return {}

    def watch(phase):
        """It stands at the end of the road and does not move. Only the tendrils drift —
        on six different clocks, so they never agree with each other."""
        p = {"torso": (1.0, 0.0, 0.0)}
        for i, (n, _x, _y, _z) in enumerate(TIERS_Y):
            for j, (side, sg) in enumerate((("l", 1), ("r", -1))):
                o = (i * 2 + j) * 0.17
                d = math.sin((phase + o) * math.tau)
                p[f"arm_{side}{n}"] = (3.0 * d, 2.0 * math.sin((phase + o) * math.tau * 0.5),
                                       sg * (4.0 + 2.5 * d))
                p[f"tip_{side}{n}"] = (6.0 * math.sin((phase + o + 0.3) * math.tau), 0.0, 0.0)
        # one slow turn of the head, late, and then it holds
        k = max(0.0, min(1.0, (phase - 0.55) / 0.3))
        p["neck"] = (0.0, -26.0 * k, 0.0)
        p["head"] = (0.0, -12.0 * k, 1.5 * k)
        return p

    def walk(phase):
        """The stride. Slow, enormous, and the head never moves — the hat brim holds dead
        level through the whole cycle while four metres of leg swing underneath it."""
        p = {}
        for side, off, reach in (("l", 0.0, 1.0), ("r", 0.5, 0.88)):
            a = (phase + off) * math.tau
            sw = math.sin(a)
            lift = max(0.0, math.cos(a))
            p[f"leg_{side}"] = (31.0 * sw * reach, 0.0, 0.0)
            p[f"foot_{side}"] = (-16.0 * sw + 12.0 * lift, 0.0, 0.0)
        body = math.sin(phase * math.tau * 2.0)
        p["pelvis"] = (0.0, 2.2 * math.sin(phase * math.tau), 1.1 * body)
        p["torso"] = (2.0, 0.0, -0.8 * body)
        p["neck"] = (-2.0, 0.0, 0.8 * body)                  # cancels it: the head is fixed
        p["head"] = (0.0, 0.0, 0.0)
        for i, (n, _x, _y, _z) in enumerate(TIERS_Y):
            for j, (side, sg) in enumerate((("l", 1), ("r", -1))):
                o = (i * 2 + j) * 0.13
                d = math.sin((phase + o) * math.tau)
                p[f"arm_{side}{n}"] = (7.0 * d, 0.0, sg * (3.0 + 2.0 * d))
                p[f"tip_{side}{n}"] = (10.0 * math.sin((phase + o + 0.22) * math.tau), 0.0, 0.0)
        return p

    def loom(phase):
        """It folds down to your height. The brim tips forward over the eyes as it comes."""
        k = min(1.0, phase * 1.35)
        e = k * k * (3 - 2 * k)
        p = {
            "torso": (46.0 * e, 0.0, 0.0),
            "neck": (-22.0 * e, 0.0, 0.0),
            "head": (16.0 * e, 0.0, 0.0),
            "hat": (9.0 * e, 0.0, 0.0),
            "leg_l": (16.0 * e, 0.0, 3.0 * e), "leg_r": (13.0 * e, 0.0, -3.0 * e),
            "foot_l": (-14.0 * e, 0.0, 0.0), "foot_r": (-11.0 * e, 0.0, 0.0),
        }
        for i, (n, _x, _y, _z) in enumerate(TIERS_Y):
            for j, (side, sg) in enumerate((("l", 1), ("r", -1))):
                o = (i * 2 + j) * 0.15
                p[f"arm_{side}{n}"] = (-34.0 * e - 8.0 * math.sin((phase + o) * math.tau),
                                       0.0, sg * (10.0 + 6.0 * i) * e)
                p[f"tip_{side}{n}"] = (-20.0 * e, 0.0, 0.0)
        return p

    def reach(phase):
        """All six come up together. The digits open at the end of the gesture, not before."""
        k = min(1.0, phase * 1.25)
        e = k * k * (3 - 2 * k)
        open_ = max(0.0, (phase - 0.62) / 0.38)
        p = {"torso": (-9.0 * e, 0.0, 0.0), "neck": (6.0 * e, 0.0, 0.0),
             "head": (8.0 * e, 0.0, 0.0), "hat": (-4.0 * e, 0.0, 0.0)}
        for i, (n, _x, _y, _z) in enumerate(TIERS_Y):
            for j, (side, sg) in enumerate((("l", 1), ("r", -1))):
                o = (i * 2 + j) * 0.09
                lead = max(0.0, min(1.0, (phase - o) * 2.2))
                p[f"arm_{side}{n}"] = (-96.0 * e * lead, 0.0, sg * (6.0 + 9.0 * i) * e)
                p[f"tip_{side}{n}"] = (-46.0 * e * lead + 30.0 * open_,
                                       0.0, sg * 18.0 * open_)
        return p

    anims = {"still": (still, 2), "watch": (watch, 8), "walk": (walk, 8),
             "loom": (loom, 6), "reach": (reach, 6)}
    light = {f"head": 15}
    return Creature("dark_walker", J, P, G, anims, light=light,
                    height_hint=7.4, display_scale=3.0)


LOCUST = _locust()
DARK_WALKER = _dark_walker()
TIERS = {"locust": LOCUST, "dark_walker": DARK_WALKER}


if __name__ == "__main__":
    for key, c in TIERS.items():
        mx = max(max(abs(v) for v in p)
                 for cubes in c.GEOMETRY.values() for cu in cubes
                 for p in c._cube_corners(cu))
        print(f"{key:16s} bones={len(c.BONE_ORDER):2d} "
              f"cubes={sum(len(v) for v in c.GEOMETRY.values()):3d} "
              f"height={c.model_height():.2f} (spec {c.height_hint})  "
              f"max local {mx * c.PX_PER_RU:.1f}px")
        for a, (fn, n) in c.ANIMATIONS.items():
            print(f"{'':18s}{a:8s} {n} keyframes, height {c.model_height(fn(0.3)):.2f}")
