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

# Target: Minecraft Java 26.3 (resource pack format 97).
RESOURCE_FORMAT = 97

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
    tex_slate().save(MC / "textures" / "item" / "sheikah_slate.png")
    pack_icon().save(RP / "pack.png")


# ------------------------------------------------------------------ model ---
# Model space: 1 unit = 1/16 of the item. Front of the cycle points NORTH
# (-Z), which is "forward" for an item worn in the head slot. X=8 is the
# centre line, Y=-5 is where the tyres touch the ground.

ELEMENTS = []


def _uv(du, dv):
    return [0, 0, round(min(abs(du), 16), 3), round(min(abs(dv), 16), 3)]


def box(frm, to, tex, rot=None, light=None, faces=None, name=None):
    """Add a cuboid. `faces` may override the texture per face."""
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
        "faces": {f: {"uv": _uv(*sizes[f]), "texture": "#" + face_tex[f]} for f in sizes},
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
    o = disc(cz, cy, R, x0, x1, 8, "tread", "tire_side", f"{name}_tyre", off=0)
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

    # --- front fork (raked struts from front hub up to the head) ----------
    pair((4.4, 2.0, -2.1), (5.15, 14.5, -0.9), "trim", rot=("x", 23.5, (8, 8.25, -1.5)))

    # --- engine / core ----------------------------------------------------
    box((6, -0.5, 4), (10, 7.5, 15), "metal", name="engine")
    box((5.6, 1.5, 5.5), (10.4, 3.2, 13.5), "glow_cyan", light=15, name="engine_core")
    box((6.4, 4.2, 6), (9.6, 5.2, 13), "glow_orange", light=12, name="engine_coil")
    # down tube from head to engine
    box((7, 1.5, -0.5), (9, 12.5, 1.5), "trim", rot=("x", 22.5, (8, 7, 0.5)), name="down_tube")

    # --- torso / tank -----------------------------------------------------
    box((5, 8.5, 1), (11, 14, 10.5), "body", name="tank")
    box((5.5, 12.5, 0.5), (10.5, 15.5, 7.5), "body", rot=("x", -12, (8, 14, 4)), name="tank_top")
    # ornate side panels with Sheikah nodes
    pair((4.6, 7.8, 0), (5.0, 13.5, 16), "body", name="side_panel")
    pair((4.4, 7.2, -0.5), (4.8, 7.9, 16.5), "trim", name="panel_trim")
    for z, y in ((3.5, 10.5), (8.5, 9.5), (13.0, 11.0)):
        pair((4.3, y, z), (4.6, y + 0.9, z + 0.9), "glow_cyan", light=15)

    # --- head / prow (horse-like, leaning forward) ------------------------
    box((5.1, 11, -5), (10.9, 18, 1.5), "body", rot=("x", -20, (8, 14, -2)), name="head")
    box((6, 12.5, -10), (10, 16.5, -4), "body", rot=("x", -28, (8, 14.5, -7)), name="snout")
    box((6.6, 13.2, -10.6), (9.4, 14.4, -9.6), "glow_cyan", light=15,
        rot=("x", -28, (8, 14.5, -7)), name="headlight")
    pair((4.7, 15, -3.6), (5.1, 16.1, -2.4), "glow_cyan", light=15, name="eye")
    # horn / prong
    box((7.3, 14.6, -16), (8.7, 15.9, -6), "trim", rot=("x", 10, (8, 15.25, -6)), name="horn")
    box((7.65, 13.3, -12.5), (8.35, 14.3, -7), "trim", rot=("x", 4, (8, 13.8, -7)), name="horn_lower")
    # crest fins along the neck (lean back)
    for i, (z, h) in enumerate(((-4.0, 4.2), (-1.0, 3.6), (2.0, 2.8))):
        box((7.4, 16.8, z), (8.6, 16.8 + h, z + 1.6), "trim",
            rot=("x", 25, (8, 16.8, z + 0.8)), name=f"crest_{i}")
    # handlebars
    box((1.5, 17, 1), (14.5, 18, 2), "gold", name="handlebar")
    pair((0.4, 16.6, 0.6), (2.4, 18.4, 2.4), "seat", name="grip")

    # --- seat & rear body -------------------------------------------------
    box((5.5, 13, 10), (10.5, 14.2, 17.5), "seat", name="seat")
    box((5, 10.3, 16), (11, 15.5, 26), "body", name="rear_cowl")
    box((6, 14, 16.5), (10, 16, 19.5), "body", name="seat_back")
    box((4.5, 10, 14), (11.5, 11, 29.5), "trim", name="rear_fender")
    box((7.5, 14, 23.5), (8.5, 18.5, 30), "trim", rot=("x", 32, (8, 14, 24)), name="tail_fin")
    pair((4.4, 12.5, 24.5), (5.0, 13.6, 25.6), "glow_orange", light=15, name="tail_light")

    # --- swingarm & footpegs ---------------------------------------------
    pair((4.12, 1.5, 12.5), (4.93, 3.5, 16.6), "trim", name="swingarm")
    pair((3.0, 4.0, 11.0), (5.0, 4.8, 12.5), "metal", name="footpeg")

    model = {
        "credit": "Master Cycle - generated by master-cycle/tools/build_resourcepack.py",
        "texture_size": [32, 32],
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
    write_json(MC / "models" / "item" / "custom_master_cycle.json", model)
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
SR = 44100


def env(n, attack, release):
    e = np.ones(n)
    a, r = int(attack * SR), int(release * SR)
    if a:
        e[:a] = np.linspace(0, 1, a)
    if r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def tone(freq, dur, phase=0.0):
    """Sine with a time-varying frequency (freq may be an array)."""
    n = int(dur * SR)
    f = np.broadcast_to(np.asarray(freq, dtype=float), (n,))
    return np.sin(2 * np.pi * np.cumsum(f) / SR + phase)


def bell(freq, dur, decay=4.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 2.76 * t) * np.exp(-t * 6)
    return s * np.exp(-t * decay)


def place(buf, sig, at):
    i = int(at * SR)
    end = min(len(buf), i + len(sig))
    buf[i:end] += sig[: end - i]


def snd_engine_hum():
    dur = 0.75
    n = int(dur * SR)
    t = np.arange(n) / SR
    wob = 1 + 0.08 * np.sin(2 * np.pi * 7 * t)
    s = (0.55 * tone(62, dur) + 0.35 * tone(124, dur) + 0.22 * tone(186.5, dur)
         + 0.10 * tone(372, dur) + 0.05 * tone(1488 * (1 + 0.01 * np.sin(2 * np.pi * 3 * t)), dur))
    s = np.tanh(1.6 * s * wob) * 0.8
    return s * env(n, 0.12, 0.2)


def snd_start():
    dur = 1.4
    n = int(dur * SR)
    t = np.arange(n) / SR
    sweep = 45 + 120 * (1 - np.exp(-t * 3))
    s = np.tanh(2 * (0.6 * tone(sweep, dur) + 0.3 * tone(sweep * 2, dur))) * 0.55 * env(n, 0.05, 0.4)
    for i, f in enumerate((659.3, 987.8, 1318.5)):
        place(s, 0.28 * bell(f, 0.8), 0.25 + i * 0.12)
    return s


def snd_boost():
    dur = 1.0
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(7)
    noise = rng.standard_normal(n)
    # crude resonant band-pass sweep via moving average differences
    lo = np.convolve(noise, np.ones(18) / 18, mode="same")
    hi = noise - np.convolve(noise, np.ones(4) / 4, mode="same")
    whoosh = (lo * (1 - t) + hi * t) * np.sin(np.pi * t / dur) ** 1.5
    rise = tone(220 + 660 * t ** 1.4, dur) * 0.3 * env(n, 0.02, 0.35)
    return 0.6 * whoosh / np.max(np.abs(whoosh)) + rise


def snd_refuel():
    dur = 1.0
    s = np.zeros(int(dur * SR))
    for i, f in enumerate((523.3, 784.0, 1046.5, 1568.0)):
        place(s, 0.35 * bell(f, 0.6, 5), i * 0.09)
    hum = tone(110, dur) * 0.2 * env(len(s), 0.05, 0.5)
    return s + hum


def snd_empty():
    dur = 1.3
    n = int(dur * SR)
    t = np.arange(n) / SR
    sweep = 180 * np.exp(-t * 2.2) + 30
    sputter = (np.sin(2 * np.pi * 9 * t) > -0.2).astype(float) * 0.7 + 0.3
    return np.tanh(2 * tone(sweep, dur) + tone(sweep * 1.5, dur)) * 0.5 * sputter * env(n, 0.01, 0.5)


def snd_summon():
    dur = 1.8
    n = int(dur * SR)
    t = np.arange(n) / SR
    shimmer = sum(tone(f * (1 + 0.004 * np.sin(2 * np.pi * 5 * t)), dur) for f in (440, 659.3, 880, 1318.5))
    s = 0.14 * shimmer * env(n, 0.5, 0.8)
    for i, f in enumerate((1318.5, 1760.0, 1975.5, 2637.0)):
        place(s, 0.22 * bell(f, 0.9, 4), 0.35 + i * 0.1)
    s += 0.25 * tone(55 + 40 * t, dur) * env(n, 0.3, 0.6)
    return s


def snd_dismiss():
    dur = 1.2
    s = np.zeros(int(dur * SR))
    for i, f in enumerate((1975.5, 1318.5, 987.8, 659.3)):
        place(s, 0.25 * bell(f, 0.7, 5), i * 0.1)
    return s


SOUNDS = {
    "engine_hum": snd_engine_hum,
    "start": snd_start,
    "boost": snd_boost,
    "refuel": snd_refuel,
    "empty": snd_empty,
    "summon": snd_summon,
    "dismiss": snd_dismiss,
}

# event name -> (file, volume, attenuation distance)
SOUND_EVENTS = {
    "engine.hum": ("engine_hum", 0.8, 24),
    "engine.start": ("start", 1.0, 24),
    "engine.boost": ("boost", 1.0, 32),
    "fuel.add": ("refuel", 0.9, 16),
    "fuel.empty": ("empty", 1.0, 16),
    "cycle.summon": ("summon", 1.0, 24),
    "cycle.dismiss": ("dismiss", 1.0, 16),
}


def build_sounds():
    sdir = NS / "sounds"
    sdir.mkdir(parents=True, exist_ok=True)
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg (with libvorbis) is required to encode the .ogg sounds")
    with tempfile.TemporaryDirectory() as tmp:
        for name, fn in SOUNDS.items():
            sig = fn()
            sig = sig / max(1e-9, np.max(np.abs(sig))) * 0.89
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
            "sounds": [{"name": f"mastercycle:{file}", "volume": vol, "attenuation_distance": dist}],
        }
        for event, (file, vol, dist) in SOUND_EVENTS.items()
    })
    write_json(NS / "lang" / "en_us.json", {
        "subtitles.mastercycle.engine.hum": "Master Cycle hums",
        "subtitles.mastercycle.engine.start": "Master Cycle powers up",
        "subtitles.mastercycle.engine.boost": "Master Cycle boosts",
        "subtitles.mastercycle.fuel.add": "Master Cycle refuels",
        "subtitles.mastercycle.fuel.empty": "Master Cycle sputters out",
        "subtitles.mastercycle.cycle.summon": "Master Cycle materializes",
        "subtitles.mastercycle.cycle.dismiss": "Master Cycle dematerializes",
    })


def build_pack_meta():
    write_json(RP / "pack.mcmeta", {
        "pack": {
            "description": [
                {"text": "Master Cycle ", "color": "aqua"},
                {"text": "model, textures & sounds", "color": "gray"},
            ],
            "min_format": RESOURCE_FORMAT,
            "max_format": RESOURCE_FORMAT,
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
