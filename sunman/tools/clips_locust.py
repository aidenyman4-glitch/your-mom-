"""The Locust's clips, as Blockbench keyframes.

"It doesn't see you... but it knows you're there."

It spawns NoAI and frozen, and the stillness is most of the horror — so most of what is
here is about how little it moves and how suddenly. Smooth keys for everything it does on
purpose; STEP keys for the things that should not have frames in between (the head coming
round, the twitches), because easing would turn them into an animal turning to look.

Rig reminders (right-handed, +X = its left, +Z = forward):
  thigh -X forward, shin +X bends the knee, torso +X hunches, head +X nods down,
  head +Y turns to its left, arms -X reach forward, +Z/-Z lifts left/right arm outward
"""
import math

import tiers
from gait import Leg, key_gait
from keyframes import CATMULLROM, STEP, Clip, periodic, px

C = tiers.LOCUST
N = "animation.locust"
TAU = math.tau
LEGS = [Leg(C, "leg_l", "shin_l", 0.0), Leg(C, "leg_r", "shin_r", 0.5)]
SIDES = (("l", 1), ("r", -1))


def sin(p):
    return math.sin(p * TAU)


def cos(p):
    return math.cos(p * TAU)


def _twitch(c, bone, t, delta, hold=0.1):
    """A twitch with no frames in it: rest, then `delta` the next instant, then rest."""
    c.key(bone, "rotation", t - 0.05, (0, 0, 0), STEP)
    c.key(bone, "rotation", t, delta, STEP)
    c.key(bone, "rotation", t + hold, (0, 0, 0), STEP)


# ====================================================================== frozen

def frozen():
    """It does not move. Almost: a finger, then nothing for a long time, then the head by a
    degree and a half — and back, with nothing in between either way."""
    c = Clip(f"{N}.frozen", 6.0, "loop", "it does not move. almost")
    for bone in ("head", "fore_l", "fore_r", "torso"):
        c.key(bone, "rotation", 0.0, (0, 0, 0), STEP)
        c.key(bone, "rotation", 6.0, (0, 0, 0), STEP)
    _twitch(c, "fore_l", 1.3, (-7, 0, 0), 0.1)
    _twitch(c, "head", 3.85, (1.5, -2, 1.5), 0.6)
    _twitch(c, "fore_r", 4.9, (-5, 0, 2), 0.05)
    _twitch(c, "torso", 5.4, (0.8, 0, 0), 0.1)
    return c


# ====================================================================== head snap

def head_snap():
    """Standing with its back to you, and then — between two frames — its head is facing
    you. 171 degrees, and nothing else on it has moved. Then one twitch, and it holds."""
    c = Clip(f"{N}.head_snap", 2.4, "hold", "between two frames its head is facing you")
    c.keys("head", "rotation", [
        (0.0, (0, 0, 0), STEP), (0.95, (0, 0, 0), STEP),
        (1.0, (-6, -171, 4), STEP),                       # no frames in between
        (1.75, (-6, -171, 4), STEP), (1.8, (-10, -168, 10), STEP),   # the twitch
        (1.9, (-8, -169, 8), CATMULLROM), (2.4, (-8, -169, 8))])
    c.keys("torso", "rotation", [(0.0, (0, 0, 0), STEP), (1.0, (0, 0, 0), STEP),
                                 (1.05, (1.5, 0, 0), STEP), (1.25, (0, 0, 0)), (2.4, (0, 0, 0))])
    c.keys("fore_l", "rotation", [(0.0, (0, 0, 0), STEP), (1.8, (0, 0, 0), STEP),
                                  (1.85, (-9, 0, 0), STEP), (2.0, (-4, 0, 0)), (2.4, (-4, 0, 0))])
    return c


# ====================================================================== twitch

def twitch():
    """The idle it drops into once you are inside 22 blocks: a slow weave of the head and
    body, broken by jerks — head, a hand, the shoulders — on no rhythm at all."""
    c = Clip(f"{N}.twitch", 3.0, "loop", "a slow weave, broken by jerks on no rhythm")
    periodic(c, "torso", "rotation", lambda p: (1.2 * sin(p), 2.0 * sin(p + 0.2), 1.0 * sin(2 * p)))
    c.keys("head", "rotation", [
        (0.0, (0, 0, 0)), (0.5, (2, 6, 3)), (0.55, (6, 14, -6), STEP), (0.65, (3, 9, -2)),
        (1.3, (-2, -4, 2)), (1.9, (1, -8, 4)), (1.95, (-6, -18, 10), STEP), (2.05, (-2, -10, 6)),
        (2.4, (0, -2, 0)), (2.7, (2, 2, 3), STEP), (2.75, (0, 0, 0)), (3.0, (0, 0, 0))])
    for side, sg in SIDES:
        c.keys(f"arm_{side}", "rotation", [
            (0.0, (0, 0, 0)), (1.0, (-3, 0, sg * 2)),
            (1.15 if side == "l" else 2.2, (-12, 0, sg * 8), STEP),
            (1.25 if side == "l" else 2.3, (-4, 0, sg * 3)), (3.0, (0, 0, 0))])
        c.keys(f"fore_{side}", "rotation", [
            (0.0, (0, 0, 0)), (0.8, (-4, 0, 0)), (0.85 if side == "l" else 1.45, (-24, 0, -sg * 6), STEP),
            (0.95 if side == "l" else 1.55, (-8, 0, 0)), (3.0, (0, 0, 0))])
    return c


# ====================================================================== stalk

def stalk():
    """It walks the way nothing walks: the legs keep a clean stride, the arms swing on a
    different count — three swings to the legs' two strides — so the two never agree, and
    the head stays tilted, level and aimed."""
    c = Clip(f"{N}.stalk", 3.2, "loop", "the arms swing three to the legs' two")
    key_gait(c, LEGS, stride=11.0, duty=0.6, lift=3.0, drop=1.0, cycles=2,
             bob=lambda s: -0.5 * math.cos(4 * math.pi * (s - 0.06)), ppb=16.0)
    periodic(c, "torso", "rotation", lambda p: (5 + 0.8 * cos(4 * p), 4 * sin(2 * p), 1.5 * sin(2 * p)), n=16)
    periodic(c, "head", "rotation", lambda p: (-5 - 0.8 * cos(4 * p), -4.5 * sin(2 * p), -1.2 * sin(2 * p)), n=16)
    for side, sg in SIDES:
        off = 0.0 if side == "l" else 0.5
        periodic(c, f"arm_{side}", "rotation",
                 lambda p, o=off, sg=sg: (-14 * sin(3 * p + o), 0, sg * (3 + 2 * sin(6 * p + o))), n=18)
        periodic(c, f"fore_{side}", "rotation",
                 lambda p, o=off: (-6 - 12 * sin(3 * p + o - 0.12), 0, 0), n=18)
    return c


# ====================================================================== scuttle

def scuttle():
    """Inside 9 blocks, at a sprint: low, the body flat over the legs, the face held level
    and aimed — and the arms reaching AHEAD of it, clawing, not swinging."""
    c = Clip(f"{N}.scuttle", 0.8, "loop", "low and fast, the arms reaching ahead, clawing")
    key_gait(c, LEGS, stride=20.0, duty=0.4, lift=6.0, drop=3.0, n=16,
             bob=lambda s: -1.0 * math.cos(4 * math.pi * (s - 0.05)), ppb=16.0)
    periodic(c, "torso", "rotation", lambda p: (40 + 2 * cos(2 * p), 5 * sin(p), 0))
    periodic(c, "head", "rotation", lambda p: (-42 - 2 * cos(2 * p), -5 * sin(p), 0))
    for side, sg in SIDES:
        off = 0.0 if side == "l" else 0.5
        periodic(c, f"arm_{side}", "rotation",
                 lambda p, o=off, sg=sg: (-96 + 22 * sin(p + o), 0, sg * 10))
        periodic(c, f"fore_{side}", "rotation",
                 lambda p, o=off: (-22 + 30 * sin(p + o - 0.15), 0, 0))
    return c


# ====================================================================== rear

def rear():
    """The wake-up. It sinks — and then it is already up: rearing back, arms flung high,
    the hands open, the head tipped back and shuddering. Waking is one-way: it holds."""
    c = Clip(f"{N}.rear", 1.6, "hold", "it sinks, and then it is already up")
    c.keys("pelvis", "position", [(0.0, (0, 0, 0)), (0.45, (0, px(-2), 0)), (0.62, (0, px(1.5), 0)),
                                  (0.8, (0, px(0.8), 0)), (1.6, (0, px(1), 0))])
    c.keys("torso", "rotation", [(0.0, (0, 0, 0)), (0.45, (12, 0, 0)), (0.62, (-36, 0, 0)),
                                 (0.8, (-30, 0, 0)), (1.6, (-32, 0, 0))])
    c.keys("head", "rotation", [(0.0, (0, 0, 0)), (0.45, (8, 0, 0)), (0.62, (-20, 0, 0)),
                                (0.85, (-14, 6, 4)), (0.9, (-18, -6, -4), STEP),
                                (0.95, (-14, 4, 2), STEP), (1.0, (-17, -3, -2), STEP),
                                (1.05, (-15, 0, 0)), (1.6, (-15, 0, 0))])
    for side, sg in SIDES:
        c.keys(f"arm_{side}", "rotation", [(0.0, (0, 0, 0)), (0.45, (10, 0, sg * 4)),
                                           (0.62, (-118, 0, sg * 34)), (0.8, (-110, 0, sg * 30)),
                                           (1.6, (-112, 0, sg * 32))])
        c.keys(f"fore_{side}", "rotation", [(0.0, (0, 0, 0)), (0.45, (-20, 0, 0)),
                                            (0.66, (10, 0, sg * 6)), (0.85, (-30, 0, 0)),
                                            (1.6, (-26, 0, 0))])
        c.keys(f"leg_{side}", "rotation", [(0.0, (0, 0, 0)), (0.45, (-12, 0, 0)),
                                           (0.62, (14, 0, 0)), (1.6, (12, 0, 0))])
        c.keys(f"shin_{side}", "rotation", [(0.0, (0, 0, 0)), (0.45, (22, 0, 0)),
                                            (0.62, (-8, 0, 0)), (1.6, (-6, 0, 0))])
    return c


# ====================================================================== climb

def climb():
    """Up a wall, facing it, the way a person climbs — diagonal pairs of limbs reaching in
    turn — except that its head has turned all the way round, and is looking back down the
    wall at the floor. At you."""
    c = Clip(f"{N}.climb", 1.6, "loop", "facing the wall; its head turned round to the floor")
    periodic(c, "torso", "rotation", lambda p: (6 + 2 * sin(2 * p), 5 * sin(p), 3 * sin(p)))
    periodic(c, "pelvis", "position", lambda p: (0, px(0.8 * sin(2 * p - 0.1)), px(1.0)))
    periodic(c, "pelvis", "rotation", lambda p: (0, -4 * sin(p), -2 * sin(p)))
    # the head ignores all of it: turned round, nodding down, and held on the floor
    periodic(c, "head", "rotation", lambda p: (34 - 2 * sin(2 * p), 176 - 5 * sin(p), -6 - 3 * sin(p)))
    for side, sg in SIDES:
        off = 0.0 if side == "l" else 0.5
        # a reach: up and out while the hand travels, pulled down while it grips
        periodic(c, f"arm_{side}", "rotation",
                 lambda p, o=off, sg=sg: (-160 + 22 * sin(p + o), 0, sg * (16 + 8 * cos(p + o))), n=10)
        periodic(c, f"fore_{side}", "rotation",
                 lambda p, o=off: (-12 - 26 * max(0.0, sin(p + o + 0.25)), 0, 0), n=10)
        # the opposite leg steps with it
        periodic(c, f"leg_{side}", "rotation",
                 lambda p, o=off, sg=sg: (-46 - 26 * sin(p + o + 0.5), 0, sg * 14), n=10)
        periodic(c, f"shin_{side}", "rotation",
                 lambda p, o=off: (52 + 30 * max(0.0, sin(p + o + 0.5)), 0, 0), n=10)
    return c


# ====================================================================== attack

def attack():
    """It drops, lunges, and rakes — right hand across, left hand back the other way —
    and is crouched again before you have finished seeing it."""
    c = Clip(f"{N}.attack", 1.0, "once", "drop, lunge, rake, rake")
    c.keys("pelvis", "position", [(0.0, (0, 0, 0)), (0.2, (0, px(-2.5), px(-1))),
                                  (0.35, (0, px(-1), px(5))), (0.7, (0, px(-1), px(4))),
                                  (1.0, (0, 0, 0))])
    c.keys("torso", "rotation", [(0.0, (0, 0, 0)), (0.2, (14, 10, 0)), (0.35, (30, -14, 0)),
                                 (0.55, (28, 16, 0)), (0.75, (20, 0, 0)), (1.0, (0, 0, 0))])
    c.keys("head", "rotation", [(0.0, (0, 0, 0)), (0.2, (-10, -8, 0)), (0.35, (-24, 12, 0)),
                                (0.55, (-22, -12, 0)), (0.75, (-14, 0, 0)), (1.0, (0, 0, 0))])
    c.keys("arm_r", "rotation", [(0.0, (0, 0, 0)), (0.2, (30, 0, -40)), (0.35, (-100, -30, 10)),
                                 (0.5, (-80, -40, 20)), (1.0, (0, 0, 0))])
    c.keys("fore_r", "rotation", [(0.0, (0, 0, 0)), (0.2, (-40, 0, 0)), (0.35, (-4, 0, 0)),
                                  (0.5, (-40, 0, 0)), (1.0, (0, 0, 0))])
    c.keys("arm_l", "rotation", [(0.0, (0, 0, 0)), (0.3, (34, 0, 44)), (0.52, (-100, 30, -10)),
                                 (0.68, (-80, 40, -20)), (1.0, (0, 0, 0))])
    c.keys("fore_l", "rotation", [(0.0, (0, 0, 0)), (0.3, (-40, 0, 0)), (0.52, (-4, 0, 0)),
                                  (0.68, (-40, 0, 0)), (1.0, (0, 0, 0))])
    for side, sg in SIDES:
        c.keys(f"leg_{side}", "rotation", [(0.0, (0, 0, 0)), (0.2, (-16, 0, 0)),
                                           (0.35, (sg * -14, 0, 0)), (1.0, (0, 0, 0))])
        c.keys(f"shin_{side}", "rotation", [(0.0, (0, 0, 0)), (0.2, (26, 0, 0)),
                                            (0.35, (12, 0, 0)), (1.0, (0, 0, 0))])
    return c


CLIPS = {c.name: c for c in (frozen(), head_snap(), twitch(), stalk(), scuttle(), rear(),
                             climb(), attack())}


if __name__ == "__main__":
    for clip in CLIPS.values():
        print(clip.summary())
