"""Pixel-art skins for the two tier creatures, painted into the atlas's free quadrant.

Thirty-two texels to the block — two per model pixel — so a two-pixel limb has four texels
across it: room for a highlight, a body and a shadow, which is what turns a grey stick into a
bone. Every cube gets its own box-style unwrap,

            [ up   ][ down ]
    [ west ][ south ][ east ][ north ]

so the four sides of a limb sit in one continuous strip and stay hand-paintable in
Blockbench, and the right side of a creature shares its left side's texels, mirrored, the way
a mob texture is laid out. MaxRects packs the unwraps.

Painting happens in WORLD space: every texel knows the point on the model it lands on, so
noise, ribs, string bindings and the crease in a hat brim run straight across the seams
between faces and between cubes instead of restarting on each one. The two things a player
looks at — the Locust's mask and the Dark Walker's face — are drawn by hand, a texel at a time.

The one hard contract is unchanged: only the free quadrant (x 0..256, y 256..512) is written,
and the starburst face beside it is hashed before and after; nothing is written if it moved.

    python3 tools/paint_tiers.py
"""
import hashlib
import math
import re
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tiers                              # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ATLAS = ROOT / "resourcepack" / "assets" / "sunman" / "textures" / "entity" / "sun_man.png"
FREE = (0, 256, 256, 512)                 # x0, y0, x1, y1 — the only pixels this may touch
FACE_HASH = "394858d53b822f85e30a8657ef4310e15fb496916295d27e9463b4f2bad2906c"
TEXELS = 2                                # texels per model pixel: 32 per block
DIRS = ("north", "south", "east", "west", "up", "down")
SIDES = ("north", "south", "east", "west")

# six-step ramps, highlight to deepest shadow
RAMPS = {
    # Locust: a puppet. Porcelain, black hair, charcoal ribs, pale bound limbs, black needles.
    "lc_mask":   [(246, 240, 228), (232, 222, 206), (214, 202, 186), (190, 176, 160), (158, 142, 128), (112, 98, 90)],
    "lc_hair":   [(74, 76, 90), (48, 50, 61), (31, 32, 40), (20, 20, 25), (11, 11, 14), (5, 5, 7)],
    "lc_skin":   [(96, 89, 93), (70, 65, 69), (52, 48, 52), (37, 34, 37), (24, 22, 25), (12, 11, 13)],
    "lc_flesh":  [(216, 198, 190), (196, 177, 169), (174, 154, 147), (148, 128, 122), (116, 98, 95), (80, 66, 65)],
    "lc_bone":   [(214, 200, 192), (192, 176, 168), (168, 152, 145), (142, 126, 120), (110, 96, 92), (74, 64, 62)],
    "lc_wrap":   [(80, 66, 58), (56, 46, 41), (38, 31, 28), (25, 20, 19), (14, 11, 11), (7, 5, 5)],
    "lc_rag":    [(70, 62, 62), (50, 44, 45), (35, 30, 32), (24, 21, 23), (14, 12, 14), (7, 6, 7)],
    "lc_needle": [(132, 134, 142), (84, 86, 94), (50, 51, 57), (30, 30, 35), (17, 17, 20), (8, 8, 10)],
    # Dark Walker: cold grey, a black felt hat, pale knuckles, bone-to-black claws, lit eyes.
    "dw_skin":   [(150, 153, 162), (124, 127, 137), (100, 103, 113), (78, 81, 90), (58, 60, 68), (40, 41, 48)],
    "dw_dark":   [(114, 116, 125), (92, 94, 103), (74, 76, 84), (56, 58, 65), (40, 41, 47), (26, 27, 31)],
    "dw_pale":   [(198, 200, 207), (172, 175, 183), (148, 151, 160), (122, 125, 134), (96, 99, 107), (68, 70, 77)],
    "dw_hat":    [(66, 66, 74), (47, 47, 53), (33, 33, 38), (23, 23, 27), (15, 15, 18), (8, 8, 10)],
    "dw_band":   [(116, 101, 88), (92, 80, 70), (72, 62, 54), (54, 46, 41), (38, 32, 29), (22, 19, 17)],
    "dw_claw":   [(140, 134, 124), (104, 100, 93), (74, 71, 67), (49, 47, 45), (30, 29, 28), (15, 15, 15)],
    "dw_eye":    [(255, 255, 248), (255, 251, 228), (255, 241, 188), (247, 214, 138), (214, 172, 92), (170, 120, 50)],
}
VOID = (5, 4, 5)
STAIN = (92, 54, 50)                      # old blood, gone brown
MOUTH = (58, 12, 15)
EMISSIVE = {"dw_eye"}
BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


# ====================================================================== noise

def _h(*a):
    h = 2166136261
    for v in a:
        h = ((h ^ (int(v) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
        h ^= h >> 13
    return h


def _rnd(*a):
    return _h(*a) / 0xFFFFFFFF


def vnoise(x, y, z, seed=0):
    """3D value noise in [0, 1]."""
    xi, yi, zi = math.floor(x), math.floor(y), math.floor(z)
    xf, yf, zf = x - xi, y - yi, z - zi
    u, v, w = (t * t * (3 - 2 * t) for t in (xf, yf, zf))
    acc = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                g = _rnd(xi + dx, yi + dy, zi + dz, seed)
                acc += g * (u if dx else 1 - u) * (v if dy else 1 - v) * (w if dz else 1 - w)
    return acc


def fbm(x, y, z, seed=0, octaves=3):
    amp, tot, norm = 1.0, 0.0, 0.0
    for o in range(octaves):
        tot += amp * vnoise(x, y, z, seed + o * 31)
        norm += amp
        x, y, z, amp = x * 2.03, y * 2.03, z * 2.03, amp * 0.5
    return tot / norm


# ====================================================================== layout

def _texels(v):
    return max(1, int(math.ceil(v * TEXELS - 1e-6)))


def _dims(size):
    w, h, d = size
    return {"north": (w, h), "south": (w, h), "east": (d, h), "west": (d, h),
            "up": (w, d), "down": (w, d)}


def _unwrap(size):
    w, h, d = (_texels(v) for v in size)
    off = {"up": (d, 0), "down": (d + w, 0),
           "west": (0, d), "south": (d, d), "east": (d + w, d), "north": (2 * d + w, d)}
    return off, (2 * d + 2 * w, d + h)


def twin(bone):
    """The left-side bone a right-side bone mirrors, or None."""
    m = re.match(r"^(.*)_r(\d*)$", bone)
    return f"{m.group(1)}_l{m.group(2)}" if m else None


class MaxRects:
    """MaxRects bin packing, best-short-side-fit, with free-rectangle pruning."""

    def __init__(self, x, y, w, h):
        self.free = [(x, y, w, h)]

    def insert(self, w, h):
        best, score = None, None
        for fx, fy, fw, fh in self.free:
            if w <= fw and h <= fh:
                s = (min(fw - w, fh - h), max(fw - w, fh - h), fy, fx)
                if score is None or s < score:
                    best, score = (fx, fy), s
        if best is None:
            return None
        self._split(best[0], best[1], w, h)
        return best

    def _split(self, x, y, w, h):
        out = []
        for fx, fy, fw, fh in self.free:
            if x >= fx + fw or x + w <= fx or y >= fy + fh or y + h <= fy:
                out.append((fx, fy, fw, fh))
                continue
            if x > fx:
                out.append((fx, fy, x - fx, fh))
            if x + w < fx + fw:
                out.append((x + w, fy, fx + fw - x - w, fh))
            if y > fy:
                out.append((fx, fy, fw, y - fy))
            if y + h < fy + fh:
                out.append((fx, y + h, fw, fy + fh - y - h))
        self.free = [r for i, r in enumerate(out)
                     if not any(j != i and _inside(r, o) for j, o in enumerate(out))]


def _inside(a, b):
    return (a[0] >= b[0] and a[1] >= b[1] and a[0] + a[2] <= b[0] + b[2]
            and a[1] + a[3] <= b[1] + b[3] and a != b)


def layout():
    """Every tier cube's face UVs, in 512-px atlas space. Deterministic: the exporters and
    the painter all call this and agree without a file between them. Right-side bones point
    at their left twin's texels, mirrored (east and west swap, u runs backwards)."""
    items = []
    for cname, c in tiers.TIERS.items():
        for bone in c.BONE_ORDER:
            if twin(bone) in c.CUBES_PX:
                continue
            for i, cube in enumerate(c.CUBES_PX.get(bone, [])):
                off, (fw, fh) = _unwrap(cube["size"])
                items.append((cname, bone, i, cube, off, fw, fh))
    items.sort(key=lambda it: (-max(it[5], it[6]), -it[5] * it[6], it[0], it[1], it[2]))
    x0, y0, x1, y1 = FREE
    packer = MaxRects(x0, y0, x1 - x0, y1 - y0)
    placed = {}
    for cname, bone, i, cube, off, fw, fh in items:
        at = packer.insert(fw + 1, fh + 1)                  # one texel of gutter
        assert at is not None, "tier skins no longer fit the free quadrant"
        x, y = at
        dims = _dims(cube["size"])
        faces = {}
        for d in DIRS:
            ox, oy = off[d]
            fw_, fh_ = dims[d]
            faces[d] = (x + ox, y + oy, x + ox + fw_ * TEXELS, y + oy + fh_ * TEXELS)
        placed[(cname, bone, i)] = {"faces": faces, "cube": cube, "box": (x, y, x + fw, y + fh)}
    for cname, c in tiers.TIERS.items():
        for bone in c.BONE_ORDER:
            src = twin(bone)
            if src not in c.CUBES_PX:
                continue
            for i, cube in enumerate(c.CUBES_PX.get(bone, [])):
                f = placed[(cname, src, i)]["faces"]
                swap = {"east": "west", "west": "east"}
                faces = {d: (f[swap.get(d, d)][2], f[swap.get(d, d)][1],
                             f[swap.get(d, d)][0], f[swap.get(d, d)][3]) for d in DIRS}
                placed[(cname, bone, i)] = {"faces": faces, "cube": cube, "mirror_of": src}
    return placed


# ====================================================================== the face grid

class Face:
    """One face of one cube, and where each of its texels lands on the model."""

    def __init__(self, cube, d, rect, cname, bone, index):
        self.cube, self.d, self.cname, self.bone, self.index = cube, d, cname, bone, index
        u0, v0, u1, v1 = rect
        self.x0, self.y0 = int(min(u0, u1)), int(min(v0, v1))
        self.W = max(1, int(round(abs(u1 - u0))))
        self.H = max(1, int(round(abs(v1 - v0))))
        self.side = d in SIDES
        self.key = f"{cname}:{bone}:{index}:{d}"

    def world(self, tx, ty):
        (fx, fy, fz), (sx, sy, sz) = self.cube["from"], self.cube["size"]
        a, b = (tx + 0.5) / TEXELS, (ty + 0.5) / TEXELS
        d = self.d
        if d == "south":
            return fx + a, fy + sy - b, fz + sz
        if d == "north":
            return fx + sx - a, fy + sy - b, fz
        if d == "east":
            return fx + sx, fy + sy - b, fz + sz - a
        if d == "west":
            return fx, fy + sy - b, fz + a
        if d == "up":
            return fx + a, fy + sy, fz + b
        return fx + a, fy, fz + sz - b


def _dither(tone, tx, ty):
    lo = math.floor(tone)
    frac = tone - lo
    return lo + (1 if frac * 16 > BAYER[ty % 4][tx % 4] + 0.5 else 0)


def _shade_side(f, tx, ty, base=2.0, round_=True, ao=True):
    """Light from above and the left: a rim highlight on the leading column, a shadow on the
    trailing one, a lit top row and a dark contact row at the bottom."""
    t = base
    if f.side and round_ and f.W >= 3:
        u = (tx + 0.5) / f.W
        t += -0.9 * math.exp(-((u - 0.2) / 0.16) ** 2) + 1.0 * max(0.0, (u - 0.72) / 0.28) ** 1.4
    elif f.side and round_ and f.W == 2:
        t += -0.4 if tx == 0 else 0.6
    if f.side and ao:
        if ty == 0 and f.H >= 4:
            t -= 0.6
        if ty >= f.H - 1 and f.H >= 3:
            t += 0.7
    if f.d == "up":
        t -= 0.6
    elif f.d == "down":
        t += 1.2
    return t


# ====================================================================== the hand-drawn faces

# The Locust's mask, 6 x 11 texels: long, pale, a heavy brow over two black holes that run
# down into tears, the nose its own cube in the middle, and a mouth hanging open.
# ' highlight  , light  . porcelain  - shade  = dark shade  # void  r inside the mouth  x tear
LOCUST_MASK = [
    "-,'',-",
    ",'''',",
    ".,'',.",
    "=-,,-=",
    "-#,,#-",
    "=#..#=",
    "-x..x-",
    "=-..-=",
    "-=##=-",
    "-.r#.-",
    "=-..-=",
]
# The Dark Walker's face, 10 x 14 texels. No mouth in any reference — so it has none, only a
# seam where one was sewn shut. Sockets sunk deep round the lit eyes, hollow cheeks.
WALKER_FACE = [
    "=-==--==-=",
    "--------=-",
    "-.,,..,,.-",
    "-,.,,,,.,-",
    "=--.,,.--=",
    "==-=..=-==",
    "=###..###=",
    "#  #..#  #",
    "=###.,###=",
    "-=##.'.##=",
    "-.,-.,.-,.",
    "=-=-,.-=-=",
    "-.x=x=x=.-",
    "==-=.,=-==",
]
TONE_CHAR = {"'": 0, ",": 1, ".": 2, "-": 3, "=": 4, "x": 5}


def _from_map(grid, f, tx, ty, R):
    gw, gh = len(grid[0]), len(grid)
    ch = grid[min(gh - 1, ty * gh // f.H)][min(gw - 1, tx * gw // f.W)]
    if ch == "#":
        return VOID
    if ch == "r":
        return MOUTH
    if ch == " ":
        return R[5]                                       # behind the lit eye cubes
    return R[TONE_CHAR[ch]]


# ====================================================================== styles

def paint_texel(f, tx, ty, R):
    """Colour of one texel. Returns an RGB tuple."""
    st, mat = f.cube.get("paint") or "plain", f.cube["mat"]
    x, y, z = f.world(tx, ty)
    n = fbm(x * 0.55, y * 0.55, z * 0.55, seed=_h(*map(ord, mat)) & 0xFF)  # broad mottling
    g = vnoise(x * 2.1, y * 2.1, z * 2.1, seed=7)                          # fine grain
    streak = vnoise(x * 1.6, y * 0.25, z * 1.6, seed=11)                   # grain along limbs

    if st == "mask" and f.d == "south":
        return _from_map(LOCUST_MASK, f, tx, ty, R)
    if st == "face" and f.d == "south":
        return _from_map(WALKER_FACE, f, tx, ty, R)
    if st == "eye":
        return R[0] if (tx + ty) % 3 else R[1]
    if st == "nose":
        # lit down the ridge, shaded under, a dark nostril at the bottom of the front
        if f.d == "south":
            return R[4] if ty == f.H - 1 else R[0 if ty < f.H - 2 else 1]
        return R[{"up": 0, "down": 5}.get(f.d, 3)]

    t = _shade_side(f, tx, ty)
    t += (n - 0.5) * 1.3 + (g - 0.5) * 0.15
    smooth = False                                           # styles that want a dithered ramp

    if st in ("bone", "limb", "segment", "thigh"):
        t += (streak - 0.5) * 0.9
        # scratches: short dark gouges, three texels long, running with the grain
        if f.side and _rnd(round(x * TEXELS), math.floor(y * TEXELS / 3), round(z * TEXELS), 3) < 0.03:
            t += 1.5
        # veins, the Dark Walker's: thin dark threads that wander down the limb
        if f.cube["mat"] == "dw_skin" and f.side:
            v = vnoise(x * 0.9 + z * 0.9, y * 0.22, 0.0, seed=17)
            if abs(v - 0.5) < 0.035:
                t += 1.3
        # the Locust's limbs are old pale wood: fine grain, and stains that went brown
        if f.cube["mat"] == "lc_bone" and f.side:
            v = vnoise(x * 3.5 + z * 3.5, y * 0.15, 0.0, seed=19)
            if abs(v - 0.5) < 0.05:
                t += 0.9
            stain = fbm(x * 0.32, y * 0.32, z * 0.32, seed=51)
            if stain > 0.66:
                k = min(1.0, (stain - 0.66) * 6.0)
                base = R[max(0, min(5, int(round(t))))]
                return tuple(int(b + (c - b) * k * 0.8) for b, c in zip(base, STAIN))
        # grime gathers where the segment meets its binding
        if f.side and (ty == 0 or ty >= f.H - 1):
            t += 0.6
    elif st == "wrap":
        # string wound round and round: diagonal turns that climb as they go
        turn = (y * TEXELS * 1.0 + (x + z) * TEXELS * 0.45) % 2.0
        t = 2.2 + (1.4 if turn < 0.9 else -0.2) + (g - 0.5) * 0.8
        if f.d == "up" or f.d == "down":
            t = 3.0 + (g - 0.5)
        if _rnd(round(x * 4), round(y * 4), round(z * 4), 9) < 0.03:
            t = 0.5                                          # a frayed fibre catching light
    elif st in ("ribcage", "ribs", "chest"):
        # ribs bow downward toward the flanks, three texels each: the lit top of the bone,
        # the bone, the gap; the sternum and the spine break them
        bow = 0.3 * (x * x) / 4.0
        row = int(math.floor((y + bow) * TEXELS)) % 3
        if f.side:
            t = 2.0 + (n - 0.5) * 0.6 + (-0.9, 0.2, 1.9)[row]
            if f.d == "south" and abs(x) < 0.3:
                t = 2.2 + (n - 0.5) * 0.6                    # sternum
            if f.d == "north" and abs(x) < 0.4:
                t = 4.3                                      # the groove of the spine
            if st == "chest" and f.d == "south" and abs(x) < 0.3:
                return R[5] if int(y * TEXELS) % 2 == 0 else R[1]   # stitched closed
    elif st == "waist":
        if f.side:
            t += 0.8 if int(y * TEXELS) % 3 == 0 else 0
            if f.d == "north" and abs(x) < 0.4:
                t = 4.4
    elif st == "neck":
        t += (streak - 0.5) * 1.6                            # cords of tendon
        if int(y * TEXELS) % 5 == 0:
            t += 0.7                                         # creases
    elif st in ("hair", "strand"):
        # hair falls in strands: tone runs down the length, varies across it
        k = vnoise(x * 3.2 + z * 3.2, y * 0.35, 0, seed=21)
        t = 2.6 + (k - 0.5) * 3.2
        if k > 0.78:
            t = 1.0                                          # a sheen on one strand
        if f.d == "up":
            t = 2.4 + (vnoise(x * 2.5, z * 2.5, 0, seed=23) - 0.5) * 2.6
        if f.d == "down":
            t = 4.4
        if st == "strand" and f.side:
            t = 1.6 if tx == 0 else 3.4
    elif st == "rag":
        # black cloth gone to threads: vertical weave, holes, a ragged lower edge
        t += (vnoise(x * 5, y * 0.5, z * 5, seed=31) - 0.5) * 1.8
        if _rnd(round(x * TEXELS), round(y * TEXELS), round(z * TEXELS), 33) < 0.05:
            return R[5]
        if f.side and ty >= f.H - 2 and (tx * 7 + ty) % 3 == 0:
            t = 0.8
    elif st == "blade":
        # black and oiled: one cold edge down the front, nicks along it, dull flats
        t = 3.6 + (streak - 0.5) * 0.8
        if f.side and tx == 0:
            t = 1.2 if _rnd(tx, ty, f.index, 61) > 0.12 else 3.4
        if f.d == "up":
            t = 2.0
    elif st == "ball":
        # a doll's ball joint: pale, a dark hole bored through the middle of each side
        t += (streak - 0.5) * 0.5
        if f.side and abs(tx + 0.5 - f.W / 2) < 1 and abs(ty + 0.5 - f.H / 2) < 1:
            return R[5]
        if f.side and (ty == 0 or ty == f.H - 1 or tx == 0 or tx == f.W - 1):
            t += 0.8                                         # rounded off at the edges
    elif st in ("needle", "point"):
        t = 3.0 if tx else 1.0                               # one cold highlight down the edge
        if st == "point" or (f.side and ty >= f.H - 2 and f.cube["mat"] == "lc_needle" and
                             f.cube.get("paint") == "claw"):
            t = 0.4 if tx == 0 else 2.0
    elif st in ("skull", "palm", "yoke", "collar", "pelvis", "heel", "foot", "jaw", "brow"):
        t += (streak - 0.5) * 0.6
        if st == "yoke" and f.d == "south" and ty == 0:
            t = 0.6                                          # collarbones
        if st == "pelvis" and f.d == "south" and ty <= 1:
            t -= 0.8                                         # the crest of the hip bones
        if st in ("heel", "foot") and f.side and ty >= f.H - 1:
            t += 1.0
    elif st in ("joint", "knob", "ridge"):
        if f.side:
            mid = abs(ty + 0.5 - f.H / 2.0) < 0.6
            t += 1.4 if mid else (-0.7 if ty <= 1 else 0)    # the crease across a knuckle
    elif st == "claw":
        if f.side:
            smooth = True
            u = ty / max(1, f.H - 1)
            t = 0.8 + 4.2 * u ** 1.2 + (g - 0.5) * 0.6       # bone at the root, black at the tip
            if _rnd(tx, ty, f.index, 5) < 0.06:
                t += 1.2                                     # a crack
        else:
            t += 1.0
    elif st == "brim":
        return _brim(f, tx, ty, R, x, z, g)
    elif st == "crown":
        t += (vnoise(x * 1.4, y * 0.4, z * 1.4, seed=41) - 0.5) * 1.6   # soft folds in the felt
        if f.d == "up":
            t = 2.0 + (n - 0.5) * 1.2
    elif st == "band":
        t = 2.4 + (g - 0.5) * 0.6
        if f.side:
            if ty == 0:
                t = 1.0 if tx % 2 == 0 else 2.6              # a stitch line along the top
            if ty == f.H - 1:
                t = 3.8
            if f.d == "south" and abs(x) < 0.75 and 0 < ty < f.H - 1:
                return (96, 88, 74) if (tx + ty) % 2 else (128, 118, 98)   # a dull buckle
    elif st == "face" or st == "mask":
        t += 0.2
    elif st == "plain":
        pass
    k = _dither(t, tx, ty) if smooth else int(round(t))
    return R[max(0, min(5, k))]


def _brim(f, tx, ty, R, x, z, g):
    if f.d in ("up", "down"):
        rr = math.hypot(x, z - 1.5)
        if f.d == "down":
            if abs(rr - 6.4) < 0.3 and int((math.atan2(z - 1.5, x) + 4) * 9) % 2 == 0:
                return R[3]                                  # stitching round the crown
            return R[5] if rr < 13.0 else R[4]
        t = 2.2 + (g - 0.5) * 0.9 + (fbm(x * 0.4, 0, z * 0.4, seed=43) - 0.5) * 1.0
        if rr > 14.2:
            t = 1.0                                          # the worn edge catches light
        elif rr > 13.6:
            t = 1.7
        if abs(rr - 8.2) < 0.45:
            t -= 0.9                                         # the crease where it was held
        if _rnd(round(x * TEXELS), round(z * TEXELS), 0, 47) < 0.012 and rr < 13:
            return R[5]                                      # moth holes
        return R[max(0, min(5, _dither(t, tx, ty)))]
    return R[1] if tx % 3 else R[2]                          # the edge itself


# ====================================================================== the run

def paint():
    im = Image.open(ATLAS).convert("RGBA")
    before = hashlib.sha256(im.crop((256, 256, 512, 512)).tobytes()).hexdigest()
    rest = hashlib.sha256(im.crop((0, 0, 512, 256)).tobytes()).hexdigest()
    assert before == FACE_HASH, "the face quadrant does not match its recorded hash"

    im.paste(Image.new("RGBA", (FREE[2] - FREE[0], FREE[3] - FREE[1]), (0, 0, 0, 0)),
             (FREE[0], FREE[1]))
    px = im.load()
    placed = layout()
    painted = 0
    for (cname, bone, i), entry in placed.items():
        if "mirror_of" in entry:
            continue
        cube = entry["cube"]
        R = RAMPS[cube["mat"]]
        for d, rect in entry["faces"].items():
            f = Face(cube, d, rect, cname, bone, i)
            for ty in range(f.H):
                for tx in range(f.W):
                    X, Y = f.x0 + tx, f.y0 + ty
                    if FREE[0] <= X < FREE[2] and FREE[1] <= Y < FREE[3]:
                        px[X, Y] = paint_texel(f, tx, ty, R) + (255,)
        painted += 1

    after = hashlib.sha256(im.crop((256, 256, 512, 512)).tobytes()).hexdigest()
    rest_after = hashlib.sha256(im.crop((0, 0, 512, 256)).tobytes()).hexdigest()
    assert before == after, "the face quadrant was touched — refusing to write"
    assert rest == rest_after, "pixels above the free quadrant were touched — refusing to write"
    im.save(ATLAS)
    used = sum((e["box"][2] - e["box"][0]) * (e["box"][3] - e["box"][1])
               for e in placed.values() if "box" in e)
    print(f"painted {painted} unique tier cubes ({len(placed)} with mirrored twins) into "
          f"{ATLAS.name} at {TEXELS * 16} texels/block, {used * 100 // (256 * 256)}% of the free quadrant")
    print(f"face quadrant unchanged: {after[:16]}")
    return placed


if __name__ == "__main__":
    paint()
