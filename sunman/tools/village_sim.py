"""The Abandoned Village, run on a real village without a server.

Builds a plains village from Minecraft 26.3's own structure templates (the meeting point with
its bell, houses, farms, lamps, the paths between them), puts villagers in it who remember
where their bell is, puts a player 40 blocks off, and runs the generated datapack on it in
the command emulator (tools/mcemu.py): load, the slow pass, the trigger, the decay. Then it
checks what is left, renders it before and after (docs/village_before.png,
docs/village_after.png), and tries to break it: a second slow pass, the manual command on
top of it, a pen of villagers with no bell, the switch turned off.

    python3 tools/village_sim.py            # run, check, render
    python3 tools/village_sim.py --seed 7   # another roll of the dice

check_datapack.py calls test() and fails on any problem it reports.
"""
import collections
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mcemu                                                   # noqa: E402
from check_datapack import load_pack                           # noqa: E402
from mcdata import MC                                          # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GROUND = 63

# piece, template-origin offset (x, z) from the meeting point's origin. Unrotated; the
# spacing follows a real plains village's: houses 6-20 blocks from the bell, farms further.
LAYOUT = [
    ("town_centers/plains_meeting_point_1", (0, 0)),
    ("houses/plains_small_house_1", (-11, -2)),
    ("houses/plains_small_house_3", (14, 1)),
    ("houses/plains_medium_house_1", (-3, 13)),
    ("houses/plains_butcher_shop_1", (2, -16)),
    ("houses/plains_library_1", (13, -14)),
    ("houses/plains_tool_smith_1", (-17, -15)),
    ("houses/plains_small_house_5", (-15, 9)),
    ("houses/plains_small_farm_1", (13, 13)),
    ("houses/plains_large_farm_1", (24, -2)),
    ("houses/plains_armorer_house_1", (-27, -3)),
    ("plains_lamp_1", (6, 9)),
    ("plains_lamp_1", (-6, -8)),
    ("plains_lamp_1", (9, -5)),
]


def place(world, name, ox, oz, oy=GROUND):
    s = MC.structure(f"village/plains/{name}")
    pal = s["palette"]
    bell = None
    for b in s["blocks"]:
        st = pal[b["state"]]
        bid = mcemu.strip_ns(st["id"])
        props = dict(st.get("properties", {}))
        if bid == "structure_void":
            continue
        if bid == "jigsaw":
            final = (b.get("nbt") or {}).get("final_state", "minecraft:air")
            _, bid, props = mcemu.parse_block(final)
            if bid == "structure_void":
                continue
        x, y, z = b["pos"]
        p = (ox + x, oy + y, oz + z)
        world.set_block(p, bid, {**MC.block_defaults(bid), **props})
        if bid == "bell":
            bell = p
    return s["size"], bell


def terrain(world, r=40):
    for x in range(-r, r + 1):
        for z in range(-r, r + 1):
            world.set_block((x, GROUND, z), "grass_block", {"snowy": "false"})
            for y in range(GROUND - 3, GROUND):
                world.set_block((x, y, z), "dirt", {})
            for y in range(GROUND - 6, GROUND - 3):
                world.set_block((x, y, z), "stone", {})


def paths(world, centre, targets):
    cx, cz = centre
    for tx, tz in targets:
        x, z = cx, cz
        while (x, z) != (tx, tz):
            if x != tx:
                x += 1 if tx > x else -1
            elif z != tz:
                z += 1 if tz > z else -1
            if world.block((x, GROUND, z))[0] == "grass_block" and world.block((x, GROUND + 1, z))[0] in mcemu.AIR:
                world.set_block((x, GROUND, z), "dirt_path", {})


def build(seed=1):
    funcs, tags, _ = load_pack()
    w = mcemu.World(funcs, tags, seed=seed)
    terrain(w)
    bell, doors = None, []
    for name, (ox, oz) in LAYOUT:
        size, b = place(w, name, ox, oz)
        bell = bell or b
        doors.append((ox + size[0] // 2, oz + size[2] // 2))
    paths(w, (bell[0], bell[2]), doors)
    return w, bell


def populate(w, bell, n=7, with_bell=True):
    rng = w.rng
    for i in range(n):
        a = i * math.tau / n
        pos = (bell[0] + 0.5 + math.cos(a) * rng.uniform(4, 14), GROUND + 1, bell[2] + 0.5 + math.sin(a) * rng.uniform(4, 14))
        nbt = {"Brain": {"memories": {"minecraft:meeting_point": {"value": {
            "dimension": "minecraft:overworld", "pos": list(bell)}}}}} if with_bell else {}
        w.summon("villager", pos, nbt)
    gx, gz = bell[0] + 6, bell[2] - 4
    gy = max(y for (x, y, z) in w.blocks if x == gx and z == gz) + 1      # on the surface
    w.summon("iron_golem", (gx + 0.5, gy, gz + 0.5))


def player(w, pos):
    return w.summon("player", pos, {"gamemode": "survival"})


BOX = (-16, -6, -16, 16, 10, 16)


def in_box(p, c):
    return all(c[i] + BOX[i] <= p[i] <= c[i] + BOX[i + 3] for i in range(3))


def census(w, c):
    cnt = collections.Counter()
    states = collections.Counter()
    for p, (bid, props) in w.blocks.items():
        if in_box(p, c):
            cnt[bid] += 1
            if bid.endswith("stairs") or bid.endswith("slab"):
                key = tuple(sorted((k, v) for k, v in props.items() if k in ("facing", "half", "shape", "type")))
                states[(bid.replace("mossy_", ""), key)] += 1
    return cnt, states


def run_pass(w, fid, ctx=None, ticks=8):
    """Run a function, then let `ticks` game ticks pass so anything it scheduled runs.
    Returns the largest number of commands any one call needed."""
    w.spent = 0
    w.max_spent = 0
    r = w.call(fid, ctx or mcemu.Ctx())
    first = w.spent
    w.advance(ticks, skip=("sunman:slow",))
    return r, max(first, w.max_spent)


def test(seed=1, render=False, verbose=False):
    problems = []
    w, bell = build(seed)
    populate(w, bell)
    pl = player(w, (bell[0] + 40.5, GROUND + 1, bell[2] + 0.5))
    before, st_before = census(w, bell)
    snapshot = dict(w.blocks)

    run_pass(w, "sunman:load")
    _, spent = run_pass(w, "sunman:slow")
    after, st_after = census(w, bell)
    ents = w.alive()

    def tagged(t, typ=None):
        return [e for e in ents if t in e.tags and (typ is None or e.type == typ)]

    markers = tagged("sunman_decayed", "marker")
    report = {}
    if len(markers) != 1:
        problems.append(f"expected one sunman_decayed marker after the slow pass, found {len(markers)}")
        return problems
    c = markers[0].pos
    if (math.floor(c[0]), math.floor(c[1]), math.floor(c[2])) != bell:
        problems.append(f"the village was centred at {c}, not at its bell {bell}")
    report["most_commands_in_one_call"] = spent
    if spent > 65536 // 2:
        problems.append(f"one call ran {spent} commands: too near max_command_sequence_length (65536)")
    if tagged_all(w, "sm_decay_job"):
        problems.append("the decay job never finished")

    # 3.1 - 3.4 and the doors
    gone = ["torch", "wall_torch", "campfire", "soul_campfire", "glass", "glass_pane", "wheat", "carrots",
            "potatoes", "beetroots", "farmland", "dirt_path", "cobblestone", "cobblestone_stairs",
            "cobblestone_slab", "stone_bricks", "oak_door", "spruce_door"]
    gone += [b for b in before if b.endswith("_bed") or b.endswith("_banner") or b.endswith("_wool")
             or b.endswith("_carpet") or b.endswith("_sign") or b.endswith("glass_pane")]
    for b in gone:
        if after.get(b):
            problems.append(f"{after[b]} {b} left inside the box")
    if after.get("lantern", 0) != before.get("lantern", 0):
        problems.append(f"lanterns: {before.get('lantern', 0)} before, {after.get('lantern', 0)} after (they must stay)")
    if before.get("cobblestone_stairs"):
        want = collections.Counter({k[1]: v for k, v in st_before.items() if k[0] == "cobblestone_stairs"})
        got = collections.Counter({k[1]: v for k, v in st_after.items() if k[0] == "cobblestone_stairs"})
        lost = want - got
        if lost:
            problems.append(f"stair states changed in conversion: {dict(lost)}")
    report["wood_removed"] = sum(v for k, v in before.items() if k.endswith("planks") or k.endswith("stairs")
                                 or k.endswith("slab") or k.endswith("fence")) - \
        sum(v for k, v in after.items() if k.endswith("planks") or k.endswith("stairs")
            or k.endswith("slab") or k.endswith("fence"))
    report["cobwebs"] = after.get("cobweb", 0)
    report["dead_bushes"] = after.get("dead_bush", 0)

    # the living
    living = [e for e in ents if e.type in ("villager", "iron_golem") and math.dist(e.pos, c) <= 48]
    if living:
        problems.append(f"{len(living)} villagers/golems still alive in the village")

    # the dead, the blood, what was left
    corpses = [e for e in tagged("sunman_corpse", "item_display")
               if e.nbt["item"]["components"]["minecraft:item_model"][-2:] in ("_a", "_b", "_c")]
    pieces = [e for e in tagged("sunman_corpse", "item_display") if e not in corpses]
    blood = tagged("sunman_blood", "item_display")
    smears = [e for e in blood if e.nbt["item"]["components"]["minecraft:item_model"].endswith("smear")]
    floor_blood = [e for e in blood if e not in smears]
    items = [e for e in ents if e.type == "item"]
    cores = tagged("sunman_core", "interaction")
    bones = tagged("sunman_locust_part", "item_display")
    golems = [e for e in tagged("sunman_golem", "item_display")]
    crosses = [e for e in tagged("sunman_crucified", "item_display")]
    grass = [e for e in tagged("sunman_dead_grass", "item_display")]
    wood = [e for e in tagged("sunman_debris", "item_display")]
    pieces = [e for e in pieces if e not in golems and e not in crosses]
    report.update(golems=len(golems), crucified=len(crosses), dead_grass=len(grass), broken_wood=len(wood))
    if len(golems) != 1:
        problems.append(f"{len(golems)} dead iron golems (the village had one)")
    if len(crosses) != 1:
        problems.append(f"{len(crosses)} crucified villagers (one, on a roof, wanted)")
    for e in crosses:
        x, y, z = (math.floor(v) for v in e.pos)
        if math.dist((e.pos[0], e.pos[2]), (bell[0] + 0.5, bell[2] + 0.5)) < 6:
            problems.append("the cross is over the bell, not on a house")
        if y < bell[1] + 4:
            problems.append(f"the crucified villager is at y {y}, not up on a roof (bell at {bell[1]})")
        if w.block((x, y - 1, z))[0] not in w.tag_members("sunman:smashable") | w.tag_members("sunman:solid"):
            problems.append(f"the cross stands on {w.block((x, y - 1, z))[0]}, not on a building")
        bx, bz = bell[0] + 0.5 - e.pos[0], bell[2] + 0.5 - e.pos[2]
        want = math.degrees(math.atan2(-bx, bz))
        if abs((e.rot[0] - want + 180) % 360 - 180) > 2:
            problems.append(f"the cross faces yaw {e.rot[0]:.0f}, not the bell ({want:.0f})")
    if len(grass) < 15:
        problems.append(f"only {len(grass)} tufts of dead grass")
    if len(wood) < 8:
        problems.append(f"only {len(wood)} pieces of broken wood under the breaches")
    living_green = sum(n for b, n in census(w, bell)[0].items() if b in w.tag_members("sunman:living_plants"))
    if living_green:
        problems.append(f"{living_green} living plants left in the box")
    if any(e.nbt.get("item", {}).get("components", {}).get("minecraft:item_model", "").startswith("sunman:blood")
           and math.dist(e.pos, g.pos) < 0.5 for e in ents for g in golems):
        problems.append("blood under the golem (it has none)")
    report.update(corpses=len(corpses), pieces=len(pieces), floor_blood=len(floor_blood),
                  smears=len(smears), items=len(items), locusts=len(cores))
    if not 4 <= len(corpses) <= 8:
        problems.append(f"{len(corpses)} bodies (4-8 wanted)")
    if len(floor_blood) < 34 + len(corpses):
        problems.append(f"{len(floor_blood)} blood decals on the ground ({34 + len(corpses)}+ wanted: 34 and one under each body)")
    if len(items) != 10:
        problems.append(f"{len(items)} items left behind (10 wanted)")
    if any(e.nbt.get("Age") != -32768 for e in items):
        problems.append("an item that will despawn (Age must be -32768)")
    if not 2 <= len(cores) <= 4:
        problems.append(f"{len(cores)} Locusts placed (2-4 wanted)")
    if len(bones) != 11 * len(cores):
        problems.append(f"{len(bones)} Locust bones for {len(cores)} Locusts (11 each)")
    if any(t in e.tags for e in ents for t in ("sm_new", "sm_probe", "sm_golem_spot", "sm_debris_spot")):
        problems.append("working tags (sm_new / sm_probe) or probe markers left behind")
    if [e for e in ents if e.type == "marker" and "sm_probe" in e.tags]:
        problems.append("probe markers left alive")
    for e in w.alive():
        if e.type == "interaction" and "sunman_locust" in e.tags and w.score(f"e{e.id}", "sm.awake") != 0:
            problems.append("a Locust that is not frozen (sm.awake must be 0)")

    # every model an entity shows must exist in the resource pack (macros can build names
    # the static check cannot see)
    for e in ents:
        if e.type == "item_display":
            model = e.nbt["item"]["components"]["minecraft:item_model"]
            ns, path = model.split(":")
            if not (ROOT / "resourcepack" / "assets" / ns / "items" / f"{path}.json").exists():
                problems.append(f"an item_display shows {model}, which the resource pack does not define")

    see = w.tag_members("sunman:see_through")
    solid = w.tag_members("sunman:solid")

    def bpos(p):
        return (math.floor(p[0]), math.floor(p[1] + 1e-6), math.floor(p[2]))

    for e in floor_blood + corpses + pieces + items + golems + grass + wood:
        x, y, z = bpos(e.pos)
        if w.block((x, y, z))[0] not in see:
            problems.append(f"{e.nbt.get('item', e.nbt.get('Item'))['id'] if e.type == 'item' else e.nbt['item']['components']['minecraft:item_model']} inside {w.block((x, y, z))[0]} at {(x, y, z)}")
        elif w.block((x, y - 1, z))[0] in see:
            problems.append(f"something floating at {(x, y, z)} over {w.block((x, y - 1, z))[0]}")
    # smears hang on the face of a wall: within a hair of a block edge, with solid behind
    for e in smears:
        fx, fz = e.pos[0] % 1.0, e.pos[2] % 1.0
        if min(fx, 1 - fx, fz, 1 - fz) > 0.05:
            problems.append(f"a wall smear in the middle of a block at {[round(v, 2) for v in e.pos]}")
        yaw = math.radians(e.rot[0])
        behind = (math.floor(e.pos[0] + math.sin(yaw) * 0.1), math.floor(e.pos[1]), math.floor(e.pos[2] - math.cos(yaw) * 0.1))
        if w.block(behind)[0] not in w.tag_members("sunman:solid"):
            problems.append(f"a wall smear with no wall behind it at {[round(v, 2) for v in e.pos]} ({w.block(behind)[0]})")
    for e in cores:
        x, y, z = bpos(e.pos)
        if w.block((x, y - 1, z))[0] in see:
            problems.append(f"a Locust standing on nothing at {(x, y, z)}")
        for dy in (0, 1, 2):
            if w.block((x, y + dy, z))[0] not in w.tag_members("sunman:passable"):
                problems.append(f"a Locust inside {w.block((x, y + dy, z))[0]} at {(x, y + dy, z)}")
        yaw = math.radians(e.rot[0])
        back = (math.floor(e.pos[0] + math.sin(yaw) * 0.9), y + 1, math.floor(e.pos[2] - math.cos(yaw) * 0.9))
        if w.block(back)[0] not in solid:
            problems.append(f"a Locust at {(x, y, z)} with no wall at its back (yaw {e.rot[0]:.0f}, behind it {w.block(back)[0]})")

    # never twice
    n_before = len(w.alive())
    blocks_before = dict(w.blocks)
    run_pass(w, "sunman:slow")
    if len(tagged_all(w, "sunman_decayed")) != 1 or len(w.alive()) != n_before or w.blocks != blocks_before:
        problems.append("a second slow pass changed the village again")
    w.log.clear()
    run_pass(w, "sunman:world/decay_village", mcemu.Ctx(pl, pos=(bell[0] + 0.5, bell[1], bell[2] + 0.5)))
    if w.blocks != blocks_before or len(tagged_all(w, "sunman_decayed")) != 1:
        problems.append("the manual command decayed a dead village a second time")
    if not any(k == "tellraw" and "already dead" in str(v) for k, v in [(x[0], x[1]) for x in w.log if len(x) > 1]):
        problems.append("the manual command did not say why it refused")

    # the safeguards
    w2, bell2 = build(seed)
    populate(w2, bell2, with_bell=False)
    player(w2, (bell2[0] + 30.5, GROUND + 1, bell2[2] + 0.5))
    run_pass(w2, "sunman:load")
    run_pass(w2, "sunman:slow")
    if tagged_all(w2, "sunman_decayed"):
        problems.append("villagers with no bell (a pen, a trading hall) triggered a decay")
    w3, bell3 = build(seed)
    populate(w3, bell3)
    player(w3, (bell3[0] + 30.5, GROUND + 1, bell3[2] + 0.5))
    run_pass(w3, "sunman:load")
    w3.set_score("#sm", "sm.decay", 0)
    run_pass(w3, "sunman:slow")
    if tagged_all(w3, "sunman_decayed"):
        problems.append("the trigger fired with #sm sm.decay 0")

    # the worst case for the command budget: a bell and villagers, and nothing to search
    w4 = mcemu.World(load_pack()[0], load_pack()[1], seed=seed)
    terrain(w4)
    _, bell4 = place(w4, "town_centers/plains_meeting_point_1", 0, 0)
    populate(w4, bell4)
    player(w4, (bell4[0] + 30.5, GROUND + 1, bell4[2] + 0.5))
    run_pass(w4, "sunman:load")
    _, worst = run_pass(w4, "sunman:slow")
    report["worst_case_commands"] = worst
    if worst > 65536 // 2:
        problems.append(f"an empty village (every search failing) needs {worst} commands in one call")
    if tagged_all(w4, "sm_decay_job") or len(tagged_all(w4, "sunman_decayed")) != 1:
        problems.append("the decay job did not finish on an empty village")

    # the blackstone variant: no wood left, and the ruin still had it first
    w5, bell5 = build(seed)
    populate(w5, bell5)
    pl5 = player(w5, (bell5[0] + 0.5, GROUND + 1, bell5[2] + 4.5))
    run_pass(w5, "sunman:load")
    run_pass(w5, "sunman:world/decay_village_blackstone", mcemu.Ctx(pl5, pos=(bell5[0] + 0.5, bell5[1], bell5[2] + 0.5)))
    c5, _ = census(w5, bell5)
    wood = {b: n for b, n in c5.items() if b.endswith("planks") or b.endswith("_log") or
            (b.startswith("oak_") and (b.endswith("stairs") or b.endswith("slab")))}
    if wood:
        problems.append(f"the blackstone village still has wood: {wood}")
    if not c5.get("blackstone_stairs") or not c5.get("blackstone"):
        problems.append("the blackstone village has no blackstone")

    report["ambience"] = 0
    pl.pos = [bell[0] + 5.5, GROUND + 1, bell[2] + 0.5]          # walk in
    for _ in range(200):
        run_pass(w, "sunman:slow")
    report["ambience"] = sum(1 for x in w.log if x[0] == "sound" and x[1] == "sunman:village.whisper")
    if not report["ambience"]:
        problems.append("no whisper in 200 seconds inside the dead village")

    if verbose:
        print("  emulated decay:", ", ".join(f"{k} {v}" for k, v in report.items()))
    if render:
        import iso
        iso.render_world(snapshot, [], bell, ROOT / "docs" / "village_before.png",
                         title="a plains village (26.3 templates)", radius=19, tile=32)
        iso.render_world(w.blocks, w.alive(), bell, ROOT / "docs" / "village_after.png",
                         title="after sunman:world/decay_village", radius=19, tile=32)
        iso.render_world(w.blocks, w.alive(), bell, ROOT / "docs" / "village_inside.png",
                         title="the same, roofs lifted off", cutaway=GROUND + 3, radius=19, tile=32)
    test.report = report
    return problems


def tagged_all(w, t):
    return [e for e in w.alive() if t in e.tags]


def deep(fn, *a, **kw):
    """Run `fn` on a thread with a deep stack: mcfunction loops recurse, and the emulator
    follows them through Python's own stack."""
    import threading
    sys.setrecursionlimit(1_000_000)
    threading.stack_size(1 << 29)
    out = {}

    def go():
        try:
            out["r"] = fn(*a, **kw)
        except BaseException as e:                     # re-raised on the caller's thread
            out["e"] = e
    t = threading.Thread(target=go)
    t.start()
    t.join()
    if "e" in out:
        raise out["e"]
    return out["r"]


if __name__ == "__main__":
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 1
    probs = deep(test, seed, render="--no-render" not in sys.argv, verbose=True)
    for p in probs:
        print("  FAIL ", p)
    print("village: all checks passed" if not probs else f"village: {len(probs)} problem(s)")
