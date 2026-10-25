"""Painter's-algorithm renderer, writing animated GIFs.

Face colours come straight from the atlas through each face's UV rect, so the render matches
what the pack actually ships. The starburst face is a transparent cutout, so its cube is drawn
by pasting the real art rather than filling a quad.
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rig          # noqa: E402
import anim         # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "animations"

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


def _face_art():
    im = Image.open(rig.ATLAS).convert("RGBA")
    return im.crop((256, 256, 512, 512))


FACE_ART = _face_art()


def _norm(v):
    l = math.sqrt(sum(c * c for c in v)) or 1.0
    return [c / l for c in v]


LIGHT = _norm(LIGHT)


def collect(pose):
    sol = rig.solve_grounded(pose)
    quads = []
    for bone in rig.BONE_ORDER:
        cubes = rig.GEOMETRY.get(bone)
        if not cubes:
            continue
        pos, q = sol[bone]
        for cube in cubes:
            pts = rig.cube_corners(cube)
            pts = [tuple(pos[i] + rig.quat_rotate(q, p)[i] for i in range(3)) for p in pts]
            for idx, nrm, name in FACES:
                col = cube["faces"].get(name)
                if col is None:
                    # the face-art cutout: only the forward plate is worth drawing
                    if nrm[2] <= 0:
                        continue
                    quads.append(([pts[i] for i in idx], None, 0))
                    continue
                n = rig.quat_rotate(q, nrm)
                lam = max(0.0, sum(n[i] * LIGHT[i] for i in range(3)))
                shade = 0.34 + 0.66 * lam
                emit = cube.get("emit", 0)
                if emit:
                    shade = max(shade, 0.80 + emit / 60.0)
                quads.append(([pts[i] for i in idx],
                              tuple(min(255, int(c * shade)) for c in col), emit))
    return quads


def frame(pose, yaw, pitch, size, lo, hi, span, bg):
    quads = collect(pose)
    cy, sy = math.cos(math.radians(yaw + 180)), math.sin(math.radians(yaw + 180))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))

    def view(p):
        x, y, z = p
        x, z = x * cy - z * sy, x * sy + z * cy
        y, z = y * cp - z * sp, y * sp + z * cp
        return (x, y, z)

    pts = [[view(p) for p in q[0]] for q in quads]
    W, H = size
    s = (H - 70) / span
    ox = W / 2
    oy = H - 34 + lo * s

    img = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(img)
    order = sorted(range(len(quads)), key=lambda i: -sum(p[2] for p in pts[i]) / 4.0)
    for i in order:
        scr = [(ox + p[0] * s, oy - p[1] * s) for p in pts[i]]
        if quads[i][1] is None:
            xs = [q[0] for q in scr]; ys = [q[1] for q in scr]
            bw = max(2, int(max(xs) - min(xs))); bh = max(2, int(max(ys) - min(ys)))
            art = FACE_ART.resize((bw, bh), Image.NEAREST)
            img.paste(art, (int(min(xs)), int(min(ys))), art)
        else:
            d.polygon(scr, fill=quads[i][1])
    return img


def scanlines(img, strength=28):
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(0, img.height, 3):
        d.line([(0, y), (img.width, y)], fill=(0, 0, 0, strength))
    return img


def make_gif(name, fn, label, note, frames=24, size=(400, 620), yaw=26.0, pitch=4.0,
             ms=90, bg=(11, 10, 14)):
    poses = [fn(i / frames) for i in range(frames)]
    los, his = zip(*(rig.extents(p) for p in poses))
    lo, hi = min(los), max(his)
    span = max(1.0, hi - lo)

    imgs = []
    for i, pose in enumerate(poses):
        im = frame(pose, yaw, pitch, size, lo, hi, span, bg)
        scanlines(im)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, size[0], 30], fill=(8, 7, 11))
        d.text((10, 10), label.upper(), fill=(226, 222, 232))
        d.text((size[0] - 54, 10), f"{i + 1:02d}/{frames}", fill=(150, 46, 46))
        d.text((10, size[1] - 20), note, fill=(126, 122, 134))
        imgs.append(im.convert("P", palette=Image.ADAPTIVE, colors=128))

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{name}.gif"
    imgs[0].save(p, save_all=True, append_images=imgs[1:], duration=ms, loop=0,
                 optimize=True, disposal=2)
    return p


if __name__ == "__main__":
    made = []
    timing = {"dread_idle": 110, "wrong_walk": 80, "lurch": 85,
              "stare_down": 95, "harvest_rise": 95}
    for key, (fn, label, note) in anim.CLIPS.items():
        p = make_gif(key, fn, label, note, ms=timing.get(key, 90))
        print(p, p.stat().st_size // 1024, "KB")
        made.append(p)
