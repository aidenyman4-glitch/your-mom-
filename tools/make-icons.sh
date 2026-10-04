#!/usr/bin/env bash
# Regenerate the extension's PNG icons from extension/assets/icon.svg.
#
# Rasterizes once at 512px, then downscales to the four sizes Chrome asks for.
# Uses rsvg-convert if present; otherwise falls back to headless Chromium.
set -euo pipefail

cd "$(dirname "$0")/.."
src="extension/assets/icon.svg"
out="extension/assets"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

master="$tmp/icon512.png"

if command -v rsvg-convert >/dev/null 2>&1; then
  rsvg-convert -w 512 -h 512 -o "$master" "$src"
else
  chrome=""
  for candidate in "${CHROME:-}" chromium chromium-browser google-chrome \
                   /opt/pw-browsers/chromium/chrome-linux/chrome \
                   /opt/pw-browsers/chromium-*/chrome-linux/chrome; do
    [ -n "$candidate" ] || continue
    if command -v "$candidate" >/dev/null 2>&1 || [ -x "$candidate" ]; then
      chrome="$candidate"
      break
    fi
  done
  if [ -z "$chrome" ]; then
    echo "error: need rsvg-convert or Chromium to rasterize $src" >&2
    exit 1
  fi

  # Chromium screenshots a page, not a file, so give it a page that is exactly
  # the icon: no margins, no scrollbars, transparent behind the artwork.
  {
    printf '<!doctype html><meta charset="utf-8"><style>'
    printf 'html,body{margin:0;padding:0;background:transparent;overflow:hidden}'
    printf 'svg{display:block;width:512px;height:512px}'
    printf '</style>'
    cat "$src"
  } > "$tmp/icon.html"

  "$chrome" --headless --no-sandbox --disable-gpu --hide-scrollbars \
    --window-size=512,512 --default-background-color=00000000 \
    --screenshot="$master" "$tmp/icon.html" >/dev/null 2>&1
fi

for size in 16 32 48 128; do
  convert "$master" -filter Lanczos -resize "${size}x${size}" \
    -strip "PNG32:$out/icon${size}.png"
  echo "wrote $out/icon${size}.png"
done
