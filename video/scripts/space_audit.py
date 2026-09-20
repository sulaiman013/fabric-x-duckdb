"""Measure how much of each frame is actually used.

The v4 film reads as half empty. That is not a taste question, it is a
measurable one: sample frames, find which horizontal bands carry ink, and
report the largest empty band and the overall coverage.

A frame is "used" when content spans most of the height with no single dead
band big enough to read as a hole. The thresholds below are the gate:

  coverage   share of frame rows that carry content        want >= 0.72
  dead band  largest run of empty rows, as a share         want <= 0.22

Run against a rendered mp4:
    python scripts/space_audit.py out/fabric-x-duckdb-v4.mp4
"""
import pathlib
import subprocess
import sys
import tempfile

from PIL import Image

SCENES = [
    ("1 hook", 0, 150),
    ("2 table", 130, 550),
    ("3 mirror", 530, 1070),
    ("4 gap", 1050, 1650),
    ("5 cluster", 1630, 2050),
    ("6 transform", 2030, 2570),
    ("7 arch", 2550, 2970),
    ("8 serve", 2950, 3370),
    ("9 report", 3350, 3890),
    ("10 threshold", 3870, 4320),
    ("11 close", 4300, 4690),
]

FPS = 30
WANT_COVERAGE = 0.72
WANT_DEAD = 0.22
# how far a pixel must sit from the paper tone to count as content
INK = 14


def frame_at(mp4: str, frame: int, out: pathlib.Path) -> pathlib.Path:
    t = frame / FPS
    p = out / ("f%d.png" % frame)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % t, "-i", mp4,
         "-frames:v", "1", "-vf", "scale=480:-1", str(p)],
        check=True,
    )
    return p


def analyse(path: pathlib.Path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    # the paper tone is whatever dominates the top-left corner region
    bg = px[4, 4]

    # Measure in BANDS, not single rows. A 5px gap between grid cells is not
    # perceived as empty space, but a row-by-row scan counts it as empty and
    # caps a perfectly dense grid at about 84%. Bands of roughly 3% of the
    # height are what the eye actually reads as "this part of the frame is
    # used" or "this part is blank".
    band_h = max(4, int(h * 0.03))
    rows = []
    for y0 in range(0, h, band_h):
        hit = 0
        for y in range(y0, min(h, y0 + band_h), 2):
            for x in range(0, w, 3):
                r, g, b = px[x, y]
                if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > INK:
                    hit += 1
        rows += [hit > 6] * min(band_h, h - y0)

    coverage = sum(rows) / h

    # longest run of empty rows, ignoring the outer margins
    m = int(h * 0.04)
    best = cur = 0
    for y in range(m, h - m):
        cur = 0 if rows[y] else cur + 1
        best = max(best, cur)
    dead = best / h

    # where the ink actually sits
    first = next((y for y in range(h) if rows[y]), 0)
    last = next((y for y in range(h - 1, -1, -1) if rows[y]), h - 1)
    return coverage, dead, first / h, last / h


def main() -> None:
    mp4 = sys.argv[1] if len(sys.argv) > 1 else "out/fabric-x-duckdb-v4.mp4"
    if not pathlib.Path(mp4).exists():
        sys.exit("no such file: %s" % mp4)

    tmp = pathlib.Path(tempfile.mkdtemp())
    print("%-11s %6s  %8s  %9s  %s" % ("scene", "at", "coverage", "dead band", "ink spans"))
    print("-" * 66)

    bad = []
    for name, a, b in SCENES:
        worst = None
        for q in (0.45, 0.65, 0.85):
            f = int(a + (b - a) * q)
            cov, dead, top, bot = analyse(frame_at(mp4, f, tmp))
            if worst is None or cov < worst[1]:
                worst = (f, cov, dead, top, bot)
        f, cov, dead, top, bot = worst
        flag = ""
        if cov < WANT_COVERAGE:
            flag += " LOW COVERAGE"
        if dead > WANT_DEAD:
            flag += " DEAD BAND"
        if flag:
            bad.append((name, cov, dead))
        print("%-11s %6d  %7.0f%%  %8.0f%%  %3.0f%% to %3.0f%%%s"
              % (name, f, cov * 100, dead * 100, top * 100, bot * 100, flag))

    print()
    if bad:
        print("FAILED: %d scene(s) waste the frame" % len(bad))
        for n, cov, dead in bad:
            print("  %-11s coverage %.0f%% (want %.0f%%), dead band %.0f%% (want under %.0f%%)"
                  % (n, cov * 100, WANT_COVERAGE * 100, dead * 100, WANT_DEAD * 100))
        sys.exit(1)
    print("PASSED: every scene fills the frame")


if __name__ == "__main__":
    main()
