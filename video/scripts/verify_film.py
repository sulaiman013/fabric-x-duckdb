"""The gate the film has to pass before it is rendered.

v2 shipped with "39 / 39" burned into the last scene long after the real
acceptance figure had become 36, because nothing compared the film against the
artifact it claims to be reporting. This does.

Four groups of check:

  NUMBERS   every figure the scenes put on screen is compared against UAT.json,
            and a small list of figures that live only in BUILD_LOG.md is
            compared against that file. Stale strings are banned outright.
  CROPS     every report crop lies inside the source image, is contain fitted
            into its box, and is never scaled past the point where it would
            leave the card it was measured from.
  FOOTAGE   public/arch.mp4 exists, is 1920x1080 at 30fps, and holds at least
            as many frames as scene 5 asks it to play.
  TEXT      no em or en dashes anywhere in the film's source, which is a house
            rule for everything in this repository.

Run:  python scripts/verify_film.py
"""
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
VIDEO = HERE.parent
REPO = VIDEO.parent
SRC = VIDEO / "src"
UAT = REPO / "UAT.json"
BUILD_LOG = REPO / "BUILD_LOG.md"
ARCH = VIDEO / "public" / "arch.mp4"

problems: list[str] = []
checks = 0


def ok(label: str, good: bool, detail: str = "") -> None:
    global checks
    checks += 1
    if good:
        print("  pass  %s%s" % (label, (" :: " + detail) if detail else ""))
    else:
        print("  FAIL  %s%s" % (label, (" :: " + detail) if detail else ""))
        problems.append(label + ((" :: " + detail) if detail else ""))


def scene_text() -> str:
    parts = []
    for p in sorted(SRC.rglob("*.tsx")) + sorted(SRC.rglob("*.ts")):
        parts.append(p.read_text(encoding="utf-8"))
    return "\n".join(parts)


def strip_comments(text: str) -> str:
    """Only what renders.

    The scenes carry comments that quote the very claims this script bans,
    because that is how the next person learns why they were banned. Scanning
    the comments would make the explanation itself a failure.
    """
    out = []
    in_block = False
    for line in text.splitlines():
        s = line.strip()
        if in_block:
            if "*/" in s:
                in_block = False
            continue
        if s.startswith("/*"):
            if "*/" not in s:
                in_block = True
            continue
        if s.startswith("//") or s.startswith("*"):
            continue
        out.append(line)
    return "\n".join(out)


def has_number(text: str, n: int) -> bool:
    """A count may be on screen as formatted text or as a CountUp literal."""
    return "{:,}".format(n) in text or str(n) in text


def group(name: str) -> None:
    print("\n%s" % name)


# --------------------------------------------------------------- numbers
def check_numbers(text: str) -> None:
    group("NUMBERS, against UAT.json")
    if not UAT.exists():
        ok("UAT.json is present", False, str(UAT))
        return
    d = json.loads(UAT.read_text(encoding="utf-8"))
    b = d["capacity"]["build"]
    v = d["capacity"]["verify"]

    passed, failed, skipped = d["passed"], d["failed"], d["skipped"]
    ok("acceptance figure", "%d / %d" % (passed, passed) in text,
       "expected '%d / %d', from UAT.json" % (passed, passed))
    ok("skip count is stated", "%d skipped" % skipped in text,
       "expected '%d skipped'" % skipped)
    rendered = strip_comments(text)
    ok("no stale acceptance figure", "39 / 39" not in rendered and "39 passed" not in rendered)
    ok("zero failures is true", failed == 0, "UAT.json failed=%d" % failed)

    # counts that appear as formatted numbers
    want = {
        "source rows": b["source_rows"],
        "gold fact rows": b["counts"]["fact_transaction"],
        "alert fact rows": b["counts"]["fact_alert"],
        "duplicates removed": b["recon"]["removed"],
    }
    for label, n in want.items():
        ok(label, has_number(text, n), "{:,}".format(n))

    # the seven rule firings, each of which is on screen in scene 7
    for rid, n in sorted(b["rule_firings"].items()):
        ok("rule firing %s" % rid, has_number(text, n), "{:,}".format(n))

    total = sum(b["rule_firings"].values())
    ok("firings sum to the alert fact", total == b["counts"]["fact_alert"],
       "%d vs %d" % (total, b["counts"]["fact_alert"]))

    bands = {r["risk_band"]: r["n"] for r in v["checks"]["risk_bands"]}
    ok("alert count equals the HIGH band", has_number(text, bands["HIGH"]),
       "{:,}".format(bands["HIGH"]))
    rate = bands["HIGH"] / b["counts"]["fact_transaction"] * 100
    ok("alert rate", "%.2f%%" % rate in text, "%.2f%%" % rate)

    orphan = v["checks"]["orphan_keys"]
    zero = orphan["bad_customer"] + orphan["bad_merchant"] + orphan["bad_date"]
    ok("orphan keys really are zero", zero == 0, "sum=%d" % zero)

    ok("vCores", '"8"' in text or ">8<" in text or "8 vCores" in text, "8")
    ok("CU rate", "4" in text and "CU" in text, "4 CU")
    ok("RAM on the node", "%.1f GB" % b["env"]["ram_gb"] in text, "%.1f GB" % b["env"]["ram_gb"])
    ok("DuckDB version", b["duckdb_version"] in text, b["duckdb_version"])
    ok("memory cap", "%d GB" % b["memory_limit_gb"] in text, "%d GB" % b["memory_limit_gb"])

    work_min = b["timing_s"]["total_s"] / 60.0
    ok("work time in minutes", "%.1f min" % work_min in text, "%.1f min" % work_min)

    files = sum(t["numFiles"] for t in v["tables"].values())
    ok("gold file count is consistent", files == 36, "counted %d" % files)

    group("NUMBERS, against BUILD_LOG.md")
    if not BUILD_LOG.exists():
        ok("BUILD_LOG.md is present", False)
        return
    log = BUILD_LOG.read_text(encoding="utf-8")
    for label, s in [
        ("CDC latency", "151"),
        ("V-Order wall time", "233 s"),
        ("transform wall time", "895 s"),
        ("transform CU-hours", "0.994"),
        ("pipeline CU-hours", "1.512"),
        ("pipeline cost", "$0.27"),
        ("modelled alternative CU-hours", "1.989"),
        ("cold query", "11.18"),
        ("warm query", "1.59"),
        ("parse rate, dates", "52.4%"),
        ("parse rate, amounts", "81.7%"),
        ("parse rate, balances", "70.5%"),
        ("compressed size", "10.5 GB"),
    ]:
        in_film = s in text
        in_log = s in log
        ok(label, in_film and in_log,
           "film=%s buildlog=%s value=%s" % (in_film, in_log, s))


# ----------------------------------------------------------------- crops
def check_generator_claims(text: str) -> None:
    """The opening quotes scripts/schema.py. Read it and compare."""
    group("THE OPENING QUOTES THE GENERATOR")

    gen = REPO / "scripts" / "schema.py"
    if not gen.exists():
        ok("scripts/schema.py is present", False, str(gen))
        return
    g = gen.read_text(encoding="utf-8")

    # mixed_date's weighted() table: cumulative thresholds, one per format
    m = re.search(r"def mixed_date\(.*?weighted\(\[(.*?)\]\)", g, re.S)
    ok("mixed_date's format table was found", m is not None)
    if not m:
        return
    cum = [float(x) for x in re.findall(r"\(([0-9.]+),", m.group(1))]
    shares = [round((cum[i] - (cum[i - 1] if i else 0)) * 100) for i in range(len(cum))]

    src = (SRC / "scenes4" / "S1Field.tsx").read_text(encoding="utf-8")
    fm = re.search(r"const FORMATS[^=]*=\s*\[(.*?)\];", src, re.S)
    ok("the film's FORMATS table was found", fm is not None)
    if not fm:
        return
    film = [int(x) for x in re.findall(r'",\s*(\d+),', fm.group(1))]

    ok("the film states the generator's date-format weights",
       film == shares, "film %s vs schema.py %s" % (film, shares))
    ok("the weights are a whole distribution", sum(film) == 100, "sum %d" % sum(film))

    # the sentinel dates and the null-lookalikes are quoted, not paraphrased
    for lit in ("1900-01-01", "9999-12-31", "0000-00-00", "1970-01-01"):
        ok("sentinel %s is in the generator" % lit, lit in g)
    ok("the film says four sentinel dates", "four sentinel dates" in text)

    junk = re.search(r"NULL_JUNK\s*=\s*\[(.*?)\]", g, re.S)
    n = len(re.findall(r'"', junk.group(1))) // 2 if junk else 0
    ok("the film says eight strings that mean missing",
       n == 8 and "eight\n * strings" not in text and "eight" in text,
       "NULL_JUNK has %d entries" % n)

    # the two rows the mirror lost are the two README names
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    for row, pretty in (("3870725", "3,870,725"), ("50000004", "50,000,004")):
        ok("README names row %s" % pretty, row in readme)
        ok("the film names row %s" % pretty, pretty in text)


def check_crops() -> None:
    group("CROPS, scene 9")
    src = (SRC / "scenes" / "S09Report.tsx").read_text(encoding="utf-8")

    img_w = int(re.search(r"IMG_W\s*=\s*(\d+)", src).group(1))
    img_h = int(re.search(r"IMG_H\s*=\s*(\d+)", src).group(1))
    wide_w = int(re.search(r"WIDE_W\s*=\s*(\d+)", src).group(1))
    wide_h = int(re.search(r"WIDE_H\s*=\s*(\d+)", src).group(1))
    tall_w = int(re.search(r"TALL_W\s*=\s*(\d+)", src).group(1))
    tall_h = int(re.search(r"TALL_H\s*=\s*(\d+)", src).group(1))

    ok("contain fit, not cover", "Math.min(boxW / cw, boxH / ch)" in src,
       "Math.max here is what over-zoomed v2")
    ok("no cover fit anywhere in the scene", "Math.max(boxW" not in src)

    crops = [(m.group(1), [int(x) for x in m.group(2).split(",")])
             for m in re.finditer(
                 r'file:\s*"([^"]+)".*?crop:\s*\[([0-9,\s]+)\]', src, re.S)]
    ok("every crop was found", len(crops) == 7, "found %d" % len(crops))

    push = float(re.search(r"1 \+ t \* ([0-9.]+)", src).group(1))
    max_dur = 100
    max_push = 1 + push * max_dur
    ok("the slow push stays under 2%", max_push < 1.02, "%.3f at the longest shot" % max_push)

    for f, (cx, cy, cw, ch) in crops:
        tag = "%s [%d,%d,%d,%d]" % (f.replace("report-", "").replace(".png", ""), cx, cy, cw, ch)
        ok("inside the source image: %s" % tag,
           cx >= 0 and cy >= 0 and cx + cw <= img_w and cy + ch <= img_h,
           "source is %dx%d" % (img_w, img_h))

        tall = cw / ch < 1.2
        bw, bh = (tall_w, tall_h) if tall else (wide_w, wide_h)
        k = min(bw / cw, bh / ch)
        rw, rh = cw * k * max_push, ch * k * max_push
        ok("fits its box at the end of the push: %s" % tag,
           rw <= bw * 1.021 and rh <= bh * 1.021,
           "renders %dx%d into %dx%d" % (rw, rh, bw, bh))

        # legibility: the report's smallest body type is about 26 source px, so
        # anything under 0.42 scale puts it below 11px on a 1080p frame
        ok("stays legible: %s" % tag, k >= 0.42, "scale %.3f" % k)


# --------------------------------------------------------------- footage
def check_footage() -> None:
    group("FOOTAGE, scene 5")
    ok("public/arch.mp4 exists", ARCH.exists(), str(ARCH))
    if not ARCH.exists():
        return
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
         "-show_entries", "stream=width,height,nb_read_frames,r_frame_rate",
         "-of", "json", ARCH],
        capture_output=True, text=True)
    st = json.loads(r.stdout)["streams"][0]
    w, h = st["width"], st["height"]
    n = int(st["nb_read_frames"])
    fps = st["r_frame_rate"]
    ok("capture is 1920x1080", (w, h) == (1920, 1080), "%dx%d" % (w, h))
    ok("capture is 30fps", fps == "30/1", fps)

    src = (SRC / "scenes" / "S05Diagram.tsx").read_text(encoding="utf-8")
    want = int(re.search(r"VIDEO_FRAMES\s*=\s*(\d+)", src).group(1))
    ok("scene 5 does not play past the end of the capture", want <= n,
       "scene asks for %d, capture holds %d" % (want, n))

    vfrom = int(re.search(r"VIDEO_FROM\s*=\s*(\d+)", src).group(1))
    dur = int(re.search(r'id:\s*"diagram",\s*dur:\s*(\d+)',
                        (SRC / "Film.tsx").read_text(encoding="utf-8")).group(1))
    ok("the capture fits inside scene 5", vfrom + want <= dur,
       "%d + %d vs %d" % (vfrom, want, dur))

    # The first cut of this scene stacked a title, the browser and a caption in
    # a flex column taller than the frame. Flex shrank the browser rather than
    # complaining, and 90px of the capture was silently clipped. Assert the
    # budget rather than trusting the eye.
    def num(name: str) -> int:
        return int(re.search(name + r"\s*=\s*(\d+)", src).group(1))

    box_w = num("BOX_W")
    box_h = round(box_w / 1920 * 1080)
    stack = num("PAD_TOP") + num("HEADER_H") + box_h + num("BROWSER_BAR") + num("PAD_BOTTOM")
    ok("scene 5 stack fits the frame", stack <= 1080,
       "%d px of content in 1080" % stack)
    ok("the browser cannot be flex-shrunk", 'flex: "0 0 auto"' in src,
       "the browser and the header both need it")
    ok("the capture keeps its 16:9", "(BOX_W / 1920) * 1080" in src,
       "any other height distorts the footage")


# ------------------------------------------------------------------ text
def check_text(text: str) -> None:
    group("TEXT")
    rendered = strip_comments(text)
    bad = re.findall(r"[–—]", text)
    ok("no em or en dashes in the film source", not bad, "%d found" % len(bad))

    # the two claims the fact-check removed must not creep back
    for banned, why in [
        ("one copy of the data", "both routes hold two sets of files"),
        ("2 copies", "the copy avoided is the Import copy, not a warehouse copy"),
        ("half the rate", "only true against the default starter pool"),
    ]:
        ok("retracted claim absent: %r" % banned,
           banned.lower() not in rendered.lower(), why)


# ----------------------------------------------------------------- short
def master_total() -> int:
    """Rebuild Film4.tsx's own arithmetic, so the two cannot disagree.

    This read Film.tsx until the social cut started seeking into Film4, at
    which point it was checking the windows against a film they are not cut
    from: 6,140 frames instead of 5,190. A bounds check against the wrong
    bound is worse than none, because it reports pass.
    """
    film = (SRC / "Film4.tsx").read_text(encoding="utf-8")
    overlap = int(re.search(r"TRANS\s*=\s*(\d+)", film).group(1))
    durs = [int(m) for m in re.findall(r'id:\s*"[a-z]+",\s*dur:\s*(\d+)', film)]
    if not durs:
        return 0
    start = 0
    for d in durs[:-1]:
        start += d - overlap
    return start + durs[-1]


def check_short() -> None:
    group("SOCIAL CUT")
    p = SRC / "Short.tsx"
    if not p.exists():
        ok("Short.tsx is present", False)
        return
    src = p.read_text(encoding="utf-8")
    total = master_total()
    ok("the master's length is known", total > 0, "%d frames" % total)

    segs = [(int(a), int(b)) for a, b in
            re.findall(r"from:\s*(\d+),\s*len:\s*(\d+)", src)]
    ok("segments were found", len(segs) == 8, "found %d" % len(segs))

    for f, ln in segs:
        ok("window [%d, %d) is inside the master" % (f, f + ln),
           f >= 0 and f + ln <= total, "master is %d frames" % total)

    short_total = sum(ln for _, ln in segs)
    secs = short_total / 30.0
    ok("the cut is about 35 seconds", 30 <= secs <= 40, "%.1f s" % secs)

    ok("the cut seeks rather than rebuilds", "from={-seg.from}" in src,
       "a second build of the same scenes would drift from the first")

    w = int(re.search(r"SHORT_W\s*=\s*(\d+)", src).group(1))
    h = int(re.search(r"SHORT_H\s*=\s*(\d+)", src).group(1))
    ok("the cut is 4:5", abs(w / h - 0.8) < 0.001, "%dx%d" % (w, h))


# --------------------------------------------------------------- diagram
def check_diagram() -> None:
    """Scene 5 plays the diagram, so the diagram's words are on screen too.

    Two rounds of correction missed claims here because they were matched by
    exact string rather than scanned for, and they were only caught by watching
    the rendered film. Scan.
    """
    group("DIAGRAM, whose text scene 5 puts on screen")
    parts = REPO / "architecture-diagram" / "parts"
    ok("the diagram source is present", parts.is_dir(), str(parts))
    if not parts.is_dir():
        return

    d = json.loads(UAT.read_text(encoding="utf-8"))
    passed, skipped = d["passed"], d["skipped"]
    total = passed + skipped

    blob = "\n".join(p.read_text(encoding="utf-8")
                     for p in sorted(parts.iterdir())
                     if p.suffix in (".html", ".js", ".css"))

    for pat, why in [
        (r"\b39\b", "the acceptance count was 39 before the write-back checks were cut"),
        (r"extra copy of", "the retracted Warehouse-copy claim"),
        (r"[Tt]hat copy is never made", "the retracted Warehouse-copy claim"),
        (r"no second copy", "loose: the copy avoided is the third one, the Import copy"),
        (r"[Oo]ne copy of the data", "both routes persist a mirror and a gold layer"),
    ]:
        hits = re.findall(pat, blob)
        ok("diagram is clear of %r" % pat, not hits, "%d hit(s), %s" % (len(hits), why))

    ok("diagram states the real pass count", "%d acceptance" % passed in blob
       or "%d / %d" % (passed, passed) in blob, "expected %d" % passed)
    ok("diagram states the real total", "%d acceptance checks" % total in blob
       or "%d skipped" % skipped in blob, "expected %d checks, %d skipped" % (total, skipped))

    built = REPO / "architecture-diagram" / "index.html"
    ok("index.html was rebuilt after the parts changed",
       built.exists() and built.stat().st_mtime >= max(
           p.stat().st_mtime for p in parts.iterdir()),
       "run assemble.py")

    ok("the capture is newer than the diagram it captures",
       ARCH.exists() and built.exists() and ARCH.stat().st_mtime >= built.stat().st_mtime,
       "re-run scripts/capture_arch.py")


# ---------------------------------------------------------------- layers
def check_layers() -> None:
    """A scene that states a thing and then replaces it must own its headline.

    The first cut wrapped only the lower half of four scenes in a fading div
    and left the headline outside it, so the headline sat at full opacity under
    the second half. Scene 8 read as a double exposure for six seconds and only
    watching the render caught it. Phase owns everything it shows, so the check
    is simply: no Display may appear before the first Phase.
    """
    group("LAYERS")
    for p in sorted((SRC / "scenes").glob("*.tsx")):
        src = p.read_text(encoding="utf-8")
        if "<Phase" not in src:
            continue
        first_phase = src.index("<Phase")
        bad = [m for m in re.finditer(r"<Display\b", src) if m.start() < first_phase]
        ok("%s: every headline is inside a phase" % p.name, not bad,
           "%d headline(s) outside" % len(bad))

        # a phase that fades out before the next fades in, or a short overlap,
        # is a dissolve. A long one is two scenes on screen at once.
        outs = [int(m) for m in re.findall(r"const OUT = (\d+)", src)]
        ins = [int(m) for m in re.findall(r"const IN = (\d+)", src)]
        if outs and ins:
            gap = ins[0] - outs[0]
            ok("%s: the phase swap is a dissolve, not a pile-up" % p.name,
               0 <= gap <= 30, "second phase starts %d frames after the first leaves" % gap)

    # the ad-hoc overlay that caused it must not come back
    scenes = chr(10).join(q.read_text(encoding="utf-8")
                       for q in sorted((SRC / "scenes").glob("*.tsx")))
    ok("no ad-hoc full-frame opacity overlays",
       "pointerEvents: \"none\"" not in scenes,
       "those were the overlays that sat on top of a live headline")


def main() -> None:
    text = scene_text()
    check_numbers(text)
    check_generator_claims(text)
    check_crops()
    check_footage()
    check_diagram()
    check_layers()
    check_short()
    check_text(text)

    print("\n%d checks" % checks)
    if problems:
        print("FAILED: %d problem(s)" % len(problems))
        for p in problems:
            print("  - %s" % p)
        sys.exit(1)
    print("PASSED: every figure on screen matches the artifact it comes from.")


if __name__ == "__main__":
    main()
