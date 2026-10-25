"""The Sun Man's clips, as Blockbench keyframes. His geometry is the author's and is never
touched here — these only key the 29 bones it already has.

What makes 73 blocks of him frightening is not more motion, it is WRONG motion, and the five
devices from the original set still do the work — but as keys an animator would set, not as
quantised time:

  hold      long stillness, then one fast, heavy move that overshoots and settles
  lag       the head and neck trail the body, or refuse to follow it at all
  asym      one leg reaches further and lifts higher than the other; the walk never resolves
  overbend  the neck whips past where a neck stops
  stutter   ONLY where it is the point: `stare_down` arrives in eight STEP keys, so the face
            comes down in jerks with no frames between them

Position keys are in blocks (he is authored at 4/3 px per block; the exporter converts).
Rig reminders: +X = his left, +Z = forward; a hanging limb swings forward with -X; torso and
neck fold forward with +X; the head turns to his left with +Y.
"""
import math

import rig
from gait import Leg, key_gait
from keyframes import STEP, Clip, periodic

N = "animation.sun_man"
TAU = math.tau
C = rig
PPB = 1.0                              # gait maths in blocks
ARMS = [("left", "", 1), ("right", "", -1), ("left", "lower_", 1), ("right", "lower_", -1)]
LEGS = [Leg(rig, "left_thigh", "left_shin", 0.0, foot="left_foot", sole=1.512, ppb=PPB),
        Leg(rig, "right_thigh", "right_shin", 0.5, foot="right_foot", sole=1.512, ppb=PPB)]


def sin(p):
    return math.sin(p * TAU)


def cos(p):
    return math.cos(p * TAU)


def bump(p, at, width):
    d = abs(((p - at + 0.5) % 1.0) - 0.5)
    return 0.0 if d > width else math.cos(d / width * math.pi * 0.5) ** 2


def _arm(c, side, pre, bone_keys):
    for part, keys in bone_keys.items():
        c.keys(f"{side}_{pre}{part}", "rotation", keys)


# ====================================================================== idle

def idle():
    """A statue that moves twice. It breathes too slowly to see; four arms hang dead, each on
    its own clock; and twice a loop the head snaps round — fast, past where it means to stop,
    back a little — and holds there, looking, for far too long before it drifts back."""
    c = Clip(f"{N}.idle", 8.0, "loop", "stillness, broken twice by a head snap")
    periodic(c, "pelvis", "rotation", lambda p: (0, 0.6 * sin(p), 0))
    periodic(c, "torso", "rotation", lambda p: (0.9 + 0.5 * sin(2 * p), 0, 0.5 * sin(p + 0.3)))
    periodic(c, "upper_torso", "rotation", lambda p: (0.6 + 0.4 * sin(2 * p - 0.08), 1.0 * sin(p - 0.1), 0))
    c.keys("neck", "rotation", [
        (0.0, (0, 0, 0)), (1.75, (0, 0, 0)),
        (1.9, (-3, 17.5, 1.5)), (2.02, (-3, 15.5, 1.5)), (3.5, (-3, 16, 1.5)),
        (4.6, (0, 0, 0)), (5.35, (0, 0, 0)),
        (5.48, (-2, -13.5, -1.2)), (5.6, (-2, -12, -1)), (6.9, (-2, -12.5, -1)),
        (7.7, (0, 0, 0)), (8.0, (0, 0, 0))])
    c.keys("head", "rotation", [
        (0.0, (0, 0, 0)), (1.78, (0, 0, 0)),
        (1.95, (4, 10, -2.5)), (2.08, (4, 8.5, -2)), (3.5, (4, 9, -2)),
        (4.7, (0, 0, 0)), (5.4, (0, 0, 0)),
        (5.53, (3, -8, 2.2)), (5.66, (3, -7, 2)), (6.9, (3, -7.5, 2)),
        (7.75, (0, 0, 0)), (8.0, (0, 0, 0))])
    c.keys("sun_rays", "rotation", [(0.0, (0, 0, 0)), (1.9, (0, 0, 0)), (2.05, (0, 0, -2)),
                                    (2.3, (0, 0, 0.6)), (2.6, (0, 0, 0)), (5.5, (0, 0, 0)),
                                    (5.65, (0, 0, 1.6)), (5.9, (0, 0, -0.4)), (6.2, (0, 0, 0)),
                                    (8.0, (0, 0, 0))])
    for i, (side, pre, sg) in enumerate(ARMS):
        o = i * 0.11
        periodic(c, f"{side}_{pre}upper_arm", "rotation",
                 lambda p, o=o, sg=sg: (1.6 * sin(p - o), 0, sg * (2.0 + 0.8 * sin(p - o))))
        periodic(c, f"{side}_{pre}forearm", "rotation",
                 lambda p, o=o: (-2.4 - 1.2 * sin(p - o - 0.1), 0, 0))
        # fingers twitch on their own, off the body's rhythm
        at = 0.1 + i * 0.23
        c.keys(f"{side}_{pre}fingers", "rotation", [
            (0.0, (0, 0, 0)), (8.0 * at - 0.1, (0, 0, 0)), (8.0 * at, (-8, 0, 0)),
            (8.0 * at + 0.25, (0, 0, 0)), (8.0, (0, 0, 0))])
    return c


# ====================================================================== walk

def walk():
    """A stilt walk that never resolves. The legs keep a clean cycle — but the left reaches
    further and lifts higher than the right, which drags — and everything above the hips
    refuses to agree: the torso leans BACK into the stride, the arms swing at half the rate
    of the legs, and the head stays level and locked forward. It is watching you, not
    walking."""
    c = Clip(f"{N}.walk", 9.6, "loop", "the legs walk; the body refuses to agree")
    LEGS[0].stride_scale, LEGS[0].lift_scale = 1.1, 1.3
    LEGS[1].stride_scale, LEGS[1].lift_scale = 0.9, 0.7
    key_gait(c, LEGS, stride=13.0, duty=0.62, lift=2.2, drop=0.6, cycles=2, ppb=PPB,
             bob=lambda s: -0.35 * math.cos(4 * math.pi * (s - 0.08)))
    LEGS[0].stride_scale = LEGS[0].lift_scale = LEGS[1].stride_scale = LEGS[1].lift_scale = 1.0
    periodic(c, "pelvis", "rotation", lambda p: (0, -3 * cos(2 * p), 1.4 * sin(2 * p - 0.1)), n=16)
    periodic(c, "torso", "rotation",
             lambda p: (-4.5 + 1.2 * cos(4 * p), 2.2 * cos(2 * p), -1.2 * sin(2 * p - 0.1)), n=16)
    periodic(c, "upper_torso", "rotation", lambda p: (-2.5, 1.6 * sin(4 * p - 0.25), 0), n=16)
    periodic(c, "neck", "rotation",
             lambda p: (7.0 - 1.2 * cos(4 * p), 0.8 * cos(2 * p) - 1.6 * sin(4 * p - 0.25),
                        -0.2 * sin(2 * p - 0.1)), n=16)
    for i, (side, pre, sg) in enumerate(ARMS):
        lag = 0.3 + i * 0.07
        periodic(c, f"{side}_{pre}upper_arm", "rotation",
                 lambda p, l=lag, sg=sg: (sg * 9 * sin(p - l), 0, sg * 3), n=8)
        periodic(c, f"{side}_{pre}forearm", "rotation",
                 lambda p, l=lag, sg=sg: (-7 + sg * 5 * sin(p - l - 0.08), 0, 0), n=8)
        periodic(c, f"{side}_{pre}hand", "rotation",
                 lambda p, l=lag, sg=sg: (-3 + sg * 2.5 * sin(p - l - 0.14), 0, 0), n=8)
    return c


# ====================================================================== sprint

def sprint():
    """It runs. The head never moves — not a bob, not a degree — it is carried like a held
    camera while the body sprints underneath it. The stride is uneven, the left a third
    again as long as the right. The arms do not swing: all four trail, dead, and only the
    fingers move, clawing at the air ahead of it on their own clock."""
    c = Clip(f"{N}.sprint", 2.6, "loop", "the head holds still while the body runs")
    LEGS[0].stride_scale, LEGS[1].stride_scale = 1.15, 0.85
    key_gait(c, LEGS, stride=16.0, duty=0.4, lift=4.5, drop=1.6, ppb=PPB, n=16,
             bob=lambda s: -0.8 * math.cos(4 * math.pi * (s - 0.05)))
    LEGS[0].stride_scale = LEGS[1].stride_scale = 1.0
    periodic(c, "pelvis", "rotation", lambda p: (0, -4 * cos(p), 2 * sin(p - 0.08)))
    periodic(c, "torso", "rotation", lambda p: (16 + 1.5 * cos(2 * p), 2.4 * cos(p), -1.2 * sin(p)))
    periodic(c, "upper_torso", "rotation", lambda p: (9, 2.4 * sin(2 * p - 0.1), 0))
    # the neck cancels every bit of it, so the head is a fixed point
    periodic(c, "neck", "rotation",
             lambda p: (-25 - 1.5 * cos(2 * p), -2.4 * sin(2 * p - 0.1) + 1.6 * cos(p), 1.2 * sin(p)))
    for i, (side, pre, sg) in enumerate(ARMS):
        lag = 0.25 + i * 0.06
        periodic(c, f"{side}_{pre}upper_arm", "rotation",
                 lambda p, l=lag, sg=sg, i=i: (28 + 4 * sin(2 * p - l), 0, sg * (4 + i * 1.5)))
        periodic(c, f"{side}_{pre}forearm", "rotation", lambda p, l=lag: (-14 + 3 * sin(2 * p - l - 0.1), 0, 0))
        periodic(c, f"{side}_{pre}fingers", "rotation",
                 lambda p, i=i: (-44 + 34 * bump(2 * p % 1.0, i * 0.25, 0.14), 0, 0), n=16)
    return c


# ====================================================================== lurch

def lurch():
    """Three beats of nothing. Then one heavy, violent move: the torso throws forward over the
    top of you, the neck whips the OTHER way, past where a neck stops, and all four arms come
    over with it. It overshoots, recovers a little, and stays there."""
    c = Clip(f"{N}.lurch", 3.4, "hold", "three beats of nothing, then it folds over you")
    T0, T1, T2 = 1.9, 2.18, 2.42                     # gather, throw, overshoot
    def k(bone, vals):
        a, b, d, e = vals
        c.keys(bone, "rotation", [(0.0, (0, 0, 0)), (T0, a), (T1, b), (T2, d), (3.4, e)])
    k("torso", [(-3, 0, 0), (34, 0, 0), (39, 0, 0), (26, 0, 0)])
    k("upper_torso", [(-2, 0, 0), (26, 0, 0), (30, 0, 0), (20, 0, 0)])
    k("neck", [(4, 0, 0), (-46, 0, 0), (-52, 0, 0), (-36, 0, 0)])
    k("head", [(2, 0, 0), (-24, 0, 0), (-28, 0, 3), (-18, 0, 3)])
    k("sun_rays", [(0, 0, 0), (0, 0, 0), (0, 0, -4), (0, 0, 0)])
    for side, pre, sg in ARMS:
        k(f"{side}_{pre}upper_arm", [(6, 0, sg * 2), (-72, 0, sg * 16), (-80, 0, sg * 18), (-58, 0, sg * 12)])
        k(f"{side}_{pre}forearm", [(4, 0, 0), (-18, 0, 0), (-10, 0, 0), (-16, 0, 0)])
        k(f"{side}_{pre}fingers", [(0, 0, 0), (-10, 0, 0), (12, 0, 0), (-20, 0, 0)])
    for side in ("left", "right"):
        k(f"{side}_thigh", [(0, 0, 0), (-14, 0, 0), (-16, 0, 0), (-11, 0, 0)])
        k(f"{side}_shin", [(0, 0, 0), (20, 0, 0), (23, 0, 0), (16, 0, 0)])
        k(f"{side}_foot", [(0, 0, 0), (-6, 0, 0), (-7, 0, 0), (-5, 0, 0)])
    c.keys("pelvis", "position", [(0.0, (0, 0, 0)), (T0, (0, 0.2, 0)), (T1, (0, -0.7, 0)),
                                  (T2, (0, -0.85, 0)), (3.4, (0, -0.55, 0))])
    # the stillness is not dead: it breathes, barely, through the three beats
    c.key("upper_torso", "rotation", 0.95, (0.4, 0, 0))
    return c


# ====================================================================== stare down

def stare_down():
    """The neck lowers the face toward you over a full cycle, and stops. Nothing else on the
    body moves except the hands, which close. The descent is eight STEP keys: it arrives in
    jerks, with no frames between them, like footage with frames missing."""
    c = Clip(f"{N}.stare_down", 4.0, "hold", "the face comes down to you in eight jerks")
    steps = 8
    for i in range(steps + 1):
        t = 3.0 * i / steps
        e = i / steps
        # the neck brings the head down and out over you; the head tips back against it,
        # so the face arrives AIMED — about 55 degrees down, at someone standing in front
        c.key("neck", "rotation", t, (54 * e, 0, 0), STEP)
        c.key("head", "rotation", t, (-12 * e, 0, 0), STEP)
        c.key("upper_torso", "rotation", t, (9 * e, 0, 0), STEP)
        c.key("torso", "rotation", t, (3 * e, 0, 0), STEP)
    for bone in ("neck", "head", "upper_torso", "torso"):
        c.key(bone, "rotation", 4.0, c.tracks[(bone, "rotation")][-1].value, STEP)
    for i, (side, pre, sg) in enumerate(ARMS):
        c.keys(f"{side}_{pre}upper_arm", "rotation", [(0.0, (0, 0, sg * 2)), (3.0, (-6, 0, sg * 3)), (4.0, (-6, 0, sg * 3))])
        c.keys(f"{side}_{pre}forearm", "rotation", [(0.0, (0, 0, 0)), (3.0, (-24, 0, 0)), (4.0, (-24, 0, 0))])
        c.keys(f"{side}_{pre}fingers", "rotation", [(0.0, (0, 0, 0)), (1.5 + 0.2 * i, (-10, 0, 0)),
                                                    (1.6 + 0.2 * i, (-34, 0, 0), STEP),
                                                    (3.0, (-40, 0, 0)), (4.0, (-40, 0, 0))])
    return c


# ====================================================================== harvest rise

def harvest_rise():
    """Day thirty. The arms open in tiers — the upper pair first, the lower pair late — the
    back arches, the neck straightens, and the face tips up to the sky."""
    c = Clip(f"{N}.harvest_rise", 5.0, "hold", "day thirty: the arms open in tiers")
    c.keys("torso", "rotation", [(0.0, (0, 0, 0)), (0.6, (2, 0, 0)), (3.6, (-7, 0, 0)), (5.0, (-7, 0, 0))])
    c.keys("upper_torso", "rotation", [(0.0, (0, 0, 0)), (0.8, (2, 0, 0)), (3.8, (-9, 0, 0)), (5.0, (-9, 0, 0))])
    c.keys("neck", "rotation", [(0.0, (0, 0, 0)), (1.0, (3, 0, 0)), (4.0, (-14, 0, 0)), (5.0, (-14, 0, 0))])
    c.keys("head", "rotation", [(0.0, (0, 0, 0)), (1.2, (2, 0, 0)), (4.2, (-8, 0, 0)),
                                (4.6, (-10, 0, 1.5)), (5.0, (-9, 0, 1))])
    c.keys("sun_rays", "rotation", [(0.0, (0, 0, 0)), (3.8, (0, 0, 0)), (5.0, (0, 0, 6))])
    for i, (side, pre, sg) in enumerate(ARMS):
        start = 0.3 if not pre else 1.3
        tier = 1.0 if not pre else 0.82
        splay = 36.0 + i * 10.0
        c.keys(f"{side}_{pre}upper_arm", "rotation", [
            (0.0, (0, 0, 0)), (start, (4, 0, -sg * 2)),
            (start + 2.4, (-52 * tier, 0, sg * splay)), (start + 2.8, (-49 * tier, 0, sg * (splay - 3))),
            (5.0, (-50 * tier, 0, sg * (splay - 2)))])
        c.keys(f"{side}_{pre}forearm", "rotation", [(0.0, (0, 0, 0)), (start + 0.4, (-14, 0, 0)),
                                                    (start + 2.6, (-12, 0, 0)), (5.0, (-12, 0, 0))])
        c.keys(f"{side}_{pre}fingers", "rotation", [(0.0, (0, 0, 0)), (start + 1.8, (-30, 0, 0)),
                                                    (start + 2.6, (18, 0, 0)), (5.0, (14, 0, 0))])
    return c


# ====================================================================== grab

def grab():
    """The harvest. It straightens, gathers — then folds down over the top of you, and the
    LOWER arms come down to the ground with their fingers open, close on something, and
    carry it up."""
    c = Clip(f"{N}.grab", 3.8, "once", "it folds down and the lower arms close on you")
    c.keys("torso", "rotation", [(0.0, (0, 0, 0)), (0.7, (-4, 0, 0)), (1.5, (38, 0, 0)),
                                 (1.75, (42, 0, 0)), (2.0, (40, 0, 0)), (3.8, (0, 0, 0))])
    c.keys("upper_torso", "rotation", [(0.0, (0, 0, 0)), (0.7, (-3, 0, 0)), (1.5, (18, 0, 0)),
                                       (2.0, (16, 0, 0)), (3.8, (0, 0, 0))])
    c.keys("neck", "rotation", [(0.0, (0, 0, 0)), (0.7, (3, 0, 0)), (1.5, (-26, 0, 0)),
                                (2.0, (-24, 0, 0)), (3.8, (0, 0, 0))])
    c.keys("head", "rotation", [(0.0, (0, 0, 0)), (0.7, (2, 0, 0)), (1.5, (-14, 0, 0)), (3.8, (0, 0, 0))])
    for side in ("left", "right"):
        c.keys(f"{side}_thigh", "rotation", [(0.0, (0, 0, 0)), (1.5, (-16, 0, 0)), (2.2, (-14, 0, 0)), (3.8, (0, 0, 0))])
        c.keys(f"{side}_shin", "rotation", [(0.0, (0, 0, 0)), (1.5, (24, 0, 0)), (2.2, (22, 0, 0)), (3.8, (0, 0, 0))])
        c.keys(f"{side}_foot", "rotation", [(0.0, (0, 0, 0)), (1.5, (-8, 0, 0)), (2.2, (-8, 0, 0)), (3.8, (0, 0, 0))])
    c.keys("pelvis", "position", [(0.0, (0, 0, 0)), (0.7, (0, 0.3, 0)), (1.5, (0, -1.1, 0)),
                                  (2.2, (0, -1.0, 0)), (3.8, (0, 0, 0))])
    for side, sg in (("left", 1), ("right", -1)):
        _arm(c, side, "lower_", {
            "upper_arm": [(0.0, (0, 0, 0)), (0.7, (16, 0, sg * 14)), (1.55, (-62, 0, -sg * 6)),
                          (1.8, (-66, 0, -sg * 10)), (2.4, (-60, 0, -sg * 8)), (3.8, (0, 0, 0))],
            "forearm": [(0.0, (0, 0, 0)), (0.7, (-20, 0, 0)), (1.55, (-6, 0, 0)),
                        (2.4, (-40, 0, 0)), (3.8, (0, 0, 0))],
            "fingers": [(0.0, (0, 0, 0)), (1.3, (26, 0, 0)), (1.75, (30, 0, 0)),
                        (1.9, (-60, 0, 0)), (3.4, (-56, 0, 0)), (3.8, (0, 0, 0))],
        })
        _arm(c, side, "", {
            "upper_arm": [(0.0, (0, 0, 0)), (0.7, (8, 0, sg * 22)), (1.6, (-30, 0, sg * 34)),
                          (2.4, (-26, 0, sg * 30)), (3.8, (0, 0, 0))],
            "forearm": [(0.0, (0, 0, 0)), (1.6, (-20, 0, 0)), (3.8, (0, 0, 0))],
        })
    return c


CLIPS = {c.name: c for c in (idle(), walk(), sprint(), lurch(), stare_down(), harvest_rise(), grab())}


if __name__ == "__main__":
    for clip in CLIPS.values():
        print(clip.summary())
