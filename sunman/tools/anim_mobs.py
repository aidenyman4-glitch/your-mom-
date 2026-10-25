"""Clips for the two tier creatures, built on the same five devices as the Sun Man's.

tiers.py already carries the clips the datapack ships. Those are correct but polite. These
are the same poses pushed with stutter, lag, hold and overbend, plus the shots the references
describe and the original set never had: the Locust turning its head to look back at you
without moving its body, and the Dark Walker holding its hat dead level while four metres of
leg swing underneath it.
"""
import math

from anim import hold, lag, spike, stutter, sway

TAU = math.tau


# ====================================================================== LOCUST
# "It doesn't see you... but it knows you're there." Spawns NoAI with an empty animation.

def frozen_wrong(p):
    """It does not move. Then, between two frames and with nothing in between, its head
    is facing you.

    The datapack spawns it frozen inside ruined houses, and the stillness is the whole
    horror — so the only event in the clip is one impossible head yaw, held. No easing,
    because easing would make it an animal turning to look.
    """
    pose = {"pelvis": (0.0, 164.0, 0.0),           # standing turned away from you
            "torso": (6.0, 0.0, 0.0),
            "head": (-4.0, 0.0, 3.0)}
    if p >= 0.42:
        pose["head"] = (-9.0, -171.0, 6.0)         # 171 degrees. Nothing else changed.
        pose["torso"] = (6.0, 0.0, 0.0)
    if p >= 0.86:                                  # and a single twitch, right at the end
        pose["head"] = (-13.0, -168.0, 11.0)
    return pose


def twitch_hard(p):
    """The idle it drops into inside 22 blocks. Quantised so it jitters instead of shivers."""
    j = math.sin(stutter(p, 9) * TAU * 3.0)
    k = sway(lag(p, 0.12), 2.0)
    pose = {
        "head": (3.4 * j, 7.0 * k, 2.6 * j),
        "torso": (1.4 * j, 2.0 * k, 0.8 * j),
        "arm_l": (-4.0 + 7.0 * spike(p, 0.3, 0.05), 0.0, 6.0),
        "arm_r": (-4.0 - 7.0 * spike(p, 0.7, 0.05), 0.0, -6.0),
        "hand_l": (16.0 + 22.0 * spike(p, 0.34, 0.04), 0.0, 0.0),
        "hand_r": (16.0 + 22.0 * spike(p, 0.74, 0.04), 0.0, 0.0),
    }
    return pose


def scuttle(p):
    """Inside 9 blocks it stalks. At a sprint it does this — and it is door height, which
    is worse than tall: it fits through everything you can fit through."""
    pose = {}
    step = p * 2.0 % 1.0
    for side, off, reach in (("l", 0.0, 1.0), ("r", 0.5, 0.74)):
        a = stutter(step + off, 10) * TAU
        sw = math.sin(a)
        pose[f"leg_{side}"] = (62.0 * sw * reach, 0.0, 0.0)
        pose[f"foot_{side}"] = (-26.0 * sw, 0.0, 0.0)
        # the arms reach AHEAD and claw, they do not swing in opposition
        b = (step + off * 0.5 + 0.2) * TAU
        pose[f"arm_{side}"] = (-104.0 + 20.0 * math.sin(b), 0.0, 0.0)
        pose[f"hand_{side}"] = (-38.0 + 34.0 * math.sin(b * 2.0), 0.0, 0.0)
    pose["torso"] = (44.0, 4.0 * sway(step), 0.0)
    pose["head"] = (-46.0, -4.0 * sway(step), 0.0)      # face stays level, aimed at you
    pose["pelvis"] = (0.0, 2.0 * sway(step), 2.0 * sway(step, 2.0))
    return pose


def shriek(p):
    """The wake-up inside 9 blocks: it rears, marks you with glowing, and the waking is
    one-way. Four beats of nothing, then it is already up."""
    k = hold(p, 0.52, 5.0)
    j = spike(p, 0.78, 0.14)
    return {
        "torso": (-34.0 * k, 0.0, 0.0),
        "head": (26.0 * k + 12.0 * j, 6.0 * j, 4.0 * j),
        "arm_l": (-112.0 * k, 0.0, 34.0 * k), "arm_r": (-112.0 * k, 0.0, -34.0 * k),
        "hand_l": (-44.0 * k, 0.0, 0.0), "hand_r": (-44.0 * k, 0.0, 0.0),
        "leg_l": (20.0 * k, 0.0, 0.0), "leg_r": (14.0 * k, 0.0, 0.0),
        "pelvis": (0.0, 0.0, 0.0),
    }


def climb_wall(p):
    """All four limbs splayed on a wall, head craned back down at the floor — at you."""
    pose = {"torso": (58.0, 0.0, 0.0), "head": (-52.0, 0.0, 0.0)}
    for side, sg, off in (("l", 1, 0.0), ("r", -1, 0.5)):
        s = math.sin(stutter(p + off, 8) * TAU)
        pose[f"arm_{side}"] = (-78.0 + 30.0 * s, 0.0, sg * 38.0)
        pose[f"hand_{side}"] = (-28.0 - 16.0 * s, 0.0, 0.0)
        pose[f"leg_{side}"] = (48.0 - 26.0 * s, 0.0, sg * 30.0)
        pose[f"foot_{side}"] = (-22.0, 0.0, 0.0)
    return pose


LOCUST_CLIPS = {
    "frozen_wrong": (frozen_wrong, "Frozen", "it does not move. then its head is facing you"),
    "twitch_hard": (twitch_hard, "Twitch", "inside 22 blocks"),
    "scuttle": (scuttle, "Scuttle", "door height, and it fits where you fit"),
    "shriek": (shriek, "Rear", "waking is one-way"),
    "climb_wall": (climb_wall, "Climb", "craned back down at the floor"),
}


# ================================================================= DARK WALKER
# "It does not hurry, because it does not need to." 7.4 blocks, six tendril arms in three
# tiers, a wide brim, and two lit eyes under it. The outdoor tier: it cannot follow you
# through a door, which is the only good news about it.

TENDRILS = [(n, side, 1 if side == "l" else -1)
            for n in (1, 2, 3) for side in ("l", "r")]


def _drift(pose, p, amp=1.0, rate=1.0, curl=1.0, splay=0.0, lead=None):
    """Six arms on six clocks. If they ever agree with each other they read as cloth on a
    frame, and the whole creature stops being alive."""
    for i, (n, side, sg) in enumerate(TENDRILS):
        o = i * 0.167
        k = 1.0 if lead is None else lead(i, p)
        d = math.sin((p * rate + o) * TAU)
        pose[f"arm_{side}{n}"] = (amp * 3.4 * d * k, amp * 1.8 * math.sin((p * rate * 0.5 + o) * TAU),
                                  sg * (3.0 + 2.6 * d) * k)
        pose[f"tip_{side}{n}"] = (curl * 7.0 * math.sin((p * rate + o + 0.3) * TAU) - splay,
                                  0.0, sg * splay * 0.5)
    return pose


def walker_road(p):
    """The approach. The stride is enormous and slow and it skips — `stutter` drops the leg
    phase into ten holds, so one step in each cycle lands before it should.

    The head is the point. Four metres of leg swing underneath it and the brim never tips a
    degree: every bit of body roll is cancelled at the neck, so the hat holds dead level and
    the eyes stay on you the whole way in.
    """
    pose = {}
    for side, off, reach in (("l", 0.0, 1.06), ("r", 0.5, 0.86)):
        a = stutter(p + off, 10) * TAU
        sw = math.sin(a)
        lift = max(0.0, math.cos(a))
        pose[f"leg_{side}"] = (33.0 * sw * reach, 0.0, 0.0)
        pose[f"foot_{side}"] = (-18.0 * sw + 14.0 * lift, 0.0, 0.0)
    roll = sway(p, 2.0)
    pose["pelvis"] = (0.0, 2.4 * sway(p), 1.2 * roll)
    pose["torso"] = (2.0, 0.0, -0.9 * roll)
    pose["neck"] = (-2.0, 0.0, 0.9 * roll)            # cancels the roll. The brim is level.
    pose["head"] = (0.0, 0.0, 0.0)
    pose["hat"] = (0.0, 0.0, 0.0)
    return _drift(pose, lag(p, 0.18), amp=2.1, rate=1.0, curl=1.5)


def walker_watch(p):
    """It is at the end of the road and it is not coming. Nothing moves but the tendrils —
    and then, late and all at once, the head turns and the eyes are on you."""
    pose = {"torso": (1.0, 0.0, 0.4 * sway(p, 0.5))}
    _drift(pose, p, amp=1.0, rate=0.6, curl=1.0)
    k = hold(p, 0.58, 6.0)
    pose["neck"] = (0.0, -30.0 * k, 0.0)
    pose["head"] = (-2.0 * k, -14.0 * k, 1.6 * k)
    pose["hat"] = (1.5 * k, 0.0, -2.0 * k)
    if p > 0.93:                                       # one twitch, held, then the loop
        pose["head"] = (-5.0, -16.0, 4.0)
    return pose


def walker_loom(p):
    """It folds down to your height. Nothing this tall should be able to reach you without
    kneeling, and it does not kneel — it hinges at the hips and the brim tips forward over
    the eyes on the way down, so the last thing you see lit goes out.
    """
    k = hold(p, 0.18, 2.4)
    e = k * k * (3 - 2 * k)
    pose = {
        "torso": (48.0 * e, 0.0, 0.0),
        "neck": (-24.0 * e, 0.0, 0.0),
        "head": (17.0 * e, 0.0, 2.0 * spike(p, 0.74, 0.06)),
        "hat": (11.0 * e, 0.0, 0.0),
        "leg_l": (17.0 * e, 0.0, 3.0 * e), "leg_r": (13.0 * e, 0.0, -3.0 * e),
        "foot_l": (-15.0 * e, 0.0, 0.0), "foot_r": (-11.0 * e, 0.0, 0.0),
    }
    for i, (n, side, sg) in enumerate(TENDRILS):
        o = i * 0.15
        pose[f"arm_{side}{n}"] = (-30.0 * e - 9.0 * sway(lag(p, o), 1.0),
                                  0.0, sg * (3.0 + 2.5 * i) * e)
        pose[f"tip_{side}{n}"] = (-22.0 * e, 0.0, 0.0)
    return pose


def walker_reach(p):
    """All six come down, but not together — each leads the next by a sixth of a beat, so
    they arrive as a wave rather than a gesture. The digits open last.

    It has to hinge to do this at all. Its shoulders are 5.7 blocks up and its arms are 2.9
    long, so standing straight it cannot reach anything shorter than a horse; the fold is
    not drama, it is the only way the gesture closes.
    """
    e = min(1.0, p * 1.3) ** 0.8
    open_ = max(0.0, (p - 0.60) / 0.40)
    pose = {"torso": (38.0 * e, 0.0, 0.0), "neck": (-16.0 * e, 0.0, 0.0),
            "head": (13.0 * e, 0.0, 0.0), "hat": (7.0 * e, 0.0, 0.0),
            "leg_l": (12.0 * e, 0.0, 0.0), "leg_r": (9.0 * e, 0.0, 0.0),
            "foot_l": (-10.0 * e, 0.0, 0.0), "foot_r": (-8.0 * e, 0.0, 0.0)}
    for i, (n, side, sg) in enumerate(TENDRILS):
        lead = max(0.0, min(1.0, (p - i * 0.055) * 2.4))
        pose[f"arm_{side}{n}"] = (-46.0 * e * lead, 0.0, sg * (2.0 + 3.0 * i) * e
                                  + sg * 16.0 * open_)
        pose[f"tip_{side}{n}"] = (-26.0 * e * lead - 24.0 * open_, 0.0, sg * 26.0 * open_)
    return pose


WALKER_CLIPS = {
    "walker_road": (walker_road, "Dark Walker", "the brim never tips. the eyes stay on you"),
    "walker_watch": (walker_watch, "Dark Walker · watch", "it is not coming. then it turns"),
    "walker_loom": (walker_loom, "Dark Walker · loom", "it hinges at the hips. it does not kneel"),
    "walker_reach": (walker_reach, "Dark Walker · reach", "six arms, each leading the next"),
}
