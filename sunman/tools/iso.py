"""Isometric renders of an emulated world: the way to LOOK at what the datapack did.

Blocks are drawn with Minecraft 26.3's own textures (fetched by mcdata, never shipped), the
pack's entities in place: blood decals with their real textures at their real yaw, wall
smears, the dead villagers and the Locusts from their actual geometry, items left behind.
Two views: the whole village from above, and a cutaway with everything above the ground floor
lifted off, so the inside of the houses can be seen.

Used by tools/village_sim.py.
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mcdata                                                    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TW = 24                       # a block's top face is TW wide on screen
H = TW // 2                   # and the cube's side is H tall

_tex = {}


def texture(name):
    """A 16x16 RGBA block texture from 26.3, or None."""
    if name in _tex:
        return _tex[name]
    im = None
    try:
        data = mcdata._fetch("assets", f"assets/minecraft/textures/block/{name}.png")
        import io
        im = Image.open(io.BytesIO(data)).convert("RGBA")
        im = im.crop((0, 0, 16, 16)) if im.height > 16 else im
    except Exception:
        im = None
    _tex[name] = im
    return im


TINT = {"grass_block_top": (124, 189, 107), "short_grass": (124, 189, 107), "tall_grass_bottom": (124, 189, 107),
        "oak_leaves": (96, 160, 64), "fern": (110, 170, 90), "water_still": (63, 118, 228)}


_tinted = {}


def tinted(name):
    im = texture(name)
    if im is None or name not in TINT:
        return im
    if name in _tinted:
        return _tinted[name]
    r, g, b = TINT[name]
    px = im.load()
    out = im.copy()
    po = out.load()
    for y in range(im.height):
        for x in range(im.width):
            c = px[x, y]
            po[x, y] = (c[0] * r // 255, c[1] * g // 255, c[2] * b // 255, c[3])
    _tinted[name] = out
    return out


def faces_for(bid, props):
    """(top texture, side texture, shape) for a block id."""
    base = bid
    for suf in ("_stairs", "_slab", "_fence_gate", "_fence", "_wall", "_pressure_plate", "_button"):
        if bid.endswith(suf):
            base = bid[: -len(suf)]
            break
    material = {"oak": "oak_planks", "spruce": "spruce_planks", "birch": "birch_planks",
                "dark_oak": "dark_oak_planks", "acacia": "acacia_planks", "jungle": "jungle_planks",
                "cobblestone": "cobblestone", "mossy_cobblestone": "mossy_cobblestone",
                "stone_brick": "stone_bricks", "mossy_stone_brick": "mossy_stone_bricks",
                "blackstone": "blackstone", "smooth_stone": "smooth_stone", "stone": "stone",
                "sandstone": "sandstone", "polished_blackstone_brick": "polished_blackstone_bricks"}
    shape = "cube"
    if bid.endswith("_stairs"):
        shape = "stairs"
    elif bid.endswith("_slab"):
        shape = {"top": "slab_top", "double": "cube"}.get(props.get("type"), "slab")
    elif bid.endswith("_fence") or bid.endswith("_wall"):
        shape = "post"
    elif bid.endswith("_fence_gate"):
        shape = "post"
    if base != bid:
        t = material.get(base, base + "_planks" if texture(base + "_planks") else base)
        return t, t, shape
    if bid.endswith("_log") or bid.endswith("_wood") or bid in ("hay_block", "barrel", "composter",
                                                                    "crafting_table", "smoker", "furnace",
                                                                    "blast_furnace", "fletching_table",
                                                                    "smithing_table", "cartography_table",
                                                                    "loom", "bookshelf", "lectern", "chest"):
        top = {"bookshelf": "oak_planks", "chest": "oak_planks", "lectern": "lectern_top"}.get(bid, bid + "_top")
        side = {"bookshelf": "bookshelf", "chest": "oak_planks", "barrel": "barrel_side",
                "composter": "composter_side", "crafting_table": "crafting_table_front",
                "furnace": "furnace_front", "smoker": "smoker_front", "blast_furnace": "blast_furnace_front",
                "lectern": "lectern_sides", "fletching_table": "fletching_table_front",
                "smithing_table": "smithing_table_front", "cartography_table": "cartography_table_side1",
                "loom": "loom_front"}.get(bid, bid if not bid.endswith("_wood") else bid.replace("_wood", "_log"))
        if bid.endswith("_wood"):
            top = side
        return top, side, "cube"
    if bid == "grass_block":
        return "grass_block_top", "grass_block_side", "cube"
    if bid == "dirt_path":
        return "dirt_path_top", "dirt_path_side", "path"
    if bid == "farmland":
        return "farmland", "dirt", "path"
    if bid.endswith("_door"):
        return bid + "_bottom", bid + "_bottom", "thin"
    if bid.endswith("glass_pane"):
        return bid.replace("_pane", ""), bid.replace("_pane", ""), "thin"
    if bid.endswith("_carpet"):
        return bid.replace("_carpet", "_wool"), bid.replace("_carpet", "_wool"), "carpet"
    if bid.endswith("_bed"):
        return bid.replace("_bed", "_wool"), bid.replace("_bed", "_wool"), "slab"
    if bid in ("torch", "wall_torch", "soul_torch", "lantern", "dead_bush", "cobweb", "short_grass", "fern",
               "poppy", "dandelion", "oxeye_daisy", "cornflower", "azure_bluet", "wheat", "carrots",
               "potatoes", "beetroots", "bell", "campfire"):
        tex = {"wall_torch": "torch", "wheat": "wheat_stage7", "carrots": "carrots_stage3",
               "potatoes": "potatoes_stage3", "beetroots": "beetroots_stage3", "bell": "bell_bottom",
               "campfire": "campfire_log"}.get(bid, bid)
        return tex, tex, "sprite"
    if bid == "water":
        return "water_still", "water_still", "water"
    if texture(bid):
        return bid, bid, "cube"
    if texture(bid + "_top"):
        return bid + "_top", bid + "_side" if texture(bid + "_side") else bid + "_top", "cube"
    return None, None, "cube"


# ====================================================================== projection

def P(x, y, z):
    return ((x - z) * TW / 2, (x + z) * TW / 4 - y * H)


def _affine_for(tri_dst, size_src):
    """Coefficients mapping output pixel -> source pixel for a parallelogram given by three
    screen points: origin, +u end, +v end (u, v along the source's x and y)."""
    (ox, oy), (ux, uy), (vx, vy) = tri_dst
    w, h = size_src
    a, b = (ux - ox) / w, (vx - ox) / h
    c, d = (uy - oy) / w, (vy - oy) / h
    det = a * d - b * c
    ia, ib, ic, idd = d / det, -b / det, -c / det, a / det
    return (ia, ib, -(ia * ox + ib * oy), ic, idd, -(ic * ox + idd * oy))


def quad(canvas, img, o, u, v, shade=1.0):
    """Paste `img` mapped onto the parallelogram o, o+u, o+v (screen coordinates)."""
    if img is None:
        return
    xs = [o[0], u[0], v[0], u[0] + v[0] - o[0]]
    ys = [o[1], u[1], v[1], u[1] + v[1] - o[1]]
    x0, y0 = int(math.floor(min(xs))), int(math.floor(min(ys)))
    x1, y1 = int(math.ceil(max(xs))) + 1, int(math.ceil(max(ys))) + 1
    if x1 - x0 <= 0 or y1 - y0 <= 0:
        return
    coeffs = _affine_for(((o[0] - x0, o[1] - y0), (u[0] - x0, u[1] - y0), (v[0] - x0, v[1] - y0)), img.size)
    tile = img.transform((x1 - x0, y1 - y0), Image.AFFINE, coeffs, resample=Image.NEAREST)
    if shade != 1.0:
        r, g, b, a = tile.split()
        r, g, b = (ch.point(lambda p: int(p * shade)) for ch in (r, g, b))
        tile = Image.merge("RGBA", (r, g, b, a))
    # keep only the inside of the parallelogram (transform fills outside with source edges)
    mask = Image.new("L", tile.size, 0)
    ImageDraw.Draw(mask).polygon([(o[0] - x0, o[1] - y0), (u[0] - x0, u[1] - y0),
                                  (u[0] + v[0] - o[0] - x0, u[1] + v[1] - o[1] - y0), (v[0] - x0, v[1] - y0)], fill=255)
    alpha = Image.fromarray(np.minimum(np.array(mask), np.array(tile.getchannel("A"))))
    canvas.paste(tile, (x0, y0), alpha)


def poly(canvas, pts, color, shade=1.0, alpha=255):
    c = tuple(int(v * shade) for v in color[:3]) + (alpha,)
    ImageDraw.Draw(canvas).polygon(pts, fill=c)


# ====================================================================== the world

OPAQUE_SHAPES = {"cube"}


def render_world(blocks, entities, centre, out, title="", radius=26, cutaway=None, tile=24):
    global TW, H
    TW, H = tile, tile // 2
    cx, cy, cz = centre
    keep = {}
    for p, (bid, props) in blocks.items():
        if abs(p[0] - cx) > radius or abs(p[2] - cz) > radius:
            continue
        if p[1] < cy - 3:
            continue
        if cutaway is not None and p[1] > cutaway:
            continue
        keep[p] = (bid, props)

    def opaque(p):
        b = keep.get(p)
        if not b:
            return False
        return faces_for(*b)[2] in OPAQUE_SHAPES and not b[0].endswith("glass") and b[0] != "water"

    items = []
    for p, (bid, props) in keep.items():
        x, y, z = p
        if opaque((x, y + 1, z)) and opaque((x + 1, y, z)) and opaque((x, y, z + 1)):
            continue
        items.append(((x + z) * 4 + y * 2 + 0.0, "block", p, bid, props))
    for e in entities:
        if abs(e.pos[0] - cx) > radius or abs(e.pos[2] - cz) > radius:
            continue
        if cutaway is not None and e.pos[1] > cutaway + 1:
            continue
        x, y, z = e.pos
        items.append(((math.floor(x) + math.floor(z)) * 4 + math.floor(y + 1e-6) * 2 + 1.5, "entity", e))
    items.sort(key=lambda it: it[0])

    # canvas bounds
    xs, ys = [], []
    for dx in (-radius, radius + 1):
        for dz in (-radius, radius + 1):
            for dy in (-4, 14):
                sx, sy = P(cx + dx, cy + dy, cz + dz)
                xs.append(sx)
                ys.append(sy)
    ox, oy = -min(xs) + 10, -min(ys) + 30
    W, Hh = int(max(xs) - min(xs) + 20), int(max(ys) - min(ys) + 40)
    canvas = Image.new("RGBA", (W, Hh), (34, 34, 40, 255))

    def S(x, y, z):
        sx, sy = P(x, y, z)
        return (sx + ox, sy + oy)

    for it in items:
        if it[1] == "block":
            _, _, (x, y, z), bid, props = it
            draw_block(canvas, S, x, y, z, bid, props)
        else:
            draw_entity(canvas, S, it[2])

    if title:
        d = ImageDraw.Draw(canvas)
        try:
            import cine
            font = ImageFont.truetype(cine.FONT, 18)
        except Exception:
            font = None
        d.text((14, 8), title, fill=(230, 222, 214), font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, optimize=True)
    return out


def draw_block(canvas, S, x, y, z, bid, props):
    top, side, shape = faces_for(bid, props)
    ttex, stex = tinted(top) if top else None, tinted(side) if side else None
    if ttex is None and stex is None:
        ttex = stex = Image.new("RGBA", (16, 16), (128, 128, 128, 255))
    h0, h1 = 0.0, 1.0
    inset = 0.0
    if shape == "slab":
        h1 = 0.5
    elif shape == "slab_top":
        h0 = 0.5
    elif shape == "path":
        h1 = 15 / 16
    elif shape == "carpet":
        h1 = 1 / 16
    elif shape == "stairs":
        h1 = 0.75
    elif shape in ("post", "thin"):
        inset = 6 / 16 if shape == "post" else 7 / 16
    elif shape == "water":
        h1 = 14 / 16
    if shape == "sprite":
        im = ttex
        if im is None:
            return
        a = S(x + 0.15, y + 1, z + 0.85)
        b = S(x + 0.85, y + 1, z + 0.15)
        c = S(x + 0.15, y, z + 0.85)
        quad(canvas, im, a, b, c)
        return
    x0, x1, z0, z1 = x + inset, x + 1 - inset, z + inset, z + 1 - inset
    # east (+x) face, south (+z) face, then the top
    quad(canvas, stex, S(x1, y + h1, z0), S(x1, y + h1, z1), S(x1, y + h0, z0), 0.62)
    quad(canvas, stex, S(x0, y + h1, z1), S(x1, y + h1, z1), S(x0, y + h0, z1), 0.8)
    quad(canvas, ttex, S(x0, y + h1, z0), S(x1, y + h1, z0), S(x0, y + h1, z1), 1.0)


# ====================================================================== entities

_decal_cache = {}


def _decal_img(model):
    if model not in _decal_cache:
        name = model.split(":")[-1]
        p = ROOT / "resourcepack" / "assets" / "sunman" / "textures" / "decal" / f"{name}.png"
        im = Image.open(p).convert("RGBA")
        # rendered at a fixed light of sky 4: darker than the world round it
        r, g, b, a = im.split()
        r, g, b = (ch.point(lambda v: int(v * 0.62)) for ch in (r, g, b))
        _decal_cache[model] = Image.merge("RGBA", (r, g, b, a))
    return _decal_cache[model]


def _rot_y(v, yaw):
    """Minecraft yaw: 0 faces +Z; +90 faces -X. Rotates an entity-local vector into the world,
    including the half turn item_display applies to every item model."""
    a = math.radians(yaw)
    x, y, z = -v[0], v[1], -v[2]                         # the item_display half turn
    return (x * math.cos(a) - z * math.sin(a), y, x * math.sin(a) + z * math.cos(a))


def draw_entity(canvas, S, e):
    model = (e.nbt.get("item") or {}).get("components", {}).get("minecraft:item_model", "")
    x, y, z = e.pos
    if e.type == "item_display" and "decal/" not in model and model.startswith("sunman:blood"):
        im = _decal_img(model)
        sizes = {"blood_pool": (2, 2), "blood_splatter": (2, 2), "blood_trail": (1, 2), "blood_smear": (1, 1.5)}
        w, d = sizes[model.split(":")[-1]]
        if model.endswith("smear"):
            # standing on a wall, facing its yaw
            o = _rot_y((w / 2, d / 2, 0), e.rot[0])
            u = _rot_y((-w / 2, d / 2, 0), e.rot[0])
            v = _rot_y((w / 2, -d / 2, 0), e.rot[0])
            quad(canvas, im, S(x + o[0], y + o[1], z + o[2]), S(x + u[0], y + u[1], z + u[2]),
                 S(x + v[0], y + v[1], z + v[2]), 0.9)
            return
        o = _rot_y((-w / 2, 0, -d / 2), e.rot[0])
        u = _rot_y((w / 2, 0, -d / 2), e.rot[0])
        v = _rot_y((-w / 2, 0, d / 2), e.rot[0])
        quad(canvas, im, S(x + o[0], y + 0.01, z + o[2]), S(x + u[0], y + 0.01, z + u[2]),
             S(x + v[0], y + 0.01, z + v[2]))
        return
    if e.type == "item_display" and model.split(":")[-1] in __import__("props").PROPS:
        draw_corpse(canvas, S, e, model.split(":")[-1])
        return
    if e.type == "interaction" and "sunman_locust" in e.tags:
        draw_locust(canvas, S, e)
        return
    if e.type == "item":
        a = S(x - 0.15, y + 0.1, z - 0.15)
        b = S(x + 0.15, y + 0.1, z - 0.15)
        c = S(x + 0.15, y + 0.1, z + 0.15)
        dd = S(x - 0.15, y + 0.1, z + 0.15)
        poly(canvas, [a, b, c, dd], (214, 196, 120))


def _draw_boxes(canvas, S, boxes):
    """boxes: [(8 world corners, colour)]; corners ordered (dx, dy, dz) in {0,1}^3 binary."""
    faces = []
    for corners, col in boxes:
        for name, idx in (("top", [2, 6, 7, 3]), ("east", [4, 6, 7, 5]), ("south", [1, 3, 7, 5]),
                          ("west", [0, 2, 3, 1]), ("north", [0, 4, 6, 2]), ("bottom", [0, 1, 5, 4])):
            pts = [corners[i] for i in idx]
            # back-face cull against the iso view direction (looking toward -x, -y, -z)
            a, b, c = pts[0], pts[1], pts[2]
            nx = (b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1])
            ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
            nz = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            cen = [sum(p[k] for p in pts) / 4 for k in range(3)]
            mid = [sum(p[k] for p in corners) / 8 for k in range(3)]
            out = [cen[k] - mid[k] for k in range(3)]
            if nx * out[0] + ny * out[1] + nz * out[2] < 0:
                nx, ny, nz = -nx, -ny, -nz
            view = nx * 1 + ny * 1.2 + nz * 1
            if view <= 0:
                continue
            ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1
            shade = 0.55 + 0.45 * max(0.0, ny / ln) + 0.15 * max(0.0, nz / ln)
            depth = cen[0] + cen[2] + cen[1] * 0.5
            faces.append((depth, [S(*p) for p in pts], col, min(1.0, shade)))
    faces.sort(key=lambda f: f[0])
    for _, pts, col, shade in faces:
        poly(canvas, pts, col, shade)


def draw_corpse(canvas, S, e, name):
    """Any of the village props, from its real geometry (props.py), at the entity's yaw.
    Colour is each material's mid tone; dead grass is drawn as straw-coloured planes."""
    import props
    parts, _, _ = props.parts_of(name)
    boxes = []
    for c in parts:
        col = props.RAMPS[c["mat"]][2 if c["paint"] != "blades" else 3]
        cs = []
        for p in props._corners(c):
            w = _rot_y((p[0] / 16, p[1] / 16, p[2] / 16), e.rot[0])
            cs.append((e.pos[0] + w[0], e.pos[1] + w[1], e.pos[2] + w[2]))
        boxes.append((cs, col))
    _draw_boxes(canvas, S, boxes)


def draw_locust(canvas, S, e):
    import paint_tiers
    import tiers
    from export_datapack import _LOCUST_POSES
    from rig import mat_vec
    c = tiers.LOCUST
    pose = _LOCUST_POSES["full" if e.nbt.get("height", 3.4) > 3.2 else "cramped"]
    sol = c.solve_m(pose)
    lo = c.extents(pose)[0]
    boxes = []
    a = math.radians(e.rot[0])
    for bone, cubes in c.GEOMETRY.items():
        pos, m = sol[bone]
        for cu in cubes:
            col = paint_tiers.RAMPS[cu["mat"]][2]
            cs = []
            for p in c._cube_corners(cu):
                wpt = mat_vec(m, p)
                wx, wy, wz = pos[0] + wpt[0], pos[1] + wpt[1] - lo, pos[2] + wpt[2]
                # entity yaw (the creature's +Z is its front, kept by the baked flip)
                rx_ = wx * math.cos(a) - wz * math.sin(a)
                rz_ = wx * math.sin(a) + wz * math.cos(a)
                cs.append((e.pos[0] + rx_, e.pos[1] + wy, e.pos[2] + rz_))
            boxes.append((cs, col))                    # corners ordered (dx, dy, dz), like props
    _draw_boxes(canvas, S, boxes)
