"""Blood decals: four painted textures, their flat item models and item definitions.

The datapack lays blood as `item_display` quads, never as a block: retexturing a vanilla block
would turn every one of them in the world into blood, and a display quad takes no block
updates and turns to any angle. These are the textures on those quads.

Pixel art at 32 texels to the block, hard-edged like the references (a splat on grass is a
clump of flat red pixels with droplets thrown off it, never a soft airbrush). Every outline is
built from two or three LOW-frequency harmonics on a circle — a single high-frequency sine,
the obvious approach, draws a regular star, not a puddle — and the satellite drops are placed
by the same seeded generator, so a rebuild is pixel-identical.

    pool      2 x 2 blocks, ~60% covered   the big one: wet in the middle, a dried dark rim
    splatter  2 x 2 blocks, ~17% covered   an impact: a small core and drops flung outward
    trail     1 x 2 blocks, ~32% covered   something dragged: parallel smears that thin out,
                                           laid along z so it lies along a body at the body's yaw
    smear     1 x 1.5 blocks, vertical     on a wall: three claw gouges, run down with blood

The ramp runs from dried near-black #4A0709 to wet #D21A18. The datapack shows decals at a
fixed light level (`brightness:{sky:4,block:0}`) so they stay dark at night, which pulls
these down to the brief's #580A0C-#9E1A1A range on screen.

    python3 tools/paint_decals.py
"""
import json
import math
import random
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "resourcepack" / "assets" / "sunman"
TEX = PACK / "textures" / "decal"
TPB = 32                                   # texels per block

RAMP = [(74, 7, 9), (98, 10, 12), (126, 15, 17), (154, 22, 22), (182, 28, 26), (210, 38, 34)]


def _h(*a):
    h = 2166136261
    for v in a:
        h = ((h ^ (int(v) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
        h ^= h >> 13
    return h / 0xFFFFFFFF


def vnoise(x, y, seed):
    xi, yi = math.floor(x), math.floor(y)
    xf, yf = x - xi, y - yi
    u, v = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)
    a, b = _h(xi, yi, seed), _h(xi + 1, yi, seed)
    c, d = _h(xi, yi + 1, seed), _h(xi + 1, yi + 1, seed)
    return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v


class Blob:
    """A closed outline r(theta) = R * (1 + sum a_k sin(k theta + phi_k)) for k in 2..4."""

    def __init__(self, cx, cy, R, rnd, harmonics=((2, 0.16), (3, 0.11), (4, 0.06)), stretch=(1.0, 1.0)):
        self.cx, self.cy, self.R, self.sx, self.sy = cx, cy, R, stretch[0], stretch[1]
        self.terms = [(k, a * (0.7 + 0.6 * rnd.random()), rnd.random() * math.tau) for k, a in harmonics]

    def inside(self, x, y):
        dx, dy = (x - self.cx) / self.sx, (y - self.cy) / self.sy
        r = math.hypot(dx, dy)
        th = math.atan2(dy, dx)
        edge = self.R * (1 + sum(a * math.sin(k * th + p) for k, a, p in self.terms))
        return r / max(edge, 1e-6)                        # < 1 inside


def _paint(w, h, shapes, seed, wet=(0.35, 0.75), ragged=0.3):
    """Rasterise a list of Blob-like shapes into an RGBA image. Tone comes from how deep a
    texel is inside its shape (the rim dries dark), plus low-frequency mottling."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = im.load()
    for y in range(h):
        for x in range(w):
            best = min(s.inside(x + 0.5, y + 0.5) for s in shapes)
            # a ragged edge: the outline wanders by a texel or two, and loose texels sit
            # just outside it, the way blood soaks into grass
            edge = 1.0 + (vnoise(x / 1.6, y / 1.6, seed + 17) - 0.5) * ragged
            if best >= edge:
                if best < edge + 0.3 and _h(x, y, seed + 29) < 0.12 * ragged / 0.3:
                    px[x, y] = RAMP[1 if _h(x, y, seed) < 0.5 else 2] + (255,)
                continue
            depth = max(0.0, 1.0 - best / edge)           # 0 at the edge, 1 at the centre
            mott = vnoise(x / 5.0, y / 5.0, seed) * 0.6 + vnoise(x / 2.2, y / 2.2, seed + 9) * 0.4
            t = 1.2 + 3.2 * min(1.0, depth / 0.55) + (mott - 0.5) * 2.0
            if depth < 0.08:
                t = 0.6                                   # the dried rim
            if wet[0] < mott < wet[1] and depth > 0.45 and _h(x, y, seed + 3) < 0.08:
                t = 5.4                                   # a wet glint
            px[x, y] = RAMP[max(0, min(5, int(round(t))))] + (255,)
    return im


def _coverage(im):
    a = im.getchannel("A")
    return sum(1 for y in range(im.height) for x in range(im.width) if a.getpixel((x, y))) / (im.width * im.height)


def pool():
    rnd = random.Random(11)
    w = h = 2 * TPB
    shapes = [Blob(w * 0.48, h * 0.5, w * 0.27, rnd, harmonics=((2, 0.2), (3, 0.14), (4, 0.08)))]
    for k in range(5):                                    # lobes where it ran off
        a = k * math.tau / 5 + rnd.uniform(-0.5, 0.5)
        d = w * (0.18 + 0.08 * rnd.random())
        shapes.append(Blob(w / 2 + math.cos(a) * d, h / 2 + math.sin(a) * d,
                           w * (0.09 + 0.07 * rnd.random()), rnd))
    for k in range(16):                                   # drops, all the way round
        a = k * math.tau / 16 + rnd.uniform(-0.25, 0.25)
        d = w * (0.36 + 0.1 * rnd.random())
        shapes.append(Blob(w / 2 + math.cos(a) * d, h / 2 + math.sin(a) * d, 0.7 + rnd.random() * 1.7, rnd,
                           harmonics=((2, 0.2),)))
    return _paint(w, h, shapes, 101, ragged=0.34)


def splatter():
    rnd = random.Random(23)
    w = h = 2 * TPB
    cx, cy = w * 0.47, h * 0.5
    shapes = [Blob(cx, cy, w * 0.13, rnd, harmonics=((2, 0.22), (3, 0.18), (5, 0.08)))]
    for i in range(26):                                   # flung outward, the far ones smaller
        a = rnd.random() * math.tau
        d = w * (0.14 + 0.32 * rnd.random() ** 0.8)
        r = max(0.6, 3.2 * (1.0 - d / (w * 0.5)) * (0.5 + rnd.random()))
        el = 1.0 + 1.6 * (d / (w * 0.5))                  # drops stretch along their flight
        x, y = cx + math.cos(a) * d, cy + math.sin(a) * d
        s = Blob(x, y, r, rnd, harmonics=((2, 0.18),))
        s.sx, s.sy = el * abs(math.cos(a)) + abs(math.sin(a)), el * abs(math.sin(a)) + abs(math.cos(a))
        shapes.append(s)
    return _paint(w, h, shapes, 202)


def trail():
    rnd = random.Random(37)
    w, h = 2 * TPB, TPB
    shapes = []
    # three or four parallel drag marks, thick where it started, thinning, breaking up
    for k, yy in enumerate((h * 0.32, h * 0.47, h * 0.6, h * 0.72)):
        x = 2.0
        while x < w - 2:
            t = x / w
            r = (3.2 - 2.6 * t) * (0.75 + 0.5 * rnd.random()) * (0.7 if k in (0, 3) else 1.0)
            if r < 0.7 or rnd.random() < 0.06 + 0.25 * t * t:
                x += 2.5
                continue
            shapes.append(Blob(x, yy + math.sin(x / 9.0 + k) * 1.4, r, rnd, harmonics=((2, 0.15),),
                               stretch=(2.2, 1.0)))
            x += r * 1.6
    shapes.append(Blob(5, h * 0.52, h * 0.3, rnd))          # where it lay first
    return _paint(w, h, shapes, 303)


def smear():
    """On a wall: three claw gouges raked down at a slant, blood run down from each in drips."""
    rnd = random.Random(41)
    w, h = TPB, int(TPB * 1.5)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = im.load()

    def put(x, y, t):
        if 0 <= x < w and 0 <= y < h:
            px[x, y] = RAMP[max(0, min(5, int(round(t))))] + (255,)

    shapes = [Blob(w * 0.52, h * 0.24, w * 0.3, rnd, harmonics=((2, 0.2), (3, 0.14)))]
    blob = _paint(w, h, shapes, 404)
    im.alpha_composite(blob)
    for k in range(3):                                     # the gouges: dark, clean, parallel
        x0 = w * 0.18 + k * w * 0.22
        for i in range(int(h * 0.7)):
            x = int(round(x0 + i * 0.3))
            y = int(h * 0.06) + i
            put(x - 1, y, 4.6)                             # the lit lip of the cut
            put(x, y, 0.0)
            put(x + 1, y, 0.0)
    for k in range(7):                                     # runs: gravity, uneven lengths
        x = int(w * (0.2 + 0.6 * rnd.random()))
        y0 = int(h * (0.2 + 0.15 * rnd.random()))
        ln = int(h * (0.25 + 0.5 * rnd.random()))
        for i in range(ln):
            put(x, y0 + i, 2.6 + (1.2 if i < ln * 0.3 else 0.0))
        put(x, y0 + ln, 3.6)
        put(x + 1, y0 + ln, 2.6)
        put(x, y0 + ln + 1, 2.0)
    return im


def _plane(size_blocks, vertical=False):
    """A flat quad centred on the model origin column, `size_blocks` (w, d) in blocks.
    Horizontal decals lie in y = 8 (the entity's own height); the wall smear stands in z = 8.
    Both faces are given, so a mirrored or flipped display can never show its back as empty."""
    w, d = (s * 16 for s in size_blocks)
    x0, x1 = 8 - w / 2, 8 + w / 2
    if vertical:
        y0, y1 = 8 - d / 2, 8 + d / 2
        frm, to = [x0, y0, 7.995], [x1, y1, 8.0]
        faces = {"south": {"uv": [0, 0, 16, 16], "texture": "#0"},
                 "north": {"uv": [16, 0, 0, 16], "texture": "#0"}}
    else:
        z0, z1 = 8 - d / 2, 8 + d / 2
        frm, to = [x0, 7.99, z0], [x1, 8.0, z1]
        faces = {"up": {"uv": [0, 0, 16, 16], "texture": "#0"},
                 "down": {"uv": [0, 16, 16, 0], "texture": "#0"}}
    return {"from": [round(v, 3) for v in frm], "to": [round(v, 3) for v in to], "faces": faces}


DECALS = {
    "blood_pool": (pool, (2, 2), False),
    "blood_splatter": (splatter, (2, 2), False),
    "blood_trail": (lambda: trail().transpose(Image.Transpose.ROTATE_270), (1, 2), False),
    "blood_smear": (smear, (1, 1.5), True),
}


def build():
    TEX.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, (fn, size, vertical) in DECALS.items():
        im = fn()
        im.save(TEX / f"{name}.png", optimize=True)
        model = {"textures": {"0": f"sunman:decal/{name}", "particle": f"sunman:decal/{name}"},
                 "elements": [_plane(size, vertical)]}
        mp = PACK / "models" / "item" / "decal" / f"{name}.json"
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(json.dumps(model, indent=2) + "\n")
        (PACK / "items" / f"{name}.json").write_text(json.dumps(
            {"model": {"type": "minecraft:model", "model": f"sunman:item/decal/{name}"}}, indent=2) + "\n")
        out[name] = (im.size, _coverage(im))
        print(f"  {name:15} {im.width}x{im.height}  {size[0]}x{size[1]} blocks  "
              f"{out[name][1] * 100:4.1f}% covered{'  (vertical)' if vertical else ''}")
    return out


def preview(out=ROOT / "docs" / "blood_decals.png", scale=6):
    """The four textures laid on 26.3's own grass, pixel for pixel, for the docs."""
    import iso
    grass = iso.tinted("grass_block_top")
    tiles = []
    for name in DECALS:
        im = Image.open(TEX / f"{name}.png").convert("RGBA")
        bg = Image.new("RGBA", im.size)
        for y in range(0, im.height, 16):
            for x in range(0, im.width, 16):
                bg.paste(grass.resize((16, 16)), (x, y))
        bg = bg.resize((im.width * 2, im.height * 2), Image.NEAREST)      # grass at 16 px/block
        bg.alpha_composite(im.resize(bg.size, Image.NEAREST))
        tiles.append(bg.resize((bg.width * scale // 2, bg.height * scale // 2), Image.NEAREST))
    w = sum(t.width for t in tiles) + 12 * (len(tiles) + 1)
    h = max(t.height for t in tiles) + 24
    sheet = Image.new("RGB", (w, h), (28, 28, 32))
    x = 12
    for t in tiles:
        sheet.paste(t, (x, 12))
        x += t.width + 12
    sheet.save(out, optimize=True)
    return out


if __name__ == "__main__":
    build()
    print(f"  preview -> {preview().relative_to(ROOT)}")
