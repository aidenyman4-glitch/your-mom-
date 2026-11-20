#!/usr/bin/env python3
"""Build pixel-rearranger/index.html: inlines src/target.jpg into src/page.html.

Usage: python3 build.py [--fragment OUT]   (--fragment writes the page without the
<!doctype>/<head> wrapper, for hosts that add their own.)
"""
import base64, pathlib, sys

here = pathlib.Path(__file__).resolve().parent
page = (here / "src" / "page.html").read_text()
b64 = base64.b64encode((here / "src" / "target.jpg").read_bytes()).decode()
body = page.replace("__TARGET_B64__", b64)

if len(sys.argv) == 3 and sys.argv[1] == "--fragment":
    pathlib.Path(sys.argv[2]).write_text(body)
else:
    head = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
            '<style>body{margin:0}[hidden]{display:none!important}</style>\n</head>\n<body>\n')
    (here / "index.html").write_text(head + body + "\n</body>\n</html>\n")
