"""The Abandoned Village's props, built as Blockbench models: the dead, and what is left.

The Abandoned Village needs its dead. The old pack dressed armour stands as corpses, and they
read as scarecrows: a stand cannot lie down. These are real models instead, each one a single
item model shown by a single `item_display`, so a corpse costs one entity and lies flat on the
ground at any angle, exactly as drawn here.

Built after the references (a villager left in the grass, the arms broken apart from the
crossed pose, the head knocked off and rolled away, blood under the neck):

    dead_villager_a   on its back, arms flung out, the head torn half off and turned aside
    dead_villager_b   face down; the head is off, rolled onto its side an arm's length away;
                      one arm torn away entirely
    dead_villager_c   on its side, one arm reaching on past the head the way it was crawling,
                      the knees drawn up, three claw gashes down its back
    dead_villager_head  a head on its own, on its side
    dead_villager_arm   an arm on its own, torn off at the shoulder
    crucified_villager  nailed to a cross on the roof of a house, the head lolled over, roped at
                        the wrists and ankles, the blood run down the post (shown at 3x)
    dead_iron_golem     the village's golem, fallen on its back and left: cracked, rusted, an
                        arm broken off, vines grown over it, a dead poppy on its chest; no blood
                        (shown at 2x)
    dead_grass_a / _b   tufts of dead grass, crossed planes like a plant model: tall straw, and
                        a short dry clump with a twig
    broken_wood_a/_b/_c splintered boards; a snapped beam with a plank fallen across it; a door
                        torn off its hinges and broken

Villager proportions (head 8 x 10 x 8, robe 8 x 18 x 6, legs 4 x 12 x 4, arms 4 x 10 x 4) and
iron golem proportions (head 8 x 10 x 8, body 18 x 12 x 11, arms 4 x 30 x 6, legs 6 x 16 x 5), on
a true pixel grid, 16 px to the block. Every part is a box with at most ONE rotation axis (a yaw
for anything lying on the ground; a tilt about X or Z for a leaning plank or a lolled head) --
a single-axis element renders the same in Blockbench and in the game whatever the Euler order.
The two big props are written into their item models at 1/2 and 1/3 size (so every element
stays inside the [-16, 32] box) and the datapack shows them scaled back up (SCALE).

The skin is the pack's own (`textures/entity/village_props.png`, 32 texels to the block),
painted after the villager look — the brown robe, the big nose, the heavy brow — in the grey of
something that has been dead a day, with blood soaked into the cloth around every wound and
stumps that show the meat and the bone.

    python3 tools/props.py      ->  texture, item models + item definitions, blockbench/village_props.bbmodel
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paint_tiers import (DIRS, Face, MaxRects, _dims, _h, _rnd, _shade_side,  # noqa: E402
                         _unwrap, fbm, vnoise)

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "resourcepack" / "assets" / "sunman"
TEXTURE = PACK / "textures" / "entity" / "village_props.png"
TEXTURE_ID = "sunman:entity/village_props"
SIZE = 512
TEXELS = 2

RAMPS = {
    "skin":  [(206, 172, 152), (188, 152, 132), (166, 130, 112), (142, 107, 92), (114, 84, 74), (82, 60, 54)],
    "robe":  [(134, 98, 68), (114, 82, 56), (96, 68, 46), (80, 56, 37), (62, 43, 29), (43, 29, 20)],
    "pants": [(110, 84, 62), (92, 70, 51), (76, 57, 41), (62, 46, 33), (47, 34, 25), (32, 23, 17)],
    "shoe":  [(98, 88, 80), (80, 71, 64), (64, 56, 50), (50, 43, 38), (37, 31, 27), (24, 20, 17)],
    "iron":  [(214, 208, 198), (190, 184, 174), (164, 158, 150), (138, 132, 125), (108, 103, 98), (74, 70, 66)],
    "vine":  [(108, 150, 60), (88, 128, 48), (70, 106, 40), (54, 86, 32), (40, 66, 26), (28, 46, 20)],
    "wood":  [(170, 138, 92), (150, 120, 78), (128, 100, 64), (106, 82, 52), (84, 64, 40), (60, 45, 28)],
    "beam":  [(122, 102, 80), (104, 86, 66), (88, 72, 54), (72, 58, 44), (56, 45, 34), (40, 32, 24)],
    "fresh": [(222, 196, 146), (206, 178, 128), (188, 158, 110), (166, 136, 92), (140, 112, 74), (110, 86, 56)],
    "rope":  [(150, 128, 94), (128, 108, 78), (106, 88, 62), (86, 70, 50), (64, 52, 36), (44, 36, 26)],
    "straw": [(198, 184, 142), (176, 160, 118), (152, 136, 98), (128, 114, 80), (104, 92, 64), (80, 70, 48)],
    "hinge": [(96, 92, 90), (78, 74, 72), (62, 58, 56), (48, 45, 44), (36, 34, 33), (24, 22, 22)],
    "poppy": [(150, 60, 44), (124, 48, 36), (98, 40, 30), (70, 90, 40), (52, 70, 30), (36, 50, 22)],
}
RUST = (148, 84, 46)
SCALE = {"crucified_villager": 3, "dead_iron_golem": 2}     # shown this many times bigger
BLOOD = [(74, 7, 9), (98, 10, 12), (126, 15, 17), (154, 22, 22), (182, 28, 26), (210, 38, 34)]
MEAT = (150, 40, 44)
BONE = (226, 216, 196)
EYE = (212, 210, 198)
VOID = (16, 10, 10)


def box(frm, size, mat, paint, ry=0.0, origin=None, rx=0.0, rz=0.0, **extra):
    """A part in ground-relative pixels (y = 0 is the ground), with at most one rotation
    (a yaw `ry`, or a tilt `rx` / `rz`) about `origin`. `extra` names special faces:
    face="up" puts the face on that side and top="south" says which way the top of the head
    points; stump=["north"] makes a face a torn stump; broken=["east"] a splintered end."""
    assert sum(1 for a in (rx, ry, rz) if a) <= 1, "one rotation axis per element"
    c = {"from": tuple(float(v) for v in frm), "size": tuple(float(v) for v in size),
         "mat": mat, "paint": paint}
    for k, a in (("rx", rx), ("ry", ry), ("rz", rz)):
        if a:
            c[k] = float(a)
            c["origin"] = tuple(float(v) for v in (origin or frm))
    c.update(extra)
    return c


def _group(cubes, ry, origin):
    """Yaw a whole limb (several boxes) about one joint."""
    for c in cubes:
        c["ry"] = float(ry)
        c["origin"] = tuple(float(v) for v in origin)
    return cubes


# ====================================================================== the bodies

def corpse_a():
    """On its back. The arms flung out, the head torn half off at the neck and turned."""
    parts = [box((-4, 0, -9), (8, 6, 18), "robe", "robe", ry=-6, origin=(0, 0, 0))]
    parts += _group([box((0.2, 0, -15), (3.8, 3.8, 6), "pants", "leg"),
                     box((0.2, 0, -17), (3.8, 3.8, 2), "shoe", "shoe")], 9, (2, 0, -9))
    parts += _group([box((-4.0, 0, -15), (3.8, 3.8, 6), "pants", "leg"),
                     box((-4.0, 0, -17), (3.8, 3.8, 2), "shoe", "shoe")], -15, (-2, 0, -9))
    parts += _group([box((-4, 0, 9.5), (8, 8, 10), "skin", "head", face="up", top="south",
                         stump=["north"]),
                     box((-1, 8, 11), (2, 2, 4), "skin", "nose")], 24, (0, 0, 9.5))
    parts += _group([box((4.5, 0, -1), (4, 4, 8), "robe", "sleeve"),
                     box((4.5, 0, -3), (4, 3.6, 2), "skin", "hand")], -48, (6.5, 0, 7))
    parts += _group([box((-8.5, 0, -1), (4, 4, 8), "robe", "sleeve"),
                     box((-8.5, 0, -3), (4, 3.6, 2), "skin", "hand")], 18, (-6.5, 0, 7))
    wounds = [((0, 4, 9.5), 4.5), ((1.5, 6, 2.5), 2.6)]
    return parts, wounds


def corpse_b():
    """Face down. The head is off and lies on its side an arm's length away, looking back
    at the body. One arm is gone from the shoulder and lies further off."""
    parts = [box((-4, 0, -9), (8, 6, 18), "robe", "robe", ry=4, origin=(0, 0, 0), stump=["south"])]
    parts += _group([box((0.3, 0, -15), (3.8, 3.8, 6), "pants", "leg"),
                     box((0.3, 0, -17), (3.8, 3.8, 2), "shoe", "shoe")], 4, (2, 0, -9))
    parts += _group([box((-4.1, 0, -15), (3.8, 3.8, 6), "pants", "leg"),
                     box((-4.1, 0, -17), (3.8, 3.8, 2), "shoe", "shoe")], 22, (-2, 0, -9))
    # the head, rolled onto its side: its top points +X, its face +Z
    parts += _group([box((9, 0, 7), (10, 8, 8), "skin", "head", face="south", top="east",
                         stump=["west"]),
                     box((10.5, 3, 15), (4, 2, 2), "skin", "nose")], -32, (14, 0, 11))
    # the right arm still on, crushed under it at the side
    parts += _group([box((-8.5, 0, -1), (4, 4, 8), "robe", "sleeve"),
                     box((-8.5, 0, -3), (4, 3.6, 2), "skin", "hand")], 10, (-6.5, 0, 7))
    # the left arm, torn away, lying out past the hip
    parts += _group([box((8, 0, -14), (4, 4, 8), "robe", "sleeve", stump=["south"]),
                     box((8, 0, -16), (4, 3.6, 2), "skin", "hand")], 64, (10, 0, -10))
    wounds = [((0, 3, 9), 4.5), ((13, 4, 9), 3.5), ((4.5, 3, 6), 3.0), ((10, 2, -6), 2.5)]
    return parts, wounds


def corpse_c():
    """On its side, curled. One arm reaches on past the head, the way it was crawling when
    it was caught; three gashes run down its back."""
    parts = [box((-3, 0, -9), (6, 8, 18), "robe", "robe", ry=-8, origin=(0, 0, 0), claws="west")]
    # knees drawn up: thighs forward of the hips, shins back under
    parts += _group([box((-2, 0, -14), (4, 3.8, 5), "pants", "leg")], 38, (0, 0, -9))
    parts += _group([box((-2, 0, -12), (4, 3.8, 5), "pants", "leg"),
                     box((-2, 0, -14), (4, 3.8, 2), "shoe", "shoe")], -42, (3, 0, -15.5))
    parts += _group([box((-2, 3.8, -14), (4, 3.8, 5), "pants", "leg")], 52, (0, 3.8, -9))
    # the head on its side: top +Z, face to +X
    parts += _group([box((-4, 0, 9.5), (8, 8, 10), "skin", "head", face="east", top="south"),
                     box((4, 3, 11), (2, 2, 4), "skin", "nose")], 14, (0, 0, 9.5))
    # the reaching arm, out past the head
    parts += _group([box((3.5, 0, 9), (4, 4, 9), "robe", "sleeve"),
                     box((3.5, 0, 18), (4, 3.6, 2.5), "skin", "hand")], -12, (5.5, 0, 9))
    parts += _group([box((-7.5, 0, -3), (4, 4, 8), "robe", "sleeve"),
                     box((-7.5, 0, -5), (4, 3.6, 2), "skin", "hand")], 30, (-5.5, 0, 5))
    wounds = [((-3, 6, 1), 4.0), ((0, 4, 9.5), 2.5)]
    return parts, wounds


def loose_head():
    parts = [box((-5, 0, -4), (10, 8, 8), "skin", "head", face="south", top="east", stump=["west"]),
             box((-3.5, 3, 4), (4, 2, 2), "skin", "nose")]
    return parts, [((-5, 4, 0), 3.0)]


def loose_arm():
    parts = [box((-2, 0, -4), (4, 4, 8), "robe", "sleeve", stump=["south"]),
             box((-2, 0, -6), (4, 3.6, 2), "skin", "hand")]
    return parts, [((0, 2, 4), 3.0)]


def crucified():
    """Nailed to a cross on a roof, facing the bell. The model faces -Z, so the item_display
    half turn leaves it facing the entity's yaw."""
    parts = [box((-1.5, 0, -1.5), (3, 58, 3), "beam", "beam"),
             box((-17, 42, -1.5), (34, 3, 3), "beam", "beam"),
             box((-4, 16, -7.5), (8, 20, 6), "robe", "robe"),
             box((-3.9, 5, -6.4), (3.8, 11, 3.8), "pants", "leg"),
             box((0.1, 5, -6.4), (3.8, 11, 3.8), "pants", "leg"),
             box((-3.9, 3, -6.4), (3.8, 2, 3.8), "shoe", "shoe"),
             box((0.1, 3, -6.4), (3.8, 2, 3.8), "shoe", "shoe"),
             box((4, 38, -6), (13, 4, 4), "robe", "sleeve"),
             box((17, 38, -6), (2.5, 4, 4), "skin", "hand"),
             box((-17, 38, -6), (13, 4, 4), "robe", "sleeve"),
             box((-19.5, 38, -6), (2.5, 4, 4), "skin", "hand"),
             box((14, 37.5, -6.5), (1.2, 5, 5), "rope", "rope"),
             box((-15.2, 37.5, -6.5), (1.2, 5, 5), "rope", "rope"),
             box((-4.3, 6, -6.8), (8.6, 1.2, 4.6), "rope", "rope")]
    # the head lolled over to one side
    parts += [box((-4, 36.5, -8.5), (8, 10, 8), "skin", "head", face="north", top="up", rz=18, origin=(0, 36.5, -4.5)),
              box((-1, 37.5, -10.5), (2, 4, 2), "skin", "nose", face="north", rz=18, origin=(0, 36.5, -4.5))]
    wounds = [((18.2, 40, -6), 2.4), ((-18.2, 40, -6), 2.4), ((0, 4, -6.6), 2.6), ((3.5, 27, -7.5), 3.2)]
    drips = [((-1.2, 1.2), (0, 5), (-1.6, -1.4)), ((2.6, 4.2), (16, 26), (-7.6, -7.4)),
             ((16.6, 19.6), (35, 38.2), (-6.1, -1.9)), ((-19.6, -16.6), (35, 38.2), (-6.1, -1.9))]
    return parts, wounds, drips


def dead_golem():
    """The village's iron golem, on its back where it fell. No blood: it never had any.
    Cracked, rusting, one arm broken off and lying apart, vines grown over it, and the poppy
    it carried dead on its chest."""
    parts = [box((-9, 0, -2), (18, 11, 12), "iron", "iron"),
             box((-4.5, 1, -7), (9, 6, 5), "iron", "iron"),
             box((0.5, 0, -23), (6, 5, 16), "iron", "iron", ry=-6, origin=(3.5, 0, -7)),
             box((-6.5, 0, -23), (6, 5, 16), "iron", "iron", ry=10, origin=(-3.5, 0, -7)),
             box((-4, 2, 10), (8, 8, 10), "iron", "golem_head", face="up", top="south", ry=14, origin=(0, 0, 10)),
             box((-1, 10, 11.5), (2, 2, 4), "iron", "nose", face="up", ry=14, origin=(0, 0, 10)),
             box((9, 0, -22), (4, 6, 30), "iron", "iron", ry=-28, origin=(11, 0, 8)),
             box((-26, 0, -18), (4, 6, 30), "iron", "iron", ry=40, origin=(-24, 0, -3), breaks=["south"]),
             box((-6, 11, 1), (8, 0.4, 8), "vine", "vine"),
             box((2.5, 7, -6.5), (2, 0.4, 4), "vine", "vine"),
             box((-2, 10, 13), (5, 0.4, 4), "vine", "vine", ry=14, origin=(0, 0, 10)),
             box((9.5, 6, -12), (3, 0.4, 9), "vine", "vine", ry=-28, origin=(11, 0, 8)),
             box((2, 11, 3), (1, 0.6, 5), "poppy", "poppy", ry=24, origin=(2.5, 11, 5.5))]
    return parts, [], []


def _planes(w, h, angles):
    return [box((-w / 2, 0, 0), (w, h, 0.01), "straw", "blades", ry=a, origin=(0, 0, 0), seed=i) if a else
            box((-w / 2, 0, 0), (w, h, 0.01), "straw", "blades", seed=i) for i, a in enumerate(angles)]


def dead_grass_a():
    """Tall dead grass: three crossed planes of straw-grey blades, some broken over."""
    return _planes(12, 10, (0, 60, 120)), [], []


def dead_grass_b():
    """A short dry clump, and a dead twig lying across it."""
    parts = _planes(8, 6, (30, 120))
    parts.append(box((-5, 0, -0.3), (10, 0.7, 0.7), "beam", "twig", ry=20, origin=(0, 0, 0)))
    return parts, [], []


def _board(frm, size, ry, origin, ends=("east",), splinters=True):
    """A broken board along X, splintered at its broken end(s)."""
    out = [box(frm, size, "wood", "plank", ry=ry, origin=origin, broken=list(ends))]
    if splinters:
        x1 = frm[0] + size[0]
        z0 = frm[2]
        out += [box((x1, frm[1] + 0.2, z0 + 0.3), (1.8, 0.6, 0.6), "fresh", "splinter", ry=ry, origin=origin),
                box((x1, frm[1] + 0.2, z0 + size[2] - 1.0), (1.2, 0.6, 0.6), "fresh", "splinter", ry=ry, origin=origin)]
    return out


def broken_wood_a():
    """Boards torn out of a wall, snapped, thrown down on top of each other."""
    parts = _board((-7, 0, -1.5), (14, 1, 3), 12, (0, 0, 0))
    parts += _board((-6, 1, -4.5), (12, 1, 3), -28, (0, 1, -3))
    parts += _board((-5, 0, 3), (10, 1, 3), 70, (0, 0, 4.5), ends=("east", "west"))
    parts += _board((2, 0, -8), (5, 1, 3), 40, (4.5, 0, -6.5))
    return parts, [], []


def broken_wood_b():
    """A beam snapped off and dropped, the break all splinters, a plank fallen across it."""
    parts = [box((-11, 0, -2), (22, 4, 4), "beam", "beam", broken=["east"]),
             box((11, 0.5, -1.6), (3.2, 1, 1), "fresh", "splinter"),
             box((11, 2.2, -0.2), (2.2, 1, 1.2), "fresh", "splinter"),
             box((11, 1.2, 1.0), (4.0, 0.8, 0.8), "fresh", "splinter"),
             box((11, 3.0, -1.2), (1.4, 0.8, 0.8), "fresh", "splinter"),
             box((-8, 2.5, -7.5), (16, 1, 3), "wood", "plank", rz=15, origin=(0, 3, -6), broken=["west"])]
    return parts, [], []


def broken_wood_c():
    """A door torn off its hinges: a corner of it gone, the torn edge splintered, the piece
    lying beside it."""
    parts = [box((-6.5, 0, -14), (13, 1.5, 22), "wood", "door", broken=["south"]),
             box((-6.5, 0, 8), (8, 1.5, 6), "wood", "door", broken=["east"]),
             box((-6.5, 1.5, -10), (4, 0.3, 1.5), "hinge", "hinge"),
             box((-6.5, 1.5, 9), (4, 0.3, 1.5), "hinge", "hinge"),
             box((1.5, 0.3, 8), (1.2, 0.8, 3.2), "fresh", "splinter"),
             box((3.2, 0.3, 7.6), (1.0, 0.8, 2.0), "fresh", "splinter"),
             box((-1.0, 0.3, 14), (1.0, 0.8, 1.6), "fresh", "splinter"),
             box((8, 0, -1), (5, 1.5, 6), "wood", "door", ry=35, origin=(10.5, 0, 2), broken=["west", "north"])]
    return parts, [], []


PROPS = {
    "dead_villager_a": corpse_a,
    "dead_villager_b": corpse_b,
    "dead_villager_c": corpse_c,
    "dead_villager_head": loose_head,
    "dead_villager_arm": loose_arm,
    "crucified_villager": crucified,
    "dead_iron_golem": dead_golem,
    "dead_grass_a": dead_grass_a,
    "dead_grass_b": dead_grass_b,
    "broken_wood_a": broken_wood_a,
    "broken_wood_b": broken_wood_b,
    "broken_wood_c": broken_wood_c,
}


def parts_of(name):
    """(parts, wounds, drips) for any prop; the corpses have no drips."""
    r = PROPS[name]()
    return r if len(r) == 3 else (r[0], r[1], [])


# ====================================================================== the skin

# The face, 8 x 10 px (16 x 20 texels), top of the head at row 0. The brow is one heavy bar;
# the eyes are open and dull, the pupils rolled up under the lids; blood has run from the nose
# (the nose itself is its own cube in the middle, rows 10..17).
#   . skin   - shade   = deep shade   B brow   W eye white   P pupil   r blood
FACE = [
    "................",
    "................",
    ".....-....-.....",
    "................",
    "...-........-...",
    "-..............-",
    "-BBBBBBBBBBBBBB-",
    "-BBBBBBBBBBBBBB-",
    "-.PWW-....-WWP.-",
    "-.WWW-....-WWW.-",
    "-..--......--..-",
    "-..............-",
    "=......rr......=",
    "=......rr......=",
    "=.....-rr-.....=",
    "=......rr......=",
    "==....=rr=....==",
    "==-....rr....-==",
    "===-...rr...-===",
    "====---rr---====",
]


# The golem's face, 8 x 10 px: the heavy brow, two empty sockets where the light was, a crack
# across the cheek. No red in the eyes: whatever lit them has gone out.
#   . iron   - shade   = deep shade   # void   x crack
GOLEM_FACE = [
    "-..............-",
    "................",
    "....-......-....",
    "................",
    "-..............-",
    "=--------------=",
    "==============x=",
    "=--==-....-==-x=",
    "-.####-..-####x-",
    "-.####-..-####.-",
    "-..--x....--...-",
    "-....x.........-",
    "-.....x........-",
    "-......x.......-",
    "-..............-",
    "=..............=",
    "=-....x.......-=",
    "==-....x.....-==",
    "===-..........==",
    "====--------====",
]


def _face_uv(f, tx, ty, cube):
    """Where a texel on the face side sits in the face map: (u 0..1 across, v 0..1 from
    the top of the head down)."""
    x, y, z = f.world(tx, ty)
    (fx, fy, fz), (sx, sy, sz) = cube["from"], cube["size"]
    rel = {"x": (x - fx) / sx, "y": (y - fy) / sy, "z": (z - fz) / sz}
    top = cube["top"]
    axis = {"south": "z", "north": "z", "east": "x", "west": "x", "up": "y", "down": "y"}[top]
    v = 1.0 - rel[axis] if top in ("south", "east", "up") else rel[axis]
    normal = {"south": "z", "north": "z", "east": "x", "west": "x", "up": "y", "down": "y"}[cube["face"]]
    across = [a for a in "xyz" if a not in (axis, normal)][0]
    return rel[across], v


def _wound_blood(x, y, z, wounds, seed):
    best = 0.0
    for (wx, wy, wz), r in wounds:
        d = math.dist((x, y, z), (wx, wy, wz))
        rr = r * (0.75 + 0.5 * vnoise(x * 0.7, y * 0.7 + 3, z * 0.7, seed))
        if d < rr:
            best = max(best, 1.0 - d / rr)
    return best


def _blades(f, tx, ty, cube):
    """Dead grass on a plane: blades from the ground, leaning, a few broken over. None where
    there is no blade (transparent)."""
    if f.d not in ("north", "south"):
        return None
    x, y, _ = f.world(tx, ty)
    lx, ly = x - cube["from"][0], y - cube["from"][1]
    w, h = cube["size"][0], cube["size"][1]
    seed = 91 + 13 * cube.get("seed", 0) + int(w * 7)
    for k in range(int(w * 1.6)):
        bx = (k + 0.5) / (w * 1.6) * w + (_rnd(k, seed, 1) - 0.5) * 0.8
        bh = h * (0.45 + 0.55 * _rnd(k, seed, 2))
        lean = (_rnd(k, seed, 3) - 0.5) * 4.0
        broken = _rnd(k, seed, 4) < 0.25
        if broken and ly > bh * 0.6:
            # snapped: the top hangs back down beside the stem
            t = (ly - bh * 0.6) / (bh * 0.4)
            cx = bx + lean * 0.6 + 1.2 * t
            if abs(lx - cx) < 0.32 and ly < bh * 0.6 + bh * 0.4 * (1 - t):
                return RAMPS["straw"][3]
            continue
        cx = bx + lean * (ly / bh) ** 1.6
        if ly < bh and abs(lx - cx) < 0.3:
            tone = 4 - int(3.5 * ly / bh) + (1 if _rnd(k, seed, 5) < 0.3 else 0)
            return RAMPS["straw"][max(0, min(5, tone))]
    return None


def _drip(x, y, z, drips):
    for (x0, x1), (y0, y1), (z0, z1) in drips:
        if x0 <= x <= x1 and y0 <= y <= y1 and z0 <= z <= z1:
            col = int(math.floor(x * 2 + z * 2))
            run = y0 + (y1 - y0) * (0.25 + 0.75 * _rnd(col, 77, 1))
            if y >= run - 0.01 or _rnd(col, 77, 2) < 0.3:
                return True
    return False


def paint_texel(f, tx, ty, cube, wounds, drips=()):
    R = RAMPS[cube["mat"]]
    st = cube["paint"]
    x, y, z = f.world(tx, ty)
    n = fbm(x * 0.4, y * 0.4, z * 0.4, seed=_h(*map(ord, cube["mat"])) & 0xFF)
    g = vnoise(x * 2.0, y * 2.0, z * 2.0, seed=7)
    d = f.d

    if st == "blades":
        return _blades(f, tx, ty, cube)
    # broken iron: the dark inside of a casting, a jagged bright rim, rust bleeding from it
    if d in cube.get("breaks", ()):
        rim = vnoise(x * 1.5, y * 1.5, z * 1.5, seed=81)
        if rim > 0.62:
            return R[1]
        return RUST if _rnd(tx, ty, 83) < 0.18 else R[5]
    # snapped wood: fresh pale fibres, dark where it split
    if d in cube.get("broken", ()):
        fib = vnoise(x * 2.5, y * 2.5, z * 2.5, seed=85)
        return RAMPS["fresh"][1 if fib > 0.55 else (3 if fib > 0.35 else 5)]

    # stumps: a ring of what it was, then meat, then bone at the heart of it
    if d in cube.get("stump", ()):
        (fx, fy, fz), (sx, sy, sz) = cube["from"], cube["size"]
        cx, cy, cz = fx + sx / 2, fy + sy / 2, fz + sz / 2
        if d in ("north", "south"):
            r = math.hypot((x - cx) / (sx / 2), (y - cy) / (sy / 2))
        elif d in ("east", "west"):
            r = math.hypot((z - cz) / (sz / 2), (y - cy) / (sy / 2))
        else:
            r = math.hypot((x - cx) / (sx / 2), (z - cz) / (sz / 2))
        r += (vnoise(x * 2, y * 2, z * 2, seed=31) - 0.5) * 0.25
        if r < 0.28:
            return BONE if _rnd(tx, ty, 3) > 0.15 else (196, 184, 162)
        if r < 0.8:
            k = 0.5 + 0.5 * vnoise(x * 3, y * 3, z * 3, seed=33)
            return tuple(int(a * (0.6 + 0.4 * k)) for a in MEAT) if _rnd(tx, ty, 5) > 0.2 else BLOOD[0]
        if r < 0.95:
            return BLOOD[1]

    if st == "golem_head" and d == cube.get("face"):
        u, v = _face_uv(f, tx, ty, cube)
        ch = GOLEM_FACE[min(19, int(v * 20))][min(15, int(u * 16))]
        if ch == "#":
            return VOID
        if ch == "x":
            return R[5]
        t = {".": 1.8, "-": 2.8, "=": 3.8}[ch] + (n - 0.5) * 0.8
        return R[max(0, min(5, int(round(t))))]
    if st == "head" and d == cube.get("face"):
        u, v = _face_uv(f, tx, ty, cube)
        ch = FACE[min(19, int(v * 20))][min(15, int(u * 16))]
        if ch == "B":
            return (56, 40, 34)
        if ch == "W":
            return EYE
        if ch == "P":
            return (48, 66, 44)
        if ch == "r":
            return BLOOD[3] if (tx + ty) % 3 else BLOOD[2]
        t = {".": 2.0, "-": 3.0, "=": 4.0}[ch] + (n - 0.5) * 0.8
        return R[max(0, min(5, int(round(t))))]

    t = _shade_side(f, tx, ty)
    t += (n - 0.5) * 1.0 + (g - 0.5) * 0.2
    if st in ("robe", "sleeve"):
        # coarse cloth: folds running down the length, a weave, the hem darker
        fold = vnoise(x * 0.9 + z * 0.15, y * 0.9, z * 0.15 + x * 0.15, seed=41)
        t += (fold - 0.5) * 1.4 + (0.3 if (tx + ty) % 2 else -0.1)
        if cube.get("claws") == d:
            # three gashes raked down the back: the cloth torn open on the meat beneath
            for k in range(3):
                off = (z - cube["from"][2]) - (6 + 3.2 * k) - 0.5 * (y - cube["from"][1])
                if abs(off) < 0.5:
                    return MEAT if abs(off) < 0.3 else BLOOD[0]
    elif st == "head":
        if d == cube.get("top"):
            t += 0.6 + (0.6 if _rnd(tx, ty, 9) < 0.08 else 0)        # the bald crown
    elif st == "nose":
        t = 1.0 if d in ("up", cube.get("face")) else 2.6
    elif st == "shoe":
        t += 0.5
    elif st == "leg":
        t += (vnoise(x * 0.8, y * 0.8, z * 0.8, seed=43) - 0.5) * 1.0
    elif st in ("iron", "golem_head"):
        # cast iron gone dull: hairline cracks, rust where the rain sat, moss underneath
        # a few long cracks, not speckle: thin lines of a slow noise field
        crack = vnoise(x * 0.35 + z * 0.12, y * 0.35, z * 0.35 + x * 0.12, seed=61)
        if abs(crack - 0.5) < 0.012:
            return R[5]
        if fbm(x * 0.35, y * 0.35, z * 0.35, seed=63) > 0.7:
            return RUST if _rnd(tx, ty, 65) > 0.35 else tuple(int(c * 0.82) for c in RUST)
        if d == "down":
            return RAMPS["vine"][4]
        if f.side and ty == f.H - 1 and y - cube["from"][1] < 0.6 and _rnd(tx, ty, 67) < 0.5:
            return RAMPS["vine"][3]
        t += 0.6 + (n - 0.5) * 0.6
    elif st == "vine":
        leaf = vnoise(x * 1.8, y * 1.8, z * 1.8, seed=71)
        t = 1.0 + 3.6 * (1 - leaf) + (0.8 if _rnd(tx, ty, 73) < 0.15 else 0)
    elif st in ("plank", "door"):
        # weathered planks: grain along the length, the gaps between boards, nail holes
        along_z = st == "door" or cube["size"][2] > cube["size"][0]
        u = x if not along_z else z
        across = z if not along_z else x
        grain = vnoise(u * 0.25, across * 2.4, y * 2.4, seed=75)
        t = 1.6 + (grain - 0.5) * 2.4 + (n - 0.5) * 0.8
        if st == "door" and int(math.floor((across - cube["from"][0 if along_z else 2]) * 2)) % 6 == 0:
            t += 1.6                                      # the seams between the door's boards
        if _rnd(int(u * 2), int(across * 2), 79) < 0.01:
            t = 5
        if f.d == "down":
            t += 1.0
    elif st == "beam":
        grain = vnoise(x * 0.2 + z * 0.2, y * 2.0, (x + z) * 1.5, seed=87)
        t = 1.8 + (grain - 0.5) * 2.6 + (n - 0.5) * 0.6
        if not f.side and f.d in ("up", "down") and cube["size"][1] > 20:
            rr = math.hypot(x - (cube["from"][0] + cube["size"][0] / 2), z - (cube["from"][2] + cube["size"][2] / 2))
            t = 1.4 + (int(rr * 3) % 2) * 1.6             # rings on the end of the post
    elif st == "splinter":
        t = 0.8 + (2.0 if (tx + ty) % 3 == 0 else 0.0) + (g - 0.5)
    elif st == "rope":
        t = 1.4 + (1.6 if int(math.floor((x + y + z) * 2.0)) % 2 else 0.0)
    elif st == "hinge":
        t = 2.6 + (2.0 if (tx + ty) % 4 == 0 else 0.0)
    elif st == "poppy":
        t = 0.6 if (z - cube["from"][2]) > cube["size"][2] - 1.6 else 3.6
    elif st == "twig":
        t = 2.4 + (1.0 if tx % 2 else 0.0)

    k = int(round(t))
    col = R[max(0, min(5, k))]
    # soaked in around each wound, patchy: the cloth shows through where it did not take
    if drips and _drip(x, y, z, drips):
        return BLOOD[2] if (tx + ty) % 4 else BLOOD[3]
    b = _wound_blood(x, y, z, wounds, seed=51) - 0.3 * vnoise(x * 1.3, y * 1.3, z * 1.3, seed=53)
    if b > 0.05:
        tone = 1 + int(4 * b ** 0.8) if cube["mat"] != "skin" else 2 + int(3 * b)
        col = BLOOD[max(0, min(5, tone - (1 if _rnd(tx, ty, 11) < 0.3 else 0)))]
    return col


# ====================================================================== layout + export

def layout():
    items = []
    for name in PROPS:
        parts, _, _ = parts_of(name)
        for i, c in enumerate(parts):
            off, (fw, fh) = _unwrap(c["size"])
            items.append((name, i, c, off, fw, fh))
    items.sort(key=lambda it: (-max(it[4], it[5]), -it[4] * it[5], it[0], it[1]))
    packer = MaxRects(0, 0, SIZE, SIZE)
    placed = {"_pool": {"box": packer.insert(64, 64) + (64, 64)}}
    for name, i, c, off, fw, fh in items:
        at = packer.insert(fw + 1, fh + 1)
        assert at is not None, "the village props no longer fit their texture"
        x, y = at
        dims = _dims(c["size"])
        faces = {}
        for d in DIRS:
            ox, oy = off[d]
            w_, h_ = dims[d]
            faces[d] = (x + ox, y + oy, x + ox + w_ * TEXELS, y + oy + h_ * TEXELS)
        placed[(name, i)] = {"faces": faces, "box": (x, y, x + fw, y + fh)}
    return placed


def paint(placed):
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    # a copy of the blood pool, for the Blockbench preview only: Bedrock projects take one
    # texture, and the pools are their own entities in game
    pool = Image.open(PACK / "textures" / "decal" / "blood_pool.png").convert("RGBA")
    im.alpha_composite(pool, placed["_pool"]["box"][:2])
    px = im.load()
    for name in PROPS:
        parts, wounds, drips = parts_of(name)
        for i, c in enumerate(parts):
            for d, rect in placed[(name, i)]["faces"].items():
                f = Face(c, d, rect, name, "body", i)
                for ty in range(f.H):
                    for tx in range(f.W):
                        col = paint_texel(f, tx, ty, c, wounds, drips)
                        if col is not None:                   # None: transparent (grass)
                            px[f.x0 + tx, f.y0 + ty] = col + (255,)
    TEXTURE.parent.mkdir(parents=True, exist_ok=True)
    im.save(TEXTURE, optimize=True)
    used = sum((e["box"][2] - e["box"][0]) * (e["box"][3] - e["box"][1])
               for k, e in placed.items() if k != "_pool")
    return used * 100 // (SIZE * SIZE)


def _r(v, n=4):
    v = round(float(v), n)
    return 0.0 if v == 0 else v


def item_model(name, placed):
    """One element per part: the model origin (8, 8, 8) is the entity's position, which the
    datapack puts on the ground, so ground-relative y = 0 lands at model y = 8. A prop with a
    SCALE is written that many times smaller; the datapack shows it scaled back up."""
    parts, _, _ = parts_of(name)
    k = float(SCALE.get(name, 1))
    els = []
    for i, c in enumerate(parts):
        frm = [c["from"][j] / k + 8 for j in range(3)]
        to = [frm[j] + c["size"][j] / k for j in range(3)]
        faces = {d: {"uv": [_r(v * 16.0 / SIZE) for v in rect], "texture": "#0"}
                 for d, rect in placed[(name, i)]["faces"].items()}
        el = {"from": [_r(v, 3) for v in frm], "to": [_r(v, 3) for v in to], "faces": faces}
        if any(c.get(a) for a in ("rx", "ry", "rz")):
            o = c["origin"]
            el["rotation"] = {"origin": [_r(o[j] / k + 8, 3) for j in range(3)],
                              "x": _r(c.get("rx", 0.0), 3), "y": _r(c.get("ry", 0.0), 3), "z": _r(c.get("rz", 0.0), 3)}
        els.append(el)
    return {"textures": {"0": TEXTURE_ID, "particle": TEXTURE_ID}, "elements": els}


def _corners(c):
    """The eight corners of a part, its one rotation applied (right-handed, degrees, about
    its origin; Blockbench's and the game's convention for a single-axis element)."""
    fx, fy, fz = c["from"]
    sx, sy, sz = c["size"]
    pts = [(fx + a, fy + b, fz + e) for a in (0, sx) for b in (0, sy) for e in (0, sz)]
    o = c.get("origin")
    if c.get("ry"):
        a = math.radians(c["ry"])
        pts = [(o[0] + (p[0] - o[0]) * math.cos(a) + (p[2] - o[2]) * math.sin(a), p[1],
                o[2] - (p[0] - o[0]) * math.sin(a) + (p[2] - o[2]) * math.cos(a)) for p in pts]
    if c.get("rx"):
        a = math.radians(c["rx"])
        pts = [(p[0], o[1] + (p[1] - o[1]) * math.cos(a) - (p[2] - o[2]) * math.sin(a),
                o[2] + (p[1] - o[1]) * math.sin(a) + (p[2] - o[2]) * math.cos(a)) for p in pts]
    if c.get("rz"):
        a = math.radians(c["rz"])
        pts = [(o[0] + (p[0] - o[0]) * math.cos(a) - (p[1] - o[1]) * math.sin(a),
                o[1] + (p[0] - o[0]) * math.sin(a) + (p[1] - o[1]) * math.cos(a), p[2]) for p in pts]
    return pts


def footprint(name):
    """(x0, z0, x1, z1) in blocks around the entity position: where a decal under it fits."""
    parts, _, _ = parts_of(name)
    pts = [p for c in parts for p in _corners(c)]
    xs, zs = [p[0] for p in pts], [p[2] for p in pts]
    return tuple(round(v / 16.0, 3) for v in (min(xs), min(zs), max(xs), max(zs)))


# where each prop sits in the Blockbench project (px): bodies in a row, then the big ones,
# then the debris
GRID = {"dead_villager_a": (-88, 0), "dead_villager_b": (-44, 0), "dead_villager_c": (0, 0),
        "dead_villager_head": (44, 0), "dead_villager_arm": (88, 0),
        "crucified_villager": (-60, 70), "dead_iron_golem": (20, 70),
        "dead_grass_a": (-54, 130), "dead_grass_b": (-38, 130),
        "broken_wood_a": (10, 130), "broken_wood_b": (50, 130), "broken_wood_c": (95, 130)}


def bbmodel(placed):
    """Every prop in one Blockbench project, each in its own group on a grid (GRID), with a
    blood pool under each body (preview only: those planes are not exported)."""
    from export_bb import FORMAT_VERSION, _group, _uid
    import base64
    im = Image.open(TEXTURE)
    tex = [{"name": TEXTURE.name, "folder": "entity", "namespace": "sunman", "id": "0",
            "particle": True, "render_mode": "default", "render_sides": "auto",
            "frame_time": 1, "frame_order_type": "loop", "frame_order": "",
            "frame_interpolate": False, "visible": True, "internal": True, "saved": False,
            "uuid": _uid("props_tex", TEXTURE.name), "mode": "bitmap", "width": im.width,
            "height": im.height, "uv_width": im.width, "uv_height": im.height,
            "source": "data:image/png;base64," + base64.b64encode(TEXTURE.read_bytes()).decode()}]
    px0, py0 = placed["_pool"]["box"][:2]
    elements, outliner = [], []
    for k, name in enumerate(PROPS):
        ox, oz = GRID[name]
        g = _group("props", name, (ox, 0, oz))
        parts, _, _ = parts_of(name)
        for i, c in enumerate(parts):
            frm = [c["from"][0] + ox, c["from"][1], c["from"][2] + oz]
            to = [frm[j] + c["size"][j] for j in range(3)]
            o = c.get("origin", c["from"])
            e = {"name": f"{name}_{c['paint']}_{i}", "box_uv": False, "type": "cube",
                 "uuid": _uid("props", name, i), "from": [_r(v) for v in frm], "to": [_r(v) for v in to],
                 "origin": [_r(o[0] + ox), _r(o[1]), _r(o[2] + oz)],
                 "faces": {d: {"uv": [_r(v, 3) for v in rect], "texture": 0}
                           for d, rect in placed[(name, i)]["faces"].items()}}
            if any(c.get(a) for a in ("rx", "ry", "rz")):
                e["rotation"] = [_r(c.get("rx", 0.0), 3), _r(c.get("ry", 0.0), 3), _r(c.get("rz", 0.0), 3)]
            elements.append(e)
            g["children"].append(e["uuid"])
        if name.startswith("dead_villager_") and name[-1] in "abc":
            # the pool under it, as the datapack lays one
            e = {"name": f"{name}_blood_preview", "box_uv": False, "type": "cube", "export": False,
                 "uuid": _uid("props", name, "blood"), "from": [ox - 16, 0.02, oz - 14], "to": [ox + 16, 0.03, oz + 18],
                 "origin": [ox, 0, 0],
                 "faces": {"up": {"uv": [px0, py0, px0 + 64, py0 + 64], "texture": 0},
                           "down": {"uv": [px0, py0 + 64, px0 + 64, py0], "texture": 0}}}
            elements.append(e)
            g["children"].append(e["uuid"])
        outliner.append(g)
    return {"meta": {"format_version": FORMAT_VERSION, "model_format": "bedrock", "box_uv": False},
            "name": "village_props", "model_identifier": "village_props",
            "visible_box": [12, 2, 0], "variable_placeholders": "", "variable_placeholder_buttons": [],
            "timeline_setups": [], "unhandled_root_fields": {},
            "resolution": {"width": SIZE, "height": SIZE},
            "elements": elements, "outliner": outliner, "textures": tex, "animations": []}


def build():
    placed = layout()
    used = paint(placed)
    for name in PROPS:
        mp = PACK / "models" / "item" / "prop" / f"{name}.json"
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(json.dumps(item_model(name, placed), indent=2) + "\n")
        (PACK / "items" / f"{name}.json").write_text(json.dumps(
            {"model": {"type": "minecraft:model", "model": f"sunman:item/prop/{name}"}}, indent=2) + "\n")
        parts, _, _ = parts_of(name)
        print(f"  {name:20} {len(parts):2d} parts  footprint {footprint(name)} blocks"
              f"{'  (shown at %dx)' % SCALE[name] if name in SCALE else ''}")
    old = ROOT / "blockbench" / "dead_villagers.bbmodel"
    if old.exists():
        old.unlink()
    old_tex = PACK / "textures" / "entity" / "dead_villagers.png"
    if old_tex.exists():
        old_tex.unlink()
    bb = ROOT / "blockbench" / "village_props.bbmodel"
    bb.write_text(json.dumps(bbmodel(placed)))
    print(f"  texture {TEXTURE.name} {SIZE}x{SIZE}, {used}% used  ->  {bb.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
