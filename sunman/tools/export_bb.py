"""Blockbench projects + machine-readable rigs for every creature.

    python3 tools/export_bb.py     ->  blockbench/*.bbmodel  +  rig/*.rig.json

Every project is a **Bedrock Entity** model — the format Blockbench mods are animated in: it
keeps per-cube rotations on any axis and per-face UVs, it carries a bone hierarchy with
pivots and rest rotations, and File > Export gives a `.geo.json` + `.animation.json` pair
that GeckoLib and Bedrock read directly. Each project also carries its clips as real
keyframes, so the Animate tab is no longer empty.

The Sun Man is built from the SHIPPED part models, as before: each
`models/item/part/<bone>.json` is already exact (from/to in model px with the bone pivot at
8,8,8, real UVs, per-element rotation), so the only things added are where each bone's pivot
sits and who its parent is. Nothing is reinterpreted, so nothing can drift — the 197 cubes,
29 pivots and per-cube rotations come out exactly as they went in.

The Locust and the Dark Walker are built straight from `tiers.py` at true scale, 16 px to the
block, with the UVs `paint_tiers.layout()` painted. The Birthday People (`birthday.py`, both
variants) are built the same way against their own texture and `paint_birthday.layout()`.

Keyframes are written in the pre-5.0 value convention (Bedrock's), and the file declares
format 4.10, so it opens identically in Blockbench 4.x and 5.x — 5.x converts on load.
"""
import base64
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rig as sunman                       # noqa: E402
import birthday                            # noqa: E402
import paint_birthday                      # noqa: E402
import tiers                               # noqa: E402
from paint_tiers import layout             # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "resourcepack" / "assets" / "sunman"
ATLAS = PACK / "textures" / "entity" / "sun_man.png"
BB = ROOT / "blockbench"
RIG = ROOT / "rig"
UV_SCALE = 32.0                            # 0..16 model UV -> 512 px atlas
FORMAT_VERSION = "4.10"


def _uid(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_OID, ":".join(map(str, parts))))


def _r(v, n=4):
    v = round(float(v), n)
    return 0.0 if v == 0 else v


def _texture(path=ATLAS):
    raw = base64.b64encode(path.read_bytes()).decode()
    return {"name": path.name, "folder": "entity", "namespace": "sunman", "id": "0",
            "particle": True, "render_mode": "default", "render_sides": "auto",
            "frame_time": 1, "frame_order_type": "loop", "frame_order": "",
            "frame_interpolate": False, "visible": True, "internal": True, "saved": False,
            "uuid": _uid("tex") if path == ATLAS else _uid("tex", path.name), "mode": "bitmap", "width": 512, "height": 512,
            "uv_width": 512, "uv_height": 512,
            "source": "data:image/png;base64," + raw}


def _clips(name):
    try:
        mod = __import__(f"clips_{name}")
    except ImportError:
        return []
    return list(mod.CLIPS.values())


def _project(name, elements, groups, bones, parents, clips, px_per_block, visible_box,
             texture=ATLAS):
    outliner = []
    for bone in bones:
        p = parents.get(bone)
        (groups[p]["children"] if p in groups else outliner).append(groups[bone])
    group_uuid = {b: groups[b]["uuid"] for b in bones}
    for clip in clips:
        missing = [b for b in clip.bones() if b not in group_uuid]
        assert not missing, f"{clip.name} keys bones the rig does not have: {missing}"
    return {
        "meta": {"format_version": FORMAT_VERSION, "model_format": "bedrock", "box_uv": False},
        "name": name, "model_identifier": name,
        "visible_box": visible_box,
        "variable_placeholders": "", "variable_placeholder_buttons": [],
        "timeline_setups": [], "unhandled_root_fields": {},
        "resolution": {"width": 512, "height": 512},
        "elements": elements, "outliner": outliner,
        "textures": [_texture(texture)],
        "animations": [c.to_bbmodel(group_uuid, px_per_block) for c in clips],
    }


def _group(name, bone, origin, rotation=(0.0, 0.0, 0.0)):
    return {"name": bone, "origin": [_r(v) for v in origin],
            "rotation": [_r(v, 3) for v in rotation], "color": 0,
            "uuid": _uid(name, "bone", bone), "export": True, "mirror_uv": False,
            "isOpen": False, "locked": False, "visibility": True, "autouv": 0,
            "children": []}


# ====================================================================== Sun Man

def sun_man():
    px = sunman.PX_PER_RU
    sol = sunman.solve(sunman._zero())
    pivots = {b: tuple(sol[b][0][k] * px for k in range(3)) for b in sunman.BONE_ORDER}
    part_dir = PACK / "models" / "item" / "part"
    elements, groups = [], {}
    for bone in sunman.BONE_ORDER:
        bx, by, bz = pivots[bone]
        groups[bone] = _group("sun_man", bone, (bx, by, bz))
        src = part_dir / f"{bone}.json"
        if not src.exists():
            continue
        for i, el in enumerate(json.loads(src.read_text()).get("elements", [])):
            # the part model is authored with the pivot at (8,8,8); shift it to the bone's
            # real place and the whole skeleton assembles in rest pose
            frm = [el["from"][k] - 8.0 + (bx, by, bz)[k] for k in range(3)]
            to = [el["to"][k] - 8.0 + (bx, by, bz)[k] for k in range(3)]
            faces = {d: {"uv": [_r(v * UV_SCALE, 3) for v in f["uv"]], "texture": 0}
                     for d, f in (el.get("faces") or {}).items()}
            e = {"name": f"{bone}_{i}", "box_uv": False, "type": "cube",
                 "uuid": _uid("sun_man", bone, i), "from": [_r(v) for v in frm],
                 "to": [_r(v) for v in to], "origin": [_r(v) for v in (bx, by, bz)],
                 "faces": faces}
            r = el.get("rotation")
            if r:
                o = r.get("origin", [8, 8, 8])
                e["rotation"] = [r.get("x", 0.0), r.get("y", 0.0), r.get("z", 0.0)]
                e["origin"] = [_r(o[k] - 8.0 + (bx, by, bz)[k]) for k in range(3)]
            if el.get("light_emission"):
                e["light_emission"] = el["light_emission"]
            elements.append(e)
            groups[bone]["children"].append(e["uuid"])
    clips = _clips("sun_man")
    doc = _project("sun_man", elements, groups, sunman.BONE_ORDER, sunman.PARENT, clips,
                   px, [3, 6, 0])
    rigdoc = {
        "name": "sun_man", "height_blocks": round(sunman.model_height(), 3),
        "bbmodel_px_per_block": px, "item_px_per_block": px,
        "display_scale": sunman.DISPLAY_SCALE,
        "note": "v5 geometry, shipped verbatim. Do not reshape — surface and animation only.",
        "bones": [{"name": b, "parent": sunman.PARENT.get(b),
                   "pivot_blocks": [round(v, 4) for v in sunman.J[b]],
                   "rest_rotation": [0.0, 0.0, 0.0],
                   "cubes": len(sunman.GEOMETRY.get(b, []))} for b in sunman.BONE_ORDER],
        "clips": _clip_index(clips),
    }
    return doc, rigdoc


# ====================================================================== tiers

def creature(c, uvs=None, texture=ATLAS):
    uvs = uvs or layout()
    elements, groups = [], {}
    for bone in c.BONE_ORDER:
        groups[bone] = _group(c.name, bone, c.J_PX[bone], c.REST.get(bone, (0, 0, 0)))
        for i, cube in enumerate(c.CUBES_PX.get(bone, [])):
            frm = cube["from"]
            to = [frm[k] + cube["size"][k] for k in range(3)]
            faces = {d: {"uv": [_r(v, 3) for v in rect], "texture": 0}
                     for d, rect in uvs[(c.name, bone, i)]["faces"].items()}
            e = {"name": f"{bone}_{cube.get('paint') or cube['mat']}_{i}", "box_uv": False,
                 "type": "cube", "uuid": _uid(c.name, bone, i),
                 "from": [_r(v) for v in frm], "to": [_r(v) for v in to],
                 "origin": [_r(v) for v in cube.get("origin", c.J_PX[bone])], "faces": faces}
            if "rot" in cube:
                e["rotation"] = [_r(v, 3) for v in cube["rot"]]
            if cube.get("emit"):
                e["light_emission"] = int(cube["emit"])
            elements.append(e)
            groups[bone]["children"].append(e["uuid"])
    clips = _clips(c.name)
    lo, hi = c.extents({})
    xlo, xhi = c.extents({}, 0)
    doc = _project(c.name, elements, groups, c.BONE_ORDER, c.parents, clips,
                   c.BB_PX_PER_BLOCK, [round(max(1.0, xhi - xlo) + 0.5, 1),
                                       round(hi - lo + 0.5, 1), 0], texture)
    rigdoc = {
        "name": c.name, "height_blocks": round(hi - lo, 3),
        "bbmodel_px_per_block": c.BB_PX_PER_BLOCK, "item_px_per_block": c.PX_PER_RU,
        "display_scale": c.DISPLAY_SCALE,
        "texture": f"sunman:entity/{texture.stem}",
        "bones": [{"name": b, "parent": c.parents.get(b),
                   "pivot_blocks": [round(v, 4) for v in c.J[b]],
                   "rest_rotation": list(c.REST.get(b, (0.0, 0.0, 0.0))),
                   "cubes": len(c.GEOMETRY.get(b, [])),
                   "materials": sorted({cu["mat"] for cu in c.GEOMETRY.get(b, [])})}
                  for b in c.BONE_ORDER],
        "clips": _clip_index(clips),
    }
    return doc, rigdoc


def _clip_index(clips):
    return {c.name: {"loop": c.loop, "length": c.length, "note": c.note,
                     "keys": sum(len(v) for v in c.tracks.values())} for c in clips}


def jobs():
    people = paint_birthday.layout()
    return ([sun_man()] + [creature(c) for c in tiers.TIERS.values()]
            + [creature(c, people, paint_birthday.TEXTURE) for c in birthday.PEOPLE.values()])


if __name__ == "__main__":
    BB.mkdir(exist_ok=True)
    RIG.mkdir(exist_ok=True)
    for doc, rigdoc in jobs():
        n = doc["name"]
        (BB / f"{n}.bbmodel").write_text(json.dumps(doc))
        (RIG / f"{n}.rig.json").write_text(json.dumps(rigdoc, indent=2, ensure_ascii=False) + "\n")
        print(f"  {n:12} {len(doc['elements']):3d} cubes  {len(rigdoc['bones']):2d} bones  "
              f"{len(doc['animations']):2d} clips  {rigdoc['height_blocks']:6.2f} blocks  "
              f"{(BB / f'{n}.bbmodel').stat().st_size // 1024:4d} KB")
