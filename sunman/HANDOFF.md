# Sun Man — rig handoff

Five creature models (three creatures, plus the Birthday People in two variants), the dead
villagers, and a datapack with the Abandoned Village. Every `.bbmodel` is a **Bedrock Entity** project that opens in Blockbench with
its texture embedded, assembled in its rest pose, hierarchy intact — and with its clips in the
Animate tab as real keyframes.

| file | bones | cubes | clips | height | authored at |
|---|---|---|---|---|---|
| `blockbench/sun_man.bbmodel` | 29 | 197 | 8 | 72.89 blocks | 16/12 px per block (display scale 12) |
| `blockbench/locust.bbmodel` | 11 | 113 | 10 | 3.42 blocks | 16 px per block, true scale |
| `blockbench/dark_walker.bbmodel` | 21 | 144 | 7 | 7.28 blocks | 16 px per block, true scale |
| `blockbench/birthday_crown.bbmodel` | 18 | 195 | 7 | 6.4 blocks (7.55 with the strings) | 16 px per block, true scale |
| `blockbench/birthday_tree.bbmodel` | 18 | 274 | 7 | 7.56 blocks | 16 px per block, true scale |

`rig/<name>.rig.json` is the same skeleton as data: bone, parent, pivot **in blocks**, rest
rotation, cube count, materials, and the clip index. `bedrock/` holds the `.geo.json` +
`.animation.json` pair for each, written by Blockbench's own exporter (GeckoLib reads these).
`animations/previews/` has a GIF of every clip, played in Blockbench; `docs/` a turnaround of
each creature.

## HARD CONSTRAINT

**The Sun Man's geometry is the author's and must not be reshaped.** A reproportioned
rebuild was already made and rejected. Surface, animation and features are open; the 197
cubes, 29 pivots and per-cube rotations are not. The starburst face at atlas (256,256) is
pixel-for-pixel fixed.

Both are machine-checked: `python3 tools/check.py` hashes the Sun Man's elements (from, to,
origin, rotation, every face UV) against the handoff, checks all 29 pivots and that no rest
rotation was added, and hashes the face quadrant. His own thirteen material tiles are surface,
and have been repainted (see below); every other tile is hashed against the handoff too.

The Locust and Dark Walker are open to reshaping, and have been.

## The Abandoned Village

New: the datapack's first real content. `sunman:world/decay_village` ruins a generated village
in place: the light out, glass and beds gone, stone aged, fields dead, walls clawed open and
roofs fallen in, the villagers replaced by dead villagers (Blockbench models,
`blockbench/village_props.bbmodel`), painted blood on the ground and up the walls, and Locusts
standing frozen inside. The same Blockbench project holds the other props: a crucified villager
(placed on one rooftop, facing the bell), a dead iron golem (where each golem stood; no blood),
two dead-grass tufts and three pieces of broken wood (dropped under the breaches). All twelve
share `textures/entity/village_props.png`; the old `dead_villagers.bbmodel` and its texture are
gone. **Destructive and permanent, and automatic by default**: see
`docs/VILLAGE.md`, which also lists every deviation from the build brief and why.

The resource pack gained the `pack.mcmeta` and atlas sources 26.3 needs to show any `sunman:`
texture on an item model; without them every creature and decal would have rendered as the
missing texture.

## The Birthday People (after Dr. Nowhere)

New: `tools/birthday.py`, `tools/paint_birthday.py`, `tools/clips_birthday.py` (and the two
per-variant modules `clips_birthday_crown.py` and `clips_birthday_tree.py`). They were built
from the five references in `docs/references/birthday_people/`.

- **Two variants, one skeleton:** `birthday_crown` (a ring of ball-tipped spikes, five across the
  front as in the drawings) and `birthday_tree` (the column narrows into a leaning trunk that
  splits into dead branches). The tree is grown from a fixed seed, so it rebuilds identically.
  The variants share every body cube and every texel of it.
- **The body:** a pale, starved body with a washboard of proud ribs and shadows gone red, a
  sunken belly with a dark hollow in it, and arms that hang dead straight nearly to the ground.
  Each arm ends in four black fingers longer than a forearm. A tall black column of a head is
  painted as pencil strokes and frays onto the shoulders. A small pale bearded face looks out of
  it, a third of the way down. Two red strings rise from the head (their own bone, so a datapack
  can hide them).
- **Size:** 6.4 blocks to the tip of the crown (5.6 to the top of the column) and 7.6 blocks
  to the tree's twigs. No reference shows one next to a person, but in every frame they tower,
  so the face sits three blocks above a player's eyes.
- **Rig:** 18 bones. The chain is pelvis → torso → chest → head, with crown and strings on the
  head. Each arm has three bones, so the hand bends at the wrist. Each leg has three, with a real
  ankle so the foot can be keyed flat while walking.
- **Texture:** its own `textures/entity/birthday_people.png` (512×512, 32 texels/block, 12% used).
  The Sun Man atlas is untouched.
- **Clips:** idle, walk, turn, reach, grab, dangle, death (see `animations/CLIPS.md`). The walk's
  feet are placed by IK and kept flat by the ankle (`_level_feet`). The grab re-solves the pelvis
  so the feet stay down. The death is grounded every 0.05 s. `check.py` asserts that nothing goes
  through the floor in any clip.
- **Previews** are rendered on paper grey, like the drawings, so the black columns read. Each
  variant also gets a 36-frame turntable GIF in `docs/`.

## Third pass: the Locust matched to its references

The five Locust references now live in `docs/references/locust/`, and the model was reshaped
to them:

- **Proportions from the ink sheet:** 3.4 blocks tall, legs over half of it, the torso the
  shortest part, shoulders three quarters of the way up. 113 cubes, still 11 bones.
- **Blades instead of hands:** each forearm runs on into a long black blade, four tapering
  segments that bow outward and reach the floor. At rest the arms are splayed, so blades and
  legs make one tall narrow tent, as in the silhouette reference. The forearm item models are
  written at `display_scale` 1.5 so the 28 px from elbow to blade tip fits the item-model box.
- **The head from the room photos:** a pale long-nosed mask (the nose is its own cube) with
  hollow eyes and a slack open mouth, in a full mass of black hair with wire-stiff curls and long
  strands falling to the chest, on a black neck.
- **The body from the sheet and the doll:** doll's ball joints with a bored hole at the
  shoulders, a sagging pale chest over a black ribbed waist, string binding under the chest,
  torn black shorts whose hem hangs over the thighs, and shins that taper to stakes.
- **Clips re-fitted, not rewritten:** the crouches in `twitch`, `rear` and `attack` re-solve the
  pelvis height so the lower foot stays on the floor (`_plant`). The `death` collapse grounds the
  body every 0.05 s so the blades never pass through the floor. The `scuttle` plants the blade
  points as its front feet.

## Second pass: the Locust redone, more detail, creepier

- **Locust rebuilt** to the second set of references — a puppet: a small porcelain mask of a face
  in long black hair, a neck far too long (riding the head bone, so the whole stalk cranes and
  snaps round), a body all ribs with a caved pale chest stitched shut, black ragged hips, pale
  limb segments of old stained wood bound at every joint with black string, four needles to a
  hand, and legs that taper to points. Still 11 bones. (Reshaped again in the third pass.)
- **Textures at 32 texels/block** for both tier creatures (two per model pixel), right-side limbs
  mirroring their left twin's texels, MaxRects-packed into 81% of the free quadrant, painted in
  world space so detail runs across face seams, with the two faces drawn by hand. The Dark
  Walker's eyes became narrow lit slits; its mouth is sewn shut.
- **The Sun Man's surface repainted** — his thirteen material tiles, as pixel art (robe folds and
  old blood, wrappings, the ridged neck, cracked bone, stained fingers, crazed porcelain). His UVs,
  geometry and face are untouched.
- **Creepier clips.** Locust: ten clips for the new rig — a marionette walk on reverse-bending
  knees, a four-legged scuttle on its hands, the head snap with a neck that then
  cracks over sideways, a peek round a door frame, a strings-cut death. Sun Man: a ray halo that
  ticks, spins and flares; a neck that STRETCHES (scale keys) in `stare_down`, `harvest_rise` and
  the new `peer`; harder head snaps, spasming fingers, a lolling head on the walk.
- **Scale keys** are new. The solver now carries full matrices (`fk_matrices` / `solve_m`) and a
  real Blockbench agrees with it on every bone's world position to 0.0001 px.
- **IK feet under any body** (`gait.key_feet`): the Locust's feet and hands plant even hunched over.
  In a limp the longer stride stays down longer, so every planted foot moves at the body's speed.

## First pass

- **Animations are Blockbench keyframes.** All 22 clips (`animations/CLIPS.md`) are sparse,
  hand-editable keys in the projects, exported to Bedrock JSON, and sampled by the Python
  tools through a port of Blockbench's own interpolator — checked against a real Blockbench
  5.1.3 to 0.0001° over 13,000+ samples (`tools/blockbench_run.py verify`).
- **Walks plant their feet** — the legs come from a designed foot path through two-bone IK
  (`tools/gait.py`), and `check.py` measures it. Movement speeds are in CLIPS.md.
- **Dark Walker rebuilt to the five references**: round brim (a stepped disc of plates, no
  coplanar faces) over a low stepped crown; small head pushed forward on a long neck; lit eyes
  under a brow in the brim's shadow; stooped torso with shoulders wider than its pinched waist;
  six arms that FAN in three tiers and hang to the knee, each with an elbow and four long
  two-knuckled fingers plus a thumb; long legs with knees.
- **Locust re-rigged** with elbows and knees, rebuilt on a whole-pixel grid; its head tilt is
  now the head bone's rest rotation rather than a rotation baked into each cube.
- **Joints moved, budget kept.** The old tier rigs broke each limb at the wrist and ankle,
  which left every arm and leg one rigid stick — nothing a walk could bend. Same bone counts
  (11 and 21), but the breaks are now at the elbow and knee, and hands/feet ride the lower
  segment. Renamed: `hand_* → fore_*`, `foot_* → shin_*` (Locust); `tip_* → fore_*`,
  `foot_* → shin_*` (Dark Walker).
- **Real pixel-art skins** at 16 texels per block (vanilla density) replace the noise tiles,
  each cube unwrapped box-style so the texture stays hand-paintable in Blockbench.
- `anim.py`, `anim_mobs.py`, `render_gif.py` and `atlas_patch.py` are gone; `clips_*.py`,
  `paint_tiers.py` and `blockbench_run.py` replace them. `shots.py` renders the cinematic
  shots from the keyframed clips (it also had a macOS-only font path; fixed).

## How it actually renders in game

No mod loader. Each creature is an invisible core mob (`minecraft:scale` attribute) plus one
`item_display` per bone, posed from offline-baked keyframes — a datapack cannot do matrix
maths, so every frame of every clip is precomputed and written out as `^` local offsets with
`rotated as @s`, and per-instance tags come from macro functions.

That means **a bone is an entity**. Bone count is a runtime cost, not just a modelling
choice. 29 + 11 + 21 is the budget, and it is unchanged.

To bake a clip: `Creature.solve_m(clip.sample(t))` (or `rig.solve_m` for the Sun Man) gives
every bone's world position and 3×3 matrix at time `t` — rest rotations, position and scale keys
included — exactly as Blockbench poses it. Sample at 20 Hz. Most clips are pure rotation, and
`solve` (position + quaternion) is enough for them; the ones with SCALE keys need the matrix,
which an `item_display` takes as its `transformation` (any 3×3 decomposes into its
left_rotation · scale · right_rotation): the Sun Man's `lurch`, `stare_down`, `harvest_rise` and
`peer` (the neck and the ray halo).

**If it goes to a mod instead** (GeckoLib, or any Bedrock-format loader): use `bedrock/`. The
creatures face **+Z** (the datapack's convention); vanilla-style entity renderers expect the
model's front at −Z, so turn the model 180° about Y in the renderer. The Dark Walker's eyes are
emissive only through item-model `light_emission`; under GeckoLib, give them a glowmask (their
texels are the two `dw_eye` cubes in the layout).

## Target

Minecraft Java **26.3**. Relevant relaxations, all used here:
- arbitrary Euler XYZ per element (`CuboidRotation$EulerXYZRotation`) — no 22.5° single-axis limit
  (the fingers use two axes)
- no `[-16, 32]` element bound — Blockbench still enforces it for Java models, so the per-bone
  item models stay inside it anyway (the Dark Walker's are written at 16/3 px per block)
- per-element `light_emission` 0–15 — the Dark Walker's eyes are at 15

## Geometry conventions

- `+X` = the creature's LEFT, `+Y` = up, `+Z` = FORWARD (the face points +Z)
- right-handed rotations, Euler order Z·Y·X — the same as Blockbench's: a hanging limb swings
  FORWARD with negative X, a torso folds forward with positive X, the head turns to its left
  with positive Y
- limbs are authored hanging along local −Y and posed by bone REST rotations (Blockbench group
  rotation = Bedrock bone `rotation`); keyframes ADD to the rest Euler angles, as Blockbench
  and GeckoLib do
- part (item) models carry the bone pivot at model `(8,8,8)`; world pivot is in the rig JSON
- UVs in the `.bbmodel` are in 512-space; the shipped item models use vanilla 0..16 (×32 apart)
- keyframes in the `.bbmodel` use the pre-5.0 (Bedrock) value convention — rotation X/Y and
  position X negated — and the files declare format 4.10, so they open identically in
  Blockbench 4.x and 5.x (5.x converts on load). The Python side works in the rig convention
  above and converts on export.

## Source of truth

| what | where |
|---|---|
| Sun Man rig + geometry loader | `tools/rig.py` (geometry: the shipped `models/item/part/*.json`) |
| Locust + Dark Walker rigs and geometry | `tools/tiers.py` |
| clips | `tools/clips_sun_man.py`, `tools/clips_locust.py`, `tools/clips_dark_walker.py` |
| keyframe model, Blockbench-exact sampler, `.bbmodel` writer | `tools/keyframes.py` |
| foot-planted walk cycles (IK), level hips or any body | `tools/gait.py` |
| tier skins: UV layout + pixel painter | `tools/paint_tiers.py` |
| the Sun Man's material tiles | `tools/paint_sun_man.py` |
| material colours, the grade | `tools/palette.py` |
| model export | `tools/export_tiers.py` (item models), `tools/export_bb.py` (`.bbmodel` + rig JSON) |
| every contract, checked | `tools/check.py` |
| real-Blockbench verify / Bedrock export / previews | `tools/blockbench_run.py` + `tools/blockbench/bb.js` |
| cinematic renderer (perspective, tape grade) | `tools/cine.py`, `tools/shots.py` |
| original audio synth | `tools/audio.py` |
| clip reference | `animations/CLIPS.md` |

Rebuild, in order:

    python3 tools/paint_tiers.py      # tier skins into the free quadrant (face hash-guarded)
    python3 tools/paint_sun_man.py    # the Sun Man's own tiles (face + every other tile guarded)
    python3 tools/paint_birthday.py   # the Birthday People's own texture
    python3 tools/paint_decals.py     # the blood decals (textures, models, item definitions)
    python3 tools/props.py            # the village props (texture, models, .bbmodel)
    python3 tools/audio.py            # every sound + sounds.json (needs `pip install soundfile`)
    python3 tools/export_tiers.py     # per-bone item models for the datapack
    python3 tools/export_bb.py        # .bbmodel projects (+ clips) and rig JSON
    python3 tools/export_datapack.py  # datapack/ + the resource pack's pack.mcmeta and atlases
    python3 tools/check.py            # every model/clip contract
    python3 tools/check_datapack.py   # the datapack against 26.3, then emulated on a real village
    python3 tools/server_test.py      # a real 26.3 server (needs Mojang reachable, Java)
    python3 tools/blockbench_run.py --blockbench <web build> all   # verify, bedrock/, previews

## Editing in Blockbench

The Python files are the source, but nothing stops you working in Blockbench: tweak keys in the
Animate tab and File > Export the animations; the Bedrock JSON is what a mod reads. If an edited
clip has to feed the datapack too, port the change back into `clips_*.py` (or write a reader
for the `.animation.json` — the sampler in `keyframes.py` already does the maths). Keep in mind
that `export_bb.py` regenerates the projects from Python.

## Known gaps

- **The datapack is only partly rebuilt.** `datapack/` (generated by `tools/export_datapack.py`)
  now has the infrastructure (load, the slow pass, `util/ground`, `util/roll`, `fx/blood`, block
  tags, objectives), **the Abandoned Village** (`docs/VILLAGE.md`), and a frozen Locust
  (`spawn/locust`). The creature AI and pose playback are still missing (`BEHAVIOUR.md` was
  lost with them): no clip is played in game yet. `tools/rig.py` and `tiers.Creature.solve_m`
  are what a pose baker should call; `export_datapack.locust_pose` shows how one pose becomes
  `item_display` transformation matrices.
- Clip names follow the Bedrock `animation.<creature>.<clip>` convention so they can be
  referenced from an animation controller or a GeckoLib controller as-is.
- **Nothing has run on a real 26.3 server in this pass** (the build environment could not reach
  Mojang). `tools/server_test.py` does it, scripted.
