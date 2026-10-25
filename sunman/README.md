# Sun Man, the Locust and the Dark Walker

Three horror creatures for Minecraft Java 26.3, modelled and animated in Blockbench mod style.
Open any `.bbmodel` in [`blockbench/`](blockbench) and press play in the Animate tab.

| | bones | cubes | clips | height |
|---|---|---|---|---|
| **Sun Man** | 29 | 197 | idle · walk · sprint · lurch · stare_down · harvest_rise · grab · peer | 72.9 blocks |
| **Locust** | 11 | 77 | frozen · head_snap · twitch · stalk · scuttle · rear · climb · attack · peek · death | 2.7 blocks |
| **Dark Walker** | 21 | 144 | idle · walk · chase · notice · loom · attack · death | 7.3 blocks |

![Dark Walker](docs/dark_walker_turnaround.png)
![Locust](docs/locust_turnaround.png)
![Sun Man](docs/sun_man_turnaround.png)

| Locust · head_snap | Locust · scuttle | Sun Man · peer |
|---|---|---|
| ![](animations/previews/locust_head_snap.gif) | ![](animations/previews/locust_scuttle.gif) | ![](animations/previews/sun_man_peer.gif) |
| **Dark Walker · walk** | **Locust · stalk** | **Sun Man · stare_down** |
| ![](animations/previews/dark_walker_walk.gif) | ![](animations/previews/locust_stalk.gif) | ![](animations/previews/sun_man_stare_down.gif) |

Every clip has a preview in [`animations/previews/`](animations/previews), rendered by Blockbench
itself. What each clip is for, and the movement speed each walk is tuned to, is in
[`animations/CLIPS.md`](animations/CLIPS.md).

## What's where

- `blockbench/` — the three projects (Bedrock Entity format, texture embedded, clips included)
- `bedrock/` — `.geo.json` + `.animation.json` for each, for GeckoLib or Bedrock
- `resourcepack/` — the per-bone item models and the atlas the datapack rig uses
- `rig/` — each skeleton as JSON: pivots in blocks, rest rotations, clip index
- `tools/` — the generators; `python3 tools/check.py` verifies every contract
- [`HANDOFF.md`](HANDOFF.md) — the technical handoff: constraints, conventions, how to rebuild

The Sun Man's geometry is the original author's and is untouched — his animations and the
painting on his surface are new.
