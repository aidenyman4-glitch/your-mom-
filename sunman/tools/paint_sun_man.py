"""The Sun Man's surface, repainted in place. His geometry, UVs and face are untouched.

His cubes map onto 64x64 material tiles in the top half of the atlas at three texels per
model pixel (four to the block), each face sampling its own rectangle of a tile. Those tiles
were flat photographic noise — a robe, a neck and a bone limb were the same static in three
greys — so this repaints the thirteen tiles that are his and only his, as pixel art, each for
what it dresses:

    the robe        vertical folds, deep creases, a weave, tears, holes, old blood
    the wrappings   strips wound round and round him, each overlapping the last
    the neck        the ink drawing's neck: ridged with wrinkles all the way up, cords of tendon
    the bones       cracked ivory, sinew down the length, grime in the creases
    the hands       knuckle creases, and the fingers dark to the second joint — dipped in it
    the head        pale crazed porcelain behind the face
    the rays        bone-white, flecked

Because any face can land anywhere on a tile, every texture is stationary — detailed
everywhere, with no one feature you would notice repeating.

Untouched, and hashed before and after: the starburst face quadrant, the villager-head prop's
tiles, every tile nothing currently uses, and the whole free quadrant (the tier creatures').

    python3 tools/paint_sun_man.py
"""
import hashlib
import math
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paint_tiers import _rnd, fbm, vnoise   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ATLAS = ROOT / "resourcepack" / "assets" / "sunman" / "textures" / "entity" / "sun_man.png"
FACE_HASH = "394858d53b822f85e30a8657ef4310e15fb496916295d27e9463b4f2bad2906c"
TILE = 64
BLOOD = (74, 24, 22)
OLD_BLOOD = (58, 32, 29)

# seven-step ramps, highlight to deepest shadow, keyed off each tile's original average
ROBE = [(110, 111, 116), (90, 91, 96), (72, 73, 78), (56, 57, 62), (42, 42, 47), (28, 28, 32), (16, 16, 19)]
WRAP = [(98, 96, 93), (76, 74, 72), (58, 57, 56), (43, 42, 43), (31, 30, 32), (20, 19, 21), (10, 10, 11)]
NECK = [(126, 118, 110), (102, 95, 89), (82, 76, 72), (64, 59, 57), (49, 45, 44), (34, 31, 31), (19, 17, 18)]
BELT = [(98, 99, 104), (80, 81, 86), (63, 64, 68), (50, 51, 55), (38, 38, 42), (26, 26, 30), (15, 15, 18)]
BONE = [(246, 242, 232), (232, 227, 215), (216, 210, 197), (198, 192, 178), (176, 169, 155), (146, 139, 126), (104, 98, 88)]
SKIN = [(206, 199, 186), (190, 183, 170), (174, 167, 155), (156, 149, 138), (136, 129, 119), (110, 104, 96), (78, 73, 67)]
SINEW = [(132, 132, 135), (114, 114, 117), (96, 96, 99), (80, 80, 83), (64, 64, 67), (48, 48, 51), (30, 30, 33)]
HAND = [(190, 186, 175), (172, 168, 157), (152, 148, 138), (132, 128, 119), (112, 108, 100), (90, 86, 80), (62, 59, 55)]
FOOT = [(102, 92, 88), (84, 75, 72), (68, 60, 58), (54, 47, 46), (41, 36, 35), (29, 25, 25), (17, 15, 15)]
PORCELAIN = [(255, 254, 248), (246, 243, 235), (236, 232, 223), (222, 218, 208), (202, 197, 186), (172, 166, 154), (128, 122, 112)]
RAY = [(252, 250, 244), (240, 238, 232), (228, 226, 220), (214, 212, 205), (196, 193, 185), (170, 166, 157), (130, 126, 118)]


def tone(ramp, t):
    return ramp[max(0, min(len(ramp) - 1, int(round(t))))]


def mix(a, b, k):
    k = max(0.0, min(1.0, k))
    return tuple(int(x + (y - x) * k) for x, y in zip(a, b))


def stain(rgb, x, y, seed, amount=0.62, colour=OLD_BLOOD):
    s = fbm(x * 0.07, y * 0.07, 0.0, seed=seed)
    if s > amount:
        return mix(rgb, colour, (s - amount) * 5.0)
    return rgb


# ====================================================================== the painters

def robe(x, y):
    """Heavy cloth falling in vertical folds that wander, a fine weave, the odd tear and hole,
    and old blood soaked up from the hem."""
    w = vnoise(x * 0.11, y * 0.025, 0.0, seed=101)
    fold = math.sin((x / 8.5 + 0.9 * w) * math.tau)
    t = 3.0 - 1.5 * fold
    if fold > 0.93:
        t = 1.0                                              # the lit ridge of a fold
    if fold < -0.9:
        t = 5.6                                              # the crease
    t += ((x + y) % 2) * 0.35 + (vnoise(x * 0.6, y * 0.6, 0, seed=103) - 0.5) * 0.9
    for ty in (11, 37, 52):                                  # tears, frayed below
        wob = int(2 * vnoise(x * 0.3, ty, 0, seed=105))
        if y == ty + wob and vnoise(x * 0.2, ty, 1, seed=107) > 0.45:
            t = 6
        elif y == ty + wob + 1 and x % 3 == 0:
            t = 1.5
    if _rnd(x // 2, y // 2, 109) < 0.012:
        t = 6.6                                              # moth-eaten
    return stain(tone(ROBE, t), x, y, 111, 0.60)


def wraps(x, y):
    """Strips wound round him, each overlapping the one below: a lit upper edge, the cloth,
    a dark lip of shadow where the next strip lies over it, and gaps between."""
    yy = y + 0.28 * x + 2.0 * vnoise(x * 0.08, 0, 0, seed=121)
    band = math.floor(yy / 6.5)
    v = yy - band * 6.5
    base = 2.6 + 1.4 * (_rnd(band, 123) - 0.5)
    if v < 1.0:
        t = base - 1.6
    elif v > 5.2:
        t = base + 2.3
    else:
        t = base + (vnoise(x * 0.9, y * 0.4, band, seed=125) - 0.5) * 1.4
        if (x * 3 + int(v * 2)) % 7 == 0:
            t += 0.8                                         # the weave
    if _rnd(band, x // 9, 127) < 0.08 and 1 <= v <= 5:
        t = 6.2                                              # a gap: the dark under it
    rgb = tone(WRAP, t)
    return stain(rgb, x, y, 129, 0.64, BLOOD)


def neck(x, y):
    """The neck in the ink drawing is wrinkled all the way up — ridge after ridge, never evenly
    spaced — with cords of tendon running the length under the skin."""
    wave = 1.4 * math.sin(x / 6.5 + 1.7 * vnoise(0, y * 0.2, 0, seed=141))
    yy = y + wave
    spacing = 4.2 + 1.6 * vnoise(0, yy * 0.15, 0, seed=143)
    p = (yy % spacing) / spacing
    t = 2.6
    if p < 0.18:
        t = 1.0                                              # the lit crest of a wrinkle
    elif p < 0.34:
        t = 1.8
    elif p > 0.82:
        t = 5.2                                              # the fold under it
    t += (vnoise(x * 0.35, y * 0.05, 0, seed=145) - 0.5) * 1.6   # tendons
    if _rnd(x, y, 147) < 0.03:
        t += 1.2                                             # pores
    return tone(NECK, t)


def belt(x, y):
    """The hips: dark cloth drawn tight in diagonal folds, and a twisted cord round them."""
    fold = math.sin(((x + 0.35 * y) / 11.0 + 1.4 * vnoise(x * 0.06, y * 0.06, 0, seed=161)) * math.tau)
    t = 3.0 - 0.8 * fold
    if 26 <= y <= 31:
        twist = (x + (y - 26) * 2) % 6
        t = 1.4 if twist < 2 else (3.0 if twist < 4 else 5.4)   # the cord
    t += (vnoise(x * 0.7, y * 0.7, 0, seed=163) - 0.5) * 0.8
    return stain(tone(BELT, t), x, y, 165, 0.66)


def _bone(x, y, ramp, seed, cracks=0.010):
    t = 2.2 + (vnoise(x * 0.5, y * 0.06, 0, seed=seed) - 0.5) * 2.0      # sinew, lengthwise
    t += (fbm(x * 0.12, y * 0.12, 0, seed=seed + 1) - 0.5) * 1.6         # grime
    ring = (y + int(4 * vnoise(x * 0.12, 0, 0, seed=seed + 2))) % 23
    if ring == 0 and vnoise(x * 0.3, y, 0, seed=seed + 5) > 0.4:
        t += 1.4                                                          # a crease, part-way round
    elif ring == 1:
        t -= 0.6
    # cracks: rare, short, jagged lines that wander down the bone
    cx = x + int(2.5 * vnoise(0, y * 0.3, 0, seed=seed + 3))
    if cx % 7 == 0 and _rnd(cx // 7, y // 11, seed + 4) < cracks * 14:
        t = 5.2
    return tone(ramp, t)


def limb_bone(x, y):
    return _bone(x, y, BONE, 181)


def shin_bone(x, y):
    rgb = _bone(x, y, BONE, 191, cracks=0.016)
    return stain(rgb, x, y, 195, 0.68)


def forearm(x, y):
    """Thin skin over the bone, and veins wandering under it."""
    t = 2.3 + (vnoise(x * 0.4, y * 0.08, 0, seed=201) - 0.5) * 1.6
    t += (fbm(x * 0.15, y * 0.15, 0, seed=202) - 0.5) * 1.2
    v = vnoise(x * 0.16 + y * 0.03, y * 0.1, 0, seed=203)
    if abs(v - 0.5) < 0.03:
        t = 5.0                                              # a vein
    if y % 19 == 7:
        t += 1.2
    return tone(SKIN, t)


def sinew(x, y):
    """Grey cords: fibres side by side, dark between them."""
    t = 2.6 + (1.6 if x % 4 == 3 else -0.4 * (x % 4 == 1))
    t += (vnoise(x * 0.5, y * 0.12, 0, seed=211) - 0.5) * 1.8
    return tone(SINEW, t)


def hands(x, y):
    """Knuckles creased dark, and the lower half stained — the hands have been in it."""
    t = 2.4 + (fbm(x * 0.2, y * 0.2, 0, seed=221) - 0.5) * 1.6
    if (y % 8 == 0 and vnoise(x * 0.4, y, 0, seed=223) > 0.35):
        t = 5.2                                              # knuckle creases
    if (y % 8 == 1):
        t -= 0.8
    rgb = tone(HAND, t)
    if y > 34:
        rgb = stain(rgb, x, y, 225, 0.60 - (y - 34) / 160.0, OLD_BLOOD)
    return rgb


def fingers(x, y):
    """Pale to the second joint, then darker, then black at the tip — and between the two,
    the brown of something dried."""
    t = 2.0 + (vnoise(x * 0.5, y * 0.1, 0, seed=231) - 0.5) * 1.4
    if y % 7 == 0:
        t += 1.8                                             # joint creases
    rgb = tone(HAND, t)
    if y > 34:
        k = (y - 34) / 29.0
        dark = mix(OLD_BLOOD, (12, 10, 10), max(0.0, (k - 0.35) / 0.65))
        rgb = mix(rgb, dark, min(1.0, k * 1.6 + (vnoise(x * 0.6, y * 0.3, 0, seed=233) - 0.5) * 0.5))
    return rgb


def feet(x, y):
    t = 2.6 + (fbm(x * 0.18, y * 0.18, 0, seed=241) - 0.5) * 2.0
    if (y + int(2 * math.sin(x / 5.0))) % 9 == 0:
        t += 1.8                                             # creases across the toes
    if _rnd(x, y, 243) < 0.04:
        t = 6                                                # grit
    return tone(FOOT, t)


def head(x, y):
    """Porcelain gone to a craze of hairline cracks."""
    t = 2.0 + (fbm(x * 0.09, y * 0.09, 0, seed=251) - 0.5) * 2.2
    c = vnoise(x * 0.22, y * 0.22, 0, seed=253)
    if abs(c - 0.5) < 0.022:
        t = 5.4                                              # the craze
    if abs(vnoise(x * 0.5, y * 0.5, 0, seed=255) - 0.5) < 0.012:
        t = 4.6
    return tone(PORCELAIN, t)


def rays(x, y):
    t = 2.0 + (vnoise(x * 0.3, y * 0.3, 0, seed=261) - 0.5) * 2.0
    if _rnd(x, y, 263) < 0.05:
        t = 4.5                                              # flecks
    return tone(RAY, t)


TILES = {
    (0, 0): limb_bone,       # upper arms and thighs
    (0, 64): robe,           # torso and upper torso
    (192, 0): wraps,         # torso and upper torso
    (0, 192): rays,          # the sun rays
    (64, 0): hands,
    (128, 64): shin_bone,
    (192, 64): feet,
    (256, 0): belt,          # pelvis
    (256, 64): neck,
    (320, 0): sinew,         # forearm and shin cords
    (320, 64): head,         # the head behind the face
    (384, 0): fingers,
    (448, 0): forearm,
}


def _protected(im):
    """Hash of everything this must not touch: the face, the free quadrant, and every tile
    in the top half that is not one of his."""
    h = hashlib.sha256()
    h.update(im.crop((256, 256, 512, 512)).tobytes())
    h.update(im.crop((0, 256, 256, 512)).tobytes())
    for ty in range(0, 256, TILE):
        for tx in range(0, 512, TILE):
            if (tx, ty) not in TILES:
                h.update(im.crop((tx, ty, tx + TILE, ty + TILE)).tobytes())
    return h.hexdigest()


def paint():
    im = Image.open(ATLAS).convert("RGBA")
    assert hashlib.sha256(im.crop((256, 256, 512, 512)).tobytes()).hexdigest() == FACE_HASH, \
        "the face quadrant does not match its recorded hash"
    before = _protected(im)
    px = im.load()
    for (ox, oy), fn in TILES.items():
        for y in range(TILE):
            for x in range(TILE):
                px[ox + x, oy + y] = fn(x, y) + (255,)
    assert _protected(im) == before, "something outside the Sun Man's tiles moved — refusing to write"
    im.save(ATLAS)
    print(f"repainted the Sun Man's {len(TILES)} tiles; face, free quadrant and every other tile "
          f"unchanged ({before[:16]})")


if __name__ == "__main__":
    paint()
