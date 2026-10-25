"""The Birthday People's skin: their own 512 x 512 texture, painted like the drawings.

Same method as `paint_tiers.py` (and its machinery): 32 texels to the block, a box unwrap
per cube packed with MaxRects, right-side limbs mirroring their left twin, every texel painted
in WORLD space so strokes and ribs run across the seams. The two variants share every cube
they have in common, so only the crown and the tree add texels.

The references are pencil, so the paint is pencil: the black column is laid down in vertical
graphite strokes that thin out where it frays onto the shoulders, the pale body is shaded
with soft grey, and the ribs are a washboard of lit bars over shadows gone red (the frame
behind the railing shows the bodies red-ribbed). The face is drawn by hand, texel by texel.

It has its own file, `textures/entity/birthday_people.png`, so the Sun Man atlas and its
hashed face are never touched.

    python3 tools/paint_birthday.py
"""
import math
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import birthday                                                         # noqa: E402
from paint_tiers import (DIRS, Face, MaxRects, _dims, _dither, _h, _rnd,  # noqa: E402
                         _shade_side, _unwrap, fbm, twin, vnoise)

ROOT = Path(__file__).resolve().parent.parent
TEXTURE = ROOT / "resourcepack" / "assets" / "sunman" / "textures" / "entity" / "birthday_people.png"
SIZE = 512
TEXELS = 2

RAMPS = {
    "bp_skin":   [(222, 208, 200), (203, 187, 180), (181, 163, 157), (153, 134, 130), (119, 101, 99), (82, 68, 68)],
    "bp_bone":   [(230, 219, 211), (211, 198, 190), (189, 174, 167), (160, 144, 139), (125, 110, 106), (88, 76, 74)],
    "bp_dark":   [(96, 94, 98), (68, 66, 70), (47, 46, 49), (32, 31, 34), (20, 19, 21), (9, 9, 10)],
    "bp_face":   [(240, 233, 223), (222, 213, 203), (198, 187, 177), (168, 155, 147), (128, 115, 109), (72, 63, 61)],
    "bp_hand":   [(88, 84, 84), (62, 58, 59), (42, 40, 41), (28, 27, 28), (17, 16, 17), (7, 7, 8)],
    "bp_bark":   [(98, 88, 80), (72, 64, 58), (52, 46, 42), (36, 32, 30), (22, 20, 19), (11, 10, 10)],
    "bp_string": [(218, 62, 54), (188, 42, 40), (156, 30, 30), (120, 21, 23), (86, 14, 16), (54, 8, 10)],
}
RIB_RED = (150, 62, 60)                  # the shadows between the ribs, gone red
VOID = (8, 7, 8)

# The face, 6 x 8 texels: a pale window under the black brow, two small dark eyes, the nose its
# own cube in the middle, a moustache over a small dark mouth, and the beard below it.
# ' highlight  , light  . pale  - shade  = dark shade  # void
FACE = [
    "=-..-=",
    "-,'',-",
    "-#,,#-",
    "==..==",
    "-.,,.-",
    "=-''-=",
    "==--==",
    "==##==",
]
TONE = {"'": 0, ",": 1, ".": 2, "-": 3, "=": 4}


# ====================================================================== layout

def layout():
    """Face UVs for every cube of both variants, in 512-px texture space, keyed
    (creature, bone, index). A cube the crown and the tree share gets one set of texels."""
    items, seen = [], {}
    for cname, c in birthday.PEOPLE.items():
        for bone in c.BONE_ORDER:
            if twin(bone) in c.CUBES_PX:
                continue
            for i, cube in enumerate(c.CUBES_PX.get(bone, [])):
                sig = (bone, i, repr(sorted(cube.items())))
                if sig in seen:
                    continue
                seen[sig] = (cname, bone, i)
                off, (fw, fh) = _unwrap(cube["size"])
                items.append((cname, bone, i, cube, off, fw, fh))
    items.sort(key=lambda it: (-max(it[5], it[6]), -it[5] * it[6], it[0], it[1], it[2]))
    packer = MaxRects(0, 0, SIZE, SIZE)
    placed = {}
    for cname, bone, i, cube, off, fw, fh in items:
        at = packer.insert(fw + 1, fh + 1)
        assert at is not None, "the Birthday People no longer fit their texture"
        x, y = at
        dims = _dims(cube["size"])
        faces = {}
        for d in DIRS:
            ox, oy = off[d]
            fw_, fh_ = dims[d]
            faces[d] = (x + ox, y + oy, x + ox + fw_ * TEXELS, y + oy + fh_ * TEXELS)
        placed[(cname, bone, i)] = {"faces": faces, "cube": cube, "box": (x, y, x + fw, y + fh)}
    for cname, c in birthday.PEOPLE.items():
        for bone in c.BONE_ORDER:
            for i, cube in enumerate(c.CUBES_PX.get(bone, [])):
                if (cname, bone, i) in placed:
                    continue
                src = twin(bone)
                if src in c.CUBES_PX:
                    f = _find(placed, seen, src, i, c.CUBES_PX[src][i])["faces"]
                    swap = {"east": "west", "west": "east"}
                    faces = {d: (f[swap.get(d, d)][2], f[swap.get(d, d)][1],
                                 f[swap.get(d, d)][0], f[swap.get(d, d)][3]) for d in DIRS}
                    placed[(cname, bone, i)] = {"faces": faces, "cube": cube, "mirror_of": src}
                else:
                    shared = _find(placed, seen, bone, i, cube)
                    placed[(cname, bone, i)] = {"faces": shared["faces"], "cube": cube, "shared": True}
    return placed


def _find(placed, seen, bone, i, cube):
    return placed[seen[(bone, i, repr(sorted(cube.items())))]]


# ====================================================================== styles

def paint_texel(f, tx, ty, R):
    st, mat = f.cube.get("paint") or "plain", f.cube["mat"]
    x, y, z = f.world(tx, ty)
    n = fbm(x * 0.45, y * 0.45, z * 0.45, seed=_h(*map(ord, mat)) & 0xFF)
    g = vnoise(x * 2.1, y * 2.1, z * 2.1, seed=7)
    streak = vnoise(x * 1.6, y * 0.22, z * 1.6, seed=11)

    if st == "face" and f.d == "south":
        gw, gh = len(FACE[0]), len(FACE)
        ch = FACE[min(gh - 1, ty * gh // f.H)][min(gw - 1, tx * gw // f.W)]
        return VOID if ch == "#" else R[TONE[ch]]
    if st == "nose":
        if f.d == "south":
            return R[3] if ty == f.H - 1 else R[0 if ty < f.H - 2 else 1]
        return R[{"up": 0, "down": 5}.get(f.d, 3)]

    t = _shade_side(f, tx, ty)
    t += (n - 0.5) * 1.1 + (g - 0.5) * 0.15
    smooth = False

    if mat == "bp_dark":
        # graphite laid on in vertical strokes: each column of texels is one stroke, darker or
        # lighter, broken where the pencil lifted
        stroke = vnoise(x * 5.5 + z * 5.5, y * 0.35, 0.0, seed=71)
        lift = vnoise(x * 5.5 + z * 5.5, y * 1.6, 0.0, seed=73)
        t = 3.2 + (stroke - 0.5) * 3.0 + (n - 0.5) * 0.8
        if lift > 0.8:
            t -= 1.2
        if st == "column":
            # lighter low down, where the black thins out onto the shoulders
            t -= max(0.0, (birthday.NECK + 5.0 - y) / 5.0) * 1.0
            if f.d == "south" and 76.5 < y < 87.5 and abs(x) < 3.0:
                t += 0.9                                     # a shadow round the face
        if st in ("skirt", "strand"):
            t -= 0.8
            if f.d == "down":
                t = 3.0
        if st == "beard":
            t = 3.4 + (vnoise(x * 6, y * 0.6, z * 6, seed=79) - 0.5) * 2.6
        if st in ("spike", "ball"):
            # solid black, with one hard pencil highlight down the lit edge
            t = 4.0 + (stroke - 0.5) * 0.8
            if f.side and tx == 0:
                t = 1.4
            if st == "ball" and f.side and tx == 1 and ty == 1:
                t = 2.2
            if f.d == "up":
                t = 2.0
        if f.d == "up":
            t = 2.6 + (g - 0.5) * 1.2
        if f.d == "down":
            t = 4.6
    elif st == "ribcage":
        # ribs bow down to the flanks: the lit top of a rib, the rib, a shadow gone red
        bow = 0.22 * x * x
        row = int(math.floor((y + bow) * TEXELS)) % 4
        if f.side:
            t = 2.0 + (n - 0.5) * 0.6 + (-0.6, 0.3, 1.6, 2.4)[row]
            if f.d == "south" and abs(x) < 0.6:
                t = 2.0 + (n - 0.5) * 0.5
            if f.d == "north" and abs(x) < 0.5:
                t = 4.2
            if row >= 2 and f.d != "north":
                base = R[max(0, min(5, int(round(t))))]
                k = 0.35 if row == 2 else 0.5
                return tuple(int(b + (c - b) * k) for b, c in zip(base, RIB_RED))
    elif st == "rib":
        t = 0.6 if (f.d == "up" or (f.side and ty == 0)) else (2.0 if f.side else 4.0)
        t += (g - 0.5) * 0.6
    elif st == "belly":
        t += 0.4
        if f.side:
            if int(math.floor(y * TEXELS * 0.7 + vnoise(x, y, z, seed=5))) % 3 == 0:
                t += 0.8                                    # loose skin, creased across
            # the hollow in the belly: a dark slit, like a mouth, under the navel
            if f.d == "south":
                dx, dy = abs(x) / 0.9, abs(y - (birthday.HIP + 4.5)) / 2.0
                r = dx * dx + dy * dy
                if r < 1.0:
                    return VOID if r < 0.45 else R[5]
                if r < 1.6:
                    t += 1.2
    elif st == "fold":
        t = 0.8 if f.d == "up" else (4.0 if f.d == "down" else 2.0 + (ty / max(1, f.H - 1)) * 1.6)
    elif st in ("shoulders", "collar"):
        t += (streak - 0.5) * 0.6
        if st == "collar" and f.d == "south" and ty <= 1:
            t = 0.6                                         # the collarbones catch the light
        if st == "shoulders" and f.d == "south" and abs(x) < 0.5:
            t += 1.0
    elif st in ("limb", "shoulder", "heel", "foot", "pelvis", "groin", "hipbone"):
        t += (streak - 0.5) * 0.9
        if f.side and _rnd(round(x * TEXELS), math.floor(y * TEXELS / 3), round(z * TEXELS), 3) < 0.02:
            t += 1.4                                        # a scratch, a vein
        if st == "hipbone" and f.d == "up":
            t = 0.5
        if st in ("heel", "foot") and f.side and ty >= f.H - 1:
            t += 1.2
    elif st in ("joint", "knob", "sternum"):
        if f.side:
            mid = abs(ty + 0.5 - f.H / 2.0) < 0.6
            t += 1.4 if mid else (-0.7 if ty <= 1 else 0)
    elif st == "palm":
        t = 2.8 + (streak - 0.5) * 1.2
    elif st == "finger":
        t = 2.8 + (streak - 0.5) * 1.0
        if f.side and ty in (0, f.H - 1):
            t += 1.0                                        # the knuckle creases
        if f.side and tx == 0:
            t -= 1.0
    elif st == "nail":
        t = 3.6 if f.side else 4.5
        if f.side and tx == 0:
            t = 1.6
    elif st in ("bark", "twig"):
        # bark in long cracked ridges
        ridge = vnoise(x * 4.0 + z * 4.0, y * 0.3, 0.0, seed=83)
        t = 2.8 + (ridge - 0.5) * 3.2 + (n - 0.5) * 0.6
        if st == "twig":
            t = 3.0 if tx else 1.8
        if f.d in ("up", "down"):
            t = 3.4
    elif st == "string":
        twist = (y * TEXELS + (x + z) * TEXELS) % 3.0
        t = 1.4 + (1.2 if twist < 1.0 else 0.0) + (g - 0.5) * 0.6
        if not f.side:
            t = 2.4
    k = _dither(t, tx, ty) if smooth else int(round(t))
    return R[max(0, min(5, k))]


# ====================================================================== the run

def paint():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    px = im.load()
    placed = layout()
    painted = 0
    for (cname, bone, i), entry in placed.items():
        if "mirror_of" in entry or "shared" in entry:
            continue
        cube = entry["cube"]
        R = RAMPS[cube["mat"]]
        for d, rect in entry["faces"].items():
            f = Face(cube, d, rect, cname, bone, i)
            for ty in range(f.H):
                for tx in range(f.W):
                    X, Y = f.x0 + tx, f.y0 + ty
                    if 0 <= X < SIZE and 0 <= Y < SIZE:
                        px[X, Y] = paint_texel(f, tx, ty, R) + (255,)
        painted += 1
    TEXTURE.parent.mkdir(parents=True, exist_ok=True)
    im.save(TEXTURE, optimize=True)
    used = sum((e["box"][2] - e["box"][0]) * (e["box"][3] - e["box"][1])
               for e in placed.values() if "box" in e)
    print(f"painted {painted} unique cubes ({len(placed)} across both variants) into "
          f"{TEXTURE.name} at {TEXELS * 16} texels/block, {used * 100 // (SIZE * SIZE)}% of it")


if __name__ == "__main__":
    paint()
