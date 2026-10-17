#!/usr/bin/env python3
"""Offline validator for the Master Cycle packs.

Without a Minecraft server to load the packs into, this is the next best
thing: it parses every command in every .mcfunction file against the real
command tree of the target version (published by misode/mcmeta, extracted from
the game), parses the SNBT / text components / selectors inside them, and
cross-checks ids against the game's registries:

  * command syntax (Brigadier tree walk, including execute ... run chains)
  * SNBT syntax in NBT, components, item stacks and particle options
  * selector arguments, entity types, items, particles, attributes, sounds
  * function / predicate references, scoreboard objectives, macro arguments
  * JSON files: predicate & item-model types, entity sub-predicate keys,
    model element bounds, textures/models referenced by the resource pack
  * models: no z-fighting (same-facing faces that are coplanar and overlap)

    python3 master-cycle/tools/validate.py [--version 26.3]

Exit status is non-zero if anything is wrong.
"""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model_check import zfight_pairs  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DP = ROOT / "datapack"
RP = ROOT / "resourcepack"
CACHE = ROOT / "tools" / ".cache"
MCMETA = "https://raw.githubusercontent.com/misode/mcmeta/{version}-summary/{path}"

errors = []


def err(where, msg):
    errors.append(f"{where}: {msg}")


def fetch(version, path):
    dest = CACHE / version / path
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = MCMETA.format(version=version, path=path)
        with urllib.request.urlopen(url, timeout=60) as r:
            dest.write_bytes(r.read())
    return json.loads(dest.read_text())


# ------------------------------------------------------------------ SNBT ---
class SNBTError(Exception):
    pass


class SNBT:
    """Small strict-ish SNBT reader (enough to catch structural mistakes)."""

    NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?[bslfdBSLFD]?")
    UNQUOTED = re.compile(r"[A-Za-z0-9._+\-]+")

    def __init__(self, s, i=0):
        self.s, self.i = s, i

    def ws(self):
        while self.i < len(self.s) and self.s[self.i] in " \t":
            self.i += 1

    def peek(self):
        self.ws()
        return self.s[self.i] if self.i < len(self.s) else ""

    def expect(self, ch):
        if self.peek() != ch:
            raise SNBTError(f"expected {ch!r} at col {self.i} in {self.s[max(0, self.i - 20):self.i + 20]!r}")
        self.i += 1

    def value(self):
        c = self.peek()
        if c == "{":
            return self.compound()
        if c == "[":
            return self.list()
        if c in "\"'":
            return self.quoted()
        m = self.UNQUOTED.match(self.s, self.i)
        if not m:
            raise SNBTError(f"bad value at col {self.i}: {self.s[self.i:self.i + 20]!r}")
        self.i = m.end()
        return m.group(0)

    def quoted(self):
        q = self.s[self.i]
        self.i += 1
        out = []
        while self.i < len(self.s):
            ch = self.s[self.i]
            if ch == "\\":
                out.append(self.s[self.i + 1])
                self.i += 2
                continue
            if ch == q:
                self.i += 1
                return "".join(out)
            out.append(ch)
            self.i += 1
        raise SNBTError("unterminated string")

    def key(self):
        c = self.peek()
        if c in "\"'":
            return self.quoted()
        m = self.UNQUOTED.match(self.s, self.i)
        if not m:
            raise SNBTError(f"bad key at col {self.i}: {self.s[self.i:self.i + 20]!r}")
        self.i = m.end()
        return m.group(0)

    def compound(self):
        self.expect("{")
        out = {}
        if self.peek() == "}":
            self.i += 1
            return out
        while True:
            k = self.key()
            self.expect(":")
            out[k] = self.value()
            c = self.peek()
            if c == ",":
                self.i += 1
                continue
            self.expect("}")
            return out

    def list(self):
        self.expect("[")
        if re.match(r"[BIL];", self.s[self.i:self.i + 2]):
            self.i += 2
        out = []
        if self.peek() == "]":
            self.i += 1
            return out
        while True:
            out.append(self.value())
            c = self.peek()
            if c == ",":
                self.i += 1
                continue
            self.expect("]")
            return out


def parse_snbt(s, i=0):
    p = SNBT(s, i)
    v = p.value()
    return v, p.i


# --------------------------------------------------------------- commands ---
COORD = r"(?:[~^](?:[-+]?(?:\d+\.?\d*|\.\d+))?|[-+]?(?:\d+\.?\d*|\.\d+))"
SELECTOR_KEYS = {
    "x", "y", "z", "distance", "dx", "dy", "dz", "x_rotation", "y_rotation", "scores", "tag", "team",
    "name", "type", "predicate", "nbt", "level", "gamemode", "advancements", "limit", "sort",
}


class Ctx:
    def __init__(self, reg, where, refs):
        self.reg, self.where, self.refs = reg, where, refs


def read_word(s, i):
    j = i
    while j < len(s) and s[j] != " ":
        j += 1
    return s[i:j], j


def read_balanced(s, i):
    """Read a token that may contain brackets/quotes, up to a space at depth 0."""
    depth, j, q = 0, i, None
    while j < len(s):
        ch = s[j]
        if q:
            if ch == "\\":
                j += 2
                continue
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
        elif ch in "[{(":
            depth += 1
        elif ch in "]})":
            depth -= 1
        elif ch == " " and depth == 0:
            break
        j += 1
    return s[i:j], j


def check_id(ctx, registry, value, what):
    v = value[10:] if value.startswith("minecraft:") else value
    if ":" in v or registry not in ctx.reg:
        return
    if v not in ctx.reg[registry]:
        err(ctx.where, f"unknown {what} {value!r}")


def parse_selector(ctx, s, i):
    if s[i:i + 1] == "@":
        if i + 1 >= len(s) or s[i + 1] not in "parsen":
            return None
        j = i + 2
        if s[j:j + 1] == "[":
            tok, j2 = read_balanced(s, j)
            inner = tok[1:-1]
            depth, start, parts, q = 0, 0, [], None
            for k, ch in enumerate(inner):
                if q:
                    if ch == q:
                        q = None
                    continue
                if ch in "\"'":
                    q = ch
                elif ch in "[{":
                    depth += 1
                elif ch in "]}":
                    depth -= 1
                elif ch == "," and depth == 0:
                    parts.append(inner[start:k])
                    start = k + 1
            if inner.strip():
                parts.append(inner[start:])
            for part in parts:
                if "=" not in part:
                    err(ctx.where, f"bad selector argument {part!r}")
                    continue
                k, v = part.split("=", 1)
                k, v = k.strip(), v.strip()
                if k not in SELECTOR_KEYS:
                    err(ctx.where, f"unknown selector key {k!r}")
                neg = v.startswith("!")
                v = v.lstrip("!")
                if k == "type" and not v.startswith("#"):
                    check_id(ctx, "entity_type", v, "entity type")
                if k == "predicate":
                    ctx.refs["predicate"].add((v if ":" in v else "minecraft:" + v, ctx.where))
                if k == "nbt":
                    try:
                        parse_snbt(v)
                    except SNBTError as e:
                        err(ctx.where, f"selector nbt: {e}")
                if k == "gamemode" and v not in ("survival", "creative", "adventure", "spectator"):
                    err(ctx.where, f"bad gamemode {v!r}")
                if k == "scores":
                    for m in re.finditer(r"([\w.+\-]+)=", v):
                        ctx.refs["objective"].add((m.group(1), ctx.where))
                _ = neg
            j = j2
        return j
    word, j = read_word(s, i)
    return j if word else None


def parse_argument(ctx, parser, props, s, i):
    """Return end index if the argument parses at s[i:], else None."""
    if i >= len(s):
        return None
    if parser == "brigadier:string":
        t = props.get("type")
        if t == "greedy":
            return len(s)
        if t == "phrase" and s[i] in "\"'":
            _, j = parse_snbt(s, i)
            return j
        w, j = read_word(s, i)
        return j if w else None
    if parser in ("brigadier:integer", "brigadier:long"):
        w, j = read_word(s, i)
        if not re.fullmatch(r"-?\d+", w):
            return None
        if "min" in props and int(w) < props["min"]:
            return None
        if "max" in props and int(w) > props["max"]:
            return None
        return j
    if parser in ("brigadier:float", "brigadier:double"):
        w, j = read_word(s, i)
        if not re.fullmatch(r"-?(\d+\.?\d*|\.\d+)", w):
            return None
        if "min" in props and float(w) < props["min"]:
            return None
        if "max" in props and float(w) > props["max"]:
            return None
        return j
    if parser == "brigadier:bool":
        w, j = read_word(s, i)
        return j if w in ("true", "false") else None
    if parser in ("minecraft:vec3", "minecraft:block_pos"):
        m = re.match(rf"{COORD} {COORD} {COORD}(?= |$)", s[i:])
        return i + m.end() if m else None
    if parser in ("minecraft:vec2", "minecraft:rotation", "minecraft:column_pos"):
        m = re.match(rf"{COORD} {COORD}(?= |$)", s[i:])
        return i + m.end() if m else None
    if parser in ("minecraft:entity", "minecraft:score_holder", "minecraft:game_profile"):
        if parser == "minecraft:entity" and props.get("type") == "players" and s[i:i + 2] in ("@e", "@n"):
            j = parse_selector(ctx, s, i)
            sel = s[i:j]
            if "type=player" not in sel and "type=minecraft:player" not in sel:
                err(ctx.where, f"selector {sel!r} may target non-players")
            return j
        if parser == "minecraft:score_holder" and s[i] == "*":
            return i + 1
        return parse_selector(ctx, s, i)
    if parser in ("minecraft:nbt_compound_tag", "minecraft:nbt_tag", "minecraft:component", "minecraft:style"):
        try:
            v, j = parse_snbt(s, i)
        except SNBTError as e:
            err(ctx.where, f"SNBT: {e}")
            return None
        if j < len(s) and s[j] != " ":
            return None
        if parser == "minecraft:component":
            check_component(ctx, v)
        return j
    if parser == "minecraft:item_stack" or parser == "minecraft:item_predicate":
        tok, j = read_balanced(s, i)
        m = re.match(r"([#a-z0-9_.:/\-*]+)(\[.*\])?$", tok)
        if not m:
            return None
        if not m.group(1).startswith("#") and m.group(1) != "*":
            check_id(ctx, "item", m.group(1), "item")
        if m.group(2):
            inner = m.group(2)[1:-1]
            p = SNBT(inner)
            try:
                while p.i < len(inner):
                    p.ws()
                    k = p.key()
                    if p.peek() == ":":  # namespaced key
                        p.i += 1
                        k = k + ":" + p.key()
                    if parser == "minecraft:item_predicate" and p.peek() == "~":
                        p.i += 1  # partial match: key~{...}
                    else:
                        p.expect("=")
                    p.value()
                    check_id(ctx, "data_component_type", k, "item component")
                    if p.peek() == ",":
                        p.i += 1
                    elif p.i < len(inner):
                        raise SNBTError(f"junk after component {k}")
            except SNBTError as e:
                err(ctx.where, f"item components: {e}")
        return j
    if parser == "minecraft:particle":
        tok, j = read_balanced(s, i)
        m = re.match(r"([a-z0-9_.:/\-]+)(\{.*\})?$", tok)
        if not m:
            return None
        check_id(ctx, "particle_type", m.group(1), "particle")
        if m.group(2):
            try:
                parse_snbt(m.group(2))
            except SNBTError as e:
                err(ctx.where, f"particle options: {e}")
        return j
    if parser == "minecraft:function":
        w, j = read_word(s, i)
        if not w.startswith("#"):
            ctx.refs["function"].add((w, ctx.where))
        return j
    if parser == "minecraft:resource":
        w, j = read_word(s, i)
        reg = props.get("registry", "").replace("minecraft:", "")
        check_id(ctx, reg, w, reg)
        return j
    if parser == "minecraft:resource_location":
        w, j = read_word(s, i)
        if not re.fullmatch(r"[a-z0-9_.\-]+(:[a-z0-9_.\-/]+)?", w):
            return None
        return j
    if parser == "minecraft:objective":
        w, j = read_word(s, i)
        ctx.refs["objective"].add((w, ctx.where))
        return j
    if parser == "minecraft:operation":
        w, j = read_word(s, i)
        return j if w in ("=", "+=", "-=", "*=", "/=", "%=", "<", ">", "><") else None
    if parser == "minecraft:message":
        return len(s)
    if parser == "minecraft:loot_predicate" and s[i] not in "{[":
        w, j = read_word(s, i)
        ctx.refs["predicate"].add((w if ":" in w else "minecraft:" + w, ctx.where))
        return j
    if parser == "minecraft:slot_source":
        tok, j = read_balanced(s, i)
        if tok.startswith(("{", "[")):  # typed slot source, e.g. {type:"slot_range",...}
            return j
        groups = {"container": 54, "inventory": 27, "enderchest": 27, "hotbar": 9,
                  "horse": 15, "mob.inventory": 8, "player.crafting": 4}
        named = {"weapon", "weapon.mainhand", "weapon.offhand", "weapon.*", "saddle", "contents",
                 "player.cursor", "armor.head", "armor.chest", "armor.legs", "armor.feet",
                 "armor.body", "armor.*", "horse.chest"}
        if tok in named:
            return j
        base, _, idx = tok.rpartition(".")
        if base in groups and (idx == "*" or (idx.isdigit() and int(idx) < groups[base])):
            return j
        err(ctx.where, f"{tok!r} is not a valid item slot")
        return j
    if parser in ("minecraft:nbt_path", "minecraft:loot_modifier",
                  "minecraft:block_predicate", "minecraft:block_state", "minecraft:loot_predicate",
                  "minecraft:loot_table"):
        tok, j = read_balanced(s, i)
        return j if tok else None
    # everything else is a single word (objective criteria, int ranges, ...)
    w, j = read_word(s, i)
    return j if w else None


def check_component(ctx, v):
    """Light checks on SNBT text components."""
    if isinstance(v, list):
        for x in v:
            check_component(ctx, x)
    elif isinstance(v, dict):
        known = {"text", "translate", "with", "fallback", "score", "selector", "separator", "keybind",
                 "nbt", "storage", "entity", "block", "interpret", "source", "plain", "extra", "color",
                 "font", "bold", "italic", "underlined", "strikethrough", "obfuscated", "shadow_color",
                 "insertion", "click_event", "hover_event", "type", "object", "sprite", "atlas", "player"}
        for k in v:
            if k not in known:
                err(ctx.where, f"unknown text component key {k!r}")
        if "score" in v and isinstance(v["score"], dict):
            ctx.refs["objective"].add((v["score"].get("objective"), ctx.where))
        if "extra" in v:
            check_component(ctx, v["extra"])


def walk(ctx, tree, root, node, s, i):
    """True if s[i:] completes a command from `node`."""
    if i >= len(s):
        return bool(node.get("executable"))
    if s[i] != " ":
        return False
    i += 1
    if "redirect" in node:
        target = root
        for name in node["redirect"]:
            target = target["children"][name]
        node = target
    for name, child in node.get("children", {}).items():
        if child["type"] == "literal":
            if s.startswith(name, i) and (i + len(name) == len(s) or s[i + len(name)] == " "):
                j = i + len(name)
                if not child.get("children") and "redirect" not in child and not child.get("executable"):
                    # `execute ... run <command>`
                    if j < len(s) and walk_root(ctx, tree, s, j + 1):
                        return True
                    continue
                if walk(ctx, tree, root, child, s, j):
                    return True
        else:
            try:
                j = parse_argument(ctx, child.get("parser"), child.get("properties", {}), s, i)
            except SNBTError:
                j = None
            if j is not None and walk(ctx, tree, root, child, s, j):
                return True
    return False


def walk_root(ctx, tree, s, i=0):
    word, j = read_word(s, i)
    child = tree["children"].get(word)
    if child is None:
        err(ctx.where, f"unknown command {word!r}")
        return True  # already reported
    return walk(ctx, tree, tree, child, s, j)


# ------------------------------------------------------------- validation ---
def validate_functions(tree, reg, refs, sounds):
    fdir = DP / "data"
    known_functions = set()
    for f in fdir.glob("*/function/**/*.mcfunction"):
        ns = f.relative_to(fdir).parts[0]
        rel = f.relative_to(fdir / ns / "function").with_suffix("").as_posix()
        known_functions.add(f"{ns}:{rel}")
    declared_objectives = set()
    count = 0
    for f in sorted(fdir.glob("*/function/**/*.mcfunction")):
        lines = f.read_text().splitlines()
        for n, raw in enumerate(lines, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            where = f"{f.relative_to(ROOT)}:{n}"
            if raw != raw.rstrip():
                err(where, "trailing whitespace")
            if line.startswith("$"):
                macro_args = set(re.findall(r"\$\((\w+)\)", line))
                refs["macro"].add((f.relative_to(fdir).as_posix(), frozenset(macro_args), where))
                sample = {"d": "4.5", "amount": "600", "item": "minecraft:coal"}
                line = re.sub(r"\$\((\w+)\)", lambda m: sample.get(m.group(1), "1"), line[1:])
            m = re.match(r"scoreboard objectives add (\S+)", line)
            if m:
                declared_objectives.add(m.group(1))
            for snd in re.findall(r"\bplaysound (\S+)", line):
                if snd.startswith("mastercycle:"):
                    if snd.split(":", 1)[1] not in sounds:
                        err(where, f"sound event {snd} is not defined in sounds.json")
                else:
                    check_id(Ctx(reg, where, refs), "sound_event", snd, "sound event")
            ctx = Ctx(reg, where, refs)
            count += 1
            if not walk_root(ctx, tree, line):
                err(where, f"does not parse against the command tree: {line[:120]}")
    for name, where in refs["function"]:
        if name not in known_functions:
            err(where, f"function {name} does not exist")
    for name, where in refs["objective"]:
        if name and name not in declared_objectives:
            err(where, f"scoreboard objective {name!r} is never created")
    for f in fdir.glob("*/tags/function/*.json"):
        for v in json.loads(f.read_text())["values"]:
            if v not in known_functions:
                err(str(f.relative_to(ROOT)), f"function tag references missing {v}")
    return count, known_functions


def check_predicate(where, cond, reg):
    t = cond.get("type", "").replace("minecraft:", "")
    if "condition" in cond:
        err(where, "26.3 loot conditions use 'type', not 'condition'")
    if t not in reg["loot_condition_type"]:
        err(where, f"unknown loot condition type {t!r}")
    if t in ("any_of", "all_of"):
        for term in cond["terms"]:
            check_predicate(where, term, reg)
    if t == "entity_properties":
        check_entity_predicate(where, cond.get("predicate", {}), reg)


def check_entity_predicate(where, pred, reg):
    for k, v in pred.items():
        if not k.startswith("minecraft:"):
            err(where, f"entity predicate key {k!r} must be namespaced in 26.3")
            continue
        key = k[10:]
        if key not in reg["entity_sub_predicate_type"]:
            err(where, f"unknown entity sub-predicate {k!r}")
        if key in ("vehicle", "passenger", "targeted_entity"):
            check_entity_predicate(where, v, reg)
        if key == "entity_type" and isinstance(v, str) and not v.startswith("#"):
            if v.replace("minecraft:", "") not in reg["entity_type"]:
                err(where, f"unknown entity type {v}")
        if key == "equipment":
            for slot, item_pred in v.items():
                items = item_pred.get("items", [])
                for it in [items] if isinstance(items, str) else items:
                    if it.replace("minecraft:", "") not in reg["item"]:
                        err(where, f"unknown item {it}")
                for comp in item_pred.get("predicates", {}):
                    if comp.replace("minecraft:", "") not in reg["data_component_predicate_type"]:
                        err(where, f"unknown item sub-predicate {comp}")


def validate_datapack_json(reg, refs, known_functions):
    pdir = DP / "data"
    known_preds = set()
    for f in pdir.glob("*/predicate/**/*.json"):
        ns = f.relative_to(pdir).parts[0]
        known_preds.add(f"{ns}:{f.relative_to(pdir / ns / 'predicate').with_suffix('').as_posix()}")
        check_predicate(str(f.relative_to(ROOT)), json.loads(f.read_text()), reg)
    for name, where in refs["predicate"]:
        if name not in known_preds:
            err(where, f"predicate {name} does not exist")
    for f in pdir.glob("*/recipe/*.json"):
        r = json.loads(f.read_text())
        for comp in r.get("result", {}).get("components", {}):
            if comp.replace("minecraft:", "") not in reg["data_component_type"]:
                err(str(f.relative_to(ROOT)), f"unknown component {comp}")
        for v in r.get("key", {}).values():
            if v.replace("minecraft:", "") not in reg["item"]:
                err(str(f.relative_to(ROOT)), f"unknown item {v}")
    # macro functions must be called with the arguments they use
    calls = {}
    for f in pdir.glob("*/function/**/*.mcfunction"):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            for m in re.finditer(r"function (\S+) (\{[^}]*\})", line):
                keys = set(re.findall(r"(\w+):", m.group(2)))
                calls.setdefault(m.group(1), []).append(keys)
            for m in re.finditer(r"function (\S+) with storage \S+ (\S+)", line):
                calls.setdefault(m.group(1), []).append(None)
    for path, args, where in refs["macro"]:
        ns, _, rest = path.partition("/function/")
        name = f"{ns}:{rest[:-len('.mcfunction')]}"
        if name not in calls:
            err(where, f"macro function {name} is never called with arguments")
        for keys in calls.get(name, []):
            if keys is not None and not args <= keys:
                err(where, f"call to {name} is missing macro args {sorted(args - keys)}")


def validate_resourcepack(reg):
    mdir = RP / "assets"
    for f in mdir.glob("*/items/*.json"):
        where = str(f.relative_to(ROOT))
        if f.stem not in reg["item"]:
            err(where, f"no vanilla item named {f.stem}")

        def walk_model(m):
            t = m["type"].replace("minecraft:", "")
            if t not in ("model", "range_dispatch", "select", "condition", "composite", "empty", "special",
                         "bundle/selected_item"):
                err(where, f"unknown item model type {t}")
            if t == "model":
                ns, path = m["model"].split(":")
                if not (mdir / ns / "models" / f"{path}.json").exists() and ns != "minecraft":
                    err(where, f"missing model {m['model']}")
                if ns == "minecraft" and not (mdir / ns / "models" / f"{path}.json").exists():
                    if path not in ("item/warped_fungus_on_a_stick",):
                        err(where, f"missing model {m['model']}")
            for e in m.get("entries", []):
                walk_model(e["model"])
            if "fallback" in m:
                walk_model(m["fallback"])

        walk_model(json.loads(f.read_text())["model"])
    for f in mdir.glob("*/models/**/*.json"):
        where = str(f.relative_to(ROOT))
        model = json.loads(f.read_text())
        for slot, ref in model.get("textures", {}).items():
            if ref.startswith("#"):
                continue
            ns, path = ref.split(":")
            if not (mdir / ns / "textures" / f"{path}.png").exists():
                err(where, f"texture {ref} missing")
        for el in model.get("elements", []):
            for v in el["from"] + el["to"]:
                if not -16 <= v <= 32:
                    err(where, f"element {el.get('name')} out of bounds ({v})")
            if "shade" in el:
                err(where, "'shade' was replaced by 'shade_direction_override' in 26.3")
            for face, spec in el["faces"].items():
                if spec["texture"].lstrip("#") not in model["textures"]:
                    err(where, f"face uses undefined texture {spec['texture']}")
        for a, fa, b, fb, area in zfight_pairs(model, plane_eps=0.02):
            err(where, f"z-fighting: {a}.{fa} and {b}.{fb} are coplanar and overlap ({area:.2f} sq units)")
        for ctx_name, tr in model.get("display", {}).items():
            if any(not -80 <= v <= 80 for v in tr.get("translation", [])):
                err(where, f"display.{ctx_name}.translation outside [-80, 80]")
            if any(not -4 <= v <= 4 for v in tr.get("scale", [])):
                err(where, f"display.{ctx_name}.scale outside [-4, 4]")
    sounds = json.loads((mdir / "mastercycle" / "sounds.json").read_text())
    for event, spec in sounds.items():
        for s in spec["sounds"]:
            ns, path = s["name"].split(":")
            if not (mdir / ns / "sounds" / f"{path}.ogg").exists():
                err("sounds.json", f"{event}: missing {path}.ogg")
    return set(sounds)


def fmt(v):
    """pack.mcmeta format -> (major, minor); a bare int means minor 0."""
    if isinstance(v, int):
        return (v, 0)
    return (v[0], v[1] if len(v) > 1 else 0)


def validate_pack_meta(version_info):
    for kind, root, major_key, minor_key in (
            ("data pack", DP, "data_pack_version", "data_pack_version_minor"),
            ("resource pack", RP, "resource_pack_version", "resource_pack_version_minor")):
        where = str((root / "pack.mcmeta").relative_to(ROOT))
        pack = json.loads((root / "pack.mcmeta").read_text())["pack"]
        game = (version_info[major_key], version_info.get(minor_key, 0))
        if "min_format" not in pack or "max_format" not in pack:
            err(where, "needs min_format and max_format")
            continue
        lo, hi = fmt(pack["min_format"]), fmt(pack["max_format"])
        if not lo <= game <= hi:
            err(where, f"{kind} supports formats {lo}..{hi}, but Minecraft "
                       f"{version_info['id']} is {game[0]}.{game[1]} - the game would mark it incompatible")
        if "pack_format" in pack and pack["pack_format"] != game[0]:
            err(where, f"pack_format {pack['pack_format']} should be the major format {game[0]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="26.3")
    args = ap.parse_args()
    tree = fetch(args.version, "commands/data.json")
    reg = fetch(args.version, "registries/data.json")
    validate_pack_meta(fetch(args.version, "version.json"))
    reg = {k: set(v) for k, v in reg.items()}
    for f in list(DP.rglob("*.json")) + list(RP.rglob("*.json")) + [DP / "pack.mcmeta", RP / "pack.mcmeta"]:
        try:
            json.loads(f.read_text())
        except json.JSONDecodeError as e:
            err(str(f.relative_to(ROOT)), f"invalid JSON: {e}")
    refs = {"function": set(), "objective": set(), "predicate": set(), "macro": set()}
    sounds = validate_resourcepack(reg)
    n, known = validate_functions(tree, reg, refs, sounds)
    validate_datapack_json(reg, refs, known)
    if errors:
        print("\n".join(sorted(set(errors))))
        print(f"\n{len(set(errors))} problem(s) found")
        sys.exit(1)
    print(f"OK: {n} commands in {len(known)} functions parse against Minecraft {args.version}; "
          f"all references, ids and JSON check out")


if __name__ == "__main__":
    main()
