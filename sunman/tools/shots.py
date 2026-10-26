"""Every clip, with its camera. Run this to rebuild `animations/`.

A shot is a pose function plus a camera path plus a grade ramp. The camera matters as much
as the pose: the same `sprint` clip is a curiosity at 60 blocks and unbearable at 4, and
only a perspective camera can tell the difference.
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cine                      # noqa: E402
import clips_dark_walker         # noqa: E402
import clips_locust              # noqa: E402
import clips_sun_man             # noqa: E402
import palette as pal            # noqa: E402
import rig                       # noqa: E402
import tiers                     # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "animations" / "shots"
SIZE = (400, 540)

SM = clips_sun_man.CLIPS
LC = clips_locust.CLIPS
DW = clips_dark_walker.CLIPS
STILL = {"torso": (1.2, 0.0, 0.0), "neck": (-1.0, 0.0, 0.0)}   # for the shot where only the distance changes


def clip_fn(clip):
    """The renderers take pose(phase); a keyframed clip samples itself at phase * length."""
    return clip.at


def lerp(a, b, t):
    return a + (b - a) * t


def ease_in(t, power=1.7):
    return t ** power


# ---------------------------------------------------------------- the insert frame

_ART = None


def face_art():
    global _ART
    if _ART is None:
        _ART = Image.open(rig.ATLAS).convert("RGBA").crop((256, 256, 512, 512))
    return _ART


def face_plate(size, rng, text="DO NOT LOOK UP"):
    """One frame of nothing but the face, full bleed.

    This is not a liberty: `fx/overlay_gaze` swaps the player's camera_overlay to the
    white-out plate the moment the raycast in ai/gaze_step connects with the head. Looking
    at it really does fill your screen. The clip cuts to it the way the game does.

    The art is a white starburst on transparency, so it goes on a near-black ground and is
    bloomed rather than brightened — on a pale ground it vanishes into the paper.
    """
    W, H = size
    art = face_art()
    s = W * 1.22
    big = art.resize((int(s), int(s)), Image.LANCZOS)
    img = Image.new("RGB", size, (11, 10, 13))
    img.paste(big, (int((W - s) / 2), int(H * 0.40 - s / 2)), big)

    halo = img.filter(ImageFilter.GaussianBlur(14))
    img = Image.fromarray(np.clip(np.asarray(img, dtype=np.float32)
                                  + np.asarray(halo, dtype=np.float32) * 0.85,
                                  0, 255).astype(np.uint8))

    a = np.asarray(img, dtype=np.float32)
    a += rng.normal(0.0, 9.0, (H // 2 + 1, W // 2 + 1, 1)).repeat(2, 0).repeat(2, 1)[:H, :W]
    a[0::3, :, :] *= 0.80
    off = int(rng.integers(3, 9))
    a[..., 0] = np.roll(a[..., 0], off, axis=1)
    a[..., 2] = np.roll(a[..., 2], -off, axis=1)
    y0 = int(rng.integers(0, H - 30))
    a[y0:y0 + 18] = np.roll(a[y0:y0 + 18], int(rng.integers(-30, 30)), axis=1) * 0.85
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

    d = ImageDraw.Draw(img, "RGBA")
    f = ImageFont.truetype(cine.FONT, 27)
    tw = d.textlength(text, font=f)
    d.text(((W - tw) / 2 + 2, H * 0.855 + 2), text, font=f, fill=(0, 0, 0, 190))
    d.text(((W - tw) / 2, H * 0.855), text, font=f, fill=(236, 231, 222, 240))
    return img


def black_frame(size, ghost=None, strength=0.10):
    img = Image.new("RGB", size, (4, 4, 6))
    if ghost is not None:
        img = Image.blend(img, ghost.filter(ImageFilter.GaussianBlur(5)), strength)
    return img


# ---------------------------------------------------------------- the shot runner

def render(spec):
    name = spec["name"]
    frames = spec["frames"]
    size = spec.get("size", SIZE)
    subject = spec["subject"]
    scene = spec.get("scene", [])
    rng = np.random.default_rng(spec.get("seed", 7))
    art = face_art() if spec.get("art", False) else None

    imgs, durations = [], []
    for i in range(frames):
        p = i / frames
        k = spec["f"](i, p)
        if k.get("insert") == "face":
            imgs.append(face_plate(size, rng))
            durations.append(k.get("ms", 70))
            continue
        if k.get("insert") == "black":
            imgs.append(black_frame(size, imgs[-1] if imgs else None,
                                    k.get("ghost", 0.10)))
            durations.append(k.get("ms", 260))
            continue

        shake = k.get("shake", 0.0)
        jit = rng.normal(0.0, shake, 3) if shake else (0.0, 0.0, 0.0)
        eye = tuple(k["eye"][j] + jit[j] for j in range(3))
        cam = cine.Cam(eye, k["target"], fov=k.get("fov", 70.0), roll=k.get("roll", 0.0))
        quads = scene + cine.collect(subject, k["pose"])
        img, glow = cine.rasterise(quads, cam, size, fog_dist=k.get("fog", 78.0), art=art,
                                   sky=k.get("sky"), lamp=k.get("lamp", 0.0),
                                   lamp_reach=k.get("lamp_reach", 9.0))
        img = cine.grade(img, glow, k.get("intensity", 0.3), rng, bloom=k.get("bloom", 0.0),
                         mono=k.get("mono", False))
        cine.burn_in(img, spec["label"], spec["note"], i, frames,
                     tape=spec.get("tape", "REC"), flash=k.get("flash", 0.0))
        imgs.append(img)
        durations.append(k.get("ms", 90))

    path = cine.save_gif(OUT / f"{name}.gif", imgs, durations)
    print(f"  {path.name:22} {frames:3d}f  {path.stat().st_size // 1024:5d} KB")
    return path


# ====================================================================== SUN MAN

ROAD = cine.ground_quads() + cine.treeline(11, count=34, near=16.0, far=130.0, road=10.0)
FIELD = cine.ground_quads() + cine.treeline(4, count=26, near=26.0, far=150.0, road=18.0)


def sunman_charge():
    """It closes from 56 blocks to four and a half. The camera is a player's eyes: 1.62 up,
    and it tilts further back the whole way, because it has to."""
    sun = cine.sunman_subject()
    N = 46

    def f(i, p):
        if i >= N - 5:
            seq = {N - 5: ("face", 70), N - 4: ("face", 60), N - 3: ("black", 90),
                   N - 2: ("face", 50), N - 1: ("black", 420)}
            kind, ms = seq[i]
            return {"insert": kind, "ms": ms, "ghost": 0.16}
        t = i / (N - 6)
        k = ease_in(t, 1.8)
        d = lerp(56.0, 4.4, k)
        stride = (p * 3.6) % 1.0
        bob = 0.05 * math.sin(stride * math.tau * 2)
        return {
            "pose": SM["animation.sun_man.sprint"].at(stride),
            "eye": (lerp(0.0, 0.6, k), 1.62 + bob, d),
            "target": (0.0, 30.0, 0.0),
            "fov": lerp(70.0, 96.0, k),
            "roll": math.sin(t * 9.0) * 3.4 * k,
            "shake": 0.02 + 0.30 * k ** 2,
            "intensity": 0.12 + 0.88 * k,
            "bloom": max(0.0, (k - 0.45) / 0.55) * 1.3,
            "fog": lerp(115.0, 170.0, k),
            "flash": 0.55 * max(0.0, (k - 0.93) / 0.07),
            "ms": int(lerp(120, 46, k)),
        }
    return {"name": "charge", "label": "Sprint", "note": "state 2 · inside 55 blocks",
            "subject": sun, "frames": N, "scene": ROAD, "f": f, "art": True,
            "tape": "REC", "seed": 3}


def sunman_closer():
    """Five stations. It is nearer at every one and it has not moved a limb.

    No transitions, and the frame right after each jump is a short one, so the change
    lands a beat after you have already looked at it. By the last station it no longer
    fits in the frame, which is the honest answer to what 73 blocks looks like at eleven
    paces — so the shot ends the only way it can, by tilting up to find the face.
    """
    sun = cine.sunman_subject()
    stations = [62.0, 44.0, 30.0, 19.0, 11.0]
    held = 5
    N = len(stations) * held + 5

    def f(i, p):
        if i >= N - 5:                                   # look up. Rule Two.
            j = i - (N - 5)
            if j >= 3:
                return {"insert": "face", "ms": 90 if j == 3 else 520, "ghost": 0.2}
            return {
                "pose": STILL,
                "eye": (0.0, 1.62, 11.0),
                "target": (0.0, lerp(5.2, 62.0, (j + 1) / 3.0), 0.0),
                "fov": 86.0, "shake": 0.05 + 0.05 * j,
                "intensity": 0.6 + 0.2 * j, "bloom": 0.5 + 0.5 * j,
                "fog": 90.0, "ms": 150,
            }
        st, step = divmod(i, held)
        d = stations[st]
        jump = step == 0 and st > 0
        return {
            "pose": STILL,
            "eye": (0.0, 1.62, d),
            "target": (0.0, d * 0.47, 0.0),
            "fov": 74.0,
            "shake": 0.004,
            "intensity": 0.95 if jump else 0.22 + 0.1 * st,
            "bloom": 0.1 * st,
            "fog": 86.0,
            "ms": 70 if jump else (430 if step < held - 1 else 250),
        }
    return {"name": "closer", "label": "It has not moved",
            "note": "62 / 44 / 30 / 19 / 11 blocks", "subject": sun,
            "frames": N, "scene": ROAD, "f": f, "art": True, "tape": "PLAY", "seed": 19}


def sunman_arch():
    """State 3, inside 26 blocks: it holds still, then folds forward over the top of you."""
    sun = cine.sunman_subject()
    N = 30

    def f(i, p):
        snap = max(0.0, (p - 0.60) / 0.40)
        return {
            "pose": SM["animation.sun_man.lurch"].at(p),
            "eye": (1.2, 1.62, 33.0),
            "target": (0.0, 34.0 + 12.0 * snap, 0.0),
            "fov": lerp(76.0, 90.0, snap),
            "roll": -2.0 * snap,
            "shake": 0.01 + 0.22 * snap,
            "intensity": 0.34 + 0.62 * snap,
            "bloom": 0.9 * snap,
            "fog": 110.0,
            "flash": 0.42 if 0.60 <= p < 0.66 else 0.0,
            "ms": 150 if p < 0.58 else 60,
        }
    return {"name": "arch", "label": "Arch", "note": "state 3 · inside 26 blocks",
            "subject": sun, "frames": N, "scene": ROAD, "f": f, "art": True, "seed": 5}


def sunman_stare():
    """The neck lowers the face toward you in eight steps and then stops."""
    sun = cine.sunman_subject()
    N = 28

    def f(i, p):
        return {
            "pose": SM["animation.sun_man.stare_down"].at(p),
            "eye": (0.0, 1.62, 40.0),
            "target": (0.0, 34.0, 0.0),
            "fov": 76.0,
            "shake": 0.01 + 0.05 * p,
            "intensity": 0.28 + 0.5 * p,
            "bloom": 0.3 + 0.7 * p,
            "fog": 96.0,
            "ms": 110,
        }
    return {"name": "stare_down", "label": "Stare down", "note": "the face descends in jerks",
            "subject": sun, "frames": N, "scene": ROAD, "f": f, "art": True, "seed": 8}


def sunman_wide(name, label, note, clip, dist=74.0, ty=36.0, intensity=0.3, ms=110, N=24):
    sun = cine.sunman_subject()

    def f(i, p):
        return {"pose": clip(p), "eye": (6.0, 1.62, dist), "target": (0.0, ty, 0.0),
                "fov": 68.0, "shake": 0.02, "intensity": intensity,
                "bloom": 0.25, "fog": 120.0, "ms": ms}
    return {"name": name, "label": label, "note": note, "subject": sun, "frames": N,
            "scene": FIELD, "f": f, "art": True, "tape": "REC", "seed": 13}


# ====================================================================== LOCUST

def locust_shot(name, label, note, clip, cam, N=22, ms=100, scene=None, seed=21,
                intensity=0.34, bloom=0.0, flash=None, tail=None):
    sub = cine.creature_subject(tiers.LOCUST)

    def f(i, p):
        if tail and i >= N - len(tail):
            kind, ms2 = tail[i - (N - len(tail))]
            return {"insert": kind, "ms": ms2, "ghost": 0.2}
        c = cam(p)
        c.setdefault("intensity", intensity)
        c.setdefault("bloom", bloom)
        c.setdefault("ms", ms)
        c["pose"] = clip(p)
        if flash:
            c["flash"] = flash(p)
        return c
    return {"name": name, "label": label, "note": note, "subject": sub, "frames": N,
            "scene": scene if scene is not None else
            cine.ground_quads() + cine.doorway(), "f": f, "seed": seed}


# ================================================================= DARK WALKER

def walker_shot(name, label, note, clip, cam, N=22, ms=100, scene=None, seed=51,
                intensity=0.34, tail=None, **fixed):
    sub = cine.creature_subject(tiers.DARK_WALKER)

    def f(i, p):
        if tail and i >= N - len(tail):
            kind, ms2 = tail[i - (N - len(tail))]
            return {"insert": kind, "ms": ms2, "ghost": 0.18}
        c = cam(p)
        c.setdefault("intensity", intensity)
        c.setdefault("ms", ms)
        for k, v in fixed.items():
            c.setdefault(k, v)
        c["pose"] = clip(p)
        return c
    return {"name": name, "label": label, "note": note, "subject": sub, "frames": N,
            "scene": scene if scene is not None else
            cine.road() + cine.treeline(17, count=22, near=10.0, far=90.0, road=5.2),
            "f": f, "seed": seed}


# ====================================================================== all of them

def every_shot():
    def L(name):
        return LC[f"animation.locust.{name}"]

    def W(name):
        return DW[f"animation.dark_walker.{name}"]

    def still_cam(d, h=1.62, ty=1.5, fov=70.0, shake=0.006, fog=40.0, **kw):
        def c(p):
            out = {"eye": (0.0, h, d), "target": (0.0, ty, 0.0), "fov": fov, "shake": shake,
                   "fog": fog}
            out.update(kw)
            return out
        return c

    def walker_approach():
        """Down the road. The lens tilts back to keep the brim in frame the whole way, and
        on the last two frames the headlight dies and only the eyes are left."""
        def c(p):
            k = ease_in(min(1.0, p / 0.88), 1.7)
            out_ = p > 0.88
            return {"eye": (lerp(0.0, 0.5, k), 1.62 + 0.05 * math.sin(p * 26), lerp(26.0, 3.4, k)),
                    "target": (0.0, lerp(4.0, 6.6, k), 0.0),
                    "fov": lerp(62.0, 88.0, k), "roll": math.sin(p * 8) * 2.4 * k,
                    "shake": 0.008 + 0.16 * k ** 2,
                    "intensity": 0.15 + 0.8 * k,
                    "bloom": 0.5 + 0.9 * k,
                    "lamp": 0.0 if out_ else 1.9, "lamp_reach": 10.0,
                    "fog": lerp(90.0, 150.0, k),
                    "ms": 150 if out_ else int(lerp(130, 52, k))}
        return c

    def grab_cam():
        """The lens closes as the arms do. Standing still for this would be a choice the
        player does not get to make."""
        def c(p):
            k = min(1.0, max(0.0, (p - 0.22) / 0.78)) ** 1.4
            return {"eye": (0.0, lerp(1.30, 1.16, k), lerp(2.7, 1.15, k)),
                    "target": (0.0, lerp(1.45, 1.52, k), 0.0),
                    "fov": lerp(78.0, 98.0, k), "roll": 3.0 * k,
                    "shake": 0.008 + 0.09 * k, "intensity": 0.34 + 0.56 * k,
                    "fog": 40.0, "ms": int(lerp(120, 60, k))}
        return c

    def run_cam(d0, d1, h=1.62, ty=1.4, fov0=72.0, fov1=94.0):
        def c(p):
            k = ease_in(p, 1.6)
            return {"eye": (lerp(0.0, 0.25, k), h + 0.04 * math.sin(p * 18), lerp(d0, d1, k)),
                    "target": (0.0, ty, 0.0), "fov": lerp(fov0, fov1, k),
                    "roll": math.sin(p * 11) * 2.6 * k,
                    "shake": 0.01 + 0.09 * k, "intensity": 0.3 + 0.65 * k,
                    "fog": 44.0, "ms": int(lerp(105, 48, k))}
        return c

    return [
        # ---- the Sun Man
        sunman_charge(),
        sunman_closer(),
        sunman_arch(),
        sunman_stare(),
        sunman_wide("dread_idle", "Dread idle", "state 0 · stillness, broken twice",
                    clip_fn(SM["animation.sun_man.idle"]), dist=80.0, ms=130),
        sunman_wide("wrong_walk", "Wrong walk", "state 1 · the body refuses the legs",
                    clip_fn(SM["animation.sun_man.walk"]), dist=70.0, ms=95),
        sunman_wide("harvest_rise", "Harvest", "state 4 · day thirty",
                    clip_fn(SM["animation.sun_man.harvest_rise"]), dist=86.0, ty=40.0, ms=100),
        # ---- the Locust
        locust_shot("locust_frozen", "Locust · frozen", L("head_snap").note,
                    # standing with its back to you; the clip turns the head round to you
                    lambda p: {**L("head_snap").at(p), "pelvis": {"rotation": (0.0, 164.0, 0.0)}},
                    still_cam(3.4, ty=1.30, fov=62.0),
                    N=14, ms=430, intensity=0.26),
        locust_shot("locust_scuttle", "Locust · scuttle", L("scuttle").note,
                    lambda p: L("scuttle").at(p * 3 % 1.0), run_cam(7.0, 1.30, ty=1.25),
                    N=26, scene=cine.ground_quads()
                    + cine.treeline(5, count=18, near=6.0, far=60.0, road=4.0),
                    tail=[("black", 300)], seed=29),
        locust_shot("locust_rear", "Locust · rear", L("rear").note,
                    clip_fn(L("rear")), still_cam(3.6, ty=1.45, fov=66.0, shake=0.02),
                    N=22, ms=95, flash=lambda p: 0.45 if 0.52 <= p < 0.60 else 0.0),
        locust_shot("locust_climb", "Locust · climb", L("climb").note,
                    clip_fn(L("climb")),
                    still_cam(2.7, h=0.42, ty=1.95, fov=76.0, roll=4.0),
                    N=20, ms=95, scene=cine.ground_quads() + cine.wall(), seed=23),
        # ---- the Dark Walker
        walker_shot("walker_road", "Dark Walker", W("walk").note,
                    lambda p: W("walk").at(p * 2 % 1.0), walker_approach(),
                    N=34, seed=53, tail=[("black", 300)]),
        walker_shot("walker_ridge", "Dark Walker · ridge", W("notice").note,
                    clip_fn(W("notice")),
                    still_cam(44.0, ty=4.6, fov=42.0, shake=0.004, fog=170.0),
                    N=18, ms=150, intensity=0.5, bloom=0.3, mono=True,
                    sky=((196, 194, 194), (138, 136, 139)),
                    scene=cine.ground_quads()
                    + cine.treeline(29, count=14, near=60.0, far=140.0, road=22.0),
                    seed=59),
        walker_shot("walker_loom", "Dark Walker · loom", W("loom").note,
                    clip_fn(W("loom")),
                    lambda p: {"eye": (5.4, 1.30, 5.0), "target": (0.0, 3.4, 0.0),
                               "fov": 82.0, "shake": 0.018, "fog": 60.0},
                    N=24, ms=105, intensity=0.42, bloom=0.9, lamp=1.5, lamp_reach=8.0,
                    seed=61),
        walker_shot("walker_reach", "Dark Walker · reach", W("attack").note,
                    clip_fn(W("attack")),
                    lambda p: {"eye": (0.7, 0.30, 2.9), "target": (0.0, 3.1, 0.0),
                               "fov": 94.0, "roll": 6.0, "shake": 0.028, "fog": 46.0},
                    N=20, ms=95, intensity=0.55, bloom=1.1, lamp=2.0, lamp_reach=6.0,
                    tail=[("black", 260)], seed=67),
    ]


if __name__ == "__main__":
    want = set(sys.argv[1:])
    OUT.mkdir(parents=True, exist_ok=True)
    for spec in every_shot():
        if want and spec["name"] not in want:
            continue
        render(spec)
