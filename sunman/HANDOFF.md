# Sun Man — rig handoff

Three creatures. Every `.bbmodel` is a **Bedrock Entity** project that opens in Blockbench with
its texture embedded, assembled in its rest pose, hierarchy intact — and with its clips in the
Animate tab as real keyframes.

| file | bones | cubes | clips | height | authored at |
|---|---|---|---|---|---|
| `blockbench/sun_man.bbmodel` | 29 | 197 | 7 | 72.89 blocks | 16/12 px per block (display scale 12) |
| `blockbench/locust.bbmodel` | 11 | 59 | 8 | 2.60 blocks | 16 px per block, true scale |
| `blockbench/dark_walker.bbmodel` | 21 | 144 | 7 | 7.28 blocks | 16 px per block, true scale |

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
rotation was added, and hashes the face quadrant and his material tiles.

The Locust and Dark Walker are open to reshaping, and have been.

## What changed in this pass

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

To bake a clip: `Creature.solve(clip.sample(t))` (or `rig.solve` for the Sun Man) gives every
bone's world position and quaternion at time `t`, rest rotations and position keys included,
exactly as Blockbench poses it. Sample at 20 Hz.

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
| foot-planted walk cycles (IK) | `tools/gait.py` |
| tier skins: UV layout + pixel painter | `tools/paint_tiers.py` |
| material colours, the grade | `tools/palette.py` |
| model export | `tools/export_tiers.py` (item models), `tools/export_bb.py` (`.bbmodel` + rig JSON) |
| every contract, checked | `tools/check.py` |
| real-Blockbench verify / Bedrock export / previews | `tools/blockbench_run.py` + `tools/blockbench/bb.js` |
| cinematic renderer (perspective, tape grade) | `tools/cine.py`, `tools/shots.py` |
| original audio synth | `tools/audio.py` |
| clip reference | `animations/CLIPS.md` |

Rebuild, in order:

    python3 tools/paint_tiers.py      # skins into the free quadrant (face + tiles hash-guarded)
    python3 tools/export_tiers.py     # per-bone item models for the datapack
    python3 tools/export_bb.py        # .bbmodel projects (+ clips) and rig JSON
    python3 tools/check.py            # every contract
    python3 tools/blockbench_run.py --blockbench <web build> all   # verify, bedrock/, previews

## Editing in Blockbench

The Python files are the source, but nothing stops you working in Blockbench: tweak keys in the
Animate tab and File > Export the animations; the Bedrock JSON is what a mod reads. If an edited
clip has to feed the datapack too, port the change back into `clips_*.py` (or write a reader
for the `.animation.json` — the sampler in `keyframes.py` already does the maths). Keep in mind
that `export_bb.py` regenerates the projects from Python.

## Known gaps

- **The datapack does not exist.** It was lost; the generators were recovered from the session
  transcript into `recovered-src/` (not part of this handoff), but `recovered-src/rig.py` cannot run — it loads a v5
  `.geo.json` that went with the folder. `tools/rig.py` is the working reconstruction, and the
  pose solver above is what a baker should call.
- No spawn, AI, or pose functions are wired to any of these clips yet. Clip names follow the
  Bedrock `animation.<creature>.<clip>` convention so they can be referenced from an animation
  controller or a GeckoLib controller as-is.
