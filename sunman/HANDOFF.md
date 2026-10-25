# Sun Man — rig handoff

Three creatures. Every `.bbmodel` opens in Blockbench with its texture embedded, assembled
in rest pose, hierarchy intact.

| file | bones | cubes | height | authored at |
|---|---|---|---|---|
| `blockbench/sun_man.bbmodel` | 29 | 197 | 72.89 blocks | 16/12 px per block, display scale 12 |
| `blockbench/locust.bbmodel` | 11 | 58 | 2.37 blocks | 16 px per block, scale 1 |
| `blockbench/dark_walker.bbmodel` | 21 | 115 | 7.38 blocks | 16/3 px per block, scale 3 |

`rig/<name>.rig.json` is the same skeleton as data: bone, parent, pivot **in blocks**, cube
count, materials, and the clip list.

## HARD CONSTRAINT

**The Sun Man's geometry is the author's and must not be reshaped.** A reproportioned
rebuild was already made and rejected. Surface, animation and features are open; the 197
cubes, 29 pivots and per-cube rotations are not. The starburst face at atlas (256,256) is
pixel-for-pixel fixed and hash-checked on build.

The Locust and Dark Walker are open to reshaping.

## How it actually renders in game

No mod loader. Each creature is an invisible core mob (`minecraft:scale` attribute) plus one
`item_display` per bone, posed from offline-baked keyframes — a datapack cannot do matrix
maths, so every frame of every clip is precomputed and written out as `^` local offsets with
`rotated as @s`, and per-instance tags come from macro functions.

That means **a bone is an entity**. Bone count is a runtime cost, not just a modelling
choice. 29 + 11 + 21 is already the budget.

## Target

Minecraft Java **26.3**. Relevant relaxations, all used here:
- arbitrary Euler XYZ per element (`CuboidRotation$EulerXYZRotation`) — no 22.5° single-axis limit
- no `[-16, 32]` element bound (Blockbench still enforces it, so nothing here exceeds it)
- per-element `light_emission` 0–15 — the Dark Walker's eyes are at 15

## Geometry conventions

- `+X` = the creature's LEFT, `+Y` = up, `+Z` = FORWARD (the face points +Z)
- part models carry the bone pivot at model `(8,8,8)`; world pivot is in the rig JSON, in blocks
- limbs are authored hanging along local `−Y`, so a positive X rotation swings a limb forward
- UVs in the `.bbmodel` are in 512-space; the shipped item models use vanilla 0..16 (×32 apart)

## Source of truth

| what | where |
|---|---|
| Sun Man rig + geometry loader | `tools/rig.py` |
| Locust + Dark Walker rigs | `tools/tiers.py` |
| Sun Man clips | `tools/anim.py` |
| tier clips | `tools/anim_mobs.py` |
| material colours | `tools/palette.py` |
| atlas tile slots | `tools/atlas_patch.py` |
| model export | `tools/export_tiers.py`, `tools/export_bb.py` |
| renderer (perspective, tape grade) | `tools/cine.py`, `tools/shots.py` |
| original audio synth | `tools/audio.py` |
| clip reference | `animations/CLIPS.md` |

## Known gaps

- **The datapack does not exist.** It was lost; the generators were recovered from the session
  transcript into `recovered-src/`, but `recovered-src/rig.py` cannot run — it loads a v5
  `.geo.json` that went with the folder. `tools/rig.py` is the working reconstruction, so the
  exporters need adapting to its module-level API before the pack can be rebuilt.
- No spawn, AI, or pose functions are wired to any of these clips yet.
