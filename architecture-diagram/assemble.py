"""Compose template.html from parts/, then hand it to build.py.

Editing a part and re-running `python assemble.py` is the whole loop; it calls
build.py at the end so index.html is never stale relative to the template.

Order matters: VIEWS must exist before the view files register themselves on it,
and the renderer, wires and boot code must come after the data.

The theme is the one from sulaimanahmed.dev, carried over verbatim from the
reference architecture deck so the two documents look like one hand. The guards
below exist because a theme token that drifts, or a stray identifier from
another project, is exactly the kind of thing nobody notices until it ships.
"""
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
P = HERE / "parts"

STYLE = (P / "style.css.html").read_text(encoding="utf-8")
STYLE_ADD = (P / "style-add.css").read_text(encoding="utf-8")
FRONT = (P / "shell-front.html").read_text(encoding="utf-8")
BACK = (P / "back-face.html").read_text(encoding="utf-8")

JS_PARTS = ["glyphs.js", "view-pipeline.js", "view-transform.js",
            "renderer.js", "wires.js", "boot.js"]

# The theme tokens must survive assembly untouched.
for token in ("--paper:#F2FAEB", "--green:#35AE00", "--amber:#C77A00",
              "--W:1800px", "--H:1000px", "--serif:", "--mono:"):
    if token not in STYLE:
        raise SystemExit("theme token missing from the stylesheet: %s" % token)

# Nothing from any client engagement may appear in a page that describes a
# public, synthetic-data project. Checked against the assembled output, not just
# the stylesheet, because the page head lives in this file.
FORBIDDEN_NAMES = ("HOPS", "hops", "Opsimize", "opsimize", "Mendix", "mendix",
                   "hopshq", "PizzaLuxe", "Thick PROD", "analytics_wh")
# The account identifier is redacted everywhere else in this repository; it has
# no business being in a diagram either.
FORBIDDEN_RE = (r"@[a-z0-9-]{3,}\.onmicrosoft\.com",)

style = STYLE.replace("</style>", STYLE_ADD + "\n</style>")

head = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>50M rows on Fabric &middot; Architecture</title>
<meta name="description" content="How 50 million rows move from on-premises PostgreSQL to a Power BI report on Microsoft Fabric: open mirroring with CDC, a DuckDB transformation on a Python notebook, V-Ordered Delta, and Direct Lake.">
%s
</head>
<body>
{{SPRITE}}
<div class="viewport"><div id="pan"></div><div class="stage" id="stage"><div class="flipper" id="flipper"><div class="face front" id="faceFront">
""" % style

js = "\n".join((P / f).read_text(encoding="utf-8") for f in JS_PARTS)

script = """
<script>
(function(){
"use strict";
var W=1800,H=1000;                       // must match --W/--H in the CSS and the #wires viewBox
var VIEWS={};
var ico=function(k){return '<svg class="ico" aria-hidden="true"><use href="#ic-'+k+'"></use></svg>';};
var fmt=function(n){return typeof n==="number"?n.toLocaleString("en-GB"):n;};

%s
})();
</script>
</body>
</html>
""" % js

out = head + FRONT + "  </div>\n" + BACK + "\n</div></div></div>\n" + script
(HERE / "template.html").write_text(out, encoding="utf-8")
print("template.html %s bytes, %d lines" % (format(len(out), ","), out.count("\n")))

# Every key used across nodes, chips, tiles, flow steps and KPIs shares one flat
# DATA map per view, so a duplicate silently overwrites a card. Catch it here.
keys = re.findall(r"^\s{2,3}([a-z_][a-z0-9_]*)\s*:\s*\{", js, re.M)
dupes = {k for k in keys if keys.count(k) > 1}
noise = {"kv", "pts", "flow", "nodes", "chips", "plats", "tiles", "edges", "kpis", "brackets"}
dupes -= noise
if dupes:
    print("WARNING: repeated object keys across views (fine only if in different views): %s"
          % sorted(dupes))

leaks = [t for t in FORBIDDEN_NAMES if t in out]
for pat in FORBIDDEN_RE:
    leaks += re.findall(pat, out)
if leaks:
    raise SystemExit("assembled output failed its guards: %s" % leaks)
print("guards: theme tokens intact, no foreign identifiers")

r = subprocess.run([sys.executable, str(HERE / "build.py")], cwd=HERE)
sys.exit(r.returncode)
