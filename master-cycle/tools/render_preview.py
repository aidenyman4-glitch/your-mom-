#!/usr/bin/env python3
"""Render preview images of the Master Cycle item model without Minecraft.

A tiny orthographic software renderer: it reads the generated model JSON,
applies each element's rotation, textures every face from the pack's PNGs
(painter's algorithm, subdivided quads) and shades faces the way Minecraft's
item lighting roughly does. Good enough to sanity-check the geometry.

    python3 master-cycle/tools/render_preview.py [out.png]
"""

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
RP = ROOT / "resourcepack"
MODEL = RP / "assets/minecraft/models/item/custom_master_cycle.json"

FACE_CORNERS = {
    # corners in (u, v) order matching Minecraft's UV layout per face
    "north": lambda f, t: [(t[0], t[1], f[2]), (f[0], t[1], f[2]), (f[0], f[1], f[2]), (t[0], f[1], f[2])],
    "south": lambda f, t: [(f[0], t[1], t[2]), (t[0], t[1], t[2]), (t[0], f[1], t[2]), (f[0], f[1], t[2])],
    "west": lambda f, t: [(f[0], t[1], f[2]), (f[0], t[1], t[2]), (f[0], f[1], t[2]), (f[0], f[1], f[2])],
    "east": lambda f, t: [(t[0], t[1], t[2]), (t[0], t[1], f[2]), (t[0], f[1], f[2]), (t[0], f[1], t[2])],
    "up": lambda f, t: [(f[0], t[1], f[2]), (t[0], t[1], f[2]), (t[0], t[1], t[2]), (f[0], t[1], t[2])],
    "down": lambda f, t: [(f[0], f[1], t[2]), (t[0], f[1], t[2]), (t[0], f[1], f[2]), (f[0], f[1], f[2])],
}


def rot_matrix(axis, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def load_textures(model):
    tex = {}
    for key, ref in model["textures"].items():
        ns, path = ref.split(":")
        img = Image.open(RP / "assets" / ns / "textures" / f"{path}.png").convert("RGBA")
        tex[key] = np.asarray(img).astype(float)
    return tex


def collect_quads(model, tex, density=1.6):
    quads = []  # (points3d[4], rgb, emissive)
    for el in model["elements"]:
        f, t = el["from"], el["to"]
        R, origin = np.eye(3), np.zeros(3)
        if "rotation" in el:
            r = el["rotation"]
            origin = np.array(r["origin"], float)
            for ax in ("x", "y", "z"):
                if ax in r:
                    R = R @ rot_matrix(ax, r[ax])
            if "axis" in r:
                R = rot_matrix(r["axis"], r["angle"])
        emissive = el.get("light_emission", 0) > 0
        for face, spec in el["faces"].items():
            corners = np.array(FACE_CORNERS[face](f, t), float)
            corners = (corners - origin) @ R.T + origin
            img = tex[spec["texture"].lstrip("#")]
            h, w = img.shape[:2]
            u0, v0, u1, v1 = spec["uv"]
            # subdivide the face into small cells sampled from the texture
            e1, e2 = corners[1] - corners[0], corners[3] - corners[0]
            nu = max(1, int(np.linalg.norm(e1) * density))
            nv = max(1, int(np.linalg.norm(e2) * density))
            normal = np.cross(e1, e2)
            normal /= np.linalg.norm(normal) + 1e-9
            for i in range(nu):
                for j in range(nv):
                    a, b = i / nu, (i + 1) / nu
                    c, d = j / nv, (j + 1) / nv
                    p = [corners[0] + e1 * x + e2 * y for x, y in ((a, c), (b, c), (b, d), (a, d))]
                    su = u0 + (u1 - u0) * (a + b) / 2
                    sv = v0 + (v1 - v0) * (c + d) / 2
                    px = img[min(h - 1, int(sv / 16 * h)), min(w - 1, int(su / 16 * w))]
                    quads.append((np.array(p), px[:3], emissive, normal))
    return quads


def render(quads, yaw, pitch, size=420, scale=7.0):
    Ry = rot_matrix("y", yaw)
    Rx = rot_matrix("x", pitch)
    V = Rx @ Ry
    center = np.array([8, 8, 8])
    img = Image.new("RGB", (size, size), (236, 236, 236))
    draw = ImageDraw.Draw(img)
    light = np.array([0.3, 1.0, 0.6])
    light /= np.linalg.norm(light)
    items = []
    for pts, rgb, emissive, normal in quads:
        q = (pts - center) @ V.T
        depth = q[:, 2].mean()
        shade = 1.0 if emissive else 0.55 + 0.45 * max(0.0, float(normal @ light))
        col = tuple(int(min(255, c * shade)) for c in rgb)
        poly = [(size / 2 + x * scale, size / 2 - y * scale) for x, y, _ in q]
        items.append((depth, poly, col))
    items.sort(key=lambda it: it[0], reverse=True)
    for _, poly, col in items:
        draw.polygon(poly, fill=col)
    # ground line (model y=-5)
    return img


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "model-preview.png"
    model = json.loads(MODEL.read_text())
    tex = load_textures(model)
    quads = collect_quads(model, tex)
    views = [
        ("left side", -90, 0),
        ("front 3/4", -140, -20),
        ("rear 3/4", -30, -25),
        ("top", -90, -89),
    ]
    tiles = [render(quads, yaw, pitch) for _, yaw, pitch in views]
    sheet = Image.new("RGB", (840, 840), (236, 236, 236))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, ((i % 2) * 420, (i // 2) * 420))
    d = ImageDraw.Draw(sheet)
    for i, (label, _, _) in enumerate(views):
        d.text(((i % 2) * 420 + 10, (i // 2) * 420 + 8), label, fill=(90, 90, 90))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"preview written to {out}")


if __name__ == "__main__":
    main()
