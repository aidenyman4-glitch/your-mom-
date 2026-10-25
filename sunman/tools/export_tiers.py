"""Emits the tier creatures as vanilla 26.3 item models, one per bone.

Same conventions as `export_models.py` does for the Sun Man — a bone's cubes are written
with the bone pivot at model (8,8,8), UVs in the 0..16 space vanilla uses regardless of
texture resolution, and one `items/` definition per part pointing at its model. The UVs are
the ones `paint_tiers.layout()` painted, so the item models and the Blockbench projects show
exactly the same skin.

Models are written at `creature.PX_PER_RU` px per block (16 / display_scale) and the
item_display scale undoes it; that keeps the Dark Walker's longest bone inside the
[-16, 32] box. A bone's REST rotation is not baked in here — it is a bone transform, and the
pose baker applies it along with the animation (see `tiers.Creature.solve`).

Emissive cubes carry `light_emission`, which 26.3 accepts per element: the Dark Walker's
eyes are lit at 15 and are the only part of it that is ever its own light source.

Models for bones that no longer exist (the old wrist and ankle bones) are removed, so the
pack never ships a part nothing poses.

    python3 tools/export_tiers.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tiers                              # noqa: E402
from paint_tiers import layout            # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "resourcepack" / "assets" / "sunman"
UV_PER_TEXEL = 16.0 / 512.0


def _r(v, n=4):
    v = round(float(v), n)
    return 0.0 if v == 0 else v


def _element(cube, px_per_ru, faces_px):
    s = px_per_ru
    frm = [8.0 + c * s for c in cube["from"]]
    to = [frm[i] + cube["size"][i] * s for i in range(3)]
    faces = {d: {"uv": [_r(v * UV_PER_TEXEL) for v in rect], "texture": "#0"}
             for d, rect in faces_px.items()}
    el = {"from": [_r(v, 3) for v in frm], "to": [_r(v, 3) for v in to], "faces": faces}
    rot = cube.get("rotation")
    if rot:
        # 26.3 takes arbitrary Euler XYZ here; the old single-axis 22.5 degree limit is gone.
        o = rot["origin"]
        el["rotation"] = {"origin": [_r(8.0 + o[i] * s, 3) for i in range(3)],
                          "x": _r(rot["x"], 3), "y": _r(rot["y"], 3), "z": _r(rot["z"], 3)}
    if cube.get("emit"):
        el["light_emission"] = int(cube["emit"])
    return el


def export(creature, uvs=None):
    uvs = uvs or layout()
    models = PACK / "models" / "item" / creature.name
    items = PACK / "items"
    models.mkdir(parents=True, exist_ok=True)
    items.mkdir(parents=True, exist_ok=True)

    written, lit, far = [], 0, 0.0
    for bone in creature.BONE_ORDER:
        cubes = creature.GEOMETRY.get(bone)
        if not cubes:
            continue
        elements = [_element(c, creature.PX_PER_RU, uvs[(creature.name, bone, i)]["faces"])
                    for i, c in enumerate(cubes)]
        lit += sum(1 for e in elements if "light_emission" in e)
        far = max([far] + [abs(v - 8.0) for e in elements for v in e["from"] + e["to"]])
        (models / f"{bone}.json").write_text(json.dumps({
            "textures": {"0": "sunman:entity/sun_man", "particle": "sunman:entity/sun_man"},
            "elements": elements,
            "gui_light": "front",
        }, indent=2) + "\n")
        (items / f"{creature.name}_{bone}.json").write_text(json.dumps({
            "model": {"type": "minecraft:model",
                      "model": f"sunman:item/{creature.name}/{bone}"}
        }, indent=2))
        written.append(bone)

    stale = [p for p in models.glob("*.json") if p.stem not in written]
    stale += [p for p in items.glob(f"{creature.name}_*.json")
              if p.stem[len(creature.name) + 1:] not in written]
    for p in stale:
        p.unlink()
    print(f"  {creature.name:12} {len(written):2d} parts  "
          f"{sum(len(creature.GEOMETRY[b]) for b in written):3d} cubes  "
          f"{lit} emissive  scale {creature.DISPLAY_SCALE}  furthest {far:.1f}px from pivot  "
          f"removed {len(stale)} stale files")
    assert far <= 24.0, "an element left the [-16, 32] box Blockbench opens"
    return written


if __name__ == "__main__":
    print("exporting tier creatures:")
    uv = layout()
    for c in tiers.TIERS.values():
        export(c, uv)
