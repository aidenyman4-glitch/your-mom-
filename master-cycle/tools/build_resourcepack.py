#!/usr/bin/env python3
"""Generate the Master Cycle resource pack: 3D model, textures, item definitions,
synthesized sounds and pack icon.

Everything under master-cycle/resourcepack/ is produced by this script, so the
pack can be rebuilt (or tweaked) without Blockbench:

    python3 master-cycle/tools/build_resourcepack.py

Needs Pillow + numpy, and ffmpeg (with libvorbis) for the .ogg sounds.
"""

import json
import math
import random
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from model_check import zfight_pairs

ROOT = Path(__file__).resolve().parent.parent
RP = ROOT / "resourcepack"
MC = RP / "assets" / "minecraft"
NS = RP / "assets" / "mastercycle"

# Target: Minecraft Java 26.3 (resource pack format 97.1). Formats have a
# minor number since 1.21.9; a bare integer means "<major>.0", which would
# exclude 26.3's 97.1, so the range is written out as [major, minor] pairs.
RESOURCE_FORMAT = 97
RESOURCE_MIN = [97, 0]
RESOURCE_MAX = [97, 1]

# The model with element names kept, read by rider_fit.py (not shipped).
NAMED_MODEL = ROOT / "tools" / ".cache" / "custom_master_cycle.named.json"

# CustomModelData values (component: custom_model_data={floats:[...]})
CMD_CYCLE = 7701
CMD_SLATE = 7702

# ---------------------------------------------------------------- palette ---
CHARCOAL = (42, 42, 47)
CHARCOAL_HI = (58, 58, 65)
CHARCOAL_LO = (30, 30, 34)
GOLD = (196, 154, 92)
GOLD_HI = (226, 192, 132)
GOLD_LO = (128, 92, 52)
CYAN = (79, 227, 255)
CYAN_HI = (200, 250, 255)
ORANGE = (255, 166, 58)
RUBBER = (30, 30, 33)
RUBBER_HI = (48, 48, 53)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def jitter(rgb, rng, amount=6):
    d = rng.randint(-amount, amount)
    return tuple(max(0, min(255, c + d)) for c in rgb)


# --------------------------------------------------------------- textures ---
def tex_body(rng):
    """Dark Sheikah stone plate with gold filigree channels."""
    im = Image.new("RGB", (32, 32))
    px = im.load()
    for y in range(32):
        for x in range(32):
            px[x, y] = jitter(CHARCOAL, rng, 4)
    d = ImageDraw.Draw(im)
    # Sweeping filigree: two interlocking spirals and a running border line.
    d.arc((3, 4, 17, 18), 200, 470, fill=GOLD, width=1)
    d.arc((7, 8, 13, 14), 30, 300, fill=GOLD, width=1)
    d.arc((15, 13, 30, 28), 20, 290, fill=GOLD, width=1)
    d.arc((19, 17, 26, 24), 180, 450, fill=GOLD, width=1)
    d.line((0, 29, 12, 29), fill=GOLD_LO)
    d.line((12, 29, 15, 26), fill=GOLD_LO)
    d.line((17, 2, 31, 2), fill=GOLD_LO)
    d.line((0, 2, 4, 2), fill=GOLD_LO)
    # Cyan Sheikah node in the middle of a spiral.
    d.point([(10, 11), (22, 20)], fill=CYAN)
    # Bevel highlight on the top edge so blocks read as plates.
    for x in range(32):
        px[x, 0] = CHARCOAL_HI
        px[x, 31] = CHARCOAL_LO
    return im


def tex_trim(rng):
    """Bronze/tan ornamental trim with carved grooves."""
    im = Image.new("RGB", (32, 32))
    px = im.load()
    for y in range(32):
        for x in range(32):
            px[x, y] = jitter(GOLD, rng, 7)
    d = ImageDraw.Draw(im)
    d.arc((2, 2, 16, 16), 0, 300, fill=GOLD_LO, width=1)
    d.arc((6, 6, 12, 12), 120, 420, fill=GOLD_LO, width=1)
    d.arc((16, 16, 30, 30), 180, 480, fill=GOLD_LO, width=1)
    d.arc((20, 20, 26, 26), 300, 600, fill=GOLD_LO, width=1)
    d.line((16, 4, 30, 4), fill=GOLD_LO)
    d.line((2, 26, 14, 26), fill=GOLD_LO)
    for x in range(32):
        px[x, 0] = GOLD_HI
        px[x, 31] = GOLD_LO
    for y in range(32):
        px[0, y] = GOLD_HI
    return im


def tex_tread(rng):
    im = Image.new("RGB", (32, 32))
    px = im.load()
    for y in range(32):
        for x in range(32):
            px[x, y] = jitter(RUBBER, rng, 3)
    d = ImageDraw.Draw(im)
    # Chunky off-road chevron lugs.
    for row in range(0, 32, 8):
        d.polygon([(2, row + 1), (14, row + 4), (2, row + 7)], fill=RUBBER_HI)
        d.polygon([(29, row + 1), (17, row + 4), (29, row + 7)], fill=RUBBER_HI)
    return im


def tex_seat(rng):
    im = Image.new("RGB", (32, 32))
    px = im.load()
    base = (40, 34, 36)
    for y in range(32):
        for x in range(32):
            px[x, y] = jitter(base, rng, 4)
    for y in range(2, 30, 3):
        px[2, y] = GOLD_LO
        px[29, y] = GOLD_LO
    for x in range(4, 28, 3):
        px[x, 16] = (52, 46, 48)
    return im


def tex_metal(rng):
    im = Image.new("RGB", (32, 32))
    px = im.load()
    base = (56, 59, 66)
    for y in range(32):
        for x in range(32):
            px[x, y] = jitter(base, rng, 5)
    d = ImageDraw.Draw(im)
    d.rectangle((3, 3, 28, 28), outline=(40, 42, 48))
    d.line((3, 16, 28, 16), fill=(40, 42, 48))
    d.rectangle((14, 7, 17, 10), fill=CYAN)
    d.rectangle((14, 21, 17, 24), fill=ORANGE)
    return im


def tex_flat(rgb, glow=False):
    im = Image.new("RGB", (16, 16), rgb)
    if glow:
        # Brighter core so emissive parts read as light sources.
        d = ImageDraw.Draw(im)
        d.rectangle((4, 4, 11, 11), fill=tuple(min(255, c + 40) for c in rgb))
        d.rectangle((6, 6, 9, 9), fill=CYAN_HI if rgb == CYAN else (255, 230, 170))
    return im


def sheikah_eye(draw, cx, cy, s, color, pupil):
    """Draw the Sheikah eye: eye outline, pupil, three lashes and a teardrop."""
    w, h = 1.0 * s, 0.55 * s
    pts_top = [(cx - w + 2 * w * t, cy - h * math.sin(math.pi * t)) for t in np.linspace(0, 1, 24)]
    pts_bot = [(cx + w - 2 * w * t, cy + 0.65 * h * math.sin(math.pi * t)) for t in np.linspace(0, 1, 24)]
    lw = max(1, int(s * 0.12))
    draw.line(pts_top + pts_bot + [pts_top[0]], fill=color, width=lw, joint="curve")
    r = s * 0.28
    draw.ellipse((cx - r, cy - r * 0.9, cx + r, cy + r * 0.9), fill=pupil)
    for ang in (-35, 0, 35):
        a = math.radians(ang - 90)
        x0, y0 = cx + math.cos(a) * h * 1.25, cy + math.sin(a) * h * 1.25
        x1, y1 = cx + math.cos(a) * h * 1.9, cy + math.sin(a) * h * 1.9
        draw.line((x0, y0, x1, y1), fill=color, width=lw)
    ty = cy + h * 0.9
    draw.polygon([(cx, ty), (cx - s * 0.18, ty + s * 0.45), (cx, ty + s * 0.65), (cx + s * 0.18, ty + s * 0.45)], fill=color)


def tex_emblem():
    """The Sheikah eye, lit, for the side panels."""
    im = Image.new("RGB", (32, 32), CHARCOAL_LO)
    d = ImageDraw.Draw(im)
    big = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    sheikah_eye(ImageDraw.Draw(big), 64, 56, 38, CYAN + (255,), CYAN_HI + (255,))
    big = big.resize((30, 30), Image.LANCZOS)
    im.paste(big, (1, 1), big)
    d.rectangle((0, 0, 31, 31), outline=GOLD_LO)
    return im


def tex_slate():
    """Hand-held Sheikah Slate item sprite (32x32)."""
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Body
    d.rounded_rectangle((3, 6, 28, 26), radius=3, fill=CHARCOAL, outline=GOLD_LO)
    d.rounded_rectangle((4, 7, 27, 25), radius=2, outline=GOLD)
    # Screen
    d.rectangle((8, 9, 23, 22), fill=(22, 38, 46))
    # Side grips
    d.rectangle((3, 10, 5, 22), fill=GOLD_LO)
    d.rectangle((26, 10, 28, 22), fill=GOLD_LO)
    # Sheikah eye on the screen
    eye = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    sheikah_eye(ImageDraw.Draw(eye), 64, 52, 34, CYAN + (255,), CYAN_HI + (255,))
    eye = eye.resize((14, 14), Image.LANCZOS)
    im.alpha_composite(eye, (9, 8))
    # Orange indicator
    d.point([(25, 8), (6, 24)], fill=ORANGE)
    return im


def pack_icon():
    im = Image.new("RGBA", (128, 128), CHARCOAL + (255,))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 4, 123, 123), radius=14, outline=GOLD, width=4)
    d.rounded_rectangle((12, 12, 115, 115), radius=10, outline=GOLD_LO, width=2)
    sheikah_eye(d, 64, 58, 34, CYAN, CYAN_HI)
    return im


def build_textures():
    rng = random.Random(1337)
    tdir = MC / "textures" / "item" / "master_cycle"
    tdir.mkdir(parents=True, exist_ok=True)
    tex_body(rng).save(tdir / "body.png")
    tex_trim(rng).save(tdir / "trim.png")
    tex_tread(rng).save(tdir / "tread.png")
    tex_seat(rng).save(tdir / "seat.png")
    tex_metal(rng).save(tdir / "metal.png")
    tex_flat(RUBBER).save(tdir / "tire_side.png")
    tex_flat(GOLD).save(tdir / "gold.png")
    tex_flat(CYAN, glow=True).save(tdir / "glow_cyan.png")
    tex_flat(ORANGE, glow=True).save(tdir / "glow_orange.png")
    tex_emblem().save(tdir / "eye.png")
    tex_slate().save(MC / "textures" / "item" / "sheikah_slate.png")
    pack_icon().save(RP / "pack.png")


# ------------------------------------------------------------------ model ---
# Model space: 1 unit = 1/16 of the item. Front of the cycle points NORTH
# (-Z), which is "forward" for an item worn in the head slot. X=8 is the
# centre line, Y=-5 is where the tyres touch the ground.

ELEMENTS = []


def _uv(du, dv):
    return [0, 0, round(min(abs(du), 16), 3), round(min(abs(dv), 16), 3)]


def box(frm, to, tex, rot=None, light=None, faces=None, name=None, full_uv=()):
    """Add a cuboid. `faces` may override the texture per face; faces listed in
    `full_uv` show the whole texture instead of a slice the size of the face,
    which is what an emblem or a decal wants."""
    (x0, y0, z0), (x1, y1, z1) = frm, to
    dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
    sizes = {
        "north": (dx, dy), "south": (dx, dy),
        "east": (dz, dy), "west": (dz, dy),
        "up": (dx, dz), "down": (dx, dz),
    }
    face_tex = {f: tex for f in sizes}
    if faces:
        face_tex.update(faces)
    el = {
        "from": [round(v, 3) for v in frm],
        "to": [round(v, 3) for v in to],
        "faces": {f: {"uv": [0, 0, 16, 16] if f in full_uv else _uv(*sizes[f]),
                      "texture": "#" + face_tex[f]} for f in sizes},
    }
    if name:
        el["name"] = name
    if rot:
        axis, angle, origin = rot
        if abs(angle) > 1e-6:
            el["rotation"] = {"origin": [round(v, 3) for v in origin], axis: round(angle, 3)}
    if light:
        el["light_emission"] = light
    ELEMENTS.append(el)


# Faces that point the same way, lie in the same plane and overlap z-fight
# (flicker). Overlapping slabs of a disc would all put their side faces on one
# plane, so every slab is pushed out STEP further than the previous one. 0.05
# model units is ~0.003 blocks in game: invisible, but far more than depth-buffer
# precision needs to keep the faces apart at normal viewing distances.
STEP = 0.05


def disc(cz, cy, r, x0, x1, n, tex, side_tex, name, off, light=None):
    """A polygonal disc around the X axis made of n overlapping rotated slabs
    (gives a 2n-sided wheel silhouette). Slab k sticks out `off + k*STEP`
    beyond x0/x1 on each side; returns the offset of the outermost slab."""
    edge = 2 * r * math.tan(math.pi / (2 * n)) * 1.04
    for k in range(n):
        ang = k * 180.0 / n
        if ang > 90:
            ang -= 180
        o = off + k * STEP
        box(
            (x0 - o, cy - r, cz - edge / 2), (x1 + o, cy + r, cz + edge / 2), tex,
            rot=("x", ang, (8, cy, cz)), light=light,
            faces={"east": side_tex, "west": side_tex}, name=f"{name}_{k}",
        )
    return off + (n - 1) * STEP


def wheel(cz, cy, R, x0, x1, name):
    # Tyre: 16-sided, treaded rim, flat rubber sidewall.
    o = disc(cz, cy, R, x0, x1, 12, "tread", "tire_side", f"{name}_tyre", off=0)
    # Concentric hub layers, each in its own depth band further out from the
    # tyre wall: gold rim band, dark recess with ornate spokes, glowing orange
    # ring, gold hub and a cyan Sheikah core.
    o = disc(cz, cy, R * 0.68, x0, x1, 4, "gold", "gold", f"{name}_rim", off=o + STEP)
    o = disc(cz, cy, R * 0.55, x0, x1, 4, "tire_side", "tire_side", f"{name}_recess", off=o + STEP)
    spoke_off = o + STEP
    for i, ang in enumerate((0, 60, -60)):
        so = spoke_off + i * STEP
        for side, (sx0, sx1) in (("l", (x0 - so - 0.15, x0 - so)), ("r", (x1 + so, x1 + so + 0.15))):
            box((sx0, cy - R * 0.6, cz - 0.6), (sx1, cy + R * 0.6, cz + 0.6), "gold",
                rot=("x", ang, (8, cy, cz)), name=f"{name}_spoke_{side}{i}")
    o = spoke_off + 2 * STEP + 0.15
    o = disc(cz, cy, R * 0.36, x0, x1, 4, "glow_orange", "glow_orange", f"{name}_ring", off=o + STEP, light=15)
    o = disc(cz, cy, R * 0.27, x0, x1, 4, "gold", "gold", f"{name}_hub", off=o + STEP)
    disc(cz, cy, R * 0.14, x0, x1, 2, "glow_cyan", "glow_cyan", f"{name}_core", off=o + STEP, light=15)


def fender(cz, cy, r, x0, x1, angles, name):
    """A curved mudguard: overlapping slabs tangent to a circle around the
    wheel axle. Like the discs, each slab is STEP wider than the last so the
    overlapping side faces never share a plane."""
    for k, ang in enumerate(angles):
        o = k * STEP
        box((x0 - o, cy + r, cz - 1.75), (x1 + o, cy + r + 0.75, cz + 1.75), "trim",
            rot=("x", ang, (8, cy, cz)), name=f"{name}{k}")


def plume(z, y, x0, x1, segments, name):
    """A chain of thin gold segments rising backwards, each starting where the
    previous one ends. segments = (length, elevation in degrees, thickness);
    every segment narrows by 0.1 per side so joints never share a face plane."""
    for k, (length, elev, thick) in enumerate(segments):
        n = k * 0.1
        box((x0 + n, y, z - thick / 2), (x1 - n, y + length, z + thick / 2),
            "gold" if k == len(segments) - 1 else "trim",
            rot=("x", 90 - elev, (8, y, z)), name=f"{name}{k}")
        a = math.radians(elev)
        back = min(0.3, length * 0.1)  # overlap the next segment slightly
        z += (length - back) * math.cos(a)
        y += (length - back) * math.sin(a)


def mirror_x(frm, to):
    """Return the box mirrored across the centre line x=8."""
    return (16 - to[0], frm[1], frm[2]), (16 - frm[0], to[1], to[2])


def pair(frm, to, tex, **kw):
    box(frm, to, tex, **kw)
    mf, mt = mirror_x(frm, to)
    box(mf, mt, tex, **kw)


def build_cycle_model():
    ELEMENTS.clear()
    # --- wheels -----------------------------------------------------------
    wheel(cz=-4, cy=2.5, R=7.5, x0=5.25, x1=10.75, name="front")
    wheel(cz=21, cy=2.5, R=7.5, x0=4.75, x1=11.25, name="rear")

    # --- front fork: raked gold struts with coil springs ------------------
    FORK = ("x", 23.5, (8, 8.25, -1.5))
    pair((4.475, 2.0, -2.1), (5.125, 14.5, -0.9), "trim", rot=FORK, name="fork")
    for i in range(4):
        y = 6.0 + i * 1.1
        pair((4.175, y, -2.42), (5.175, y + 0.5, -0.58), "gold", rot=FORK, name=f"fork_coil{i}")
    # front fender: gold arc hugging the top-front of the front tyre
    fender(cz=-4, cy=2.5, r=7.9, x0=6.12, x1=9.88, angles=(-5, -24, -43, -62), name="front_fender")

    # --- engine: glowing Sheikah core wrapped in gold bands ----------------
    box((6, -0.5, 4), (10, 7.5, 15), "metal", name="engine")
    box((5.6, 1.5, 5.5), (10.4, 3.2, 13.5), "glow_cyan", light=15, name="engine_core")
    box((6.4, 4.2, 6), (9.6, 5.2, 13), "glow_orange", light=12, name="engine_coil")
    for i, z in enumerate((6.6, 9.2, 11.8)):
        box((5.45, 1.35, z), (10.55, 3.35, z + 0.5), "gold", name=f"core_band{i}")
    # down tube from head to engine
    box((7, 1.5, -0.5), (9, 12.5, 1.5), "trim", rot=("x", 22.5, (8, 7, 0.5)), name="down_tube")
    # gold "ribcage" between the wheels, like the reference's skeletal frame
    for i, zc in enumerate((4.0, 6.6, 9.2, 11.8)):
        pair((4.2, 0.6, zc - 0.4), (4.5, 7.6, zc + 0.4), "trim", rot=("x", -12, (8, 4, zc)), name=f"rib{i}")
    pair((4.15, 0.35, 3.2), (4.45, 0.95, 12.6), "trim", name="belly_bar")

    # --- torso / tank -----------------------------------------------------
    # The rider sits in Minecraft's fixed riding pose: thighs forward, splayed
    # 18 degrees, arms reaching forward 36 degrees. The tank stays below the
    # thighs, and only a narrow spine rises between the knees.
    box((5, 8.5, 1), (11, 12.4, 10.5), "body", name="tank")
    box((6.7, 11.5, 0.5), (9.3, 14.3, 6.5), "body", rot=("x", -12, (8, 13, 3.5)), name="tank_spine")
    # ornate side panels with Sheikah nodes
    pair((4.6, 7.8, 0), (5.0, 12.2, 16), "body", name="side_panel")
    pair((4.4, 7.2, -0.5), (4.8, 7.9, 16.5), "trim", name="panel_trim")
    for z, y in ((3.5, 10.5), (13.0, 11.0)):
        pair((4.3, y, z), (4.6, y + 0.9, z + 0.9), "glow_cyan", light=15)

    # --- head: a horse-like prow with a unicorn horn ------------------------
    # Narrow (|x - 8| <= 2.3) so the rider's feet pass either side of it.
    box((6.0, 11.0, -4.0), (10.0, 17.0, 1.8), "body", rot=("x", -22, (8, 14, -1)), name="neck")
    HEAD = ("x", -10, (8, 17.2, -5.5))
    box((5.7, 15.2, -8.6), (10.3, 19.2, -2.4), "body", rot=HEAD, name="head")
    pair((5.45, 16.8, -7.2), (5.75, 17.7, -6.0), "glow_cyan", light=15, rot=HEAD, name="eye")
    pair((6.1, 19.0, -4.2), (7.0, 21.4, -3.2), "trim", rot=("x", -15, (6.5, 19, -3.7)), name="ear")
    MUZZLE = ("x", 18, (8, 15.4, -9.9))
    box((6.4, 13.8, -12.2), (9.6, 17.0, -7.6), "body", rot=MUZZLE, name="muzzle")
    box((6.3, 13.6, -12.0), (9.7, 14.2, -7.8), "trim", rot=MUZZLE, name="jaw")
    box((6.9, 14.6, -12.5), (9.1, 15.8, -12.15), "glow_cyan", light=15, rot=MUZZLE, name="headlight")
    HORN = ("x", 12, (8, 19, -7.6))
    box((7.0, 18.0, -8.2), (9.0, 20.0, -7.4), "gold", rot=HORN, name="horn_base")
    box((7.35, 18.4, -14.5), (8.65, 19.6, -7.6), "trim", rot=HORN, name="horn")
    box((7.6, 18.65, -16.0), (8.4, 19.35, -14.3), "gold", rot=HORN, name="horn_tip")
    # gold mane down the back of the neck (leans back)
    for i, (z, y, h) in enumerate(((-5.0, 19.0, 3.0), (-3.0, 18.3, 3.4), (-1.0, 17.4, 3.0), (1.0, 16.4, 2.5), (3.0, 15.4, 2.0))):
        box((7.4, y, z), (8.6, y + h, z + 1.3), "trim", rot=("x", 30, (8, y, z + 0.65)), name=f"mane{i}")
    # handlebar right where the riding pose puts the rider's hands, on a
    # steering stem that comes up between the knees
    box((7.35, 12.2, 7.25), (8.65, 18.75, 8.45), "trim", rot=("x", -8, (8, 12.2, 7.85)), name="stem")
    box((1.5, 18.6, 7.4), (14.5, 19.55, 8.35), "gold", name="handlebar")
    # steering column joining the stem to the neck, so the cockpit reads as one piece
    box((7.5, 17.55, 1.6), (8.5, 18.35, 7.55), "gold", rot=("x", -6, (8, 17.95, 4.6)), name="steering_column")
    pair((0.4, 18.25, 6.95), (2.4, 19.9, 8.8), "seat", name="grip")

    # --- seat & rear body -------------------------------------------------
    box((5.5, 12.5, 10), (10.5, 13.65, 17.5), "seat", name="seat")
    box((5, 10.3, 16), (11, 15.5, 26), "body", name="rear_cowl")
    box((5.4, 14.5, 18), (10.6, 16.6, 27.5), "body", rot=("x", 14, (8, 15.5, 22)), name="rear_cowl_top")
    pair((4.78, 10.1, 16.15), (5.08, 10.7, 26.3), "trim", name="cowl_trim")
    box((6, 14, 16.5), (10, 16, 19.5), "body", name="seat_back")
    pair((4.4, 12.5, 24.5), (5.0, 13.6, 25.6), "glow_orange", light=15, name="tail_light")
    # rear fender: gold arc over the top-back of the rear tyre
    fender(cz=21, cy=2.5, r=7.9, x0=4.6, x1=11.4, angles=(6, 25, 44, 63, 82), name="rear_fender")
    # flowing tail: connected plumes sweeping up and back from the rear cowl
    plume(z=24.0, y=15.6, x0=7.4, x1=8.6, segments=((4.2, 18, 1.3), (3.6, 38, 1.1), (2.8, 62, 0.8)), name="tail")
    plume(z=25.0, y=15.2, x0=6.2, x1=6.9, segments=((3.5, 24, 0.9), (2.8, 48, 0.7)), name="tail_l")
    plume(z=25.0, y=15.2, x0=9.1, x1=9.8, segments=((3.5, 24, 0.9), (2.8, 48, 0.7)), name="tail_r")

    # Sheikah eye emblem, lit, on both side panels
    pair((4.24, 8.6, 5.6), (4.56, 11.6, 10.6), "eye", light=15, name="emblem",
         full_uv=("east", "west"))
    # underglow strip along the belly
    box((6.2, -0.75, 4.5), (9.8, -0.45, 14.5), "glow_cyan", light=15, name="underglow")
    # rear thruster nozzles
    pair((5.6, 11.2, 25.6), (7.4, 13.0, 26.9), "metal", name="nozzle")
    pair((5.85, 11.45, 26.85), (7.15, 12.75, 27.15), "glow_cyan", light=15, name="nozzle_glow")

    # --- swingarm & footrests ---------------------------------------------
    pair((4.12, 1.5, 12.5), (4.93, 3.5, 16.6), "trim", name="swingarm")
    # footrests under the rider's feet, either side of the prow
    pair((2.4, 10.55, -1.2), (6.05, 11.35, 2.3), "metal", name="footrest")

    model = {
        "textures": {
            "body": "minecraft:item/master_cycle/body",
            "trim": "minecraft:item/master_cycle/trim",
            "tread": "minecraft:item/master_cycle/tread",
            "tire_side": "minecraft:item/master_cycle/tire_side",
            "gold": "minecraft:item/master_cycle/gold",
            "glow_cyan": "minecraft:item/master_cycle/glow_cyan",
            "glow_orange": "minecraft:item/master_cycle/glow_orange",
            "seat": "minecraft:item/master_cycle/seat",
            "metal": "minecraft:item/master_cycle/metal",
            "eye": "minecraft:item/master_cycle/eye",
            "particle": "minecraft:item/master_cycle/body",
        },
        "elements": ELEMENTS[:],
        "display": {
            # Worn on the head of an invisible armor stand scaled to 0.5.
            # scale 2.75 -> ~2.5 blocks long; translation drops the tyres onto
            # the ground and slides the bike so the seat sits under the rider.
            "head": {"rotation": [0, 0, 0], "translation": [0, -7.2, -16.5], "scale": [2.75, 2.75, 2.75]},
            "gui": {"rotation": [20, 135, 0], "translation": [0, -0.5, 0], "scale": [0.32, 0.32, 0.32]},
            "ground": {"rotation": [0, 0, 0], "translation": [0, 2, 0], "scale": [0.2, 0.2, 0.2]},
            "fixed": {"rotation": [0, 90, 0], "translation": [0, 0, 0], "scale": [0.32, 0.32, 0.32]},
            "thirdperson_righthand": {"rotation": [0, 90, 0], "translation": [0, 3, 0], "scale": [0.2, 0.2, 0.2]},
            "thirdperson_lefthand": {"rotation": [0, 90, 0], "translation": [0, 3, 0], "scale": [0.2, 0.2, 0.2]},
            "firstperson_righthand": {"rotation": [0, 90, 0], "translation": [0, 2, 0], "scale": [0.2, 0.2, 0.2]},
            "firstperson_lefthand": {"rotation": [0, 90, 0], "translation": [0, 2, 0], "scale": [0.2, 0.2, 0.2]},
        },
    }
    for el in model["elements"]:
        for v in el["from"] + el["to"]:
            assert -16 <= v <= 32, (el.get("name"), v)
    # 0.02 also catches near-coplanar faces, not just exact matches
    fights = zfight_pairs(model, plane_eps=0.02)
    assert not fights, f"z-fighting faces: {fights[:5]}"
    # element names are only for our own tools (z-fight / rider reports); the
    # game ignores them, so keep the shipped model to the documented keys
    shipped = dict(model, elements=[{k: v for k, v in el.items() if k != "name"} for el in model["elements"]])
    write_json(MC / "models" / "item" / "custom_master_cycle.json", shipped)
    write_json(NAMED_MODEL, model)  # same model with element names, for tools only
    return model


def build_slate_model():
    write_json(MC / "models" / "item" / "sheikah_slate.json", {
        "parent": "minecraft:item/handheld",
        "textures": {"layer0": "minecraft:item/sheikah_slate"},
        "display": {
            "thirdperson_righthand": {"rotation": [0, -90, 10], "translation": [0, 3.5, 0.5], "scale": [0.85, 0.85, 0.85]},
            "thirdperson_lefthand": {"rotation": [0, 90, -10], "translation": [0, 3.5, 0.5], "scale": [0.85, 0.85, 0.85]},
            "firstperson_righthand": {"rotation": [0, -90, 15], "translation": [1.13, 3.2, 1.13], "scale": [0.68, 0.68, 0.68]},
            "firstperson_lefthand": {"rotation": [0, 90, -15], "translation": [1.13, 3.2, 1.13], "scale": [0.68, 0.68, 0.68]},
        },
    })


def build_item_definition():
    """assets/minecraft/items/warped_fungus_on_a_stick.json — routes the
    custom_model_data float to our models and keeps the vanilla look otherwise."""
    write_json(MC / "items" / "warped_fungus_on_a_stick.json", {
        "model": {
            "type": "minecraft:range_dispatch",
            "property": "minecraft:custom_model_data",
            "index": 0,
            "fallback": {"type": "minecraft:model", "model": "minecraft:item/warped_fungus_on_a_stick"},
            "entries": [
                {"threshold": CMD_CYCLE, "model": {"type": "minecraft:model", "model": "minecraft:item/custom_master_cycle"}},
                {"threshold": CMD_SLATE, "model": {"type": "minecraft:model", "model": "minecraft:item/sheikah_slate"}},
                # Anything above our range falls back to the vanilla model again.
                {"threshold": CMD_SLATE + 1, "model": {"type": "minecraft:model", "model": "minecraft:item/warped_fungus_on_a_stick"}},
            ],
        }
    })


# ----------------------------------------------------------------- sounds ---
# A small DSP kit (filters, reverb, saturation) so the sounds have real body
# instead of bare sine tones.
SR = 44100


def noise(n, seed):
    return np.random.default_rng(seed).standard_normal(n)


def env(n, attack, release, curve=1.0):
    e = np.ones(n)
    a, r = int(attack * SR), int(release * SR)
    if a:
        e[:a] = np.linspace(0, 1, a) ** curve
    if r:
        e[-r:] *= np.linspace(1, 0, r) ** curve
    return e


def decay(n, rate):
    return np.exp(-np.arange(n) / SR * rate)


def tone(freq, dur, phase=0.0):
    """Sine with a time-varying frequency (freq may be an array)."""
    n = int(dur * SR)
    f = np.broadcast_to(np.asarray(freq, dtype=float), (n,))
    return np.sin(2 * np.pi * np.cumsum(f) / SR + phase)


def saw(freq, dur, harmonics=14, phase=0.0):
    """Band-limited sawtooth: the harmonic stack an electric motor whines with."""
    out = np.zeros(int(dur * SR))
    f = np.asarray(freq, dtype=float)
    for k in range(1, harmonics + 1):
        if np.max(f) * k > SR * 0.45:
            break
        out += tone(f * k, dur, phase * k) / k
    return out * (2 / np.pi)


def svf(sig, cutoff, res=1.0, mode="lp"):
    """State-variable filter. `cutoff` may be an array, so it can sweep."""
    n = len(sig)
    f = np.broadcast_to(np.asarray(cutoff, dtype=float), (n,))
    f = 2 * np.sin(np.pi * np.clip(f, 20, SR * 0.45) / SR)
    out = np.empty(n)
    low = band = 0.0
    if mode == "lp":
        for i in range(n):
            high = sig[i] - low - res * band
            band += f[i] * high
            low += f[i] * band
            out[i] = low
    elif mode == "bp":
        for i in range(n):
            high = sig[i] - low - res * band
            band += f[i] * high
            low += f[i] * band
            out[i] = band
    else:
        for i in range(n):
            high = sig[i] - low - res * band
            band += f[i] * high
            low += f[i] * band
            out[i] = high
    return out


def lowpass2(sig, cutoff, res=0.7):
    """Two lowpasses in series: a steeper slope, so "low" really is low."""
    return svf(svf(sig, cutoff, res=res), cutoff, res=res)


def comb(x, delay, g):
    """Feedback comb, computed a delay-block at a time so it stays vectorised."""
    y = x.copy()
    for i in range(delay, len(y), delay):
        seg = min(delay, len(y) - i)
        y[i:i + seg] += g * y[i - delay:i - delay + seg]
    return y


def reverb(x, size=1.0, mix=0.3):
    """Schroeder reverb: four combs in parallel, then two allpasses."""
    wet = np.zeros(len(x))
    for d, g in ((1557, 0.78), (1617, 0.77), (1491, 0.79), (1422, 0.76)):
        wet += comb(x, max(1, int(d * size)), g)
    wet /= 4
    for d, g in ((225, 0.7), (556, 0.7)):
        d = max(1, int(d * size))
        delayed = np.concatenate([np.zeros(d), wet[:-d]])
        wet = -g * wet + delayed + g * np.concatenate([np.zeros(d), (-g * wet + delayed)[:-d]])
    return (1 - mix) * x + mix * wet / (np.max(np.abs(wet)) + 1e-9) * (np.max(np.abs(x)) + 1e-9)


def mix(*layers):
    """Mix (gain, signal) layers, each normalised to the same RMS first, so the
    balance is what the gains say rather than whatever the filters left behind.
    RMS rather than peak, so noise layers don't swing with the random seed."""
    n = max(len(sig) for _, sig in layers)
    out = np.zeros(n)
    for gain, sig in layers:
        rms = np.sqrt(np.mean(sig ** 2))
        if rms > 1e-9:
            out[:len(sig)] += gain * sig / rms
    return out


def saturate(x, drive=2.0):
    return np.tanh(drive * x) / np.tanh(drive)


def bell(freq, dur, rate=4.0, partials=(1.0, 2.76, 5.4), gains=(1.0, 0.35, 0.12)):
    """Struck metal: inharmonic partials, each decaying faster than the last."""
    n = int(dur * SR)
    out = np.zeros(n)
    for p, g in zip(partials, gains):
        out += g * tone(freq * p, dur) * decay(n, rate * (1 + 0.7 * (p - 1)))
    return out


def place(buf, sig, at):
    i = max(0, int(at * SR))
    end = min(len(buf), i + len(sig))
    if end > i:
        buf[i:end] += sig[: end - i]


# ---- engine --------------------------------------------------------------
def snd_engine_hum():
    """Sheikah motor: a saw stack under a resonant filter, a coil whine on top,
    and a slow wobble so a looping sample never sounds static."""
    dur = 0.6
    n = int(dur * SR)
    t = np.arange(n) / SR
    wob = 1 + 0.015 * np.sin(2 * np.pi * 3.3 * t)
    core = 0.7 * saw(62 * wob, dur) + 0.4 * saw(93 * wob, dur, harmonics=8)
    core = svf(core, 420 + 120 * np.sin(2 * np.pi * 2.1 * t), res=0.55)
    sub = 0.5 * tone(31 * wob, dur)
    whine = 0.055 * tone(2480 * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * t)), dur)
    whine += 0.03 * tone(3720, dur)
    air = 0.05 * svf(noise(n, 11), 1800, res=0.9, mode="bp")
    s = saturate(core + sub, 1.6) * 0.8 + whine + air
    return s * env(n, 0.03, 0.06)


def snd_start():
    """Ignition: a clunk, the motor spinning up, and the Sheikah chime."""
    dur = 1.6
    n = int(dur * SR)
    t = np.arange(n) / SR
    spin = 1 - np.exp(-t * 2.6)
    rpm = 28 + 70 * spin
    s = saturate(0.8 * saw(rpm, dur) + 0.4 * tone(rpm / 2, dur), 2.0) * spin * 0.6
    s = svf(s, 250 + 900 * spin, res=0.5)
    s += 0.08 * tone(1200 + 1400 * spin, dur) * spin
    clunk = svf(noise(int(0.12 * SR), 3), 300, res=0.4) * decay(int(0.12 * SR), 40)
    place(s, 1.1 * clunk, 0.0)
    for i, f in enumerate((659.3, 987.8, 1318.5)):
        place(s, 0.3 * bell(f, 0.9, 4.5), 0.42 + i * 0.11)
    return reverb(s * env(n, 0.002, 0.35), size=0.8, mix=0.2)


def snd_engine_stop():
    """Power-down: the motor spinning down, then the core going quiet."""
    dur = 1.3
    n = int(dur * SR)
    t = np.arange(n) / SR
    glide = np.exp(-t * 2.3)
    s = saturate(0.8 * saw(26 + 76 * glide, dur), 1.8) * glide * 0.7
    s = svf(s, 180 + 700 * glide, res=0.5)
    s += 0.05 * tone(2400 * glide + 300, dur) * glide
    place(s, 0.22 * bell(880, 0.6, 7), 0.0)
    thunk = svf(noise(int(0.1 * SR), 5), 220, res=0.4) * decay(int(0.1 * SR), 45)
    place(s, 0.8 * thunk, 0.82)
    return reverb(s * env(n, 0.004, 0.3), size=0.7, mix=0.18)


def snd_boost():
    """Afterburner: a filtered noise sweep, a rising tone and a spark crackle."""
    dur = 1.1
    n = int(dur * SR)
    t = np.arange(n) / SR
    shape = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.3
    whoosh = svf(noise(n, 7), 300 + 5200 * (t / dur) ** 1.5, res=0.35, mode="bp") * shape
    whoosh /= np.max(np.abs(whoosh)) + 1e-9
    rise = 0.35 * saw(190 + 700 * (t / dur) ** 1.4, dur, harmonics=6) * env(n, 0.03, 0.4)
    crack = svf(noise(n, 9), 4800, res=0.2, mode="hp") * decay(n, 7) * 0.25
    return reverb(0.75 * whoosh + rise + crack, size=1.1, mix=0.25)


# ---- fuel ----------------------------------------------------------------
def snd_refuel():
    """Energy pouring in: a rising arpeggio over a charging hum."""
    dur = 1.1
    s = np.zeros(int(dur * SR))
    for i, f in enumerate((523.3, 784.0, 1046.5, 1568.0, 2093.0)):
        place(s, 0.3 * bell(f, 0.7, 5.5), i * 0.075)
    t = np.arange(len(s)) / SR
    s += 0.22 * tone(110 * (1 + 0.6 * t / dur), dur) * env(len(s), 0.05, 0.45)
    s += 0.07 * svf(noise(len(s), 13), 2600 + 2000 * t / dur, res=0.5, mode="bp") * env(len(s), 0.1, 0.5)
    return reverb(s, size=0.9, mix=0.22)


def snd_fuel_low():
    """Two soft falling tones: a warning, not an alarm."""
    s = np.zeros(int(1.0 * SR))
    place(s, 0.5 * bell(1318.5, 0.5, 6), 0.0)
    place(s, 0.45 * bell(987.8, 0.6, 5), 0.21)
    return reverb(s, size=0.7, mix=0.25)


def snd_empty():
    """The core sputtering out: a gated, falling tone collapsing into hiss."""
    dur = 1.5
    n = int(dur * SR)
    t = np.arange(n) / SR
    glide = np.exp(-t * 2.0)
    body = saturate(0.9 * saw(34 + 150 * glide, dur, harmonics=10), 2.4)
    gate = (np.sin(2 * np.pi * (7 + 10 * t) * t) > -0.25).astype(float) * 0.75 + 0.25
    body = svf(body * gate, 160 + 900 * glide, res=0.6) * glide
    hiss = svf(noise(n, 17), 1400, res=0.8, mode="bp") * decay(n, 2.2) * 0.12
    place(body, 0.3 * bell(392, 0.7, 6), 0.55)
    return reverb(body * 0.8 + hiss, size=0.8, mix=0.2) * env(n, 0.005, 0.3)


# ---- summon / dismiss ----------------------------------------------------
def snd_summon():
    """Materialising: a shimmer swelling under a bell cluster and a sub rise."""
    dur = 2.0
    n = int(dur * SR)
    t = np.arange(n) / SR
    shimmer = sum(tone(f * (1 + 0.003 * np.sin(2 * np.pi * (4 + i) * t)), dur)
                  for i, f in enumerate((440, 659.3, 880, 1318.5, 1760)))
    s = 0.11 * shimmer * env(n, 0.55, 0.7, curve=1.5)
    s += 0.1 * svf(noise(n, 19), 600 + 5000 * t / dur, res=0.4, mode="bp") * env(n, 0.5, 0.6)
    for i, f in enumerate((1318.5, 1760.0, 1975.5, 2637.0)):
        place(s, 0.2 * bell(f, 1.0, 3.6), 0.42 + i * 0.1)
    s += 0.28 * tone(48 + 50 * t, dur) * env(n, 0.3, 0.6)
    return reverb(s, size=1.4, mix=0.35)


def snd_dismiss():
    """Dematerialising: the same bells falling, with the shimmer running out."""
    dur = 1.3
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for i, f in enumerate((1975.5, 1318.5, 987.8, 659.3)):
        place(s, 0.24 * bell(f, 0.8, 5), i * 0.095)
    s += 0.09 * svf(noise(n, 23), 5200 - 4200 * t / dur, res=0.4, mode="bp") * env(n, 0.02, 0.5)
    s += 0.2 * tone(120 - 70 * t / dur, dur) * env(n, 0.02, 0.6)
    return reverb(s, size=1.2, mix=0.32)


# ---- impacts (several variants each, so repeats don't sound identical) ----
def _impact(seed, thud_f, ring_f, ring_g, crunch_g, dur=0.55, ring_lp=1800):
    """Weight on the bottom (body), a short metallic ring, a little grit."""
    n = int(dur * SR)
    body = lowpass2(noise(n, seed), thud_f, res=0.35) * decay(n, 26)
    drop = tone(np.linspace(thud_f * 1.1, thud_f * 0.6, n), dur) * decay(n, 30)
    ring = bell(ring_f, dur, 11, partials=(1.0, 2.1, 3.4, 5.9), gains=(1.0, 0.6, 0.3, 0.15))
    ring = svf(ring, ring_lp, res=0.7)  # keep the clang from turning into a ping
    grit = svf(noise(n, seed + 1), 3200, res=0.5, mode="bp") * decay(n, 34)
    s = mix((1.0, body), (0.85, drop), (ring_g, ring), (crunch_g, grit))
    return reverb(s * env(n, 0.001, 0.12), size=0.6, mix=0.16)


def snd_ram(seed):
    """Nose hitting a mob: a heavy thud with a metallic crack."""
    return _impact(seed, 110, 640, 0.07, 0.03)


def snd_wall(seed):
    """Running into blocks: a duller, grittier crunch."""
    return _impact(seed, 85, 320, 0.042, 0.018, dur=0.6)


def snd_land(seed):
    """Suspension bottoming out on touchdown: a soft thump and a spring ring."""
    n = int(0.45 * SR)
    s = mix((1.0, lowpass2(noise(n, seed), 190, res=0.3) * decay(n, 30)),
            (0.8, tone(np.linspace(150, 60, n), 0.45) * decay(n, 22)),
            (0.07, bell(1180, 0.45, 16, partials=(1.0, 2.4), gains=(1.0, 0.4))))
    return reverb(s * env(n, 0.001, 0.1), size=0.5, mix=0.12)


# ---- surfaces & liquids --------------------------------------------------
def snd_tyre_roll():
    """Tyres on ground: a loopable low rumble with grit on top."""
    dur = 0.6
    n = int(dur * SR)
    t = np.arange(n) / SR
    rumble = lowpass2(noise(n, 31), 150 + 40 * np.sin(2 * np.pi * 2.7 * t), res=0.6)
    thrum = lowpass2(noise(n, 33), 380, res=0.5)
    grit = svf(noise(n, 37), 2100, res=0.7, mode="bp") * (0.5 + 0.5 * np.sin(2 * np.pi * 11 * t))
    s = mix((1.0, rumble), (0.5, thrum), (0.025, grit))
    return s * env(n, 0.04, 0.06)


def snd_splash():
    """Hitting water: a burst, then bubbles."""
    dur = 0.9
    n = int(dur * SR)
    t = np.arange(n) / SR
    burst = svf(noise(n, 41), 700 + 2600 * np.exp(-t * 9), res=0.4, mode="bp") * decay(n, 7)
    burst = svf(burst, 3000, res=0.7)  # water is a thud with spray, not a hiss
    s = mix((0.9, burst), (1.3, lowpass2(noise(n, 43), 400, res=0.4) * decay(n, 11)))
    for i in range(7):
        f = 700 + 900 * ((i * 97) % 11) / 11
        place(s, 0.1 * tone(np.linspace(f, f * 1.7, int(0.07 * SR)), 0.07)
              * decay(int(0.07 * SR), 26), 0.14 + i * 0.07)
    return reverb(s * env(n, 0.001, 0.2), size=0.7, mix=0.2)


def snd_sizzle():
    """Floating on lava: a thick, slow hiss with bubbling underneath."""
    dur = 1.2
    n = int(dur * SR)
    t = np.arange(n) / SR
    hiss = svf(noise(n, 47), 1150 + 350 * np.sin(2 * np.pi * 1.7 * t), res=0.3, mode="bp")
    hiss = svf(hiss, 2600, res=0.7)  # tame the top so it hisses rather than spits
    bubble = lowpass2(noise(n, 53), 220, res=0.5) * (0.6 + 0.4 * np.sin(2 * np.pi * 3.1 * t))
    s = mix((1.0, hiss), (1.1, bubble))
    for i in range(5):
        place(s, 0.18 * tone(np.linspace(90, 150, int(0.12 * SR)), 0.12)
              * decay(int(0.12 * SR), 18), 0.1 + i * 0.22)
    return reverb(s * env(n, 0.06, 0.25), size=0.9, mix=0.18)


# name -> (generator, target loudness). The hum and the tyre roll play
# constantly, so they sit well under the one-shot effects.
SOUNDS = {
    "engine_hum": (snd_engine_hum, 0.115),
    "tyre_roll": (snd_tyre_roll, 0.075),
    "start": (snd_start, 0.20),
    "stop": (snd_engine_stop, 0.17),
    "boost": (snd_boost, 0.21),
    "refuel": (snd_refuel, 0.18),
    "fuel_low": (snd_fuel_low, 0.16),
    "empty": (snd_empty, 0.20),
    "summon": (snd_summon, 0.18),
    "dismiss": (snd_dismiss, 0.17),
    "splash": (snd_splash, 0.19),
    "sizzle": (snd_sizzle, 0.13),
    **{f"ram{i}": ((lambda i: lambda: snd_ram(60 + i * 7))(i), 0.23) for i in range(1, 4)},
    **{f"wall{i}": ((lambda i: lambda: snd_wall(80 + i * 7))(i), 0.21) for i in range(1, 4)},
    **{f"land{i}": ((lambda i: lambda: snd_land(100 + i * 7))(i), 0.19) for i in range(1, 4)},
}

# event -> (files, volume, attenuation distance). Several files means
# Minecraft picks one at random, so repeated impacts never sound identical.
SOUND_EVENTS = {
    "engine.hum": (["engine_hum"], 0.8, 24),
    "engine.roll": (["tyre_roll"], 0.7, 20),
    "engine.start": (["start"], 1.0, 24),
    "engine.stop": (["stop"], 1.0, 16),
    "engine.boost": (["boost"], 1.0, 32),
    "fuel.add": (["refuel"], 0.9, 16),
    "fuel.low": (["fuel_low"], 1.0, 16),
    "fuel.empty": (["empty"], 1.0, 16),
    "cycle.summon": (["summon"], 1.0, 24),
    "cycle.dismiss": (["dismiss"], 1.0, 16),
    "impact.ram": (["ram1", "ram2", "ram3"], 1.0, 24),
    "impact.wall": (["wall1", "wall2", "wall3"], 1.0, 24),
    "impact.land": (["land1", "land2", "land3"], 0.9, 20),
    "liquid.splash": (["splash"], 1.0, 20),
    "liquid.sizzle": (["sizzle"], 0.8, 16),
}

SUBTITLES = {
    "engine.hum": "Master Cycle hums",
    "engine.roll": "Master Cycle rolls",
    "engine.start": "Master Cycle powers up",
    "engine.stop": "Master Cycle powers down",
    "engine.boost": "Master Cycle boosts",
    "fuel.add": "Master Cycle refuels",
    "fuel.low": "Master Cycle low on fuel",
    "fuel.empty": "Master Cycle sputters out",
    "cycle.summon": "Master Cycle materializes",
    "cycle.dismiss": "Master Cycle dematerializes",
    "impact.ram": "Master Cycle rams",
    "impact.wall": "Master Cycle crashes",
    "impact.land": "Master Cycle lands",
    "liquid.splash": "Master Cycle splashes",
    "liquid.sizzle": "Master Cycle sizzles",
}


def finish(sig, rms_target):
    """Remove DC offset, add click-free 3 ms / 8 ms fades, set loudness, limit peaks."""
    sig = sig - np.mean(sig)
    n_in, n_out = int(0.003 * SR), int(0.008 * SR)
    sig[:n_in] *= np.linspace(0, 1, n_in)
    sig[-n_out:] *= np.linspace(1, 0, n_out)
    sig = sig * (rms_target / max(1e-9, np.sqrt(np.mean(sig ** 2))))
    peak = np.max(np.abs(sig))
    if peak > 0.89:
        sig = np.tanh(sig / peak * 1.2) / np.tanh(1.2) * 0.89  # soft-limit instead of clipping
    return sig


# event-file -> (low, high) spectral centroid in Hz. A thud belongs at the
# bottom, a shimmer up top; this catches layers swamping each other.
SPECTRUM = {
    "engine_hum": (200, 2200), "tyre_roll": (150, 1200),
    "start": (300, 2500), "stop": (150, 1500), "boost": (1500, 7000),
    "refuel": (1500, 7000), "fuel_low": (800, 3000), "empty": (400, 3000),
    "summon": (1500, 7000), "dismiss": (1500, 7500),
    "ram": (250, 1600), "wall": (200, 1400), "land": (150, 900),
    "splash": (700, 4500), "sizzle": (500, 4000),
}


def centroid(sig):
    """Brightness: the energy-weighted mean frequency, in Hz."""
    spec = np.abs(np.fft.rfft(sig * np.hanning(len(sig))))
    freqs = np.fft.rfftfreq(len(sig), 1 / SR)
    return float((spec * freqs).sum() / max(spec.sum(), 1e-9))


def build_sounds():
    sdir = NS / "sounds"
    sdir.mkdir(parents=True, exist_ok=True)
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg (with libvorbis) is required to encode the .ogg sounds")
    with tempfile.TemporaryDirectory() as tmp:
        for name, (fn, loudness) in SOUNDS.items():
            sig = finish(fn(), loudness)
            lo, hi = SPECTRUM[name.rstrip("123")]
            c = centroid(sig)
            assert lo <= c <= hi, f"{name}: centroid {c:.0f}Hz outside {lo}-{hi}Hz"
            wav_path = Path(tmp) / f"{name}.wav"
            with wave.open(str(wav_path), "wb") as w:
                w.setnchannels(1)  # mono, so Minecraft plays it positionally
                w.setsampwidth(2)
                w.setframerate(SR)
                w.writeframes((sig * 32767).astype("<i2").tobytes())
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav_path),
                 "-c:a", "libvorbis", "-q:a", "5", "-ac", "1", "-map_metadata", "-1",
                 "-fflags", "+bitexact", "-flags:a", "+bitexact", str(sdir / f"{name}.ogg")],
                check=True,
            )
    write_json(NS / "sounds.json", {
        event: {
            "subtitle": f"subtitles.mastercycle.{event}",
            "sounds": [{"name": f"mastercycle:{f}", "volume": vol, "attenuation_distance": dist}
                       for f in files],
        }
        for event, (files, vol, dist) in SOUND_EVENTS.items()
    })
    write_json(NS / "lang" / "en_us.json",
               {f"subtitles.mastercycle.{k}": v for k, v in SUBTITLES.items()})


def build_pack_meta():
    write_json(RP / "pack.mcmeta", {
        "pack": {
            "description": [
                {"text": "Master Cycle ", "color": "aqua"},
                {"text": "model, textures & sounds", "color": "gray"},
            ],
            "pack_format": RESOURCE_FORMAT,
            "min_format": RESOURCE_MIN,
            "max_format": RESOURCE_MAX,
        }
    })


def main():
    if RP.exists():
        shutil.rmtree(RP)
    RP.mkdir(parents=True)
    build_pack_meta()
    build_textures()
    model = build_cycle_model()
    build_slate_model()
    build_item_definition()
    build_sounds()
    print(f"resource pack written to {RP} ({len(model['elements'])} model elements)")


if __name__ == "__main__":
    main()
