# Clips

Every clip is a set of **Blockbench keyframes**. They live in the `.bbmodel` files — open one,
switch to the Animate tab, and they are there to play, scrub and edit — and they are exported
to `bedrock/<name>.animation.json` for GeckoLib / Bedrock. The source is
`tools/clips_<creature>.py`, which keys them the way an animator keys a mob: a handful of poses
per clip, Catmull-Rom between them, a STEP key where something has to happen in no time.

Before this, the clips were Python pose functions. Only the (lost) datapack baker and the GIF
renderer could see them; every `.bbmodel` shipped with an empty Animate tab.

Rebuild:  `python3 tools/export_bb.py` (writes the keys into the projects)
Previews: `python3 tools/blockbench_run.py --blockbench <web build> previews`
          → `animations/previews/*.gif`, rendered by Blockbench itself

## How they are built

The original set got its creepiness from five devices, and they still do the work — but not by
quantising time any more. A creature that stutters all the time reads as a glitch; one that
moves with weight and then does ONE thing too fast reads as alive, which is worse.

| device     | now                                                                          |
|------------|------------------------------------------------------------------------------|
| `hold`     | long stillness, then one fast heavy move that overshoots and settles          |
| `lag`      | the head and neck trail the body — or refuse to follow it at all              |
| `asym`     | one leg reaches further and lifts higher; arms on a different count to legs   |
| `overbend` | a joint carried past where a joint stops (the Sun Man's neck in `lurch`)      |
| `stutter`  | only where it IS the point: STEP keys, no frames between (`stare_down`, `head_snap`) |

**Walks plant their feet.** A hand-keyed walk on a four-block stilt slides. The legs of every
locomotion clip are generated: the FOOT path is designed (locked to the ground and carried back
at constant speed through stance, then lifted and swung forward), two-bone IK turns it into
thigh and knee angles, and those are sampled back to 12–16 sparse keys per cycle. The Locust's
feet — and, when it scuttles, its hands — are solved against the rig's full forward kinematics
(`gait.key_feet`), so they plant correctly under a body bent double. A longer stride is a
longer stance, so in a limp both feet still move at the body's one speed. `tools/check.py`
measures how far a planted foot leaves the ground. Set the entity's movement speed to the
clip's or the feet will slide:

| clip                     | speed (blocks/s) | notes |
|--------------------------|------------------|-------|
| `dark_walker.walk`       | 1.72             | 2.5-block strides, foot down 62% of the cycle |
| `dark_walker.chase`      | 6.27             | a flight phase in every stride |
| `locust.stalk`           | 0.62             | high, pulled steps on reverse-bending knees |
| `locust.scuttle`         | 2.17             | four-legged: hands and feet, diagonal pairs |
| `sun_man.walk`           | 4.52             | the left leg reaches 22% further than the right |
| `sun_man.sprint`         | 15.7             | the left a third again as long as the right |

**Scale keys** stretch the Sun Man's neck. Blockbench, GeckoLib and Bedrock all scale a bone in
its own frame with the children inheriting it; the head takes the inverse, so the face is
carried out on the neck without being stretched. The Python solver carries full matrices
(`fk_matrices`), and a real Blockbench agrees with it on every bone's world position to 0.0001 px.

**Loops are seamless.** Blockbench wraps Catmull-Rom neighbours on a looping clip, so every
looping track starts and ends on the same key; `check.py` asserts it.

**Values are deltas on the rest pose.** The Locust and the Dark Walker stand in a posed rest
(bone rest rotations: the stoop, the fanned arms, the soft knees), so `idle` only has to breathe.

## Sun Man — mapped to the datapack's real states

State is picked by distance: 0 idle, 1 inside 110 blocks, 2 inside 55, 3 inside 26, 4 harvest.
His geometry is the author's; these only key the 29 bones it already has.

| clip           | state | loop | length | the idea |
|----------------|-------|------|--------|----------|
| `idle`         | 0     | loop | 8 s    | a statue that moves twice: the head snaps round past where it means to stop, shudders, and holds there listing over, far too long. The fingers spasm shut. Once, the body jumps a frame. The rays tick round like a clock, and tick back |
| `walk`         | 1     | loop | 9.6 s  | the legs walk — the left reaching further, the right dragging — and everything above the hips refuses: the torso leans BACK, the arms swing at half rate, the head lolls on a clock of its own and twitches hard, twice. The halo turns once |
| `sprint`       | 2     | loop | 2.6 s  | it runs, and the head never moves: carried like a held camera while the body sprints under it; the arms trail dead, only the fingers claw — and the rays spin like a saw blade the whole way in |
| `lurch`        | 3     | hold | 3.4 s  | three beats of nothing, then one heavy throw forward over the top of you, the neck whipping the other way, the rays flaring out |
| `stare_down`   | 3     | hold | 4 s    | the face comes down to you in eight STEP keys — jerks with no frames between — and with every jerk the neck is LONGER and the rays have ticked round. It arrives aimed at you, 54° down |
| `harvest_rise` | 4     | hold | 5 s    | day thirty: the upper arms open, then the lower; the neck straightens and lengthens until the whole thing is taller; the face tips up to the sky and the rays flare and turn |
| `grab`         | 4     | once | 3.8 s  | it folds down over you and the LOWER arms come to the ground, open, close, and carry it up |
| `peer`         | 3     | hold | 6 s    | it does not need to bend: the neck goes out over you and keeps going, twice as long as it was, until the face hangs in the air above you looking straight down, the rays turning round it |

## Locust — "It doesn't see you... but it knows you're there."

Rebuilt to the second set of references: **2.74 blocks, 11 bones, 77 cubes**. A puppet — a small
pale porcelain mask of a face (hollow eyes running into black tears, an open mouth) in a mass of
long black hair; a neck far too long; a body that is all ribs, with a caved pale chest stitched
shut and a black binding under it; black ragged hips; pale limb segments of old stained wood,
bound at every joint with black string; four needles for fingers on each hand, long enough to
reach the knee; and legs that taper to points instead of feet. The neck rides the head bone,
pivoting on the shoulders, so the whole stalk cranes, droops and snaps round as one.

Spawns `NoAI`, frozen. Waking is one-way.

| clip        | loop | length | the idea |
|-------------|------|--------|----------|
| `frozen`    | loop | 7 s    | it does not move; it does not breathe. Over seven seconds the head lists over too slowly to see — and at the end of the loop it is upright again, with nothing in between. A finger, once. A shoulder, once |
| `head_snap` | hold | 2.8 s  | its back to you, and then — between two frames — the mask is looking at you, 171° round on that neck. A breath later the neck cracks over sideways, as far as a neck does not go, and it shivers there |
| `twitch`    | loop | 3.2 s  | the idle inside 22 blocks: a slow weave, and through it spasms — the neck whips, a shoulder jumps out of its socket and back, the needles splay, a knee gives |
| `stalk`     | loop | 3.2 s  | a puppet nobody is working: high pulled steps on the points of its feet, the knees bending BACKWARD like a locust's, the body bobbing as if it hangs from a string, the arms swinging late and loose, the head lolling and looking about, never in time |
| `scuttle`   | loop | 0.9 s  | at a run it goes down: bent double, the neck straight up out of its shoulders so the mask stays level and aimed, running on the needles of its hands and the points of its feet |
| `rear`      | hold | 1.9 s  | the wake-up: it sinks, and then it is already up — arched back, arms flung high and splayed, needles open, the neck thrown back and over, shuddering |
| `climb`     | loop | 1.6 s  | up a wall facing it, diagonal pairs of limbs reaching in turn — with its head turned all the way round on that neck, looking back down at the floor. At you |
| `attack`    | once | 1.1 s  | it drops, lunges, both hands go in needles-first, it twists, and it tears them out |
| `peek`      | hold | 3.2 s  | round a door frame: one hand takes the jamb, the body leans, and the neck lays itself out sideways until the mask is looking at you on its side. It tips a little further, as if to see you better |
| `death`     | hold | 2.2 s  | its strings are cut: one last tug up, then everything at once — the knees fold the wrong way, the head swings down and bounces, and it tips over into a heap |

## Dark Walker — "It does not hurry, because it does not need to."

Tier 2, built from five references: a hilltop silhouette, an ink drawing, two frames of
something standing in a road at night with lit eyes, and one of it reaching over a fence at a
house. **7.28 blocks, 21 bones, 144 cubes**: a round brim twice the shoulder width over a low
stepped crown, a small head pushed out on a long neck, two eyes at `light_emission: 15` — narrow
lit slits — in the shadow of the brim, a stooped torso with shoulders wider than its hips, six arms in three tiers
that fan out and hang to the knee — each with an elbow and four long two-knuckled fingers — and
legs that are more than half of it, with knees.

It is deliberately the **outdoor** tier. The Locust is found standing inside houses at door
height; this one cannot follow you through a door. It is what is in the road, on the ridge,
over the fence.

| clip     | loop | length | the idea |
|----------|------|--------|----------|
| `idle`   | loop | 4 s    | it breathes — in, in, out short — six arms drifting on six clocks; once a loop the head tips over to one side, quicker than anything else it does, and stays, looking |
| `walk`   | loop | 2.4 s  | 1.2 s a step, knees giving on every contact; hips swing, torso turns against them, the neck cancels the rest so the brim never tips; each arm tier a beat behind the one above, so every step sends a wave down them |
| `chase`  | loop | 1.2 s  | when it does hurry: a long low lope, body pitched over its legs, arms streaming behind, head still level and aimed; the only clip where the brim bounces |
| `notice` | hold | 2.6 s  | looking off to its right — then the head comes round, slowly, and the last few degrees all at once; the body straightens, the hands open |
| `loom`   | hold | 3 s    | it folds down to your height without kneeling: hinges at the hips, the arms open round you, the brim tips forward over the eyes |
| `attack` | once | 1.6 s  | everything drawn back, then thrown — each arm a twentieth of a second behind the last, so they arrive as a wave; the hands close on the far side of you |
| `death`  | hold | 2.6 s  | thrown back, the knees go, and seven blocks of it go over sideways like something felled — the drop solved against the ground by the rig's own kinematics, the arms landing after the body |

**Why the body is grey and not black.** A black body can be a silhouette but it can never be
the pale thing caught in a headlight, and two of the five references are exactly that. A cold
mid-grey does both: backlit against a bright sky it reads as a pure silhouette, and in a light
at night it is the thing in the road. The hat stays black in every light.

## The grade

Shots are degraded like tape on purpose, and it is not decoration: `fx/overlay_vhs` is a
real `camera_overlay` the datapack keeps equipped, so scanlines and chroma tearing ARE the
player's view. Degradation ramps with proximity, the same way the sound design does.

`charge` and `closer` (the cinematic shots in `tools/shots.py`) cut to a full-bleed plate of the face. That is not a liberty either —
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

Everything lives in the one 512×512 atlas the pack already ships, because the item models have to
find their texture in-game and that one is known to work.

**The Locust and the Dark Walker** — `tools/paint_tiers.py` — are painted into the free quadrant
(x 0..256, y 256..512) at **32 texels to the block**, two per model pixel, so a two-pixel limb has a
highlight, a body and a shadow across it. Each cube has a box-style unwrap; right-side limbs share
their left twin's texels, mirrored; MaxRects packs it all into 77% of the quadrant. Painting is
done in world space — every texel knows the point on the model it lands on — so noise, ribs, string
bindings and the crease in a hat brim run across the seams between faces. The Locust's mask and
the Dark Walker's face are drawn by hand, a texel at a time: the Walker's eyes are narrow lit slits
in black sockets over a mouth that has been sewn shut.

**The Sun Man** — `tools/paint_sun_man.py` — keeps every UV he had. His faces sample 64×64
material tiles in the top half at three texels per model pixel, and those tiles were photographic
noise; the thirteen that are his and only his are repainted as pixel art for what they dress — robe
folds with tears and old blood, wrappings wound round him, the ink drawing's ridged neck, cracked
ivory bone, veined forearms, fingers dark to the second joint, crazed porcelain behind the face.

The contracts are unchanged and machine-checked (`tools/check.py`): the starburst face at
(256,256) is pixel-identical, and so is every tile that is not one of the Sun Man's thirteen (the
villager-head prop's and the unused ones). Both painters hash what they must not touch before and
after, and refuse to write if it moved.
