"""Blockbench projects + machine-readable rigs for all three creatures.

Built from the SHIPPED part models, not re-derived: each `models/item/.../<bone>.json` is
already exact (from/to in model px with the bone pivot at 8,8,8, real UVs, per-element
rotation and light_emission), so the only thing added here is where each bone's pivot sits
in the world and who its parent is. Nothing is reinterpreted, so nothing can drift.

    python3 tools/export_bb.py     ->  blockbench/*.bbmodel  +  rig/*.rig.json
"""
import base64
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rig as sunman                       # noqa: E402
import tiers                               # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "resourcepack" / "assets" / "sunman"
ATLAS = PACK / "textures" / "entity" / "sun_man.png"
BB = ROOT / "blockbench"
RIG = ROOT / "rig"
UV_SCALE = 32.0                            # 0..16 model UV -> 512 px atlas


def _uid(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_OID, ":".join(map(str, parts))))


def _texture():
    raw = base64.b64encode(ATLAS.read_bytes()).decode()
    return {"path": str(ATLAS), "name": "sun_man.png", "folder": "entity",
            "namespace": "sunman", "id": "0", "particle": True, "render_mode": "normal",
            "visible": True, "mode": "bitmap", "saved": False, "uuid": _uid("tex"),
            "source": "data:image/png;base64," + raw}


def build(name, bones, parents, pivots_px, part_dir):
    """bones in parent-first order; pivots_px are world pivots already in model px."""
    elements, groups = [], {}

    for bone in bones:
        src = part_dir / f"{bone}.json"
        px, py, pz = pivots_px[bone]
        kids = []
        if src.exists():
            for i, el in enumerate(json.loads(src.read_text()).get("elements", [])):
                # the part model is authored with the pivot at (8,8,8); shift it to the
                # bone's real place and the whole skeleton assembles in rest pose
                frm = [el["from"][k] - 8.0 + (px, py, pz)[k] for k in range(3)]
                to = [el["to"][k] - 8.0 + (px, py, pz)[k] for k in range(3)]
                faces = {d: {"uv": [round(v * UV_SCALE, 3) for v in f["uv"]], "texture": 0}
                         for d, f in (el.get("faces") or {}).items()}
                e = {"name": f"{bone}_{i}", "box_uv": False, "type": "cube",
                     "uuid": _uid(name, bone, i), "from": [round(v, 4) for v in frm],
                     "to": [round(v, 4) for v in to],
                     "origin": [round(v, 4) for v in (px, py, pz)], "faces": faces}
                r = el.get("rotation")
                if r:
                    o = r.get("origin", [8, 8, 8])
                    e["rotation"] = [r.get("x", 0.0), r.get("y", 0.0), r.get("z", 0.0)]
                    e["origin"] = [round(o[k] - 8.0 + (px, py, pz)[k], 4) for k in range(3)]
                if el.get("light_emission"):
                    e["light_emission"] = el["light_emission"]
                elements.append(e)
                kids.append(e["uuid"])
        groups[bone] = {"name": bone, "uuid": _uid(name, "bone", bone),
                        "origin": [round(px, 4), round(py, 4), round(pz, 4)],
                        "export": True, "isOpen": False, "children": kids}

    # nest, so the hierarchy is the rig and not a flat pile of cubes
    outliner = []
    for bone in bones:
        p = parents.get(bone)
        (groups[p]["children"] if p in groups else outliner).append(groups[bone])

    return {"meta": {"format_version": "4.5", "model_format": "free", "box_uv": False},
            "name": name, "model_identifier": name,
            "resolution": {"width": 512, "height": 512},
            "elements": elements, "outliner": outliner,
            "textures": [_texture()], "animations": []}


def sun_man():
    px = sunman.PX_PER_RU
    sol = sunman.solve(sunman._zero())
    pivots = {b: tuple(sol[b][0][k] * px for k in range(3)) for b in sunman.BONE_ORDER}
    doc = build("sun_man", sunman.BONE_ORDER, sunman.PARENT, pivots,
                PACK / "models" / "item" / "part")
    rigdoc = {
        "name": "sun_man", "height_blocks": round(sunman.model_height(), 3),
        "px_per_block": px, "display_scale": sunman.DISPLAY_SCALE,
        "note": "v5 geometry, shipped verbatim. Do not reshape — surface and animation only.",
        "bones": [{"name": b, "parent": sunman.PARENT.get(b),
                   "pivot_blocks": [round(v, 4) for v in sunman.J[b]],
                   "cubes": len(sunman.GEOMETRY.get(b, []))} for b in sunman.BONE_ORDER],
        "clips": _clips("anim", "CLIPS"),
    }
    return doc, rigdoc


def creature(c):
    px = c.PX_PER_RU
    sol = c.solve(c._zero())
    pivots = {b: tuple(sol[b][0][k] * px for k in range(3)) for b in c.BONE_ORDER}
    parents = {b: c.BONES[b][0] for b in c.BONE_ORDER}
    doc = build(c.name, c.BONE_ORDER, parents, pivots, PACK / "models" / "item" / c.name)
    rigdoc = {
        "name": c.name, "height_blocks": round(c.model_height(), 3),
        "px_per_block": px, "display_scale": c.DISPLAY_SCALE,
        "bones": [{"name": b, "parent": parents.get(b),
                   "pivot_blocks": [round(v, 4) for v in c.J[b]],
                   "cubes": len(c.GEOMETRY.get(b, [])),
                   "materials": sorted({cu["mat"] for cu in c.GEOMETRY.get(b, [])})}
                  for b in c.BONE_ORDER],
        "datapack_clips": {k: {"keyframes": v[1]} for k, v in c.ANIMATIONS.items()},
        "render_clips": _clips("anim_mobs",
                               "LOCUST_CLIPS" if c.name == "locust" else "WALKER_CLIPS"),
    }
    return doc, rigdoc


def _clips(module, attr):
    mod = __import__(module)
    return {k: {"label": v[1], "note": v[2], "fn": f"{module}.{v[0].__name__}"}
            for k, v in getattr(mod, attr).items()}


if __name__ == "__main__":
    BB.mkdir(exist_ok=True)
    RIG.mkdir(exist_ok=True)
    jobs = [sun_man()] + [creature(c) for c in tiers.TIERS.values()]
    for doc, rigdoc in jobs:
        n = doc["name"]
        (BB / f"{n}.bbmodel").write_text(json.dumps(doc))
        (RIG / f"{n}.rig.json").write_text(json.dumps(rigdoc, indent=2))
        print(f"  {n:12} {len(doc['elements']):3d} cubes  "
              f"{len(rigdoc['bones']):2d} bones  {rigdoc['height_blocks']:6.2f} blocks  "
              f"{(BB / f'{n}.bbmodel').stat().st_size // 1024:4d} KB")
