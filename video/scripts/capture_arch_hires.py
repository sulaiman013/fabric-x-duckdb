"""Capture the architecture diagram at 2x, for the theatre scene.

The existing arch.mp4 is 1920 wide, which is fine to prove the page is alive
but goes soft the moment a camera pushes into one component. These stills are
3840 x 2160, so a 2.5x push still resolves the node labels.

One still per view, plus the written back face.
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
VIDEO = HERE.parent
DIAGRAM = VIDEO.parent / "architecture-diagram" / "index.html"
OUT = VIDEO / "public" / "arch"


def chromium():
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


def main() -> None:
    if not DIAGRAM.exists():
        sys.exit("diagram not found: %s" % DIAGRAM)
    OUT.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        exe = chromium()
        browser = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=2,
            reduced_motion="reduce",
        )
        page.goto(DIAGRAM.as_uri())
        page.wait_for_timeout(1800)

        for view in ("pipeline", "transform"):
            page.evaluate("v => window.__setView(v)", view)
            page.wait_for_timeout(1300)
            p = OUT / ("%s.png" % view)
            page.screenshot(path=str(p))
            print("wrote %s" % p.name)

        page.evaluate("() => window.__setView('pipeline')")
        page.wait_for_timeout(700)
        page.click("#bFlip")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT / "explained.png"))
        print("wrote explained.png")

        browser.close()

    for p in sorted(OUT.glob("*.png")):
        print("  %-16s %.1f MB" % (p.name, p.stat().st_size / 1e6))


if __name__ == "__main__":
    main()
