#!/usr/bin/env python3
"""Runs the datapack's driving logic in a tiny mcfunction interpreter.

Only the parts that are pure scoreboard math are interpreted (scoreboard
operations, `execute if/unless score`, `execute store ... run scoreboard
players get`, `function`, `return`). Predicates are answered from a dict that
the test controls (that is how WASD input is "pressed"); world-touching
commands (particles, sounds, titles, entity data) are recorded, not executed.

This checks the vehicle actually behaves: throttle, boost, braking, reverse,
coasting, steering, the motion vector, fuel burn and the fuel-empty cutoff.

    python3 master-cycle/tools/sim_test.py
"""

import math
import re
import sys
from pathlib import Path

FN = Path(__file__).resolve().parent.parent / "datapack" / "data" / "mastercycle" / "function"


class Return(Exception):
    pass


class Sim:
    def __init__(self):
        self.scores = {}  # (holder, objective) -> int
        self.preds = set()  # predicate ids that are currently true
        self.stored = {}  # target path -> float
        self.log = []
        self.executor = None
        self.motion = [0.0, 0.0, 0.0]  # the cycle's Motion as the game left it
        self.wall = False
        self.pos = [0.0, 0.0]  # cycle x, z (ground level is y = 0)
        self.rider_yaw = 0.0  # where the rider is looking, degrees
        self.solid = set()  # (x, y, z) of blocks in #minecraft:blocks_motion

    def local_block(self, coords):
        """Block under a ^left ^up ^forward offset from the cycle, using its yaw."""
        lx, ly, lz = (float(c[1:] or 0) for c in coords)
        yaw = math.radians((self.get("cycle", "mc.yaw") or 0) / 100)
        fx, fz = -math.sin(yaw), math.cos(yaw)  # forward
        rx, rz = math.cos(yaw), math.sin(yaw)  # left
        x = self.pos[0] + fx * lz + rx * lx
        z = self.pos[1] + fz * lz + rz * lx
        return (math.floor(x), math.floor(ly), math.floor(z))

    def get(self, holder, obj):
        return self.scores.get((self.resolve(holder), obj))

    def set(self, holder, obj, v):
        v = int(v)
        v = (v + 2**31) % 2**32 - 2**31  # Java int overflow
        self.scores[(self.resolve(holder), obj)] = v

    def resolve(self, holder):
        if holder == "@s":
            return self.executor
        if holder.startswith("@e[") and "mc.this" in holder:
            return "cycle"
        return holder

    def run_function(self, name):
        path = FN / (name.split(":", 1)[1] + ".mcfunction")
        try:
            for line in path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    self.run(line)
        except Return:
            pass

    def run(self, cmd):
        t = cmd.split(" ")
        if t[0] == "function":
            if len(t) > 2:  # macro call: not needed for the physics path
                self.log.append(cmd)
                return
            return self.run_function(t[1])
        if t[0] == "return":
            if t[1] == "run":
                self.run(" ".join(t[2:]))
            raise Return
        if t[0] == "scoreboard" and t[1] == "players":
            op, holder, obj = t[2], t[3], t[4]
            if op == "set":
                self.set(holder, obj, int(t[5]))
            elif op == "add":
                self.set(holder, obj, (self.get(holder, obj) or 0) + int(t[5]))
            elif op == "remove":
                self.set(holder, obj, (self.get(holder, obj) or 0) - int(t[5]))
            elif op == "reset":
                self.scores.pop((self.resolve(holder), obj), None)
            elif op == "get":
                return self.get(holder, obj)
            elif op == "operation":
                a = self.get(holder, obj) or 0
                b = self.get(t[6], t[7])
                assert b is not None, f"unset score {t[6]} {t[7]} in: {cmd}"
                o = t[5]
                if o == "=":
                    r = b
                elif o == "+=":
                    r = a + b
                elif o == "-=":
                    r = a - b
                elif o == "*=":
                    r = a * b
                elif o == "/=":
                    r = a // b  # Minecraft uses floor division
                elif o == "%=":
                    r = a % b
                elif o == "<":
                    r = min(a, b)
                elif o == ">":
                    r = max(a, b)
                else:
                    raise NotImplementedError(o)
                self.set(holder, obj, r)
            return
        if t[0] == "execute":
            return self.execute(t[1:], cmd)
        if cmd == "data modify entity @s Motion set from storage mastercycle:tmp m":
            # the game moves the stand, then applies ground friction (0.6 * 0.91)
            self.motion = [self.stored.get("m[0]", 0) * 0.546, 0, self.stored.get("m[2]", 0) * 0.546]
            if self.wall:
                self.motion = [0.0, 0.0, 0.0]
            return
        if cmd == "data get entity @s Rotation[0] 100" and self.executor == "rider":
            return int(self.rider_yaw * 100)
        m = re.match(r"data get storage mastercycle:tmp m\[(\d)\] (\S+)", cmd)
        if m:
            return int(self.motion[int(m.group(1))] * float(m.group(2)))
        self.log.append(cmd)  # side effects we don't simulate

    def execute(self, t, cmd):
        i = 0
        store = None
        while i < len(t):
            k = t[i]
            if k == "run":
                v = self.run(" ".join(t[i + 1:]))
                if store is not None and store[0] == "score":
                    self.set(store[1], store[2], v or 0)
                elif store is not None:
                    self.stored[store[0]] = (v or 0) * store[1]
                return v
            if k in ("if", "unless"):
                kind = t[i + 1]
                if kind == "score":
                    a = self.get(t[i + 2], t[i + 3])
                    if t[i + 4] == "matches":
                        lo, _, hi = t[i + 5].partition("..")
                        if ".." not in t[i + 5]:
                            hi = lo
                        ok = a is not None and (lo == "" or a >= int(lo)) and (hi == "" or a <= int(hi))
                        i += 6
                    else:
                        b = self.get(t[i + 5], t[i + 6])
                        o = t[i + 4]
                        ok = a is not None and b is not None and {
                            "<": a < b, "<=": a <= b, "=": a == b, ">": a > b, ">=": a >= b}[o]
                        i += 7
                elif kind == "predicate":
                    ok = t[i + 2] in self.preds
                    i += 3
                elif kind == "entity":
                    ok = True
                    i += 3
                elif kind == "data":
                    ok = False
                    i += 4
                elif kind == "block":
                    ok = self.local_block(t[i + 2:i + 5]) in self.solid
                    assert t[i + 5] == "#minecraft:blocks_motion", cmd
                    i += 6
                else:
                    raise NotImplementedError(kind)
                if ok != (k == "if"):
                    return None
                continue
            if k == "store":
                # execute store result <storage|entity> <target> <path> <type> <scale>
                if t[i + 2] == "score":
                    store = ("score", t[i + 3], t[i + 4])
                    i += 5
                    continue
                store = (t[i + 4], float(t[i + 6]))
                i += 7
                continue
            if k == "on":
                if t[i + 1] == "passengers":
                    # the rider: run the rest as them, then restore
                    prev = self.executor
                    self.executor = "rider"
                    try:
                        return self.execute(t[i + 2:], cmd)
                    finally:
                        self.executor = prev
                i += 2
                continue
            if k in ("as", "at", "rotated", "positioned", "in", "anchored", "facing", "align"):
                skip = {"rotated": 3 if t[i + 1] == "as" else 3, "positioned": 2 if t[i + 1] != "as" else 3,
                        "as": 2, "at": 2, "in": 2, "anchored": 2, "align": 2, "facing": 3}[k]
                if k == "positioned" and t[i + 1].startswith(("^", "~")) or k == "positioned" and re.match(r"-?\d", t[i + 1]):
                    skip = 4
                i += skip
                continue
            raise NotImplementedError(f"execute {k}: {cmd}")


def make_sim():
    s = Sim()
    s.run_function("mastercycle:load")
    s.executor = "cycle"
    for obj, v in (("mc.fuel", 6000), ("mc.speed", 0), ("mc.yaw", 0), ("mc.jcd", 0), ("mc.hum", 0), ("mc.boost", 0)):
        s.set("cycle", obj, v)
    return s


def tick(s, keys=(), on_ground=True):
    """One game tick of a ridden cycle with the given keys held."""
    s.preds = {f"mastercycle:input/{k}" for k in keys}
    if on_ground:
        s.preds.add("mastercycle:on_ground")
    s.executor = "cycle"
    for k in ("#fwd", "#back", "#left", "#right", "#jump", "#sprint"):
        s.set(k, "mc.tmp", 0)
    # read_input runs as the rider; the predicates above answer for them
    s.executor = "rider"
    s.run_function("mastercycle:drive/read_input")
    s.executor = "cycle"
    s.stored.clear()
    s.run_function("mastercycle:drive/physics")
    s.pos[0] += s.stored.get("m[0]", 0)
    s.pos[1] += s.stored.get("m[2]", 0)
    return s


def speed(s):
    return s.get("cycle", "mc.speed")



def ride_tick(s, keys=(), on_ground=True, ridden=True, t20=1, t40=1):
    """One full game tick of cycle/tick: hitbox, ride detection, driving,
    effects, HUD. Predicates answer for the cycle and its rider."""
    s.preds = {f"mastercycle:input/{k}" for k in keys}
    if on_ground:
        s.preds.add("mastercycle:on_ground")
    if ridden:
        s.preds.add("mastercycle:has_rider")
    s.set("#t20", "mc.tmp", t20)
    s.set("#t40", "mc.tmp", t40)
    s.executor = "cycle"
    s.stored.clear()
    s.run_function("mastercycle:cycle/tick")
    return s


def count(s, needle):
    return sum(needle in line for line in s.log)


failures = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failures.append(msg)


def main():
    print("math/sin against math.sin:")
    s = make_sim()
    worst = 0
    for deg in range(360):
        s.set("#a", "mc.tmp", deg)
        s.run_function("mastercycle:math/sin")
        worst = max(worst, abs(s.get("#r", "mc.tmp") - 1000 * math.sin(math.radians(deg))))
    check(worst <= 3, f"sin error <= 0.003 for every degree (worst {worst / 1000:.4f})")

    print("throttle:")
    s = make_sim()
    n = 0
    while speed(s) < 600 and n < 200:
        tick(s, ["forward"])
        n += 1
    check(speed(s) == 600, f"reaches cruise speed 600 (12 blocks/s) in {n} ticks")
    for _ in range(20):
        tick(s, ["forward"])
    check(speed(s) == 600, "holds at the cruise cap")
    fuel_before = s.get("cycle", "mc.fuel")
    tick(s, ["forward"])
    check(fuel_before - s.get("cycle", "mc.fuel") == 1, "burns 1 fuel per tick of throttle")

    print("boost:")
    for _ in range(40):
        tick(s, ["forward", "sprint"])
    check(speed(s) == 950, f"boost reaches 950 (19 blocks/s): {speed(s)}")
    f0 = s.get("cycle", "mc.fuel")
    tick(s, ["forward", "sprint"])
    check(f0 - s.get("cycle", "mc.fuel") == 3, "boost burns 3 fuel per tick")
    tick(s, ["forward"])
    check(600 < speed(s) < 950, f"releasing boost eases back down, not a snap ({speed(s)})")
    for _ in range(60):
        tick(s, ["forward"])
    check(speed(s) == 600, "back to cruise after boost")

    print("motion vector:")
    s.set("cycle", "mc.yaw", 0)
    s.rider_yaw = 0
    tick(s, ["forward"])
    mx, mz = s.stored.get("m[0]"), s.stored.get("m[2]")
    check(abs(mx) < 0.01 and abs(mz - 0.6) < 0.01, f"yaw 0 drives south (+Z): motion ({mx:.3f}, {mz:.3f})")
    s.set("cycle", "mc.yaw", 9000)
    s.rider_yaw = 90
    tick(s, ["forward"])
    mx, mz = s.stored.get("m[0]"), s.stored.get("m[2]")
    check(abs(mx + 0.6) < 0.01 and abs(mz) < 0.01, f"yaw 90 drives west (-X): motion ({mx:.3f}, {mz:.3f})")
    s.set("cycle", "mc.yaw", 22500)
    s.rider_yaw = 225
    tick(s, ["forward"])
    mx, mz = s.stored.get("m[0]"), s.stored.get("m[2]")
    check(mx > 0.4 and mz < -0.4, f"yaw 225 drives north-east (+X, -Z): motion ({mx:.3f}, {mz:.3f})")

    print("steering (follows the rider's view):")
    s.set("cycle", "mc.yaw", 0)
    s.rider_yaw = 90
    tick(s, ["forward"])
    check(s.get("cycle", "mc.yaw") == 600, f"turns toward the view at 6 deg/tick ({s.get('cycle', 'mc.yaw')})")
    for _ in range(20):
        tick(s, ["forward"])
    check(s.get("cycle", "mc.yaw") == 9000, f"settles exactly on the view, no overshoot ({s.get('cycle', 'mc.yaw')})")
    s.rider_yaw = -170  # shortest way from 90 is through 180, i.e. turning right
    for _ in range(3):
        tick(s, ["forward"])
    check(s.get("cycle", "mc.yaw") == 9000 + 1800, f"takes the short way round past 180 ({s.get('cycle', 'mc.yaw')})")
    for _ in range(30):
        tick(s, ["forward"])
    check(s.get("cycle", "mc.yaw") == 19000, f"and wraps cleanly to 190 = -170 ({s.get('cycle', 'mc.yaw')})")
    s.rider_yaw = 190 + 720  # players' yaw can wind up past 360
    tick(s, ["forward"])
    check(s.get("cycle", "mc.yaw") == 19000, "a wound-up camera yaw (910 = 190) doesn't make it spin")
    for _ in range(20):
        tick(s, ["forward", "right"])
    check(s.get("cycle", "mc.yaw") == 23500, f"D carves 45 deg right of the view ({s.get('cycle', 'mc.yaw')})")
    s.rider_yaw = 190
    for _ in range(100):
        tick(s, [])
        if speed(s) == 0:
            break
    parked = s.get("cycle", "mc.yaw")
    s.rider_yaw = 0
    for _ in range(10):
        tick(s, [])
    check(speed(s) == 0 and s.get("cycle", "mc.yaw") == parked, "parked: looking around doesn't swing the bike")
    s.rider_yaw = 0
    s.set("cycle", "mc.yaw", 0)

    print("braking & reverse:")
    n = 0
    while speed(s) > 0 and n < 100:
        tick(s, ["backward"])
        n += 1
    check(speed(s) == 0 and n <= 15, f"S brakes from 600 to a stop in {n} ticks")
    for _ in range(30):
        tick(s, ["backward"])
    check(speed(s) == -150, f"holding S reverses, capped at -150 ({speed(s)})")
    for _ in range(30):
        tick(s, [])
    check(speed(s) == 0, "coasts to a stop from reverse")

    print("coasting:")
    for _ in range(40):
        tick(s, ["forward"])
    n = 0
    while speed(s) > 0 and n < 200:
        tick(s, [])
        n += 1
    check(40 <= n <= 80, f"rolls to a stop in {n} ticks after letting go of W")

    print("wall crash:")
    for _ in range(40):
        tick(s, ["forward"])
    s.wall = True  # the game zeroes Motion on the blocked axis
    tick(s, ["forward"])
    s.wall = False
    tick(s, ["forward"])
    check(speed(s) < 200, f"driving into a wall knocks the speed down ({speed(s)})")
    check(any("item.shield.block" in line for line in s.log), "with a clunk")
    s.log.clear()
    for _ in range(40):
        tick(s, ["forward", "left"])
    check(not any("item.shield.block" in line for line in s.log), "no false crashes while cornering at speed")

    print("walls & steps:")
    s = make_sim()
    s.rider_yaw = 0  # heading south (+z)
    s.solid = {(x, y, 6) for x in range(-3, 4) for y in range(0, 4)}  # a wall, face at z = 6
    for _ in range(80):
        tick(s, ["forward"])
    nose = s.pos[1] + 1.37
    check(speed(s) == 0 and nose <= 6.0, f"drives up to a wall and stops with the nose outside it (nose z {nose:.2f}, wall at 6)")
    check(any("item.shield.block" in line for line in s.log), "hitting the wall at speed clunks")
    for _ in range(10):
        tick(s, ["forward", "sprint"])
    check(s.pos[1] + 1.37 <= 6.0, "holding throttle or boost doesn't push it through")
    for _ in range(20):
        tick(s, ["backward"])
    check(speed(s) < 0, "it can still reverse away from the wall")
    s = make_sim()
    s.rider_yaw = 0
    s.solid = {(x, y, 30) for x in range(-3, 4) for y in range(0, 4)}
    for _ in range(40):
        tick(s, ["forward", "sprint"])
    for _ in range(40):
        tick(s, ["forward", "sprint"])
    check(s.pos[1] + 1.37 <= 30.0, f"even at full boost the nose never enters the wall (nose z {s.pos[1] + 1.37:.2f}, wall at 30)")
    s = make_sim()
    s.rider_yaw = 0
    s.solid = {(x, 0, z) for x in range(-3, 4) for z in range(6, 12)}  # a knee-high step
    hopped = False
    for _ in range(30):
        tick(s, ["forward"])
        hopped |= s.get("#hop", "mc.tmp") == 1
    check(hopped and speed(s) > 0, "a one-block step ahead: the front hops up onto it instead of stopping")
    check(s.get("cycle", "mc.fuel") > 6000 - 40, "auto-hopping a step costs no fuel")
    s = make_sim()
    s.rider_yaw = 0
    s.solid = {(x, y, z) for x in range(-3, 4) for y in (0, 1) for z in range(-6, -2)}  # wall behind
    for _ in range(60):
        tick(s, ["backward"])
    check(s.pos[1] - 0.78 >= -2.0 and speed(s) == 0, f"reversing stops before the tail enters a wall (tail z {s.pos[1] - 0.78:.2f})")

    print("hop:")
    s2 = make_sim()
    s2.preds = set()
    log_before = len(s2.log)
    tick(s2, ["jump"])
    check(s2.get("#hop", "mc.tmp") == 1 and s2.get("cycle", "mc.fuel") == 6000 - 25, "Space hops and costs 25 fuel")
    tick(s2, ["jump"])
    check(s2.get("#hop", "mc.tmp") == 0, "hop has a cooldown")
    tick(s2, ["jump"], on_ground=False)
    check(s2.get("#hop", "mc.tmp") == 0, "can't hop in mid-air")
    _ = log_before

    print("fuel empty:")
    s = make_sim()
    s.set("cycle", "mc.fuel", 30)
    for _ in range(40):
        tick(s, ["forward"])
    check(s.get("cycle", "mc.fuel") == 0, "fuel bottoms out at exactly 0")
    check(any("Fuel Empty" in line for line in s.log), "rider is told 'Fuel Empty!'")
    check(any("mastercycle:fuel.empty" in line for line in s.log), "power-down sound plays")
    top = speed(s)
    n = 0
    while speed(s) > 0 and n < 100:
        tick(s, ["forward"])
        n += 1
    check(speed(s) == 0 and n <= 25, f"with no fuel, holding W still stops the bike ({top} -> 0 in {n} ticks)")
    tick(s, ["forward"])
    check(speed(s) == 0, "and it won't move again until refuelled")
    tick(s, ["backward"])
    check(speed(s) == 0, "no reversing without fuel either")
    s.set("cycle", "mc.fuel", 100)
    tick(s, ["forward"])
    check(speed(s) > 0, "refuelled -> drives again")

    print("hud:")
    s = make_sim()
    for fuel, want in ((6000, "▮" * 10), (3000, "▮" * 5 + "▯" * 5), (1, "▮" + "▯" * 9)):
        s.set("#hud_fuel", "mc.tmp", fuel)
        s.set("#hud_speed", "mc.tmp", 600)
        s.set("#boosting", "mc.tmp", 0)
        s.executor = "rider"
        s.log.clear()
        s.run_function("mastercycle:hud/show")
        bar = next((line for line in s.log if line.startswith("data modify storage mastercycle:hud bar")), "")
        check(want in bar and s.get("#kmh", "mc.tmp") == 43,
              f"fuel {fuel} -> {s.get('#pct', 'mc.tmp')}% {want}, 600 -> {s.get('#kmh', 'mc.tmp')} km/h")

    print("effects & sounds (full tick loop):")
    s = make_sim()
    s.set("cycle", "mc.cid", 1)
    s.set("cycle", "mc.fuel", 1250)
    for _ in range(100):
        ride_tick(s, ["forward"])
    check(count(s, "mastercycle:fuel.low") == 1, f"low-fuel chime plays once when crossing 20% ({count(s, 'mastercycle:fuel.low')}x)")
    s.set("cycle", "mc.fuel", 3000)
    ride_tick(s, ["forward"])
    s.set("cycle", "mc.fuel", 1100)
    ride_tick(s, ["forward"])
    check(count(s, "mastercycle:fuel.low") == 2, "and re-arms after refuelling above the line")

    s = make_sim(); s.set("cycle", "mc.cid", 1)
    for _ in range(6):
        ride_tick(s, [], on_ground=False)
    ride_tick(s, [])
    check(count(s, "entity.breeze.land") == 1, "landing after 6 airborne ticks: thump + dust")
    ride_tick(s, [], on_ground=False); ride_tick(s, [], on_ground=False); ride_tick(s, [])
    check(count(s, "entity.breeze.land") == 1, "a 2-tick bump doesn't count as a landing")

    s = make_sim(); s.set("cycle", "mc.cid", 1)
    for _ in range(5):
        ride_tick(s, ["forward", "sprint"])
    check(s.get("cycle", "mc.boost") == 1 and count(s, "effect give @s minecraft:speed") == 5,
          "boosting gives the rider a hidden Speed effect each tick (FOV kick)")
    check(count(s, "mastercycle:engine.boost") == 1, "boost sound plays once when the boost starts")
    ride_tick(s, [], ridden=False)
    check(count(s, "mastercycle:engine.stop") == 1 and s.get("cycle", "mc.boost") == 0 and s.get("cycle", "mc.ridden") == 0,
          "getting off: power-down sound, boost state reset")
    ride_tick(s, [], ridden=False)
    check(count(s, "mastercycle:engine.stop") == 1, "power-down plays only once")
    for _ in range(3):
        ride_tick(s, ["forward", "sprint"])
    check(count(s, "mastercycle:engine.boost") == 2, "next boost after remounting plays its sound again")

    s = make_sim(); s.set("cycle", "mc.cid", 1)
    ride_tick(s, [])
    p_idle = s.stored.get("hum.p")
    for _ in range(60):
        ride_tick(s, ["forward", "sprint"])
    p_fast = s.stored.get("hum.p")
    for _ in range(9):
        ride_tick(s, ["forward", "sprint"])
        p_fast = s.stored.get("hum.p") or p_fast
    check(p_idle is not None and abs(p_idle - 0.65) < 0.01 and p_fast is not None and abs(p_fast - 1.4575) < 0.01,
          f"engine hum pitch follows speed: {p_idle} idle -> {p_fast} at full boost")

    s = make_sim(); s.set("cycle", "mc.cid", 1)
    for _ in range(40):
        ride_tick(s, ["forward"])
    for _ in range(10):
        ride_tick(s, ["backward"])
    check(count(s, "entity.breeze.slide") == 1, "hard braking screeches once per skid")

    s = make_sim(); s.set("cycle", "mc.cid", 1)
    ride_tick(s, [], ridden=False, t40=0)
    check(count(s, "particle minecraft:dust") == 4, "a parked cycle with fuel pulses from both hubs every 2 s")
    s.set("cycle", "mc.fuel", 0); s.log.clear()
    ride_tick(s, [], ridden=False, t40=0)
    check(count(s, "particle minecraft:dust") == 0, "an empty parked cycle stays dark")

    s = make_sim()
    s.set("#hud_fuel", "mc.tmp", 9000); s.set("#hud_speed", "mc.tmp", 0); s.set("#boosting", "mc.tmp", 0)
    s.executor = "rider"; s.log.clear()
    s.run_function("mastercycle:hud/show")
    bar = next((line for line in s.log if line.startswith("data modify storage mastercycle:hud bar")), "")
    check(s.get("#pct", "mc.tmp") == 100 and "▮" * 10 in bar, "fuel above the tank size shows a full gauge, not a stale one")

    print()
    if failures:
        print(f"{len(failures)} check(s) failed")
        sys.exit(1)
    print("all driving checks passed")


if __name__ == "__main__":
    main()
