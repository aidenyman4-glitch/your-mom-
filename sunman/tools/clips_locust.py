"""The Locust's clips, as Blockbench keyframes.

"It doesn't see you... but it knows you're there."

It is a puppet now — pale bound limbs, a mask on a stalk of a neck — and it moves like one:
held up by nothing, its weight in the wrong places. It spawns NoAI and frozen, and the
stillness is most of the horror, so most of what is here is about how little it moves and how
suddenly. Smooth keys for what it does on purpose. STEP keys for what should have no frames
in between — the head coming round, the twitches, the snap at the end of a loop — because
easing turns those into an animal deciding to move.

Its legs bend the WRONG way when it walks: a locust's legs, not a man's. The legs and, when
it scuttles, the arms are keyed by IK against whatever the body is doing (`gait.key_feet`), so
the points of its feet plant and stay planted.

Rig reminders (right-handed, +X = its left, +Z = forward). The head bone IS the neck: it
pivots on the shoulders, so head +X droops the whole stalk forward, +Y twists the face round
on it, +Z leans it over to its right.
"""
import math

import tiers
from gait import Foot, end_point, key_feet
from keyframes import LINEAR, STEP, Clip, periodic, px

C = tiers.LOCUST
N = "animation.locust"
TAU = math.tau
SIDES = (("l", 1), ("r", -1))


def sin(p):
    return math.sin(p * TAU)


def cos(p):
    return math.cos(p * TAU)


def _twitch(c, bone, t, delta, hold=0.1, back=(0, 0, 0)):
    """A twitch with no frames in it: rest, then `delta` the next instant, then rest."""
    c.key(bone, "rotation", t - 0.05, back, STEP)
    c.key(bone, "rotation", t, delta, STEP)
    c.key(bone, "rotation", t + hold, back, STEP)


def _hold_ends(c, bones, length):
    for b in bones:
        c.key(b, "rotation", 0.0, (0, 0, 0), STEP)
        c.key(b, "rotation", length, (0, 0, 0), STEP)


# feet: the legs bend like a locust's; for the scuttle the hands are feet too
LEGS = [Foot(C, "leg_l", "shin_l", 0.0, bend=-1.0, base={"leg_l": (0, 2), "shin_l": (0, -1)}),
        Foot(C, "leg_r", "shin_r", 0.5, bend=-1.0, base={"leg_r": (0, -2), "shin_r": (0, 1)})]
FEET = LEGS


# ====================================================================== frozen

def frozen():
    """It does not move. It does not breathe. Over seven seconds the head lists over by a few
    degrees, too slowly to see — and then, at the end of the loop, it is upright again with
    nothing in between. A blade moves once. A shoulder, once."""
    c = Clip(f"{N}.frozen", 7.0, "loop", "it does not move. then it is upright again")
    c.keys("head", "rotation", [(0.0, (0, 0, 0), LINEAR), (6.9, (1.5, 3, 7), STEP),
                                (7.0, (0, 0, 0), STEP)])
    _hold_ends(c, ("fore_l", "fore_r", "arm_r", "torso"), 7.0)
    _twitch(c, "fore_l", 1.6, (-9, 0, 0), 0.1)
    _twitch(c, "arm_r", 3.2, (0, 0, -8), 0.1)
    _twitch(c, "fore_r", 4.7, (-6, 0, 3), 0.05)
    _twitch(c, "torso", 5.5, (1.2, 0, 0), 0.08)
    return c


# ====================================================================== head snap

def head_snap():
    """Its back to you. Then — between two frames — the face is looking at you: 171 degrees
    round on that neck, and nothing else on it has moved. A breath later the neck goes over
    sideways with a crack, as far as a neck does not go, and it shivers there and holds."""
    c = Clip(f"{N}.head_snap", 2.8, "hold", "its face comes round; then the neck cracks over")
    c.keys("head", "rotation", [
        (0.0, (0, 0, 0), STEP), (0.95, (0, 0, 0), STEP),
        (1.0, (-4, -171, 4), STEP),                                   # no frames in between
        (1.55, (-4, -171, 4), STEP), (1.6, (-6, -171, 30), STEP),     # crack
        (1.7, (-6, -170, 27), STEP), (1.8, (-6, -172, 31), STEP), (1.9, (-6, -171, 28), STEP),
        (2.05, (-6, -171, 29)), (2.8, (-5, -171, 28))])
    c.keys("torso", "rotation", [(0.0, (0, 0, 0), STEP), (1.0, (0, 0, 0), STEP),
                                 (1.05, (1.5, 0, 0), STEP), (1.3, (0, 0, 0)),
                                 (1.6, (0, 0, -1.5), STEP), (1.85, (0, 0, -0.6)), (2.8, (0, 0, -0.6))])
    c.keys("fore_l", "rotation", [(0.0, (0, 0, 0), STEP), (1.62, (0, 0, 0), STEP),
                                  (1.67, (-14, 0, -6), STEP), (1.9, (-6, 0, -2)), (2.8, (-6, 0, -2))])
    c.keys("fore_r", "rotation", [(0.0, (0, 0, 0), STEP), (1.64, (0, 0, 0), STEP),
                                  (1.7, (-10, 0, 5), STEP), (1.95, (-4, 0, 2)), (2.8, (-4, 0, 2))])
    return c


# ====================================================================== twitch

def twitch():
    """The idle inside 22 blocks. A slow weave — and through it, spasms: the neck whips, a
    shoulder jumps out of its socket and back, the blades splay, a knee gives."""
    c = Clip(f"{N}.twitch", 3.2, "loop", "a slow weave, broken by spasms on no rhythm")
    periodic(c, "torso", "rotation", lambda p: (1.0 * sin(p), 2.5 * sin(p + 0.2), 1.5 * sin(2 * p)))
    c.keys("head", "rotation", [
        (0.0, (0, 0, 0)), (0.5, (3, 8, 4)), (0.55, (10, 18, -8), STEP), (0.75, (4, 10, 0)),
        (1.4, (-2, -6, 4)), (1.95, (-3, -8, 6)), (2.0, (-10, -24, 18), STEP), (2.15, (-4, -12, 8)),
        (2.7, (0, -2, 0)), (2.75, (4, 4, -6), STEP), (2.85, (0, 0, 0)), (3.2, (0, 0, 0))])
    c.keys("arm_l", "rotation", [(0.0, (0, 0, 0)), (1.05, (-2, 0, 1), STEP), (1.1, (-14, 0, 16), STEP),
                                 (1.2, (-3, 0, 2)), (3.2, (0, 0, 0))])
    c.keys("arm_r", "rotation", [(0.0, (0, 0, 0)), (2.25, (-2, 0, -1), STEP), (2.3, (-12, 0, -18), STEP),
                                 (2.4, (-3, 0, -2)), (3.2, (0, 0, 0))])
    c.keys("fore_l", "rotation", [(0.0, (0, 0, 0)), (0.8, (-3, 0, 0), STEP), (0.85, (-28, 0, -8), STEP),
                                  (1.0, (-6, 0, 0)), (3.2, (0, 0, 0))])
    c.keys("fore_r", "rotation", [(0.0, (0, 0, 0)), (1.45, (-3, 0, 0), STEP), (1.5, (-24, 0, 8), STEP),
                                  (1.65, (-6, 0, 0)), (3.2, (0, 0, 0))])
    c.keys("shin_l", "rotation", [(0.0, (0, 0, 0)), (2.4, (0, 0, 0), STEP), (2.45, (16, 0, 0), STEP),
                                  (2.6, (4, 0, 0)), (3.2, (0, 0, 0))])
    c.keys("pelvis", "position", [(0.0, (0, 0, 0)), (2.4, (0, 0, 0), STEP), (2.45, (0, px(-0.7), 0), STEP),
                                  (2.6, (0, px(-0.2), 0)), (3.2, (0, 0, 0))])
    _plant(c)
    return c


# ====================================================================== stalk

def stalk():
    """It walks like a puppet nobody is working: high, pulled steps on the points of its feet,
    the knees bending BACKWARD, a locust's — the body bobbing as if it hangs from a string,
    the arms swinging late and loose, and the head lolling, looking about, never in time."""
    c = Clip(f"{N}.stalk", 3.2, "loop", "high pulled steps; its knees bend the wrong way")
    periodic(c, "pelvis", "position", lambda p: (0, px(-1.2 - 0.6 * cos(4 * p - 0.15)), 0), n=16)
    periodic(c, "pelvis", "rotation", lambda p: (0, 5 * sin(2 * p), 3 * sin(2 * p - 0.1)), n=16)
    periodic(c, "torso", "rotation", lambda p: (6 + 2.5 * cos(4 * p - 0.3), -3 * sin(2 * p), -2.5 * sin(2 * p - 0.2)), n=16)
    periodic(c, "head", "rotation",
             lambda p: (-4 - 3 * cos(4 * p - 0.5), 22 * sin(p) - 6 * sin(3 * p), 10 * sin(2 * p - 0.35)), n=16)
    for side, sg in SIDES:
        off = 0.0 if side == "l" else 0.5
        periodic(c, f"arm_{side}", "rotation",
                 lambda p, o=off, sg=sg: (-12 * sin(2 * p + o - 0.15), 0, sg * (4 + 3 * sin(4 * p))), n=16)
        periodic(c, f"fore_{side}", "rotation",
                 lambda p, o=off: (-8 - 14 * sin(2 * p + o - 0.3), 0, 0), n=16)
    key_feet(c, C, LEGS, stride=9.0, duty=0.56, lift=5.0, n=12, cycles=2)
    return c


# ====================================================================== scuttle

def _scuttle_feet(body_pose):
    """The hands become the front feet: they land a little ahead of and outside the
    shoulders, wherever the bent-double body has put them."""
    sol = C.solve_m(body_pose)
    feet = []
    for side, sg, phase in (("l", 1, 0.5), ("r", -1, 0.0)):
        sh = sol[f"arm_{side}"][0]
        f = Foot(C, f"arm_{side}", f"fore_{side}", phase, bend=-1.0,
                 base={f"arm_{side}": (0, -sg * 4), f"fore_{side}": (0, 0)})
        # plant each blade where it can reach with the limb swung only fore and aft: as far
        # out as the splayed arm already puts it, and a little ahead of the shoulder
        reach = dict(body_pose)
        reach[f"arm_{side}"] = {"rotation": (-40.0, 0.0, -sg * 4)}
        out_x = end_point(C, reach, f"fore_{side}", f.end)[0]
        f.home = (out_x, 0.0, sh[2] + px(3.0))
        feet.append(f)
    return feet


def scuttle():
    """At a run it goes down: hunched over, the neck straight up out of its shoulders so the
    mask stays level and aimed, stilting along on the blades of its arms and the points of its
    feet — diagonal pairs, the arms longer than the legs, fast."""
    c = Clip(f"{N}.scuttle", 0.9, "loop", "hunched over, stilting on the blades of its arms")
    periodic(c, "pelvis", "position", lambda p: (0, px(-5.0 - 0.9 * cos(4 * p - 0.1)), 0), n=12)
    periodic(c, "pelvis", "rotation", lambda p: (0, 6 * sin(p), 3 * sin(p - 0.1)), n=12)
    periodic(c, "torso", "rotation", lambda p: (60 + 3 * cos(2 * p), -5 * sin(p), -2 * sin(p)), n=12)
    periodic(c, "head", "rotation", lambda p: (-62 - 3 * cos(2 * p - 0.2), 5 * sin(p), 4 * sin(p - 0.25)), n=12)
    key_feet(c, C, LEGS, stride=14.0, duty=0.45, lift=5.0, n=12)
    # the hands reach further than the feet, so they stay down longer: same ground speed
    key_feet(c, C, _scuttle_feet(c.sample(0.0)), stride=16.0, duty=0.45 * 16.0 / 14.0, lift=4.0, n=12,
             ground=px(0.6))   # the point, not its corner, on the floor
    return c


# ====================================================================== rear

def rear():
    """The wake-up. It sinks — and then it is already up, arched back, the arms flung high and
    the blades splayed, the neck thrown back and over — and it shudders there, and holds."""
    c = Clip(f"{N}.rear", 1.9, "hold", "it sinks, and then it is already up")
    c.keys("pelvis", "position", [(0.0, (0, 0, 0)), (0.45, (0, px(-2), 0)), (0.62, (0, px(1.4), 0)),
                                  (0.8, (0, px(0.8), 0)), (1.9, (0, px(1), 0))])
    c.keys("torso", "rotation", [(0.0, (0, 0, 0)), (0.45, (14, 0, 0)), (0.62, (-34, 0, 0)),
                                 (0.8, (-28, 0, 0)), (1.9, (-30, 0, 0))])
    c.keys("head", "rotation", [(0.0, (0, 0, 0)), (0.45, (18, 0, 0)), (0.62, (-48, 0, 20)),
                                (0.8, (-40, 6, 26)), (0.85, (-44, -6, 18), STEP), (0.9, (-40, 5, 28), STEP),
                                (0.95, (-43, -4, 20), STEP), (1.0, (-41, 3, 26), STEP),
                                (1.1, (-42, 0, 24)), (1.9, (-40, 2, 26))])
    for side, sg in SIDES:
        # raised past the horizontal, an arm swings OUT with the opposite sign of Z
        c.keys(f"arm_{side}", "rotation", [(0.0, (0, 0, 0)), (0.45, (10, 0, sg * 4)),
                                           (0.62, (-152, 0, -sg * 34)), (0.8, (-142, 0, -sg * 30)),
                                           (0.85, (-146, 0, -sg * 33), STEP), (0.9, (-141, 0, -sg * 29), STEP),
                                           (0.95, (-144, 0, -sg * 31)), (1.9, (-143, 0, -sg * 31))])
        c.keys(f"fore_{side}", "rotation", [(0.0, (0, 0, 0)), (0.45, (-22, 0, 0)),
                                            (0.66, (10, 0, sg * 8)), (0.85, (-24, 0, 0)),
                                            (1.9, (-20, 0, 0))])
        c.keys(f"leg_{side}", "rotation", [(0.0, (0, 0, 0)), (0.45, (-14, 0, 0)),
                                           (0.62, (12, 0, 0)), (1.9, (10, 0, 0))])
        c.keys(f"shin_{side}", "rotation", [(0.0, (0, 0, 0)), (0.45, (24, 0, 0)),
                                            (0.62, (-8, 0, 0)), (1.9, (-6, 0, 0))])
    _plant(c)
    return c


# ====================================================================== climb

def climb():
    """Up a wall, facing it, diagonal pairs of limbs reaching in turn — and its head has
    turned all the way round on that neck, and is looking back down the wall at the floor.
    At you."""
    c = Clip(f"{N}.climb", 1.6, "loop", "facing the wall; its head turned round to the floor")
    periodic(c, "torso", "rotation", lambda p: (6 + 2 * sin(2 * p), 5 * sin(p), 3 * sin(p)))
    periodic(c, "pelvis", "position", lambda p: (0, px(0.8 * sin(2 * p - 0.1)), px(1.0)))
    periodic(c, "pelvis", "rotation", lambda p: (0, -4 * sin(p), -2 * sin(p)))
    # the head ignores all of it: turned round, drooping at the floor, and held there
    periodic(c, "head", "rotation", lambda p: (26 - 2 * sin(2 * p), 176 - 5 * sin(p), -6 - 3 * sin(p)))
    for side, sg in SIDES:
        off = 0.0 if side == "l" else 0.5
        periodic(c, f"arm_{side}", "rotation",
                 lambda p, o=off, sg=sg: (-160 + 22 * sin(p + o), 0, -sg * (16 + 8 * cos(p + o))), n=10)
        periodic(c, f"fore_{side}", "rotation",
                 lambda p, o=off: (-12 - 26 * max(0.0, sin(p + o + 0.25)), 0, 0), n=10)
        periodic(c, f"leg_{side}", "rotation",
                 lambda p, o=off, sg=sg: (-46 - 26 * sin(p + o + 0.5), 0, sg * 14), n=10)
        periodic(c, f"shin_{side}", "rotation",
                 lambda p, o=off: (52 + 30 * max(0.0, sin(p + o + 0.5)), 0, 0), n=10)
    return c


# ====================================================================== attack

def attack():
    """It drops, and lunges, and both blades go in point-first — then it twists, and tears
    them out, and is crouched again before you have finished seeing it."""
    c = Clip(f"{N}.attack", 1.1, "once", "drop, lunge, blades in, twist, tear out")
    c.keys("pelvis", "position", [(0.0, (0, 0, 0)), (0.22, (0, px(-2.5), px(-1))),
                                  (0.36, (0, px(-1.2), px(6))), (0.6, (0, px(-1.2), px(5))),
                                  (1.1, (0, 0, 0))])
    c.keys("torso", "rotation", [(0.0, (0, 0, 0)), (0.22, (16, 0, 0)), (0.36, (22, 0, 0)),
                                 (0.46, (22, 22, 0)), (0.56, (18, -18, 0)), (0.75, (10, 0, 0)), (1.1, (0, 0, 0))])
    c.keys("head", "rotation", [(0.0, (0, 0, 0)), (0.22, (-12, 0, 0)), (0.36, (24, 0, 0)),
                                (0.46, (22, -16, 8)), (0.56, (20, 14, -8)), (0.8, (8, 0, 0)), (1.1, (0, 0, 0))])
    for side, sg in SIDES:
        c.keys(f"arm_{side}", "rotation", [(0.0, (0, 0, 0)), (0.22, (30, 0, sg * 18)),
                                           (0.36, (-96, 0, -sg * 4)), (0.46, (-92, 0, -sg * 6)),
                                           (0.56, (-60, 0, sg * 18)), (1.1, (0, 0, 0))])
        c.keys(f"fore_{side}", "rotation", [(0.0, (0, 0, 0)), (0.22, (-50, 0, 0)), (0.36, (2, 0, 0)),
                                            (0.48, (-6, 0, 0)), (0.56, (-46, 0, 0)), (1.1, (0, 0, 0))])
        c.keys(f"leg_{side}", "rotation", [(0.0, (0, 0, 0)), (0.22, (-18, 0, 0)),
                                           (0.36, (sg * -14, 0, 0)), (1.1, (0, 0, 0))])
        c.keys(f"shin_{side}", "rotation", [(0.0, (0, 0, 0)), (0.22, (28, 0, 0)),
                                            (0.36, (12, 0, 0)), (1.1, (0, 0, 0))])
    _plant(c)
    return c


# ====================================================================== peek

def peek():
    """Round a door frame: one hand takes the jamb, the body leans, and the neck lays itself
    out sideways until the mask is looking at you on its side. It tips a little further, as
    if to see you better. It stays."""
    c = Clip(f"{N}.peek", 3.2, "hold", "the neck laid out sideways round a door frame")
    c.keys("torso", "rotation", [(0.0, (0, 0, 0)), (0.6, (2, 0, 0)), (1.6, (4, -8, -16)),
                                 (2.0, (4, -8, -15)), (3.2, (4, -9, -16))])
    c.keys("head", "rotation", [(0.0, (0, 0, 0)), (0.7, (0, 0, 2)), (1.7, (-4, 10, -64)),
                                (1.9, (-4, 10, -60)), (2.6, (-6, 14, -84)), (2.7, (-6, 14, -76), STEP),
                                (2.8, (-6, 12, -78)), (3.2, (-6, 13, -79))])
    c.keys("arm_l", "rotation", [(0.0, (0, 0, 0)), (0.5, (-10, 0, 10)), (1.3, (-40, 0, 62)),
                                 (1.5, (-36, 0, 58)), (3.2, (-38, 0, 60))])
    c.keys("fore_l", "rotation", [(0.0, (0, 0, 0)), (0.6, (-10, 0, 0)), (1.4, (-62, 0, -10)),
                                  (1.6, (-56, 0, -8)), (3.2, (-58, 0, -9))])
    c.keys("arm_r", "rotation", [(0.0, (0, 0, 0)), (1.6, (6, 0, -4)), (3.2, (6, 0, -4))])
    c.keys("pelvis", "rotation", [(0.0, (0, 0, 0)), (1.6, (0, 0, -6)), (3.2, (0, 0, -6))])
    c.keys("leg_l", "rotation", [(0.0, (0, 0, 0)), (1.6, (0, 0, 5)), (3.2, (0, 0, 5))])
    c.keys("leg_r", "rotation", [(0.0, (0, 0, 0)), (1.6, (0, 0, 7)), (3.2, (0, 0, 7))])
    return c


# ====================================================================== death

def death():
    """Its strings are cut. One last tug upward — then everything goes at once: the knees fold
    the wrong way, the body drops onto them, the head swings down on its neck and bounces,
    and the whole thing tips over into a heap."""
    c = Clip(f"{N}.death", 2.2, "hold", "the strings are cut; it drops into a heap")
    c.keys("torso", "rotation", [(0.0, (0, 0, 0)), (0.12, (-6, 0, 0)), (0.42, (48, 0, 8)),
                                 (0.55, (40, 0, 6)), (1.0, (52, 0, 10)), (2.2, (52, 0, 10))])
    c.keys("head", "rotation", [(0.0, (0, 0, 0)), (0.12, (-10, 0, 0)), (0.4, (70, 0, -20)),
                                (0.5, (48, 0, -14)), (0.6, (64, 0, -24)), (0.75, (58, 0, -20)),
                                (1.3, (66, 10, -30)), (2.2, (66, 10, -30))])
    for side, sg in SIDES:
        c.keys(f"leg_{side}", "rotation", [(0.0, (0, 0, 0)), (0.12, (2, 0, 0)), (0.4, (40, 0, sg * 10)),
                                           (2.2, (42, 0, sg * 12))])
        c.keys(f"shin_{side}", "rotation", [(0.0, (0, 0, 0)), (0.12, (-2, 0, 0)), (0.4, (-88, 0, 0)),
                                            (2.2, (-92, 0, 0))])
        # it falls to its left: the left arm ends up under it, the right flops over it
        land = (-40, 0, 12) if side == "l" else (-20, 0, 64)
        c.keys(f"arm_{side}", "rotation", [(0.0, (0, 0, 0)), (0.12, (-8, 0, sg * 4)), (0.4, (-30, 0, sg * 26)),
                                           (0.55, (-20, 0, sg * 18)), (1.2, land), (1.35, (land[0] + 6, 0, land[2] - 6)),
                                           (2.2, (land[0] + 4, 0, land[2] - 4))])
        c.keys(f"fore_{side}", "rotation", [(0.0, (0, 0, 0)), (0.4, (-30, 0, 0)), (0.6, (-10, 0, 0)),
                                            (1.3, (-34, 0, 0)), (2.2, (-34, 0, 0))])
    _collapse(c, [(0.0, 0.0), (0.12, 0.0), (0.4, 0.0), (0.7, 14.0), (1.0, 62.0), (1.15, 86.0),
                  (1.3, 80.0), (1.5, 84.0), (2.2, 84.0)])
    return c


def _collapse(c, roll_keys):
    """Pelvis roll, with the position solved so the lowest point of the body is on the ground
    at every key and every twentieth of a second between — the drop comes out of the rig, not
    out of a guess, and the blades never go through the floor on the way down."""
    for t, roll in roll_keys:
        c.key("pelvis", "rotation", t, (0, 0, -roll))
    base_lo = C.extents({})[0]
    times = sorted({t for t, _ in roll_keys} |
                   {round(k * 0.05, 4) for k in range(int(c.length * 20) + 1)})
    for t in times:
        pose = c.sample(t)
        pose.setdefault("pelvis", {})["position"] = (0.0, 0.0, 0.0)
        lo = C.extents(pose)[0]
        c.key("pelvis", "position", t, (0.0, base_lo - lo, 0.0))


def _plant(c):
    """Re-solve the pelvis height at every key that moves the legs, so the lower foot stays
    on the floor however the knees are keyed — a crouch sinks the body, never the feet."""
    legs = ("leg_l", "leg_r", "shin_l", "shin_r")
    pel = {k.time: k for k in c.tracks.get(("pelvis", "position"), [])}
    times = set(pel)
    interp = {}
    for (bone, ch), track in c.tracks.items():
        if bone in legs or (bone == "pelvis" and ch == "rotation"):
            for k in track:
                times.add(k.time)
                if k.interp == STEP:
                    interp[k.time] = STEP
    ts = sorted(times)                     # and halfway along every eased span
    times |= {round((t0 + t1) / 2, 4) for t0, t1 in zip(ts, ts[1:])
              if t1 - t0 > 0.1 and interp.get(t1) != STEP and interp.get(t0) != STEP}
    rest = C.solve_m({})
    base = min(_lowest(rest, b) for b in ("shin_l", "shin_r"))
    keys = []
    for t in sorted(times):
        pose = c.sample(t)
        x, _y, z = pose.get("pelvis", {}).get("position", (0.0, 0.0, 0.0))
        pose.setdefault("pelvis", {})["position"] = (x, 0.0, z)
        sol = C.solve_m(pose)
        lo = min(_lowest(sol, b) for b in ("shin_l", "shin_r"))
        it = pel[t].interp if t in pel else interp.get(t)
        keys.append((t, (x, base - lo, z), it))
    c.tracks.pop(("pelvis", "position"), None)
    for t, v, it in keys:
        c.key("pelvis", "position", t, v, *([it] if it else []))


def _lowest(sol, bone):
    from rig import mat_vec
    pos, m = sol[bone]
    return min(pos[1] + mat_vec(m, p)[1] for cu in C.GEOMETRY[bone] for p in C._cube_corners(cu))


CLIPS = {c.name: c for c in (frozen(), head_snap(), twitch(), stalk(), scuttle(), rear(),
                             climb(), attack(), peek(), death())}


if __name__ == "__main__":
    for clip in CLIPS.values():
        print(clip.summary())
