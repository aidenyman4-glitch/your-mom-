"""Gives the tier creatures real tiles in the atlas, in place, without touching the face.

`export_models.py` resolves a cube's material with `SLOTS.get(mat, SLOTS["bone"])`, and
`texture.py`'s SLOTS has never had an entry for a single one of the `lc_*` / `dw_*`
materials the tier creatures are authored with. So every Locust cube — and now every Dark
Walker cube — lands on the Sun Man's bone tile, and the creatures come out of the exporter
the same dead grey as each other and as him.

This paints the missing tiles into the atlas's free quadrant rather than regenerating it.
Regenerating would mean re-running `texture.py`, which wants
`references/EXACT_SOURCE_Face_Starburst.png` — lost with the project folder — and the one
hard contract in this project is that the face at (256,256) stays pixel-for-pixel. Patching
in place cannot break what it does not touch, and the check at the bottom proves it.

    python3 tools/atlas_patch.py
"""
import hashlib
import random
from pathlib import Path

from PIL import Image

import palette as pal

ROOT = Path(__file__).resolve().parent.parent
ATLAS = ROOT / "resourcepack" / "assets" / "sunman" / "textures" / "entity" / "sun_man.png"
TILE = 64

# The free 4x4 block of tiles at x 0..256, y 256..512. Everything above y=256 is the Sun
# Man's own material tiles; everything right of x=256 below y=256 is the face.
TIER_SLOTS = {
    "lc_light": (0, 256),   "lc_mid":  (64, 256),  "lc_dark": (128, 256), "lc_joint": (192, 256),
    "lc_void":  (0, 320),   "dw_dark": (64, 320),  "dw_mid":  (128, 320), "dw_hat":   (192, 320),
    "dw_pale":  (0, 384),   "dw_eye":  (64, 384),
}

# How each material is surfaced. `streak` adds vertical grain, which reads as fibre on a
# limb and as grown bone on the Locust's plates; `pit` is the chance of a dark pock.
STYLE = {
    "lc_light": dict(amount=11, streak=0.5, pit=0.010),
    "lc_mid":   dict(amount=12, streak=0.7, pit=0.014),
    "lc_dark":  dict(amount=9,  streak=0.8, pit=0.016),
    "lc_joint": dict(amount=14, streak=0.2, pit=0.022),
    "lc_void":  dict(amount=2,  streak=0.0, pit=0.000),
    "dw_dark":  dict(amount=8,  streak=0.9, pit=0.006),
    "dw_mid":   dict(amount=9,  streak=1.1, pit=0.008),
    "dw_hat":   dict(amount=4,  streak=0.3, pit=0.004),
    "dw_pale":  dict(amount=10, streak=0.4, pit=0.012),
    "dw_eye":   dict(amount=3,  streak=0.0, pit=0.000),
}


def _tile(rng, base, amount=12, streak=0.0, pit=0.012):
    img = Image.new("RGBA", (TILE, TILE), tuple(base) + (255,))
    px = img.load()
    col = [rng.gauss(0, amount * streak) for _ in range(TILE)]
    for y in range(TILE):
        for x in range(TILE):
            d = rng.gauss(0, amount) + col[x]
            if rng.random() < pit:
                d -= rng.uniform(16, 38)
            px[x, y] = tuple(max(0, min(255, int(c + d))) for c in base) + (255,)
    return img


def patch():
    im = Image.open(ATLAS).convert("RGBA")
    before = hashlib.sha256(im.crop((256, 256, 512, 512)).tobytes()).hexdigest()

    for mat, (x, y) in TIER_SLOTS.items():
        rng = random.Random(hash(mat) & 0xFFFF)
        im.paste(_tile(rng, pal.MATS[mat], **STYLE[mat]), (x, y))

    after = hashlib.sha256(im.crop((256, 256, 512, 512)).tobytes()).hexdigest()
    assert before == after, "the face quadrant was touched — refusing to write"
    im.save(ATLAS)
    print(f"patched {len(TIER_SLOTS)} tier tiles into {ATLAS.name}")
    print(f"face quadrant unchanged: {before[:16]}")


if __name__ == "__main__":
    patch()
