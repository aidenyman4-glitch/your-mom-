#!/usr/bin/env bash
# Build an installable zip of the extension into dist/.
#
# The zip has manifest.json at its root, which is what both "Load unpacked"
# (after unzipping) and a Chrome Web Store upload expect.
set -euo pipefail

cd "$(dirname "$0")/.."
version="$(python3 -c "import json;print(json.load(open('extension/manifest.json'))['version'])")"
out="dist/67-jumpscare-v${version}.zip"

mkdir -p dist
rm -f "$out"

# -x excludes editor leftovers; the SVG icon source is build input, not runtime.
( cd extension && zip -q -r -X "../$out" . \
    -x '*.DS_Store' -x '__MACOSX/*' -x '*.swp' )

echo "built $out"
unzip -l "$out"
