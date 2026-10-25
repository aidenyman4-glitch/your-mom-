"""Dead villagers, built as Blockbench models: three sprawled bodies and two loose pieces.

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

Villager proportions (head 8 x 10 x 8, robe 8 x 18 x 6, legs 4 x 12 x 4, arms 4 x 10 x 4), on a
true pixel grid, 16 px to the block. Every part is a box lying on the ground with at most a
YAW (rotation about Y): a body on the ground never needs another axis, and a yaw-only element
renders identically in Blockbench and in the game whatever the Euler order.

The skin is the pack's own (`textures/entity/dead_villagers.png`, 32 texels to the block),
painted after the villager look — the brown robe, the big nose, the heavy brow — in the grey of
something that has been dead a day, with blood soaked into the cloth around every wound and
stumps that show the meat and the bone.

    python3 tools/props.py      ->  texture, item models + item definitions, blockbench/dead_villagers.bbmodel
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
TEXTURE = PACK / "textures" / "entity" / "dead_villagers.png"
SIZE = 256
TEXELS = 2

RAMPS = {
    "skin":  [(206, 172, 152), (188, 152, 132), (166, 130, 112), (142, 107, 92), (114, 84, 74), (82, 60, 54)],
    "robe":  [(134, 98, 68), (114, 82, 56), (96, 68, 46), (80, 56, 37), (62, 43, 29), (43, 29, 20)],
    "pants": [(110, 84, 62), (92, 70, 51), (76, 57, 41), (62, 46, 33), (47, 34, 25), (32, 23, 17)],
    "shoe":  [(98, 88, 80), (80, 71, 64), (64, 56, 50), (50, 43, 38), (37, 31, 27), (24, 20, 17)],
}
BLOOD = [(74, 7, 9), (98, 10, 12), (126, 15, 17), (154, 22, 22), (182, 28, 26), (210, 38, 34)]
MEAT = (150, 40, 44)
BONE = (226, 216, 196)
EYE = (212, 210, 198)
VOID = (16, 10, 10)


def box(frm, size, mat, paint, ry=0.0, origin=None, **extra):
    """A part in ground-relative pixels (y = 0 is the ground), with an optional yaw about
    `origin`. `extra` names special faces: face="up" puts the face on that side and
    top="south" says which way the top of the head points; stump=["north"] makes a face a
    torn stump."""
    c = {"from": tuple(float(v) for v in frm), "size": tuple(float(v) for v in size),
         "mat": mat, "paint": paint}
    if ry:
        c["ry"] = float(ry)
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


PROPS = {
    "dead_villager_a": corpse_a,
    "dead_villager_b": corpse_b,
    "dead_villager_c": corpse_c,
    "dead_villager_head": loose_head,
    "dead_villager_arm": loose_arm,
}


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


def paint_texel(f, tx, ty, cube, wounds):
    R = RAMPS[cube["mat"]]
    st = cube["paint"]
    x, y, z = f.world(tx, ty)
    n = fbm(x * 0.4, y * 0.4, z * 0.4, seed=_h(*map(ord, cube["mat"])) & 0xFF)
    g = vnoise(x * 2.0, y * 2.0, z * 2.0, seed=7)
    d = f.d

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

    k = int(round(t))
    col = R[max(0, min(5, k))]
    # soaked in around each wound, patchy: the cloth shows through where it did not take
    b = _wound_blood(x, y, z, wounds, seed=51) - 0.3 * vnoise(x * 1.3, y * 1.3, z * 1.3, seed=53)
    if b > 0.05:
        tone = 1 + int(4 * b ** 0.8) if cube["mat"] != "skin" else 2 + int(3 * b)
        col = BLOOD[max(0, min(5, tone - (1 if _rnd(tx, ty, 11) < 0.3 else 0)))]
    return col


# ====================================================================== layout + export

def layout():
    items = []
    for name, fn in PROPS.items():
        parts, _ = fn()
        for i, c in enumerate(parts):
            off, (fw, fh) = _unwrap(c["size"])
            items.append((name, i, c, off, fw, fh))
    items.sort(key=lambda it: (-max(it[4], it[5]), -it[4] * it[5], it[0], it[1]))
    packer = MaxRects(0, 0, SIZE, SIZE)
    placed = {"_pool": {"box": packer.insert(64, 64) + (64, 64)}}
    for name, i, c, off, fw, fh in items:
        at = packer.insert(fw + 1, fh + 1)
        assert at is not None, "the dead villagers no longer fit their texture"
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
    for name, fn in PROPS.items():
        parts, wounds = fn()
        for i, c in enumerate(parts):
            for d, rect in placed[(name, i)]["faces"].items():
                f = Face(c, d, rect, name, "body", i)
                for ty in range(f.H):
                    for tx in range(f.W):
                        px[f.x0 + tx, f.y0 + ty] = paint_texel(f, tx, ty, c, wounds) + (255,)
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
    datapack puts on the ground, so ground-relative y = 0 lands at model y = 8."""
    parts, _ = PROPS[name]()
    els = []
    for i, c in enumerate(parts):
        frm = [c["from"][0] + 8, c["from"][1] + 8, c["from"][2] + 8]
        to = [frm[k] + c["size"][k] for k in range(3)]
        faces = {d: {"uv": [_r(v * 16.0 / SIZE) for v in rect], "texture": "#0"}
                 for d, rect in placed[(name, i)]["faces"].items()}
        el = {"from": [_r(v, 3) for v in frm], "to": [_r(v, 3) for v in to], "faces": faces}
        if c.get("ry"):
            o = c["origin"]
            el["rotation"] = {"origin": [_r(o[0] + 8, 3), _r(o[1] + 8, 3), _r(o[2] + 8, 3)],
                              "x": 0.0, "y": _r(c["ry"], 3), "z": 0.0}
        els.append(el)
    return {"textures": {"0": "sunman:entity/dead_villagers", "particle": "sunman:entity/dead_villagers"},
            "elements": els}


def _corners(c):
    fx, fy, fz = c["from"]
    sx, sy, sz = c["size"]
    pts = [(fx + a, fy + b, fz + e) for a in (0, sx) for b in (0, sy) for e in (0, sz)]
    if c.get("ry"):
        a = math.radians(c["ry"])
        ox, _, oz = c["origin"]
        # Blockbench / Minecraft yaw: positive turns +X toward -Z (counter-clockwise from above)
        pts = [(ox + (p[0] - ox) * math.cos(a) + (p[2] - oz) * math.sin(a), p[1],
                oz - (p[0] - ox) * math.sin(a) + (p[2] - oz) * math.cos(a)) for p in pts]
    return pts


def footprint(name):
    """(x0, z0, x1, z1) in blocks around the entity position: where a decal under it fits."""
    parts, _ = PROPS[name]()
    pts = [p for c in parts for p in _corners(c)]
    xs, zs = [p[0] for p in pts], [p[2] for p in pts]
    return tuple(round(v / 16.0, 3) for v in (min(xs), min(zs), max(xs), max(zs)))


def bbmodel(placed):
    """All five props side by side in one Blockbench project, each in its own group, with a
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
        ox = (k - 2) * 44.0
        g = _group("props", name, (ox, 0, 0))
        parts, _ = PROPS[name]()
        for i, c in enumerate(parts):
            frm = [c["from"][0] + ox, c["from"][1], c["from"][2]]
            to = [frm[j] + c["size"][j] for j in range(3)]
            o = c.get("origin", c["from"])
            e = {"name": f"{name}_{c['paint']}_{i}", "box_uv": False, "type": "cube",
                 "uuid": _uid("props", name, i), "from": [_r(v) for v in frm], "to": [_r(v) for v in to],
                 "origin": [_r(o[0] + ox), _r(o[1]), _r(o[2])],
                 "faces": {d: {"uv": [_r(v, 3) for v in rect], "texture": 0}
                           for d, rect in placed[(name, i)]["faces"].items()}}
            if c.get("ry"):
                e["rotation"] = [0.0, _r(c["ry"], 3), 0.0]
            elements.append(e)
            g["children"].append(e["uuid"])
        if name.startswith("dead_villager_") and name[-1] in "abc":
            # the pool under it, as the datapack lays one
            e = {"name": f"{name}_blood_preview", "box_uv": False, "type": "cube", "export": False,
                 "uuid": _uid("props", name, "blood"), "from": [ox - 16, 0.02, -14], "to": [ox + 16, 0.03, 18],
                 "origin": [ox, 0, 0],
                 "faces": {"up": {"uv": [px0, py0, px0 + 64, py0 + 64], "texture": 0},
                           "down": {"uv": [px0, py0 + 64, px0 + 64, py0], "texture": 0}}}
            elements.append(e)
            g["children"].append(e["uuid"])
        outliner.append(g)
    return {"meta": {"format_version": FORMAT_VERSION, "model_format": "bedrock", "box_uv": False},
            "name": "dead_villagers", "model_identifier": "dead_villagers",
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
        parts, _ = PROPS[name]()
        print(f"  {name:20} {len(parts):2d} parts  footprint {footprint(name)} blocks")
    bb = ROOT / "blockbench" / "dead_villagers.bbmodel"
    bb.write_text(json.dumps(bbmodel(placed)))
    print(f"  texture {TEXTURE.name} {SIZE}x{SIZE}, {used}% used  ->  {bb.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
