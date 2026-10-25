"""The Dark Walker's clips, as Blockbench keyframes.

"It does not hurry, because it does not need to."

Everything here is keyed the way an animator keys a mob in Blockbench: a handful of poses
per clip, Catmull-Rom between them, a step key where something has to happen in no time at
all. Values are DELTAS on the rest pose (see tiers.py): the rig already stands stooped with
its arms fanned, so `idle` only has to breathe.

Rig reminders (right-handed, +X = its left, +Z = forward):
  thigh  -X swings the leg forward       shin  +X bends the knee
  torso  +X folds it forward             head  +X nods down, +Y turns to its left,
  arms   -X reaches forward, +Z (left) / -Z (right) lifts the arm out to the side

The old clips' ideas are kept — the brim that never tips, six arms on six clocks, the hinge
at the hips — but they are no longer faked with quantised time. A creature that stutters
reads as a glitch; one that moves with weight and then does one thing too fast reads as
alive, which is worse.
"""
import math

import tiers
from rig import quat_rotate  # noqa: F401
from gait import Leg, key_gait
from keyframes import LINEAR, Clip, periodic, px

C = tiers.DARK_WALKER
N = "animation.dark_walker"
TENDRILS = [(n, side, 1 if side == "l" else -1) for n in (1, 2, 3) for side in ("l", "r")]
TAU = math.tau


def cos(p):
    return math.cos(p * TAU)


def sin(p):
    return math.sin(p * TAU)


# ====================================================================== idle

def idle():
    """It stands at the end of the road. It breathes — slowly, in, in, and out short — and
    the six arms drift on six different clocks, so they never agree. Once a loop the head
    tips over to one side, quicker than anything else it does, and stays there, looking."""
    c = Clip(f"{N}.idle", 4.0, "loop", "breathing, six arms on six clocks, one head tilt")
    c.keys("torso", "rotation", [(0, (0, 0, 0)), (1.4, (1.6, 0, -0.4)), (2.0, (0.2, 0, 0)),
                                 (3.4, (1.6, 0, 0.4)), (4.0, (0, 0, 0))])
    c.keys("neck", "rotation", [(0, (0, 0, 0)), (1.4, (-1.1, 0, 0)), (2.0, (-0.1, 0, 0)),
                                (3.4, (-1.1, 0, 0)), (4.0, (0, 0, 0))])
    periodic(c, "pelvis", "rotation", lambda p: (0, 0.6 * sin(p), 1.0 * sin(p)))
    periodic(c, "leg_l", "rotation", lambda p: (0, 0, -1.0 * sin(p)))
    periodic(c, "leg_r", "rotation", lambda p: (0, 0, -1.0 * sin(p)))
    # the tilt: 0.25 s in, a little overshoot, a long look, and a slow way back
    c.keys("head", "rotation", [
        (0.0, (0, 0, 0)), (1.0, (0, 0, 0)),
        (1.25, (-3, 8, 12.5)), (1.4, (-3, 8, 11)),
        (2.7, (-3.5, 9, 11.5)), (3.3, (0, 0, 0)), (4.0, (0, 0, 0))])
    c.keys("hat", "rotation", [
        (0.0, (0, 0, 0)), (1.1, (0, 0, 0)), (1.35, (0, 0, -3)), (1.6, (0, 0, 1)),
        (1.9, (0, 0, 0)), (3.0, (0, 0, 0)), (3.4, (0.5, 0, 1.5)), (3.8, (0, 0, 0)),
        (4.0, (0, 0, 0))])
    for i, (n, side, sg) in enumerate(TENDRILS):
        o = i / 6.0
        periodic(c, f"arm_{side}{n}", "rotation",
                 lambda p, o=o, sg=sg: (1.6 * sin(p + o), 0, sg * 1.8 * sin(p + o + 0.25)))
        periodic(c, f"fore_{side}{n}", "rotation",
                 lambda p, o=o, sg=sg: (2.6 * sin(p + o - 0.12), 0, -sg * 1.2 * sin(p + o)))
    return c


# ====================================================================== walk

LEGS = [Leg(C, "leg_l", "shin_l", 0.0), Leg(C, "leg_r", "shin_r", 0.5)]


def _hips(c, yaw, roll):
    c.cycle("pelvis", "rotation", [(0, y, z) for y, z in zip(yaw, roll)])


def walk():
    """The stride. Slow and enormous — 1.2 s a step — with the knees giving on every
    contact, the way the road frames show them giving. The hips swing and roll under it;
    the torso turns against them; the neck cancels whatever is left, so the head is carried
    dead level and the brim never tips a degree. The six arms swing against the legs and
    each tier is a beat behind the one above, so every step sends a wave down them."""
    c = Clip(f"{N}.walk", 2.4, "loop", "the brim never tips; a wave runs down the arms")
    yaw = [-4, -3, 0, 3, 4, 3, 0, -3]
    roll = [0, 1.6, 2, 1, 0, -1.6, -2, -1]
    # 2.5-block strides at 1.7 blocks a second; the foot is planted 62% of the cycle
    key_gait(c, LEGS, stride=40.0, duty=0.62, lift=6.0, drop=2.5,
             bob=lambda s: -1.0 * math.cos(4 * math.pi * (s - 0.08)))
    _hips(c, yaw, roll)
    dip = [0, 0.8, 0, -0.4] * 2
    c.cycle("torso", "rotation", [(4 + d, -0.7 * y, -0.8 * r) for d, y, r in zip(dip, yaw, roll)])
    c.cycle("neck", "rotation", [(-4 - d, -0.3 * y, -0.2 * r) for d, y, r in zip(dip, yaw, roll)])
    periodic(c, "hat", "rotation", lambda p: (0.8 * sin(2 * p - 0.1), 0, 0))
    for n, amp, lag in ((1, 10.0, 0.0), (2, 8.0, 0.06), (3, 6.5, 0.12)):
        for side, sg in (("l", 1), ("r", -1)):
            periodic(c, f"arm_{side}{n}", "rotation",
                     lambda p, a=amp, l=lag, sg=sg: (-4 + sg * a * cos(p - l), 0,
                                                     sg * 1.5 * sin(2 * p - l)))
            periodic(c, f"fore_{side}{n}", "rotation",
                     lambda p, a=amp, l=lag, sg=sg: (-5 + sg * 0.7 * a * cos(p - l - 0.1), 0, 0))
    return c


# ====================================================================== chase

def chase():
    """When it does hurry. A long, low lope with the body pitched over its legs and the
    arms streaming behind it — and the head still level, still aimed. The brim finally
    bounces: this is the only clip where it is in a hurry."""
    c = Clip(f"{N}.chase", 1.2, "loop", "a long low lope; the head still aimed at you")
    yaw = [-6, -4, 0, 4, 6, 4, 0, -4]
    roll = [0, 2, 3, 1, 0, -2, -3, -1]
    # 6 blocks a second: each foot is down for 42% of the cycle, so there is a moment in
    # every stride when nothing of it is touching the road
    key_gait(c, LEGS, stride=50.0, duty=0.42, lift=15.0, drop=5.0, n=16,
             bob=lambda s: -2.2 * math.cos(4 * math.pi * (s - 0.06)))
    _hips(c, yaw, roll)
    dip = [0, 1.5, 0, -1.0] * 2
    c.cycle("torso", "rotation", [(22 + d, -0.6 * y, -0.6 * r) for d, y, r in zip(dip, yaw, roll)])
    c.cycle("neck", "rotation", [(-14 - d, -0.4 * y, -0.4 * r) for d, y, r in zip(dip, yaw, roll)])
    c.cycle("head", "rotation", [(-8, 0, 0)] * 8)
    periodic(c, "hat", "rotation", lambda p: (2.5 * sin(2 * p - 0.15), 0, 1.0 * sin(p)))
    for n, amp, lag in ((1, 14.0, 0.0), (2, 12.0, 0.08), (3, 10.0, 0.16)):
        for side, sg in (("l", 1), ("r", -1)):
            periodic(c, f"arm_{side}{n}", "rotation",
                     lambda p, a=amp, l=lag, sg=sg: (34 + sg * a * cos(p - l), 0,
                                                     sg * (6 + 4 * sin(2 * p - l))))
            periodic(c, f"fore_{side}{n}", "rotation",
                     lambda p, a=amp, l=lag, sg=sg: (-18 + sg * 10 * cos(p - l - 0.12), 0, 0))
    return c


# ====================================================================== notice

def notice():
    """It is looking at something off to its right. Then, slowly, it is not: the head comes
    round, a long way, and the last few degrees happen all at once. The body straightens.
    The hands open. It holds."""
    c = Clip(f"{N}.notice", 2.6, "hold", "the head comes round; the last degrees all at once")
    c.keys("head", "rotation", [
        (0.0, (0, -38, 0)), (0.35, (0, -38, 0)),
        (1.35, (-2, -9, 2)),                                  # most of the way, slowly
        (1.45, (-4, 3, 9), LINEAR), (1.6, (-3, 0, 8)),        # the snap, and it overshoots
        (2.6, (-3, 0, 8))])
    c.keys("neck", "rotation", [(0.0, (0, -14, 0)), (0.4, (0, -14, 0)), (1.4, (0, -2, 0)),
                                (1.6, (-1, 0, 0)), (2.6, (-1, 0, 0))])
    c.keys("torso", "rotation", [(0.0, (0, 0, 0)), (1.3, (0, 0, 0)), (1.7, (-4, 0, 0)),
                                 (2.6, (-4, 0, 0))])
    c.keys("hat", "rotation", [(0.0, (0, 0, 0)), (1.4, (0, 0, 0)), (1.55, (0, 0, -3)),
                               (1.85, (0, 0, 1)), (2.2, (0, 0, 0)), (2.6, (0, 0, 0))])
    for i, (n, side, sg) in enumerate(TENDRILS):
        d = 0.04 * i
        c.keys(f"arm_{side}{n}", "rotation", [
            (0.0, (0, 0, 0)), (1.45 + d, (0, 0, 0)),
            (1.75 + d, (-6, 0, sg * 5)), (2.6, (-5, 0, sg * 4))])
        c.keys(f"fore_{side}{n}", "rotation", [
            (0.0, (0, 0, 0)), (1.5 + d, (0, 0, 0)),
            (1.85 + d, (-14, 0, -sg * 4)), (2.6, (-12, 0, -sg * 3))])
    return c


# ====================================================================== loom

def loom():
    """It folds down to your height. Nothing this tall should be able to reach you without
    kneeling, and it does not kneel — it hinges at the hips, the hips go back, the arms open
    round you, and the brim tips forward over the eyes on the way down, so the last thing
    you see lit goes out."""
    c = Clip(f"{N}.loom", 3.0, "hold", "it hinges at the hips; it does not kneel")
    c.keys("pelvis", "position", [(0.0, (0, 0, 0)), (0.4, (0, px(0.6), 0)),
                                  (2.0, (0, px(-3), px(-4))), (3.0, (0, px(-3.2), px(-4.4)))])
    c.keys("torso", "rotation", [(0.0, (0, 0, 0)), (0.4, (-4, 0, 0)), (1.9, (68, 0, 0)),
                                 (2.2, (64, 0, 0)), (3.0, (66, 0, 0))])
    c.keys("neck", "rotation", [(0.0, (0, 0, 0)), (0.4, (2, 0, 0)), (1.9, (-34, 0, 0)),
                                (2.3, (-30, 0, 0)), (3.0, (-31, 0, 0))])
    c.keys("head", "rotation", [(0.0, (0, 0, 0)), (0.5, (0, 0, 0)), (2.0, (-22, 0, 4)),
                                (2.4, (-20, 0, 6)), (3.0, (-20, 0, 6))])
    c.keys("hat", "rotation", [(0.0, (0, 0, 0)), (0.6, (0, 0, 0)), (2.1, (14, 0, 0)),
                               (2.5, (11, 0, 0)), (3.0, (12, 0, 0))])
    for side, sg in (("l", 1), ("r", -1)):
        c.keys(f"leg_{side}", "rotation", [(0.0, (0, 0, 0)), (2.0, (12, 0, sg * 2)),
                                           (3.0, (12, 0, sg * 2))])
        c.keys(f"shin_{side}", "rotation", [(0.0, (0, 0, 0)), (2.0, (-4, 0, 0)),
                                            (3.0, (-4, 0, 0))])
    for i, (n, side, sg) in enumerate(TENDRILS):
        d = 0.06 * i
        open_ = (26.0, 34.0, 42.0)[n - 1]
        c.keys(f"arm_{side}{n}", "rotation", [
            (0.0, (0, 0, 0)), (0.5 + d, (2, 0, sg * 5)),
            (2.0 + d, (-112, 0, sg * open_)), (2.4 + d, (-106, 0, sg * (open_ - 4))),
            (3.0, (-109, 0, sg * (open_ - 2)))])
        c.keys(f"fore_{side}{n}", "rotation", [
            (0.0, (0, 0, 0)), (0.7 + d, (0, 0, 0)),
            (2.1 + d, (-34, 0, -sg * 26)), (3.0, (-30, 0, -sg * 24))])
    return c


# ====================================================================== attack

def attack():
    """The reach. It draws everything back — the body rears, six arms cock behind it — then
    throws them, but not together: each arm leads the next by a twentieth of a second, so
    they arrive as a wave rather than a gesture. The hands close on the far side of you."""
    c = Clip(f"{N}.attack", 1.6, "once", "wind-up, then six arms arriving as a wave")
    c.keys("torso", "rotation", [(0.0, (0, 0, 0)), (0.45, (-12, 0, 0)), (0.62, (34, 0, 0)),
                                 (0.8, (30, 0, 0)), (1.6, (0, 0, 0))])
    c.keys("neck", "rotation", [(0.0, (0, 0, 0)), (0.45, (6, 0, 0)), (0.62, (-20, 0, 0)),
                                (0.8, (-18, 0, 0)), (1.6, (0, 0, 0))])
    c.keys("head", "rotation", [(0.0, (0, 0, 0)), (0.45, (4, 0, -4)), (0.62, (-10, 0, 0)),
                                (1.0, (-8, 0, 2)), (1.6, (0, 0, 0))])
    c.keys("hat", "rotation", [(0.0, (0, 0, 0)), (0.5, (-3, 0, 0)), (0.66, (5, 0, 0)),
                               (0.85, (-2, 0, 0)), (1.1, (1, 0, 0)), (1.6, (0, 0, 0))])
    c.keys("pelvis", "position", [(0.0, (0, 0, 0)), (0.45, (0, px(0.8), px(-1.5))),
                                  (0.65, (0, px(-1.6), px(3))), (1.6, (0, 0, 0))])
    for side, sg in (("l", 1), ("r", -1)):
        lead = -1 if side == "l" else 1
        c.keys(f"leg_{side}", "rotation", [(0.0, (0, 0, 0)), (0.45, (lead * 4, 0, 0)),
                                           (0.65, (lead * -10, 0, 0)), (1.6, (0, 0, 0))])
        c.keys(f"shin_{side}", "rotation", [(0.0, (0, 0, 0)), (0.65, (10, 0, 0)),
                                            (1.6, (0, 0, 0))])
    for i, (n, side, sg) in enumerate(TENDRILS):
        d = 0.05 * i
        c.keys(f"arm_{side}{n}", "rotation", [
            (0.0, (0, 0, 0)),
            (0.42, (32, 0, sg * 16)),                       # cocked behind it
            (0.6 + d, (-96, 0, -sg * 6)),                   # thrown, each a beat late
            (0.72 + d, (-104, 0, -sg * 10)),                # carried past
            (1.0 + d, (-80, 0, -sg * 4)),
            (1.6, (0, 0, 0))])
        c.keys(f"fore_{side}{n}", "rotation", [
            (0.0, (0, 0, 0)),
            (0.42, (-34, 0, 0)),
            (0.6 + d, (6, 0, 0)),                           # flung straight
            (0.76 + d, (-46, 0, -sg * 10)),                 # and closing
            (1.6, (0, 0, 0))])
    return c


# ====================================================================== death

def death():
    """Struck, it is thrown back; the knees go; it folds; and seven blocks of it go over
    sideways like something felled, the arms arriving after the body does."""
    c = Clip(f"{N}.death", 2.6, "hold", "thrown back, the knees go, it goes over sideways")
    c.keys("torso", "rotation", [(0.0, (0, 0, 0)), (0.2, (-14, 0, 0)), (0.8, (26, 0, -6)),
                                 (1.6, (30, 0, -10)), (1.85, (24, 0, -8)), (2.6, (26, 0, -8))])
    c.keys("neck", "rotation", [(0.0, (0, 0, 0)), (0.2, (-10, 0, 0)), (0.9, (18, 0, 6)),
                                (1.7, (14, 0, 10)), (1.95, (22, 0, 12)), (2.6, (20, 0, 12))])
    c.keys("head", "rotation", [(0.0, (0, 0, 0)), (0.15, (-16, 6, 0)), (0.9, (14, 0, 10)),
                                (1.7, (8, 0, 14)), (2.0, (16, 4, 20)), (2.6, (16, 4, 20))])
    c.keys("hat", "rotation", [(0.0, (0, 0, 0)), (0.2, (-8, 0, 0)), (0.9, (10, 0, 0)),
                               (1.7, (14, 0, -6)), (2.0, (22, 0, -10)), (2.6, (22, 0, -10))])
    for side, sg in (("l", 1), ("r", -1)):
        c.keys(f"leg_{side}", "rotation", [(0.0, (0, 0, 0)), (0.25, (4, 0, 0)),
                                           (0.9, (-38, 0, sg * 4)), (2.6, (-40, 0, sg * 6))])
        c.keys(f"shin_{side}", "rotation", [(0.0, (0, 0, 0)), (0.25, (2, 0, 0)),
                                            (0.9, (62, 0, 0)), (2.6, (64, 0, 0))])
    for i, (n, side, sg) in enumerate(TENDRILS):
        d = 0.04 * i
        late = 0.12 + 0.03 * n
        if side == "l":          # it falls to its left: these end up underneath, sprawled
            land, settle = (-(95 - 20 * n), 0, 10), (-(88 - 20 * n), 0, 8)
        else:                    # these are on top, and flop over the body to the ground
            land, settle = (-(40 - 10 * n), 0, 78), (-(36 - 10 * n), 0, 72)
        c.keys(f"arm_{side}{n}", "rotation", [
            (0.0, (0, 0, 0)), (0.2 + d, (-30, 0, sg * 30)),            # flung up
            (0.9 + d, (6, 0, sg * 8)),
            (1.6 + late, land), (1.85 + late, settle), (2.6, settle)])
        c.keys(f"fore_{side}{n}", "rotation", [
            (0.0, (0, 0, 0)), (0.25 + d, (-20, 0, 0)), (1.0 + d, (0, 0, 0)),
            (1.7 + late, (-30, 0, 0)), (1.95 + late, (-18, 0, 0)), (2.6, (-22, 0, 0))])
    # the fall: pelvis roll eases in like gravity, with the drop solved against the ground
    _topple(c, [(0.0, 0.0), (0.25, 0.0), (0.9, 6.0), (1.25, 30.0), (1.6, 86.0),
                (1.85, 80.0), (2.1, 84.0), (2.6, 83.0)])
    return c


def _feet_x(pose):
    sol = C.solve(pose)
    xs = []
    for side in ("l", "r"):
        pos, q = sol[f"shin_{side}"]
        foot = quat_rotate(q, (0.0, -C.J["shin_" + side][1], 0.0))
        xs.append(pos[0] + foot[0])
    return sum(xs) / 2.0


def _topple(c, roll_keys):
    """Key the pelvis roll, and key its position so the feet stay where they stood and the
    lowest point of the body rests on the ground at every roll key — the drop and the slide
    come out of the rig's own FK instead of being guessed."""
    for t, roll in roll_keys:
        c.key("pelvis", "rotation", t, (0, 0, -roll))
    base_lo = C.extents({})[0]
    base_fx = _feet_x({})
    for t, _roll in roll_keys:
        pose = c.sample(t)
        pose.setdefault("pelvis", {})["position"] = (0.0, 0.0, 0.0)
        dx = base_fx - _feet_x(pose)
        pose["pelvis"]["position"] = (dx, 0.0, 0.0)
        lo = C.extents(pose)[0]
        c.key("pelvis", "position", t, (dx, base_lo - lo, 0.0))


CLIPS = {c.name: c for c in (idle(), walk(), chase(), notice(), loom(), attack(), death())}


if __name__ == "__main__":
    for clip in CLIPS.values():
        print(clip.summary())
