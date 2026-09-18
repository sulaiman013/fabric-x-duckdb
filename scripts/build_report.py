"""Generate the PBIP report: four pages, each one HTML Content visual.

  python build_report.py
  python build_report.py --open      also create the junction and launch Desktop

Shape
-----
A thin report, live connected to `fincrime_model` in Fabric. Every page carries
two visuals: a native page navigator across the top, and below it one HTML
Content visual fed by a report-level measure that holds both its data and the
renderer.

Navigation has to be native. An HTML visual has no handle on IVisualHost, so it
cannot switch pages no matter what JavaScript is injected into it. Rather than
float a navigator over the content, each page reserves a strip for it and the
content visual starts below.

Why report-level measures
-------------------------
The model is Direct Lake and shared, so a presentation concern has no business
in it. Keeping the measures in `reportExtensions.json` also means the report
carries everything it needs in one folder, which is what makes it reviewable in
git.

A report extension EXTENDS an entity that already exists in the model. Binding
to one that does not exist fails with "Something's wrong with one or more
fields", which reads like a DAX problem and is not.

The HTML Content visual
-----------------------
`htmlContent443BE3AD55E043BF878BED274D3A6855`, the STANDARD edition. The
certified lite edition ends D3A6865 instead, silently strips script tags, and
renders a blank box with no error. It is a public custom visual, so Desktop must
already have it installed; it is not bundled here.

Path length
-----------
PBIR page and visual folders add roughly 105 characters. This project sits deep,
so artifact names are short and the project opens through a junction at
%USERPROFILE%\\pbip\\fincrime. Desktop fails over 260 characters and the error
does not mention paths.
"""

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "report")
DAXDIR = os.path.abspath(os.path.join(ROOT, "..", "dax-with-js", "dax"))

WORKSPACE = "fabric duckdb"
MODEL_NAME = "fincrime_model"
MODEL_ID = "cb8a25d5-76aa-4698-9a25-1e8646809aaa"

VISUAL = "htmlContent443BE3AD55E043BF878BED274D3A6855"
CANVAS_W, CANVAS_H = 1600, 900

# An HTML visual cannot navigate pages: it has no handle on IVisualHost, so no
# amount of injected JavaScript will switch a tab. Navigation therefore has to
# be a native visual, and the page reserves a strip for it rather than letting
# it float over content.
NAV_H = 54
ENTITY = "fact_transaction"

# Theme colours as hex, because Power BI object properties do not take oklch.
# These track the renderer tokens: ground, surface, ink, accent, accent-weak.
C_SURFACE = "#FFFFFF"
C_GROUND = "#F2F8F0"
C_INK = "#1F2A22"
C_INK2 = "#5A6A5E"
C_ACCENT = "#1F8A3B"
C_ACCENT_WEAK = "#CFEBD5"
C_LINE = "#DBE3D9"

# page id, tab label, measure name, generated inline dax file
# Order is the reading order, and the first entry is the landing page. The
# guide sits LAST: a reader opening the report wants the numbers, and sends
# themselves to the guide when something needs explaining.
PAGES = [
    ("Overview", "Overview", "Financial Crime Overview", "overview-inline.dax"),
    ("Rules", "Rule effectiveness", "Rule Effectiveness", "rules-inline.dax"),
    ("Risk", "Risk and exposure", "Risk and Exposure", "risk-inline.dax"),
    ("Guide", "Guide", "Guide", "guide-inline.dax"),
]

JUNCTION = os.path.join(os.path.expanduser("~"), "pbip", "fincrime")


def write(path, obj, raw=False):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        if raw:
            fh.write(obj)
        else:
            json.dump(obj, fh, indent=2)
            fh.write("\n")


def measure_expression(fname, measure):
    """Lift the DAX body out of a generated inline measure file."""
    path = os.path.join(DAXDIR, fname)
    if not os.path.exists(path):
        raise SystemExit("missing %s. Run fincrime/build-measure.py first."
                         % path)
    src = io.open(path, encoding="utf-8").read()
    m = re.search("^" + re.escape(measure) + r" =\s*$(.*)", src, re.S | re.M)
    if not m:
        raise SystemExit("could not find %r in %s" % (measure, path))
    return m.group(1).strip("\n")


def desktop_exe():
    """Locate pbidesktop.exe.

    Two traps. The Store build has no .pbip file association, so os.startfile()
    on a .pbip opens an EMPTY Desktop and still reports success. And its install
    directory under WindowsApps cannot be listed at all (PermissionError), so
    globbing finds nothing even though the exact path exists. The package
    manifest is the only reliable way in.
    """
    ps = ("(Get-AppxPackage -Name Microsoft.MicrosoftPowerBIDesktop | "
          "Select-Object -First 1 -ExpandProperty InstallLocation)")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=30)
        loc = (out.stdout or "").strip()
        if loc:
            exe = os.path.join(loc, "bin", "pbidesktop.exe")
            if os.path.exists(exe):
                return exe
    except Exception:
        pass
    for pat in (os.path.join("C:" + os.sep, "Program Files",
                             "Microsoft Power BI Desktop", "bin",
                             "PBIDesktop.exe"),
                os.path.join("C:" + os.sep, "Program Files (x86)",
                             "Microsoft Power BI Desktop", "bin",
                             "PBIDesktop.exe")):
        if os.path.exists(pat):
            return pat
    return None


def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def color(hex_):
    return {"solid": {"color": lit("'%s'" % hex_)}}


def page_navigator(vid):
    """A native page navigator, styled to match the renderer.

    Selected and default states are set explicitly. Left to itself the
    navigator inherits the base theme and lands in Power BI blue next to a sage
    and green page, which looks like two reports stapled together.
    """
    def txt(sel, col, bold):
        return {"properties": {"fontSize": lit("11D"),
                               "fontColor": color(col),
                               "bold": lit("true" if bold else "false"),
                               "fontFamily": lit("'Segoe UI'")},
                "selector": {"id": sel}}

    def fill(sel, col):
        return {"properties": {"fillColor": color(col),
                               "transparency": lit("0D")},
                "selector": {"id": sel}}

    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.11.0/schema.json",
        "name": vid,
        "position": {"x": 16, "y": 8, "z": 9000,
                     "width": CANVAS_W - 32, "height": NAV_H - 14,
                     "tabOrder": 9000},
        "visual": {
            "visualType": "pageNavigator",
            "objects": {
                "pages": [{"properties": {
                    "showByDefault": lit("true"),
                    "showHiddenPages": lit("false"),
                    "showTooltipPages": lit("false"),
                }}],
                "text": [txt("default", C_INK2, False),
                         txt("selected", "#14532D", True),
                         txt("hover", C_INK, False)],
                "fill": [fill("default", C_SURFACE),
                         fill("selected", C_ACCENT_WEAK),
                         fill("hover", C_GROUND)],
                "outline": [{"properties": {
                    "lineColor": color(C_LINE),
                    "weight": lit("1D"),
                    "transparency": lit("0D"),
                }, "selector": {"id": "default"}},
                    {"properties": {
                        "lineColor": color(C_ACCENT),
                        "weight": lit("1D"),
                        "transparency": lit("0D"),
                    }, "selector": {"id": "selected"}}],
                "shape": [{"properties": {"roundedCornerRadius": lit("7D")}}],
                "padding": [{"properties": {"top": lit("6D"), "bottom": lit("6D"),
                                            "left": lit("14D"), "right": lit("14D")}}],
            },
            "drillFilterOtherVisuals": True,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--open", action="store_true",
                    help="create the junction and launch Power BI Desktop")
    args = ap.parse_args()

    name = "FinCrime"
    rep = os.path.join(OUT, name + ".Report")
    d = os.path.join(rep, "definition")

    # Wipe the pages tree. Overwriting is not enough: a stale visual folder is
    # still a visual, and PBIR renders all of them.
    pages_dir = os.path.join(d, "pages")
    if os.path.isdir(pages_dir):
        shutil.rmtree(pages_dir)

    write(os.path.join(OUT, name + ".pbip"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0",
        "artifacts": [{"report": {"path": name + ".Report"}}],
        "settings": {"enableAutoRecovery": True},
    })

    write(os.path.join(rep, ".platform"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report",
                     "displayName": "Financial Crime Monitoring"},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid4())},
    })

    # definitionProperties 2.0.0 allows EXACTLY ONE property under byConnection:
    # connectionString. The older 1.0 shape carried pbiModelDatabaseName,
    # pbiModelVirtualServerName and connectionType alongside it, and passing
    # those makes Desktop refuse the whole file. The model GUID therefore has to
    # travel inside the connection string as semanticModelId.
    write(os.path.join(rep, "definition.pbir"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {
            "byConnection": {
                "connectionString": (
                    "Data Source=powerbi://api.powerbi.com/v1.0/myorg/%s;"
                    "Initial Catalog=%s;Integrated Security=ClaimsToken;"
                    "semanticModelId=%s"
                    % (WORKSPACE, MODEL_NAME, MODEL_ID)),
            }
        },
    })

    write(os.path.join(d, "version.json"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0",
    })

    # A SharedResources base theme must exist as a resourcePackages entry AND as
    # a file, and carry reportVersionAtImport, or Desktop greets you with
    # "issues that could not be resolved" on every open.
    theme_src = os.path.join(
        os.path.expanduser("~"), "Desktop", "work", "25 - tufail",
        "build - WITHOUT BRANDING", "StockFlow.Report", "StaticResources",
        "SharedResources", "BaseThemes", "CY22SU11.json")
    theme_dst = os.path.join(rep, "StaticResources", "SharedResources",
                             "BaseThemes", "CY22SU11.json")
    if os.path.exists(theme_src):
        if not os.path.isdir(os.path.dirname(theme_dst)):
            os.makedirs(os.path.dirname(theme_dst))
        shutil.copyfile(theme_src, theme_dst)
    elif not os.path.exists(theme_dst):
        write(theme_dst, {"name": "CY22SU11"})

    write(os.path.join(d, "report.json"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/2.0.0/schema.json",
        "themeCollection": {"baseTheme": {
            "name": "CY22SU11",
            "reportVersionAtImport": "5.55",
            "type": "SharedResources",
        }},
        "resourcePackages": [{
            "name": "SharedResources",
            "type": "SharedResources",
            "items": [{"name": "CY22SU11", "path": "BaseThemes/CY22SU11.json",
                       "type": "BaseTheme"}],
        }],
        "publicCustomVisuals": [VISUAL],
        "settings": {
            "useStylableVisualContainerHeader": True,
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "useEnhancedTooltips": True,
        },
    })

    # -- the report-level measures, one per page ----------------------------
    measures = []
    for _pid, _lbl, mname, fname in PAGES:
        expr = measure_expression(fname, mname)
        measures.append({
            "name": mname,
            "dataType": "Text",
            "expression": expr,
            "displayFolder": "HTML",
        })
        print("  %-26s %9s chars" % (mname, "{:,}".format(len(expr))))

    write(os.path.join(d, "reportExtensions.json"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/reportExtension/1.0.0/schema.json",
        "name": "extension",
        "entities": [{"name": ENTITY, "measures": measures}],
    })

    write(os.path.join(d, "pages", "pages.json"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
        "pageOrder": [p[0] for p in PAGES],
        "activePageName": PAGES[0][0],
    })

    off = [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}]
    zero = [{"properties": {k: {"expr": {"Literal": {"Value": "0D"}}}
                            for k in ("top", "bottom", "left", "right")}}]

    for pid, label, mname, _f in PAGES:
        write(os.path.join(d, "pages", pid, "page.json"), {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
            "name": pid,
            "displayName": label,
            "displayOption": "FitToPage",
            "height": CANVAS_H,
            "width": CANVAS_W,
            "objects": {"background": [{"properties": {
                "color": color(C_SURFACE),
                "transparency": lit("0D"),
            }}]},
        })

        # Deterministic per page. A fresh uuid per build left the previous
        # visual folder behind, and PBIR renders EVERY folder it finds, so the
        # page ended up with a stack of full-canvas visuals showing whichever
        # orphan errored.
        vid = ("fcv" + pid.lower()).ljust(20, "0")[:20]

        # Full bleed, chrome off, padding zero: the renderer draws its own
        # header and panels, so container styling would sit on top of a page
        # that already has one.
        write(os.path.join(d, "pages", pid, "visuals", vid, "visual.json"), {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.11.0/schema.json",
            "name": vid,
            "position": {"x": 0, "y": NAV_H, "z": 0,
                         "width": CANVAS_W, "height": CANVAS_H - NAV_H,
                         "tabOrder": 0},
            "visual": {
                "visualType": VISUAL,
                "query": {"queryState": {"content": {"projections": [{
                    "field": {"Measure": {
                        "Expression": {"SourceRef": {"Schema": "extension",
                                                     "Entity": ENTITY}},
                        "Property": mname}},
                    "queryRef": ENTITY + "." + mname,
                }]}}},
                "visualContainerObjects": {
                    "background": off, "border": off, "padding": zero,
                    "visualHeader": off,
                },
                "drillFilterOtherVisuals": True,
            },
        })

        nav_id = ("fcn" + pid.lower()).ljust(20, "0")[:20]
        write(os.path.join(d, "pages", pid, "visuals", nav_id, "visual.json"),
              page_navigator(nav_id))

    write(os.path.join(OUT, ".gitignore"),
          "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n", raw=True)

    # Refuse to ship a page with more than one visual: they stack, the top one
    # wins, and chasing that looks exactly like a measure bug.
    for pid, _l, _m, _f in PAGES:
        vdir = os.path.join(d, "pages", pid, "visuals")
        nvis = len(os.listdir(vdir))
        if nvis != 2:
            raise SystemExit("REFUSED: page %s has %d visual folders, expected 2 "
                             "(content + navigator). Every folder renders, and "
                             "stray ones stack on top of the page." % (pid, nvis))

    n = sum(len(f) for _, _, f in os.walk(OUT))
    print()
    print("wrote %s" % os.path.normpath(OUT))
    print("  %d files, canvas %dx%d, %d pages, %dpx nav strip"
          % (n, CANVAS_W, CANVAS_H, len(PAGES), NAV_H))
    longest = max(
        (len(os.path.join(r, f)) for r, _, fs in os.walk(OUT) for f in fs),
        default=0)
    print("  longest path %d chars (Desktop fails over 260)" % longest)

    if args.open:
        jd = os.path.dirname(JUNCTION)
        if not os.path.isdir(jd):
            os.makedirs(jd)
        if not os.path.exists(JUNCTION):
            subprocess.run(["cmd", "/c", "mklink", "/J", JUNCTION, OUT],
                           capture_output=True)
        short = os.path.join(JUNCTION, name + ".pbip")
        print()
        print("junction: %s" % JUNCTION)
        if not os.path.exists(short):
            print("  ERROR: %s not found through the junction" % short)
            return 1
        exe = desktop_exe()
        if exe:
            print("  launching %s" % os.path.basename(exe))
            subprocess.Popen([exe, short])
        else:
            print("  Power BI Desktop not found; opening by association")
            os.startfile(short)
    return 0


if __name__ == "__main__":
    sys.exit(main())
