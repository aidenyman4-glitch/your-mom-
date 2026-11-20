#!/usr/bin/env python3
"""Build the Pixel Rearranger site.

Inlines src/target.jpg into src/page.html and writes ../docs/index.html, which
GitHub Pages serves (Settings -> Pages -> Deploy from a branch -> /docs).
The file is self-contained, so it also works opened straight from disk.

Usage: python3 build.py [--fragment OUT]   (--fragment writes the page without the
<!doctype>/<head> wrapper, for hosts that add their own.)
"""
import base64, pathlib, sys

here = pathlib.Path(__file__).resolve().parent
SITE = "https://aidenyman4-glitch.github.io/your-mom-/"
DESC = ("Drop in any picture and watch every one of its pixels fly into place "
        "to rebuild a target image. Nothing recolored, nothing added.")
ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E"
        "%3Crect width='16' height='16' rx='3' fill='%230c0b17'/%3E"
        "%3Crect x='3' y='3' width='4' height='4' fill='%237fd8ff'/%3E"
        "%3Crect x='9' y='3' width='4' height='4' fill='%23ff8fd6'/%3E"
        "%3Crect x='3' y='9' width='4' height='4' fill='%23ff8fd6'/%3E"
        "%3Crect x='9' y='9' width='4' height='4' fill='%23eeebff'/%3E%3C/svg%3E")

page = (here / "src" / "page.html").read_text()
b64 = base64.b64encode((here / "src" / "target.jpg").read_bytes()).decode()
body = page.replace("__TARGET_B64__", b64)

if len(sys.argv) == 3 and sys.argv[1] == "--fragment":
    pathlib.Path(sys.argv[2]).write_text(body)
    sys.exit()

head = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="{DESC}">
<meta name="theme-color" content="#0c0b17">
<link rel="icon" href="{ICON}">
<meta property="og:type" content="website">
<meta property="og:title" content="Pixel Rearranger">
<meta property="og:description" content="{DESC}">
<meta property="og:url" content="{SITE}">
<meta property="og:image" content="{SITE}og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<style>body{{margin:0}}[hidden]{{display:none!important}}:root{{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}</style>
</head>
<body>
"""
out = here.parent / "docs" / "index.html"
out.write_text(head + body + "\n</body>\n</html>\n")
(here.parent / "docs" / ".nojekyll").write_text("")
print("wrote", out)
