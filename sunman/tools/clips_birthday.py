"""The Birthday People's clips, as Blockbench keyframes — the same set for both variants.

They are marionettes nobody is working. They hang off their strings more than they stand:
the arms never swing on their own, they DANGLE and lag and settle; the column of a head
rides on top like something balanced there; and when one moves on purpose it is slow,
except for the moments it is not. Smooth keys for the hanging and the swaying. STEP keys
for the moments that should have no frames in them: the head coming round in notches, the
strings jerking taut.

`build(creature)` keys a set of clips against either variant (`birthday.CROWN`,
`birthday.TREE`); the crown bone carries the spikes or the tree, so in the tree variant the
same keys make the branches sway. `clips_birthday_crown.py` and `clips_birthday_tree.py`
are the per-variant modules the exporters and `check.py` import.

Rig reminders (right-handed, +X = its left, +Z = forward):
  leg  -X swings the leg forward     shin  +X bends the knee
  chest/torso  +X folds it forward   head  +X nods the column forward, +Y turns it to its left
  arm  -X reaches forward, +Z (left) / -Z (right) lifts the arm out to the side
"""
import math

from birthday import ANKLE
from gait import Foot, key_feet
from keyframes import STEP, Clip, periodic, px

TAU = math.tau
SIDES = (("l", 1), ("r", -1))


def sin(p):
    return math.sin(p * TAU)


def cos(p):
    return math.cos(p * TAU)


def feet(C):
    return [Foot(C, "leg_l", "shin_l", 0.0, bend=1.0, base={"leg_l": (0, 0.75), "shin_l": (0, -0.75)}),
            Foot(C, "leg_r", "shin_r", 0.5, bend=1.0, base={"leg_r": (0, -0.75), "shin_r": (0, 0.75)})]


def _level_feet(C, c, toe_up=0.0):
    """Key each foot flat on the floor however the leg above it is angled: the ankle undoes
    whatever pitch the hip, thigh and shin have stacked up. In the air the toes hang a
    little (`toe_up` degrees), the way a lifted foot does."""
    times = sorted({k.time for (b, ch), tr in c.tracks.items()
                    if b.startswith(("leg_", "shin_")) or b in ("pelvis", "torso")
                    for k in tr if ch == "rotation"})
    for side in ("l", "r"):
        rest = C.solve_m({})
        ground = min(_low(C, rest, f"foot_{side}"), 0.0)
        for t in times:
            pose = c.sample(t)
            sol = C.solve_m(pose)
            m = sol[f"shin_{side}"][1]
            # pitch of the shin's frame about X, from where its forward axis now points
            pitch = math.degrees(math.atan2(-m[1][2], m[2][2]))
            lifted = _low(C, sol, f"shin_{side}") - (ground + ANKLE / 16.0) > 0.05
            c.key(f"foot_{side}", "rotation", t, (-pitch - (toe_up if lifted else 0.0), 0, 0))


def _low(C, sol, bone):
    from rig import mat_vec
    pos, m = sol[bone]
    return min(pos[1] + mat_vec(m, p)[1] for cu in C.GEOMETRY[bone] for p in C._cube_corners(cu))


def _plant(C, c):
    """Re-solve the pelvis height at every key that moves the legs or body, so the lower
    foot stays on the floor: a lunge sinks the body, never the feet."""
    pel = {k.time: k for k in c.tracks.get(("pelvis", "position"), [])}
    times = set(pel) | {k.time for (b, ch), tr in c.tracks.items()
                        if b.startswith(("leg_", "shin_")) or (b == "pelvis" and ch == "rotation")
                        for k in tr}
    rest = C.solve_m({})
    base = min(_low(C, rest, b) for b in ("foot_l", "foot_r"))
    keys = []
    for t in sorted(times):
        pose = c.sample(t)
        x, _y, z = pose.get("pelvis", {}).get("position", (0.0, 0.0, 0.0))
        pose.setdefault("pelvis", {})["position"] = (x, 0.0, z)
        sol = C.solve_m(pose)
        lo = min(_low(C, sol, b) for b in ("foot_l", "foot_r"))
        keys.append((t, (x, base - lo, z), pel[t].interp if t in pel else None))
    c.tracks.pop(("pelvis", "position"), None)
    for t, v, it in keys:
        c.key("pelvis", "position", t, v, *([it] if it else []))


def _strings_sway(c, amp=1.0, period=1.0):
    """The strings hang slack and drift, whatever the body does."""
    n = max(1, round(c.length / period))
    periodic(c, "strings", "rotation",
             lambda p: (amp * 3.0 * sin(n * p + 0.1), 0, amp * 4.0 * sin(n * p)), n=12)


def _hold_ends(c, bones, channel="rotation"):
    for b in bones:
        c.key(b, channel, 0.0, (0, 0, 0), STEP)
        c.key(b, channel, c.length, (0, 0, 0), STEP)


# ====================================================================== idle

def idle(C, N):
    """It stands under its strings. It sways, the way something hanging sways — the body one
    way, the column the other, a beat late — and the arms swing off the shoulders like
    weights on threads. Once, a hand closes and opens. Once, the strings twitch, and the
    whole of it lifts a pixel off its heels and settles."""
    c = Clip(f"{N}.idle", 6.0, "loop", "hanging sway, a hand that closes once, a twitch of the strings")
    periodic(c, "pelvis", "rotation", lambda p: (0.6 * sin(p + 0.25), 0, 1.4 * sin(p)), n=12)
    periodic(c, "chest", "rotation", lambda p: (0.8 * sin(2 * p), 0, -0.9 * sin(p - 0.08)), n=12)
    periodic(c, "head", "rotation", lambda p: (0.6 * sin(p - 0.1), 2.0 * sin(p - 0.2), -1.6 * sin(p - 0.16)), n=12)
    periodic(c, "crown", "rotation", lambda p: (0.8 * sin(2 * p - 0.2), 0, -1.2 * sin(p - 0.3)), n=12)
    for side, sg in SIDES:
        periodic(c, f"arm_{side}", "rotation", lambda p, sg=sg: (1.2 * sin(p - 0.15), 0, -1.4 * sin(p - 0.12)), n=12)
        periodic(c, f"fore_{side}", "rotation", lambda p: (-0.8 * sin(p - 0.25), 0, 0), n=12)
        periodic(c, f"leg_{side}", "rotation", lambda p: (0, 0, -1.4 * sin(p)), n=12)
    # the hand that closes: the fingers curl in, quick, and open slowly
    c.keys("hand_r", "rotation", [(0.0, (0, 0, 0)), (2.3, (0, 0, 0)), (2.45, (-22, 0, 10)),
                                  (2.7, (-24, 0, 11)), (3.6, (0, 0, 0)), (6.0, (0, 0, 0))])
    # the strings twitch: everything lifts on them and drops back
    c.keys("pelvis", "position", [(0.0, (0, 0, 0)), (4.4, (0, 0, 0), STEP), (4.45, (0, px(0.8), 0), STEP),
                                  (4.6, (0, px(0.3), 0)), (5.1, (0, 0, 0)), (6.0, (0, 0, 0))])
    c.keys("strings", "rotation", [(0.0, (0, 0, 0)), (4.4, (0, 0, 0), STEP), (4.45, (-4, 0, 2), STEP),
                                   (4.7, (-1, 0, 0)), (6.0, (0, 0, 0))])
    return c


# ====================================================================== walk

def walk(C, N):
    """A marionette's walk: each foot lifted high and set down stiff, as if by a string at
    the knee; the body dips and lifts with it; the arms do not swing — they hang and are
    dragged, a beat behind, the long black fingers trailing; the column sways on top."""
    c = Clip(f"{N}.walk", 2.8, "loop", "lifted by the knees, arms dragged, fingers trailing")
    periodic(c, "pelvis", "position", lambda p: (0, px(-3.4 - 0.8 * cos(2 * p - 0.1)), 0), n=16)
    periodic(c, "pelvis", "rotation", lambda p: (0, 5 * sin(p), 3 * sin(p - 0.08)), n=16)
    periodic(c, "chest", "rotation", lambda p: (2.5 + 1.0 * cos(2 * p - 0.3), -4 * sin(p), -2 * sin(p - 0.15)), n=16)
    periodic(c, "head", "rotation", lambda p: (-1.5 - 1.0 * cos(2 * p - 0.45), -2 * sin(p - 0.1), 3 * sin(p - 0.3)), n=16)
    periodic(c, "crown", "rotation", lambda p: (1.5 * cos(2 * p - 0.6), 0, 2.5 * sin(p - 0.45)), n=16)
    for side, sg in SIDES:
        off = 0.0 if side == "l" else 0.5
        # dragged, not swung: small, late, and the hand later still
        periodic(c, f"arm_{side}", "rotation",
                 lambda p, o=off, sg=sg: (5 * sin(p + o - 0.2), 0, sg * (1.5 + 1.0 * sin(2 * p))), n=16)
        periodic(c, f"fore_{side}", "rotation", lambda p, o=off: (-3 - 3 * sin(p + o - 0.3), 0, 0), n=16)
        periodic(c, f"hand_{side}", "rotation", lambda p, o=off: (6 * sin(p + o - 0.42), 0, 0), n=16)
    _strings_sway(c, 1.2, c.length / 2)
    key_feet(c, C, feet(C), stride=18.0, duty=0.6, lift=5.0, n=16, ground=px(ANKLE + 0.6))
    _level_feet(C, c, toe_up=8.0)
    return c


# ====================================================================== turn

def turn(C, N):
    """It has noticed you. The body does not move. The column turns — not smoothly, in
    notches, like something heavy being wound round by hand — until the face is on you. The
    crown, or the tree, comes round a moment after the head, and keeps going a little."""
    c = Clip(f"{N}.turn", 3.4, "hold", "the column winds round to you in notches")
    seq = []
    t, yaw = 0.5, 0
    for step in (9, 7, 11, 6, 10, 8, 5):
        seq += [(t - 0.04, yaw, STEP), (t, yaw + step, STEP)]
        yaw += step
        t += 0.3 + 0.05 * (step % 3)
    keys = [(0.0, (0, 0, 0), STEP)]
    for tt, y, it in seq:
        keys.append((tt, (1.0, y, -0.02 * y), it))
    keys.append((3.4, (1.0, yaw, -0.02 * yaw), STEP))
    c.keys("head", "rotation", keys)
    c.keys("crown", "rotation", [(0.0, (0, 0, 0)), (0.6, (0, 0, 0)), (1.2, (0, 6, 1.5)),
                                 (2.6, (0, 11, 2)), (3.0, (0, 7, 0.5)), (3.4, (0, 8, 1))])
    c.keys("chest", "rotation", [(0.0, (0, 0, 0)), (3.0, (0, 4, 0)), (3.4, (0, 4, 0))])
    _hold_ends(c, ("hand_l",))
    c.keys("hand_l", "rotation", [(2.6, (0, 0, 0), STEP), (2.65, (-14, 0, -6), STEP), (3.0, (-10, 0, -4))])
    c.keys("strings", "rotation", [(0.0, (0, 0, 0)), (1.0, (2, 0, -3)), (2.2, (-1, 0, 3)), (3.4, (1, 0, -1))])
    return c


# ====================================================================== reach

def reach(C, N):
    """Both arms come up, slowly, as if lifted by the wrists — straight out in front, the
    long fingers hanging off the ends and then opening — and the column leans after them
    and down, so the face comes toward you."""
    c = Clip(f"{N}.reach", 3.0, "hold", "arms lifted by the wrists; the face leans in")
    for side, sg in SIDES:
        c.keys(f"arm_{side}", "rotation", [(0.0, (0, 0, 0)), (0.4, (-6, 0, sg * 2)), (1.6, (-78, 0, -sg * 4)),
                                           (2.1, (-84, 0, -sg * 6)), (3.0, (-82, 0, -sg * 5))])
        c.keys(f"fore_{side}", "rotation", [(0.0, (0, 0, 0)), (1.0, (-14, 0, 0)), (1.8, (-4, 0, 0)), (3.0, (-6, 0, 0))])
        # the hands hang from the wrists until the arms are up, then the fingers open
        c.keys(f"hand_{side}", "rotation", [(0.0, (0, 0, 0)), (1.4, (60, 0, 0)), (1.9, (40, 0, 0)),
                                            (2.2, (-8, 0, sg * 10)), (3.0, (-4, 0, sg * 8))])
    c.keys("chest", "rotation", [(0.0, (0, 0, 0)), (1.6, (6, 0, 0)), (3.0, (9, 0, 0))])
    c.keys("head", "rotation", [(0.0, (0, 0, 0)), (1.4, (2, 0, 0)), (2.4, (14, 0, -4)), (3.0, (16, 0, -5))])
    c.keys("crown", "rotation", [(0.0, (0, 0, 0)), (2.0, (-2, 0, 0)), (2.6, (4, 0, 1)), (3.0, (3, 0, 1))])
    c.keys("strings", "rotation", [(0.0, (0, 0, 0)), (1.6, (-6, 0, 2)), (3.0, (-8, 0, 3))])
    return c


# ====================================================================== grab

def grab(C, N):
    """The arms come up and over far faster than anything that size should move, the
    fingers close on whatever was in front of it, and it pulls it in to the face."""
    c = Clip(f"{N}.grab", 1.4, "once", "too fast: up, over, the fingers close, pulled in")
    c.keys("pelvis", "position", [(0.0, (0, 0, 0)), (0.25, (0, px(-1.0), px(-1))), (0.45, (0, px(-0.6), px(3))),
                                  (0.9, (0, px(-0.4), px(1.5))), (1.4, (0, 0, 0))])
    c.keys("chest", "rotation", [(0.0, (0, 0, 0)), (0.25, (-6, 0, 0)), (0.45, (16, 0, 0)), (0.9, (8, 0, 0)), (1.4, (0, 0, 0))])
    c.keys("head", "rotation", [(0.0, (0, 0, 0)), (0.25, (-4, 0, 0)), (0.45, (10, 0, 0)), (0.9, (18, 0, 3)), (1.4, (0, 0, 0))])
    for side, sg in SIDES:
        c.keys(f"arm_{side}", "rotation", [(0.0, (0, 0, 0)), (0.25, (12, 0, sg * 14)), (0.45, (-112, 0, -sg * 10)),
                                           (0.6, (-96, 0, -sg * 14)), (0.9, (-70, 0, -sg * 18)), (1.4, (0, 0, 0))])
        c.keys(f"fore_{side}", "rotation", [(0.0, (0, 0, 0)), (0.25, (-10, 0, 0)), (0.45, (-4, 0, 0)),
                                            (0.6, (-36, 0, 0)), (0.9, (-70, 0, 0)), (1.4, (0, 0, 0))])
        c.keys(f"hand_{side}", "rotation", [(0.0, (0, 0, 0)), (0.45, (-6, 0, sg * 12)), (0.5, (-48, 0, -sg * 8), STEP),
                                            (0.9, (-44, 0, -sg * 6)), (1.4, (0, 0, 0))])
    c.keys("crown", "rotation", [(0.0, (0, 0, 0)), (0.45, (-6, 0, 0)), (0.6, (5, 0, 1)), (0.9, (-2, 0, 0)), (1.4, (0, 0, 0))])
    c.keys("strings", "rotation", [(0.0, (0, 0, 0)), (0.45, (-10, 0, 4)), (0.9, (6, 0, -3)), (1.4, (0, 0, 0))])
    _plant(C, c)
    return c


# ====================================================================== dangle

def dangle(C, N):
    """Hauled up by its strings. The feet leave the floor; the body hangs off the head and
    turns slowly on the threads; every limb swings dead from its joint, each on its own
    clock — and then the strings jerk, and it all jumps, and swings."""
    c = Clip(f"{N}.dangle", 4.0, "loop", "hauled up on its strings, limp, turning, jerked")
    lift = [(0.0, (0, px(3.0), 0)), (1.6, (0, px(3.4), 0)), (1.9, (0, px(3.4), 0), STEP),
            (1.95, (0, px(5.2), 0), STEP), (2.3, (0, px(3.8), 0)), (4.0, (0, px(3.0), 0))]
    c.keys("pelvis", "position", lift)
    periodic(c, "pelvis", "rotation", lambda p: (2 * sin(p + 0.2), 14 * sin(p), 2.5 * sin(2 * p)), n=16)
    c.keys("head", "rotation", [(0.0, (-2, 0, 0)), (1.9, (-3, 0, 2), STEP), (1.95, (-8, 0, -3), STEP),
                                (2.5, (-3, 0, 1)), (4.0, (-2, 0, 0))])
    c.keys("chest", "rotation", [(0.0, (4, 0, 0)), (1.9, (5, 0, 1), STEP), (1.95, (-3, 0, -2), STEP),
                                 (2.6, (5, 0, 0)), (4.0, (4, 0, 0))])
    for side, sg in SIDES:
        off = 0.0 if side == "l" else 0.37
        periodic(c, f"arm_{side}", "rotation", lambda p, o=off, sg=sg: (8 * sin(p + o), 0, sg * (3 + 3 * sin(2 * p + o))), n=16)
        periodic(c, f"fore_{side}", "rotation", lambda p, o=off: (-6 - 6 * sin(p + o - 0.2), 0, 0), n=16)
        periodic(c, f"hand_{side}", "rotation", lambda p, o=off: (10 * sin(p + o - 0.35), 0, 0), n=16)
        periodic(c, f"leg_{side}", "rotation", lambda p, o=off, sg=sg: (-6 * sin(p + o + 0.1), 0, sg * 2 * sin(2 * p)), n=16)
        periodic(c, f"shin_{side}", "rotation", lambda p, o=off: (8 + 7 * sin(p + o - 0.1), 0, 0), n=16)
    periodic(c, "crown", "rotation", lambda p: (3 * sin(p - 0.3), 0, 3 * sin(2 * p - 0.2)), n=16)
    c.keys("strings", "rotation", [(0.0, (0, 0, 0)), (1.9, (0, 0, 0), STEP), (1.95, (-3, 0, 0), STEP),
                                   (2.4, (0, 0, 0)), (4.0, (0, 0, 0))])
    return c


# ====================================================================== death

def death(C, N):
    """The strings are cut. Nothing holds it up: the knees go, the body folds over them, and
    the column — heaviest, highest — topples, and takes the rest of it down onto the ground,
    face first. The arms land last, far too long, across it."""
    c = Clip(f"{N}.death", 2.6, "hold", "the strings are cut; the column topples it over")
    for side, sg in SIDES:
        c.keys(f"leg_{side}", "rotation", [(0.0, (0, 0, 0)), (0.1, (0, 0, 0)), (0.5, (-34, 0, sg * 6)),
                                           (1.0, (-50, 0, sg * 8)), (2.6, (-50, 0, sg * 8))])
        c.keys(f"shin_{side}", "rotation", [(0.0, (0, 0, 0)), (0.1, (0, 0, 0)), (0.5, (70, 0, 0)),
                                            (1.0, (96, 0, 0)), (2.6, (98, 0, 0))])
        land = (-160, 0, sg * 18) if side == "l" else (-150, 0, -sg * 6)
        c.keys(f"arm_{side}", "rotation", [(0.0, (0, 0, 0)), (0.5, (14, 0, sg * 10)), (1.2, (-40, 0, sg * 20)),
                                           (1.7, land), (1.85, (land[0] + 8, 0, land[2])), (2.6, (land[0] + 6, 0, land[2]))])
        c.keys(f"hand_{side}", "rotation", [(0.0, (0, 0, 0)), (1.7, (10, 0, 0)), (1.85, (-30, 0, 0)), (2.6, (-24, 0, 0))])
    c.keys("chest", "rotation", [(0.0, (0, 0, 0)), (0.5, (14, 0, 0)), (1.2, (26, 0, 4)), (2.6, (26, 0, 4))])
    c.keys("head", "rotation", [(0.0, (0, 0, 0)), (0.5, (8, 0, 0)), (1.3, (22, 0, -6)), (1.55, (14, 0, -4)),
                                (1.7, (20, 0, -5)), (2.6, (20, 0, -5))])
    c.keys("crown", "rotation", [(0.0, (0, 0, 0)), (1.3, (6, 0, 0)), (1.5, (-8, 0, 2)), (1.7, (4, 0, -1)), (2.6, (2, 0, 0))])
    # the strings fall slack: they swing down over it
    c.keys("strings", "rotation", [(0.0, (0, 0, 0)), (0.1, (6, 0, 4), STEP), (0.8, (60, 0, 20)),
                                   (1.6, (110, 0, 30)), (2.0, (100, 0, 26)), (2.6, (104, 0, 28))])
    _topple(C, c, [(0.0, 0.0), (0.1, 0.0), (0.5, 6.0), (0.9, 20.0), (1.3, 50.0), (1.6, 76.0),
                   (1.75, 70.0), (1.95, 74.0), (2.6, 74.0)])
    return c


def _topple(C, c, pitch_keys):
    """Pelvis pitch forward, with its height solved every 0.05 s so the lowest point of the
    body is always on the ground — the fall comes out of the rig. The strings are left out:
    they are not body, and they fall where they like."""
    for t, a in pitch_keys:
        c.key("pelvis", "rotation", t, (a, 0, 0))
    body = {b: cs for b, cs in C.GEOMETRY.items() if b != "strings"}

    def lowest(pose):
        from rig import mat_vec
        sol = C.solve_m(pose)
        return min(sol[b][0][1] + mat_vec(sol[b][1], p)[1]
                   for b, cs in body.items() for cu in cs for p in C._cube_corners(cu))

    base = lowest({})
    times = sorted({t for t, _ in pitch_keys} | {round(k * 0.05, 4) for k in range(int(c.length * 20) + 1)})
    for t in times:
        pose = c.sample(t)
        pose.setdefault("pelvis", {})["position"] = (0.0, 0.0, 0.0)
        c.key("pelvis", "position", t, (0.0, base - lowest(pose), 0.0))


def build(C):
    N = f"animation.{C.name}"
    clips = [idle(C, N), walk(C, N), turn(C, N), reach(C, N), grab(C, N), dangle(C, N), death(C, N)]
    return {c.name: c for c in clips}

