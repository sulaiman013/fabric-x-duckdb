"""Verification gate for the architecture diagram. Run after every layout edit.

Eye review is not enough: reading the screenshots by hand misses collisions that
a box check catches immediately. This asserts, per view:

  (a) no two interactive elements overlap, and nothing escapes its container
      or the stage,
  (b) the expected number of wires is actually drawn, because a box check
      cannot see a wire that is missing,
  (c) packets move (sampled twice under reduced_motion="reduce", which the page
      deliberately ignores),
  (d) night mode and the card flip both apply,
  (e) desktop and phone screenshots land for the record.

Run: python verify.py            (all views)
     python verify.py transform  (one view)
"""
import pathlib
import sys
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
PAGE = (HERE / "index.html").as_uri()
VIEWS = ["pipeline", "transform"]

# Expected drawn wires per view. A silently missing edge is invisible to a box
# check, so it is asserted directly. Each edge draws a base path plus a marching
# overlay, so the count is roughly twice the number of declared edges.
EXPECTED_PATHS = {"pipeline": 16, "transform": 14}

BOXES_JS = """
() => {
  const sel = '.node, .src, .chip, .flow .fn, .kpis .kbtn, .plat .foot, .bracket .t';
  const out = [];
  for (const el of document.querySelectorAll(sel)) {
    if (el.closest('[hidden]')) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    out.push({
      k: el.dataset.k || el.className,
      cls: el.className,
      l: r.left, t: r.top, r: r.right, b: r.bottom,
      host: (el.closest('.plat') || {}).id || null,
    });
  }
  const plats = [];
  for (const el of document.querySelectorAll('.plat')) {
    const r = el.getBoundingClientRect();
    plats.push({ id: el.id, l: r.left, t: r.top, r: r.right, b: r.bottom });
  }
  const stage = document.getElementById('stage').getBoundingClientRect();
  const chrome = [];
  for (const s of ['#kpis', '.footer', '.head', '.brandbar', '.ctl', '.bctl']) {
    const el = document.querySelector(s);
    if (!el) continue;
    const r = el.getBoundingClientRect();
    chrome.push({ k: s, l: r.left, t: r.top, r: r.right, b: r.bottom });
  }
  return { out, plats, chrome,
           stage: { l: stage.left, t: stage.top, r: stage.right, b: stage.bottom } };
}
"""


def chromium():
    """Find the newest installed Playwright chromium.

    The reference deck hard-coded an absolute path for one machine's user
    account, which meant the gate could not run anywhere else. Discover it.
    """
    root = pathlib.Path.home() / "AppData" / "Local" / "ms-playwright"
    if not root.exists():
        root = pathlib.Path.home() / ".cache" / "ms-playwright"
    builds = sorted(root.glob("chromium-*"), key=lambda p: int(p.name.split("-")[-1]))
    for b in reversed(builds):
        for rel in ("chrome-win64/chrome.exe", "chrome-win/chrome.exe",
                    "chrome-linux/chrome", "chrome-mac/Chromium.app/Contents/MacOS/Chromium"):
            exe = b / rel
            if exe.exists():
                return str(exe)
    return None


def overlap(a, b, tol=0.5):
    w = min(a["r"], b["r"]) - max(a["l"], b["l"])
    h = min(a["b"], b["b"]) - max(a["t"], b["t"])
    return w > tol and h > tol


def check_view(page, view):
    problems = []
    page.evaluate("v => window.__setView && window.__setView(v)", view)
    page.wait_for_timeout(900)

    data = page.evaluate(BOXES_JS)
    boxes, plats, stage = data["out"], data["plats"], data["stage"]

    for plat in plats:
        for ch in data["chrome"]:
            if overlap(plat, ch, tol=2):
                problems.append("container %s overlaps %s" % (plat["id"], ch["k"]))

    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            if overlap(a, b):
                problems.append("overlap: %s <-> %s" % (a["k"], b["k"]))

    for a in boxes:
        if (a["l"] < stage["l"] - 1 or a["r"] > stage["r"] + 1
                or a["t"] < stage["t"] - 1 or a["b"] > stage["b"] + 1):
            problems.append("outside stage: %s" % a["k"])
        if a["host"]:
            host = next((p for p in plats if p["id"] == a["host"]), None)
            if host and (a["l"] < host["l"] - 1 or a["r"] > host["r"] + 1
                         or a["t"] < host["t"] - 1 or a["b"] > host["b"] + 1):
                problems.append("escapes %s: %s" % (a["host"], a["k"]))

    drawn = page.evaluate("() => document.querySelectorAll('#wires path[stroke]').length")
    want = EXPECTED_PATHS.get(view)
    if want is not None and drawn < want:
        problems.append("only %d wires drawn, expected at least %d" % (drawn, want))

    pos = page.evaluate("() => { const c = document.querySelector('#wires circle[fill]');"
                        " return c ? [c.getAttribute('cx'), c.getAttribute('cy')] : null; }")
    page.wait_for_timeout(700)
    pos2 = page.evaluate("() => { const c = document.querySelector('#wires circle[fill]');"
                         " return c ? [c.getAttribute('cx'), c.getAttribute('cy')] : null; }")
    if pos is None:
        problems.append("no packets drawn")
    elif pos == pos2:
        problems.append("packets are static (%s)" % (pos,))

    print("  %-10s %3d elements, %d containers, %2d wires -> %s"
          % (view, len(boxes), len(plats), drawn,
             "OK" if not problems else "%d PROBLEM(S)" % len(problems)))
    for p in problems:
        print("      %s" % p)
    return problems


def main():
    wanted = [v for v in sys.argv[1:] if v in VIEWS] or VIEWS
    exe = chromium()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080},
                                reduced_motion="reduce")
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:200]))
        page.goto(PAGE)
        page.wait_for_timeout(1200)

        problems = []
        print("layout + motion, 1920x1080:")
        for v in wanted:
            problems += check_view(page, v)

        page.evaluate("() => document.getElementById('bTheme').click()")
        page.wait_for_timeout(600)
        if page.evaluate("() => document.documentElement.getAttribute('data-theme')") != "dark":
            problems.append("night mode did not apply")
        print("night mode:")
        for v in wanted:
            problems += check_view(page, v)
        page.screenshot(path=str(HERE / "shot-dark.png"))
        page.evaluate("() => document.getElementById('bTheme').click()")
        page.wait_for_timeout(600)

        for v in wanted:
            page.evaluate("v => window.__setView(v)", v)
            page.wait_for_timeout(900)
            page.screenshot(path=str(HERE / ("shot-%s.png" % v)))

        page.evaluate("() => document.getElementById('bFlip').click()")
        page.wait_for_timeout(1200)
        if not page.evaluate("() => document.getElementById('flipper')"
                             ".classList.contains('flipped')"):
            problems.append("card did not flip")
        page.screenshot(path=str(HERE / "shot-back.png"))
        page.evaluate("() => document.getElementById('bBack').click()")
        page.wait_for_timeout(1000)

        for name, size in (("phone", {"width": 390, "height": 844}),
                           ("phone-land", {"width": 844, "height": 390})):
            page.set_viewport_size(size)
            page.wait_for_timeout(700)
            page.screenshot(path=str(HERE / ("shot-%s.png" % name)))
        browser.close()

    if errors:
        problems += ["script error: %s" % e for e in dict.fromkeys(errors)]

    print()
    if problems:
        print("FAILED: %d problem(s)" % len(problems))
        sys.exit(1)
    print("PASSED: no overlaps, nothing escapes, every wire drawn, packets move, "
          "night mode and flip work.")


if __name__ == "__main__":
    main()
