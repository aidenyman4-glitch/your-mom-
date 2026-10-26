"""Generates the datapack: `datapack/` (Minecraft Java 26.3, data pack format 121).

Edit this file, not the pack. Every .mcfunction, block tag and pack.mcmeta is written here,
then checked by `tools/check_datapack.py` against the real 26.3 command tree and registries,
and run through its emulator on a real vanilla village.

    python3 tools/export_datapack.py

WHAT IS IN IT

  sunman:load / sunman:slow     objectives (all of OBJECTIVES, declared nowhere else), the
                                once-a-second slow pass: the decal cap, the village trigger,
                                the village's ambience
  sunman:util/roll              random 0..99 -> #sm sm.rng
  sunman:util/ground            as an entity: step it down (48 blocks at most, counted in
                                #sm sm.probe -- reset it to 0 first) until it stands in a
                                see-through block over one that is not
  sunman:fx/blood               one blood decal on the ground under the executor
  sunman:spawn/locust           a frozen Locust (NoAI, sm.awake 0), facing the executor's yaw
  sunman:world/decay_village    THE ABANDONED VILLAGE. Destructive and permanent: see
                                docs/VILLAGE.md. Run by hand where you stand, or fired by the
                                slow pass at a village's bell when a player comes within 56
                                blocks of its villagers (#sm sm.decay 1, the default).
  sunman:world/decay_village_blackstone   the same, then the village rebuilt in blackstone
                                (the older biome sheet's version, offered per world)

Also writes the resource pack's pack.mcmeta and its atlas sources: 26.3 builds item models
from its own `items` atlas, which holds only `textures/item/` unless a pack adds to it, so
without these the decals and the dead would render as the missing texture.

GOTCHAS this file is written around (each has cost the project real time):
  * `#` is a comment only at the START of a line. Never trail a comment after a command.
  * a dangling tag fails the whole pack at load: every tag entry is checked against 26.3.
  * `damage` takes exactly one entity.
  * a wrong sound id is a silent sound, not an error: every id is checked.
  * gamerules are namespaced snake_case in 26.3.
  * text components in NBT are SNBT compounds, not stringified JSON.
  * `fill ... replace` cannot carry a block state across a type change, so stairs and slabs
    are converted one state at a time, and never from a full block to a stair or slab.
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tiers                                                   # noqa: E402
from mcdata import DATA_PACK_FORMAT, MC, RESOURCE_PACK_FORMAT  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "datapack"
RP = ROOT / "resourcepack"
NS = "sunman"

# Every objective the pack uses. load.mcfunction declares exactly these; nothing else may.
OBJECTIVES = [
    ("sm.rng", "random rolls (util/roll)"),
    ("sm.probe", "step counter for util/ground"),
    ("sm.decay", "1: villages decay when a player comes near (0 switches it off)"),
    ("sm.awake", "0 frozen, 1 awake (Locust)"),
    ("sm.i", "loop counter"),
    ("sm.n", "loop target"),
    ("sm.try", "attempts left in a placement search"),
    ("sm.ok", "result flag"),
    ("sm.decals", "how many decals exist (the cap)"),
    ("sm.head", "headroom at a placement spot"),
    ("sm.stage", "which stage a village's decay job is at"),
    ("sm.cy", "the height of the village centre (for finding roofs)"),
]

BOX = "~-16 ~-6 ~-16 ~16 ~10 ~16"        # the 32 x 16 x 32 box round the village centre
STORAGE = f"{NS}:village"
# text components are SNBT compounds in 26.3, not stringified JSON
ALREADY = '{text:"This place is already dead.",color:"dark_red"}'
DONE = '{text:"Once a peaceful home... now a place of silence, ruin, and blood.",color:"dark_red",italic:true}'


# ====================================================================== files

FUNCS = {}
TAGS = {}


def fn(path, *lines):
    """Register a function. Lines are commands or `# comments` (whole-line only)."""
    body = []
    for ln in lines:
        body.extend(ln if isinstance(ln, (list, tuple)) else [ln])
    for ln in body:
        # a `$` line with no variable is a load error; so is a trailing comment
        assert not ln.startswith("$") or "$(" in ln, f"{path}: macro line without a variable: {ln}"
    FUNCS[path] = body


def tag(name, values):
    TAGS[name] = list(values)


def snbt_float_list(vals):
    return "[" + ",".join(f"{_f(v)}f" for v in vals) + "]"


def _f(v):
    v = round(float(v), 5)
    if v == 0:
        v = 0.0
    s = f"{v:.5f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-") else "0"


def display(model, tags, extra=""):
    """An item_display showing one of the pack's item models (an item definition id)."""
    t = ",".join(f'"{x}"' for x in tags)
    return (f'{{Tags:[{t}],item:{{id:"minecraft:paper",count:1,components:{{"minecraft:item_model":"{model}"}}}},'
            f'item_display:"fixed"{"," + extra if extra else ""}}}')


# ====================================================================== tags

def block_tags():
    tag("light_out", ["minecraft:torch", "minecraft:wall_torch", "minecraft:soul_torch",
                      "minecraft:soul_wall_torch", "minecraft:campfire", "minecraft:soul_campfire"])
    glass = sorted(b for b in MC.registry("block") if b.endswith("glass") or b.endswith("glass_pane"))
    tag("fabric", [f"minecraft:{b}" for b in glass] +
        ["#minecraft:beds", "#minecraft:banners", "#minecraft:all_signs", "#minecraft:wool",
         "#minecraft:wool_carpets"])
    tag("crops", ["minecraft:wheat", "minecraft:carrots", "minecraft:potatoes", "minecraft:beetroots"])
    tag("ruinable", ["#minecraft:planks", "#minecraft:wooden_stairs", "#minecraft:wooden_slabs",
                     "#minecraft:wooden_doors", "#minecraft:wooden_fences"])
    # what a thing tearing through a house takes with it: the wood, the frame, the shutters
    tag("smashable", ["#sunman:ruinable", "#minecraft:logs", "#minecraft:wooden_trapdoors",
                      "#minecraft:fence_gates", "minecraft:hay_block", "minecraft:bookshelf",
                      "minecraft:white_terracotta", "minecraft:mud_bricks", "minecraft:packed_mud"])
    tag("living_plants", ["minecraft:short_grass", "minecraft:tall_grass", "minecraft:fern",
                          "minecraft:large_fern", "minecraft:bush", "minecraft:firefly_bush",
                          "#minecraft:small_flowers", "minecraft:sunflower", "minecraft:lilac",
                          "minecraft:rose_bush", "minecraft:peony", "minecraft:pink_petals",
                          "minecraft:wildflowers"])
    tag("dead_ground", ["minecraft:grass_block", "minecraft:coarse_dirt", "minecraft:dirt",
                        "minecraft:podzol", "minecraft:rooted_dirt"])
    tag("roofing", ["#minecraft:planks", "#minecraft:wooden_stairs", "#minecraft:wooden_slabs"])
    plants = ["minecraft:short_grass", "minecraft:tall_grass", "minecraft:fern", "minecraft:large_fern",
              "minecraft:dead_bush", "minecraft:short_dry_grass", "minecraft:tall_dry_grass",
              "minecraft:bush", "minecraft:leaf_litter", "#minecraft:small_flowers", "#minecraft:saplings"]
    tag("plants", plants)
    tag("see_through", ["#minecraft:air", "#sunman:plants", "minecraft:cobweb",
                        "#sunman:light_out", "minecraft:redstone_wire", "minecraft:vine",
                        "minecraft:ladder"])
    tag("passable", ["#sunman:see_through", "#minecraft:wool_carpets", "#minecraft:rails",
                     "#minecraft:pressure_plates", "#minecraft:buttons", "minecraft:lever",
                     "minecraft:water"])
    tag("solid", ["#minecraft:planks", "#minecraft:logs", "#minecraft:terracotta", "#minecraft:dirt",
                  "minecraft:grass_block", "minecraft:podzol", "minecraft:mycelium",
                  "minecraft:cobblestone", "minecraft:mossy_cobblestone", "minecraft:stone",
                  "minecraft:smooth_stone", "minecraft:stone_bricks", "minecraft:cracked_stone_bricks",
                  "minecraft:mossy_stone_bricks", "minecraft:bricks", "minecraft:mud_bricks",
                  "minecraft:packed_mud", "minecraft:sandstone", "minecraft:smooth_sandstone",
                  "minecraft:cut_sandstone", "minecraft:chiseled_sandstone", "minecraft:hay_block",
                  "minecraft:bookshelf", "minecraft:snow_block", "minecraft:packed_ice",
                  "minecraft:blackstone", "minecraft:polished_blackstone_bricks",
                  "minecraft:cracked_polished_blackstone_bricks", "minecraft:polished_basalt"])


# ====================================================================== infrastructure

def infrastructure():
    fn("load",
       "# Declares every objective the pack uses (OBJECTIVES in tools/export_datapack.py).",
       [f"scoreboard objectives add {o} dummy" for o, _ in OBJECTIVES],
       "# villages decay when players come near, unless a world has switched it off",
       "execute unless score #sm sm.decay matches -2147483648..2147483647 run scoreboard players set #sm sm.decay 1",
       f"data merge storage {STORAGE} {{}}",
       f"schedule function {NS}:slow 20t replace")

    fn("slow",
       "# Once a second.",
       f"schedule function {NS}:slow 20t replace",
       "# the decal cap: past 512 blood decals, the ones furthest from a player go first",
       "execute store result score #sm sm.decals if entity @e[type=item_display,tag=sm_decal]",
       "execute if score #sm sm.decals matches 513.. as @r at @s run kill @e[type=item_display,tag=sm_decal,sort=furthest,limit=16]",
       "# the abandoned village: a player near living villagers who know where their bell is",
       f"execute if score #sm sm.decay matches 1.. as @a[gamemode=!spectator] at @s if entity @e[type=villager,distance=..56] run function {NS}:world/try_decay",
       "# a decay job whose chunks were unloaded mid-way picks up again when they load",
       f"execute if entity @e[type=marker,tag=sm_decay_job] run schedule function {NS}:world/decay/job 1t replace",
       "# and what a dead village sounds like",
       f"execute as @a[gamemode=!spectator] at @s if entity @e[type=marker,tag=sunman_decayed,distance=..36] run function {NS}:world/ambience")

    fn("util/roll",
       "# Random 0..99 into #sm sm.rng.",
       "execute store result score #sm sm.rng run random value 0..99")

    fn("util/ground",
       "# As an entity, at it: step it down until it stands in a see-through block over one",
       "# that is not. At most 48 steps, counted in #sm sm.probe (reset it to 0 first).",
       "# Returns 1 when it found ground, fails when it ran out.",
       "scoreboard players add #sm sm.probe 1",
       "execute if block ~ ~ ~ #sunman:see_through unless block ~ ~-1 ~ #sunman:see_through run return 1",
       "execute if score #sm sm.probe matches 48.. run return fail",
       "tp @s ~ ~-1 ~",
       f"execute at @s run return run function {NS}:util/ground")

    fn("util/roofed",
       "# Is there a roof over here? Anything not see-through within 2..7 blocks above.",
       [f"execute unless block ~ ~{k} ~ #sunman:see_through run return 1" for k in range(2, 8)],
       "return fail")

    fn("fx/blood",
       "# One blood decal on the ground under the executor.",
       "summon marker ~ ~1 ~ {Tags:[\"sm_probe\"]}",
       "scoreboard players set #sm sm.probe 0",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s run function {NS}:util/ground",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s if block ~ ~ ~ #sunman:see_through unless block ~ ~-1 ~ #sunman:see_through run function {NS}:world/decay/decal_random",
       "kill @e[type=marker,tag=sm_probe]")


# ====================================================================== the village

def _rand(key, lo, hi, store="p"):
    return f"execute store result storage {STORAGE} {store}.{key} int 1 run random value {lo}..{hi}"


def _loop(name, count_var, body_fn):
    """A counted loop: `body` runs while sm.i < count. The caller sets #sm sm.i and #sm sm.n."""
    fn(name,
       f"function {NS}:{body_fn}",
       "scoreboard players add #sm sm.i 1",
       f"execute if score #sm sm.i < #sm {count_var} run function {NS}:{name}")


def stairs_and_slabs(src, dst, kind):
    """Convert `src` to `dst` (same shape) one block state at a time, so every stair keeps
    its facing, half and shape and every slab its type. `fill ... replace` sets one fixed
    state; done in one pass, every stair in the village would snap to face north."""
    states = MC.block_states(dst.replace("minecraft:", ""))
    keys = [k for k in ("facing", "half", "shape", "type") if k in states]
    combos = [{}]
    for k in keys:
        combos = [dict(c, **{k: v}) for c in combos for v in states[k]]
    out = []
    for c in combos:
        for wl in ("false", "true"):
            st = ",".join(f"{k}={v}" for k, v in c.items()) + f",waterlogged={wl}"
            out.append(f"fill {BOX} {dst}[{st}] replace {src}[{st}]")
    return out


def village():
    D = f"{NS}:world/decay"

    fn("world/decay_village",
       "# THE ABANDONED VILLAGE, where you stand.",
       "# DESTRUCTIVE AND PERMANENT: torches out, glass and beds and banners gone, stone aged,",
       "# fields dead, walls torn open, the villagers replaced by their bodies. There is no undo.",
       "# Refuses within 40 blocks of a place that has already been decayed.",
       "execute align xyz if entity @e[type=marker,tag=sunman_decayed,distance=..40] run return run tellraw @s " + ALREADY,
       f"execute align xyz run function {D}/guarded",
       "execute align xyz if entity @e[type=marker,tag=sunman_decayed,distance=..1] run tellraw @s " + DONE)

    fn("world/decay_village_blackstone",
       "# The Abandoned Village, then rebuilt in blackstone and coarse dirt: the biome sheet's",
       "# older version, for worlds that want it. As destructive as the default, and more.",
       "execute align xyz if entity @e[type=marker,tag=sunman_decayed,distance=..40] run return run tellraw @s " + ALREADY,
       f"execute align xyz run function {D}/guarded",
       "# the job's last stage rebuilds it in blackstone, after the ruin has had the wood",
       "execute align xyz run tag @e[type=marker,tag=sm_decay_job,distance=..1] add sm_blackstone")

    fn("world/try_decay",
       "# As and at a player near villagers. Finds a villager that remembers its village's",
       "# meeting point (the bell) and decays the village there. Villagers with no bell -- a",
       "# breeding pen, a trading hall -- never trigger it.",
       f"execute as @e[type=villager,distance=..56,sort=nearest] if data entity @s Brain.memories.\"minecraft:meeting_point\".value.pos run return run function {D}/from_villager")

    fn("world/decay/from_villager",
       "# As a villager: read where its bell is and decay the village round it.",
       f"data modify storage {STORAGE} c set value {{}}",
       f"data modify storage {STORAGE} c.x set from entity @s Brain.memories.\"minecraft:meeting_point\".value.pos[0]",
       f"data modify storage {STORAGE} c.y set from entity @s Brain.memories.\"minecraft:meeting_point\".value.pos[1]",
       f"data modify storage {STORAGE} c.z set from entity @s Brain.memories.\"minecraft:meeting_point\".value.pos[2]",
       f"function {D}/at_bell with storage {STORAGE} c")

    fn("world/decay/at_bell",
       f"$execute positioned $(x) $(y) $(z) run return run function {D}/guarded")

    fn("world/decay/guarded",
       "# Positioned at the centre. Never twice in one place, never into unloaded chunks.",
       "execute if entity @e[type=marker,tag=sunman_decayed,distance=..40] run return fail",
       ["execute unless loaded ~-16 ~ ~-16 run return fail", "execute unless loaded ~16 ~ ~16 run return fail",
        "execute unless loaded ~16 ~ ~-16 run return fail", "execute unless loaded ~-16 ~ ~16 run return fail"],
       f"function {D}/run",
       "return 1")

    fn("world/decay/run",
       "# The transform. The decayed marker goes down FIRST: if anything cuts this short, the",
       "# place is still never decayed twice. The blocks change now; the rest is staged over the",
       "# next ticks by a job marker, so no single tick runs more than a third of",
       "# max_command_sequence_length however awkward the village.",
       "summon marker ~ ~ ~ {Tags:[\"sunman_decayed\"]}",
       f"function {D}/light",
       f"function {D}/fabric",
       f"function {D}/stone",
       f"function {D}/fields",
       f"function {D}/doors",
       "# the villagers are gone, and their bodies will be here instead",
       f"execute as @e[type=villager,distance=..48] at @s run function {D}/vanish",
       f"execute as @e[type=iron_golem,distance=..48] at @s run function {D}/vanish_golem",
       "summon marker ~ ~ ~ {Tags:[\"sm_decay_job\",\"sm_new\"]}",
       "scoreboard players set @e[type=marker,tag=sm_new,tag=sm_decay_job] sm.stage 2",
       "tag @e[type=marker,tag=sm_new] remove sm_new",
       f"schedule function {D}/job 1t replace")

    fn("world/decay/job",
       "# Scheduled: no executor. Each job marker stands at its village's centre.",
       f"execute as @e[type=marker,tag=sm_decay_job] at @s run function {D}/stage")
    fn("world/decay/stage",
       f"execute if score @s sm.stage matches 2 run function {D}/stage_ruin",
       f"execute if score @s sm.stage matches 3 run function {D}/stage_rot",
       f"execute if score @s sm.stage matches 4 run function {D}/stage_dead",
       f"execute if score @s sm.stage matches 5 run function {D}/stage_blood",
       f"execute if score @s sm.stage matches 6 run function {D}/stage_locusts",
       f"execute if score @s sm.stage matches 6 if entity @s[tag=sm_blackstone] run function {D}/blackstone",
       "scoreboard players add @s sm.stage 1",
       "execute if score @s sm.stage matches 7.. run kill @s",
       f"execute if score @s sm.stage matches ..6 run schedule function {D}/job 1t replace")

    fn("world/decay/stage_ruin",
       "# 3.5: the ruin, 130 probes",
       "scoreboard players set #sm sm.i 0",
       "scoreboard players set #sm sm.n 130",
       f"function {D}/ruin_loop",
       "# something went through the walls: 40 places torn open, clawed through, caved in",
       "scoreboard players set #sm sm.i 0",
       "scoreboard players set #sm sm.try 320",
       f"function {D}/smash_search",
       "# two roofs fallen in",
       "scoreboard players set #sm sm.i 0",
       "scoreboard players set #sm sm.try 200",
       f"function {D}/collapse_search",
       "kill @e[type=marker,tag=sm_collapse]")
    fn("world/decay/stage_rot",
       "# webs strung under the ceilings of the rooms nobody uses",
       "scoreboard players set #sm sm.i 0",
       "scoreboard players set #sm sm.try 500",
       f"function {D}/web_search",
       "# the ground died where it stood: patches of dead earth, dead bushes",
       "scoreboard players set #sm sm.i 0",
       "scoreboard players set #sm sm.n 22",
       f"function {D}/blight_loop",
       "# the broken wood under the breaches",
       f"execute as @e[type=marker,tag=sm_debris_spot,distance=..48] at @s run function {D}/debris_drop",
       "# and dead grass where the green was: 40 tufts",
       "scoreboard players set #sm sm.i 0",
       "scoreboard players set #sm sm.n 40",
       f"function {D}/grass_loop")
    fn("world/decay/stage_dead",
       "# 3.7: the bodies, and the pieces of others",
       f"function {D}/corpses",
       "# the golem, dead where it stood (or somewhere in the open, if the village had none)",
       "scoreboard players set #sm sm.i 0",
       "scoreboard players set #sm sm.try 60",
       f"execute unless entity @e[type=marker,tag=sm_golem_spot,distance=..64] run function {D}/golem_spot_search",
       f"execute as @e[type=marker,tag=sm_golem_spot,distance=..64] at @s run function {D}/dead_golem",
       "kill @e[type=marker,tag=sm_golem_spot,distance=..64]",
       "# and one of them nailed up on a roof, facing the bell",
       "execute store result score #sm sm.cy run data get entity @s Pos[1]",
       "scoreboard players set #sm sm.i 0",
       "scoreboard players set #sm sm.try 150",
       f"function {D}/crucifix_search")
    fn("world/decay/stage_blood",
       "# 3.6: blood, 34 decals",
       "scoreboard players set #sm sm.i 0",
       "scoreboard players set #sm sm.n 34",
       f"function {D}/blood_loop",
       "# blood up the walls: 14 smears where something was dragged or raked",
       "scoreboard players set #sm sm.i 0",
       "scoreboard players set #sm sm.try 120",
       f"function {D}/smear_search",
       "# 3.8: what people left behind",
       "scoreboard players set #sm sm.i 0",
       "scoreboard players set #sm sm.n 10",
       f"function {D}/items_loop")
    fn("world/decay/stage_locusts",
       "# 5: the Locusts, already standing inside",
       f"function {D}/locusts")

    # ------------------------------------------------------------------ 3.1 - 3.4
    fn("world/decay/light",
       "# 3.1 The light goes out. Lanterns stay: the only light left in the place.",
       f"fill {BOX} air replace #sunman:light_out")
    fn("world/decay/fabric",
       "# 3.2 Fabric and glass are gone.",
       f"fill {BOX} air replace #sunman:fabric")
    fn("world/decay/stone",
       "# 3.3 Stone ages. Full blocks to full blocks; stairs and slabs state by state.",
       f"fill {BOX} mossy_cobblestone replace cobblestone",
       f"fill {BOX} cracked_stone_bricks replace stone_bricks",
       stairs_and_slabs("cobblestone_stairs", "mossy_cobblestone_stairs", "stairs"),
       stairs_and_slabs("cobblestone_slab", "mossy_cobblestone_slab", "slab"))
    fn("world/decay/fields",
       "# 3.4 The fields are dead and the paths gone to coarse dirt.",
       f"fill {BOX} air replace #sunman:crops",
       f"fill {BOX} coarse_dirt replace farmland",
       f"fill {BOX} coarse_dirt replace dirt_path",
       "# and everything green dies: the only grass left is the dead grass laid down later",
       f"fill {BOX} air replace #sunman:living_plants")
    fn("world/decay/doors",
       "# Every door torn off. Whatever came through did not use the handle.",
       f"fill {BOX} air replace #minecraft:wooden_doors")

    # ------------------------------------------------------------------ 3.5 the ruin
    fn("world/decay/ruin_probe",
       _rand("bx", -15, 15), _rand("by", -1, 7), _rand("bz", -15, 15),
       f"function {D}/ruin_at with storage {STORAGE} p")
    _loop("world/decay/ruin_loop", "sm.n", "world/decay/ruin_probe")
    fn("world/decay/ruin_at",
       f"$execute positioned ~$(bx) ~$(by) ~$(bz) run function {NS}:world/ruin_block")
    fn("world/ruin_block",
       "# One probe. Wood goes; webs hang where a ceiling is left; dead bushes on bare ground.",
       "execute if block ~ ~ ~ #sunman:ruinable run setblock ~ ~ ~ air",
       "execute if block ~ ~ ~ #minecraft:air if block ~ ~1 ~ #minecraft:planks run setblock ~ ~ ~ cobweb",
       "execute if block ~ ~ ~ #minecraft:air if block ~ ~-1 ~ coarse_dirt run setblock ~ ~ ~ dead_bush")

    # ------------------------------------------------------------------ the breach
    fn("world/decay/smash_search",
       "# Probe for a wall or a roof. When one is hit, tear a hole through it there.",
       _rand("bx", -14, 14), _rand("by", 0, 8), _rand("bz", -14, 14), _rand("shape", 0, 5),
       f"execute store success score #sm sm.ok run function {D}/smash_at with storage {STORAGE} p",
       "execute if score #sm sm.ok matches 1 run scoreboard players add #sm sm.i 1",
       "scoreboard players remove #sm sm.try 1",
       f"execute if score #sm sm.i matches ..39 if score #sm sm.try matches 1.. run function {D}/smash_search")
    fn("world/decay/smash_at",
       f"$execute positioned ~$(bx) ~$(by) ~$(bz) if block ~ ~ ~ #sunman:smashable run return run function {D}/smash_$(shape)",
       "return fail")
    fn("world/decay/smash_0",
       "# clawed through a wall, east-west: a tall ragged gap",
       "fill ~ ~-1 ~-1 ~ ~1 ~1 air replace #sunman:smashable",
       "fill ~ ~ ~-2 ~ ~ ~2 air replace #sunman:smashable",
       f"function {D}/debris",
       "return 1")
    fn("world/decay/smash_1",
       "# clawed through a wall, north-south",
       "fill ~-1 ~-1 ~ ~1 ~1 ~ air replace #sunman:smashable",
       "fill ~-2 ~ ~ ~2 ~ ~ air replace #sunman:smashable",
       f"function {D}/debris",
       "return 1")
    fn("world/decay/smash_2",
       "# burst up through a roof",
       "fill ~-1 ~ ~-1 ~1 ~1 ~1 air replace #sunman:smashable",
       "fill ~ ~-1 ~ ~ ~2 ~ air replace #sunman:smashable",
       "fill ~-2 ~1 ~ ~2 ~1 ~ air replace #sunman:roofing",
       f"function {D}/debris",
       "return 1")
    fn("world/decay/smash_3",
       "# a roof caved in: the roofing gone over five by five, the frame left standing",
       "execute if block ~ ~-3 ~ #sunman:see_through if block ~ ~-2 ~ #sunman:see_through run return fail",
       "fill ~-2 ~-1 ~-2 ~2 ~1 ~2 air replace #sunman:roofing",
       "fill ~-1 ~-2 ~-1 ~1 ~-2 ~1 air replace #minecraft:wooden_slabs",
       f"function {D}/debris",
       "return 1")
    fn("world/decay/smash_5",
       "# (as 3: caved roofs are what reads from the road)",
       f"return run function {D}/smash_3")
    fn("world/decay/smash_4",
       "# torn open low down, the way something big gets in: a doorway where there was a wall",
       "fill ~-1 ~ ~ ~1 ~2 ~ air replace #sunman:smashable",
       "fill ~ ~ ~-1 ~ ~2 ~1 air replace #sunman:smashable",
       f"function {D}/debris",
       "return 1")

    # ------------------------------------------------------------------ webs, dead ground
    fn("world/decay/web_search",
       "# 18 webs: under a ceiling, against a wall",
       _rand("bx", -14, 14), _rand("by", 1, 5), _rand("bz", -14, 14),
       f"execute store success score #sm sm.ok run function {D}/web_at with storage {STORAGE} p",
       "execute if score #sm sm.ok matches 1 run scoreboard players add #sm sm.i 1",
       "scoreboard players remove #sm sm.try 1",
       f"execute if score #sm sm.i matches ..17 if score #sm sm.try matches 1.. run function {D}/web_search")
    fn("world/decay/web_at",
       f"$execute positioned ~$(bx) ~$(by) ~$(bz) if block ~ ~ ~ #minecraft:air unless block ~ ~1 ~ #sunman:see_through run return run function {D}/web_corner",
       "return fail")
    fn("world/decay/web_corner",
       "execute if block ~1 ~ ~ #sunman:solid run return run setblock ~ ~ ~ cobweb",
       "execute if block ~-1 ~ ~ #sunman:solid run return run setblock ~ ~ ~ cobweb",
       "execute if block ~ ~ ~1 #sunman:solid run return run setblock ~ ~ ~ cobweb",
       "execute if block ~ ~ ~-1 #sunman:solid run return run setblock ~ ~ ~ cobweb",
       "return fail")
    fn("world/decay/collapse_search",
       _rand("bx", -13, 13), _rand("by", 4, 8), _rand("bz", -13, 13),
       f"execute store success score #sm sm.ok run function {D}/collapse_at with storage {STORAGE} p",
       "execute if score #sm sm.ok matches 1 run scoreboard players add #sm sm.i 1",
       "scoreboard players remove #sm sm.try 1",
       f"execute if score #sm sm.i matches ..1 if score #sm sm.try matches 1.. run function {D}/collapse_search")
    fn("world/decay/collapse_at",
       f"$execute positioned ~$(bx) ~$(by) ~$(bz) if block ~ ~ ~ #sunman:roofing unless entity @e[type=marker,tag=sm_collapse,distance=..9] run return run function {D}/collapse",
       "return fail")
    fn("world/decay/collapse",
       "# a roof fallen in: seven by seven of it gone, a few rafters left hanging",
       "fill ~-3 ~-2 ~-3 ~3 ~2 ~3 air replace #sunman:roofing",
       "fill ~-1 ~-3 ~-1 ~1 ~-3 ~1 air replace #minecraft:wooden_slabs",
       "summon marker ~ ~ ~ {Tags:[\"sm_collapse\"]}",
       "return 1")
    fn("world/decay/blight_probe",
       _rand("bx", -15, 15), _rand("bz", -15, 15),
       f"function {D}/blight_at with storage {STORAGE} p")
    _loop("world/decay/blight_loop", "sm.n", "world/decay/blight_probe")
    fn("world/decay/blight_at",
       "$execute positioned ~$(bx) ~8 ~$(bz) summon marker run tag @s add sm_probe",
       "scoreboard players set #sm sm.probe 0",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s run function {NS}:util/ground",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s if block ~ ~ ~ #sunman:see_through unless block ~ ~-1 ~ #sunman:see_through run function {D}/blight",
       "kill @e[type=marker,tag=sm_probe]")
    fn("world/decay/blight",
       "execute if block ~ ~ ~ #sunman:plants run setblock ~ ~ ~ air",
       "fill ~-1 ~-1 ~-1 ~1 ~-1 ~1 coarse_dirt replace grass_block",
       "fill ~ ~-1 ~-2 ~ ~-1 ~2 coarse_dirt replace grass_block",
       "fill ~-2 ~-1 ~ ~2 ~-1 ~ coarse_dirt replace grass_block",
       f"function {NS}:util/roll",
       "execute if score #sm sm.rng matches ..54 if block ~ ~ ~ #minecraft:air run setblock ~ ~ ~ dead_bush",
       "execute if score #sm sm.rng matches 30..74 if block ~1 ~ ~1 #minecraft:air if block ~1 ~-1 ~1 coarse_dirt run setblock ~1 ~ ~1 dead_bush",
       "execute if score #sm sm.rng matches 60.. if block ~-1 ~ ~ #minecraft:air if block ~-1 ~-1 ~ coarse_dirt run setblock ~-1 ~ ~ short_dry_grass")

    # ------------------------------------------------------------------ 3.6 blood
    fn("world/decay/blood_probe",
       _rand("bx", -15, 15), _rand("bz", -15, 15),
       f"function {D}/blood_at with storage {STORAGE} p")
    _loop("world/decay/blood_loop", "sm.n", "world/decay/blood_probe")
    fn("world/decay/blood_at",
       f"$execute positioned ~$(bx) ~8 ~$(bz) run function {D}/drop_decal")
    fn("world/decay/drop_decal",
       "# Down the column from ~8 to the ground (through a roof, onto the floor under it).",
       "summon marker ~ ~ ~ {Tags:[\"sm_probe\"]}",
       "scoreboard players set #sm sm.probe 0",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s run function {NS}:util/ground",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s if block ~ ~ ~ #sunman:see_through unless block ~ ~-1 ~ #sunman:see_through run function {D}/decal_random",
       "kill @e[type=marker,tag=sm_probe]")
    fn("world/decay/decal_random",
       "# At the ground. Trample what grows there, then one of three decals at a random yaw.",
       "execute if block ~ ~ ~ #sunman:plants run setblock ~ ~ ~ air",
       _rand("yaw", -180, 180, "d"),
       "execute store result score #sm sm.rng run random value 0..9",
       f"data modify storage {STORAGE} d.model set value \"{NS}:blood_splatter\"",
       f"execute if score #sm sm.rng matches 0..3 run data modify storage {STORAGE} d.model set value \"{NS}:blood_pool\"",
       f"execute if score #sm sm.rng matches 8..9 run data modify storage {STORAGE} d.model set value \"{NS}:blood_trail\"",
       f"function {D}/decal with storage {STORAGE} d")
    fn("world/decay/decal",
       "# A blood decal: a flat quad 0.015 above the ground, dark (fixed light), prunable (sm_decal).",
       "$summon item_display ~ ~0.015 ~ " + display("$(model)", ["sm_decal", "sunman_blood"],
                                                     "Rotation:[$(yaw)f,0f],view_range:1.2f,shadow_radius:0f,brightness:{sky:4,block:0}"))

    # ------------------------------------------------------------------ smears on walls
    fn("world/decay/smear_search",
       "# Blood on the walls: an air block, low down, against a wall.",
       _rand("bx", -14, 14), _rand("by", 0, 2), _rand("bz", -14, 14),
       f"execute store success score #sm sm.ok run function {D}/smear_at with storage {STORAGE} p",
       "execute if score #sm sm.ok matches 1 run scoreboard players add #sm sm.i 1",
       "scoreboard players remove #sm sm.try 1",
       f"execute if score #sm sm.i matches ..13 if score #sm sm.try matches 1.. run function {D}/smear_search")
    fn("world/decay/smear_at",
       f"$execute positioned ~$(bx) ~$(by) ~$(bz) if block ~ ~ ~ #minecraft:air if block ~ ~1 ~ #minecraft:air run return run function {D}/smear_wall",
       "return fail")
    fn("world/decay/smear_wall",
       "# Find which side the wall is on; hang the smear on its face, facing out into the room.",
       _rand("yaw", -4, 4, "s"),
       f"execute if block ~ ~ ~-1 #sunman:solid if block ~ ~1 ~-1 #sunman:solid align xyz positioned ~0.5 ~0.75 ~0.02 run return run function {D}/smear with storage {STORAGE} s",
       f"execute if block ~ ~ ~1 #sunman:solid if block ~ ~1 ~1 #sunman:solid align xyz positioned ~0.5 ~0.75 ~0.98 rotated 180 0 run return run function {D}/smear_r with storage {STORAGE} s",
       f"execute if block ~-1 ~ ~ #sunman:solid if block ~-1 ~1 ~ #sunman:solid align xyz positioned ~0.02 ~0.75 ~0.5 rotated -90 0 run return run function {D}/smear_r with storage {STORAGE} s",
       f"execute if block ~1 ~ ~ #sunman:solid if block ~1 ~1 ~ #sunman:solid align xyz positioned ~0.98 ~0.75 ~0.5 rotated 90 0 run return run function {D}/smear_r with storage {STORAGE} s",
       "return fail")
    smear_nbt = display(f"{NS}:blood_smear", ["sm_decal", "sunman_blood", "sm_new"],
                        "view_range:1.0f,shadow_radius:0f,brightness:{sky:4,block:0}")
    fn("world/decay/smear",
       "# The smear model stands in its own z plane; yaw 0 puts it flat on a north wall.",
       f"summon item_display ~ ~ ~ {smear_nbt}",
       "$execute as @e[type=item_display,tag=sm_new] run tp @s ~ ~ ~ $(yaw) 0",
       "tag @e[type=item_display,tag=sm_new] remove sm_new",
       "return 1")
    fn("world/decay/smear_r",
       "# Rotated to face out of a south, west or east wall (the executor's yaw).",
       f"summon item_display ~ ~ ~ {smear_nbt}",
       "$execute as @e[type=item_display,tag=sm_new] run tp @s ~ ~ ~ ~$(yaw) 0",
       "tag @e[type=item_display,tag=sm_new] remove sm_new",
       "return 1")


    # ------------------------------------------------------------------ what is left
    fn("world/decay/debris",
       "# A breach: mark it. What came out of the wall is laid on the floor below it once all",
       "# the ruin is done (stage 3), so a later breach cannot pull the floor out from under it.",
       f"function {NS}:util/roll",
       "execute if score #sm sm.rng matches ..69 run summon marker ~ ~ ~ {Tags:[\"sm_debris_spot\"]}")
    fn("world/decay/debris_drop",
       "# As a debris marker: down to the floor, and a piece of broken wood on it.",
       _rand("yaw", -180, 180, "w"),
       "execute store result score #sm sm.rng run random value 0..2",
       f"execute if score #sm sm.rng matches 0 run data modify storage {STORAGE} w.v set value \"a\"",
       f"execute if score #sm sm.rng matches 1 run data modify storage {STORAGE} w.v set value \"b\"",
       f"execute if score #sm sm.rng matches 2 run data modify storage {STORAGE} w.v set value \"c\"",
       "scoreboard players set #sm sm.probe 0",
       f"function {NS}:util/ground",
       f"execute at @s if block ~ ~ ~ #minecraft:air unless block ~ ~-1 ~ #sunman:see_through unless entity @e[type=item_display,tag=sunman_debris,distance=..1.5] run function {D}/wood_piece with storage {STORAGE} w",
       "kill @s")
    fn("world/decay/wood_piece",
       "$summon item_display ~ ~ ~ " + display(f"{NS}:broken_wood_$(v)", ["sunman_debris"],
                                                 "Rotation:[$(yaw)f,0f],view_range:1.2f,shadow_radius:0.6f,shadow_strength:0.5f"))

    fn("world/decay/grass_probe",
       _rand("bx", -15, 15), _rand("bz", -15, 15), _rand("yaw", -180, 180),
       f"function {NS}:util/roll",
       f"data modify storage {STORAGE} p.v set value \"a\"",
       f"execute if score #sm sm.rng matches 50.. run data modify storage {STORAGE} p.v set value \"b\"",
       f"function {D}/grass_at with storage {STORAGE} p")
    _loop("world/decay/grass_loop", "sm.n", "world/decay/grass_probe")
    fn("world/decay/grass_at",
       "$execute positioned ~$(bx) ~8 ~$(bz) summon marker run tag @s add sm_probe",
       "scoreboard players set #sm sm.probe 0",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s run function {NS}:util/ground",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s if block ~ ~ ~ #minecraft:air if block ~ ~-1 ~ #sunman:dead_ground run function {D}/tuft with storage {STORAGE} p",
       "kill @e[type=marker,tag=sm_probe]")
    fn("world/decay/tuft",
       "$summon item_display ~ ~ ~ " + display(f"{NS}:dead_grass_$(v)", ["sunman_dead_grass"],
                                                 "Rotation:[$(yaw)f,0f],view_range:0.8f,shadow_radius:0f"))

    fn("world/decay/golem_spot_search",
       "# no golem here: lay one out in the open somewhere near the middle",
       _rand("bx", -12, 12), _rand("bz", -12, 12),
       f"execute store success score #sm sm.ok run function {D}/golem_spot_at with storage {STORAGE} p",
       "execute if score #sm sm.ok matches 1 run scoreboard players add #sm sm.i 1",
       "scoreboard players remove #sm sm.try 1",
       f"execute if score #sm sm.i matches ..0 if score #sm sm.try matches 1.. run function {D}/golem_spot_search")
    fn("world/decay/golem_spot_at",
       "$execute positioned ~$(bx) ~8 ~$(bz) summon marker run tag @s add sm_probe",
       "scoreboard players set #sm sm.probe 0",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s run function {NS}:util/ground",
       "scoreboard players set #sm sm.ok 0",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s if block ~ ~ ~ #sunman:see_through unless block ~ ~-1 ~ #sunman:see_through unless function {NS}:util/roofed run function {D}/golem_spot_mark",
       "kill @e[type=marker,tag=sm_probe]",
       "execute if score #sm sm.ok matches 1 run return 1",
       "return fail")
    fn("world/decay/golem_spot_mark",
       "summon marker ~ ~ ~ {Tags:[\"sm_golem_spot\"]}",
       "scoreboard players set #sm sm.ok 1")
    fn("world/decay/dead_golem",
       "# As the spot marker: from a little above where it stood, down to the ground, and the",
       "# golem lying on it. No blood.",
       "tp @s ~ ~3 ~",
       "scoreboard players set #sm sm.probe 0",
       f"execute at @s run function {NS}:util/ground",
       _rand("yaw", -180, 180, "g"),
       f"execute at @s if block ~ ~ ~ #sunman:see_through unless block ~ ~-1 ~ #sunman:see_through run function {D}/golem_body with storage {STORAGE} g")
    fn("world/decay/golem_body",
       "execute if block ~ ~ ~ #sunman:plants run setblock ~ ~ ~ air",
       "$summon item_display ~ ~ ~ " + display(f"{NS}:dead_iron_golem", ["sunman_corpse", "sunman_golem"],
                                                 "Rotation:[$(yaw)f,0f],view_range:2.0f,shadow_radius:1.6f,shadow_strength:0.6f," + 'transformation:{left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f],translation:[0f,0f,0f],scale:[2f,2f,2f]}'))

    fn("world/decay/crucifix_search",
       _rand("bx", -13, 13), _rand("bz", -13, 13),
       f"execute store success score #sm sm.ok run function {D}/crucifix_at with storage {STORAGE} p",
       "execute if score #sm sm.ok matches 1 run scoreboard players add #sm sm.i 1",
       "scoreboard players remove #sm sm.try 1",
       f"execute if score #sm sm.i matches ..0 if score #sm sm.try matches 1.. run function {D}/crucifix_search")
    fn("world/decay/crucifix_at",
       "# From high above down onto whatever is there; it has to be a roof, four blocks up or more.",
       "$execute positioned ~$(bx) ~16 ~$(bz) summon marker run tag @s add sm_probe",
       "scoreboard players set #sm sm.probe 0",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s run function {NS}:util/ground",
       "scoreboard players set #sm sm.ok 0",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s run function {D}/crucifix_check",
       "kill @e[type=marker,tag=sm_probe]",
       "execute if score #sm sm.ok matches 1 run return 1",
       "return fail")
    fn("world/decay/crucifix_check",
       "execute store result score #sm sm.head run data get entity @s Pos[1]",
       "scoreboard players operation #sm sm.head -= #sm sm.cy",
       "execute unless score #sm sm.head matches 4.. run return fail",
       "# on a house, not over the bell itself",
       "execute if entity @e[type=marker,tag=sm_decay_job,distance=..6] run return fail",
       "execute unless block ~ ~ ~ #minecraft:air run return fail",
       "execute unless block ~ ~1 ~ #minecraft:air run return fail",
       "execute unless block ~ ~-1 ~ #sunman:smashable unless block ~ ~-1 ~ #sunman:solid run return fail",
       "# facing the bell, so it is the first thing you see from the middle of the village",
       "execute facing entity @e[type=marker,tag=sm_decay_job,limit=1,sort=nearest] feet run summon item_display ~ ~ ~ " +
       display(f"{NS}:crucified_villager", ["sunman_corpse", "sunman_crucified", "sm_new"],
               "view_range:3.0f,shadow_radius:0f," + 'transformation:{left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f],translation:[0f,0f,0f],scale:[3f,3f,3f]}'),
       "execute facing entity @e[type=marker,tag=sm_decay_job,limit=1,sort=nearest] feet as @e[type=item_display,tag=sm_new] run tp @s ~ ~ ~ ~ 0",
       "tag @e[type=item_display,tag=sm_new] remove sm_new",
       "scoreboard players set #sm sm.ok 1",
       "return 1")

    # ------------------------------------------------------------------ 3.7 the dead
    fn("world/decay/vanish_golem",
       "# The golem goes the same way, but leaves its body where it stood (stage 4).",
       "summon marker ~ ~ ~ {Tags:[\"sm_golem_spot\"]}",
       "tp @s ~ -2100 ~",
       "kill @s")
    fn("world/decay/vanish",
       "# A living villager (or golem) leaves no trace: out of the world, then gone.",
       "tp @s ~ -2100 ~",
       "kill @s")
    fn("world/decay/corpses",
       "# 3.7: 4 to 8 bodies, inside the houses first, then round them; and pieces of others.",
       "execute store result score #sm sm.n run random value 4..8",
       "scoreboard players set #sm sm.i 0",
       "scoreboard players set #sm sm.try 80",
       f"function {D}/corpse_search",
       "scoreboard players set #sm sm.i 0",
       "scoreboard players set #sm sm.n 3",
       "scoreboard players set #sm sm.try 40",
       f"function {D}/gore_search")
    fn("world/decay/corpse_search",
       _rand("bx", -13, 13), _rand("bz", -13, 13), _rand("yaw", -180, 180),
       "# which body: a, b or c (the model ids are letters, so the roll is mapped, not stored)",
       "execute store result score #sm sm.rng run random value 0..2",
       f"execute if score #sm sm.rng matches 0 run data modify storage {STORAGE} p.v set value \"a\"",
       f"execute if score #sm sm.rng matches 1 run data modify storage {STORAGE} p.v set value \"b\"",
       f"execute if score #sm sm.rng matches 2 run data modify storage {STORAGE} p.v set value \"c\"",
       f"execute store success score #sm sm.ok run function {D}/corpse_at with storage {STORAGE} p",
       "execute if score #sm sm.ok matches 1 run scoreboard players add #sm sm.i 1",
       "scoreboard players remove #sm sm.try 1",
       f"execute if score #sm sm.i < #sm sm.n if score #sm sm.try matches 1.. run function {D}/corpse_search")
    fn("world/decay/corpse_at",
       "$execute positioned ~$(bx) ~8 ~$(bz) summon marker run tag @s add sm_probe",
       "scoreboard players set #sm sm.probe 0",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s run function {NS}:util/ground",
       "scoreboard players set #sm sm.ok 0",
       "# the first half of the tries take only spots under a roof: inside the houses",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s if block ~ ~ ~ #sunman:see_through if block ~ ~1 ~ #sunman:see_through unless block ~ ~-1 ~ #sunman:see_through unless entity @e[type=item_display,tag=sunman_corpse,distance=..2.5] if score #sm sm.try matches 41.. run function {D}/corpse_roofed with storage {STORAGE} p",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s if block ~ ~ ~ #sunman:see_through if block ~ ~1 ~ #sunman:see_through unless block ~ ~-1 ~ #sunman:see_through unless entity @e[type=item_display,tag=sunman_corpse,distance=..2.5] if score #sm sm.try matches ..40 run function {D}/corpse with storage {STORAGE} p",
       "kill @e[type=marker,tag=sm_probe]",
       "execute if score #sm sm.ok matches 1 run return 1",
       "return fail")
    fn("world/decay/corpse_roofed",
       f"$execute if function {NS}:util/roofed run function {D}/corpse {{v:$(v),yaw:$(yaw)}}")
    fn("world/decay/corpse",
       "# A body, the blood it lies in, and for some the trail where it was dragged.",
       "execute if block ~ ~ ~ #sunman:plants run setblock ~ ~ ~ air",
       "$summon item_display ~ ~ ~ " + display(f"{NS}:dead_villager_$(v)", ["sunman_corpse"],
                                                 "Rotation:[$(yaw)f,0f],view_range:1.6f,shadow_radius:0.9f,shadow_strength:0.55f"),
       "$summon item_display ~ ~0.015 ~ " + display(f"{NS}:blood_pool", ["sm_decal", "sunman_blood"],
                                                   "Rotation:[$(yaw)f,0f],view_range:1.2f,shadow_radius:0f,brightness:{sky:4,block:0}"),
       "# the drag mark runs back from the body along its length (the trail model is laid along z)",
       "$execute if score #sm sm.rng matches ..49 rotated $(yaw) 0 positioned ^ ^ ^-1.6 if block ~ ~ ~ #sunman:see_through unless block ~ ~-1 ~ #sunman:see_through run summon item_display ~ ~0.016 ~ " +
       display(f"{NS}:blood_trail", ["sm_decal", "sunman_blood"],
               "Rotation:[$(yaw)f,0f],view_range:1.2f,shadow_radius:0f,brightness:{sky:4,block:0}"),
       f"function {NS}:util/roll",
       "scoreboard players set #sm sm.ok 1")
    fn("world/decay/gore_search",
       _rand("bx", -14, 14), _rand("bz", -14, 14), _rand("yaw", -180, 180),
       f"execute store success score #sm sm.ok run function {D}/gore_at with storage {STORAGE} p",
       "execute if score #sm sm.ok matches 1 run scoreboard players add #sm sm.i 1",
       "scoreboard players remove #sm sm.try 1",
       f"execute if score #sm sm.i < #sm sm.n if score #sm sm.try matches 1.. run function {D}/gore_search")
    fn("world/decay/gore_at",
       "$execute positioned ~$(bx) ~8 ~$(bz) summon marker run tag @s add sm_probe",
       "scoreboard players set #sm sm.probe 0",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s run function {NS}:util/ground",
       "scoreboard players set #sm sm.ok 0",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s if block ~ ~ ~ #sunman:see_through unless block ~ ~-1 ~ #sunman:see_through run function {D}/gore with storage {STORAGE} p",
       "kill @e[type=marker,tag=sm_probe]",
       "execute if score #sm sm.ok matches 1 run return 1",
       "return fail")
    fn("world/decay/gore",
       "# A loose head or an arm, and the splash it made.",
       "execute if block ~ ~ ~ #sunman:plants run setblock ~ ~ ~ air",
       "$execute if score #sm sm.rng matches 0..49 run summon item_display ~ ~ ~ " +
       display(f"{NS}:dead_villager_head", ["sunman_corpse"], "Rotation:[$(yaw)f,0f],view_range:1.2f,shadow_radius:0.35f"),
       "$execute if score #sm sm.rng matches 50.. run summon item_display ~ ~ ~ " +
       display(f"{NS}:dead_villager_arm", ["sunman_corpse"], "Rotation:[$(yaw)f,0f],view_range:1.2f,shadow_radius:0.3f"),
       "$summon item_display ~ ~0.015 ~ " + display(f"{NS}:blood_splatter", ["sm_decal", "sunman_blood"],
                                                    "Rotation:[$(yaw)f,0f],view_range:1.2f,shadow_radius:0f,brightness:{sky:4,block:0}"),
       f"function {NS}:util/roll",
       "scoreboard players set #sm sm.ok 1")

    # ------------------------------------------------------------------ 3.8 left behind
    items = ["egg", "wheat", "stick", "bread", "wooden_hoe", "bone"]
    fn("world/decay/items_probe",
       _rand("bx", -14, 14), _rand("bz", -14, 14),
       "execute store result score #sm sm.rng run random value 0..%d" % (len(items) - 1),
       [f"execute if score #sm sm.rng matches {i} run data modify storage {STORAGE} p.item set value \"minecraft:{it}\""
        for i, it in enumerate(items)],
       f"function {D}/item_at with storage {STORAGE} p")
    _loop("world/decay/items_loop", "sm.n", "world/decay/items_probe")
    fn("world/decay/item_at",
       "$execute positioned ~$(bx) ~8 ~$(bz) summon marker run tag @s add sm_probe",
       "scoreboard players set #sm sm.probe 0",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s run function {NS}:util/ground",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s if block ~ ~ ~ #sunman:see_through unless block ~ ~-1 ~ #sunman:see_through run function {D}/item with storage {STORAGE} p",
       "kill @e[type=marker,tag=sm_probe]")
    fn("world/decay/item",
       "# Never despawns (Age -32768).",
       "$summon item ~ ~0.05 ~ {Item:{id:\"$(item)\",count:1},Age:-32768s,Motion:[0d,0d,0d]}")

    # ------------------------------------------------------------------ 5 the Locusts
    fn("world/decay/locusts",
       "# 2 to 4 Locusts, standing frozen against the inside walls of the houses.",
       "execute store result score #sm sm.n run random value 2..4",
       "scoreboard players set #sm sm.i 0",
       "scoreboard players set #sm sm.try 400",
       f"function {D}/locust_search")
    fn("world/decay/locust_search",
       _rand("bx", -14, 14), _rand("by", 2, 5), _rand("bz", -14, 14),
       f"execute store success score #sm sm.ok run function {D}/locust_at with storage {STORAGE} p",
       "execute if score #sm sm.ok matches 1 run scoreboard players add #sm sm.i 1",
       "scoreboard players remove #sm sm.try 1",
       f"execute if score #sm sm.i < #sm sm.n if score #sm sm.try matches 1.. run function {D}/locust_search")
    fn("world/decay/locust_at",
       "$execute positioned ~$(bx) ~$(by) ~$(bz) summon marker run tag @s add sm_probe",
       "scoreboard players set #sm sm.probe 0",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s run function {NS}:util/ground",
       "scoreboard players set #sm sm.ok 0",
       f"execute as @e[type=marker,tag=sm_probe,limit=1,sort=nearest] at @s align xyz positioned ~0.5 ~ ~0.5 unless entity @e[type=interaction,tag=sunman_locust,distance=..4] if function {NS}:util/roofed run function {D}/locust_spot",
       "kill @e[type=marker,tag=sm_probe]",
       "execute if score #sm sm.ok matches 1 run return 1",
       "return fail")
    fn("world/decay/locust_spot",
       "# A floor, three blocks clear above it, not a doorway, a wall at its back.",
       "execute unless block ~ ~ ~ #sunman:passable run return fail",
       "execute unless block ~ ~1 ~ #sunman:passable run return fail",
       "execute unless block ~ ~2 ~ #sunman:passable run return fail",
       "execute if block ~ ~-1 ~ #sunman:passable run return fail",
       "execute if block ~1 ~1 ~ #sunman:solid if block ~-1 ~1 ~ #sunman:solid run return fail",
       "execute if block ~ ~1 ~1 #sunman:solid if block ~ ~1 ~-1 #sunman:solid run return fail",
       "scoreboard players set #sm sm.head 3",
       "execute if block ~ ~3 ~ #sunman:passable run scoreboard players set #sm sm.head 4",
       "# wall to the north: face south (yaw 0), and so on round",
       f"execute if block ~ ~1 ~-1 #sunman:solid if block ~ ~1 ~1 #sunman:passable rotated 0 0 positioned ^ ^ ^-0.2 run return run function {D}/locust_place",
       f"execute if block ~ ~1 ~1 #sunman:solid if block ~ ~1 ~-1 #sunman:passable rotated 180 0 positioned ^ ^ ^-0.2 run return run function {D}/locust_place",
       f"execute if block ~-1 ~1 ~ #sunman:solid if block ~1 ~1 ~ #sunman:passable rotated -90 0 positioned ^ ^ ^-0.2 run return run function {D}/locust_place",
       f"execute if block ~1 ~1 ~ #sunman:solid if block ~-1 ~1 ~ #sunman:passable rotated 90 0 positioned ^ ^ ^-0.2 run return run function {D}/locust_place",
       "return fail")
    fn("world/decay/locust_place",
       "# Full height where the ceiling allows; bowed under it where it does not.",
       f"execute if score #sm sm.head matches 4.. run function {NS}:spawn/locust",
       f"execute if score #sm sm.head matches ..3 run function {NS}:spawn/locust_cramped",
       "scoreboard players set #sm sm.ok 1",
       "return 1")

    # ------------------------------------------------------------------ ambience
    fn("world/ambience",
       "# As and at a player inside a dead village: now and then, whispering behind them.",
       f"function {NS}:util/roll",
       "execute if score #sm sm.rng matches ..3 rotated as @s positioned ^2 ^1 ^-6 run playsound sunman:village.whisper ambient @s ~ ~ ~ 0.7 1",
       "execute if score #sm sm.rng matches 4 rotated as @s positioned ^-3 ^1 ^-8 run playsound sunman:village.whisper ambient @s ~ ~ ~ 0.5 0.85")

    # ------------------------------------------------------------------ blackstone
    fn("world/decay/blackstone",
       "# The older sheet's village: no wood left, all blackstone and coarse dirt.",
       f"fill {BOX} blackstone replace #minecraft:planks",
       f"fill {BOX} polished_basalt replace #minecraft:logs",
       f"fill {BOX} blackstone replace mossy_cobblestone",
       f"fill {BOX} cracked_polished_blackstone_bricks replace cracked_stone_bricks",
       f"fill {BOX} coarse_dirt replace grass_block",
       f"fill {BOX} coarse_dirt replace dirt",
       f"fill {BOX} air replace #minecraft:wooden_fences",
       stairs_and_slabs("#minecraft:wooden_stairs", "blackstone_stairs", "stairs"),
       stairs_and_slabs("mossy_cobblestone_stairs", "blackstone_stairs", "stairs"),
       stairs_and_slabs("#minecraft:wooden_slabs", "blackstone_slab", "slab"),
       stairs_and_slabs("mossy_cobblestone_slab", "blackstone_slab", "slab"))


# ====================================================================== the Locust

def _mat4(pos, m, s):
    """Row-major 4x4 for an item_display `transformation`: the bone's world placement in the
    entity frame, times the item model's display scale, times a half turn about Y -- the
    item_display renderer turns every item model 180 degrees about Y before drawing it, and
    this undoes that so the model's +Z (the Locust's front) stays its front."""
    flip = (-1.0, 1.0, -1.0)
    rows = []
    for r in range(3):
        rows.append([m[r][c] * s * flip[c] for c in range(3)] + [pos[r]])
    rows.append([0.0, 0.0, 0.0, 1.0])
    return [v for row in rows for v in row]


def locust_pose(name, pose):
    c = tiers.LOCUST
    sol = c.solve_m(pose)
    lo, hi = c.extents(pose)
    lines = [f"summon interaction ~ ~ ~ {{Tags:[\"sunman_locust\",\"sunman_core\",\"sm_new\"],width:0.9f,height:{_f(hi - lo)}f,response:0b}}"]
    for bone in c.BONE_ORDER:
        if not c.GEOMETRY.get(bone):
            continue
        pos, m = sol[bone]
        pos = (pos[0], pos[1] - lo, pos[2])
        mat = _mat4(pos, m, c.DISPLAY_SCALE)
        extra = "transformation:" + snbt_float_list(mat) + ",view_range:1.0f,shadow_radius:0f"
        lines.append("summon item_display ~ ~ ~ " + display(f"{NS}:locust_{bone}",
                                                          ["sunman_locust", "sunman_locust_part", "sm_new"], extra))
    fn(name,
       "# A Locust, frozen where it stands: NoAI by construction (it has no mob at all yet --",
       "# an interaction box takes the hits, the bones are item_displays), sm.awake 0.",
       "# Faces the executor's yaw. Pose baked from tools/tiers.py by tools/export_datapack.py.",
       lines,
       "execute as @e[tag=sm_new,tag=sunman_locust] run tp @s ~ ~ ~ ~ 0",
       "scoreboard players set @e[type=interaction,tag=sm_new,tag=sunman_locust] sm.awake 0",
       "tag @e[tag=sm_new,tag=sunman_locust] remove sm_new")
    return hi - lo


_LOCUST_POSES = {
    "full": {},
    # bowed under a ceiling three blocks up: folded at the waist, the neck laid forward
    "cramped": {"torso": {"rotation": (34.0, 0.0, 0.0)}, "head": {"rotation": (30.0, 0.0, 6.0)},
                "leg_l": {"rotation": (-8.0, 0.0, 0.0)}, "leg_r": {"rotation": (-8.0, 0.0, 0.0)},
                "shin_l": {"rotation": (14.0, 0.0, 0.0)}, "shin_r": {"rotation": (14.0, 0.0, 0.0)},
                "arm_l": {"rotation": (-24.0, 0.0, 0.0)}, "arm_r": {"rotation": (-24.0, 0.0, 0.0)}},
}


def locust():
    full = locust_pose("spawn/locust", _LOCUST_POSES["full"])
    bowed = locust_pose("spawn/locust_cramped", _LOCUST_POSES["cramped"])
    return full, bowed


# ====================================================================== write

def pack_meta():
    meta = {"pack": {"description": {"text": "Sun Man: the creatures, and the Abandoned Village",
                                     "color": "dark_red"},
                     "min_format": DATA_PACK_FORMAT, "max_format": DATA_PACK_FORMAT}}
    (OUT / "pack.mcmeta").write_text(json.dumps(meta, indent=2) + "\n")
    major, minor = RESOURCE_PACK_FORMAT
    rmeta = {"pack": {"description": {"text": "Sun Man: models, skins, blood and sound", "color": "dark_red"},
                      "min_format": [major, 0], "max_format": [major, minor]}}
    (RP / "pack.mcmeta").write_text(json.dumps(rmeta, indent=2) + "\n")
    # 26.3 builds item models from its own atlas; add the pack's textures to it (and to the
    # block atlas, which some model lookups use)
    sources = {"sources": [
        {"type": "minecraft:directory", "source": "decal", "prefix": "decal/"},
        {"type": "minecraft:single", "resource": f"{NS}:entity/sun_man"},
        {"type": "minecraft:single", "resource": f"{NS}:entity/birthday_people"},
        {"type": "minecraft:single", "resource": f"{NS}:entity/village_props"},
    ]}
    atl = RP / "assets" / "minecraft" / "atlases"
    atl.mkdir(parents=True, exist_ok=True)
    for a in ("items", "blocks"):
        (atl / f"{a}.json").write_text(json.dumps(sources, indent=2) + "\n")


def write():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "data" / NS / "function").mkdir(parents=True)
    pack_meta()
    for name, values in TAGS.items():
        p = OUT / "data" / NS / "tags" / "block" / f"{name}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"values": values}, indent=2) + "\n")
    ft = OUT / "data" / "minecraft" / "tags" / "function"
    ft.mkdir(parents=True)
    (ft / "load.json").write_text(json.dumps({"values": [f"{NS}:load"]}, indent=2) + "\n")
    for path, body in FUNCS.items():
        p = OUT / "data" / NS / "function" / f"{path}.mcfunction"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(body) + "\n")


def build():
    FUNCS.clear()
    TAGS.clear()
    block_tags()
    infrastructure()
    village()
    full, bowed = locust()
    write()
    n = sum(len([ln for ln in b if ln and not ln.startswith("#")]) for b in FUNCS.values())
    print(f"  datapack/: {len(FUNCS)} functions, {n} commands, {len(TAGS)} block tags")
    print(f"  Locust baked standing ({full:.2f} blocks) and bowed ({bowed:.2f} blocks)")
    return FUNCS, TAGS


if __name__ == "__main__":
    build()
