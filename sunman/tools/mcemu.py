"""A small Minecraft command emulator, for testing the generated datapack without a server.

It is not Minecraft. It runs the subset of 26.3 commands the pack uses — scoreboard, execute
(as/at/positioned/rotated/align/if/unless/store/summon/run), function (with macros), return,
fill, setblock, summon, kill, tp, tag, data, random, playsound, tellraw — against a block world
and an entity list, with Minecraft's semantics where they matter to the pack's logic:

  * a function's result is its `return` value; `return fail` fails; no return, no value
  * `execute` forks per selected entity, `store` applies per fork, `if function` passes on a
    non-zero return, `return run` inside a fork leaves the function at the first one
  * macro lines substitute $(key) from the argument compound before the line is parsed
  * vec3 arguments centre bare integer x/z on the block (+0.5); block positions floor
  * `^left ^up ^forward` local coordinates from the executor's rotation
  * a command budget per call, like the game's max_command_sequence_length (65536)

What it cannot tell you: whether an entity's NBT is accepted, how anything renders, how the
game's own block updates react. That is what a real server is for (tools/server_test.py).
"""
import math
import random
import re

from mcdata import MC

AIR = {"air", "cave_air", "void_air"}


def strip_ns(i):
    i = i.lstrip("#")
    return i[10:] if i.startswith("minecraft:") else i


# ====================================================================== SNBT

class SNBTError(ValueError):
    pass


class SNBT:
    """Parses SNBT into Python values: dicts, lists, ints, floats, strings. Typed arrays
    become lists. Numbers keep their int/float nature; suffixes are dropped."""
    WORD = re.compile(r"[A-Za-z0-9_\-.+]+")
    NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?([bBsSlLfFdD]?)$")

    def __init__(self, s):
        self.s, self.i = s, 0

    @classmethod
    def parse(cls, s, partial=False):
        p = cls(s)
        v = p.value()
        p.ws()
        if not partial and p.i != len(s):
            raise SNBTError(f"trailing text after SNBT at {p.i}: {s[p.i:p.i + 30]!r}")
        return (v, p.i) if partial else v

    def ws(self):
        while self.i < len(self.s) and self.s[self.i] in " \t\n":
            self.i += 1

    def peek(self):
        self.ws()
        return self.s[self.i] if self.i < len(self.s) else ""

    def expect(self, ch):
        if self.peek() != ch:
            raise SNBTError(f"expected {ch!r} at {self.i}: {self.s[self.i:self.i + 30]!r}")
        self.i += 1

    def string(self):
        q = self.s[self.i]
        self.i += 1
        out = []
        while self.i < len(self.s):
            c = self.s[self.i]
            if c == "\\":
                out.append(self.s[self.i + 1])
                self.i += 2
                continue
            if c == q:
                self.i += 1
                return "".join(out)
            out.append(c)
            self.i += 1
        raise SNBTError("unterminated string")

    def value(self):
        c = self.peek()
        if c == "{":
            self.i += 1
            out = {}
            if self.peek() == "}":
                self.i += 1
                return out
            while True:
                self.ws()
                if self.s[self.i] in "\"'":
                    k = self.string()
                else:
                    m = self.WORD.match(self.s, self.i)
                    if not m:
                        raise SNBTError(f"bad key at {self.i}: {self.s[self.i:self.i + 20]!r}")
                    k = m.group(0)
                    self.i = m.end()
                self.expect(":")
                out[k] = self.value()
                if self.peek() == ",":
                    self.i += 1
                    if self.peek() == "}":
                        self.i += 1
                        return out
                    continue
                self.expect("}")
                return out
        if c == "[":
            self.i += 1
            if re.match(r"[BIL];", self.s[self.i:self.i + 2]):
                self.i += 2
            out = []
            if self.peek() == "]":
                self.i += 1
                return out
            while True:
                out.append(self.value())
                if self.peek() == ",":
                    self.i += 1
                    if self.peek() == "]":
                        self.i += 1
                        return out
                    continue
                self.expect("]")
                return out
        if c in "\"'":
            return self.string()
        m = self.WORD.match(self.s, self.i)
        if not m:
            raise SNBTError(f"bad value at {self.i}: {self.s[self.i:self.i + 20]!r}")
        self.i = m.end()
        w = m.group(0)
        if w in ("true", "false"):
            return 1 if w == "true" else 0
        n = self.NUM.match(w)
        if n:
            suf = n.group(1).lower()
            body = w[:-1] if suf else w
            if suf in ("f", "d") or any(ch in body for ch in ".eE"):
                return float(body)
            return int(body)
        return w


def snbt_text(v):
    """A value as macro substitution text: numbers bare, strings unquoted."""
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, float):
        return repr(v).rstrip("0").rstrip(".") if "." in repr(v) else repr(v)
    return str(v)


# ====================================================================== tokens

def split_args(s):
    """Split a command on top-level spaces; brackets, braces and quotes group."""
    out, cur, depth, q = [], [], 0, None
    i = 0
    while i < len(s):
        c = s[i]
        if q:
            cur.append(c)
            if c == "\\" and i + 1 < len(s):
                cur.append(s[i + 1])
                i += 2
                continue
            if c == q:
                q = None
        elif c in "\"'":
            q = c
            cur.append(c)
        elif c in "[{(":
            depth += 1
            cur.append(c)
        elif c in "]})":
            depth -= 1
            cur.append(c)
        elif c == " " and depth == 0:
            if cur:
                out.append("".join(cur))
                cur = []
        else:
            cur.append(c)
        i += 1
    if cur:
        out.append("".join(cur))
    return out


def parse_block(spec):
    """'minecraft:oak_stairs[facing=north]{...}' or '#tag[...]' -> (is_tag, id, {props})."""
    is_tag = spec.startswith("#")
    m = re.match(r"#?([a-z0-9_.\-:/]+)(\[[^\]]*\])?(\{.*\})?$", spec)
    if not m:
        raise ValueError(f"bad block spec {spec!r}")
    props = {}
    if m.group(2):
        for kv in m.group(2)[1:-1].split(","):
            if kv.strip():
                k, v = kv.split("=")
                props[k.strip()] = v.strip()
    return is_tag, strip_ns(m.group(1)) if not is_tag else m.group(1), props


def parse_selector(tok):
    """'@e[type=marker,tag=a,tag=!b,distance=..3,limit=1,sort=nearest]' -> (kind, [(k, v)])."""
    m = re.match(r"@([aeprsn])(?:\[(.*)\])?$", tok)
    if not m:
        return None
    args = []
    if m.group(2):
        for part in split_top(m.group(2)):
            k, v = part.split("=", 1)
            args.append((k.strip(), v.strip()))
    return m.group(1), args


def split_top(s, sep=","):
    out, cur, depth, q = [], [], 0, None
    for c in s:
        if q:
            cur.append(c)
            if c == q:
                q = None
            continue
        if c in "\"'":
            q = c
        elif c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1
        if c == sep and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(c)
    if cur:
        out.append("".join(cur))
    return out


def parse_range(tok):
    if ".." in tok:
        a, b = tok.split("..")
        return (float(a) if a else -math.inf, float(b) if b else math.inf)
    v = float(tok)
    return (v, v)


# ====================================================================== world

class Entity:
    _next = 0

    def __init__(self, etype, pos, nbt=None, rot=(0.0, 0.0)):
        Entity._next += 1
        self.id = Entity._next
        self.type = strip_ns(etype)
        self.pos = list(pos)
        self.nbt = dict(nbt or {})
        r = self.nbt.get("Rotation")
        self.rot = [float(r[0]), float(r[1])] if r else list(rot)
        self.tags = set(self.nbt.get("Tags", []))
        self.alive = True

    def __repr__(self):
        return f"<{self.type} {sorted(self.tags)} @ {[round(v, 2) for v in self.pos]}>"


class Return(Exception):
    def __init__(self, value):
        self.value = value


class Ctx:
    __slots__ = ("entity", "pos", "rot")

    def __init__(self, entity=None, pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0)):
        self.entity, self.pos, self.rot = entity, tuple(pos), tuple(rot)

    def but(self, **kw):
        c = Ctx(self.entity, self.pos, self.rot)
        for k, v in kw.items():
            setattr(c, k, v)
        return c


class World:
    def __init__(self, functions, block_tags, seed=1, budget=65536):
        self.functions = functions                 # id -> [lines]
        self.pack_tags = block_tags                # 'sunman:x' -> [values]
        self.blocks = {}                           # (x, y, z) -> (id, props)
        self.entities = []
        self.scores = {}                           # objective -> holder -> int
        self.storage = {}
        self.rng = random.Random(seed)
        self.log = []                              # (kind, details)
        self.budget = budget
        self.spent = 0
        self._tag_cache = {}
        self.calls = {}
        self.pending = []                          # (due tick, function id)
        self.time = 0

    # ------------------------------------------------------------------ blocks
    def block(self, p):
        return self.blocks.get(p, ("air", {}))

    def set_block(self, p, bid, props=None):
        if bid in AIR:
            self.blocks.pop(p, None)
        else:
            self.blocks[p] = (bid, dict(props or {}))

    def tag_members(self, name):
        name = name.lstrip("#")
        if name in self._tag_cache:
            return self._tag_cache[name]
        if name.startswith("minecraft:") or ":" not in name:
            out = set(MC.tag("block", name))
        else:
            out = set()
            for v in self.pack_tags[name]:
                out |= self.tag_members(v) if v.startswith("#") else {strip_ns(v)}
        self._tag_cache[name] = out
        return out

    def matches(self, p, spec):
        is_tag, ident, props = parse_block(spec)
        bid, bprops = self.block(p)
        if is_tag:
            if bid not in self.tag_members(ident):
                return False
        elif bid != ident:
            return False
        return all(bprops.get(k, MC.block_defaults(bid).get(k)) == v for k, v in props.items())

    # ------------------------------------------------------------------ scores / storage
    def score(self, holder, obj):
        return self.scores.get(obj, {}).get(holder)

    def set_score(self, holder, obj, v):
        self.scores.setdefault(obj, {})[holder] = int(v)

    def holders(self, tok, ctx):
        if tok.startswith("@"):
            return [f"e{e.id}" for e in self.select(tok, ctx)]
        return [tok]

    def path_get(self, root, path):
        cur = root
        for seg in self._path(path):
            if isinstance(seg, int):
                if not isinstance(cur, list) or seg >= len(cur):
                    return None
                cur = cur[seg]
            else:
                if not isinstance(cur, dict) or seg not in cur:
                    return None
                cur = cur[seg]
        return cur

    def path_set(self, root, path, value):
        segs = self._path(path)
        cur = root
        for seg in segs[:-1]:
            cur = cur.setdefault(seg, {})
        cur[segs[-1]] = value

    @staticmethod
    def _path(path):
        segs = []
        for m in re.finditer(r'"([^"]*)"|([A-Za-z0-9_\-+:]+)|\[(\d+)\]', path):
            if m.group(1) is not None:
                segs.append(m.group(1))
            elif m.group(2) is not None:
                segs.append(m.group(2))
            else:
                segs.append(int(m.group(3)))
        return segs

    def store(self, ident):
        return self.storage.setdefault(ident, {})

    # ------------------------------------------------------------------ entities
    def summon(self, etype, pos, nbt=None):
        e = Entity(etype, pos, nbt)
        self.entities.append(e)
        return e

    def alive(self):
        return [e for e in self.entities if e.alive]

    def select(self, tok, ctx):
        sel = parse_selector(tok)
        if sel is None:
            return [e for e in self.alive() if e.nbt.get("name") == tok]
        kind, args = sel
        if kind == "s":
            pool = [ctx.entity] if ctx.entity is not None and ctx.entity.alive else []
        elif kind in "apr":
            pool = [e for e in self.alive() if e.type == "player"]
        else:
            pool = self.alive()
        limit, sort = None, None
        if kind in "pn":
            limit, sort = 1, "nearest"
        if kind == "r":
            limit, sort = 1, "random"
        out = []
        for e in pool:
            ok = True
            for k, v in args:
                neg = v.startswith("!")
                vv = v[1:] if neg else v
                if k == "type":
                    ok = (e.type == strip_ns(vv)) != neg
                elif k == "tag":
                    ok = ((vv in e.tags) if vv else not e.tags) != neg
                elif k == "distance":
                    lo, hi = parse_range(vv)
                    ok = lo <= math.dist(e.pos, ctx.pos) <= hi
                elif k == "gamemode":
                    ok = (e.nbt.get("gamemode", "survival") == vv) != neg
                elif k == "limit":
                    limit = int(vv)
                elif k == "sort":
                    sort = vv
                else:
                    raise NotImplementedError(f"selector argument {k}")
                if not ok:
                    break
            if ok:
                out.append(e)
        if sort == "nearest":
            out.sort(key=lambda e: math.dist(e.pos, ctx.pos))
        elif sort == "furthest":
            out.sort(key=lambda e: -math.dist(e.pos, ctx.pos))
        elif sort == "random":
            self.rng.shuffle(out)
        return out[:limit] if limit is not None else out

    # ------------------------------------------------------------------ coordinates
    @staticmethod
    def _local(ctx, l, u, f):
        yaw, pitch = math.radians(ctx.rot[0]), math.radians(ctx.rot[1])
        fwd = (-math.sin(yaw) * math.cos(pitch), -math.sin(pitch), math.cos(yaw) * math.cos(pitch))
        left = (math.cos(yaw), 0.0, math.sin(yaw))
        up = (fwd[1] * left[2] - fwd[2] * left[1], fwd[2] * left[0] - fwd[0] * left[2],
              fwd[0] * left[1] - fwd[1] * left[0])
        return tuple(ctx.pos[i] + left[i] * l + up[i] * u + fwd[i] * f for i in range(3))

    def vec3(self, toks, ctx, block=False):
        if toks[0].startswith("^"):
            vals = [float(t[1:] or 0) for t in toks]
            return self._local(ctx, *vals)
        out = []
        for i, t in enumerate(toks):
            if t.startswith("~"):
                out.append(ctx.pos[i] + float(t[1:] or 0))
            else:
                v = float(t)
                if not block and i != 1 and "." not in t:
                    v += 0.5                        # vec3 centres a bare integer x / z
                out.append(v)
        return tuple(out)

    def bpos(self, toks, ctx):
        return tuple(math.floor(v) for v in self.vec3(toks, ctx, block=True))

    def rotation(self, toks, ctx):
        out = []
        for i, t in enumerate(toks):
            out.append(ctx.rot[i] + float(t[1:] or 0) if t.startswith("~") else float(t))
        return tuple(out)

    # ------------------------------------------------------------------ running
    def tick(self):
        self.spent += 1
        if self.spent > self.budget:
            raise RuntimeError("command budget exceeded (max_command_sequence_length)")

    def call(self, fid, ctx, args=None):
        """Run a function. Returns its return value (int), None for fail, or 'none' when
        it ended without a return."""
        fid = fid if ":" in fid else f"minecraft:{fid}"
        if fid not in self.functions:
            raise KeyError(f"unknown function {fid}")
        self.calls[fid] = self.calls.get(fid, 0) + 1
        try:
            for raw in self.functions[fid]:
                if not raw.strip() or raw.startswith("#"):
                    continue
                line = raw
                if line.startswith("$"):
                    if args is None:
                        raise RuntimeError(f"{fid}: macro line run without arguments")

                    def sub(m):
                        if m.group(1) not in args:
                            raise RuntimeError(f"{fid}: macro argument $({m.group(1)}) missing")
                        return snbt_text(args[m.group(1)])
                    line = re.sub(r"\$\(([A-Za-z0-9_]+)\)", sub, line[1:])
                self.run(split_args(line), ctx)
        except Return as r:
            return r.value
        return "none"

    def run(self, toks, ctx):
        """Run one command. Returns (success, value)."""
        self.tick()
        head = toks[0]
        h = getattr(self, "c_" + head.replace("-", "_"), None)
        if h is None:
            raise NotImplementedError(f"command {head}")
        return h(toks[1:], ctx)

    # ------------------------------------------------------------------ commands
    def c_execute(self, t, ctx, stores=()):
        if not t:
            return (True, 1)
        k = t[0]
        if k in ("as", "at"):
            ents = self.select(t[1], ctx)
            n = 0
            for e in ents:
                c = ctx.but(entity=e) if k == "as" else ctx.but(pos=tuple(e.pos), rot=tuple(e.rot))
                ok, _ = self.c_execute(t[2:], c, stores)
                n += 1 if ok else 0
            return (n > 0, n)
        if k == "positioned":
            if t[1] == "as":
                return self._fork_pos(t[2:], ctx, stores, t[2])
            return self.c_execute(t[4:], ctx.but(pos=self.vec3(t[1:4], ctx)), stores)
        if k == "rotated":
            if t[1] == "as":
                ents = self.select(t[2], ctx)
                n = 0
                for e in ents:
                    ok, _ = self.c_execute(t[3:], ctx.but(rot=tuple(e.rot)), stores)
                    n += 1 if ok else 0
                return (n > 0, n)
            return self.c_execute(t[3:], ctx.but(rot=self.rotation(t[1:3], ctx)), stores)
        if k == "align":
            p = list(ctx.pos)
            for ax in t[1]:
                i = "xyz".index(ax)
                p[i] = math.floor(p[i])
            return self.c_execute(t[2:], ctx.but(pos=tuple(p)), stores)
        if k == "summon":
            e = self.summon(t[1], ctx.pos)
            return self.c_execute(t[2:], ctx.but(entity=e), stores)
        if k in ("if", "unless"):
            ok, used = self._cond(t[1:], ctx)
            ok = ok if k == "if" else not ok
            rest = t[1 + used:]
            if not rest:
                for s in stores:
                    self._store(s, ctx, ok, 1 if ok else 0)
                return (ok, 1 if ok else 0)
            if not ok:
                return (False, 0)
            return self.c_execute(rest, ctx, stores)
        if k == "store":
            mode = t[1]
            if t[2] == "score":
                s = (mode, "score", t[3], t[4])
                return self.c_execute(t[5:], ctx, stores + (s,))
            if t[2] == "storage":
                s = (mode, "storage", t[3], t[4], t[5], float(t[6]))
                return self.c_execute(t[7:], ctx, stores + (s,))
            raise NotImplementedError(f"execute store {t[2]}")
        if k == "run":
            ok, val = self.run(t[1:], ctx)
            for s in stores:
                self._store(s, ctx, ok, val)
            return (ok, val)
        raise NotImplementedError(f"execute {k}")

    def _fork_pos(self, t, ctx, stores, sel):
        ents = self.select(sel, ctx)
        n = 0
        for e in ents:
            ok, _ = self.c_execute(t[1:], ctx.but(pos=tuple(e.pos)), stores)
            n += 1 if ok else 0
        return (n > 0, n)

    def _store(self, s, ctx, ok, val):
        v = (1 if ok else 0) if s[0] == "success" else (val if ok and val is not None else 0)
        if s[1] == "score":
            for h in self.holders(s[2], ctx):
                self.set_score(h, s[3], v)
        else:
            _, _, ident, path, typ, scale = s
            num = v * scale
            self.path_set(self.store(ident), path, int(num) if typ in ("int", "short", "byte", "long") else float(num))

    def _cond(self, t, ctx):
        k = t[0]
        if k == "block":
            return self.matches(self.bpos(t[1:4], ctx), t[4]), 5
        if k == "entity":
            return bool(self.select(t[1], ctx)), 2
        if k == "loaded":
            return True, 4
        if k == "score":
            hs = self.holders(t[1], ctx)
            a = self.score(hs[0], t[2]) if hs else None
            if t[3] == "matches":
                lo, hi = parse_range(t[4])
                return (a is not None and lo <= a <= hi), 5
            bh = self.holders(t[4], ctx)
            b = self.score(bh[0], t[5]) if bh else None
            if a is None or b is None:
                return False, 6
            return {"<": a < b, "<=": a <= b, "=": a == b, ">=": a >= b, ">": a > b}[t[3]], 6
        if k == "data":
            if t[1] == "entity":
                es = self.select(t[2], ctx)
                return bool(es) and self.path_get(es[0].nbt, t[3]) is not None, 4
            if t[1] == "storage":
                return self.path_get(self.store(t[2]), t[3]) is not None, 4
        if k == "function":
            r = self.call(t[1], ctx)
            return (r not in (None, "none", 0)), 2
        raise NotImplementedError(f"execute if {k}")

    def c_scoreboard(self, t, ctx):
        if t[0] == "objectives":
            self.scores.setdefault(t[2], {})
            return (True, 0)
        op = t[1]
        hs = self.holders(t[2], ctx)
        obj = t[3]
        if op == "set":
            for h in hs:
                self.set_score(h, obj, int(t[4]))
            return (bool(hs), int(t[4]))
        if op in ("add", "remove"):
            d = int(t[4]) * (1 if op == "add" else -1)
            v = 0
            for h in hs:
                v = (self.score(h, obj) or 0) + d
                self.set_score(h, obj, v)
            return (bool(hs), v)
        if op == "get":
            v = self.score(hs[0], obj) if hs else None
            return (v is not None, v or 0)
        if op == "reset":
            for h in hs:
                self.scores.get(obj, {}).pop(h, None)
            return (True, 0)
        if op == "operation":
            src = self.holders(t[5], ctx)
            b = self.score(src[0], t[6]) or 0
            for h in hs:
                a = self.score(h, obj) or 0
                v = {"=": b, "+=": a + b, "-=": a - b, "*=": a * b,
                     "/=": a // b if b else a, "%=": a % b if b else a,
                     "<": min(a, b), ">": max(a, b)}[t[4]]
                self.set_score(h, obj, v)
            return (True, 0)
        raise NotImplementedError(f"scoreboard players {op}")

    def c_function(self, t, ctx):
        args = None
        if len(t) > 1:
            if t[1] == "with":
                if t[2] != "storage":
                    raise NotImplementedError("function with " + t[2])
                args = self.path_get(self.store(t[3]), t[4])
                if not isinstance(args, dict):
                    raise RuntimeError(f"function {t[0]} with storage {t[3]} {t[4]}: no compound there")
            else:
                args = SNBT.parse(t[1])
        r = self.call(t[0], ctx, args)
        if r == "none":
            return (True, 0)
        return (r is not None, r or 0)

    def c_return(self, t, ctx):
        if t[0] == "fail":
            raise Return(None)
        if t[0] == "run":
            ok, val = self.run(t[1:], ctx)
            raise Return(val if ok else None)
        raise Return(int(t[0]))

    def c_fill(self, t, ctx):
        a, b = self.bpos(t[0:3], ctx), self.bpos(t[3:6], ctx)
        _, bid, props = parse_block(t[6])
        props = {**MC.block_defaults(bid), **props}
        filt = t[8] if len(t) > 8 and t[7] == "replace" else None
        vol = (abs(a[0] - b[0]) + 1) * (abs(a[1] - b[1]) + 1) * (abs(a[2] - b[2]) + 1)
        if vol > 32768:
            raise RuntimeError(f"fill volume {vol} over max_block_modifications")
        n = 0
        for x in range(min(a[0], b[0]), max(a[0], b[0]) + 1):
            for y in range(min(a[1], b[1]), max(a[1], b[1]) + 1):
                for z in range(min(a[2], b[2]), max(a[2], b[2]) + 1):
                    p = (x, y, z)
                    if filt and not self.matches(p, filt):
                        continue
                    if self.block(p) == (bid, props) or (bid in AIR and self.block(p)[0] in AIR):
                        continue
                    self.set_block(p, bid, props)
                    n += 1
        return (n > 0, n)

    def c_setblock(self, t, ctx):
        p = self.bpos(t[0:3], ctx)
        _, bid, props = parse_block(t[3])
        self.set_block(p, bid, {**MC.block_defaults(bid), **props})
        return (True, 1)

    def c_summon(self, t, ctx):
        pos = self.vec3(t[1:4], ctx) if len(t) > 1 else ctx.pos
        nbt = SNBT.parse(t[4]) if len(t) > 4 else {}
        self.summon(t[0], pos, nbt)
        return (True, 1)

    def c_kill(self, t, ctx):
        es = self.select(t[0], ctx) if t else [ctx.entity]
        for e in es:
            e.alive = False
        return (bool(es), len(es))

    def c_tp(self, t, ctx):
        es = self.select(t[0], ctx)
        pos = self.vec3(t[1:4], ctx)
        rot = self.rotation(t[4:6], ctx) if len(t) >= 6 else None
        for e in es:
            e.pos = list(pos)
            if rot:
                e.rot = list(rot)
        return (bool(es), len(es))

    c_teleport = c_tp

    def c_tag(self, t, ctx):
        es = self.select(t[0], ctx)
        for e in es:
            (e.tags.add if t[1] == "add" else e.tags.discard)(t[2])
        return (bool(es), len(es))

    def c_data(self, t, ctx):
        if t[0] == "merge" and t[1] == "storage":
            self.store(t[2]).update(SNBT.parse(t[3]))
            return (True, 1)
        if t[0] == "modify" and t[1] == "storage":
            root, path = self.store(t[2]), t[3]
            if t[4] != "set":
                raise NotImplementedError("data modify " + t[4])
            if t[5] == "value":
                self.path_set(root, path, SNBT.parse(t[6]))
                return (True, 1)
            if t[5] == "from":
                if t[6] == "entity":
                    es = self.select(t[7], ctx)
                    v = self.path_get(es[0].nbt, t[8]) if es else None
                else:
                    v = self.path_get(self.store(t[7]), t[8])
                if v is None:
                    return (False, 0)
                self.path_set(root, path, v)
                return (True, 1)
        raise NotImplementedError("data " + " ".join(t[:2]))

    def c_random(self, t, ctx):
        lo, hi = (int(v) for v in t[1].split(".."))
        return (True, self.rng.randint(lo, hi))

    def c_playsound(self, t, ctx):
        targets = self.select(t[2], ctx)
        pos = self.vec3(t[3:6], ctx) if len(t) >= 6 else ctx.pos
        self.log.append(("sound", t[0], pos, len(targets)))
        return (bool(targets), len(targets))

    def c_tellraw(self, t, ctx):
        self.log.append(("tellraw", SNBT.parse(t[1])))
        return (True, 1)

    def c_schedule(self, t, ctx):
        """schedule function <id> <time> [append|replace]; run by advance()."""
        fid, when = t[1], t[2]
        n = float(when[:-1]) if when[-1] in "tsd" else float(when)
        ticks = int(n * {"t": 1, "s": 20, "d": 24000}.get(when[-1], 1))
        if (t[3] if len(t) > 3 else "replace") == "replace":
            self.pending = [p for p in self.pending if p[1] != fid]
        self.pending.append((self.time + ticks, fid))
        self.log.append(("schedule", fid, when))
        return (True, 1)

    def advance(self, ticks, skip=()):
        """Let game ticks pass, running scheduled functions as they fall due (each with its
        own command budget, as the game gives each scheduled function)."""
        for _ in range(ticks):
            self.time += 1
            due = [p for p in self.pending if p[0] <= self.time]
            self.pending = [p for p in self.pending if p[0] > self.time]
            for _, fid in due:
                if fid in skip:
                    continue
                self.spent = 0
                self.call(fid, Ctx())
                self.max_spent = max(getattr(self, "max_spent", 0), self.spent)
