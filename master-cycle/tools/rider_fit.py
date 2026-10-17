#!/usr/bin/env python3
"""Check that a player in Minecraft's riding pose fits on the Master Cycle.

The game always draws a mounted player in a fixed pose (HumanoidModel
"riding"): thighs forward at 81 degrees and splayed 18 degrees, arms reaching
forward 36 degrees. A data pack cannot change that pose, so the bike is shaped
around it. This script puts a vanilla-sized player on the model exactly where
the game would (armor stand passenger point 0.9875 - player vehicle attachment
0.6), measures how much of each body part ends up inside the bike, and renders
docs/rider-preview.png.

    python3 master-cycle/tools/rider_fit.py

Exits non-zero if the body, head or legs pass through the bike. The hands are
allowed inside the grips, since that is the rider holding them.
"""
import json, math, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import render_preview as rp

# model display.head transform (from the model) -> world blocks, rider frame
NAMED = rp.ROOT / "tools" / ".cache" / "custom_master_cycle.named.json"
m = json.loads((NAMED if NAMED.exists() else rp.MODEL).read_text())
d = m["display"]["head"]; S = d["scale"][0]; T = d["translation"]
K = 0.625 * 0.5 / 16                 # head-slot 0.625, armor stand scale 0.5, 1/16
HEAD_CENTER = (1.501 - 1 / 16) * 0.5 + 0.25 * 0.5

def world_to_model(p):               # p = (lateral, height, forward) in blocks
    l, h, f = p
    x = 8 + l / (K * S)
    y = 8 + ((h - HEAD_CENTER) / K - T[1]) / S
    z = 8 + ((-f) / K - T[2]) / S
    return (x, y, z)

FEET = 0.9875 - 0.6
PX = 1 / 16

def rot(axis, deg):
    return rp.rot_matrix(axis, deg)

def part(size, pivot, offset, R, color):
    """Box of `size` px whose corner is at `offset` px from `pivot` (px, player
    frame: x lateral, y up, z forward), rotated by R about the pivot."""
    sx, sy, sz = size; ox, oy, oz = offset
    corners = np.array([[ox + a * sx, oy + b * sy, oz + c * sz] for a in (0, 1) for b in (0, 1) for c in (0, 1)], float)
    pts = corners @ R.T + np.array(pivot, float)
    pts = pts * PX + np.array([0, FEET, 0])
    return [world_to_model(p) for p in pts], color

def faces(box):
    pts, col = box
    P = np.array(pts)
    idx = [(0, 1, 3, 2), (4, 5, 7, 6), (0, 1, 5, 4), (2, 3, 7, 6), (0, 2, 6, 4), (1, 3, 7, 5)]
    out = []
    for f in idx:
        q = P[list(f)]
        n = np.cross(q[1] - q[0], q[3] - q[0]); n /= np.linalg.norm(n) + 1e-9
        out.append((q, np.array(col, float), False, n))
    return out

SKIN, SHIRT, PANTS, HAIR = (200, 150, 110), (0, 170, 170), (60, 60, 150), (70, 45, 20)
leg_fwd = rot("x", -81)                # rotate the hanging leg (−y) forward (+z)
arm_fwd = rot("x", -36)
boxes = [
    part((8, 12, 4), (0, 12, 0), (-4, 0, -2), np.eye(3), SHIRT),                 # body
    part((8, 8, 8), (0, 24, 0), (-4, 0, -4), np.eye(3), SKIN),                   # head
]
for side in (-1, 1):
    Rleg = rot("y", 18 * side) @ rot("z", 4.5 * side) @ leg_fwd
    boxes.append(part((4, 12, 4), (1.9 * side, 12, 0), (-2, -12, -2), Rleg, PANTS))
    boxes.append(part((4, 12, 4), (5 * side, 22, 0), (-2, -10, -2), arm_fwd, SHIRT))
    # hand: the last 4px of the arm
    boxes.append(part((4.02, 4, 4.02), (5 * side, 22, 0), (-2.01, -10, -2.01), arm_fwd, SKIN))

def render(out, views):
    tex = rp.load_textures(m)
    q = rp.collect_quads(m, tex, density=2.5)
    for b in boxes:
        q += faces(b)
    # centre the view a little higher so the rider's head is in frame
    q = [(pts + np.array([0, -9, 0]), col, glow, n) for pts, col, glow, n in q]
    tiles = [rp.render(q, yaw, pitch, size=480, scale=6.6) for _, yaw, pitch in views]
    sheet = Image.new("RGB", (480 * len(tiles), 480), (236, 236, 236))
    for i, t in enumerate(tiles):
        sheet.paste(t, (i * 480, 0))
    dr = ImageDraw.Draw(sheet)
    for i, (label, _, _) in enumerate(views):
        dr.text((i * 480 + 10, 8), label, fill=(90, 90, 90))
    sheet.save(out)



def clipping(model=None, margin=0.15):
    """Sample each rider part's volume and report how much of it is inside the bike."""
    model = model or m
    els = []
    for el in model["elements"]:
        R, o = np.eye(3), np.zeros(3)
        r = el.get("rotation")
        if r:
            o = np.array(r["origin"], float)
            for ax in ("x", "y", "z"):
                if ax in r:
                    R = R @ rp.rot_matrix(ax, r[ax])
        els.append((el.get("name", "?"), np.array(el["from"]) + margin, np.array(el["to"]) - margin, R, o))
    names = ["body", "head"] + [f"{p}_{s}" for s in ("right", "left") for p in ("leg", "arm", "hand")]
    report = {}
    for name, (pts, _) in zip(names, boxes):
        P = np.array(pts)
        a, b, c = P[4] - P[0], P[2] - P[0], P[1] - P[0]
        samples = [P[0] + a * i + b * j + c * k for i in np.linspace(0.05, .95, 8) for j in np.linspace(0.05, .95, 8) for k in np.linspace(0.05, .95, 8)]
        hit = {}
        for s in samples:
            for en, lo, hi, R, o in els:
                local = (s - o) @ R + o
                if np.all(local > lo) and np.all(local < hi):
                    hit[en] = hit.get(en, 0) + 1
        if hit:
            report[name] = {k: round(v / len(samples) * 100, 1) for k, v in sorted(hit.items(), key=lambda kv: -kv[1])}
    return report


# Hands may sit inside the grips (that's holding them); a seat contact this
# small is the rider resting on the cushion.
ALLOWED = {"grip", "handlebar"}
LIMIT = 1.0  # percent of a body part's volume


def main():
    report = clipping()
    bad = {}
    for part_name, hits in report.items():
        for el, pct in hits.items():
            if el.split("_")[0] in ALLOWED and part_name.startswith(("hand", "arm")):
                continue
            if pct > LIMIT:
                bad.setdefault(part_name, {})[el] = pct
    out = rp.ROOT / "docs" / "rider-preview.png"
    render(str(out), [("left side", -90, 0), ("front 3/4", -145, -12), ("rear 3/4", -35, -18)])
    if bad:
        for k, v in bad.items():
            print(f"rider's {k} passes through {v}")
        sys.exit(1)
    print(f"rider fits: no body part more than {LIMIT}% inside the bike; preview written to {out}")


if __name__ == "__main__":
    main()
