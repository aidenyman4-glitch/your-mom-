"""Pixel-art skins for the two tier creatures, painted into the atlas's free quadrant.

The previous pass gave every material one 64x64 tile of noise and pointed every face of every
cube at a random sub-rect of it — so a Locust finger, a Dark Walker hat and a joint knob were
all the same grey static. A Blockbench mob is not textured that way. Here every cube gets its
own unwrap at one texel per model pixel (16 per block, vanilla density), laid out the way box
UV lays a cube out —

            [ up   ][ down ]
    [ west ][ south ][ east ][ north ]

— so the four sides of a limb sit in one continuous strip and stay hand-paintable in
Blockbench's UV editor, and each one is painted for what it IS: ribs on a chest, a crease on a
joint, claws that darken to the tip, a hat band with a stitch line, eye sockets on a face.

The one hard contract is unchanged: only the free quadrant (x 0..256, y 256..512) is written.
The Sun Man's tiles above it and the starburst face beside it are hashed before and after,
and nothing is written if either moved.

    python3 tools/paint_tiers.py
"""
import hashlib
import math
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tiers                              # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ATLAS = ROOT / "resourcepack" / "assets" / "sunman" / "textures" / "entity" / "sun_man.png"
FREE = (0, 256, 256, 512)                 # x0, y0, x1, y1 — the only pixels this may touch
FACE_HASH = "394858d53b822f85e30a8657ef4310e15fb496916295d27e9463b4f2bad2906c"
DIRS = ("north", "south", "east", "west", "up", "down")

# highlight, light, base, shade, dark — five-step ramps, the way a mob palette is built
RAMPS = {
    "dw_skin": [(148, 151, 160), (120, 123, 133), (96, 99, 109), (74, 77, 86), (54, 56, 64)],
    "dw_dark": [(112, 114, 123), (90, 92, 101), (72, 74, 82), (54, 56, 63), (38, 39, 45)],
    "dw_pale": [(190, 192, 199), (164, 167, 175), (140, 143, 152), (114, 117, 126), (88, 91, 99)],
    "dw_hat":  [(58, 58, 66), (41, 41, 47), (27, 27, 32), (18, 18, 22), (10, 10, 13)],
    "dw_band": [(98, 91, 84), (79, 73, 67), (62, 57, 53), (47, 43, 40), (32, 30, 28)],
    "dw_claw": [(104, 101, 96), (78, 76, 73), (55, 54, 52), (37, 36, 36), (21, 21, 22)],
    "dw_eye":  [(255, 255, 242), (255, 248, 218), (255, 238, 176), (242, 208, 124), (204, 162, 82)],
    "lc_light": [(214, 222, 226), (196, 205, 210), (178, 188, 193), (152, 162, 168), (124, 134, 140)],
    "lc_mid":   [(166, 175, 180), (148, 157, 163), (131, 141, 147), (109, 119, 125), (87, 96, 102)],
    "lc_dark":  [(110, 118, 124), (92, 100, 106), (74, 82, 88), (58, 65, 71), (42, 48, 53)],
    "lc_joint": [(142, 150, 156), (122, 131, 137), (102, 111, 117), (84, 92, 98), (66, 73, 79)],
    "lc_void":  [(18, 19, 22), (11, 12, 14), (6, 7, 9), (4, 4, 6), (2, 2, 3)],
}
EMISSIVE = {"dw_eye"}


def _hash(*parts):
    h = 2166136261
    for p in parts:
        for ch in str(p):
            h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


def _rnd(*parts):
    return _hash(*parts) / 0xFFFFFFFF


# ====================================================================== layout

def _dims(size):
    """Face pixel sizes (w, h) for each direction, from a cube size in px."""
    w, h, d = size
    return {"north": (w, h), "south": (w, h), "east": (d, h), "west": (d, h),
            "up": (w, d), "down": (w, d)}


def _ceil(v):
    return max(1, int(math.ceil(v - 1e-6)))


def _unwrap(size):
    """Offsets of each face inside a cube's unwrap, and the unwrap's footprint."""
    w, h, d = (_ceil(v) for v in size)
    off = {"up": (d, 0), "down": (d + w, 0),
           "west": (0, d), "south": (d, d), "east": (d + w, d), "north": (2 * d + w, d)}
    return off, (2 * d + 2 * w, d + h)


def layout():
    """Every tier cube's face UVs, in 512-px atlas space. Deterministic: the exporters and
    the painter all call this and agree without a file between them."""
    items = []
    for cname, c in tiers.TIERS.items():
        for bone in c.BONE_ORDER:
            for i, cube in enumerate(c.CUBES_PX.get(bone, [])):
                off, (fw, fh) = _unwrap(cube["size"])
                items.append((cname, bone, i, cube, off, fw, fh))
    # shelf pack, tallest first; ties broken by name so the layout is stable
    items.sort(key=lambda it: (-it[6], -it[5], it[0], it[1], it[2]))
    x0, y0, x1, y1 = FREE
    x, y, shelf = x0, y0, 0
    placed = {}
    for cname, bone, i, cube, off, fw, fh in items:
        if x + fw > x1:
            x, y, shelf = x0, y + shelf + 1, 0
        assert y + fh <= y1, "tier skins no longer fit the free quadrant"
        dims = _dims(cube["size"])
        faces = {}
        for d in DIRS:
            ox, oy = off[d]
            fw_, fh_ = dims[d]
            faces[d] = (x + ox, y + oy, x + ox + fw_, y + oy + fh_)
        placed[(cname, bone, i)] = {"origin": (x, y), "faces": faces, "cube": cube,
                                    "box": (x, y, x + fw, y + fh)}
        x += fw + 1
        shelf = max(shelf, fh)
    return placed


# ====================================================================== painting

class Canvas:
    def __init__(self, img):
        self.px = img.load()

    def put(self, x, y, rgb):
        if FREE[0] <= x < FREE[2] and FREE[1] <= y < FREE[3]:
            self.px[x, y] = tuple(int(c) for c in rgb) + (255,)


def _face_texels(rect):
    u0, v0, u1, v1 = rect
    return int(u0), int(v0), _ceil(u1 - u0), _ceil(v1 - v0)


def _tone(ramp, k):
    return ramp[max(0, min(len(ramp) - 1, k))]


def paint_face(cv, rect, cube, d, key):
    mat, style = cube["mat"], cube.get("paint") or "plain"
    R = RAMPS[mat]
    x0, y0, W, H = _face_texels(rect)
    side = d in ("north", "south", "east", "west")
    for ty in range(H):
        for tx in range(W):
            k = 2
            r = _rnd(key, d, tx, ty)
            if d == "up":
                k = 1
            elif d == "down":
                k = 3
            if side:
                # light from above: the top row catches it, the bottom row sits in shadow
                if H >= 4 and ty == 0:
                    k -= 1
                if H >= 3 and ty == H - 1:
                    k += 1
                # thin limbs read round with the trailing column a step darker
                if W >= 2 and tx == W - 1 and style in ("limb", "thigh", "segment", "neck", "waist"):
                    k += 1
                if W >= 3 and tx == 0 and style in ("limb", "thigh", "segment", "waist"):
                    k -= 1
            k = _style(style, d, tx, ty, W, H, k, r, cube, key)
            if k is None:
                continue
            if isinstance(k, tuple):
                rgb = k
            else:
                # sparse speckle, run vertically on the sides so it reads as grain, not static
                if mat not in EMISSIVE and style not in ("void", "eye"):
                    if side and _rnd(key, d, tx, ty // 2) < 0.10:
                        k += 1 if _rnd(key, d, tx, "s") < 0.6 else -1
                    elif not side and r < 0.08:
                        k += 1
                rgb = _tone(R, k)
            cv.put(x0 + tx, y0 + ty, rgb)


def _style(style, d, tx, ty, W, H, k, r, cube, key):
    side = d in ("north", "south", "east", "west")
    front = d == "south"
    if style in ("eye", "void"):
        return 0 if style == "eye" and (ty == 0 or tx == 0) else (1 if style == "eye" else 2)
    if style in ("joint", "knob", "ridge"):
        if side and H >= 3 and ty == H // 2:
            return k + 1                                   # the crease across a knuckle
        if side and ty == 0:
            return 0
        return k
    if style in ("claw",):
        if side:
            t = ty / max(1, H - 1)
            return 1 + int(round(t * 3.2))                 # bone at the root, black at the tip
        return k + 1
    if style == "bone":
        if side and ty == H - 1:
            return k + 1                                   # the knuckle under each segment
        return k - 1 if side else k
    if style in ("ribs", "chest"):
        if side and d != "north" and 1 <= ty < H - 1:
            if ty % 2 == 1:
                return k + 1                               # a rib's shadow
            if front and (tx == W // 2 or (W % 2 == 0 and tx == W // 2 - 1)):
                return k                                   # the sternum breaks the ribs
            return k - 1 if ty % 4 == 2 else k
        if d == "north" and (tx == W // 2 or tx == (W - 1) // 2):
            return k + 1                                   # the spine's groove
        return k
    if style == "waist":
        if front and tx in (W // 2 - 1, W // 2) and ty % 3 == 1:
            return k + 1                                   # a pinched, segmented gut
        return k
    if style == "yoke":
        if front and ty == 0:
            return 0                                       # collarbones
        return k
    if style == "face":
        # the head of the Dark Walker: the brim's shadow over the top rows, sunk sockets
        # round the eyes, hollow cheeks — and no mouth. None of the references has one.
        if front:
            if ty <= 1:
                return k + 1 + (1 - ty)
            if ty in (3, 4) and tx in (0, 1, W - 2, W - 1):
                return 4
            if ty == 5 and tx in (1, W - 2):
                return 1
            if ty == 6 and 1 <= tx <= W - 2:
                return k + 1
            return k
        if side and ty <= 1:
            return k + 1
        return k
    if style == "jaw":
        return k + 1
    if style == "brow":
        return k + 1
    if style == "skull":
        # the Locust's head: plates with seams, and a hollow under each eye
        if front and (2 <= ty <= 5 and (0 <= tx <= 4 or W - 5 <= tx <= W - 1)
                      or 6 <= ty <= 8 and 2 <= tx <= W - 3):
            return k + 1 if not (ty in (2, 5, 6, 8) and r < 0.35) else k   # sockets, ragged
        if front and ty == 1 and 1 <= tx <= W - 2:
            return k - 1                                   # the brow plate catches the light
        if side and (tx == 0 or tx == W - 1) and ty > 0:
            return k + 1
        if d == "up" and (tx == W // 2) and ty % 2 == 0:
            return k + 2                                   # the cranial seam
        if r < 0.025:
            return k + 2                                   # hairline cracks
        return k
    if style in ("segment", "plate"):
        if side and H >= 4 and ty % 3 == 2:
            return k + 1                                   # carapace banding
        return k
    if style == "knuckle":
        return k + 1 if side and ty == H - 1 else k
    if style == "brim":
        # painted in WORLD space, because the brim is many plates: the edge and the crease
        # have to follow the disc, not each plate's own rectangle
        fx, fy, fz = cube["from"]
        if d in ("up", "down"):
            wx = fx + tx + 0.5
            wz = fz + ty + 0.5 if d == "up" else fz + cube["size"][2] - ty - 0.5
            rr = math.hypot(wx, wz - 1.5)
            if d == "down":
                return 4 if rr < 13.0 else 3
            if rr > 13.6:
                return 1                                   # the worn edge catches light
            if abs(rr - 8.2) < 0.55 and r < 0.8:
                return 1                                   # the crease where it was held
            if r < 0.06:
                return 3
            return 2
        return 1                                           # the edge itself
    if style == "crown":
        if side and tx % 4 == 1 and ty > 0:
            return k - 1                                   # soft folds in the felt
        if d == "up":
            return 2
        return k
    if style == "band":
        if side:
            return 1 if (ty == 0 and tx % 2 == 0) else (3 if ty == H - 1 else 2)
        return k
    if style == "pelvis":
        if front and ty == 1:
            return k + 1
        return k
    if style in ("heel", "foot", "palm"):
        return k + 1 if side and ty == H - 1 else k
    return k


def paint():
    im = Image.open(ATLAS).convert("RGBA")
    before = hashlib.sha256(im.crop((256, 256, 512, 512)).tobytes()).hexdigest()
    tiles = hashlib.sha256(im.crop((0, 0, 512, 256)).tobytes()).hexdigest()
    assert before == FACE_HASH, "the face quadrant does not match its recorded hash"

    # clear the free quadrant: the old noise tiles go, unused space is transparent
    im.paste(Image.new("RGBA", (FREE[2] - FREE[0], FREE[3] - FREE[1]), (0, 0, 0, 0)),
             (FREE[0], FREE[1]))
    cv = Canvas(im)
    placed = layout()
    for (cname, bone, i), entry in placed.items():
        cube = entry["cube"]
        for d, rect in entry["faces"].items():
            paint_face(cv, rect, cube, d, f"{cname}:{bone}:{i}")

    after = hashlib.sha256(im.crop((256, 256, 512, 512)).tobytes()).hexdigest()
    tiles_after = hashlib.sha256(im.crop((0, 0, 512, 256)).tobytes()).hexdigest()
    assert before == after, "the face quadrant was touched — refusing to write"
    assert tiles == tiles_after, "the Sun Man's tiles were touched — refusing to write"
    im.save(ATLAS)
    used = max(e["box"][3] for e in placed.values()) - FREE[1]
    print(f"painted {len(placed)} tier cubes into {ATLAS.name} ({used}/256 rows of the free quadrant)")
    print(f"face quadrant unchanged: {after[:16]}   Sun Man tiles unchanged: {tiles_after[:16]}")
    return placed


if __name__ == "__main__":
    paint()
