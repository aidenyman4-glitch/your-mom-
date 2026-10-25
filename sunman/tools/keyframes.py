"""Keyframed clips, evaluated exactly the way Blockbench plays them.

The clips used to be Python pose functions that only the (lost) datapack baker and the GIF
renderer could see. Open a .bbmodel and the Animate tab was empty. Now every clip is a set of
sparse keyframes — the thing an animator would actually key in Blockbench — and the same keys
are written into the .bbmodel, exported to Bedrock/GeckoLib `.animation.json`, and sampled
here for the renderers and the datapack.

`Clip.sample` is a port of Blockbench 5.1's `BoneAnimator.interpolate`, so what the tools
bake is what the Animate tab shows:

  * linear between two linear keys, `step` holds the key before
  * otherwise uniform Catmull-Rom (three.js `SplineCurve`, tension 0.5) through the key before
    the segment, the segment's two keys and the key after it
  * on a looping clip with three or more keys the missing neighbours wrap: before the first
    key it uses the second-to-last, after the last it uses the second. That is why every
    looping track here starts and ends on the same value — the loop is then seamless.

Units: rotation in degrees in the rig's own right-handed convention (+X = the creature's
left, +Y up, +Z forward; Euler order Z·Y·X, added on top of the bone's rest rotation exactly
as Blockbench adds keyframes to a group's rotation). Position in BLOCKS, converted to model
pixels only on export. Blockbench files older than format 5.0 — and Bedrock animation JSON —
store rotation X/Y and position X negated; `to_bbmodel` writes that convention so the file
opens identically in Blockbench 4.x and 5.x.
"""
import math
import uuid

LINEAR, CATMULLROM, STEP = "linear", "catmullrom", "step"
CHANNELS = ("rotation", "position", "scale")
_EPS = 1.0 / 1200.0


def _catmull(t, p0, p1, p2, p3):
    v0 = (p2 - p0) * 0.5
    v1 = (p3 - p1) * 0.5
    t2 = t * t
    t3 = t * t2
    return (2 * p1 - 2 * p2 + v0 + v1) * t3 + (-3 * p1 + 3 * p2 - 2 * v0 - v1) * t2 + v0 * t + p1


class Key:
    __slots__ = ("time", "value", "interp")

    def __init__(self, time, value, interp=CATMULLROM):
        self.time = float(time)
        self.value = tuple(float(v) for v in value)
        self.interp = interp

    def __repr__(self):
        return f"Key({self.time:.3f}, {self.value}, {self.interp})"


class Clip:
    """One animation. `loop` is Blockbench's: "loop", "once" or "hold"."""

    def __init__(self, name, length, loop="loop", note="", snapping=20, override=False):
        self.name = name
        self.length = float(length)
        self.loop = loop
        self.note = note
        self.snapping = snapping
        self.override = override
        self.tracks = {}                      # (bone, channel) -> [Key], kept sorted

    # ------------------------------------------------------------- authoring
    def key(self, bone, channel, time, value, interp=CATMULLROM):
        assert channel in CHANNELS, channel
        t = round(float(time), 4)
        assert -1e-9 <= t <= self.length + 1e-9, f"{self.name}: key at {t} outside 0..{self.length}"
        track = self.tracks.setdefault((bone, channel), [])
        track[:] = [k for k in track if abs(k.time - t) > 1e-6]   # re-keying replaces
        track.append(Key(t, value, interp))
        track.sort(key=lambda k: k.time)
        return self

    def keys(self, bone, channel, seq, interp=CATMULLROM):
        """seq of (time, value) or (time, value, interp)."""
        for item in seq:
            if len(item) == 3:
                self.key(bone, channel, item[0], item[1], item[2])
            else:
                self.key(bone, channel, item[0], item[1], interp)
        return self

    def cycle(self, bone, channel, values, start=0.0, end=None, interp=CATMULLROM, close=True):
        """Evenly spaced keys over [start, end]; with `close` the first value is repeated at
        `end`, which is what makes a looping track seamless (see the module docstring)."""
        end = self.length if end is None else end
        n = len(values)
        span = end - start
        for i, v in enumerate(values):
            self.key(bone, channel, start + span * i / n, v, interp)
        if close:
            self.key(bone, channel, end, values[0], interp)
        return self

    def bones(self):
        return sorted({b for b, _ in self.tracks})

    # ------------------------------------------------------------- evaluation
    def _channel(self, track, t):
        before = after = None
        for k in track:
            if k.time < t:
                if before is None or k.time > before.time:
                    before = k
            elif after is None or k.time < after.time:
                after = k
        if before is not None and abs(before.time - t) < _EPS:
            return before.value
        if after is not None and abs(after.time - t) < _EPS:
            return after.value
        if before is not None and before.interp == STEP:
            return before.value
        if before is not None and after is None:
            return before.value
        if after is not None and before is None:
            return after.value
        a = (t - before.time) / (after.time - before.time)
        if before.interp == LINEAR and after.interp in (LINEAR, STEP):
            return tuple(b + (c - b) * a for b, c in zip(before.value, after.value))
        i = track.index(before)
        prev = track[i - 1] if i >= 1 else None
        nxt = track[i + 2] if i + 2 < len(track) else None
        if self.loop == "loop" and len(track) >= 3:
            prev = prev or track[-2]
            nxt = nxt or track[1]
        p0 = prev.value if prev is not None else before.value
        p3 = nxt.value if nxt is not None else after.value
        return tuple(_catmull(a, p0[j], before.value[j], after.value[j], p3[j]) for j in range(3))

    def sample(self, t):
        """Pose at time `t` seconds: {bone: {"rotation": .., "position": .., "scale": ..}}."""
        if self.loop == "loop" and self.length > 0 and t > self.length:
            t = t % self.length          # exactly `length` stays the last key, as in Blockbench
        else:
            t = min(max(t, 0.0), self.length)
        pose = {}
        for (bone, channel), track in self.tracks.items():
            pose.setdefault(bone, {})[channel] = self._channel(track, t)
        return pose

    def at(self, p):
        """Pose at normalised phase 0..1 — the signature the renderers expect."""
        return self.sample(p * self.length)

    def max_step(self, bone, channel, fps=20):
        """Largest per-tick change on one track; used to catch pops at loop seams."""
        n = max(2, int(round(self.length * fps)))
        prev, worst = None, 0.0
        for i in range(n + 1):
            v = self.sample(i * self.length / n).get(bone, {}).get(channel)
            if v is None:
                continue
            if prev is not None:
                worst = max(worst, max(abs(a - b) for a, b in zip(v, prev)))
            prev = v
        return worst

    # ------------------------------------------------------------- export
    def to_bbmodel(self, group_uuid, px_per_block):
        """Blockbench `animations[]` entry, in the pre-5.0 (Bedrock) value convention."""
        animators = {}
        for bone in self.bones():
            kfs = []
            for channel in CHANNELS:
                for k in self.tracks.get((bone, channel), []):
                    x, y, z = k.value
                    if channel == "rotation":
                        x, y = -x, -y
                    elif channel == "position":
                        x, y, z = -x * px_per_block, y * px_per_block, z * px_per_block
                    kfs.append({
                        "channel": channel,
                        "data_points": [{"x": _num(x), "y": _num(y), "z": _num(z)}],
                        "uuid": _uid(self.name, bone, channel, k.time),
                        "time": k.time,
                        "color": -1,
                        "interpolation": k.interp,
                    })
            animators[group_uuid[bone]] = {"name": bone, "type": "bone", "keyframes": kfs}
        return {
            "uuid": _uid(self.name), "name": self.name, "loop": self.loop,
            "override": self.override, "length": self.length, "snapping": self.snapping,
            "selected": False, "anim_time_update": "", "blend_weight": "",
            "start_delay": "", "loop_delay": "", "animators": animators,
        }

    def summary(self):
        n = sum(len(v) for v in self.tracks.values())
        return f"{self.name:38s} {self.loop:5s} {self.length:5.2f}s {len(self.bones()):2d} bones {n:4d} keys"


def _num(v):
    v = round(v, 4)
    return 0.0 if v == 0 else v


def _uid(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_OID, "clip:" + ":".join(map(str, parts))))


# ----------------------------------------------------------------- authoring helpers

def wave(phase, amp=1.0, offset=0.0, rate=1.0):
    return amp * math.sin((phase * rate + offset) * math.tau)


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def lerp3(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def add3(*vs):
    return tuple(sum(v[i] for v in vs) for i in range(3))


def scale3(v, s):
    return tuple(c * s for c in v)


def shift(values, steps):
    """Rotate a cyclic value table — the same cycle, started `steps` keys later."""
    steps %= len(values)
    return values[steps:] + values[:steps]


def periodic(clip, bone, channel, fn, n=8, start=0.0, end=None, interp=CATMULLROM):
    """Key a cyclic channel by sampling `fn(phase)` at `n` evenly spaced phases over
    [start, end] (closing the loop). The sparse result is what an animator would key; the
    Catmull-Rom between the keys reconstructs the curve."""
    clip.cycle(bone, channel, [tuple(fn(i / n)) for i in range(n)], start, end, interp)
    return clip


def px(v, ppb=16.0):
    """Model pixels to blocks, for position keys authored in pixels."""
    return v / ppb
