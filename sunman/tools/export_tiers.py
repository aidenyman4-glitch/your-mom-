"""Emits the tier creatures as vanilla 26.3 item models, one per bone.

Same conventions as `export_models.py` does for the Sun Man — a bone's cubes are written
with the bone pivot at model (8,8,8), UVs in the 0..16 space vanilla uses regardless of
texture resolution, and one `items/` definition per part pointing at its model — but the
materials resolve through `atlas_patch.TIER_SLOTS`, so a Locust cube finally lands on a
Locust tile instead of falling back to the Sun Man's bone.

Emissive cubes carry `light_emission`, which 26.3 accepts per element: the Dark Walker's
eyes are lit at 15 and are the only part of it that is ever its own light source.

    python3 tools/export_tiers.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tiers                              # noqa: E402
from atlas_patch import TIER_SLOTS, TILE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "resourcepack" / "assets" / "sunman"
ATLAS_PX = 512
UV_PER_TEXEL = 16.0 / ATLAS_PX
TEXELS_PER_PX = 3.0
FACE_DIRS = ("north", "south", "east", "west", "up", "down")


def _face_span(direction, w, h, d):
    return {"north": (w, h), "south": (w, h), "east": (d, h),
            "west": (d, h), "up": (w, d), "down": (w, d)}[direction]


def _uv_for(mat, direction, w, h, d, salt):
    """A sub-rect of the material tile, sized to the face so texel density stays even."""
    tx, ty = TIER_SLOTS[mat]
    fw, fh = _face_span(direction, w, h, d)
    uw = max(2.0, min(float(TILE), fw * TEXELS_PER_PX))
    uh = max(2.0, min(float(TILE), fh * TEXELS_PER_PX))
    ox = (salt * 17) % max(1, int(TILE - uw))
    oy = (salt * 29) % max(1, int(TILE - uh))
    return [(tx + ox) * UV_PER_TEXEL, (ty + oy) * UV_PER_TEXEL,
            (tx + ox + uw) * UV_PER_TEXEL, (ty + oy + uh) * UV_PER_TEXEL]


def _element(cube, px_per_ru, salt):
    s = px_per_ru
    fx, fy, fz = (c * s for c in cube["from"])
    w, h, d = (c * s for c in cube["size"])
    frm = [8.0 + fx, 8.0 + fy, 8.0 + fz]
    to = [frm[0] + w, frm[1] + h, frm[2] + d]

    faces = {dirn: {"uv": [round(v, 4) for v in _uv_for(cube["mat"], dirn, w, h, d, salt)],
                    "texture": "#0"} for dirn in FACE_DIRS}
    el = {"from": [round(v, 3) for v in frm], "to": [round(v, 3) for v in to], "faces": faces}

    rot = cube.get("rotation")
    if rot:
        # 26.3 takes arbitrary Euler XYZ here; the old single-axis 22.5 degree limit is gone.
        o = rot.get("origin", [0.0, 0.0, 0.0])
        el["rotation"] = {"origin": [round(8.0 + o[i] * s, 3) for i in range(3)],
                          "x": rot.get("x", 0.0), "y": rot.get("y", 0.0),
                          "z": rot.get("z", 0.0)}
    if cube.get("emit"):
        el["light_emission"] = int(cube["emit"])
    return el


def export(creature):
    models = PACK / "models" / "item" / creature.name
    items = PACK / "items"
    models.mkdir(parents=True, exist_ok=True)
    items.mkdir(parents=True, exist_ok=True)

    written, lit = [], 0
    for bone in creature.BONE_ORDER:
        cubes = creature.GEOMETRY.get(bone)
        if not cubes:
            continue
        elements = [_element(c, creature.PX_PER_RU, i + 7 * len(bone))
                    for i, c in enumerate(cubes)]
        lit += sum(1 for e in elements if "light_emission" in e)
        (models / f"{bone}.json").write_text(json.dumps({
            "textures": {"0": "sunman:entity/sun_man", "particle": "sunman:entity/sun_man"},
            "elements": elements,
            "gui_light": "front",
        }, indent=2))
        (items / f"{creature.name}_{bone}.json").write_text(json.dumps({
            "model": {"type": "minecraft:model",
                      "model": f"sunman:item/{creature.name}/{bone}"}
        }, indent=2))
        written.append(bone)

    # how far the furthest element sits from its bone pivot, in model px. 26.3 dropped the
    # [-16, 32] bound, but Blockbench still will not open a project that exceeds it.
    far = max(abs(v - 8.0)
              for bone in written for i, c in enumerate(creature.GEOMETRY[bone])
              for v in (_element(c, creature.PX_PER_RU, i)["to"]
                        + _element(c, creature.PX_PER_RU, i)["from"]))
    print(f"  {creature.name:12} {len(written):2d} parts  "
          f"{sum(len(creature.GEOMETRY[b]) for b in written):3d} cubes  "
          f"{lit} emissive  scale {creature.DISPLAY_SCALE}  furthest {far:.1f}px from pivot")
    return written


if __name__ == "__main__":
    print("exporting tier creatures:")
    for c in tiers.TIERS.values():
        export(c)
