"""Runs the projects through a REAL Blockbench, headlessly, and keeps what it says.

Everything else in tools/ is our own maths; this is the ground truth. It serves a Blockbench
web build locally, opens each .bbmodel in it with Playwright, and:

    verify    loads every project, reports what Blockbench sees (format, cubes, bones,
              textures, clips), then samples Blockbench's OWN interpolator on every
              animated bone and compares it with keyframes.Clip.sample — so the
              datapack/renderers bake exactly what the Animate tab plays
    bedrock   exports bedrock/<name>.geo.json + .animation.json through Blockbench's own
              Bedrock codecs (what GeckoLib and Bedrock read)
    previews  plays every clip in Blockbench and writes animations/previews/<clip>.gif,
              plus a turnaround still of each creature in docs/

    python3 tools/blockbench_run.py --blockbench /path/to/blockbench-web all

Needs Node with `playwright` available and a Blockbench web build (a directory with
index.html — e.g. `npm run build-web` in a Blockbench checkout). Validated against 5.1.3.
"""
import argparse
import functools
import math
import http.server
import json
import socketserver
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
TOOLS = Path(__file__).resolve().parent
BB = ROOT / "blockbench"
NAMES = ("sun_man", "locust", "dark_walker", "birthday_crown", "birthday_tree")
PPB = {"sun_man": 4.0 / 3.0, "locust": 16.0, "dark_walker": 16.0,
       "birthday_crown": 16.0, "birthday_tree": 16.0}
# the Birthday People are drawn in pencil on paper; render them on paper grey, so the black
# columns read the way they do in the drawings
BACKGROUND = {"birthday_crown": "#b8b2a8", "birthday_tree": "#b8b2a8"}
# creatures that also get a 360-degree turntable GIF in docs/
TURNTABLE = {"birthday_crown": ([0, 70, 175], [0, 58, 0]),
             "birthday_tree": ([0, 74, 185], [0, 62, 0])}

# camera per clip: (fps, eye, target, extra frames held on the last pose)
CAM = {
    "dark_walker": {"_still": ([105, 82, 140], [0, 58, 0]),
                    "idle": (10, [70, 98, 120], [0, 80, 0], 0),
                    "walk": (12.5, [170, 70, 40], [0, 56, 0], 0),
                    "chase": (15, [170, 70, 40], [0, 52, 0], 0),
                    "notice": (12.5, [60, 102, 110], [0, 86, 0], 4),
                    "loom": (10, [150, 66, 150], [0, 50, 20], 4),
                    "attack": (15, [150, 70, 110], [0, 55, 10], 0),
                    "death": (10, [30, 120, 230], [20, 36, 0], 4)},
    "locust": {"_still": ([45, 40, 60], [0, 29, 0]),
               "frozen": (10, [45, 40, 60], [0, 30, 0], 0),
               "head_snap": (10, [-38, 42, -65], [0, 30, 0], 4),
               "twitch": (12.5, [42, 40, 60], [0, 30, 0], 0),
               "stalk": (12.5, [80, 35, 20], [0, 26, 0], 0),
               "scuttle": (20, [75, 32, 32], [0, 18, 5], 0),
               "rear": (12.5, [55, 40, 65], [0, 30, 0], 4),
               "climb": (12.5, [-50, 45, -58], [0, 30, 0], 0),
               "attack": (15, [62, 38, 60], [0, 25, 8], 0),
               "peek": (10, [12, 40, 75], [0, 32, 0], 4),
               "death": (12.5, [58, 38, 70], [0, 18, 0], 4)},
    **{name: {"_still": ([95, 76, 160], [0, 58, 0]),
              "idle": (10, [70, 84, 150], [0, 64, 0], 0),
              "walk": (12.5, [185, 66, 40], [0, 54, 0], 0),
              "turn": (10, [36, 92, 120], [0, 78, 0], 4),
              "reach": (10, [150, 74, 110], [0, 62, 18], 4),
              "grab": (15, [150, 74, 120], [0, 60, 14], 0),
              "dangle": (12.5, [95, 80, 150], [0, 64, 0], 0),
              "death": (10, [60, 105, 215], [0, 30, 30], 4)}
       for name in ("birthday_crown", "birthday_tree")},
    "sun_man": {"_still": ([80, 60, 140], [0, 48, 0]),
                "idle": (6, [60, 80, 110], [0, 70, 6], 0),
                "walk": (6, [170, 50, 30], [0, 46, 0], 0),
                "sprint": (12.5, [170, 50, 30], [0, 44, 0], 0),
                "lurch": (10, [90, 50, 140], [0, 48, 10], 4),
                "stare_down": (8, [100, 50, 150], [0, 54, 16], 4),
                "harvest_rise": (8, [70, 60, 150], [0, 52, 0], 4),
                "grab": (10, [120, 55, 130], [0, 44, 10], 0),
                "peer": (8, [150, 46, 130], [0, 50, 30], 4)},
}


class Server:
    def __init__(self, directory):
        handler = functools.partial(_Quiet, directory=str(directory))
        self.httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/index.html"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def run_job(job):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(job, f)
    out = subprocess.run(["node", str(TOOLS / "blockbench" / "bb.js"), f.name],
                         capture_output=True, text=True, timeout=3600)
    Path(f.name).unlink()
    if out.returncode:
        raise RuntimeError(out.stderr[-2000:])
    lines = [l for l in out.stdout.splitlines() if l.strip()]
    return json.loads(lines[0]), lines[1:]


def verify(url, names=NAMES):
    mods = {n: __import__(f"clips_{n}") for n in NAMES}
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        for name in names:
            sample = Path(tmp) / f"{name}.json"
            rep, extra = run_job({"url": url, "model": str(BB / f"{name}.bbmodel"),
                                  "sample": {"path": str(sample), "steps": 37}})
            print(f"  {name:12} Blockbench {rep['blockbench']}  format {rep['format']}  "
                  f"{rep['cubes']} cubes  {rep['bones']} bones  {rep['animations']} clips  "
                  f"texture {rep['textures'][0]['width']}x{rep['textures'][0]['height']}"
                  f"{'  ' + ' '.join(extra) if extra else ''}")
            ok &= not rep["errors"] and not any(t["error"] for t in rep["textures"])
            dump = json.loads(sample.read_text())
            worst, n = 0.0, 0
            for clip_name, rows in dump.items():
                clip = mods[name].CLIPS[clip_name]
                for row in rows:
                    mine = clip.sample(row["t"])
                    for bone, v in row["bones"].items():
                        for ch, key, scale in (("rotation", "r", 1.0), ("position", "p", PPB[name])):
                            m = mine.get(bone, {}).get(ch)
                            if v[key] is None or m is None:
                                continue
                            worst = max(worst, max(abs(v[key][i] - m[i] * scale) for i in range(3)))
                            n += 1
            print(f"  {'':12} interpolation: {n} channel samples, worst |Blockbench - Python| = {worst:.5f}")
            ok &= worst < 1e-3
    print("verify:", "passed" if ok else "FAILED")
    return ok


def bedrock(url, names=NAMES):
    out = ROOT / "bedrock"
    out.mkdir(exist_ok=True)
    for name in names:
        geo, anim = out / f"{name}.geo.json", out / f"{name}.animation.json"
        rep, extra = run_job({"url": url, "model": str(BB / f"{name}.bbmodel"),
                              "export": {"bedrock_geo": str(geo), "bedrock_anim": str(anim)}})
        g = json.loads(geo.read_text())
        a = json.loads(anim.read_text())
        bones = g["minecraft:geometry"][0]["bones"]
        print(f"  {name:12} {len(bones)} bones  {sum(len(b.get('cubes', [])) for b in bones)} cubes  "
              f"{len(a['animations'])} animations  -> bedrock/{geo.name}, bedrock/{anim.name}")


def _fit(text, n):
    return text if len(text) <= n else text[:text.rfind(" ", 0, n - 1)] + "…"


def _centre(im, aspect=1.0):
    """With the side panels hidden the viewport is wide; keep the middle, where the camera
    is aimed."""
    w = min(im.width, int(im.height * aspect))
    x0 = (im.width - w) // 2
    return im.crop((x0, 0, x0 + w, im.height))


def previews(url, names=NAMES):
    from PIL import Image, ImageDraw, ImageFont
    import cine
    font = ImageFont.truetype(cine.FONT, 13)
    small = ImageFont.truetype(cine.FONT, 11)
    out = ROOT / "animations" / "previews"
    out.mkdir(parents=True, exist_ok=True)
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    for name in names:
        mod = __import__(f"clips_{name}")
        cams = CAM[name]
        with tempfile.TemporaryDirectory() as tmp:
            clips = []
            for clip in mod.CLIPS.values():
                short = clip.name.split(".")[-1]
                fps, eye, target, hold = cams[short]
                clips.append({"animation": clip.name, "fps": fps, "position": eye, "target": target,
                              "frames_dir": f"{tmp}/{short}", "hold_frames": hold,
                              "background": BACKGROUND.get(name)})
            eye, target = cams["_still"]
            sides = [("front", eye, target),
                     ("side", [eye[2] * 1.15, eye[1], 0], target),
                     ("back", [-eye[0], eye[1], -eye[2]], target)]
            shots = [{"name": f"still_{s}", "position": e, "target": t} for s, e, t in sides]
            if name in TURNTABLE:
                (tx, ty, tz), tgt = TURNTABLE[name]
                for k in range(36):
                    a = math.tau * k / 36
                    shots.append({"name": f"spin_{k:02d}", "target": tgt,
                                  "position": [tz * math.sin(a), ty, tz * math.cos(a)]})
            for sh in shots:
                sh["background"] = BACKGROUND.get(name)
            run_job({"url": url, "model": str(BB / f"{name}.bbmodel"), "out_dir": tmp,
                     "clips": clips, "shots": shots})
            if name in TURNTABLE:
                spin = [_centre(Image.open(f"{tmp}/spin_{k:02d}.png").convert("RGB"), 0.62)
                        for k in range(36)]
                spin = [im.resize((300, int(im.height * 300 / im.width)), Image.LANCZOS) for im in spin]
                pal = spin[0].quantize(colors=128, method=Image.MEDIANCUT)
                q = [im.quantize(palette=pal, dither=Image.NONE) for im in spin]
                path = docs / f"{name}_turntable.gif"
                q[0].save(path, save_all=True, append_images=q[1:], duration=110, loop=0,
                          optimize=True, disposal=1)
                print(f"  {path.relative_to(ROOT)}  36 frames  {path.stat().st_size // 1024} KB")
            stills = [_centre(Image.open(f"{tmp}/still_{s}.png").convert("RGB")) for s, _, _ in sides]
            w = 420
            stills = [s.resize((w, int(s.height * w / s.width)), Image.LANCZOS) for s in stills]
            sheet = Image.new("RGB", (w * 3, stills[0].height))
            for i, s in enumerate(stills):
                sheet.paste(s, (i * w, 0))
            sheet.save(docs / f"{name}_turnaround.png", optimize=True)
            for clip, spec in zip(mod.CLIPS.values(), clips):
                frames = sorted(Path(spec["frames_dir"]).glob("*.png"))
                ims = []
                for f in frames:
                    im = _centre(Image.open(f).convert("RGB"))
                    im = im.resize((360, int(im.height * 360 / im.width)), Image.LANCZOS)
                    d = ImageDraw.Draw(im)
                    d.rectangle([0, im.height - 38, im.width, im.height], fill=(14, 15, 19))
                    d.text((8, im.height - 35), clip.name.replace("animation.", ""), font=font,
                           fill=(222, 218, 226))
                    d.text((8, im.height - 18), _fit(f"{clip.loop} · {clip.length:g}s · {clip.note}", 50),
                           font=small, fill=(130, 126, 138))
                    ims.append(im)
                pal = ims[len(ims) // 2].quantize(colors=96, method=Image.MEDIANCUT)
                q = [i.quantize(palette=pal, dither=Image.NONE) for i in ims]
                path = out / f"{clip.name.replace('animation.', '').replace('.', '_')}.gif"
                q[0].save(path, save_all=True, append_images=q[1:], duration=int(1000 / spec["fps"]),
                          loop=0, optimize=True, disposal=1)
                print(f"  {path.relative_to(ROOT)}  {len(ims)} frames  {path.stat().st_size // 1024} KB")


def props(url):
    """Stills of the village props (blockbench/village_props.bbmodel): the dead villagers
    (docs/dead_villagers.png) and the rest (docs/village_props.png), on grass green."""
    from PIL import Image
    g = "#6a9a3c"
    with tempfile.TemporaryDirectory() as tmp:
        shots = []
        for i, x in enumerate((-88, -44, 0)):
            shots.append({"name": f"p{i}_a", "position": [x + 26, 30, 34], "target": [x, 2, 2], "background": g})
            shots.append({"name": f"p{i}_b", "position": [x - 30, 26, -30], "target": [x, 2, 0], "background": g})
        shots.append({"name": "head", "position": [62, 18, 22], "target": [44, 2, 0], "background": g})
        shots.append({"name": "arm", "position": [104, 16, 20], "target": [88, 1, 0], "background": g})
        # the cross faces -Z in the model: look at it from there, and from below, as from the street
        shots.append({"name": "cross_front", "position": [-40, 40, 10], "target": [-60, 30, 70], "background": "#3c4250"})
        shots.append({"name": "cross_low", "position": [-96, 10, 20], "target": [-60, 30, 70], "background": "#3c4250"})
        shots.append({"name": "golem_a", "position": [58, 46, 108], "target": [18, 4, 70], "background": g})
        shots.append({"name": "golem_b", "position": [20, 62, 28], "target": [16, 2, 72], "background": g})
        shots.append({"name": "grass", "position": [-48, 15, 172], "target": [-48, 4, 130], "background": g})
        shots.append({"name": "wood_a", "position": [30, 24, 156], "target": [10, 1, 130], "background": g})
        shots.append({"name": "wood_b", "position": [70, 22, 158], "target": [52, 2, 130], "background": g})
        shots.append({"name": "wood_c", "position": [118, 28, 160], "target": [97, 1, 132], "background": g})
        run_job({"url": url, "model": str(BB / "village_props.bbmodel"), "out_dir": tmp, "clips": [], "shots": shots})

        def im(name, w=420):
            i = _centre(Image.open(f"{tmp}/{name}.png").convert("RGB"), 1.2)
            return i.resize((w, int(i.height * w / i.width)), Image.LANCZOS)
        ims = {s["name"]: im(s["name"]) for s in shots}
        h = ims["p0_a"].height
        sheet = Image.new("RGB", (420 * 3, h * 3), (106, 154, 60))
        for k, name in enumerate(["p0_a", "p1_a", "p2_a", "p0_b", "p1_b", "p2_b"]):
            sheet.paste(ims[name], ((k % 3) * 420, (k // 3) * h))
        sheet.paste(ims["head"], (210, 2 * h))
        sheet.paste(ims["arm"], (630, 2 * h))
        sheet.save(ROOT / "docs" / "dead_villagers.png", optimize=True)
        sheet = Image.new("RGB", (420 * 4, h * 2), (106, 154, 60))
        for k, name in enumerate(["cross_front", "cross_low", "golem_a", "golem_b",
                                  "grass", "wood_a", "wood_b", "wood_c"]):
            sheet.paste(ims[name], ((k % 4) * 420, (k // 4) * h))
        sheet.save(ROOT / "docs" / "village_props.png", optimize=True)
    print("  docs/dead_villagers.png, docs/village_props.png")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blockbench", required=True, help="Blockbench web build directory (has index.html)")
    ap.add_argument("--only", nargs="+", choices=NAMES, default=list(NAMES), help="creatures to process")
    ap.add_argument("what", nargs="+", choices=("verify", "bedrock", "previews", "props", "all"))
    args = ap.parse_args()
    what = set(args.what)
    if "all" in what:
        what = {"verify", "bedrock", "previews"}
    srv = Server(Path(args.blockbench))
    ok = True
    try:
        if "verify" in what:
            print("verify")
            ok = verify(srv.url, args.only)
        if "bedrock" in what:
            print("bedrock")
            bedrock(srv.url, args.only)
        if "previews" in what:
            print("previews")
            previews(srv.url, args.only)
        if "props" in what or "all" in what:
            print("props")
            props(srv.url)
    finally:
        srv.close()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
