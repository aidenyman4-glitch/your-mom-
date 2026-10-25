"""Verifies every contract the project has. Run it after any rebuild; it exits non-zero on
the first broken one.

    python3 tools/check.py

  * the starburst face at atlas (256,256) and the Sun Man's own tiles are pixel-identical
  * the Sun Man's 197 cubes, 29 pivots, per-cube rotations and UVs are exactly the author's
  * bone budgets: Sun Man 29, Locust 11, Dark Walker 21 (a bone is an entity in the datapack)
  * every .bbmodel is a Bedrock Entity project carrying all of its creature's clips
  * every clip keys only bones that exist, inside its own length, and every looping track
    ends on the value it starts on (Blockbench wraps Catmull-Rom on loops, so that is what
    makes a loop seamless)
  * the walk cycles keep their feet planted: through stance the sole stays on the ground
  * every posed bone ships an item model + item definition, inside the [-16, 32] box, and
    nothing ships for a bone that no longer exists
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from PIL import Image                     # noqa: E402

import clips_dark_walker                  # noqa: E402
import clips_locust                       # noqa: E402
import clips_sun_man                      # noqa: E402
import gait                               # noqa: E402
import rig                                # noqa: E402
import tiers                              # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "resourcepack" / "assets" / "sunman"
FACE_HASH = "394858d53b822f85e30a8657ef4310e15fb496916295d27e9463b4f2bad2906c"
TILES_HASH = "c16093368cdfbed6a26a3c8e425da2c81abc77953109ed39ddf88b80ca30b995"
# sha256 over the Sun Man's elements as the handoff shipped them (see sun_man_geometry_hash)
SUN_MAN_GEOMETRY = "0141eb210bcc6c7aa391847c39f2f6117a41f62de914fd3fa8477959a94312b0"
BUDGET = {"sun_man": 29, "locust": 11, "dark_walker": 21}
CLIPS = {"sun_man": clips_sun_man, "locust": clips_locust, "dark_walker": clips_dark_walker}

failures = []


def check(ok, what):
    print(("  ok    " if ok else "  FAIL  ") + what)
    if not ok:
        failures.append(what)


def sun_man_geometry_hash(doc):
    els = {}
    for e in doc["elements"]:
        els[e["name"]] = (tuple(e["from"]), tuple(e["to"]), tuple(e["origin"]),
                          tuple(e.get("rotation", (0, 0, 0))),
                          tuple(sorted((k, tuple(v["uv"])) for k, v in e["faces"].items())))
    blob = json.dumps(sorted(els.items()), sort_keys=True).replace("-0.0", "0.0")
    return hashlib.sha256(blob.encode()).hexdigest()


def groups(doc):
    out = {}

    def walk(g, parent):
        out[g["name"]] = (g, parent)
        for c in g["children"]:
            if isinstance(c, dict):
                walk(c, g["name"])
    for g in doc["outliner"]:
        walk(g, None)
    return out


def main():
    print("atlas")
    im = Image.open(PACK / "textures" / "entity" / "sun_man.png").convert("RGBA")
    check(hashlib.sha256(im.crop((256, 256, 512, 512)).tobytes()).hexdigest() == FACE_HASH,
          "starburst face quadrant is pixel-identical")
    check(hashlib.sha256(im.crop((0, 0, 512, 256)).tobytes()).hexdigest() == TILES_HASH,
          "Sun Man material tiles are pixel-identical")

    print("blockbench projects")
    for name, budget in BUDGET.items():
        doc = json.loads((ROOT / "blockbench" / f"{name}.bbmodel").read_text())
        g = groups(doc)
        check(doc["meta"]["model_format"] == "bedrock", f"{name}: Bedrock Entity project")
        check(len(g) == budget, f"{name}: {len(g)} bones (budget {budget})")
        clips = CLIPS[name].CLIPS
        names = [a["name"] for a in doc["animations"]]
        check(names == list(clips), f"{name}: carries all {len(clips)} clips")
        if name == "sun_man":
            check(len(doc["elements"]) == 197, "sun_man: 197 cubes")
            check(sun_man_geometry_hash(doc) == SUN_MAN_GEOMETRY,
                  "sun_man: cubes, pivots-relative placement, rotations and UVs are the author's")
            pivots_ok = all(abs(g[b][0]["origin"][i] - rig.J[b][i] * rig.PX_PER_RU) < 1e-3
                            for b in rig.BONE_ORDER for i in range(3) if b != "root")
            check(pivots_ok, "sun_man: all 29 pivots where the rig puts them")
            check(all(not any(g[b][0].get("rotation", [0, 0, 0])) for b in g),
                  "sun_man: no rest rotation added to any bone")

    print("clips")
    for name, mod in CLIPS.items():
        rig_bones = set(mod.C.BONE_ORDER)
        for clip in mod.CLIPS.values():
            stray = [b for b in clip.bones() if b not in rig_bones]
            check(not stray, f"{clip.name}: keys only real bones {stray or ''}".rstrip())
            inside = all(0.0 <= k.time <= clip.length + 1e-9
                         for t in clip.tracks.values() for k in t)
            seam = True
            if clip.loop == "loop":
                for (bone, ch), track in clip.tracks.items():
                    if (track[0].time > 1e-6 or abs(track[-1].time - clip.length) > 1e-6
                            or max(abs(a - b) for a, b in zip(track[0].value, track[-1].value)) > 1e-6):
                        seam = False
                        print(f"        seam: {bone}.{ch}")
            check(inside and seam, f"{clip.name}: keys inside 0..{clip.length}s"
                  + (", seamless loop" if clip.loop == "loop" else ""))

    print("gait")
    for mod, name, tol in ((clips_dark_walker, "animation.dark_walker.walk", 0.6),
                           (clips_dark_walker, "animation.dark_walker.chase", 0.8),
                           (clips_locust, "animation.locust.stalk", 0.4),
                           (clips_locust, "animation.locust.scuttle", 0.4),
                           (clips_sun_man, "animation.sun_man.walk", 0.25),
                           (clips_sun_man, "animation.sun_man.sprint", 0.4)):
        ppb = getattr(mod, "PPB", 16.0)
        rep = gait.check(mod.CLIPS[name], mod.C, mod.LEGS, ppb=ppb, fps=40)
        worst = 0.0
        for leg, pts in zip(mod.LEGS, rep):
            # a planted foot is the one travelling BACKWARD under the body; measure how far it
            # leaves the ground while it does (trimming the contact frames at each end)
            n = len(pts)
            back = [pts[(i + 1) % n][1] - pts[i][1] < -1e-4 for i in range(n)]
            runs, cur = [], []
            for i in list(range(n)) * 2:
                if back[i]:
                    cur.append(i)
                elif cur:
                    runs.append(cur)
                    cur = []
            run = max(runs, key=len)
            trim = max(1, len(run) // 10)
            # a leg with an ankle peels its heel up over the last 30% of stance, on purpose
            end = len(run) - (int(len(run) * 0.3) if leg.foot else trim)
            ys = [pts[i][0] for i in run[trim:end]]
            ref = sorted(ys)[len(ys) // 2]
            worst = max(worst, max(abs(y - ref) for y in ys))
        unit = "blocks" if ppb == 1.0 else "px"
        check(worst <= tol, f"{name}: planted foot stays within {worst:.2f} {unit} of the ground")

    print("item models")
    for c in tiers.TIERS.values():
        models = PACK / "models" / "item" / c.name
        posed = [b for b in c.BONE_ORDER if c.GEOMETRY.get(b)]
        have = sorted(p.stem for p in models.glob("*.json"))
        check(have == sorted(posed), f"{c.name}: one model per posed bone, nothing stale")
        items = sorted(p.stem for p in (PACK / "items").glob(f"{c.name}_*.json"))
        check(items == sorted(f"{c.name}_{b}" for b in posed), f"{c.name}: one item definition per part")
        far = 0.0
        lit = 0
        for p in models.glob("*.json"):
            for el in json.loads(p.read_text())["elements"]:
                far = max([far] + [abs(v - 8.0) for v in el["from"] + el["to"]])
                lit += 1 if el.get("light_emission") == 15 else 0
        check(far <= 24.0, f"{c.name}: every element inside [-16, 32] (furthest {far:.1f}px from pivot)")
        if c.name == "dark_walker":
            check(lit == 2, "dark_walker: both eyes at light_emission 15")

    print()
    if failures:
        print(f"{len(failures)} check(s) failed")
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
