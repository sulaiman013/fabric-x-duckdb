"""Generate a diagnostic notebook that checks the mirror against its source.

  python build_probe_mirror.py                      write notebooks/zz_probe_mirror.Notebook
  fab import "fabric duckdb.Workspace/zz_probe_mirror.Notebook" -i notebooks/zz_probe_mirror.Notebook -f
  fab job start "fabric duckdb.Workspace/zz_probe_mirror.Notebook"

What it measures, on capacity, against the mirrored table the lakehouse
shortcuts at Tables/raw_txn:

  1. row count and distinct trimmed txn_id, to compare with the same two
     figures measured in PostgreSQL;
  2. distinct txn_id per md5 bucket (5 hex chars), so the one bucket that
     differs from PostgreSQL can be found without moving 49 million ids;
  3. for each key in KEYS, every physical data file that holds it, with the
     file's key statistics from the Delta log, so a row the replication engine
     will not match can be located (BUILD_LOG section 40).

PostgreSQL side of the comparison, run locally:

  SELECT count(*), count(DISTINCT trim(txn_id)) FROM landing.raw_txn;
  SELECT substr(md5(trim(txn_id)),1,5) b, count(DISTINCT trim(txn_id)) n
  FROM landing.raw_txn GROUP BY 1;

Results go to Files/probe_mirror.json in the fincrime lakehouse. Delete the
notebook afterwards; it is a probe, not a pipeline step.
"""

import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "notebooks", "zz_probe_mirror.Notebook")
WS = "7e0f6e0d-3730-449f-8be6-2beaec28587b"
LAKEHOUSE = "74f54fe9-a2e4-46fc-b7c9-52cb65d752ff"
KEYS = [3870724, 3870725, 12345678, 50000004, 50000005, 50000006]

CELL = r'''
import duckdb, json, os, time
from deltalake import DeltaTable
base = "/lakehouse/default/Tables/raw_txn"
SRC = f"delta_scan('{base}')"
con = duckdb.connect(); con.execute("SET TimeZone='UTC'")
out = {}

t0 = time.time()
n, d = con.execute(f"SELECT count(*), count(DISTINCT trim(txn_id)) FROM {SRC}").fetchone()
out["rows"], out["distinct_txn_id"] = n, d
print(f"rows {n:,}  distinct txn_id {d:,}  ({time.time()-t0:.0f}s)")

t0 = time.time()
hist = dict(con.execute(f"""SELECT substr(md5(trim(txn_id)), 1, 5), count(DISTINCT trim(txn_id))
                            FROM {SRC} WHERE txn_id IS NOT NULL GROUP BY 1""").fetchall())
out["hist"] = hist
print(f"buckets {len(hist):,}  ({time.time()-t0:.0f}s)")

acts = DeltaTable(base).get_add_actions(flatten=True).to_pandas()
kmin = [c for c in acts.columns if c.startswith("min.") and c.endswith("_mirror_row_id")]
kmax = [c for c in acts.columns if c.startswith("max.") and c.endswith("_mirror_row_id")]
out["files"] = len(acts); out["keys"] = {}
for key in KEYS:
    found = []
    for _, r in acts.iterrows():
        path = os.path.join(base, r["path"])
        cnt = con.execute(f"SELECT count(*) FROM read_parquet('{path}') WHERE _mirror_row_id = {key}").fetchone()[0]
        if cnt:
            found.append({"file": r["path"][-48:], "rows_with_key": int(cnt), "num_records": int(r["num_records"]),
                          "stats_min": str(r[kmin[0]]) if kmin else None, "stats_max": str(r[kmax[0]]) if kmax else None,
                          "modified": str(r.get("modification_time"))})
    live = con.execute(f"SELECT txn_id, txn_status FROM {SRC} WHERE _mirror_row_id = {key}").fetchall()
    out["keys"][str(key)] = {"physical_files": found, "visible_rows": [[str(x) for x in v] for v in live]}
    print(key, "visible:", live, "| physical:", found)

with open("/lakehouse/default/Files/probe_mirror.json", "w") as fh:
    json.dump(out, fh)
print("written Files/probe_mirror.json")
'''


def main():
    cells = [
        {"cell_type": "code", "metadata": {}, "outputs": [], "execution_count": None,
         "source": ["%%configure -f\n", "{\n", '    "vCores": 8\n', "}\n"]},
        {"cell_type": "code", "metadata": {}, "outputs": [], "execution_count": None,
         "source": ("KEYS = %s\n" % json.dumps(KEYS) + CELL.strip("\n") + "\n").splitlines(keepends=True)},
    ]
    body = "".join(cells[1]["source"])
    compile(body, "<probe>", "exec")
    nb = {"nbformat": 4, "nbformat_minor": 5, "cells": cells, "metadata": {
        "kernel_info": {"name": "jupyter", "jupyter_kernel_name": "python3.11"},
        "kernelspec": {"name": "jupyter", "display_name": "Python (Jupyter)"},
        "language_info": {"name": "python"},
        "microsoft": {"language": "python", "language_group": "jupyter_python"},
        "dependencies": {"lakehouse": {"default_lakehouse": LAKEHOUSE, "default_lakehouse_name": "fincrime",
                                       "default_lakehouse_workspace_id": WS,
                                       "known_lakehouses": [{"id": LAKEHOUSE}]}}}}
    os.makedirs(OUT, exist_ok=True)
    with io.open(os.path.join(OUT, "notebook-content.ipynb"), "w", encoding="utf-8", newline="") as fh:
        json.dump(nb, fh, indent=1); fh.write("\n")
    with io.open(os.path.join(OUT, ".platform"), "w", encoding="utf-8", newline="") as fh:
        json.dump({"$schema": ("https://developer.microsoft.com/json-schemas/fabric/"
                               "gitIntegration/platformProperties/2.0.0/schema.json"),
                   "metadata": {"type": "Notebook", "displayName": "zz_probe_mirror"},
                   "config": {"version": "2.0", "logicalId": "00000000-0000-0000-0000-000000000000"}},
                  fh, indent=2); fh.write("\n")
    print("wrote %s" % os.path.normpath(OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
