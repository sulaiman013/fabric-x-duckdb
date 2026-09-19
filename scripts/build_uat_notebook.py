"""Generate the capacity half of the end-to-end UAT.

  python build_uat_notebook.py
  fab import "fabric duckdb.Workspace/zz_uat_capacity.Notebook" -i notebooks/zz_uat_capacity.Notebook -f
  fab job start "fabric duckdb.Workspace/zz_uat_capacity.Notebook"

`scripts/uat.py` does all of that for you and merges the result with the checks
that can only run locally. This file exists because some checks have no local
equivalent:

  * the mirror's *content*, not just its status counter
  * the gold parquet's physical types, which is what broke the Spark write once
  * the Delta tables' V-Order properties, read from the tables themselves

Every check appends to CHECKS as {id, name, ok, detail}. The notebook never
raises on a failed check: it records it and carries on, so one failure does not
hide the twelve after it. Results go to Files/uat_capacity.json.
"""

import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "notebooks", "zz_uat_capacity.Notebook")
WS = "7e0f6e0d-3730-449f-8be6-2beaec28587b"
LAKEHOUSE = "74f54fe9-a2e4-46fc-b7c9-52cb65d752ff"

# Measured in PostgreSQL 2026-09-19. uat.py re-measures these live and passes
# the fresh pair in; these are the fallback when the notebook runs standalone.
PG_ROWS = 50000001
PG_DISTINCT = 49406791

# Run 4 on capacity, the first build with every section 40 fix in place.
# A later run must reproduce this rule for rule or the build is not deterministic.
BASELINE_FIRINGS = {"R02": 10118821, "R03": 3624172, "R04": 10164144,
                    "R05": 864962, "R06": 13697031, "R07": 2126003,
                    "R09": 24580346}

TABLES = ["fact_transaction", "fact_alert", "dim_customer", "dim_merchant",
          "dim_channel", "dim_card", "dim_date", "dim_time", "dim_risk_rule"]

BODY = r'''
import json, os, time
import duckdb

CHECKS = []
NOTES = {}

def check(cid, name, fn):
    """Run one check. A raised exception is a failed check, never a dead run."""
    try:
        ok, detail = fn()
    except Exception as e:
        ok, detail = False, "{}: {}".format(type(e).__name__, str(e)[:300])
    CHECKS.append({"id": cid, "name": name, "ok": bool(ok), "detail": str(detail)[:600]})
    print("{:<5} {:<4} {}".format(cid, "PASS" if ok else "FAIL", name))
    print("        {}".format(str(detail)[:300]))

con = duckdb.connect()
con.execute("SET TimeZone='UTC'")
MIRROR = "delta_scan('/lakehouse/default/Tables/raw_txn')"
GOLD = "/lakehouse/default/Files/gold"
TABLES_DIR = "/lakehouse/default/Tables"

# ---------------------------------------------------------------- phase 1
def c_mirror_counts():
    n, d = con.execute(
        "SELECT count(*), count(DISTINCT trim(txn_id)) FROM " + MIRROR).fetchone()
    NOTES["mirror_rows"], NOTES["mirror_distinct"] = n, d
    drow, ddis = n - PG_ROWS, d - PG_DISTINCT
    # The known, documented divergence is exactly one row: 3870725, deleted at
    # the source before the replication slot existed (BUILD_LOG section 40).
    # Anything else is new and must fail the pass.
    ok = (drow, ddis) in ((0, 0), (1, 1))
    tail = "" if (drow, ddis) == (0, 0) else "; known pre-slot row 3870725"
    return ok, "mirror {:,} rows / {:,} distinct vs source {:,} / {:,} ({:+d}, {:+d}){}".format(
        n, d, PG_ROWS, PG_DISTINCT, drow, ddis, tail)

def c_probe_row():
    """The live change uat.py just made in PostgreSQL must be visible here."""
    if not PROBE_TOKEN:
        return True, "no probe token supplied, skipped"
    rows = con.execute("SELECT merchant_name, txn_status FROM " + MIRROR
                       + " WHERE _mirror_row_id = " + str(PROBE_ROW)).fetchall()
    if not rows:
        return False, "probe row {} is not in the mirror at all".format(PROBE_ROW)
    got = rows[0][0]
    return got == PROBE_TOKEN, "row {} merchant_name = {!r}, expected {!r}".format(
        PROBE_ROW, got, PROBE_TOKEN)

check("P1.1", "mirror row and key counts match the source", c_mirror_counts)
check("P1.2", "the live PostgreSQL change is visible in OneLake", c_probe_row)

# ---------------------------------------------------------------- phase 2
def c_evidence_present():
    with open("/lakehouse/default/Files/build_gold.json") as fh:
        NOTES["build"] = json.load(fh)
    with open("/lakehouse/default/Files/verify.json") as fh:
        NOTES["verify"] = json.load(fh)
    b = NOTES["build"]
    return True, "build ran {} on the {} kernel, {} vCores, duckdb {}".format(
        b["ran_at_utc"], b["kernel"], b["vcores_requested"], b["duckdb_version"])

def c_python_kernel():
    env = NOTES["build"]["env"]
    return (env["spark_in_globals"] is False and env["cpu_count"] >= 8,
            "spark_in_globals={}, cpu_count={}, ram_gb={}".format(
                env["spark_in_globals"], env["cpu_count"], env["ram_gb"]))

def c_counts_match_verify():
    b, v = NOTES["build"]["counts"], NOTES["verify"]["tables"]
    bad = [t for t in b if v.get(t, {}).get("rows") != b[t]]
    return not bad, ("all {} tables match the verified Delta layer".format(len(b))
                     if not bad else "differ: {}".format(bad))

def c_determinism():
    rf = NOTES["build"].get("rule_firings")
    if not rf:
        return False, "this build recorded no rule_firings; regenerate the notebook"
    diff = {r: (rf.get(r), BASELINE_FIRINGS.get(r))
            for r in set(rf) | set(BASELINE_FIRINGS)
            if rf.get(r) != BASELINE_FIRINGS.get(r)}
    return not diff, ("identical to the baseline rule by rule: {}".format(json.dumps(rf))
                      if not diff else "differs from the baseline: {}".format(diff))

def c_dedup_recon():
    rc = NOTES["build"].get("recon")
    if not rc:
        return False, "this build recorded no reconciliation; regenerate the notebook"
    ok = (rc["multi_survivor_txn_ids"] == 0
          and rc["scored_rows"] - rc["removed"] == rc["deduped_rows"]
          and rc["deduped_rows"] == rc["distinct_txn_id_scored"])
    return ok, "{:,} scored to {:,} kept ({:,} removed), {:,} distinct ids, {} surviving twice".format(
        rc["scored_rows"], rc["deduped_rows"], rc["removed"],
        rc["distinct_txn_id_scored"], rc["multi_survivor_txn_ids"])

def c_parquet_instants():
    """Timestamps must be isAdjustedToUTC, or Spark reads them as NTZ and the
    V-Order write fails. This is the check that would have caught it first."""
    bad = []
    for t in TABLES:
        path = "{}/{}.parquet".format(GOLD, t)
        if not os.path.exists(path):
            bad.append("{} missing".format(t))
            continue
        q = ("SELECT name, logical_type FROM parquet_schema('" + path
             + "') WHERE logical_type LIKE '%Timestamp%'")
        for name, lt in con.execute(q).fetchall():
            if "isAdjustedToUTC=1" not in str(lt):
                bad.append("{}.{} {}".format(t, name, lt))
    return not bad, "every timestamp column is an instant" if not bad else str(bad)

def c_delta_vorder():
    props = NOTES["verify"]["checks"].get("vorder_tblproperties") or {}
    bad = [t for t, p in props.items()
           if not (isinstance(p, dict)
                   and p.get("delta.parquet.vorder.enabled") == "true")]
    return (bool(props) and not bad,
            "V-Order enabled on all {} tables".format(len(props))
            if not bad else "missing on: {}".format(bad))

def c_orphans():
    o = NOTES["verify"]["checks"].get("orphan_keys") or {}
    bad = {k: v for k, v in o.items() if k.startswith("bad_") and v}
    return not bad, "0 orphan keys across {:,} fact rows".format(o.get("total", 0))

def c_delta_readable():
    from deltalake import DeltaTable
    out = []
    for t in sorted(os.listdir(TABLES_DIR)):
        if not t.startswith("gold_"):
            continue
        dt = DeltaTable("{}/{}".format(TABLES_DIR, t))
        out.append([t, dt.version(), len(dt.files())])
    NOTES["delta"] = out
    return len(out) == 9, "{} gold Delta tables, versions {}".format(
        len(out), sorted(set(v for _, v, _ in out)))

check("P2.1", "the build and verify evidence files exist", c_evidence_present)
check("P2.2", "the transformation ran on the Python kernel at 8 vCores", c_python_kernel)
check("P2.3", "notebook counts equal the verified Delta layer", c_counts_match_verify)
check("P2.4", "the build is deterministic, rule by rule", c_determinism)
check("P2.5", "dedup reconciles and no id survives twice", c_dedup_recon)
check("P2.6", "gold timestamps are instants, not naive", c_parquet_instants)
check("P2.7", "V-Order is enabled on every gold table", c_delta_vorder)
check("P2.8", "referential integrity: no orphan dimension keys", c_orphans)
check("P2.9", "all nine gold Delta tables read back", c_delta_readable)

# ---------------------------------------------------------------- result
passed = sum(1 for c in CHECKS if c["ok"])
RESULT = {"ran_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "passed": passed, "total": len(CHECKS),
          "checks": CHECKS, "notes": NOTES}
with open("/lakehouse/default/Files/uat_capacity.json", "w") as fh:
    json.dump(RESULT, fh, indent=1, default=str)
print()
print("capacity UAT: {}/{} passed".format(passed, len(CHECKS)))
for c in CHECKS:
    if not c["ok"]:
        print("  FAILED {} {}: {}".format(c["id"], c["name"], c["detail"]))
'''


def build(pg_rows=PG_ROWS, pg_distinct=PG_DISTINCT, probe_row=0, probe_token=""):
    """Write the notebook, with the source figures and probe token baked in."""
    header = (
        "PG_ROWS = {}\n"
        "PG_DISTINCT = {}\n"
        "PROBE_ROW = {}\n"
        "PROBE_TOKEN = {}\n"
        "BASELINE_FIRINGS = {}\n"
        "TABLES = {}\n"
    ).format(pg_rows, pg_distinct, probe_row, json.dumps(probe_token),
             json.dumps(BASELINE_FIRINGS), json.dumps(TABLES))
    src = header + BODY.strip("\n") + "\n"
    compile(src, "<uat>", "exec")
    cells = [
        {"cell_type": "code", "metadata": {}, "outputs": [], "execution_count": None,
         "source": ["%%configure -f\n", "{\n", '    "vCores": 8\n', "}\n"]},
        {"cell_type": "code", "metadata": {}, "outputs": [], "execution_count": None,
         "source": src.splitlines(keepends=True)},
    ]
    nb = {"nbformat": 4, "nbformat_minor": 5, "cells": cells, "metadata": {
        "kernel_info": {"name": "jupyter", "jupyter_kernel_name": "python3.11"},
        "kernelspec": {"name": "jupyter", "display_name": "Python (Jupyter)"},
        "language_info": {"name": "python"},
        "microsoft": {"language": "python", "language_group": "jupyter_python"},
        "dependencies": {"lakehouse": {
            "default_lakehouse": LAKEHOUSE, "default_lakehouse_name": "fincrime",
            "default_lakehouse_workspace_id": WS,
            "known_lakehouses": [{"id": LAKEHOUSE}]}}}}
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    with io.open(os.path.join(OUT, "notebook-content.ipynb"), "w",
                 encoding="utf-8", newline="") as fh:
        json.dump(nb, fh, indent=1)
        fh.write("\n")
    with io.open(os.path.join(OUT, ".platform"), "w", encoding="utf-8",
                 newline="") as fh:
        json.dump({"$schema": ("https://developer.microsoft.com/json-schemas/fabric/"
                               "gitIntegration/platformProperties/2.0.0/schema.json"),
                   "metadata": {"type": "Notebook", "displayName": "zz_uat_capacity"},
                   "config": {"version": "2.0",
                              "logicalId": "00000000-0000-0000-0000-000000000000"}},
                  fh, indent=2)
        fh.write("\n")
    return os.path.normpath(OUT)


def main():
    path = build()
    print("wrote %s" % path)
    print("  first cell is %%configure, body compiles, 11 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
