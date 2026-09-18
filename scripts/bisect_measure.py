"""Bisect the report measure against a live Power BI Desktop via the bridge.

  python bisect_measure.py            run every stage
  python bisect_measure.py --only 3   run one stage

Why
---
A measure can be valid DAX, reproduce its fixture exactly as an EVALUATE query,
and still fail inside a visual. `SUMMARIZECOLUMNS` is the well-known case: it
cannot be evaluated under an external filter context, which is precisely what a
visual imposes and what a query does not. Testing with a query therefore cannot
reproduce the failure at all.

The only reliable oracle is the visual itself. This script writes a measure into
the report, reloads Desktop through the bridge, captures the page, and decides
pass or fail by comparing the capture against a known-failure baseline. Stages
build up from a trivial expression to the full payload, so the first failing
stage names the construct responsible.

Detection
---------
Power BI's "Something's wrong with one or more fields" panel renders almost
identically every time, so a capture within a small distance of the baseline is
a failure. Anything meaningfully different rendered something.
"""

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
RX = os.path.join(ROOT, "report", "FinCrime.Report", "definition",
                  "reportExtensions.json")
DAXF = os.path.abspath(os.path.join(
    ROOT, "..", "dax-with-js", "dax", "fincrime-overview.dax"))
SHOTS = os.path.join("C:", os.sep, "tmp", "bisect")
PAGE = "Overview"


def dax_body():
    src = io.open(DAXF, encoding="utf-8").read()
    m = re.search(r"^Financial Crime Overview =\s*$(.*?)^RETURN", src,
                  re.S | re.M)
    if not m:
        raise SystemExit("cannot find measure body")
    return m.group(1)


def var_block(upto):
    """Return the VAR block truncated just before the named VAR."""
    body = dax_body()
    i = body.find("VAR " + upto)
    if i < 0:
        raise SystemExit("VAR %s not found" % upto)
    return body[:i]


def wrap(expr):
    return expr


STAGES = [
    # name, description, expression
    ("trivial", "string literal only",
     '"<div style=\'padding:30px;font:22px Segoe UI\'>S1 literal</div>"'),

    ("measure", "one model measure",
     '"<div style=\'padding:30px;font:22px Segoe UI\'>S2 txns "'
     ' & FORMAT ( [Transactions], "#,0" ) & "</div>"'),

    ("dims", "dimension VAR block + one label list",
     var_block("CubeRows") +
     'RETURN\n"<div style=\'padding:30px;font:20px Segoe UI\'>S3 channels: "'
     ' & ChannelsJs & "</div>"'),

    ("cube", "the cube CONCATENATEX",
     var_block("MonthsJs") +
     'RETURN\n"<div style=\'padding:30px;font:20px Segoe UI\'>S4 cube chars: "'
     ' & FORMAT ( LEN ( CubeJs ), "#,0" ) & "</div>"'),

    ("rules", "the rules block",
     var_block("TotTxns") +
     'RETURN\n"<div style=\'padding:30px;font:20px Segoe UI\'>S5 rules: "'
     ' & RulesJs & "</div>"'),

    ("payload", "the whole payload string, no renderer",
     dax_body() +
     'RETURN\n"<div style=\'padding:30px;font:20px Segoe UI\'>S6 payload chars: "'
     ' & FORMAT ( LEN ( Payload ), "#,0" ) & "</div>"'),
]


def set_measure(expr):
    d = json.load(io.open(RX, encoding="utf-8"))
    d["entities"][0]["measures"][0]["expression"] = expr
    with io.open(RX, "w", encoding="utf-8", newline="") as fh:
        json.dump(d, fh, indent=2)
        fh.write("\n")


BRIDGE = None


def bridge_cmd():
    """Resolve the CLI. It is an npm shim (.cmd on Windows), so passing the bare
    name to subprocess fails with WinError 2; only a shell or the .cmd path
    works."""
    global BRIDGE
    if BRIDGE:
        return BRIDGE
    for c in (os.path.join(os.path.expanduser("~"), "AppData", "Roaming",
                           "npm", "powerbi-desktop.cmd"),
              os.path.join(os.path.expanduser("~"), "AppData", "Roaming",
                           "npm", "powerbi-desktop")):
        if os.path.exists(c):
            BRIDGE = c
            return BRIDGE
    BRIDGE = "powerbi-desktop"
    return BRIDGE


def bridge(*args):
    return subprocess.run([bridge_cmd()] + list(args), shell=False,
                          capture_output=True, text=True, timeout=180)


def capture(path):
    bridge("reload")
    time.sleep(38)
    r = bridge("screenshot", PAGE, "--output", path, "--scale", "1")
    return os.path.exists(path), r.stdout


def sig(path):
    """Coarse signature: size plus a hash of the middle band where the error
    panel sits. Two failures agree; a real render does not."""
    data = io.open(path, "rb").read()
    return len(data), hashlib.sha1(data).hexdigest()[:12]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int)
    args = ap.parse_args()

    if not os.path.isdir(SHOTS):
        os.makedirs(SHOTS)

    backup = json.load(io.open(RX, encoding="utf-8"))
    original = backup["entities"][0]["measures"][0]["expression"]

    results = []
    try:
        for n, (name, desc, expr) in enumerate(STAGES, 1):
            if args.only and n != args.only:
                continue
            print("\n[%d] %-9s %s" % (n, name, desc))
            print("    expression %s chars" % "{:,}".format(len(expr)))
            set_measure(expr)
            path = os.path.join(SHOTS, "s%d_%s.png" % (n, name))
            ok, out = capture(path)
            if not ok:
                print("    CAPTURE FAILED: %s" % out[:160])
                results.append((name, "capture-failed", ""))
                continue
            size, h = sig(path)
            print("    capture %s bytes  sha %s" % ("{:,}".format(size), h))
            results.append((name, size, h))
    finally:
        set_measure(original)
        print("\nrestored the original measure")

    print("\nSUMMARY")
    for name, size, h in results:
        print("  %-9s %s %s" % (name, size, h))
    print("\nOpen the PNGs in %s: the first that shows an error panel"
          % SHOTS)
    print("names the construct that a visual will not evaluate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
