#!/usr/bin/env python3
"""Build, check and zip the Master Cycle packs.

    python3 master-cycle/tools/package.py

1. regenerates the resource pack (model, textures, sounds)
2. validates every command / JSON file against Minecraft 26.3
3. runs the driving-logic simulation tests
4. checks a player in the riding pose fits on the bike (docs/rider-preview.png)
5. renders docs/model-preview.png
6. writes dist/MasterCycle.zip - one file that is both the data pack and the
   resource pack - plus the two packs separately (MasterCycle-datapack.zip,
   MasterCycle-resourcepack.zip) for servers
"""

import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
DIST = ROOT / "dist"


def run(script):
    print(f"== {script}")
    subprocess.run([sys.executable, str(TOOLS / script)], check=True)


def zip_dir(src: Path, dest: Path):
    """Deterministic zip: sorted entries, fixed timestamps, pack.mcmeta at the root."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(p for p in src.rglob("*") if p.is_file()):
            info = zipfile.ZipInfo(f.relative_to(src).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, f.read_bytes())
    print(f"   wrote {dest.relative_to(ROOT.parent)} ({dest.stat().st_size // 1024} KiB)")


def main():
    run("build_resourcepack.py")
    run("validate.py")
    run("sim_test.py")
    run("rider_fit.py")
    run("render_preview.py")
    print("== zip")
    zip_dir(ROOT / "datapack", DIST / "MasterCycle-datapack.zip")
    zip_dir(ROOT / "resourcepack", DIST / "MasterCycle-resourcepack.zip")
    combined()


def combined():
    """MasterCycle.zip: ONE pack that is both the data pack and the resource
    pack. The data-pack loader reads data/, the resource-pack loader reads
    assets/, so the same file goes in the world's datapacks folder and in
    resourcepacks. Its format range must contain both of 26.3's formats
    (data 121.0, resources 97.1)."""
    import json
    info = json.loads((TOOLS / ".cache" / "26.3" / "version.json").read_text())
    data_fmt = [info["data_pack_version"], info.get("data_pack_version_minor", 0)]
    res_fmt = [info["resource_pack_version"], info.get("resource_pack_version_minor", 0)]
    lo, hi = min(data_fmt, res_fmt), max(data_fmt, res_fmt)
    meta = {"pack": {
        "description": [{"text": "Master Cycle ", "color": "aqua"},
                        {"text": "bike, riding & sounds (one file)", "color": "gray"}],
        "min_format": [lo[0], 0],
        "max_format": hi,
    }}
    assert [meta["pack"]["min_format"], meta["pack"]["max_format"]] and \
        meta["pack"]["min_format"] <= data_fmt <= meta["pack"]["max_format"] and \
        meta["pack"]["min_format"] <= res_fmt <= meta["pack"]["max_format"]
    dest = DIST / "MasterCycle.zip"
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        def add(arc, data):
            info = zipfile.ZipInfo(arc, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data)
        add("pack.mcmeta", json.dumps(meta, indent=2) + "\n")
        add("pack.png", (ROOT / "resourcepack" / "pack.png").read_bytes())
        for src in (ROOT / "datapack" / "data", ROOT / "resourcepack" / "assets"):
            for f in sorted(p for p in src.rglob("*") if p.is_file()):
                add(f.relative_to(src.parent).as_posix(), f.read_bytes())
    print(f"   wrote {dest.relative_to(ROOT.parent)} ({dest.stat().st_size // 1024} KiB) - data + resource pack in one")


if __name__ == "__main__":
    main()
