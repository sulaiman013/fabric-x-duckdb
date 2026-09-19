"""Inline the icons into a sprite and write index.html.

The icons are real vendor SVGs, not hand-drawn approximations:
  - Fabric item icons (Lakehouse, Notebook, MirroredDatabase, SemanticModel,
    Report) and the Fabric mark come from
    Microsoft's own @fabric-msft/svg-icons package, full colour with their
    original gradients.
  - Power BI comes from microsoft/PowerBI-Icons.
  - PostgreSQL, DuckDB and Apache Spark come from simple-icons (monochrome),
    tinted at the point of use.

They go into a hidden <symbol> sprite and are referenced with <use>. That
matters: inlining each SVG into a JS string literal puts newlines and quotes
inside the string and kills the whole script. A sprite keeps the markup in the
DOM and out of JS entirely.

Everything is inlined rather than linked, so index.html is one self-contained
file that works from disk, from a CDN, or behind a strict CSP.

Run: python build.py   (or just python assemble.py, which calls this)
"""
import re
import pathlib

HERE = pathlib.Path(__file__).parent
ICONS = HERE / "icons"

# key -> (file, tint for single-colour simple-icons; None keeps the vendor colours)
SET = {
    "postgres":  ("postgresql.svg",                       "currentColor"),
    "duckdb":    ("duckdb.svg",                           "currentColor"),
    "spark":     ("apachespark.svg",                      "currentColor"),
    "lakehouse": ("lakehouse_32_item.svg",                None),
    "notebook":  ("notebook_32_item.svg",                 None),
    "mirror":    ("mirrored_generic_database_32_item.svg", None),
    "semantic":  ("semantic_model_32_item.svg",           None),
    "report":    ("report_32_item.svg",                   None),
    "powerbi":   ("pbi_Power-BI.svg",                     None),
    "fabric":    ("fabric_48_color.svg",                  None),
}


def symbol(key, fname, tint):
    raw = (ICONS / fname).read_text(encoding="utf-8")
    raw = re.sub(r"<\?xml[^>]*\?>", "", raw)
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
    raw = re.sub(r"<title>.*?</title>", "", raw, flags=re.S)

    # A <symbol> scales by its viewBox, and several of the Fabric icons ship
    # with width/height and no viewBox at all. Synthesise one from the declared
    # size rather than dropping the icon: without it the symbol renders at a
    # fixed pixel size and ignores the .ico rule entirely.
    m = re.search(r'viewBox="([^"]+)"', raw)
    if m:
        vb = m.group(1)
    else:
        w = re.search(r'\bwidth="([\d.]+)"', raw)
        h = re.search(r'\bheight="([\d.]+)"', raw)
        if not (w and h):
            raise SystemExit("%s has neither a viewBox nor a width/height" % fname)
        vb = "0 0 %s %s" % (w.group(1), h.group(1))

    inner = re.sub(r"^.*?<svg[^>]*>", "", raw, flags=re.S)
    inner = re.sub(r"</svg>\s*$", "", inner.strip(), flags=re.S)

    # Gradient and clip-path ids are file-unique already, but namespace them
    # anyway so two icons can never collide once they share one document.
    for gid in set(re.findall(r'id="([^"]+)"', inner)):
        new = "%s_%s" % (key, gid)
        inner = inner.replace('id="%s"' % gid, 'id="%s"' % new)
        inner = inner.replace("url(#%s)" % gid, "url(#%s)" % new)
        inner = inner.replace('="#%s"' % gid, '="#%s"' % new)

    fill = ' fill="%s"' % tint if tint else ""
    return '<symbol id="ic-%s" viewBox="%s"%s>%s</symbol>' % (key, vb, fill, inner.strip())


def main():
    missing = [f for f, _ in SET.values() if not (ICONS / f).exists()]
    if missing:
        raise SystemExit("missing icons: %s" % missing)

    sprite_parts = [symbol(k, f, c) for k, (f, c) in SET.items()]
    sprite = ('<svg xmlns="http://www.w3.org/2000/svg" style="position:absolute;width:0;'
              'height:0;overflow:hidden" aria-hidden="true">' + "".join(sprite_parts) + "</svg>")

    tpl = HERE / "template.html"
    if not tpl.exists():
        raise SystemExit("template.html is missing; run python assemble.py")
    out = tpl.read_text(encoding="utf-8").replace("{{SPRITE}}", sprite)
    left = re.findall(r"\{\{[A-Z_]+\}\}", out)
    if left:
        raise SystemExit("unresolved placeholders: %s" % sorted(set(left)))
    (HERE / "index.html").write_text(out, encoding="utf-8")

    print("wrote index.html     %s bytes" % format((HERE / "index.html").stat().st_size, ","))
    print("sprite: %d symbols, %s bytes" % (len(sprite_parts), format(len(sprite), ",")))
    for k, (f, c) in SET.items():
        print("   %-10s %-38s %s" % (k, f, c or "full colour"))


if __name__ == "__main__":
    main()
