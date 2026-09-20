"""Capture real footage of architecture-diagram/index.html for scene 5.

The last cut redrew a lookalike of the diagram in React, which is the same as
not showing it. This drives the real page and records it.

Playwright's own video recorder is used rather than a screenshot loop: a
screenshot loop advances the page's requestAnimationFrame clock by however long
each capture took, so the packets ride 3x to 4x too fast and the timing drifts.
The recorder captures in real time.

The page already exposes window.__setView for the verification harness, and the
flip and theme controls are real buttons, so the whole sequence is scripted
through the page's own API rather than by clicking at guessed coordinates.

Output: video/public/arch.mp4, 1920x1080, ~22 s, h264, no audio.
"""
import pathlib
import subprocess
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
VIDEO = HERE.parent
DIAGRAM = VIDEO.parent / "architecture-diagram" / "index.html"
OUT = VIDEO / "public" / "arch.mp4"
SCRATCH = VIDEO / ".capture"

# Real milliseconds. The film plays this back at 1:1, so these are the seconds
# the viewer sees. Scene 5 is 24 s and holds the last frame.
BEATS = [
    ("boot", 1600),          # containers draw, nodes land, wires grow
    ("watch_pipeline", 4400),  # packets ride the flow
    ("open_nb", 3000),       # the DuckDB notebook's card, over the board
    ("close", 800),
    ("to_transform", 5000),  # the board rebuilds into the seven rules
    ("open_rules", 2500),
    ("close2", 700),
    ("flip", 3500),          # the card turns over to the written face
    ("hold", 1500),
]

TRIM_START = 1.15  # seconds of blank page before the first paint


def chromium():
    """Find the newest installed Playwright chromium, as verify.py does."""
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


def main():
    if not DIAGRAM.exists():
        sys.exit("diagram not found: %s" % DIAGRAM)
    SCRATCH.mkdir(exist_ok=True)
    for old in SCRATCH.glob("*.webm"):
        old.unlink()

    size = {"width": 1920, "height": 1080}
    errors = []
    exe = chromium()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        # NOTE: no reduced_motion here. verify.py sets it to freeze layout for
        # measurement; this script wants the motion.
        ctx = browser.new_context(viewport=size,
                                  record_video_dir=str(SCRATCH),
                                  record_video_size=size)
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)[:200]))
        page.goto(DIAGRAM.as_uri())

        page.wait_for_timeout(BEATS[0][1])
        page.wait_for_timeout(BEATS[1][1])

        page.click('#layer button.node[data-k="nb"]')
        page.wait_for_timeout(BEATS[2][1])

        page.keyboard.press("Escape")
        page.wait_for_timeout(BEATS[3][1])

        page.evaluate("() => window.__setView('transform')")
        page.wait_for_timeout(BEATS[4][1])

        page.click('#layer button.node[data-k="trules"]')
        page.wait_for_timeout(BEATS[5][1])

        page.keyboard.press("Escape")
        page.wait_for_timeout(BEATS[6][1])

        page.click("#bFlip")
        page.wait_for_timeout(BEATS[7][1])
        flipped = page.evaluate("() => document.getElementById('flipper')"
                                ".classList.contains('flipped')")
        if not flipped:
            errors.append("the card never flipped, so the last beat is dead air")

        page.wait_for_timeout(BEATS[8][1])

        video = page.video
        ctx.close()          # the file is only finalised on context close
        raw = pathlib.Path(video.path())
        browser.close()

    if errors:
        for e in dict.fromkeys(errors):
            print("page error: %s" % e)

    if not raw.exists():
        sys.exit("playwright wrote no video")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    # -r 30 resamples the browser's variable frame timing onto the film's grid,
    # so Remotion's frame N always maps to the same picture.
    cmd = ["ffmpeg", "-y", "-ss", str(TRIM_START), "-i", str(raw),
           "-r", "30", "-c:v", "libx264", "-preset", "slow", "-crf", "20",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(OUT)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3000:])
        sys.exit("ffmpeg failed")

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,nb_frames,r_frame_rate",
         "-show_entries", "format=duration", "-of", "default=nw=1", str(OUT)],
        capture_output=True, text=True)
    print(probe.stdout.strip())
    print("wrote %s (%.1f MB)" % (OUT, OUT.stat().st_size / 1e6))
    for old in SCRATCH.glob("*.webm"):
        old.unlink()
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
