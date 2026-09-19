# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "jupyter",
# META     "jupyter_kernel_name": "python3.11"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "74f54fe9-a2e4-46fc-b7c9-52cb65d752ff",
# META       "default_lakehouse_name": "fincrime",
# META       "default_lakehouse_workspace_id": "7e0f6e0d-3730-449f-8be6-2beaec28587b",
# META       "known_lakehouses": [
# META         {
# META           "id": "74f54fe9-a2e4-46fc-b7c9-52cb65d752ff"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

# MAGIC %%configure -f
# MAGIC {
# MAGIC     "vCores": 8
# MAGIC }


# CELL ********************

PG_ROWS = 50000001
PG_DISTINCT = 49406791
PROBE_ROW = 12345678
PROBE_TOKEN = "UAT-20260919-092459"
WS_ID = "7e0f6e0d-3730-449f-8be6-2beaec28587b"
OPS_DB_ID = "446f966e-7df5-4284-a279-fdb32ef3b8a1"
BASELINE_FIRINGS = {"R02": 10118821, "R03": 3624172, "R04": 10164144, "R05": 864962, "R06": 13697031, "R07": 2126003, "R09": 24580346}
TABLES = ["fact_transaction", "fact_alert", "dim_customer", "dim_merchant", "dim_channel", "dim_card", "dim_date", "dim_time", "dim_risk_rule"]
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

# ---------------------------------------------------------------- phase 4
ALERT_ID = "UAT-" + time.strftime("%Y%m%d-%H%M%S", time.gmtime())
# The ops tables are Delta inside the SQL database's own OneLake area, not in
# this lakehouse. That path is what closes the loop, so it is read directly.
OPS_TABLES = ("abfss://" + WS_ID + "@onelake.dfs.fabric.microsoft.com/"
              + OPS_DB_ID + "/Tables/ops")

def _functions():
    import notebookutils
    return notebookutils.udf.getFunctions("fincrime_fn")

def _health(fns):
    """ops_health returns 'alert_disposition=0, case=0, ...', not JSON."""
    raw = fns.ops_health()
    if isinstance(raw, dict):
        return raw
    out = {}
    for part in str(raw).split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            try:
                out[k.strip()] = int(v.strip())
            except ValueError:
                out[k.strip()] = v.strip()
    return out

def c_writeback():
    """The whole loop: read state, write through the function, read it again."""
    fns = _functions()
    NOTES["udf_functions"] = sorted(f["Name"] for f in fns.functionDetails)
    before = _health(fns)
    msg = fns.disposition_alert(alertId=ALERT_ID, mirrorRowId=12345678,
                                verdict="FALSE_POSITIVE",
                                reason="end-to-end UAT",
                                analyst="uat")
    after = _health(fns)
    NOTES["ops_before"], NOTES["ops_after"], NOTES["udf_message"] = before, after, msg
    delta = after.get("alert_disposition", 0) - before.get("alert_disposition", 0)
    return delta == 1, "alert_disposition {} to {} ({:+d}); returned {!r}".format(
        before.get("alert_disposition"), after.get("alert_disposition"),
        delta, str(msg)[:120])

def c_validation_rejects():
    """A bad verdict must come back as a clean error, not a stack trace, or the
    public endpoint could write a state the reports do not understand."""
    try:
        _functions().disposition_alert(alertId=ALERT_ID + "-BAD", mirrorRowId=1,
                                       verdict="NOT_A_VERDICT", reason="x",
                                       analyst="uat")
    except Exception as e:
        txt = str(e)
        return ("verdict must be one of" in txt or "NOT_A_VERDICT" in txt,
                "rejected: {}".format(txt[:200]))
    return False, "an invalid verdict was accepted"

def c_loop_closes():
    """The written row must be visible in OneLake as Delta with no replication
    configured at all. A Fabric SQL database mirrors itself, and that is what
    turns an analyst's click into something the next gold rebuild can join."""
    import notebookutils
    listing = [f.name.strip("/") for f in notebookutils.fs.ls(OPS_TABLES)]
    if "alert_disposition" not in listing:
        return False, "ops/alert_disposition is not in OneLake: {}".format(listing)
    # Read it with DuckDB, not delta-rs. Fabric's self-mirrored SQL tables
    # enable the deletionVectors reader feature, which DuckDB supports and
    # delta-rs does not (Microsoft Learn, "Choosing a notebook kernel"). Using
    # DuckDB is also the point: it is the engine that builds the gold layer, so
    # this proves the decision is joinable on the next rebuild.
    import shutil
    # The SQL database's self-mirroring into OneLake is asynchronous, so the
    # row is not there the instant the function returns. Poll for it and
    # report how long it took, which is the number worth knowing.
    dest = "/tmp/uat_ops"
    t0 = time.time()
    rows, total, local = [], 0, None
    for attempt in range(12):
        shutil.rmtree(dest, ignore_errors=True)
        os.makedirs(dest, exist_ok=True)
        notebookutils.fs.cp(OPS_TABLES + "/alert_disposition", "file:" + dest,
                            recurse=True)
        # cp nests the source directory inside the destination, so find the
        # level that actually holds the transaction log rather than assume it.
        local = next((root for root, dirs, _ in os.walk(dest)
                      if "_delta_log" in dirs), None)
        if local:
            rows = con.execute(
                "SELECT alert_id, _mirror_row_id, disposition, analyst FROM "
                "delta_scan('" + local + "') WHERE alert_id = '"
                + ALERT_ID + "'").fetchall()
            total = con.execute(
                "SELECT count(*) FROM delta_scan('" + local + "')").fetchone()[0]
            if rows:
                break
        time.sleep(20)
    lag = round(time.time() - t0, 1)
    if not local:
        return False, "the copy produced no _delta_log under {}: {}".format(
            dest, os.listdir(dest))
    NOTES["ops_delta_rows"] = total
    NOTES["ops_mirror_lag_s"] = lag
    NOTES["ops_delta_row_for_this_run"] = [[str(x) for x in r] for r in rows]
    if not rows:
        return False, ("this run's decision had not reached OneLake after {}s; "
                       "alert_disposition holds {} older row(s)".format(lag, total))
    return True, (
        "{} ops tables mirror themselves to OneLake with no configuration; this "
        "run's decision arrived in {}s and DuckDB read it back from {} row(s): {}"
        .format(len(listing), lag, total, [[str(x) for x in r] for r in rows]))

check("P4.1", "write-back through a user data function", c_writeback)
check("P4.2", "invalid input is rejected as a handled error", c_validation_rejects)
check("P4.3", "the written decision reaches OneLake as Delta", c_loop_closes)

# ---------------------------------------------------------------- result
passed = sum(1 for c in CHECKS if c["ok"])
RESULT = {"ran_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "passed": passed, "total": len(CHECKS),
          "checks": CHECKS, "notes": NOTES, "uat_alert_id": ALERT_ID}
with open("/lakehouse/default/Files/uat_capacity.json", "w") as fh:
    json.dump(RESULT, fh, indent=1, default=str)
print()
print("capacity UAT: {}/{} passed".format(passed, len(CHECKS)))
for c in CHECKS:
    if not c["ok"]:
        print("  FAILED {} {}: {}".format(c["id"], c["name"], c["detail"]))

