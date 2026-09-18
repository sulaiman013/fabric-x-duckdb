"""Generate 01_build_gold: the DuckDB transformation as a Fabric PYTHON notebook.

  python build_gold_notebook.py
  fab import "fabric duckdb.Workspace/01_build_gold.Notebook" -i ../notebooks/01_build_gold.Notebook -f
  fab job run "fabric duckdb.Workspace/01_build_gold.Notebook"

Why this exists
---------------
The design in notebooks/01_build_gold.md described an 8-vCore Python notebook
running the transformation on capacity. What actually produced the gold layer
in OneLake was DuckDB on a laptop, with the parquet uploaded afterwards and only
the Spark V-Order write running on capacity. This generator turns the design
into a real notebook so the architecture that was described is the one that
runs, and so its cost can be measured instead of asserted.

Python kernel, not Spark
------------------------
The whole point is the compute model. A Python notebook is a single node that
bills at 1 CU per 2 vCores, so 8 vCores is 4 CU. A Spark starter pool bills a
minimum of 8 CU once it scales up. If the metadata below selected the Spark
kernel the notebook would still run, DuckDB would still work on the driver, and
every cost figure derived from it would be wrong by at least 2x. The kernel
metadata is therefore the most important thing in this file.

The modules travel inside the notebook
--------------------------------------
transform.py, rules.py and star.py are embedded verbatim at generation time and
written to a temp directory when the notebook runs. A copy also sits in the
lakehouse under Files/scripts for anyone reading in the explorer, but the run
does not depend on it. The code that was validated against the full 50M rows is
byte-for-byte the code that runs on capacity.

What it writes
--------------
Files/gold/<table>.parquet   the nine gold tables, zstd, overwriting the laptop
                             build with identical, deterministic content
Files/build_gold.json        vCores, RAM, DuckDB version, per-phase timings and
                             per-table row counts, so a CLI-triggered run leaves
                             evidence behind. Its exit value carries the same
                             summary for the job API.

The Delta tables and the semantic model are not touched. That is 02_vorder_write.
"""

import io
import json
import os
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "notebooks", "01_build_gold.Notebook")

WS = "7e0f6e0d-3730-449f-8be6-2beaec28587b"
LAKEHOUSE = "74f54fe9-a2e4-46fc-b7c9-52cb65d752ff"
VCORES = 8

TABLES = ["fact_transaction", "fact_alert", "dim_customer", "dim_merchant",
          "dim_channel", "dim_card", "dim_date", "dim_time", "dim_risk_rule"]

# Selects the Python (Jupyter) kernel rather than Spark. Verified against the
# Fabric notebook definition reference before the first run.
PYTHON_KERNEL_METADATA = {
    "kernel_info": {"name": "jupyter", "jupyter_kernel_name": "python3.11"},
    "kernelspec": {"name": "jupyter", "display_name": "Python (Jupyter)"},
    "language_info": {"name": "python"},
    "microsoft": {"language": "python", "language_group": "jupyter_python"},
}


def md(text):
    lines = text.strip("\n").split("\n")
    return {"cell_type": "markdown", "metadata": {},
            "source": [l + "\n" for l in lines[:-1]] + [lines[-1]]}


def code(text):
    lines = text.strip("\n").split("\n")
    return {"cell_type": "code", "execution_count": None, "outputs": [],
            "metadata": {},
            "source": [l + "\n" for l in lines[:-1]] + [lines[-1]]}


def main():
    sources = {}
    for name in ("transform.py", "rules.py", "star.py"):
        sources[name] = io.open(os.path.join(HERE, name), encoding="utf-8").read()
    # json.dumps produces a literal that is valid Python, so the module text can
    # sit inside a code cell without any manual escaping.
    sources_literal = json.dumps(sources, indent=1)

    cells = [
        # Built by concatenation, never %-formatting: a % format turns the
        # "%%configure" cell magic into "%configure", a line magic that does
        # not exist, and the run dies at cell 1 or silently lands on the
        # 2-vCore default.
        code('%%configure -f\n{\n    "vCores": ' + str(VCORES) + '\n}'),

        md("""
## Build the gold layer: DuckDB on a Fabric Python notebook

Phase 2 of the pipeline, running on capacity. The mirrored PostgreSQL table is
read through the shortcut at `Tables/raw_txn`, cleaned, conformed, scored,
deduplicated and shaped into a star schema by DuckDB, then written as parquet
under `Files/gold`. `02_vorder_write` turns that parquet into V-Ordered Delta.

This is a **Python** notebook on a single node, deliberately. At 8 vCores it
bills 4 CU. The same work on a Spark starter pool would hold at least 8 CU.

The first cell sets the node size and must stay first: `%%configure` only takes
effect at session start, and an API-triggered run honours it.
"""),

        code("""
import os, sys, json, time, shutil, platform

def ram_gb():
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1e9
    except Exception:
        return None

ENV = {
    "cpu_count": os.cpu_count(),
    "ram_gb": round(ram_gb() or 0, 1),
    "tmp_free_gb": round(shutil.disk_usage("/tmp").free / 1e9, 1),
    "python": platform.python_version(),
    # A Spark-kernel session pre-defines `spark`; a Python-kernel session does
    # not. Recording it settles which compute this actually ran on.
    "spark_in_globals": "spark" in globals(),
}
print(json.dumps(ENV, indent=2))
"""),

        md("""
### The transformation code, embedded

`transform.py`, `rules.py` and `star.py` are written out and imported here.
They are the exact files validated against the full 50,000,000 rows, embedded
at generation time by `scripts/build_gold_notebook.py`, so the notebook cannot
drift from the code in the repository.
"""),

        code("SOURCES = " + sources_literal + """

SCRIPTS = "/tmp/fc_scripts"
os.makedirs(SCRIPTS, exist_ok=True)
for name, src in SOURCES.items():
    with open(os.path.join(SCRIPTS, name), "w", encoding="utf-8") as fh:
        fh.write(src)
sys.path.insert(0, SCRIPTS)

from transform import silver_sql
from rules import RULES, enriched_sql, scored_sql
from star import build

print("rules active:", [r[0] for r in RULES])
"""),

        md("""
### Read the mirror through the shortcut

The shortcut resolves to the mirrored database's Delta table. It is read-only,
which is correct: nothing here should be able to write back into the mirror.
DuckDB's memory limit is set from the RAM the node actually has, not from a
constant, so the notebook behaves sensibly whatever size it lands on.
"""),

        code("""
import duckdb

con = duckdb.connect()
limit_gb = max(4, int((ENV["ram_gb"] or 16) * 0.70))
con.execute(f"SET memory_limit='{limit_gb}GB'")
con.execute(f"SET threads={ENV['cpu_count']}")
con.execute("SET preserve_insertion_order=false")
os.makedirs("/tmp/duckdb", exist_ok=True)
con.execute("SET temp_directory='/tmp/duckdb'")
con.execute("INSTALL delta"); con.execute("LOAD delta")

SRC = "delta_scan('/lakehouse/default/Tables/raw_txn')"
TIMING = {}

t0 = time.time()
SOURCE_ROWS = con.execute(f"SELECT count(*) FROM {SRC}").fetchone()[0]
TIMING["count_source_s"] = round(time.time() - t0, 1)
print(f"duckdb {duckdb.__version__}  memory_limit {limit_gb}GB  threads {ENV['cpu_count']}")
print(f"source rows: {SOURCE_ROWS:,}  ({TIMING['count_source_s']}s)")
"""),

        md("""
### Build the star

One call. Cleaning, conforming, the seven risk rules, scoring, deduplication on
`_mirror_row_id`, and the two facts plus seven dimensions with explicit Unknown
members at key -1.
"""),

        code("""
t0 = time.time()
build(con, SRC)
TIMING["build_s"] = round(time.time() - t0, 1)
print(f"star built in {TIMING['build_s']/60:.1f} min")

COUNTS = {}
for t in %s:
    COUNTS[t] = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    print(f"  {t:<18} {COUNTS[t]:>12,}")
""" % json.dumps(TABLES)),

        md("""
### Write gold as parquet

Overwrites `Files/gold`. The content is deterministic, so a rerun produces the
same bytes the laptop build did. The V-Order Delta write is deliberately left to
Spark in `02_vorder_write`: DuckDB cannot produce V-Order, and V-Order is what
makes Direct Lake fast.
"""),

        code("""
GOLD = "/lakehouse/default/Files/gold"
os.makedirs(GOLD, exist_ok=True)

t0 = time.time()
SIZES_MB = {}
for t in %s:
    path = f"{GOLD}/{t}.parquet"
    con.execute(f"COPY {t} TO '{path}' (FORMAT PARQUET, COMPRESSION zstd)")
    SIZES_MB[t] = round(os.path.getsize(path) / 1e6, 1)
TIMING["write_s"] = round(time.time() - t0, 1)
TIMING["total_s"] = round(sum(TIMING.values()), 1)
print(f"gold parquet written in {TIMING['write_s']:.0f}s, "
      f"{sum(SIZES_MB.values())/1000:.2f} GB")
""" % json.dumps(TABLES)),

        md("""
### Leave evidence

A CLI-triggered run has no visible cell output, so the summary is written to
`Files/build_gold.json` and returned as the notebook's exit value. The README
notebook reads this file, which is how its cost figures stay measured rather
than typed.
"""),

        code("""
SUMMARY = {
    "ran_at_utc": time.strftime("%%Y-%%m-%%dT%%H:%%M:%%SZ", time.gmtime()),
    "kernel": "python",
    "vcores_requested": %d,
    "env": ENV,
    "duckdb_version": duckdb.__version__,
    "memory_limit_gb": limit_gb,
    "source_rows": SOURCE_ROWS,
    "timing_s": TIMING,
    "counts": COUNTS,
    "gold_parquet_mb": SIZES_MB,
    "cu": %d / 2,
    "cu_seconds": round(%d / 2 * TIMING["total_s"], 1),
}
with open("/lakehouse/default/Files/build_gold.json", "w") as fh:
    json.dump(SUMMARY, fh, indent=2)
print(json.dumps(SUMMARY, indent=2))

try:
    import notebookutils
    notebookutils.notebook.exit(json.dumps(SUMMARY))
except Exception as e:
    print("exit value not set:", e)
""" % (VCORES, VCORES, VCORES)),
    ]

    metadata = dict(PYTHON_KERNEL_METADATA)
    metadata["dependencies"] = {
        "lakehouse": {
            "default_lakehouse": LAKEHOUSE,
            "default_lakehouse_name": "fincrime",
            "default_lakehouse_workspace_id": WS,
            "known_lakehouses": [{"id": LAKEHOUSE}],
        }
    }
    nb = {"nbformat": 4, "nbformat_minor": 5, "metadata": metadata,
          "cells": cells}

    # Validate before writing anything: a bad cell must not reach the
    # workspace, and an import of a half-broken notebook reports success.
    for c in cells:
        if c["cell_type"] != "code":
            continue
        src = "".join(c["source"])
        if src.startswith("%%"):
            continue
        compile(src, "<cell>", "exec")
    first = "".join(cells[0]["source"])
    if not first.startswith("%%configure"):
        raise SystemExit("first cell must be the %%configure cell magic, got: "
                         + first[:30])

    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    with io.open(os.path.join(OUT, "notebook-content.ipynb"), "w",
                 encoding="utf-8", newline="") as fh:
        json.dump(nb, fh, indent=1)
        fh.write("\n")
    with io.open(os.path.join(OUT, ".platform"), "w", encoding="utf-8",
                 newline="") as fh:
        json.dump({
            "$schema": ("https://developer.microsoft.com/json-schemas/fabric/"
                        "gitIntegration/platformProperties/2.0.0/schema.json"),
            "metadata": {"type": "Notebook", "displayName": "01_build_gold"},
            "config": {"version": "2.0",
                       "logicalId": "00000000-0000-0000-0000-000000000000"},
        }, fh, indent=2)
        fh.write("\n")

    print("wrote %s" % os.path.normpath(OUT))
    print("  %d cells, %d vCores requested, modules embedded: %s"
          % (len(cells), VCORES, ", ".join(sources)))
    print("  embedded source %s chars"
          % "{:,}".format(sum(len(v) for v in sources.values())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
