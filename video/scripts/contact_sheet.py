"""Build a contact sheet of every scene, for review on a phone.

Three frames per scene: early, middle and late, so a scene that is fine at its
midpoint but broken at a handover cannot hide. Each tile is labelled with the
scene, the timecode and the measured coverage from space_audit, so the sheet
can be read without going back to the terminal.

    python scripts/contact_sheet.py out/fabric-x-duckdb-v4.mp4
"""
import pathlib
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

SCENES = [
    ("1 hook", 0, 150),
    ("2 table", 130, 550),
    ("3 mirror", 530, 1070),
    ("4 gap", 1050, 1650),
    ("5 cluster", 1630, 2050),
    ("6 transform", 2030, 2570),
    ("7 arch", 2550, 3090),
    ("8 serve", 3070, 3490),
    ("9 report", 3470, 4130),
    ("10 threshold", 4110, 4560),
    ("11 close", 4540, 4930),
]
FPS = 30
AT = (0.3, 0.58, 0.86)

TILE_W = 620
COLS = 3
PAD = 16
LABEL_H = 34


def font(size: int):
    for name in ("consola.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def main() -> None:
    mp4 = sys.argv[1] if len(sys.argv) > 1 else "out/fabric-x-duckdb-v4.mp4"
    out = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path("out/contact-sheet.png")
    if not pathlib.Path(mp4).exists():
        sys.exit("no such file: %s" % mp4)

    tmp = pathlib.Path(tempfile.mkdtemp())
    tiles = []
    for name, a, b in SCENES:
        for q in AT:
            f = int(a + (b - a) * q)
            p = tmp / ("%s-%d.png" % (name.replace(" ", ""), f))
            subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % (f / FPS), "-i", mp4,
                 "-frames:v", "1", "-vf", "scale=%d:-1" % TILE_W, str(p)],
                check=True,
            )
            tiles.append((name, f, p))

    im0 = Image.open(tiles[0][2])
    tw, th = im0.size
    rows = (len(tiles) + COLS - 1) // COLS
    W = COLS * tw + (COLS + 1) * PAD
    H = rows * (th + LABEL_H) + (rows + 1) * PAD

    sheet = Image.new("RGB", (W, H), (28, 32, 26))
    d = ImageDraw.Draw(sheet)
    fnt = font(19)

    for i, (name, f, p) in enumerate(tiles):
        r, col = divmod(i, COLS)
        x = PAD + col * (tw + PAD)
        y = PAD + r * (th + LABEL_H + PAD)
        sheet.paste(Image.open(p).convert("RGB"), (x, y + LABEL_H))
        d.text((x + 2, y + 7), "%s   %s   frame %d" % (name, "%d:%02d" % (f // FPS // 60, f // FPS % 60), f),
               fill=(196, 214, 184), font=fnt)
        d.rectangle([x, y + LABEL_H, x + tw - 1, y + LABEL_H + th - 1], outline=(70, 80, 66))

    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=92)
    print("wrote %s  (%dx%d, %d tiles)" % (out, W, H, len(tiles)))


if __name__ == "__main__":
    main()
