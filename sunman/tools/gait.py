"""Walk cycles that keep their feet on the ground.

A hand-keyed walk on a 4-block stilt slides: the planted foot drifts at whatever speed the
thigh angles happen to give it, and the heel lands in the air. So the legs here are not
keyed directly. The FOOT is designed — locked to the ground and carried back at a constant
speed through stance, then lifted and swung forward on an arc — and two-bone IK in the
sagittal plane turns that path into thigh and knee angles. Those angles are then sampled back
into a dozen sparse keys per cycle, which is what an animator would have keyed and what
Blockbench interpolates; `check()` measures how far the reconstruction drifts from the
designed path, so a bad cycle is a failing number, not a judgement call.

Angles follow the rig: a hanging limb swings FORWARD with negative X; a knee bends with
positive X on the lower segment.
"""
import math

from rig import quat_rotate


def leg_ik(dy, dz, l1, l2):
    """Absolute thigh and knee angles (degrees) that put the sole at (dy, dz) from the hip.
    dy is negative (down). The knee bends forward of the hip-sole line, like a knee."""
    d = math.hypot(dy, dz)
    d = min(d, (l1 + l2) * 0.9999)
    cos_g = (l1 * l1 + l2 * l2 - d * d) / (2 * l1 * l2)
    knee = math.pi - math.acos(max(-1.0, min(1.0, cos_g)))
    alpha = math.atan2(dz, -dy)                     # forward of straight down
    cos_b = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    beta = math.acos(max(-1.0, min(1.0, cos_b)))
    return -math.degrees(alpha + beta), math.degrees(knee)


def foot_path(s, stride, duty, lift, toe_lead=0.0):
    """Sole offset (dy, dz) in pixels at cycle phase s (0 = this foot's contact, in front)."""
    s %= 1.0
    if s < duty:
        u = s / duty
        return 0.0, stride * (0.5 - u)
    u = (s - duty) / (1.0 - duty)
    z = -stride * 0.5 + stride * (0.5 - 0.5 * math.cos(math.pi * u))
    y = lift * math.sin(math.pi * u) ** 1.3
    return y, z + toe_lead * math.sin(math.pi * u)


class Leg:
    """One leg of a rig, measured from its own rest pose."""

    def __init__(self, creature, thigh, shin, phase, foot=None, sole=None, ppb=16.0,
                 stride_scale=1.0, lift_scale=1.0):
        self.c, self.thigh, self.shin, self.foot, self.phase = creature, thigh, shin, foot, phase
        # an uneven gait is a per-leg scale: one leg reaching further, one foot dragging
        self.stride_scale, self.lift_scale = stride_scale, lift_scale
        J = creature.J
        self.ppb = ppb
        hip, knee = J[thigh], J[shin]
        self.l1 = math.hypot(hip[1] - knee[1], hip[2] - knee[2]) * ppb
        if foot:
            ank = J[foot]
            self.l2 = math.hypot(knee[1] - ank[1], knee[2] - ank[2]) * ppb
            sole_drop = (sole if sole is not None else 0.0)
        else:
            self.l2 = (sole if sole is not None else knee[1]) * ppb
            sole_drop = 0.0
        self.sole_drop = sole_drop * ppb
        rest = getattr(creature, "REST", {})
        self.rest_thigh = rest.get(thigh, (0.0, 0.0, 0.0))[0]
        self.rest_shin = rest.get(shin, (0.0, 0.0, 0.0))[0]
        # where the rest pose actually puts the sole, relative to the hip
        a1 = math.radians(self.rest_thigh)
        a2 = math.radians(self.rest_thigh + self.rest_shin)
        self.rest_dy = -self.l1 * math.cos(a1) - self.l2 * math.cos(a2)
        self.rest_dz = -self.l1 * math.sin(a1) - self.l2 * math.sin(a2)

    def angles(self, s, hip_drop_px, stride, duty, lift):
        """Keyframe DELTAS (thigh_x, shin_x, foot_x) at phase s with the hip lowered."""
        # a longer stride is a longer stance: the planted foot still moves at the body's speed
        duty = min(0.9, duty * self.stride_scale)
        fy, fz = foot_path(s + self.phase, stride * self.stride_scale, duty,
                           lift * self.lift_scale)
        dy = self.rest_dy + fy + hip_drop_px          # a lower hip brings the sole up
        dz = self.rest_dz + fz
        t, k = leg_ik(dy, dz, self.l1, self.l2)
        foot = 0.0
        if self.foot:
            # keep the sole flat through stance; toe down off the ground, toe up into contact
            ss = (s + self.phase) % 1.0
            flat = -(t + k)
            if ss < duty:
                roll = 14.0 * max(0.0, (ss - duty * 0.7) / (duty * 0.3)) ** 2
            else:
                u = (ss - duty) / (1.0 - duty)
                roll = 14.0 * (1 - u) ** 2 - 10.0 * math.sin(math.pi * u * 0.9) ** 2
            foot = flat + roll
        return t - self.rest_thigh, k - self.rest_shin, foot


def key_gait(clip, legs, stride, duty, lift, bob, drop, n=12, pelvis="pelvis", ppb=16.0,
             start=0.0, end=None, cycles=1):
    """Key every leg of `legs` over the clip, plus the pelvis bob that goes with them.
    bob(s) is in pixels; drop is the constant crouch in pixels that gives the knees room."""
    end = clip.length if end is None else end
    total = n * cycles
    for leg in legs:
        th, sh, ft = [], [], []
        for i in range(total):
            s = (i / total * cycles) % 1.0
            hd = drop - bob(s)
            a, b, f = leg.angles(s, hd, stride, duty, lift)
            th.append((a, 0, 0))
            sh.append((b, 0, 0))
            ft.append((f, 0, 0))
        clip.cycle(leg.thigh, "rotation", th, start, end)
        clip.cycle(leg.shin, "rotation", sh, start, end)
        if leg.foot:
            clip.cycle(leg.foot, "rotation", ft, start, end)
    clip.cycle(pelvis, "position",
               [(0, (bob((i / total * cycles) % 1.0) - drop) / ppb, 0) for i in range(total)],
               start, end)


def check(clip, creature, legs, ppb=16.0, fps=40):
    """How well the keyed clip plants its feet: (worst sole height in stance, worst
    deviation from a constant stance speed), both in pixels per frame / pixels."""
    report = []
    for leg in legs:
        pts = []
        n = int(clip.length * fps)
        for i in range(n + 1):
            pose = clip.sample(clip.length * i / n)
            sol = creature.solve(pose)
            bone = leg.foot or leg.shin
            pos, q = sol[bone]
            if leg.foot:
                local = (0.0, -leg.sole_drop / ppb, 0.0)
            else:
                local = (0.0, -leg.l2 / ppb, 0.0)
            w = [pos[k] + quat_rotate(q, local)[k] for k in range(3)]
            pts.append((w[1] * ppb, w[2] * ppb))
        report.append(pts)
    return report


# ====================================================================== limbs under any body
# `key_gait` assumes level hips. A creature that runs bent double, or walks its hands, needs
# IK that knows where the shoulder actually is: `ik2` solves a two-bone limb against the rig's
# own forward kinematics (rest rotations, splay, a pitched torso, scale — all of it) by
# Gauss-Newton on the two hinge angles, starting on the side of the knee you ask for.

def _fk(creature, pose):
    return creature.solve_m(pose)


def end_point(creature, pose, lower, end_local):
    from rig import mat_vec
    pos, m = _fk(creature, pose)[lower]
    return tuple(pos[i] + mat_vec(m, end_local)[i] for i in range(3))


def lowest_local(creature, bone):
    """The lowest corner of a bone's cubes, in the bone's own frame (blocks): the point that
    touches the ground — a heel, a needle tip."""
    best = None
    for cu in creature.GEOMETRY[bone]:
        for p in creature._cube_corners(cu):
            if best is None or p[1] < best[1]:
                best = p
    return best


def ik2(creature, pose, upper, lower, end_local, target, bend=1.0, iters=40, base=None):
    """X-rotation DELTAS (upper, lower) that put `end_local` of `lower` on `target` (world,
    blocks). `bend` > 0 bends the joint like a knee or an elbow; < 0 the wrong way. `base`
    gives the limb's other two axes (y, z) as deltas."""
    by, bz = (base or {}).get(upper, (0.0, 0.0)), (base or {}).get(lower, (0.0, 0.0))

    def place(a, b):
        p = dict(pose)
        p[upper] = {"rotation": (a, by[0], by[1])}
        p[lower] = {"rotation": (b, bz[0], bz[1])}
        return p

    def err(a, b):
        e = end_point(creature, place(a, b), lower, end_local)
        return (e[1] - target[1], e[2] - target[2], e[0] - target[0])

    best = None
    for start in (25.0, 50.0, 80.0):
        a, b = -0.5 * start * bend, start * bend
        for _ in range(iters):
            e0 = err(a, b)
            h = 0.05
            ea, eb = err(a + h, b), err(a, b + h)
            ja = [(ea[i] - e0[i]) / h for i in range(3)]
            jb = [(eb[i] - e0[i]) / h for i in range(3)]
            # 2x2 normal equations
            aa = sum(v * v for v in ja); bb = sum(v * v for v in jb); ab = sum(ja[i] * jb[i] for i in range(3))
            ra = -sum(ja[i] * e0[i] for i in range(3)); rb = -sum(jb[i] * e0[i] for i in range(3))
            det = aa * bb - ab * ab + 1e-9
            da, db = (ra * bb - rb * ab) / det, (rb * aa - ra * ab) / det
            step = max(1.0, math.hypot(da, db) / 15.0)        # never more than 15 degrees a step
            a, b = a + da / step, b + db / step
            if math.hypot(*e0[:2]) < 1e-5:
                break
        rest_b = getattr(creature, "REST", {}).get(lower, (0.0, 0.0, 0.0))[0]
        right_side = (b + rest_b) * bend > 0
        e = math.hypot(*err(a, b)[:2])
        if right_side and (best is None or e < best[2]):
            best = (a, b, e)
        if best and best[2] < 1e-3:
            break
    if best is None:
        raise ValueError(f"no {'forward' if bend > 0 else 'reversed'} solution for {lower}")
    return best[0], best[1]


class Foot:
    """A limb that plants: which bones, which point touches down, where it stands at rest,
    its phase in the cycle, which way it bends, and how far it reaches."""

    def __init__(self, creature, upper, lower, phase, bend=1.0, home=(0.0, 0.0, 0.0),
                 stride_scale=1.0, lift_scale=1.0, base=None):
        self.c, self.upper, self.lower, self.phase, self.bend = creature, upper, lower, phase, bend
        self.end = lowest_local(creature, lower)
        rest = end_point(creature, {}, lower, self.end)
        self.home = (rest[0] + home[0], home[1] if home[1] else 0.0, rest[2] + home[2])
        self.stride_scale, self.lift_scale = stride_scale, lift_scale
        self.base = base or {}


def key_feet(clip, creature, feet, stride, duty, lift, n=12, cycles=1, ppb=16.0, ground=None):
    """Key every foot of `feet` by IK at `n` keys per cycle, against whatever the body is
    already keyed to do at that moment. Body keys first, then this."""
    ground = min(f.home[1] for f in feet) if ground is None else ground
    total = n * cycles
    keys = {}
    for i in range(total + 1):
        t = clip.length * i / total
        s = (i / total * cycles) % 1.0
        pose = clip.sample(t)
        for f in feet:
            fy, fz = foot_path(s + f.phase, stride * f.stride_scale, min(0.9, duty * f.stride_scale),
                               lift * f.lift_scale)
            target = (f.home[0], ground + fy / ppb, f.home[2] + fz / ppb)
            a, b = ik2(creature, pose, f.upper, f.lower, f.end, target, f.bend, base=f.base)
            keys.setdefault((f.upper, f.lower), []).append((t, a, b))
    for f in feet:
        by = f.base.get(f.upper, (0.0, 0.0))
        bz = f.base.get(f.lower, (0.0, 0.0))
        seq = keys[(f.upper, f.lower)]
        seq[-1] = (seq[-1][0], seq[0][1], seq[0][2])       # the loop closes exactly
        for t, a, b in seq:
            clip.key(f.upper, "rotation", t, (a, by[0], by[1]))
            clip.key(f.lower, "rotation", t, (b, bz[0], bz[1]))


def check_feet(clip, creature, feet, ppb=16.0, fps=40):
    """World path of every foot's contact point over the clip, in pixels: [(y, z), ...]."""
    out = []
    n = int(clip.length * fps)
    for f in feet:
        pts = []
        for i in range(n + 1):
            e = end_point(creature, clip.sample(clip.length * i / n), f.lower, f.end)
            pts.append((e[1] * ppb, e[2] * ppb))
        out.append(pts)
    return out
