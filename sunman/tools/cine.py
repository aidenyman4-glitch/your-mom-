"""The camera. A perspective renderer with a tape grade, built for one shot in particular:
the Sun Man closing the distance.

The earlier renderer was orthographic, which is the wrong lens for this creature entirely.
A 73-block thing is only frightening if you can feel how far away it is and how fast that
is changing, and orthographic projection destroys exactly that information — the silhouette
is the same size at 50 blocks as at 5. So everything here is perspective, from a camera at
a player's eye height (1.62), with a ground plane and a treeline for scale.

The grade is not decoration either. The datapack keeps `fx/overlay_vhs` equipped as a real
`camera_overlay`, so a scan-lined, bloomed, torn frame IS the player's view. Degrading the
tape as the creature gets nearer is the same move the mod makes with sound.
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import palette as pal

NEAR = 0.08
def _font():
    import os
    for f in ("/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
              "C:/Windows/Fonts/courbd.ttf"):
        if os.path.exists(f):
            return f
    raise FileNotFoundError("no monospace bold font found for the burn-in text")


FONT = _font()

# _corners order: i = 4*dx + 2*dy + dz
FACES = [
    ((0, 2, 6, 4), (0, 0, -1), "north"),
    ((1, 5, 7, 3), (0, 0, 1), "south"),
    ((0, 1, 3, 2), (-1, 0, 0), "west"),
    ((4, 6, 7, 5), (1, 0, 0), "east"),
    ((0, 4, 5, 1), (0, -1, 0), "down"),
    ((2, 3, 7, 6), (0, 1, 0), "up"),
]
LIGHT = (-0.42, 0.74, 0.52)


def _norm(v):
    l = math.sqrt(sum(c * c for c in v)) or 1.0
    return [c / l for c in v]


LIGHT = _norm(LIGHT)


# ====================================================================== subjects

class Subject:
    """Wraps either rig (the Sun Man) or a tiers.Creature behind one interface."""

    def __init__(self, solve_grounded, geometry, bone_order, corners, colour):
        self.solve_grounded = solve_grounded
        self.geometry = geometry
        self.bone_order = bone_order
        self.corners = corners
        self.colour = colour


def sunman_subject():
    import rig
    def colour(cube, face):
        return cube["faces"].get(face)
    return Subject(rig.solve_grounded_m, rig.GEOMETRY, rig.BONE_ORDER, rig.cube_corners, colour)


def creature_subject(creature):
    """Face colours sampled from the painted skin through each face's UV rect, the same way
    the Sun Man's are — so a render shows the creature the pack actually ships."""
    import rig
    from paint_tiers import layout
    sample = rig._atlas_colours()
    placed = layout()
    table = {}
    for bone, cubes in creature.GEOMETRY.items():
        for i, cube in enumerate(cubes):
            faces = placed[(creature.name, bone, i)]["faces"]
            table[id(cube)] = {d: sample([v / 32.0 for v in rect]) or pal.MATS[cube["mat"]]
                               for d, rect in faces.items()}

    def colour(cube, face):
        return table[id(cube)][face]
    return Subject(creature.solve_grounded_m, creature.GEOMETRY, creature.BONE_ORDER,
                   creature._cube_corners, colour)


def collect(subject, pose, offset=(0.0, 0.0, 0.0)):
    """World-space quads for one pose: (4 points, rgb or None for the face art, emission)."""
    sol = subject.solve_grounded(pose)
    out = []
    for bone in subject.bone_order:
        cubes = subject.geometry.get(bone)
        if not cubes:
            continue
        pos, m = sol[bone]
        import rig
        for cube in cubes:
            pts = [tuple(pos[i] + rig.mat_vec(m, p)[i] + offset[i] for i in range(3))
                   for p in subject.corners(cube)]
            for idx, nrm, name in FACES:
                col = subject.colour(cube, name)
                if col is None:                      # the starburst cutout
                    if nrm[2] <= 0:
                        continue
                    out.append(([pts[i] for i in idx], None, 0))
                    continue
                n = _norm(rig.mat_vec(m, nrm))
                lam = max(0.0, sum(n[i] * LIGHT[i] for i in range(3)))
                shade = 0.38 + 0.62 * lam
                emit = cube.get("emit", 0)
                if emit:
                    shade = max(shade, 0.78 + emit / 60.0)
                out.append(([pts[i] for i in idx],
                            tuple(min(255, int(c * shade)) for c in col), emit))
    return out


# ====================================================================== the world

def treeline(seed, count=46, near=14.0, far=120.0, road=9.0):
    """Spruce silhouettes down both sides of a road. These exist purely for scale: without
    something of known size in frame, a 73-block creature reads as a 7-block one."""
    rng = random.Random(seed)
    quads = []
    for _ in range(count):
        z = rng.uniform(near, far)
        x = rng.uniform(road, road + 26.0) * rng.choice((-1, 1))
        h = rng.uniform(7.0, 17.0) * (0.7 + z / far)
        w = h * rng.uniform(0.10, 0.17)
        col = pal.TREE if rng.random() < 0.7 else pal.TREE_LIT
        # trunk, then three tapering tiers
        quads += _box_quads((x - w * 0.10, 0.0, z - w * 0.10),
                            (w * 0.20, h * 0.34, w * 0.20), col)
        for i in range(3):
            t = i / 3.0
            ww = w * (1.0 - t * 0.55)
            y = h * (0.26 + t * 0.26)
            quads += _box_quads((x - ww, y, z - ww), (ww * 2, h * 0.30, ww * 2),
                                tuple(int(c * (0.85 + 0.12 * i)) for c in col))
    return quads


def _box_quads(origin, size, col):
    ox, oy, oz = origin
    w, h, d = size
    pts = [(ox + dx, oy + dy, oz + dz)
           for dx in (0, w) for dy in (0, h) for dz in (0, d)]
    out = []
    for idx, nrm, _name in FACES:
        lam = max(0.0, sum(nrm[i] * LIGHT[i] for i in range(3)))
        shade = 0.62 + 0.38 * lam
        out.append(([pts[i] for i in idx], tuple(int(c * shade) for c in col), 0))
    return out


def ground_quads(reach=320.0):
    """One huge plate at y=0, split into depth bands so fog can grade across it."""
    out = []
    edges = [0.0, 3.0, 7.0, 13.0, 22.0, 36.0, 58.0, 95.0, 150.0, reach]
    for a, b in zip(edges, edges[1:]):
        t = min(1.0, a / 120.0)
        col = tuple(int(pal.GROUND[i] + (pal.GROUND_FAR[i] - pal.GROUND[i]) * t)
                    for i in range(3))
        out.append(([(-reach, 0.0, a), (reach, 0.0, a), (reach, 0.0, b), (-reach, 0.0, b)],
                    col, 0))
    return out


# ====================================================================== camera

class Cam:
    def __init__(self, eye, target, fov=70.0, roll=0.0):
        self.eye = eye
        self.fov = fov
        f = _norm([target[i] - eye[i] for i in range(3)])
        r = _norm([f[2], 0.0, -f[0]])
        u = [f[1] * r[2] - f[2] * r[1], f[2] * r[0] - f[0] * r[2], f[0] * r[1] - f[1] * r[0]]
        if roll:
            c, s = math.cos(math.radians(roll)), math.sin(math.radians(roll))
            r, u = ([r[i] * c + u[i] * s for i in range(3)],
                    [u[i] * c - r[i] * s for i in range(3)])
        self.basis = (r, u, f)

    def view(self, p):
        r, u, f = self.basis
        d = [p[i] - self.eye[i] for i in range(3)]
        return (sum(d[i] * r[i] for i in range(3)),
                sum(d[i] * u[i] for i in range(3)),
                sum(d[i] * f[i] for i in range(3)))


def clip_near(poly):
    """Sutherland-Hodgman against z >= NEAR. Without this, a leg passing the camera in the
    charge shot projects through infinity and smears across the whole frame."""
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        da, db = a[2] - NEAR, b[2] - NEAR
        if da >= 0:
            out.append(a)
        if (da >= 0) != (db >= 0):
            t = da / (da - db)
            out.append(tuple(a[k] + (b[k] - a[k]) * t for k in range(3)))
    return out


def _perspective_coeffs(dst, src):
    """Coefficients mapping output pixels back into the art, so the face lands on its real
    projected quad instead of a bounding box."""
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    try:
        return np.linalg.solve(np.array(A, dtype=np.float64), np.array(B, dtype=np.float64))
    except np.linalg.LinAlgError:
        return None


# ====================================================================== raster

def rasterise(quads, cam, size, fog_dist=78.0, art=None, sky=None, lamp=0.0,
              lamp_reach=9.0):
    W, H = size
    f = (H * 0.5) / math.tan(math.radians(cam.fov) * 0.5)
    cx, cy = W * 0.5, H * 0.5

    prepared = []
    for pts, col, emit in quads:
        vp = clip_near([cam.view(p) for p in pts])
        if len(vp) < 3:
            continue
        depth = sum(p[2] for p in vp) / len(vp)
        scr = [(cx + p[0] / p[2] * f, cy - p[1] / p[2] * f) for p in vp]
        prepared.append((depth, scr, col, emit))
    prepared.sort(key=lambda q: -q[0])

    hi, lo_sky = sky or (pal.SKY_HIGH, pal.SKY_LOW)
    img = Image.new("RGB", size, hi)
    _sky(img, hi, lo_sky)
    d = ImageDraw.Draw(img)
    glow = Image.new("L", size, 0)
    gd = ImageDraw.Draw(glow)

    for depth, scr, col, emit in prepared:
        t = 1.0 - math.exp(-max(0.0, depth) / fog_dist)
        if col is None:
            if art is not None and len(scr) == 4:
                _paste_art(img, art, scr, t)
                gd.polygon(scr, fill=int(150 * (1 - t)))
            continue
        if lamp:
            # A point light at the lens. Aiden's road references are lit by headlights:
            # the creature is pure black until it is close, then it is suddenly a surface.
            b = 1.0 + lamp / (1.0 + (depth / lamp_reach) ** 3)
            col = tuple(min(255, int(c * b)) for c in col)
        c = tuple(int(col[i] + (pal.FOG[i] - col[i]) * t) for i in range(3))
        d.polygon(scr, fill=c)
        if emit:
            v = int(min(255, 40 + emit * 14) * (1 - t))
            xs = [q[0] for q in scr]; ys = [q[1] for q in scr]
            if max(xs) - min(xs) < 3.0 or max(ys) - min(ys) < 3.0:
                # Two lit eyes at forty blocks are a sub-pixel quad and vanish, which loses
                # the one thing every night reference has in it. Give the glow mask a floor
                # so the eyes stay visible at any distance, the way a light source does.
                cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
                gd.ellipse([cx - 1.6, cy - 1.6, cx + 1.6, cy + 1.6], fill=v)
            else:
                gd.polygon(scr, fill=v)
    return img, glow


def _sky(img, high=None, low=None):
    """A vertical wash, drawn once per frame. Flat sky makes the fog read as a bug."""
    high = high or pal.SKY_HIGH
    low = low or pal.SKY_LOW
    W, H = img.size
    d = ImageDraw.Draw(img)
    for y in range(0, H, 2):
        t = y / H
        d.rectangle([0, y, W, y + 2],
                    fill=tuple(int(high[i] + (low[i] - high[i]) * t) for i in range(3)))


def _paste_art(img, art, scr, fog_t):
    xs = [p[0] for p in scr]; ys = [p[1] for p in scr]
    if max(xs) - min(xs) < 2 or max(ys) - min(ys) < 2:
        return
    src = [(0, 0), (art.width, 0), (art.width, art.height), (0, art.height)]
    co = _perspective_coeffs([(int(p[0]), int(p[1])) for p in scr], src)
    if co is None:
        return
    warped = art.transform(img.size, Image.PERSPECTIVE, co, Image.BILINEAR)
    if fog_t > 0.01:
        veil = Image.new("RGBA", img.size, pal.FOG + (int(255 * fog_t),))
        warped = Image.alpha_composite(warped, Image.composite(
            veil, Image.new("RGBA", img.size, (0, 0, 0, 0)), warped.split()[3]))
    img.paste(warped, (0, 0), warped)


# ====================================================================== the grade

_VIG = {}


def _vignette(size):
    if size not in _VIG:
        W, H = size
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        _VIG[size] = np.clip(1.14 - 0.44 * r ** 2.2, 0.0, 1.0)[..., None]
    return _VIG[size]


def grade(img, glow, intensity, rng, bloom=1.0, mono=False):
    """intensity 0..1 drives how badly the tape is holding together."""
    if bloom > 0:
        g = glow.filter(ImageFilter.GaussianBlur(9 + 10 * bloom))
        halo = Image.new("RGB", img.size, (255, 246, 226))
        img = Image.composite(Image.blend(img, halo, min(0.92, 0.72 * bloom)), img, g)

    a = np.asarray(img, dtype=np.float32)
    H, W, _ = a.shape
    if mono:
        a[:] = (a @ np.array([0.30, 0.59, 0.11], dtype=np.float32))[..., None]

    # chroma misregistration: the single most legible "this is a tape" cue
    shift = int(round(1 + 4 * intensity))
    if shift:
        a[..., 0] = np.roll(a[..., 0], shift, axis=1)
        a[..., 2] = np.roll(a[..., 2], -shift, axis=1)

    a *= _vignette((W, H))
    # Grain in 2x2 cells, not per pixel. Per-pixel noise is incompressible (it tripled the
    # GIF), and at this scale it reads as sensor noise; tape grain is chunkier than that.
    cell = rng.normal(0.0, 2.6 + 6.0 * intensity,
                      (H // 2 + 1, W // 2 + 1, 1)).astype(np.float32)
    a += np.repeat(np.repeat(cell, 2, axis=0), 2, axis=1)[:H, :W]
    a[0::3, :, :] *= 0.87 - 0.09 * intensity          # scanlines

    # head-tracking tear: a band of rows shoved sideways and dimmed
    if rng.random() < 0.30 + 0.5 * intensity:
        y0 = int(rng.integers(0, H - 14))
        h = int(rng.integers(5, 16 + int(22 * intensity)))
        off = int(rng.integers(-22, 22) * (0.4 + intensity))
        a[y0:y0 + h] = np.roll(a[y0:y0 + h], off, axis=1) * 0.82

    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def burn_in(img, label, note, idx, total, tape="REC", flash=0.0):
    if flash > 0:
        # Multiplicative, not additive. Adding light to every pixel lifts the sky as much
        # as the creature and the frame turns into a flat grey card; multiplying blows out
        # what was already lit and leaves the dark dark, which is what a flash does.
        a = np.asarray(img, dtype=np.float32) * (1.0 + 3.2 * flash)
        a *= np.array([1.0, 0.985, 0.94], dtype=np.float32)
        img.paste(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)), (0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    W, H = img.size
    big = ImageFont.truetype(FONT, 13)
    small = ImageFont.truetype(FONT, 11)

    d.rectangle([0, 0, W, 26], fill=(8, 7, 11, 215))
    d.rectangle([0, H - 24, W, H], fill=(8, 7, 11, 200))
    d.ellipse([10, 9, 19, 18], fill=pal.REC if idx % 2 == 0 else (72, 20, 20))
    d.text((25, 7), tape, font=big, fill=pal.INK)
    d.text((W - 86, 7), f"{idx + 1:02d}:{total:02d}", font=big, fill=(198, 70, 70))
    d.text((10, H - 18), label.upper(), font=big, fill=pal.INK)
    x = 10 + int(d.textlength(label.upper(), font=big)) + 14
    while note and x + d.textlength(note, font=small) > W - 8:
        note = note[:-1]
    d.text((x, H - 17), note, font=small, fill=(118, 114, 126))
    return img


# ====================================================================== output

def save_gif(path, imgs, ms, colors=160):
    """One palette for the whole clip. Per-frame adaptive palettes make heavy grain crawl,
    which reads as a GIF artefact instead of as tape.

    The sample frames are chosen by brightness, not by position: these clips are mostly
    very dark with a few blown-out insert frames, and an evenly-spaced sample misses the
    bright end entirely — which quantised the white face plate to a flat olive field.
    """
    lum = [float(np.asarray(im, dtype=np.float32).mean()) for im in imgs]
    order = sorted(range(len(imgs)), key=lambda i: lum[i])
    # ...and enough of them: with too few, a grey creature has no neutral greys to land on
    # and quantises to whatever tint the sky frames happened to contribute
    picks = {order[0], order[-1]}
    picks.update(order[i] for i in np.linspace(0, len(order) - 1, 12).astype(int))
    picks = sorted(picks)
    strip = Image.new("RGB", (imgs[0].width, imgs[0].height * len(picks)))
    for i, k in enumerate(picks):
        strip.paste(imgs[k], (0, i * imgs[0].height))
    master = strip.quantize(colors=colors, method=Image.MEDIANCUT)
    frames = [im.quantize(palette=master, dither=Image.NONE) for im in imgs]
    durations = ms if isinstance(ms, list) else [ms] * len(frames)
    path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, optimize=True, disposal=1)
    return path


def doorway(width=1.9, height=2.6, thick=0.26, z=-0.35):
    """A ruined door frame to stand something inside. The Locust's whole horror is being
    found standing in a house, and a silhouette with nothing around it loses that."""
    out = []
    for x in (-width / 2 - thick, width / 2):
        out += _box_quads((x, 0.0, z), (thick, height, thick), (26, 23, 20))
    out += _box_quads((-width / 2 - thick, height, z), (width + thick * 2, thick * 1.3, thick),
                      (31, 27, 23))
    out += _box_quads((-width / 2 - thick, 0.0, z - 0.6), (width + thick * 2, height * 1.35, 0.3),
                      (13, 12, 14))            # the dark of the room behind it
    return out


def wall(z=-0.7, span=9.0, height=7.0):
    out = _box_quads((-span / 2, 0.0, z), (span, height, 0.4), (27, 25, 26))
    for i in range(7):                          # a few displaced blocks, so it reads as built
        out += _box_quads((-span / 2 + 0.6 + i * 1.2, 0.3 + (i % 3) * 1.7, z + 0.38),
                          (1.0, 0.5, 0.1), (20, 19, 20))
    return out


def road(width=6.4, far=620.0):
    """Ground AND track in one mesh. Two of Aiden's references are the same photograph of
    something standing in a road, and the road is doing half the work in them: it gives the
    eye a vanishing point to measure the approach against.

    This replaces ground_quads() rather than sitting on top of it. Two coplanar meshes sorted
    by average depth interleave — the painter's algorithm has no way to break the tie — and
    the track came out as a bright trapezoid floating over the field.
    """
    out = []
    edges = [0.0, 2.5, 5.0, 9.0, 15.0, 25.0, 42.0, 70.0, 115.0, 200.0, far]
    w = width / 2
    for a, b in zip(edges, edges[1:]):
        t = min(1.0, a / 100.0)

        def strip(x0, x1, base):
            col = tuple(int(c + (pal.GROUND_FAR[i] - c) * t) for i, c in enumerate(base))
            out.append(([(x0, 0.0, a), (x1, 0.0, a), (x1, 0.0, b), (x0, 0.0, b)], col, 0))

        strip(-w, w, (34, 32, 28))                 # the track
        strip(-w - 2.6, -w, (24, 26, 20))          # verges
        strip(w, w + 2.6, (24, 26, 20))
        strip(-900.0, -w - 2.6, pal.GROUND)        # field either side
        strip(w + 2.6, 900.0, pal.GROUND)
    return out
