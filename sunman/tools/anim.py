"""Creepier animation set for the Sun Man.

What makes a 73-block thing frightening is not more motion, it is WRONG motion. Five devices
do the work here, and every clip is built out of them:

  stutter  motion quantised to a few steps, so the body jumps between poses like dropped frames
  lag      the neck and head trail the torso, as though the head is being dragged by the body
  asym     left and right desynchronised, so the walk never resolves into a clean cycle
  hold     long stretches of absolute stillness, broken by one violent frame
  overbend joints carried a few degrees past where a joint should stop

Angles are degrees. Phase is 0..1 over one loop.
"""
import math

TAU = math.tau


# ---------------------------------------------------------------- time shaping

def stutter(p, steps):
    """Quantise phase into `steps` holds — the dropped-frame look."""
    return math.floor(p * steps) / steps


def lag(p, amount):
    """Phase shifted back, for follow-through down a chain."""
    return (p - amount) % 1.0


def hold(p, until, power=3.0):
    """0 until `until`, then eases hard to 1. Stillness, then a snap."""
    if p < until:
        return 0.0
    t = (p - until) / max(1e-6, 1.0 - until)
    return t ** (1.0 / power)


def spike(p, at, width):
    """A single sharp pulse centred on `at`."""
    d = abs(((p - at + 0.5) % 1.0) - 0.5)
    if d > width:
        return 0.0
    return math.cos(d / width * math.pi * 0.5) ** 2


def sway(p, speed=1.0, off=0.0):
    return math.sin((p * speed + off) * TAU)


NECK = ["neck", "head"]
ARMS = [("left", ""), ("right", ""), ("left", "lower_"), ("right", "lower_")]


def _arm(p, side, pre, swing, bend, splay, sg):
    return {
        f"{side}_{pre}upper_arm": (swing, 0.0, sg * splay),
        f"{side}_{pre}forearm": (bend, 0.0, 0.0),
        f"{side}_{pre}hand": (bend * 0.5, 0.0, 0.0),
        f"{side}_{pre}fingers": (bend * 0.7, 0.0, 0.0),
    }


# ---------------------------------------------------------------- clips

def dread_idle(p):
    """Almost nothing happens. Twice a cycle the head snaps and freezes again.

    The stillness is the point: a creature that sways continuously reads as alive and
    therefore safe. This one is a statue that moves when you are not ready.
    """
    pose = {}
    s = sway(stutter(p, 8), 1.0)
    pose["pelvis"] = (0.0, 0.8 * s, 0.0)
    pose["torso"] = (0.9 + 0.5 * s, 0.0, 0.6 * sway(p, 0.5))
    pose["upper_torso"] = (0.6, 1.2 * sway(lag(p, 0.08), 1.0), 0.0)

    # two hard head snaps per loop, held
    snap = spike(p, 0.22, 0.045) + spike(p, 0.68, 0.035)
    pose["neck"] = (-3.0 * snap, 16.0 * snap - 2.0 * s, 1.5 * snap)
    pose["head"] = (4.0 * snap, 9.0 * snap, -2.0 * snap)

    # the four arms hang dead, each on its own slow clock
    for i, (side, pre) in enumerate(ARMS):
        sg = 1 if side == "left" else -1
        q = sway(lag(p, i * 0.11), 0.5)
        pose.update(_arm(p, side, pre, 1.6 * q, 2.4 + 1.2 * q, 2.0 + 0.8 * q, sg))
        # fingers twitch on their own, off the body's rhythm
        pose[f"{side}_{pre}fingers"] = (6.0 * spike(p, 0.1 + i * 0.23, 0.03), 0.0, 0.0)
    return pose


def wrong_walk(p):
    """A stilt walk that never resolves.

    The legs run a clean cycle; everything above the hips refuses to agree with it. The torso
    leans BACK into the stride instead of forward, the arms swing at half rate, and the head
    stays locked on you no matter what the body does.
    """
    pose = {}
    for side, off, hi in (("left", 0.0, 1.22), ("right", 0.5, 0.82)):
        a = (p + off) * TAU
        sw = math.sin(a)
        lift = max(0.0, math.cos(a)) * hi          # asymmetric: one leg drags
        pose[f"{side}_thigh"] = (24.0 * sw, 0.0, 0.0)
        pose[f"{side}_shin"] = (-30.0 * sw - 22.0 * lift, 0.0, 0.0)
        pose[f"{side}_foot"] = (14.0 * sw + 20.0 * lift, 0.0, 0.0)

    body = sway(p, 2.0)
    pose["pelvis"] = (0.0, 2.6 * sway(p), 1.4 * body)
    pose["torso"] = (-4.5 + 1.4 * body, 0.0, -1.6 * body)        # leaning BACK
    pose["upper_torso"] = (-2.5, 2.0 * sway(lag(p, 0.12), 2.0), 0.0)
    # the head counter-rotates to stay facing forward: it is watching you, not walking
    pose["neck"] = (2.0, -3.4 * sway(lag(p, 0.12), 2.0), 0.0)
    pose["head"] = (0.0, -2.0 * sway(lag(p, 0.2), 2.0), 0.0)

    for i, (side, pre) in enumerate(ARMS):
        sg = 1 if side == "left" else -1
        q = sway(lag(p, 0.3 + i * 0.07), 0.5)      # half rate, lagged, per-arm
        pose.update(_arm(p, side, pre, 9.0 * q, 7.0 + 5.0 * q, 3.0, sg))
    return pose


def lurch(p):
    """Three beats of nothing, then one violent frame.

    `hold` keeps the whole body at rest for 62% of the loop; the snap throws the torso forward,
    whips the neck past vertical and flings all four arms back behind it.
    """
    pose = {}
    k = hold(p, 0.62, 4.0)
    settle = max(0.0, (p - 0.86) / 0.14)
    f = k * (1.0 - settle * 0.55)

    pose["pelvis"] = (0.0, 0.0, 0.0)
    pose["torso"] = (34.0 * f, 0.0, 0.0)
    pose["upper_torso"] = (26.0 * f, 0.0, 0.0)
    pose["neck"] = (-46.0 * f, 0.0, 0.0)           # whips the other way: overbend
    pose["head"] = (-24.0 * f, 0.0, 0.0)

    for i, (side, pre) in enumerate(ARMS):
        sg = 1 if side == "left" else -1
        pose.update(_arm(p, side, pre, -72.0 * f, -18.0 * f, 14.0 * f + 2.0, sg))
    for side in ("left", "right"):
        pose[f"{side}_thigh"] = (-14.0 * f, 0.0, 0.0)
        pose[f"{side}_shin"] = (20.0 * f, 0.0, 0.0)
    return pose


def stare_down(p):
    """The neck lowers the face toward you over a full cycle, and stops.

    Nothing else on the body moves. The descent is stuttered into eight steps so it arrives in
    jerks rather than a smooth arc.
    """
    pose = {}
    t = stutter(min(1.0, p * 1.35), 8)
    pose["torso"] = (3.0 * t, 0.0, 0.0)
    pose["upper_torso"] = (9.0 * t, 0.0, 0.0)
    pose["neck"] = (58.0 * t, 4.0 * sway(p, 1.0) * (1 - t), 0.0)
    pose["head"] = (26.0 * t, 0.0, 0.0)

    for i, (side, pre) in enumerate(ARMS):
        sg = 1 if side == "left" else -1
        curl = 26.0 * t + 4.0 * spike(p, 0.5 + i * 0.1, 0.05)
        pose.update(_arm(p, side, pre, -6.0 * t, curl, 3.0, sg))
    return pose


def harvest_rise(p):
    """Day 30. Arms open, neck straightens, the whole thing gets taller."""
    pose = {}
    t = min(1.0, p * 1.2)
    e = t * t * (3 - 2 * t)
    pose["pelvis"] = (0.0, 0.0, 0.0)
    pose["torso"] = (-7.0 * e, 0.0, 0.0)
    pose["upper_torso"] = (-9.0 * e, 0.0, 0.0)
    pose["neck"] = (-14.0 * e, 0.0, 0.0)
    pose["head"] = (-8.0 * e + 2.0 * sway(p, 2.0), 0.0, 0.0)
    for i, (side, pre) in enumerate(ARMS):
        sg = 1 if side == "left" else -1
        tier = 1.0 - i * 0.12
        pose.update(_arm(p, side, pre,
                         -52.0 * e * tier, -12.0 * e, (36.0 + i * 10.0) * e, sg))
    return pose


CLIPS = {
    "dread_idle": (dread_idle, "Dread idle", "stillness, broken twice by a head snap"),
    "wrong_walk": (wrong_walk, "Wrong walk", "legs walk, the body refuses to agree"),
    "lurch": (lurch, "Lurch", "three beats of nothing, then one violent frame"),
    "stare_down": (stare_down, "Stare down", "the face descends toward you in jerks"),
    "harvest_rise": (harvest_rise, "Harvest rise", "day thirty, arms opening"),
}


def sprint(p):
    """State 2 (inside 55 blocks): it runs. This is the clip the charge shot is built on.

    Nothing about it is a run cycle. Three things are deliberately wrong:

      * the HEAD never moves. Not a bob, not a tilt, not a degree of counter-rotation —
        it holds a fixed point in space while the body sprints underneath it. A running
        animal's head bobs; this one is being carried like a held camera.
      * the stride is uneven and skips. The left leg takes 1.3x the stride of the right,
        and `stutter` drops the phase so one step per cycle lands early, as if a frame
        went missing between two footfalls.
      * the arms do not swing in opposition. All four trail behind, dead, and only the
        fingers move — they claw at the air ahead of it on their own clock.
    """
    pose = {}
    step = p * 2.0 % 1.0                       # two strides per loop
    for side, off, reach in (("left", 0.0, 1.30), ("right", 0.5, 0.86)):
        a = (stutter(step + off, 12)) * TAU
        sw = math.sin(a)
        lift = max(0.0, math.cos(a))
        pose[f"{side}_thigh"] = (46.0 * sw * reach, 0.0, 0.0)
        pose[f"{side}_shin"] = (-52.0 * sw - 30.0 * lift, 0.0, 0.0)
        pose[f"{side}_foot"] = (18.0 * sw + 26.0 * lift, 0.0, 0.0)

    # the torso drives forward but does not rise and fall with the stride
    pose["pelvis"] = (0.0, 3.0 * sway(step), 0.0)
    pose["torso"] = (16.0, 0.0, 1.2 * sway(step, 2.0))
    pose["upper_torso"] = (9.0, 2.4 * sway(lag(step, 0.1), 2.0), 0.0)
    # and the neck cancels every bit of it, so the head is a fixed point
    pose["neck"] = (-25.0, -2.4 * sway(lag(step, 0.1), 2.0), 0.0)
    pose["head"] = (0.0, 0.0, 0.0)

    for i, (side, pre) in enumerate(ARMS):
        sg = 1 if side == "left" else -1
        drag = 6.0 + 4.0 * sway(lag(step, 0.25 + i * 0.06), 1.0)
        pose.update(_arm(p, side, pre, 22.0 + drag, -14.0, 4.0 + i * 1.5, sg))
        pose[f"{side}_{pre}fingers"] = (-44.0 + 30.0 * spike(step, i * 0.25, 0.12), 0.0, 0.0)
    return pose


def still(p):
    """Absolutely nothing. For the shot where only the distance changes."""
    return {"torso": (1.2, 0.0, 0.0), "neck": (-1.0, 0.0, 0.0)}


CLIPS["sprint"] = (sprint, "Sprint", "the head holds still while the body runs")
