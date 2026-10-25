"""Vanilla Minecraft 26.3 reference data, fetched once and cached.

The datapack tools validate against the real game, not against memory: the Brigadier command
tree, every registry (blocks, items, entity types, sound events, damage types, memory types,
game rules), every block's state properties, the contents of every vanilla tag, the vanilla
`sounds.json`, and the village structure templates. All of it comes from misode/mcmeta, which
publishes the files Minecraft's own data generator writes, tagged per release. The tag is
pinned to `26.3`, the pack's target; change VERSION to move.

Files are cached under `tools/.mcdata/<version>/` (git-ignored) so a validation run is offline
after the first.

    from mcdata import MC
    MC.registry("block")            # ["minecraft:acacia_button", ...] as ids without namespace
    MC.block_states("oak_stairs")   # {"facing": [...], "half": [...], ...}
    MC.tag("block", "wooden_doors") # resolved, recursively, to plain block ids
    MC.commands()                   # the Brigadier tree
    MC.structure("village/plains/houses/plains_small_house_1")   # parsed NBT
"""
import gzip
import io
import json
import struct
import time
import urllib.request
from pathlib import Path

VERSION = "26.3"
DATA_PACK_FORMAT = 121
RESOURCE_PACK_FORMAT = (97, 1)
RAW = "https://raw.githubusercontent.com/misode/mcmeta"
CACHE = Path(__file__).resolve().parent / ".mcdata" / VERSION


def _fetch(branch, path):
    dest = CACHE / branch / path
    if dest.exists():
        return dest.read_bytes()
    url = f"{RAW}/{VERSION}-{branch}/{path}"
    last = None
    for wait in (0, 2, 4, 8):
        time.sleep(wait)
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                data = r.read()
            break
        except Exception as e:                       # network: retry, then give up loudly
            last = e
            if getattr(e, "code", None) == 404:
                raise FileNotFoundError(url) from e
    else:
        raise RuntimeError(f"could not fetch {url}: {last}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return data


def _strip(i):
    return i[10:] if i.startswith("minecraft:") else i


class _MC:
    version = VERSION

    def __init__(self):
        self._reg = None
        self._blocks = None
        self._tags = {}

    # ------------------------------------------------------------------ summary
    def commands(self):
        return json.loads(_fetch("summary", "commands/data.json"))

    def registries(self):
        if self._reg is None:
            self._reg = json.loads(_fetch("summary", "registries/data.json"))
        return self._reg

    def registry(self, name):
        return set(self.registries()[name])

    def blocks(self):
        if self._blocks is None:
            self._blocks = json.loads(_fetch("summary", "blocks/data.json"))
        return self._blocks

    def block_states(self, block):
        """{property: [values]} for a block id (namespace optional)."""
        entry = self.blocks().get(_strip(block))
        return {} if entry is None else entry[0]

    def block_defaults(self, block):
        entry = self.blocks().get(_strip(block))
        return {} if entry is None else entry[1]

    # ------------------------------------------------------------------ tags
    def tag_exists(self, kind, name):
        return _strip(name) in self.registry(f"tag/{kind}")

    def tag(self, kind, name, _seen=None):
        """A vanilla tag resolved to plain ids (no namespace), recursively."""
        key = (kind, _strip(name))
        if key in self._tags:
            return self._tags[key]
        seen = _seen or set()
        if key in seen:
            return set()
        seen.add(key)
        doc = json.loads(_fetch("data", f"data/minecraft/tags/{kind}/{_strip(name)}.json"))
        out = set()
        for v in doc["values"]:
            v = v["id"] if isinstance(v, dict) else v
            if v.startswith("#"):
                out |= self.tag(kind, v[1:], seen)
            else:
                out.add(_strip(v))
        self._tags[key] = out
        return out

    # ------------------------------------------------------------------ assets / data
    def sounds(self):
        return json.loads(_fetch("assets", "assets/minecraft/sounds.json"))

    def atlas(self, name):
        return json.loads(_fetch("assets", f"assets/minecraft/atlases/{name}.json"))

    def structure(self, path):
        return read_nbt(_fetch("data", f"data/minecraft/structure/{path}.nbt"))

    def template_pool(self, path):
        return json.loads(_fetch("data", f"data/minecraft/worldgen/template_pool/{path}.json"))


MC = _MC()


# ====================================================================== NBT

def read_nbt(data):
    """Parse (optionally gzipped) binary NBT into plain Python values. Compounds become
    dicts, lists lists, arrays lists of ints."""
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    f = io.BytesIO(data)

    def u(fmt):
        return struct.unpack(">" + fmt, f.read(struct.calcsize(fmt)))[0]

    def string():
        n = u("H")
        return f.read(n).decode("utf-8", "replace")

    def payload(t):
        if t == 1:
            return u("b")
        if t == 2:
            return u("h")
        if t == 3:
            return u("i")
        if t == 4:
            return u("q")
        if t == 5:
            return u("f")
        if t == 6:
            return u("d")
        if t == 7:
            return list(f.read(u("i")))
        if t == 8:
            return string()
        if t == 9:
            et, n = u("b"), u("i")
            return [payload(et) for _ in range(n)]
        if t == 10:
            out = {}
            while True:
                ct = u("b")
                if ct == 0:
                    return out
                name = string()             # read the name BEFORE the payload
                out[name] = payload(ct)
        if t == 11:
            return [u("i") for _ in range(u("i"))]
        if t == 12:
            return [u("q") for _ in range(u("i"))]
        raise ValueError(f"bad NBT tag {t}")

    t = u("b")
    string()
    return payload(t)


if __name__ == "__main__":
    reg = MC.registries()
    print(f"Minecraft {VERSION}: {len(reg)} registries, {len(MC.blocks())} blocks, "
          f"{len(reg['sound_event'])} sound events, {len(reg['tag/block'])} block tags")
    s = MC.structure("village/plains/houses/plains_small_house_1")
    print("plains_small_house_1:", s["size"], len(s["blocks"]), "blocks,",
          len(s["palette"]), "palette entries")
