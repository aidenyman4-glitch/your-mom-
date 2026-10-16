#!/usr/bin/env python3
"""Build, check and zip the Master Cycle packs.

    python3 master-cycle/tools/package.py

1. regenerates the resource pack (model, textures, sounds)
2. validates every command / JSON file against Minecraft 26.3
3. runs the driving-logic simulation tests
4. renders docs/model-preview.png
5. writes dist/MasterCycle-datapack.zip and dist/MasterCycle-resourcepack.zip
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
    run("render_preview.py")
    print("== zip")
    zip_dir(ROOT / "datapack", DIST / "MasterCycle-datapack.zip")
    zip_dir(ROOT / "resourcepack", DIST / "MasterCycle-resourcepack.zip")


if __name__ == "__main__":
    main()
