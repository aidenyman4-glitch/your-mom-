"""The Birthday People, after Dr. Nowhere — built as Blockbench mod-style models.

THE BIRTHDAY PEOPLE
    A pale, starved body under a tall black column of a head. Near the top of the column, a
    small pale bearded face looks out of the black. The column ends in a CROWN of
    ball-tipped spikes, or it grows up into a dead TREE. The arms hang dead straight and nearly
    to the ground, ending in long black fingers. The ribs stand out like a washboard over a
    sunken belly. Red strings run up from the head into the sky, like a marionette's.

Built from the five references in `docs/references/birthday_people/`: two pencil drawings of the
pair (one crowned, one with the tree), a full-length sketchbook study of the crowned one, a
frame of a black spire with a face standing on a plain with red strings rising from it, and a
frame of three of them behind a railing, their red-ribbed bodies under black columns.

PROPORTIONS are the full-length study's: the column and its crown are a quarter of the height,
the torso a third, the legs the rest. The column is nearly as wide as the shoulders, and the
face is a small pale window a third of the way down it. The fingers alone are a sixth of the
height and reach past the knee.

SIZE. 5.6 blocks to the top of the column (89 px), 6.4 to the tip of the crown, 7.6 to the
tree's highest twig. The references never put a person next to one, but in every frame they
tower: over a railing, over the horizon line. This puts the face three blocks above a player's
eyes, so you look UP at it, and keeps it a block under the Dark Walker.

THE RIG. 18 bones, the same skeleton for both variants:

    pelvis ─ torso ─ chest ─┬─ head ─┬─ crown      (spikes, or the tree)
                            │        └─ strings    (the red strings, their own bone so a
                            │                       datapack can hide them or let them sway)
                            ├─ arm_l ─ fore_l ─ hand_l    (the fingers ride the hand)
                            └─ arm_r ─ fore_r ─ hand_r
           pelvis ─ leg_l ─ shin_l ─ foot_l     pelvis ─ leg_r ─ shin_r ─ foot_r

Same conventions as `tiers.py`: true scale, 16 px to the block, absolute rest-space pixels,
+X = its LEFT, +Y = up, +Z = FORWARD.
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tiers import C, Creature, _euler_q, chain, hang, mirror_cube, quat_rotate  # noqa: E402

BONES = 18
HIP, KNEE, ANKLE, SHOULDER, NECK, TOP = 42.0, 21.0, 2.0, 70.0, 71.5, 89.0


def _tip(cube):
    """Where a rotated, hanging cube ends: its root swung down its own length."""
    rx, _ry, rz = cube["rot"]
    d = quat_rotate(_euler_q(rx, 0.0, rz), (0.0, -cube["size"][1], 0.0))
    o = cube["origin"]
    return (o[0] + d[0], o[1] + d[1], o[2] + d[2])


def _body():
    """Everything below the crown: identical in both variants."""
    P, G = {}, {}
    par = {"torso": "pelvis", "chest": "torso", "head": "chest", "crown": "head",
           "strings": "head",
           "arm_l": "chest", "fore_l": "arm_l", "hand_l": "fore_l",
           "arm_r": "chest", "fore_r": "arm_r", "hand_r": "fore_r",
           "leg_l": "pelvis", "shin_l": "leg_l", "foot_l": "shin_l",
           "leg_r": "pelvis", "shin_r": "leg_r", "foot_r": "shin_r"}

    # ---------------------------------------------------------------- pelvis
    P["pelvis"] = (0, HIP + 0.5, 0)
    G["pelvis"] = [
        C((-3.5, HIP - 2.5, -2.25), (7, 5, 4.5), "bp_skin", "pelvis"),
        C((-1.25, HIP - 3.5, -1.0), (2.5, 1.5, 2.0), "bp_skin", "groin"),
        C((-3.75, HIP + 1.0, 0.75), (1, 1.5, 1.25), "bp_skin", "hipbone"),   # crests of the
        C((2.75, HIP + 1.0, 0.75), (1, 1.5, 1.25), "bp_skin", "hipbone"),    # hip bones show
    ]

    # ---------------------------------------------------------------- torso (the belly)
    T = HIP + 2.5
    P["torso"] = (0, T, 0)
    G["torso"] = [
        C((-3.25, T, -2.0), (6.5, 8, 4), "bp_skin", "belly"),               # sunken, a hollow in it
        C((-2.5, T + 1.0, 2.0), (5, 1.5, 0.5), "bp_skin", "fold"),          # the skin hangs in a fold
    ]
    for y in (T + 1.0, T + 3.0, T + 5.0, T + 7.0):
        G["torso"].append(C((-0.5, y, -2.5), (1, 1, 0.5), "bp_bone", "knob"))

    # ---------------------------------------------------------------- chest (the ribs)
    CH = T + 8.0
    P["chest"] = (0, CH, 0)
    G["chest"] = [
        C((-4.5, CH, -2.5), (9, 11, 5), "bp_skin", "ribcage"),
        C((-0.5, CH + 2.5, 2.5), (1, 8, 0.5), "bp_bone", "sternum"),
        C((-6.0, CH + 11, -2.5), (12, 5, 5), "bp_skin", "shoulders"),       # wider than the hips
        C((-4.75, CH + 16, -2.0), (9.5, 1.5, 4), "bp_skin", "collar"),
    ]
    # ribs: bars proud of the chest, sloping down to the flanks — the washboard
    for k, y in enumerate((CH + 2.0, CH + 3.75, CH + 5.5, CH + 7.25, CH + 9.0)):
        w = 3.6 - 0.15 * abs(k - 2)
        for sg in (1, -1):
            x0 = 0.6 if sg > 0 else -0.6 - w
            o = (sg * 0.6, y + 0.4, 2.75)
            G["chest"].append(C((x0, y, 2.5), (w, 0.75, 0.6), "bp_skin", "rib",
                                rot=(0, 0, -sg * (14 + 3 * k)), origin=o))
    for y in (CH + 1.0, CH + 3.5, CH + 6.0, CH + 8.5, CH + 11.5, CH + 14.0):
        G["chest"].append(C((-0.5, y, -3.0), (1, 1.25, 0.5), "bp_bone", "knob"))

    # ---------------------------------------------------------------- head: the column
    P["head"] = (0, NECK, 0)
    G["head"] = [
        C((-5.25, NECK - 1.0, -4.0), (10.5, 3, 8), "bp_dark", "skirt"),     # it settles on the shoulders
        C((-4.5, NECK + 2.0, -3.75), (9, TOP - NECK - 2.0, 7.5), "bp_dark", "column"),
        C((-1.5, 82.0, 3.75), (3, 4, 0.5), "bp_face", "face"),              # a small pale window
        C((-0.5, 83.0, 4.25), (1, 1.5, 0.5), "bp_face", "nose"),
        C((-1.75, 79.5, 3.75), (3.5, 3, 0.75), "bp_dark", "beard"),         # bearded with the black
        C((-1.25, 78.0, 3.75), (2.5, 2, 0.5), "bp_dark", "beard"),
        C((-2.0, 86.0, 3.75), (4, 0.75, 0.6), "bp_dark", "brow"),           # the black hangs over it
    ]
    # the column frays into the shoulders: strands of black hanging off the skirt's edge
    rnd = random.Random(7)
    for k in range(18):
        a = k / 18.0
        if a < 0.25:
            x, z = -5.0 + 40 * a, 3.8
        elif a < 0.5:
            x, z = 5.0, 3.8 - 30.4 * (a - 0.25)
        elif a < 0.75:
            x, z = 5.0 - 40 * (a - 0.5), -3.8
        else:
            x, z = -5.0, -3.8 + 30.4 * (a - 0.75)
        if abs(x) < 1.6 and z > 0:
            continue                                               # not over the beard
        length = 1.5 + rnd.random() * 3.0
        sx = 6 if x > 4.9 else (-6 if x < -4.9 else 0)
        sz = 6 if z > 3.7 else (-6 if z < -3.7 else 0)
        G["head"].append(hang((x, NECK - 0.75, z), length, (sz, 0, -sx), "bp_dark", "strand"))

    # ---------------------------------------------------------------- arms
    for side, sg in (("l", 1), ("r", -1)):
        sx = 6.75
        E, W = SHOULDER - 22.0, SHOULDER - 42.0                    # elbow 48, wrist 28
        P[f"arm_{side}"] = (sg * sx, SHOULDER, 0)
        P[f"fore_{side}"] = (sg * sx, E, 0)
        P[f"hand_{side}"] = (sg * sx, W, 0)
        arm = [
            C((-1.25, SHOULDER - 2.0, -1.5), (2.5, 3, 3), "bp_skin", "shoulder"),
            C((-1.0, E + 1.0, -1.0), (2, SHOULDER - 2.0 - E - 1.0, 2), "bp_skin", "limb"),
            C((-1.1, E - 0.5, -1.1), (2.2, 2, 2.2), "bp_bone", "joint"),    # the elbow, knobbed
        ]
        fore = [
            C((-0.9, E - 12.0, -0.9), (1.8, 11.5, 1.8), "bp_skin", "limb"),
            C((-0.75, W + 0.5, -0.75), (1.5, E - 12.0 - W - 0.5, 1.5), "bp_skin", "limb"),
            C((-0.85, W - 0.25, -0.85), (1.7, 1.25, 1.7), "bp_bone", "joint"),  # the wrist
        ]
        # the hand: a narrow black palm turned in to the leg, and four fingers longer than a
        # forearm, a thumb at the front
        hand = [C((-0.6, W - 4.0, -1.25), (1.2, 3.75, 2.5), "bp_hand", "palm")]
        for z, segs in ((-0.95, [(5.0, 0.6), (4.5, 0.5), (3.5, 0.5)]),
                        (-0.3, [(6.0, 0.6), (5.5, 0.5), (4.5, 0.5)]),
                        (0.35, [(6.25, 0.6), (5.5, 0.5), (4.5, 0.5)]),
                        (1.0, [(5.5, 0.6), (5.0, 0.5), (4.0, 0.5)])):
            hand += chain((0.0, W - 3.75, z), segs, (z * 3.0, -1.5), (0.0, -1.5),
                          "bp_hand", "finger", tip_paint="nail")
        hand += chain((0.0, W - 2.0, 1.2), [(3.0, 0.6), (2.5, 0.5)], (-14.0, -6.0), (-6.0, 0.0),
                      "bp_hand", "finger", tip_paint="nail")
        # ---------------------------------------------------------------- legs
        lx = 2.25
        P[f"leg_{side}"] = (sg * lx, HIP, 0)
        P[f"shin_{side}"] = (sg * lx, KNEE, 0)
        leg = [
            C((-1.5, KNEE + 1.5, -1.5), (3, HIP - 1.5 - KNEE - 1.5, 3), "bp_skin", "limb"),
            C((-1.0, HIP - 4.0, -1.25), (2, 2.5, 0.5), "bp_skin", "limb"),
        ]
        P[f"foot_{side}"] = (sg * lx, ANKLE, 0)
        shin = [
            C((-1.5, KNEE - 1.25, -1.5), (3, 2.75, 3.1), "bp_bone", "joint"),   # the knee
            C((-1.25, 9.0, -1.25), (2.5, KNEE - 1.25 - 9.0, 2.5), "bp_skin", "limb"),
            C((-1.0, ANKLE, -1.0), (2, 9.0 - ANKLE, 2), "bp_skin", "limb"),
        ]
        foot = [
            C((-1.25, 0.0, -1.75), (2.5, 2.5, 3), "bp_skin", "heel"),
            C((-1.25, 0.0, 1.25), (2.5, 1, 3.0), "bp_skin", "foot"),
        ]
        for i, x in enumerate((-0.9, -0.3, 0.3, 0.9)):                  # long thin toes
            foot.append(C((x - 0.25, 0.0, 4.25), (0.5, 0.75, 1.0 + 0.25 * (i in (1, 2))),
                          "bp_hand", "nail"))
        for key, cubes, ox in ((f"arm_{side}", arm, sx), (f"fore_{side}", fore, sx),
                               (f"hand_{side}", hand, sx),
                               (f"leg_{side}", leg, lx), (f"shin_{side}", shin, lx),
                               (f"foot_{side}", foot, lx)):
            moved = []
            for c in cubes:                                         # authored about x = 0
                m = dict(c)
                m["from"] = (c["from"][0] + ox, c["from"][1], c["from"][2])
                if "rot" in c:
                    m["origin"] = (c["origin"][0] + ox, c["origin"][1], c["origin"][2])
                moved.append(m if sg > 0 else mirror_cube(m))
            G[key] = moved

    # ---------------------------------------------------------------- strings
    # two red threads from the top of the head, slack, looping once, gone up out of sight
    P["strings"] = (0, TOP, 0)
    G["strings"] = []
    for o, wob, phase in (((1.6, TOP + 1.5, -0.25), 26.0, 0.0), ((-1.6, TOP + 1.5, -0.75), 22.0, 0.5)):
        for k in range(18):
            ang = 180.0 + wob * math.sin((k / 3.2 + phase) * math.pi)
            if 6 <= k <= 9:                                         # one loose loop
                ang = 180.0 + 90.0 * (k - 5)
            seg = chain(o, [(2.25, 0.5)], (8.0 * math.sin(k * 0.9 + phase * 3), ang), (0, 0),
                        "bp_string", "string")[0]
            G["strings"].append(seg)
            o = _tip(seg)
    return P, par, G


def _crown():
    """Spikes all the way round the top of the column, each with a ball on its point; the
    middle of the front row tallest."""
    cubes = [C((-4.75, TOP - 0.5, -4.0), (9.5, 1.0, 8), "bp_dark", "crown")]
    # five across the front and five, lower, behind them, so it reads as five points from the
    # front, the way the drawings show it, and as a ring from anywhere else; the middle one
    # tallest. Each rises straight off the top of the column and narrows to a ball.
    spikes = [(x, z, h - (2.5 if z < 0 else 0.0))
              for z in (2.4, -2.4)
              for x, h in ((-3.6, 8.0), (-1.8, 10.0), (0.0, 12.0), (1.8, 10.0), (3.6, 8.0))]
    for x, z, h in spikes:
        y = TOP + 0.5
        cubes += [
            C((x - 0.8, y, z - 0.8), (1.6, h * 0.34, 1.6), "bp_dark", "spike"),
            C((x - 0.55, y + h * 0.34, z - 0.55), (1.1, h * 0.33, 1.1), "bp_dark", "spike"),
            C((x - 0.3, y + h * 0.67, z - 0.3), (0.6, h * 0.27, 0.6), "bp_dark", "spike"),
            C((x - 0.75, y + h * 0.94 - 0.25, z - 0.75), (1.5, 1.5, 1.5), "bp_dark", "ball"),
        ]
    return cubes


def _tree():
    """The column narrows into a trunk that leans and twists, and splits, and splits again,
    into a crown of dead branches far wider than the head."""
    cubes = [C((-4.75, TOP - 0.5, -4.0), (9.5, 2.0, 8), "bp_dark", "crown"),
             C((-3.75, TOP + 1.5, -3.0), (7.5, 2.5, 6), "bp_bark", "bark"),
             C((-2.75, TOP + 4.0, -2.25), (5.5, 2.5, 4.5), "bp_bark", "bark")]
    rnd = random.Random(1987)
    trunk = chain((0.25, TOP + 6.0, 0.0), [(3.5, 3.5), (3.5, 2.75), (3.0, 2.25)],
                  (4.0, 196.0), (-3.0, -12.0), "bp_bark", "bark")
    cubes += trunk

    def grow(base, rx, rz, length, width, depth):
        n = 2 if depth < 3 else 1
        segs = [(length / n, width)] * n
        bend = (rnd.uniform(-12, 12), rnd.uniform(-14, 14))
        part = chain(base, segs, (rx, rz), bend, "bp_bark", "twig" if width <= 0.6 else "bark")
        cubes.extend(part)
        if depth == 0:
            return
        end, erx, erz = _tip(part[-1]), part[-1]["rot"][0], part[-1]["rot"][2]
        kids = 2 if depth < 3 else 3
        for k in range(kids):
            spread = (k - (kids - 1) / 2) * rnd.uniform(28, 46)
            grow(end, erx + rnd.uniform(-30, 30), erz + spread,
                 length * rnd.uniform(0.62, 0.8), max(0.5, width * 0.66), depth - 1)

    end, rx, rz = _tip(trunk[-1]), trunk[-1]["rot"][0], trunk[-1]["rot"][2]
    for k, (drx, drz, ln) in enumerate(((10, -38, 6.5), (-16, 34, 7.0), (28, 6, 5.5), (-30, -10, 5.0))):
        grow(end, rx + drx, rz + drz, ln, 1.5, 3 if k < 2 else 2)
    return cubes


def _variant(name, top):
    P, par, G = _body()
    P["crown"] = (0, TOP, 0)
    G["crown"] = top()
    rest = {
        "chest": (2.0, 0.0, 0.0),                       # a little sunk at the chest
        "head": (-2.0, 0.0, 0.0),                       # the column held upright over it
        "arm_l": (0.0, 0.0, 2.5), "arm_r": (0.0, 0.0, -2.5),
        "fore_l": (-2.0, 0.0, -1.0), "fore_r": (-2.0, 0.0, 1.0),
        "hand_l": (0.0, 0.0, -1.5), "hand_r": (0.0, 0.0, 1.5),
        "leg_l": (0.0, 0.0, 0.75), "leg_r": (0.0, 0.0, -0.75),
        "shin_l": (0.0, 0.0, -0.75), "shin_r": (0.0, 0.0, 0.75),
    }
    return Creature(name, P, par, G, rest=rest, height_hint=6.0,
                    display_scale=3.0, bb_px_per_block=16.0)


CROWN = _variant("birthday_crown", _crown)
TREE = _variant("birthday_tree", _tree)
PEOPLE = {"birthday_crown": CROWN, "birthday_tree": TREE}


if __name__ == "__main__":
    for key, c in PEOPLE.items():
        far = max(max(abs(v) for v in p) * c.PX_PER_RU
                  for cubes in c.GEOMETRY.values() for cu in cubes
                  for p in c._cube_corners(cu))
        lo, hi = c.extents({})
        print(f"{key:15s} bones={len(c.BONE_ORDER):2d} cubes={c.cube_count():3d} "
              f"height={hi - lo:.2f} blocks  width={c.extents({}, 0)[1] - c.extents({}, 0)[0]:.2f}  "
              f"item model furthest {far:.1f}px from pivot")
