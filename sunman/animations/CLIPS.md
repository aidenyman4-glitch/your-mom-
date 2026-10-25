# Clips

Every clip is a pose function in `tools/anim.py` (Sun Man) or `tools/anim_mobs.py` (tiers),
rendered by `tools/shots.py` through the perspective camera in `tools/cine.py`.

Rebuild everything:  `python3 tools/shots.py`
Rebuild one:         `python3 tools/shots.py charge closer`

## The five devices

Nothing here is "more movement". Every clip is built out of five kinds of wrongness:

| device     | what it does                                                        |
|------------|---------------------------------------------------------------------|
| `stutter`  | quantises phase into N holds, so motion jumps instead of easing      |
| `lag`      | shifts a chain's phase back, so the head is dragged by the body      |
| `asym`     | desynchronises left and right, so a cycle never resolves             |
| `hold`     | long stillness broken by one violent frame                           |
| `overbend` | carries a joint past where a joint stops                             |

## Sun Man — mapped to the datapack's real states

`export_datapack.py` picks state by distance: 0 idle, 1 inside 110 blocks, 2 inside 55,
3 inside 26, 4 harvest. Each clip below is the animation for one of those states.

| clip            | state | the idea                                                      |
|-----------------|-------|---------------------------------------------------------------|
| `dread_idle`    | 0     | a statue that moves twice, when you are not ready              |
| `wrong_walk`    | 1     | the legs walk and everything above the hips refuses to agree   |
| `charge`        | 2     | it runs, and its head never moves while the body does          |
| `arch`          | 3     | three beats of nothing, then it folds forward over the top of you |
| `stare_down`    | 3     | the face descends toward you in eight visible jerks            |
| `harvest_rise`  | 4     | day thirty: arms opening in tiers, the whole thing getting taller |
| `closer`        | —     | a camera piece. It never moves. It is nearer every time you look |

## Locust — "It doesn't see you... but it knows you're there."

Spawns `NoAI` with an empty animation. Waking is one-way.

| clip             | the idea                                                     |
|------------------|--------------------------------------------------------------|
| `locust_frozen`  | perfectly still, then with nothing in between its head is facing you (171 degrees) |
| `locust_scuttle` | a sprint with the arms reaching ahead. Door height — it fits where you fit |
| `locust_rear`    | the wake-up inside 9 blocks                                   |
| `locust_climb`   | all four limbs on a wall, head craned back down at the floor   |

## Dark Walker — "It does not hurry, because it does not need to."

Tier 2, replacing the Organ Gatherer (archived under `archive/organ_gatherer/`). Built from
five references: a hilltop silhouette, an ink drawing, two frames of something standing in a
road at night with lit eyes, and one of it looking over a fence at a house. **7.38 blocks,
21 bones, 115 cubes**, six tendril arms in three tiers, a wide brim, two eyes at
`light_emission: 15`.

It is deliberately the **outdoor** tier. The Locust is found standing inside houses at door
height; this one cannot follow you through a door. It is what is in the road, on the ridge,
over the fence.

| clip            | the idea                                                        |
|-----------------|------------------------------------------------------------------|
| `walker_road`   | it comes down the track. The brim never tips a degree             |
| `walker_ridge`  | on the horizon against a pale sky, not coming. Then it turns      |
| `walker_loom`   | it hinges at the hips. It does not kneel                          |
| `walker_reach`  | six arms, each leading the next by a sixth of a beat              |

**Why the body is grey and not black.** A black body can be a silhouette but it can never be
the pale thing caught in a headlight, and two of the five references are exactly that. A cold
mid-grey (`84,87,95`) does both: backlit against a bright sky it reads as a pure silhouette,
and in a light at night it is the thing in the road. The hat stays black in every light.

## The grade

Shots are degraded like tape on purpose, and it is not decoration: `fx/overlay_vhs` is a
real `camera_overlay` the datapack keeps equipped, so scanlines and chroma tearing ARE the
player's view. Degradation ramps with proximity, the same way the sound design does.

`charge` and `closer` cut to a full-bleed plate of the face. That is not a liberty either —
`ai/gaze_step` raycasts from the player's eyes, and when it connects with the head,
`fx/overlay_gaze` swaps the overlay to the white-out. Looking at it really does fill your
screen with it.

## Sound

`tools/audio.py` synthesises **14 original sounds** into
`resourcepack/assets/sunman/sounds/`. Until now every event in the pack was a pitched-down
vanilla file, and that is the one thing a pitched warden can never stop being: a warden.

    python3 tools/audio.py

| file                   | what it is                                                     |
|------------------------|-----------------------------------------------------------------|
| `sun_man/heartbeat`    | 46 BPM, and the second beat lands late every time                |
| `sun_man/drone`        | 14 s loop; two partials 0.42 Hz apart, so the cluster beats       |
| `sun_man/notice`       | reverse swell into a glissando that falls below the speaker       |
| `sun_man/toll`         | real bell partials, detuned just enough that the ring sours       |
| `sun_man/step`         | impact, the ground answering late, and grit coming off it         |
| `sun_man/gaze`         | a sine climbing into the part of the range that hurts             |
| `sun_man/harvest`      | an 8 s swell with crowd formants somewhere inside the noise       |
| `locust/click`         | chitin, irregularly spaced — even spacing reads as a machine      |
| `locust/shriek`        | insect buzz with a throat behind it, cut off mid-breath           |
| `locust/step`          | light double tap                                                  |
| `dark_walker/step`     | a stilt on a road: dry, woody, far too slow to be a stride        |
| `dark_walker/drift`    | a thin tone that will not hold a pitch, with no bottom at all     |
| `dark_walker/notice`   | an intake of breath nothing with that body could take             |
| `dark_walker/reach`    | six tendrils of dry fibre, no wet in it anywhere                  |
| `music/dread`          | 74 s stereo. Eight notes, and the interval it keeps returning to is a minor second |

Built from four primitives: additive partials, noise shaped in the spectral domain, FFT
convolution reverb and phase-accumulated glissandi — plus tape wobble on anything long.

The Sun Man's heartbeat measures **85% of its energy below 120 Hz**; every one of the Dark
Walker's four sounds measures **0%**. He is 73 blocks of weight and you feel him through the
floor; it is four metres of leg and almost no body, and you only hear it because the night is
silent. That contrast is the reason they are in the same world.

Positional sounds are **mono**. Minecraft does not distance-attenuate a stereo file, so a
stereo footstep is as loud across the valley as it is underfoot.

`assets/minecraft/sounds.json` now points all eight overworld `music.*` events at
`sunman:music/dread`, so the snow biomes play it instead of Minecraft's own music. That
works from the resource pack alone — no datapack needed.

## The atlas

`tools/atlas_patch.py` paints ten tier-material tiles into the atlas's free quadrant
(x 0..256, y 256..512) and `tools/export_tiers.py` emits both tier creatures against them.

Before this, `export_models.py` resolved every material with `SLOTS.get(mat, SLOTS["bone"])`
and `texture.py`'s SLOTS had no `lc_*` or `dw_*` entry at all — so every Locust cube landed
on the Sun Man's bone tile. The patch is in place rather than a regeneration, because
regenerating needs `references/EXACT_SOURCE_Face_Starburst.png`, which went with the project
folder, and the face at (256,256) is a pixel-for-pixel contract. The script hashes the face
quadrant before and after and refuses to write if it moved. It changed exactly 40,960 pixels,
all of them inside the free quadrant.
