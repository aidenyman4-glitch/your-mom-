"""Original audio for the pack. Every sound here is synthesised from scratch.

Until now every one of the thirteen sound events pointed at a pitched-down vanilla file —
warden heartbeats at 0.42, ghast screams at 0.3. That works, and players recognise it
instantly, which is the problem: a pitched warden is a warden, and the fear belongs to the
warden. These are the project's own.

Everything is built from four primitives — additive partials, spectrally shaped noise,
phase-accumulated glissandi and FFT convolution reverb — because filters you can see the
spectrum of are easier to make frightening on purpose than filters you tune by ear.

Positional sounds are MONO: Minecraft will not attenuate a stereo file with distance, so a
stereo footstep is as loud across the valley as it is underfoot. Only the music is stereo.

    python3 tools/audio.py            # writes resourcepack/assets/sunman/sounds/**.ogg
"""
import math
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 44100
OUT = Path(__file__).resolve().parent.parent / "resourcepack" / "assets" / "sunman" / "sounds"


# ---------------------------------------------------------------- primitives

def t(dur):
    return np.arange(int(SR * dur), dtype=np.float64) / SR


def sine(freq, dur, phase=0.0):
    """freq may be a scalar or a per-sample array — phase is accumulated, so a swept
    frequency stays continuous instead of clicking at every block boundary."""
    n = int(SR * dur)
    f = np.full(n, freq, dtype=np.float64) if np.isscalar(freq) else freq[:n]
    return np.sin(2 * np.pi * np.cumsum(f) / SR + phase)


def shaped_noise(dur, curve, rng, seed_scale=1.0):
    """White noise multiplied by `curve(frequency)` in the spectral domain. Exact control
    over a band without writing a filter.

    `dur` is seconds as a float, or a sample count as an int — segments cut from an
    existing buffer need the exact count, and round-tripping through seconds loses a
    sample often enough to break the add.
    """
    n = dur if isinstance(dur, (int, np.integer)) else int(SR * dur)
    x = rng.normal(0.0, seed_scale, n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    return np.fft.irfft(X * curve(f), n)


def band(lo, hi, slope=2.0):
    def curve(f):
        with np.errstate(divide="ignore", invalid="ignore"):
            hp = 1.0 / (1.0 + (lo / np.maximum(f, 1e-6)) ** slope)
            lp = 1.0 / (1.0 + (np.maximum(f, 1e-6) / hi) ** slope)
        return hp * lp
    return curve


def reverb(x, dur=2.6, pre=0.02, mix=0.42, tone=2600.0, rng=None):
    """FFT convolution with an exponentially decaying noise impulse. A long tail is most of
    why a sound reads as enormous: the body of a 73 block creature is mostly its room."""
    rng = rng or np.random.default_rng(5)
    n = int(SR * dur)
    ir = rng.normal(0, 1, n) * np.exp(-np.arange(n) / (SR * dur * 0.34))
    ir = np.fft.irfft(np.fft.rfft(ir) * band(26.0, tone)(np.fft.rfftfreq(n, 1 / SR)), n)
    ir[:int(SR * pre)] = 0.0
    ir /= np.abs(ir).max() + 1e-9
    wet = np.fft.irfft(np.fft.rfft(x, len(x) + n) * np.fft.rfft(ir, len(x) + n))[:len(x)]
    wet /= np.abs(wet).max() + 1e-9
    return (1 - mix) * x + mix * wet


def wobble(x, depth=0.0016, rate=0.7, rng=None):
    """Tape speed drift. Pitch that will not sit still is unpleasant in a way listeners
    rarely locate, which is exactly the point."""
    n = len(x)
    rng = rng or np.random.default_rng(3)
    lfo = (np.sin(2 * np.pi * rate * np.arange(n) / SR)
           + 0.4 * np.sin(2 * np.pi * rate * 2.7 * np.arange(n) / SR + 1.3))
    idx = np.clip(np.arange(n) + lfo * depth * SR, 0, n - 1)
    return np.interp(idx, np.arange(n), x)


def fade(x, inn=0.01, out=0.08):
    a, b = int(SR * inn), int(SR * out)
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b)
    return x


def norm(x, peak=0.92):
    return x / (np.abs(x).max() + 1e-9) * peak


def soft(x, drive=1.4):
    return np.tanh(x * drive) / math.tanh(drive)


def write(rel, x, stereo=False):
    p = OUT / (rel + ".ogg")
    p.parent.mkdir(parents=True, exist_ok=True)
    data = x.T if stereo else x
    sf.write(p, np.clip(data, -1, 1).astype(np.float32), SR,
             format="OGG", subtype="VORBIS")
    frames = len(x[0]) if stereo else len(x)
    print(f"  {rel + '.ogg':30} {frames / SR:5.1f}s  {p.stat().st_size // 1024:4d} KB"
          f"  {'stereo' if stereo else 'mono'}")
    return p


# ====================================================================== SUN MAN

def heartbeat(rng):
    """Not a heartbeat you could have. 46 BPM, and the second beat lands late every time,
    so the rhythm never settles into something you can predict."""
    dur = 2.1
    out = np.zeros(int(SR * dur))
    for at, amp, f0, f1 in ((0.00, 1.00, 62.0, 29.0), (0.37, 0.62, 54.0, 26.0)):
        n = int(SR * 0.9)
        k = np.arange(n) / n
        f = f0 + (f1 - f0) * k ** 0.45
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-np.arange(n) / (SR * 0.17))
        thud = shaped_noise(0.9, band(30.0, 190.0), rng) * np.exp(-np.arange(n) / (SR * 0.05))
        seg = (body * 0.9 + thud * 0.5) * amp
        i = int(SR * at)
        out[i:i + n] += seg[:len(out) - i]
    return norm(fade(reverb(soft(out, 1.8), dur=2.2, mix=0.34, tone=900.0, rng=rng)))


def drone(rng):
    """The presence bed, 14 seconds and loopable. Two of the partials sit 0.4 Hz apart so
    the cluster beats slowly against itself — the listener hears the room breathing."""
    dur = 14.0
    tt = t(dur)
    x = np.zeros_like(tt)
    for f, a in ((36.70, 1.00), (37.12, 0.85), (55.00, 0.42), (73.42, 0.30),
                 (110.1, 0.16), (146.8, 0.09)):
        swell = 0.6 + 0.4 * np.sin(2 * np.pi * (0.031 + a * 0.013) * tt + f)
        x += np.sin(2 * np.pi * f * tt) * a * swell
    shimmer = shaped_noise(dur, band(2200.0, 4200.0, 3.0), rng)
    x += shimmer * 0.06 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.047 * tt))
    x = wobble(x, depth=0.0022, rate=0.11, rng=rng)
    return norm(fade(reverb(x, dur=3.4, mix=0.5, tone=1800.0, rng=rng), inn=1.2, out=1.2), 0.8)


def notice(rng):
    """The moment it turns. A reversed swell into a glissando that falls off the bottom of
    what a speaker can reproduce, so the end of it is felt rather than heard."""
    dur = 4.2
    n = int(SR * dur)
    rise = shaped_noise(1.5, band(140.0, 2600.0), rng)
    rise *= np.linspace(0, 1, len(rise)) ** 2.6
    out = np.zeros(n)
    out[:len(rise)] += rise * 0.5

    hit = int(SR * 1.42)
    m = n - hit
    k = np.arange(m) / m
    f = 186.0 * np.exp(-3.1 * k) + 26.0
    g = np.zeros(m)
    for mult, amp in ((1.0, 1.0), (1.47, 0.42), (2.09, 0.24), (3.31, 0.12)):
        g += np.sin(2 * np.pi * np.cumsum(f * mult) / SR) * amp
    g *= np.exp(-np.arange(m) / (SR * 0.95))
    out[hit:] += g * 0.8
    out[hit:] += shaped_noise(m, band(60.0, 700.0), rng) * np.exp(
        -np.arange(m) / (SR * 0.12)) * 0.6
    return norm(fade(reverb(soft(out, 1.6), dur=3.0, mix=0.46, tone=1500.0, rng=rng)))


def toll(rng):
    """A bell, struck wrong. Real bell partials, detuned just enough that the ring sours."""
    dur = 7.0
    tt = t(dur)
    x = np.zeros_like(tt)
    base = 57.3
    for ratio, amp, dec in ((0.50, 0.9, 5.4), (1.00, 1.0, 4.6), (1.183, 0.7, 3.2),
                            (1.506, 0.55, 2.6), (2.00, 0.42, 2.0), (2.514, 0.3, 1.5),
                            (2.662, 0.26, 1.3), (3.011, 0.2, 1.0), (4.166, 0.12, 0.7)):
        f = base * ratio * (1.0 + rng.normal(0, 0.0016))
        x += np.sin(2 * np.pi * f * tt) * amp * np.exp(-tt / dec)
    strike = shaped_noise(0.25, band(400.0, 7000.0), rng)
    x[:len(strike)] += strike * np.exp(-np.arange(len(strike)) / (SR * 0.02)) * 0.7
    return norm(fade(reverb(x, dur=4.0, mix=0.44, tone=3200.0, rng=rng), out=1.0))


def step(rng):
    """One footfall of something that weighs what this weighs: the impact, the ground
    answering it a beat later, and grit coming off the surface."""
    dur = 2.4
    n = int(SR * dur)
    k = np.arange(n) / n
    f = 46.0 * np.exp(-9.0 * k) + 23.0
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-np.arange(n) / (SR * 0.26))
    crack = shaped_noise(0.4, band(120.0, 3400.0), rng) * np.exp(
        -np.arange(int(SR * 0.4)) / (SR * 0.035))
    out = body * 1.0
    out[:len(crack)] += crack * 0.45
    grit = shaped_noise(dur, band(900.0, 6000.0), rng) * 0.08
    grit *= np.exp(-np.arange(n) / (SR * 0.5)) * (rng.random(n) < 0.02)
    out += np.convolve(grit, np.ones(60) / 60, mode="same") * 3.0
    return norm(fade(reverb(soft(out, 1.5), dur=2.4, mix=0.38, tone=1100.0, rng=rng)))


def gaze(rng):
    """What looking at it costs. A sine climbing out of the audible middle into the part of
    the range that hurts, over a sub that arrives late."""
    dur = 4.6
    n = int(SR * dur)
    k = np.arange(n) / n
    ring = np.sin(2 * np.pi * np.cumsum(1850.0 * np.exp(1.12 * k)) / SR)
    ring *= np.clip(k * 4.0, 0, 1) ** 2 * np.clip((1 - k) * 6.0, 0, 1)
    sub = np.sin(2 * np.pi * np.cumsum(np.full(n, 31.0)) / SR) * np.clip((k - 0.25) * 2, 0, 1)
    hiss = shaped_noise(dur, band(3000.0, 9000.0), rng) * 0.10 * k
    x = ring * 0.34 + sub * 0.8 + hiss
    x = wobble(x, depth=0.0009, rate=5.2, rng=rng)
    return norm(fade(reverb(x, dur=1.8, mix=0.3, tone=5200.0, rng=rng), out=0.25))


def harvest(rng):
    """Day thirty. A cluster that swells for eight seconds and resolves nowhere, with the
    vowel formants of a crowd somewhere inside the noise."""
    dur = 11.0
    tt = t(dur)
    swell = np.clip(tt / 8.0, 0, 1) ** 1.6 * np.clip((dur - tt) / 2.5, 0, 1)
    x = np.zeros_like(tt)
    for f, a in ((41.2, 1.0), (43.6, 0.8), (61.7, 0.5), (82.4, 0.34), (98.0, 0.2)):
        x += np.sin(2 * np.pi * f * tt * (1 + 0.0004 * np.sin(2 * np.pi * 0.09 * tt))) * a
    voices = np.zeros_like(tt)
    for f0 in (320.0, 640.0, 2400.0):
        voices += shaped_noise(dur, band(f0 * 0.92, f0 * 1.09, 6.0), rng)
    x += voices * 0.22 * np.clip((tt - 3.0) / 5.0, 0, 1)
    x *= swell
    return norm(fade(reverb(x, dur=4.6, mix=0.55, tone=2600.0, rng=rng), inn=0.5, out=1.6), 0.85)


# ====================================================================== LOCUST

def locust_click(rng):
    """Chitin. Irregular spacing, because anything evenly spaced reads as a machine and a
    machine is not frightening."""
    dur = 1.4
    out = np.zeros(int(SR * dur))
    at = 0.03
    while at < dur - 0.12:
        n = int(SR * 0.05)
        c = shaped_noise(0.05, band(1400.0, 5200.0, 3.0), rng)
        c *= np.exp(-np.arange(n) / (SR * 0.0045))
        i = int(SR * at)
        out[i:i + n] += c[:len(out) - i] * rng.uniform(0.5, 1.0)
        at += rng.uniform(0.055, 0.22)
    return norm(fade(reverb(out, dur=0.7, mix=0.22, tone=6000.0, rng=rng)))


def locust_shriek(rng):
    """The wake-up inside nine blocks. An insect buzz with a throat behind it, swept up and
    cut off mid-breath rather than allowed to finish."""
    dur = 2.4
    n = int(SR * dur)
    k = np.arange(n) / n
    f = 168.0 * (1 + 1.9 * k ** 1.5)
    buzz = np.zeros(n)
    for h, a in ((1, 1.0), (2, 0.6), (3, 0.42), (5, 0.24), (7, 0.14), (11, 0.08)):
        buzz += np.sin(2 * np.pi * np.cumsum(f * h) / SR) * a
    buzz *= 0.55 + 0.45 * np.sign(np.sin(2 * np.pi * 47.0 * np.arange(n) / SR))
    throat = np.zeros(n)
    for fo in (780.0, 1500.0, 3100.0):
        throat += shaped_noise(dur, band(fo * 0.85, fo * 1.2, 5.0), rng)
    x = buzz * 0.5 + throat * 0.5 * np.clip(k * 3, 0, 1)
    x *= np.clip(k * 12, 0, 1) * np.clip((1 - k) * 9, 0, 1) ** 0.5
    x[int(SR * 2.22):] *= np.linspace(1, 0, n - int(SR * 2.22)) ** 3     # cut mid-breath
    return norm(fade(reverb(soft(x, 2.0), dur=1.6, mix=0.33, tone=4200.0, rng=rng), out=0.04))


def locust_step(rng):
    dur = 0.55
    out = np.zeros(int(SR * dur))
    for at, amp in ((0.0, 1.0), (0.06, 0.45)):
        n = int(SR * 0.18)
        c = shaped_noise(0.18, band(600.0, 3800.0), rng) * np.exp(
            -np.arange(n) / (SR * 0.012))
        c += np.sin(2 * np.pi * np.cumsum(np.full(n, 96.0)) / SR) * np.exp(
            -np.arange(n) / (SR * 0.03)) * 0.5
        i = int(SR * at)
        out[i:i + n] += c[:len(out) - i] * amp
    return norm(fade(reverb(out, dur=0.6, mix=0.2, tone=4000.0, rng=rng)))


# ================================================================= DARK WALKER
# The Sun Man weighs what 73 blocks weighs and its footfall is a 28 Hz earthquake. This one
# is four metres of leg and almost no body, so none of its sounds have any low end at all —
# you hear it because the night is silent, not because it is loud. That contrast is the
# whole point of putting them in the same world.

def walker_step(rng):
    """One stilt coming down on a road. Dry, woody, and far too slow to be a stride — then
    the dust it lifts, a beat behind."""
    dur = 2.2
    n = int(SR * dur)
    out = np.zeros(n)
    knock = shaped_noise(0.22, band(320.0, 4200.0), rng)
    knock *= np.exp(-np.arange(int(SR * 0.22)) / (SR * 0.009))
    out[:len(knock)] += knock * 0.85
    # a short woody resonance, not a boom: two close modes that beat against each other
    for f, a, d in ((186.0, 0.5, 0.11), (241.0, 0.34, 0.08), (402.0, 0.2, 0.05)):
        out += np.sin(2 * np.pi * f * np.arange(n) / SR) * a * np.exp(-np.arange(n) / (SR * d))
    dust = shaped_noise(dur, band(1100.0, 5200.0), rng) * 0.05
    dust *= np.clip((np.arange(n) / SR - 0.06) * 6, 0, 1) * np.exp(-np.arange(n) / (SR * 0.3))
    out += dust
    return norm(fade(reverb(out, dur=2.6, mix=0.42, tone=4200.0, rng=rng)))


def walker_drift(rng):
    """What standing near it sounds like. A thin tone that will not hold a pitch, with the
    bottom of the spectrum simply missing — the absence is what makes it uncomfortable."""
    dur = 9.0
    tt = t(dur)
    x = np.zeros_like(tt)
    for f, a in ((494.0, 1.0), (497.6, 0.8), (742.0, 0.4), (988.0, 0.22), (1483.0, 0.1)):
        x += np.sin(2 * np.pi * f * tt) * a * (0.55 + 0.45 * np.sin(2 * np.pi * 0.07 * tt + f))
    x += shaped_noise(dur, band(2600.0, 6400.0, 3.0), rng) * 0.12
    x = wobble(x, depth=0.0042, rate=0.19, rng=rng)
    return norm(fade(reverb(x, dur=3.2, mix=0.5, tone=5200.0, rng=rng), inn=1.0, out=1.0), 0.72)


def walker_notice(rng):
    """The eyes find you. An intake of breath that nothing with that body could take, and a
    hollow tone climbing behind it that stops dead rather than resolving."""
    dur = 3.0
    n = int(SR * dur)
    k = np.arange(n) / n
    gasp = shaped_noise(1.1, band(500.0, 5000.0), rng)
    gasp *= np.sin(np.pi * np.linspace(0, 1, len(gasp))) ** 2.2
    out = np.zeros(n)
    out[:len(gasp)] += gasp * 0.55
    tone = np.sin(2 * np.pi * np.cumsum(228.0 * (1 + 1.25 * k ** 1.7)) / SR)
    tone += 0.4 * np.sin(2 * np.pi * np.cumsum(228.0 * 2.51 * (1 + 1.25 * k ** 1.7)) / SR)
    out += tone * np.clip(k * 2.4, 0, 1) * 0.42
    cut = int(SR * 2.72)
    out[cut:] *= np.linspace(1, 0, n - cut) ** 4
    return norm(fade(reverb(out, dur=2.2, mix=0.38, tone=4600.0, rng=rng), out=0.03))


def walker_reach(rng):
    """Six tendrils moving at once. Dry fibre, no wet in it anywhere."""
    dur = 1.8
    n = int(SR * dur)
    out = np.zeros(n)
    for _ in range(6):                       # one pass per arm, each on its own envelope
        at = rng.uniform(0.0, 0.5)
        ln = rng.uniform(0.7, 1.1)
        m = int(SR * ln)
        seg = shaped_noise(m, band(1800.0, 7000.0, 2.5), rng)
        seg *= np.sin(np.pi * np.arange(m) / m) ** 1.8
        seg *= 0.6 + 0.4 * np.sin(2 * np.pi * rng.uniform(14, 26) * np.arange(m) / SR)
        i0 = int(SR * at)
        out[i0:i0 + m] += seg[:n - i0] * rng.uniform(0.4, 0.9)
    return norm(fade(reverb(out, dur=1.4, mix=0.3, tone=6000.0, rng=rng)), 0.8)


# ====================================================================== MUSIC

def dread_music(rng):
    """The bed that replaces the overworld music in the snow biomes. 74 seconds, stereo.

    Eight notes in seventy four seconds. The interval it keeps returning to is a minor
    second — the one interval that will not resolve — and the whole thing is run through
    tape wobble so nothing is ever quite in tune with the take before it.
    """
    dur = 74.0
    tt = t(dur)
    n = len(tt)
    left = np.zeros(n)
    right = np.zeros(n)

    notes = [(0.0, 55.00), (9.5, 58.27), (19.0, 55.00), (27.0, 51.91),
             (37.5, 58.27), (46.0, 55.00), (55.0, 49.00), (64.0, 55.00)]
    for at, f in notes:
        ln = min(13.0, dur - at)
        m = int(SR * ln)
        k = np.arange(m) / m
        a = np.sin(np.pi * np.clip(k, 0, 1)) ** 1.3
        v = np.zeros(m)
        for h, amp in ((1, 1.0), (2, 0.5), (3, 0.3), (4, 0.18), (6, 0.1), (8, 0.05)):
            det = 1.0 + rng.normal(0, 0.0012)
            v += np.sin(2 * np.pi * f * h * det * np.arange(m) / SR) * amp
        v *= a
        i = int(SR * at)
        left[i:i + m] += v[:n - i] * 0.55
        right[i:i + m] += np.roll(v, 380)[:n - i] * 0.55          # a little width

    # a bell, three times, distant
    bell = toll(np.random.default_rng(99)) * 0.22
    for at in (14.0, 41.0, 68.0):
        i = int(SR * at)
        seg = bell[:n - i]
        left[i:i + len(seg)] += seg * 0.8
        right[i:i + len(seg)] += seg * 0.6

    air = shaped_noise(dur, band(1800.0, 7000.0, 2.0), rng) * 0.035
    hum = np.sin(2 * np.pi * 27.5 * tt) * 0.07
    left += air + hum
    right += np.roll(air, 1100) + hum

    left = wobble(left, depth=0.0030, rate=0.09, rng=rng)
    right = wobble(right, depth=0.0032, rate=0.077, rng=rng)
    st = np.stack([fade(norm(reverb(left, dur=5.0, mix=0.52, tone=2200.0, rng=rng), 0.78),
                        inn=2.0, out=4.0),
                   fade(norm(reverb(right, dur=5.0, mix=0.52, tone=2200.0, rng=rng), 0.78),
                        inn=2.0, out=4.0)])
    return st


SOUNDS = {
    "sun_man/heartbeat": heartbeat,
    "sun_man/drone": drone,
    "sun_man/notice": notice,
    "sun_man/toll": toll,
    "sun_man/step": step,
    "sun_man/gaze": gaze,
    "sun_man/harvest": harvest,
    "locust/click": locust_click,
    "locust/shriek": locust_shriek,
    "locust/step": locust_step,
    "dark_walker/step": walker_step,
    "dark_walker/drift": walker_drift,
    "dark_walker/notice": walker_notice,
    "dark_walker/reach": walker_reach,
}


if __name__ == "__main__":
    print("synthesising:")
    for i, (name, fn) in enumerate(SOUNDS.items()):
        write(name, fn(np.random.default_rng(1000 + i * 7)))
    write("music/dread", dread_music(np.random.default_rng(4242)), stereo=True)
