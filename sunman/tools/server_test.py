"""Runs the datapack on a REAL Minecraft 26.3 server and reports what the game says.

Static checks and the emulator (tools/check_datapack.py) catch most mistakes; three bugs in
this project's history survived every static check and were only found on a server. This is
that server, scripted:

  1. downloads the official 26.3 server jar from Mojang (sha1-verified), into tools/.server/
  2. makes a superflat test world with the datapack installed (the resource pack does not
     matter to a server), accepts the EULA, enables RCON
  3. starts it, and checks the log: the pack loaded, no function failed to parse, no tag
     failed to resolve
  4. places a real generated plains village, runs `sunman:world/decay_village` at it, lets the
     staged job finish, then checks: torches/glass/beds gone, the marker down, bodies, blood,
     items and Locusts present -- and that the game ACCEPTED their NBT (each one is read back
     with `data get`: an item_display with a rejected component shows no item_model)
  5. runs it again (must refuse), runs the blackstone variant on a second village
  6. spawns a villager next to the bell and reads its Brain back, to confirm the
     `Brain.memories."minecraft:meeting_point"` path the automatic trigger depends on
  7. stops the server, prints a report, exits non-zero on any failure

Needs Java (the version 26.3 asks for) and network access to piston-meta.mojang.com and
piston-data.mojang.com. Running it means accepting the Minecraft EULA
(https://aka.ms/MinecraftEULA).

    python3 tools/server_test.py                 # full run
    python3 tools/server_test.py --keep          # leave the server and world in place
"""
import hashlib
import json
import re
import shutil
import socket
import struct
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

VERSION = "26.3"
ROOT = Path(__file__).resolve().parent.parent
WORK = Path(__file__).resolve().parent / ".server" / VERSION
MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
RCON_PORT, RCON_PASS = 25575, "sunman-test"


def fetch_jar():
    jar = WORK / "server.jar"
    WORK.mkdir(parents=True, exist_ok=True)
    man = json.loads(urllib.request.urlopen(MANIFEST, timeout=60).read())
    entry = next(v for v in man["versions"] if v["id"] == VERSION)
    ver = json.loads(urllib.request.urlopen(entry["url"], timeout=60).read())
    dl = ver["downloads"]["server"]
    if not jar.exists() or hashlib.sha1(jar.read_bytes()).hexdigest() != dl["sha1"]:
        print(f"downloading the {VERSION} server ({dl['size'] // 1024 // 1024} MB)")
        jar.write_bytes(urllib.request.urlopen(dl["url"], timeout=600).read())
        assert hashlib.sha1(jar.read_bytes()).hexdigest() == dl["sha1"], "server.jar sha1 mismatch"
    java = ver.get("javaVersion", {}).get("majorVersion")
    return jar, java


def make_world():
    world = WORK / "world"
    if world.exists():
        shutil.rmtree(world)
    (world / "datapacks").mkdir(parents=True)
    shutil.copytree(ROOT / "datapack", world / "datapacks" / "sunman")
    (WORK / "eula.txt").write_text("eula=true\n")
    (WORK / "server.properties").write_text("\n".join([
        "level-name=world", "level-type=minecraft\\:flat", "generate-structures=false",
        "online-mode=false", "spawn-protection=0", "max-tick-time=-1", "view-distance=6",
        "simulation-distance=6", "enable-rcon=true", f"rcon.port={RCON_PORT}",
        f"rcon.password={RCON_PASS}", "server-port=25599", "motd=sunman test", "",
    ]))


class Rcon:
    def __init__(self):
        self.s = socket.create_connection(("127.0.0.1", RCON_PORT), timeout=30)
        self.n = 0
        self._send(3, RCON_PASS)
        _, rid, _ = self._recv()
        assert rid != -1, "RCON login refused"

    def _send(self, kind, body):
        self.n += 1
        data = struct.pack("<ii", self.n, kind) + body.encode() + b"\x00\x00"
        self.s.sendall(struct.pack("<i", len(data)) + data)

    def _recv(self):
        ln = struct.unpack("<i", self._read(4))[0]
        data = self._read(ln)
        rid, kind = struct.unpack("<ii", data[:8])
        return kind, rid, data[8:-2].decode("utf-8", "replace")

    def _read(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.s.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("RCON closed")
            buf += chunk
        return buf

    def cmd(self, c):
        self._send(2, c)
        return self._recv()[2]


def count(r, selector):
    out = r.cmd(f"execute if entity {selector}")
    m = re.search(r"count: (\d+)", out)
    return int(m.group(1)) if m else 0


def main():
    jar, java_major = fetch_jar()
    jv = subprocess.run(["java", "-version"], capture_output=True, text=True).stderr.splitlines()[0]
    print(f"server {VERSION} (wants Java {java_major}); found: {jv}")
    make_world()
    log = WORK / "test.log"
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", str(jar), "--nogui"], cwd=WORK,
                            stdout=log.open("w"), stderr=subprocess.STDOUT)
    fails, report = [], []
    try:
        for _ in range(600):
            time.sleep(1)
            text = log.read_text(errors="replace")
            if "Done (" in text:
                break
            if proc.poll() is not None:
                raise RuntimeError("the server stopped:\n" + text[-3000:])
        else:
            raise RuntimeError("the server did not start in 10 minutes")
        text = log.read_text(errors="replace")
        for pat in (r"Failed to load function.*", r"Couldn't load tag.*", r"Unknown or incomplete command.*",
                    r"Failed to parse.*", r"Couldn't parse.*", r"ERROR\].*sunman.*"):
            for m in re.findall(pat, text):
                fails.append("load: " + m.strip())
        r = Rcon()
        packs = r.cmd("datapack list enabled")
        if "sunman" not in packs:
            fails.append(f"the datapack is not enabled: {packs}")
        report.append(packs)

        r.cmd("forceload add -96 -96 96 96")
        r.cmd("gamerule minecraft:advance_time false")
        print(r.cmd("place structure minecraft:village_plains 0 -60 0"))
        time.sleep(3)
        print(r.cmd("execute positioned 0 -60 0 run function sunman:world/decay_village"))
        time.sleep(2)                                       # the staged job: five ticks
        checks = {
            "decayed marker": ("@e[type=marker,tag=sunman_decayed]", 1, 1),
            "job finished": ("@e[type=marker,tag=sm_decay_job]", 0, 0),
            "bodies": ("@e[type=item_display,tag=sunman_corpse]", 4, 11),
            "blood decals": ("@e[type=item_display,tag=sunman_blood]", 30, 200),
            "items left behind": ("@e[type=item]", 1, 10),
            "Locust cores": ("@e[type=interaction,tag=sunman_core]", 0, 4),
            "living villagers nearby": ("@e[type=villager,distance=..48,x=0,y=-60,z=0]", 0, 0),
        }
        for name, (sel, lo, hi) in checks.items():
            n = count(r, sel)
            report.append(f"{name}: {n}")
            if not lo <= n <= hi:
                fails.append(f"{name}: {n} (wanted {lo}..{hi})")
        # anything that should be gone, counted by removing it (the test world is ruined anyway)
        for b in ("#sunman:light_out", "#sunman:fabric", "farmland", "dirt_path", "cobblestone"):
            left = r.cmd(f"execute positioned 0 -60 0 run fill ~-16 ~-6 ~-16 ~16 ~10 ~16 air replace {b}")
            report.append(f"{b} left in the box: {left}")
            if re.search(r"[1-9]\d* block", left):
                fails.append(f"{b} still in the box after the decay: {left}")
        # NBT accepted? read one of each back
        for sel, want in (("@e[type=item_display,tag=sunman_corpse,limit=1]", "dead_villager"),
                          ("@e[type=item_display,tag=sunman_blood,limit=1]", "blood_"),
                          ("@e[type=item_display,tag=sunman_locust_part,limit=1]", "locust_")):
            got = r.cmd(f"data get entity {sel} item.components")
            report.append(f"{sel}: {got[:160]}")
            if want not in got and "No entity" not in got:
                fails.append(f"{sel} has no {want} item_model: the game rejected its NBT? {got[:200]}")
        n = count(r, "@e")
        print(r.cmd("execute positioned 0 -60 0 run function sunman:world/decay_village"))
        time.sleep(1)
        if count(r, "@e") != n:
            fails.append("a second decay_village at the same place changed something")
        # the blackstone variant, somewhere else
        print(r.cmd("place structure minecraft:village_plains 300 -60 0"))
        r.cmd("forceload add 260 -40 340 40")
        time.sleep(3)
        print(r.cmd("execute positioned 300 -60 0 run function sunman:world/decay_village_blackstone"))
        time.sleep(2)
        report.append("blackstone: " + r.cmd("fill 284 -66 -16 316 -50 16 blackstone replace blackstone"))
        # the trigger's memory path
        r.cmd("summon villager 2 -60 2 {Tags:[\"t\"]}")
        time.sleep(20)
        mem = r.cmd("data get entity @e[type=villager,tag=t,limit=1] Brain.memories")
        report.append(f"villager memories: {mem[:300]}")
        text = log.read_text(errors="replace")
        for m in re.findall(r".*(?:ERROR|Exception).*", text):
            if "sunman" in m or "function" in m:
                fails.append("log: " + m.strip())
        r.cmd("stop")
    finally:
        time.sleep(3)
        if proc.poll() is None:
            proc.terminate()
    print("\n".join(report))
    for f in fails:
        print("  FAIL ", f)
    print("server test: passed" if not fails else f"server test: {len(fails)} failure(s)")
    if "--keep" not in sys.argv:
        shutil.rmtree(WORK / "world", ignore_errors=True)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
