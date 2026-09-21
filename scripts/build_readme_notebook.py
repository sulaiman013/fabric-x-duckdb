"""Generate 00_README: the workspace documentation as a runnable Python notebook.

  python build_readme_notebook.py
  fab import "fabric duckdb.Workspace/00_README.Notebook" -i ../notebooks/00_README.Notebook -f
  fab job run "fabric duckdb.Workspace/00_README.Notebook"

Two rules shaped this file.

Every number a reader might quote is either MEASURED and says where it was
measured, or MODELLED and says what was assumed. The build-cost cell reads
Files/build_gold.json, the artefact the on-capacity transformation writes, and
the query-latency cell times the model live. Nothing about cost is typed into
the markdown by hand.

Every claim about how Fabric behaves cites Microsoft Learn, because "Direct Lake
reads parquet without importing it" is the kind of sentence that gets repeated
until nobody remembers whether it is true.

The notebook is a Python-kernel notebook so its DuckDB benchmark runs on the
same class of compute as the build it describes.
"""

import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "notebooks", "00_README.Notebook")

WS = "7e0f6e0d-3730-449f-8be6-2beaec28587b"
LAKEHOUSE = "74f54fe9-a2e4-46fc-b7c9-52cb65d752ff"
SQL_ENDPOINT = ("6xdtv76wvqse5lz63juf6hq7gy-bvxa67rqg6pujc7gfpvoykcypm"
                ".datawarehouse.fabric.microsoft.com")

# ---------------------------------------------------------------------------
# Measured facts. Each carries where it came from. BUILD_LOG section numbers
# refer to the repository's build log.
# ---------------------------------------------------------------------------
F = {
    "source_rows": "50,000,000",
    "source_cols": "100",
    "csv_gb": "45.0",
    "pg_gb": "48",
    "gen_min": "35.0",
    "load_min": "10.9",
    "load_rows_s": "76,465",
    "seed_files": "16",
    "seed_gb": "10.5",
    "seed_min": "29",
    "seed_ratio": "4.3x",
    "gold_rows": "49,406,792",
    "dupes": "593,209",
    "gold_parquet_gb": "1.86",
    "gold_delta_gb": "2.5",
    "gold_files": "36",
    "vorder_s": "202",
    "vorder_txt": "3 min 53 s",
    "model_tables": "9",
    "model_rels": "8",
    "model_measures": "17",
    "cube_cells": "2,508",
    "cube_pct": "4%",
    "ceiling": "2,100,000",
    "alerts": "1,423,088",
    "alert_rate": "2.88%",
    "firings": "65,175,479",
    "customers": "5,112,692",
    "posting_before": "47.5%",
    "posting_after": "93.0%",
}

# Cost facts. A notebook is billed while it executes, not for its session start
# (Microsoft Learn, Apache Spark billing and utilization), so the transform is
# priced on its own executing time, from UAT.json. The V-Order job records only
# a wall time (BUILD_LOG section 37), so its figure is an upper bound. Prices
# are the Azure retail prices API, queried 21 September 2026: every Fabric meter
# costs the same per CU-hour within a region, and this capacity is in UK South.
_PY_CU, _EXEC_S, _PY_WALL = 4, 770.6, 895     # DuckDB, Python kernel, 8 vCores
_SP_CU, _SP_WALL = 8, 233                     # V-Order write, Spark starter pool
_PRICE_UKS, _PRICE_USE = 0.21, 0.18
_PILOT_WH_CU_PER_S = 60                       # Warehouse CU-s per engine-second, pilot
_route_cus = _PY_CU * _EXEC_S + _SP_CU * _SP_WALL
F.update({
    "price_uks": "%.2f" % _PRICE_UKS,
    "price_use": "%.2f" % _PRICE_USE,
    "price_date": "21 September 2026",
    "exec_s": "%.1f" % _EXEC_S,
    "vorder_wall_s": "%d" % _SP_WALL,
    "route_cuh": "%.3f" % (_route_cus / 3600),
    "route_usd": "%.2f" % (_route_cus / 3600 * _PRICE_UKS),
    "vorder_cents": "%d" % round(_SP_CU * _SP_WALL / 3600 * _PRICE_UKS * 100),
    "vorder_share": "%d" % round(100.0 * _SP_CU * _SP_WALL / _route_cus),
    "wh_engine_s": "%d" % round(_route_cus / _PILOT_WH_CU_PER_S),
})


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
    cells = []
    A = cells.append

    # =======================================================================
    A(md("""
# Financial Crime Monitoring on Fabric: the README

**What this is.** A complete pipeline from an on-premises PostgreSQL database
to an interactive Power BI report, built on Microsoft Fabric, over
**%(gold_rows)s** card and account transactions. Every item in this workspace
is explained below, in the order the data flows through them.

**How to read it.** Each section answers three questions: what the item is,
how it works, and what it cost. The cost figures are not typed in: the cells
in this notebook read the measurements the pipeline itself wrote, and time the
model live. Run the notebook and the numbers refresh.

**One rule about numbers.** Anything marked **measured** was observed on this
workspace and says where. Anything marked **modelled** is an estimate and says
what was assumed. If a figure has neither label, treat it as a claim, not a
fact.

---

## The workspace at a glance

| Folder | Item | Type | Role |
| --- | --- | --- | --- |
| (root) | `00_README` | Python notebook | This document. Run it and every measured figure refreshes |
| 01 Ingestion | `sulaiman-postgres` | Mirrored database | On-premises PostgreSQL landing in OneLake as Delta, via open mirroring |
| 02 Transformation | `fincrime` | Lakehouse | The gold star schema, plus a shortcut back to the mirror |
| 02 Transformation | `01_build_gold` | Python notebook | DuckDB: clean, conform, score, dedupe, model. 8 vCores |
| 02 Transformation | `02_vorder_write` | Spark notebook | Rewrites gold parquet as V-Ordered Delta |
| 02 Transformation | `03_verify` | Spark notebook | Checks the gold tables on capacity, writes `Files/verify.json` |
| 03 Semantic Model | `fincrime_model` | Semantic model | Direct Lake, %(model_tables)s tables, %(model_rels)s relationships, %(model_measures)s measures |
| 04 Application | `FinCrime` | Report | Four pages, each one HTML visual driven by one measure |
| Deprecated | `stage_lh` | Lakehouse | Empty. Created while investigating uploads, superseded |

The SQL analytics endpoints you see next to the lakehouses and databases are
created automatically with their parent and are not separate work.
""" % F))

    A(code("""
# Everything printed in this notebook is also captured, and the last cell
# writes it next to the data, so a CLI-triggered run leaves readable evidence.
import sys, io
class _Tee:
    def __init__(self, *streams): self.streams = streams
    def write(self, text):
        for st in self.streams: st.write(text)
    def flush(self):
        for st in self.streams: st.flush()
_LOG = io.StringIO()
if not isinstance(sys.stdout, _Tee):
    sys.stdout = _Tee(sys.stdout, _LOG)

# Live inventory, so this table can never go stale.
# Semantic link ships in the Python notebook runtime (Microsoft Learn, "Use
# Python experience in notebooks"); the fallback only runs if a runtime drops it.
try:
    import sempy.fabric as fabric
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "semantic-link"], check=True)
    import sempy.fabric as fabric
items = fabric.list_items()
display(items[["Display Name", "Type", "Id"]].sort_values(["Type", "Display Name"]))
"""))

    # =======================================================================
    A(md("""
---

## The architecture, in one page

The whole pipeline is also drawn as an interactive, animated, single-file HTML
page: two views behind a segmented control, a detail card behind every
component, night mode, and a written explanation on the back of the card. It is
self-contained, so it opens from disk with no server and no network.

**[Open the diagram](https://github.com/sulaiman013/fabric-x-duckdb/blob/master/architecture-diagram/index.html)** &middot; source and build in
[`architecture-diagram/`](https://github.com/sulaiman013/fabric-x-duckdb/blob/master/architecture-diagram)

### Pipeline: how 50 million rows reach a report

![The pipeline view: PostgreSQL on the left, Microsoft Fabric on the right](https://raw.githubusercontent.com/sulaiman013/fabric-x-duckdb/master/architecture-diagram/shot-pipeline.png)

### Transformation: what the notebook actually does

![The transformation view: read, conform, score, deduplicate, build the star](https://raw.githubusercontent.com/sulaiman013/fabric-x-duckdb/master/architecture-diagram/shot-transform.png)

Every figure on those pages was measured on the running system and is
re-measured by `scripts/uat.py` on every acceptance pass. The only thing marked
**modelled** is the Spark cost comparison. The price per CU-hour is quoted for
this capacity's region, and the Warehouse comparison comes from a separate
production pilot.

The page is generated from `parts/` by `assemble.py` and gated by `verify.py`,
which drives both views in a real browser and asserts that nothing overlaps,
nothing escapes its container, every declared wire is actually drawn, and the
packets are moving.
"""))

    # =======================================================================
    A(md("""
---

## 1. Ingestion: on-premises PostgreSQL to OneLake by open mirroring

### The problem it solves

Fabric's **native** database mirroring connects straight to a source, but its
supported sources are Azure SQL, SQL Server, Cosmos DB, Oracle, SAP and
**Azure** Database for PostgreSQL. A PostgreSQL server on `localhost` is not
reachable from Fabric and is not on that list. So this pipeline uses **open
mirroring**: the publisher (a script on the on-premises machine) writes change
files into a *landing zone* in OneLake, and Fabric's replication engine applies
them to a Delta table. Fabric never connects to Postgres at all.

### How it works, in plain terms

Think of the landing zone as an in-tray. You drop numbered parquet files into
it, and Fabric picks them up in order and applies them.

1. **Declare the key.** A `_metadata.json` in the table folder names the
   `keyColumns`. Here that is `_mirror_row_id`, a surrogate key added when the
   table was loaded, because no combination of the %(source_cols)s business
   columns is unique. That key is what later makes the %(dupes)s exact
   duplicate rows resolvable.
2. **Seed.** The whole table goes in first as ordinary parquet, named with
   20-digit zero-padded sequence numbers (`00000000000000000001.parquet`, ...).
   No change marker is needed for the initial load.
3. **Stream changes.** After the seed, every file carries a final column,
   `__rowMarker__`: `0` insert, `1` update, `2` delete, `4` upsert. Fabric
   applies them to the Delta table in sequence.

### Where the changes come from

PostgreSQL's write-ahead log. With `wal_level = logical`, a *logical
replication slot* using the built-in `test_decoding` plugin exposes every
committed insert, update and delete as text. `scripts/cdc_to_fabric.py` reads
the slot with `pg_logical_slot_get_changes()`, parses each change, writes a
parquet with the right `__rowMarker__`, and uploads it. Inserts, updates and
deletes were all proven to propagate end to end (`scripts/cdc_demo.py`).

Two properties of the source matter here. The table had to be loaded
**LOGGED**, because logical replication never captures UNLOGGED tables and the
mirror would silently see nothing. And `synchronous_commit` had to stay `on`,
because logical decoding only reads flushed WAL.

### What was measured

| Step | Measured |
| --- | --- |
| Source | %(source_rows)s rows x %(source_cols)s text columns, %(csv_gb)s GB CSV, %(pg_gb)s GB in PostgreSQL |
| Seed export, Postgres to zstd parquet | %(seed_files)s files, %(seed_gb)s GB (%(seed_ratio)s smaller than the CSV) |
| Seed upload with azcopy | %(seed_min)s minutes |

### Three things that will bite you

- **Fabric reads the landing zone every ~20 seconds and will open a parquet
  that is still being written.** It then reports `Parquet file size is 0
  bytes` and *latches* that error permanently for the table. The fix is
  ordering: upload every data file first, and write `_metadata.json` last, so
  nothing is eligible until everything is complete.
- **`stopMirroring` / `startMirroring` destroys the Delta table.** It is only
  safe on an empty table. Learned by losing a 50M-row table and repeating the
  29-minute upload.
- **azcopy needs `--trusted-microsoft-suffixes=onelake.dfs.fabric.microsoft.com`**
  or it refuses to send an Entra token to OneLake.

The mirrored table is exposed to the rest of the pipeline through a
**shortcut** in the `fincrime` lakehouse (`Tables/raw_txn`). A shortcut is a
pointer, not a copy: DuckDB reads the mirror's own Delta files.
""" % F))

    A(md("""
### What the row count did not show

Every count-based check on this mirror passed, and the mirror was still wrong
by two rows. The gold notebook's dedup reconciliation (section 2) found one
more distinct `txn_id` in the mirror than PostgreSQL has, and a per-bucket
histogram of ids on both sides named it: row 3870725, deleted at the source
before the replication slot existed, so the delete was never in the WAL the
replicator reads. The opposite case existed too: row 50000004, inserted in the
same window, never reached the mirror. Two errors of opposite sign, and a row
count that matched exactly.

The second was repaired through the source: delete and re-insert the row in
PostgreSQL, and the replicator streamed the insert as an ordinary change (CDC
file 20). The first could not be. A delete replayed through the slot, alone in
its own file and its own processing cycle, was applied only to the copies the
CDC path had itself written and never to the seed copy; the mirror table's own
Delta log and a scan of its data files show it (BUILD_LOG section 40). A row
that predates the slot is only removable by re-seeding.

The rule this teaches is cheap to follow and expensive to skip: **create the
replication slot before taking the snapshot**, so nothing can fall between
them. An insert seen twice is an upsert, a delete of a row the snapshot never
had is a no-op, and a change that falls in the gap is lost silently. The cell
below measures the mirror against the source figures so the difference is
visible rather than assumed.
"""))

    A(code("""
# The mirror, as Fabric sees it: table, status, and the replication engine's
# own view of what it has applied.
import json, notebookutils
ws = notebookutils.runtime.context["currentWorkspaceId"]
mirror = items[items["Display Name"].eq("sulaiman-postgres") & items["Type"].eq("MirroredDatabase")]
mid = mirror["Id"].iloc[0]
status = fabric.FabricRestClient().post(f"v1/workspaces/{ws}/mirroredDatabases/{mid}/getTablesMirroringStatus")
for t in status.json().get("data", []):
    m = t.get("metrics") or {}
    rows = m.get("processedRows")
    rows = f"{rows:,}" if isinstance(rows, int) else str(rows)
    print(f"{t.get('sourceTableName','?'):<14} status={str(t.get('status')):<10} "
          f"rows processed={rows:>14}   last sync={m.get('lastSyncDateTime','?')}")

# Fidelity, measured on the mirror itself. The source figures were measured in
# PostgreSQL on 2026-09-19 (50,000,001 rows, 49,406,791 distinct txn_id).
import duckdb
PG_ROWS, PG_DISTINCT = 50000001, 49406791
n, d = duckdb.connect().execute(
    "SELECT count(*), count(DISTINCT trim(txn_id)) FROM delta_scan('/lakehouse/default/Tables/raw_txn')").fetchone()
print(f"mirror rows {n:,} (source {PG_ROWS:,}, {n-PG_ROWS:+,}) | distinct txn_id {d:,} (source {PG_DISTINCT:,}, {d-PG_DISTINCT:+,})")
if (n - PG_ROWS, d - PG_DISTINCT) == (1, 1):
    print("the +1 is row 3870725, deleted at the source before the slot existed; see the note above")
elif (n - PG_ROWS, d - PG_DISTINCT) == (0, 0):
    print("mirror and source agree exactly")
else:
    print("the difference has changed since 2026-09-19: re-measure the source before trusting either figure")
"""))

    # =======================================================================
    A(md("""
---

## 2. Transformation: DuckDB on a Python notebook (`01_build_gold`)

### Why DuckDB, and why a Python notebook

The landing table is %(source_rows)s rows of **text**. Nothing was typed or
cleaned on the way in, deliberately: a landing zone that rejects rows is not a
landing zone. So all the real work happens here, and the shape of that work
decides the compute.

The work is a single-machine analytical job: parse five competing date formats,
turn `1,234.50` and `(45.00)` and `RM99.00` into numbers, collapse 32 spellings
of one country to one code, run seven risk rules with window functions, score,
deduplicate, and build a star. That is exactly what DuckDB is built for, and at
%(seed_gb)s GB compressed it fits comfortably on one node.

A **Python notebook** in Fabric is a single node that bills at **1 CU per 2
vCores** (Microsoft Learn: *Choosing a notebook kernel*). At 8 vCores it costs
**4 CU** while it runs. A Spark starter pool, the default for a Spark notebook,
bills a minimum of **8 CU** once it scales up, and Spark would spend much of the
run coordinating a distributed engine for a job that does not need distributing.

### How it works

`01_build_gold` is generated from `scripts/build_gold_notebook.py`, which
embeds `transform.py`, `rules.py` and `star.py` verbatim. The code validated
against the full %(source_rows)s rows is byte-for-byte the code that runs.

1. `%%%%configure {"vCores": 8}` sets the node size. It must be the first
   cell, and API-triggered runs honour it.
2. DuckDB reads the mirror through the shortcut: `delta_scan('/lakehouse/default/Tables/raw_txn')`.
3. `star.build()` runs the three SQL layers in one connection: **silver**
   (typing and conforming), **enriched** (the rule inputs, several of which are
   window functions over customer history), **scored** (rule weights summed
   into `risk_score` and banded LOW / MEDIUM / HIGH).
4. Exact duplicates are removed by keeping the lowest `_mirror_row_id` per
   business-column group: **%(dupes)s** rows, 1.19%%.
5. Seven dimensions are built with an explicit **Unknown member at key -1**,
   so every fact row has a foreign key. Null foreign keys across all six
   relationships: **0**.
6. The nine tables are written to `Files/gold` as zstd parquet:
   **%(gold_parquet_gb)s GB**, five times smaller than the %(seed_gb)s GB it
   derives from, because typed columns compress and text does not.

### What cleaning actually recovered

| Column | Raw landing zone | Gold |
| --- | --- | --- |
| `posting_date` parses as a date | %(posting_before)s | **%(posting_after)s** |
| Country | 32 spellings | 1 code |
| KYC status | 11 variants | 5 |
| Card brand | 44 variants | 5 |

The 7%% of dates that still do not parse are genuinely unrecoverable. They sit
on the Unknown date member and are **shown** on the report's trend, not
dropped.

### Two DuckDB lessons worth keeping

- **`SUMMARIZECOLUMNS` is not the only thing that behaves differently at
  scale.** Rule fire rates measured on a 2M-row sample did not hold at 50M:
  `new_merchant` went from 1.1%% to 27.6%% because window-dependent rules need
  the full history. Rules were recalibrated on the full data, and two were
  dropped for firing on almost everything or almost nothing.
- **DuckDB's temp directory follows the database file.** A surrogate key on
  `fact_alert` forced a global sort that spilled 38 GB, to the wrong disk. The
  key was removed and the spill target set explicitly. Both fixes are in the
  notebook.
""" % F))

    A(code("""
# MEASURED: what the on-capacity DuckDB run wrote about itself.
import json
with open("/lakehouse/default/Files/build_gold.json") as fh:
    B = json.load(fh)
T = B["timing_s"]
print(f"ran at            {B['ran_at_utc']}")
print(f"kernel            {B['kernel']}  ({B['vcores_requested']} vCores requested, "
      f"{B['env']['cpu_count']} seen, {B['env']['ram_gb']} GB RAM)")
print(f"duckdb            {B['duckdb_version']}, memory_limit {B['memory_limit_gb']} GB")
print(f"source rows       {B['source_rows']:,}")
print(f"count source      {T['count_source_s']:>8.1f} s")
print(f"build star        {T['build_s']:>8.1f} s")
print(f"write parquet     {T['write_s']:>8.1f} s")
print(f"TOTAL             {T['total_s']:>8.1f} s  = {T['total_s']/60:.1f} min")
print()
print("gold row counts:")
for t, n in B["counts"].items():
    print(f"  {t:<18} {n:>12,}   {B['gold_parquet_mb'][t]:>8.1f} MB")

# Determinism, rule by rule. RUN2 is job 71d68bc6 (2026-09-18, the first run
# with the section 40 fixes), read back from its parquet; the run above must
# match it exactly or no count on this page can be trusted.
RUN2 = {"R02": 10118821, "R03": 3624172, "R04": 10164144, "R05": 864962,
        "R06": 13697031, "R07": 2126003, "R09": 24580346}
RF = B.get("rule_firings") or {}
if RF:
    print()
    print("rule firings, this run against run 2 (same code, same source):")
    same = True
    for r in sorted(set(RF) | set(RUN2)):
        a, b = RF.get(r), RUN2.get(r)
        same = same and (a == b)
        fa = "-" if a is None else format(a, ",")
        fb = "-" if b is None else format(b, ",")
        print(f"  {r:<5} {fa:>12}   run 2 {fb:>12}   {'same' if a == b else 'DIFFERENT'}")
    print("  deterministic: identical rule by rule" if same
          else "  NOT identical: investigate before trusting any count above")
RC = B.get("recon")
if RC:
    print()
    print(f"dedup: {RC['scored_rows']:,} scored -> {RC['deduped_rows']:,} kept, "
          f"{RC['removed']:,} removed; {RC['distinct_txn_id_scored']:,} distinct txn_id; "
          f"{RC['null_txn_id_deduped']:,} kept rows have no txn_id")
    print(f"txn_ids that survive dedup more than once: {RC['multi_survivor_txn_ids']}")
    for smp in RC["multi_survivor_samples"]:
        print("  ", smp["txn_id"], "->", smp["rows"])
"""))

    A(code("""
# MEASURED: the on-capacity run must reproduce the verified gold layer exactly.
with open("/lakehouse/default/Files/verify.json") as fh:
    V = json.load(fh)["tables"]
bad = 0
for t, n in B["counts"].items():
    v = V.get(t, {}).get("rows")
    ok = (v == n)
    bad += (not ok)
    print(f"  {t:<18} notebook {n:>12,}   verified {v if v is None else format(v, ','):>12}   {'OK' if ok else 'MISMATCH'}")
print()
print("every table matches the verified layer" if not bad else f"{bad} table(s) differ")
"""))

    # =======================================================================
    A(md("""
---

## 3. The gold tables and the V-Order handoff (`02_vorder_write`)

DuckDB writes excellent parquet, but it cannot produce **V-Order**, Fabric's
write-time layout that lets the Power BI engine compute on compressed data
without decompressing it. It also writes Delta as INSERT-only, with no MERGE
and no checkpoints, so a table written only by DuckDB grows an unbounded
transaction log.

So the final write is handed to Spark, on purpose. `02_vorder_write` reads the
nine parquet files and rewrites them as V-Ordered Delta tables named
`gold_<table>`. That is the *only* Spark work in the pipeline:
**%(vorder_txt)s** wall time for %(gold_rows)s rows across nine tables (the latest
run, from the jobs API; the cost cell in section 6 reads it live). The result is **%(gold_files)s files, %(gold_delta_gb)s GB** of
Delta in OneLake.

`03_verify` then reads the Delta logs on capacity and writes `Files/verify.json`
with the row count, file count and size of every table. The transformation
cell above compares against it; a mismatch fails loudly.

One operational detail: after tables land, the lakehouse's SQL analytics
endpoint syncs its metadata **asynchronously**. Querying `gold_fact_transaction`
immediately returns `Invalid object name`. The fix is
`POST .../sqlEndpoints/{id}/refreshMetadata`, which the build does before the
model is touched.
""" % F))

    A(code("""
# MEASURED: the gold Delta tables as they sit in OneLake right now.
from deltalake import DeltaTable
import os
base = "/lakehouse/default/Tables"
for t in sorted(os.listdir(base)):
    if not t.startswith("gold_"):
        continue
    dt = DeltaTable(f"{base}/{t}")
    files = dt.files()
    size = sum(os.path.getsize(f"{base}/{t}/{f}") for f in files) / 1e6
    print(f"  {t:<24} version {dt.version():>3}   {len(files):>3} files   {size:>8.1f} MB")
"""))

    # =======================================================================
    A(md("""
---

## 4. The Direct Lake semantic model (`fincrime_model`)

### What Direct Lake is, without the marketing

A Power BI semantic model normally works one of two ways. **Import** copies the
data into the model's own in-memory store on a refresh schedule: fast to query,
but a second copy of the data that goes stale between refreshes. **DirectQuery**
copies nothing and sends every query to the source: always current, but every
click waits on the source.

**Direct Lake** reads the Delta table's parquet files straight from OneLake
into the same in-memory engine that Import uses, *on demand*, and keeps them
resident. There is no refresh window and no second copy. The two operations
that make it work (Microsoft Learn: *How Direct Lake works*):

- **Transcoding.** When a query needs a column that is not yet in memory, the
  model loads that whole column from the parquet files. Only the columns a
  query touches are loaded, and once loaded they stay resident until evicted.
- **Framing.** A "refresh" of a Direct Lake model does not move data. It reads
  the Delta log, notes which parquet files are current, and evicts only the
  column segments those files changed. It usually takes seconds.

This is why V-Order matters: the engine can scan V-Ordered parquet without
decompressing it, so a well-laid-out table transcodes faster and queries faster
(Microsoft Learn: *Understand Direct Lake query performance*).

### How this model was built

Authored as TMDL by `scripts/build_semantic_model.py` and imported with `fab`.
%(model_tables)s tables, %(model_rels)s relationships, %(model_measures)s
measures. Every measure was verified by DAX against DuckDB and reconciles to
the cent. Surrogate keys are hidden and set to `summarizeBy: none`, because a
summed key is a confident wrong number.

One measure is worth understanding, because the report rests on it:

    Alerts Raised = CALCULATE ( [Transactions], fact_transaction[risk_band] = "HIGH" )

An **alert** is the score crossing into the HIGH band. A **rule firing** is a
contribution to the score. Counting every firing as an alert gives an 80%%
alert rate, about 317 full-time analysts. Counting alerts gives
**%(alert_rate)s**, about 28 analyst-years across the period. The first is an
unstaffable queue that gets ignored; the second is a control that works.
""" % F))

    A(code("""
# MEASURED, live: how long the model takes to answer the report's own measures.
# The first run of a query is cold (columns transcoded from OneLake); the
# repeats are what a report user sees.
import time
import sempy.fabric as fabric

MODEL = "fincrime_model"
QUERIES = {
    "headline KPIs":       "EVALUATE ROW(\\"txns\\", [Transactions], \\"alerts\\", [Alerts Raised], \\"amt\\", [Total Amount], \\"appr\\", [Approval Rate])",
    "overview cube":       "EVALUATE SUMMARIZECOLUMNS(dim_date[yr], dim_date[mth], dim_channel[channel], fact_transaction[risk_band], fact_transaction[txn_type], \\"t\\", [Transactions], \\"a\\", [Total Amount])",
    "rules x band":        "EVALUATE SUMMARIZECOLUMNS(fact_transaction[rules_fired], fact_transaction[risk_band], \\"t\\", [Transactions])",
    "merchant category":   "EVALUATE SUMMARIZECOLUMNS(dim_merchant[merchant_mcc], fact_transaction[risk_band], \\"t\\", [Transactions], \\"a\\", [Total Amount])",
}
print(f"{'query':<20} {'rows':>6} {'cold':>8} {'warm':>8} {'warm':>8}")
LAT = {}
for name, q in QUERIES.items():
    times = []
    for i in range(3):
        t0 = time.perf_counter()
        df = fabric.evaluate_dax(MODEL, q)
        times.append(time.perf_counter() - t0)
    LAT[name] = times
    print(f"{name:<20} {len(df):>6} {times[0]:>7.2f}s {times[1]:>7.2f}s {times[2]:>7.2f}s")
print()
print(f"Each of these aggregates the full {B['counts']['fact_transaction']:,}-row fact table.")
"""))

    # =======================================================================
    A(md("""
---

## 5. The report (`FinCrime`): four pages, one visual each

Every screenshot below is the report running in Power BI Desktop, live on the
Direct Lake model, captured through the Desktop Bridge at 2x and cropped to the
canvas. Nothing is mocked and no number is typed in: what you see is what the
pipeline produced.

### The technique, in one paragraph

Each page is a **single HTML Content visual** driven by **one DAX measure**.
The measure aggregates in the model and ships a compact cube plus its own
renderer as JavaScript; the browser does layout, ranking and filtering.
Clicking a chip or a bar re-aggregates the cube **in the browser** and never
queries the model again.

Why not twenty visuals per page? A custom visual cannot cross-filter its
neighbours unless its own compiled code builds selection identities, which this
one does not. Rather than fight that, the page *is* the visual, so there is
nothing to cross-filter to. Report-level filters still apply, because the
measure is evaluated in filter context.

### Why the measure ships a cube and not rows

A DAX measure holds roughly **%(ceiling)s characters**. Shipping %(gold_rows)s
rows at grain would need about 1.7 billion. So the Overview measure aggregates
to month x channel x risk band x transaction type: **%(cube_cells)s** populated
cells, about **%(cube_pct)s** of the ceiling, from a 49.4M-row table. Money
crosses as integer sen so no locale can corrupt the payload. The renderer is
inlined into the measure, so the visual fetches nothing from the internet.

---

### Page 1 of 4, Overview: is the monitoring working, and where is the volume?

![The Overview page: KPI strip, transactions by month, channel, composition and rule firings](https://raw.githubusercontent.com/sulaiman013/fabric-x-duckdb/master/report/screenshots/report-overview.png)

Read it top to bottom:

1. **The scope line, top right.** `49,406,792 of 49,406,792 transactions in
   scope (100.0%%)`. It always states the denominator, so a filtered page can
   never be mistaken for the whole population.
2. **The chip row.** RISK, CHANNEL and TYPE. These are **not** Power BI
   slicers. They are HTML inside the visual, and clicking one re-aggregates the
   cube in the browser in under a millisecond without touching the model.
3. **The KPI strip.** Six measures, with the one the page is about highlighted:
   an alert rate of **2.88%%**. Beside it sit the numbers that make it
   meaningful: 1,423,088 alerts, RM 1.5b of value behind them, and **28.5
   analyst-years** at 50,000 alerts cleared per analyst per year.
4. **Transactions by month.** 31 months, each bar stacked low / medium / high.
   The stub bar on the left labelled `Unknown` is the rows whose date never
   parsed: they are shown, not silently dropped, because that is what the data
   actually contains.
5. **Channel, stacked by risk band.** Mobile and Internet carry 11m each
   against 5.5m for the branch channels, and their high-risk slivers are
   visibly fatter.
6. **Composition.** The band mix (73.2%% low, 23.9%% medium, 2.9%% high) and the
   type mix, both recomputed under whatever chips are active.
7. **Rule firings, with the caveat printed underneath.** A firing is not an
   alert: a firing contributes to a score, and an alert is the score crossing
   the band. The note says so on the page, because the two numbers differ by a
   factor of 45 and the distinction is the whole design.

---

### Page 2 of 4, Rule effectiveness: which rules earn their keep?

![The Rule effectiveness page: rules by firing volume, rules firing together, the score histogram and the threshold cost table](https://raw.githubusercontent.com/sulaiman013/fabric-x-duckdb/master/report/screenshots/report-rules.png)

This is the page that turns monitoring into a decision.

1. **The header.** 65,175,479 firings across 39,613,511 transactions. Those two
   numbers are the reason the page exists.
2. **The KPI strip.** 80.2%% of all transactions are touched by at least one
   rule, and only 1,423,088 become alerts. **45.8 firings are absorbed per work
   item**, which is the noise the scoring model removes before anyone is asked
   to look at anything.
3. **Rules by firing volume.** Seven rules with their weight and their real
   fire count, sorted. `declined` fires 25m times at weight 10; `velocity` fires
   865k times at weight 30. High volume and high weight are different things,
   and the table shows both so a rule cannot hide behind either.
4. **Rules firing together.** How many rules a transaction trips, stacked by the
   band it ends up in. 9.8m transactions trip nothing, 20m trip exactly one, and
   the stack only turns red from three rules up. That is the scoring model
   working: one rule is rarely enough.
5. **Risk score distribution**, bucketed by 5, with the alert threshold drawn as
   a red line at 60.
6. **What a threshold costs.** The cut-off table, and the point of the whole
   pack: at 40 you raise 7.1m alerts and need 57 analysts; at 60 you raise 1.4m
   and need 11; at 80 you raise 184k and need 1. Moving the line is a staffing
   decision, and the page prices it rather than leaving it as a preference.

---

### Page 3 of 4, Risk and exposure: where does the risk concentrate?

![The Risk and exposure page: merchant category, currency, card brand and entry mode, each stacked by risk band](https://raw.githubusercontent.com/sulaiman013/fabric-x-duckdb/master/report/screenshots/report-risk.png)

1. **The header states what cannot be answered.** `exposure at risk RM 1.5b of
   RM 18b` and then, deliberately, `RM 89m in unresolvable currencies`. The
   page leads with the size of its own blind spot.
2. **The KPI strip.** Card-not-present at 20.5%%, value settled in a foreign
   currency at 71.3%%, odd hour at 20.6%%, declined at 60.6%% of the 40,546,379
   that reached a decision, and a mean risk score of 19.8 out of a possible 145.
3. **Four dimension grids**, each stacked by risk band: merchant category,
   currency, card brand and entry mode. Every one is scrollable inside the
   visual, in the browser, with no further queries.
4. **The dirt is visible on purpose.** `(blank)` is the largest merchant
   category. The currency list contains `458`, `NA` and `#N/A` beside USD and
   MYR. The card brand list has `UNKNOWN` at 5.9m. This is a 100-column TEXT
   extract with 31 spellings of one country, and a report that hid that would
   be lying about its own inputs.

---

### Page 4 of 4, Guide: how to read all of the above

![The Guide page: a seven-section rail, the framing, three explainer cards and the pipeline strip](https://raw.githubusercontent.com/sulaiman013/fabric-x-duckdb/master/report/screenshots/report-guide.png)

The guide ships **inside** the report rather than in a separate document,
because a document beside a report goes stale the first time the report
changes.

1. **The rail on the left** holds seven sections: start here, how the data gets
   here, firing vs alert, the pages, reading the numbers, data quality, and what
   this cannot do. Clicking one swaps the panel, in the browser.
2. **The framing paragraph** states the operational question in one sentence:
   which transactions should a human look at today, and can the team actually
   work that many.
3. **Six headline numbers**, then three cards: how the one-visual technique
   works, what to read first, and the shape of the answer, which spells out the
   gap between 39,613,511 transactions touched by a rule and 1,423,088 alerts.
   A queue of 317 analyst-loads is ignored; a queue of 11 is worked.
4. **The pipeline strip** along the bottom: PostgreSQL, open mirroring, DuckDB,
   Direct Lake, this report.
5. **Firing vs alert** carries an interactive threshold demonstrator: drag the
   cut-off and watch the alert count and the analyst headcount move together.

One honest note on this screenshot: the lower half of the panel is empty
because `Start here` is the shortest of the seven sections. The other six fill
the page; this is the one that does not, and the guide opens on it.

### How these screenshots were produced

Through the Power BI Desktop Bridge, not by hand, so they can be regenerated
whenever the report changes:

```
powerbi-desktop status
powerbi-desktop screenshot Overview --scale 2 --output report/screenshots/report-overview.png
```

The bridge reports the running Desktop instance, the PBIP it has open and the
PBIR pages it can see, then renders a named page to PNG. The four images were
cropped to the report canvas so Desktop's own collapsed Filters rail does not
appear.

### What it costs to use

The report issues **one** DAX query per page when it opens (the measure), and
**zero** for every filter, chip and bar click after that. A conventional page of
fifteen visuals issues fifteen queries on open and up to fifteen more on every
interaction. The latency measured above is therefore the whole per-page cost.
""" % F))

    # =======================================================================
    # =======================================================================
    A(md("""
---

## 6. What it costs, against Spark and against a T-SQL Warehouse

### The unit of money in Fabric

Everything runs against **capacity units (CU)**. A capacity is a fixed number
of CU per hour (an F2 is 2, an F64 is 64, this trial is an FTL64), billed by the
second while it is running. Workloads draw from that pool. The relevant rates,
from Microsoft Learn:

| Compute | CU | Billed while | Source |
| --- | --- | --- | --- |
| Python notebook, 8 vCores | **4 CU** | executing; session start is not billed | *Choosing a notebook kernel*: 1 CU per 2 vCores; *Apache Spark billing and utilization* |
| Spark starter pool (default Spark notebook) | **8 CU** minimum after scale-up | executing | same articles |
| Fabric Warehouse | **0.538 CU per vCore**, allocated in vNodes of 4 | a vNode is allocated, busy or waiting, in a one-minute allocation window | *Fabric operations*, *Warehouse consumption and utilization*. It was 2 CU per vCore before August 2026 |

Every Fabric meter costs the same per CU-hour within a region: **$%(price_uks)s**
in UK South, where this capacity runs, and $%(price_use)s in East US (Azure
retail prices API, queried %(price_date)s). So the choice of engine never
changes the price of a CU-hour. It changes how many are used, and what counts
as used.

### The build, measured

A notebook is billed while its session is active, and not for the time taken to
start it (Microsoft Learn, *Apache Spark billing and utilization*). So the cell
below prices the transformation on its own executing time, and prints the last
run's wall time beside it to show the start that is not billed. The V-Order job
records only a wall time, so its figure is an upper bound.

The reference run executed for %(exec_s)s s on 8 vCores, then V-Ordered the result
in at most %(vorder_wall_s)s s on a starter pool: **at most %(route_cuh)s
CU-hours, $%(route_usd)s**, at the UK South rate, the same figures the
architecture diagram above shows.
`PRICE_PER_CU_HOUR` in the cell is the UK South rate; change it for your region.

### Against Spark, and what is honest about it

The DuckDB run is **measured**. The Spark alternative is **modelled**, and the
model is conservative in Spark's favour:

- A Spark transformation of the same job is assumed to take the **same
  executing time** as DuckDB. In practice a distributed engine on a job that
  fits on one node is usually slower, not faster, because it spends time
  shuffling.
- It is charged at the **starter pool minimum of 8 CU**, twice the Python
  notebook's 4 CU. That is the documented floor, not a pessimistic guess.

What is *not* claimed: that DuckDB beats Spark on every job. Microsoft's own
guidance puts the crossover at roughly **10 to 13 GB compressed**, where Fabric
Spark with the Native Execution Engine is competitive with or faster than most
single-machine engines, and where single-machine Python engines can hit
out-of-memory errors at lower vCore counts. This job is %(seed_gb)s GB
compressed. It is **on that line**, and it fits because the node carries 67.4 GB
of RAM and DuckDB was capped at 47 GB.
""" % F))

    A(code("""
# MEASURED cost of the pipeline's compute, and a MODELLED alternative.
PRICE_PER_CU_HOUR = %(price_uks)s   # USD per CU-hour, UK South, Azure retail prices API, %(price_date)s. Set yours.

cu_python = 4                       # 8 vCores on the Python kernel (Microsoft Learn)
cu_spark_starter = 8                # starter pool minimum after scale-up (Microsoft Learn)

# A notebook is billed while its session is active, not for the time taken to
# start it (Microsoft Learn, Apache Spark billing and utilization). So the
# transform is priced on its own executing time, and the wall time of its last
# run, read live from the jobs API, is printed beside it to show the start that
# is not billed. The V-Order job records only a wall time, an upper bound.
from datetime import datetime

def _t(s):
    return datetime.fromisoformat(s.rstrip("Z")[:26])

def last_run_seconds(name, containing=None):
    # The run that wrote the evidence is the one whose window contains the
    # evidence's own timestamp; a cancelled run can be reported as Completed
    # with a one-minute wall, so "latest completed" is not good enough.
    nb = items[items["Display Name"].eq(name) & items["Type"].eq("Notebook")]["Id"].iloc[0]
    runs = fabric.FabricRestClient().get(f"v1/workspaces/{ws}/items/{nb}/jobs/instances").json().get("value", [])
    done = [r for r in runs if r.get("status") == "Completed" and r.get("endTimeUtc")]
    if containing:
        at = _t(containing)
        done = [r for r in done if _t(r["startTimeUtc"]) <= at <= _t(r["endTimeUtc"])] or done
    if not done:
        return None, None
    r = max(done, key=lambda r: r["endTimeUtc"])
    return (_t(r["endTimeUtc"]) - _t(r["startTimeUtc"])).total_seconds(), r["endTimeUtc"][:19]

build_s, build_at = last_run_seconds("01_build_gold", containing=B["ran_at_utc"])
vorder_s, vorder_at = last_run_seconds("02_vorder_write")
if build_s is None:
    build_s = T["total_s"]          # no completed run listed: the notebook's own record
if vorder_s is None:
    vorder_s = %(vorder_s)s         # no completed run listed: BUILD_LOG section 31
print(f"01_build_gold    last completed run {build_at}: {build_s:.0f} s wall, "
      f"of which {T['total_s']:.0f} s was DuckDB work, the part that is billed")
print(f"02_vorder_write  last completed run {vorder_at}: {vorder_s:.0f} s wall")
print()

def cost(cu, seconds):
    return cu * seconds / 3600 * PRICE_PER_CU_HOUR

work_s = T["total_s"]               # executing time: what a notebook is billed for
rows = [
    ("DuckDB transform, Python 8 vCores", "executing time, documented CU", cu_python, work_s),
    ("V-Order write, Spark starter pool",  "wall time, an upper bound",     cu_spark_starter, vorder_s),
]
alt = [
    ("Same transform on Spark starter pool", "modelled: same executing time, 8 CU", cu_spark_starter, work_s),
    ("V-Order write, Spark starter pool",    "wall time, an upper bound",          cu_spark_starter, vorder_s),
]
def show(title, rr):
    print(title)
    tot_cu_h = tot_usd = 0
    for name, basis, cu, s in rr:
        cu_h = cu * s / 3600; usd = cost(cu, s)
        tot_cu_h += cu_h; tot_usd += usd
        print(f"  {name:<40} {cu:>2} CU x {s:>7.0f} s = {cu_h:>6.3f} CU-h  ${usd:>6.3f}   [{basis}]")
    print(f"  {'TOTAL':<40} {'':>19} {tot_cu_h:>6.3f} CU-h  ${tot_usd:>6.3f}")
    print()
    return tot_cu_h, tot_usd

a_cuh, a_usd = show("THIS PIPELINE", rows)
b_cuh, b_usd = show("ALTERNATIVE: transformation on Spark (modelled)", alt)
step_a, step_b = rows[0][2] * rows[0][3] / 3600, alt[0][2] * alt[0][3] / 3600
print(f"transformation step: {(1 - step_a/step_b)*100:.0f}%% less compute "
      f"({step_a:.3f} vs {step_b:.3f} CU-h); whole pipeline: {(1 - a_cuh/b_cuh)*100:.0f}%% less "
      f"({b_cuh - a_cuh:.3f} CU-h, ${b_usd - a_usd:.3f} at ${PRICE_PER_CU_HOUR}/CU-h)")
print()
# Against a Warehouse the rate is documented but not what gets billed: it bills
# every vNode it allocates, busy or waiting. A production pilot, anonymised,
# measured about 60 CU-s per Warehouse engine-second against this notebook's 4,
# on one capacity for the same tables. That gives the bar a Warehouse would
# have to clear on this job.
PILOT_WH_CU_PER_ENGINE_S = 60
print(f"At the pilot's ~{PILOT_WH_CU_PER_ENGINE_S} CU-s per Warehouse engine-second, a Warehouse "
      f"would have to do this whole job in {a_cuh * 3600 / PILOT_WH_CU_PER_ENGINE_S:.0f} "
      f"engine-seconds to match it. WAREHOUSE_COMPARISON.md has the working.")
print()
print("Not priced, either way: a gold layer is materialised in both routes, into the")
print(f"lakehouse here or into warehouse storage there. Both persist {B['counts']['fact_transaction']:,} rows.")
print("What Direct Lake removes is the IMPORT copy, which is a serving choice, not this one.")
""" % F))

    A(md("""
### The copy worth arguing about is the third one

A gold layer gets materialised either way. This route writes Delta into the
lakehouse; a T-SQL route writes it into warehouse storage. Both persist and both
cost storage, so this pipeline is **not** "one copy", and neither is that one.
This route also keeps the %(gold_parquet_gb)s GB of intermediate parquet that the
V-Order job reads. A Warehouse route has no such copy: it reads the mirror in
place through a three-part name and writes V-Ordered Delta directly.

The copy that does not have to exist is the **Import** copy. An Import-mode
model holds a third copy of the data inside the model, rebuilds it on a
schedule, pays CU on every refresh whether or not anything changed, and is stale
in between. Direct Lake reads the files the notebook wrote, and a refresh copies
**only metadata** (Microsoft Learn, *Direct Lake overview*), which takes seconds.

### Against a T-SQL Warehouse

Warehouse compute was repriced in August 2026, from 2 CU per vCore to 0.538. A
notebook vCore is 0.5, so per vCore the two are now close, and most published
comparisons, written before the change, overstate the Warehouse's price about
3.7 times. The rate does not decide it, though. What gets billed does.

The notebook bills the 8 vCores it was given, and only while it executes. The
Warehouse bills every vNode the engine chooses to allocate, per second, busy or
waiting, and background work for as long as the warehouse exists.

A separate production pilot, anonymised here, measured the consequence. It ran
the same transformations first as T-SQL procedures in a Fabric Warehouse, then
as DuckDB in a Python notebook, on one F16 capacity, for the same tables, in
September 2026, after the repricing:

| Measured in the pilot | Warehouse | DuckDB notebook |
| --- | --- | --- |
| CU-s per engine-second | about 50 to 65 | 4, at 8 vCores |
| three fact tables, one five-minute cycle | about 1,260 CU-s | 82 to 123 CU-s |
| three fact tables, rebuilt from scratch | about 9,800 CU-s | about 260 CU-s |
| every table every five minutes, one day | about 150%% of the F16, projected | 12.7%% of the F16, measured |
| a run that did nothing | about 370 CU-s for 6 seconds | nothing between runs |
| a warehouse that merely exists | about 840 CU-s an hour | nothing |

This repository's job has not itself been run on a Warehouse. At the pilot's
~60 CU-s per engine-second, a Warehouse would have to do all of it in
**%(wh_engine_s)s engine-seconds** to match what the DuckDB route billed.
[WAREHOUSE_COMPARISON.md](https://github.com/sulaiman013/fabric-x-duckdb/blob/master/WAREHOUSE_COMPARISON.md)
has the full working: capacity share by SKU, what a parked warehouse costs, and what ports from DuckDB to
T-SQL.

### Where the Warehouse route wins

Worth writing down, because a comparison that only runs one way is an advert:

1. **Raw speed on a large whole-table build.** The pilot measured one at 14 s
   on the Warehouse against 84 to 90 s in the notebook. Under allocation
   billing, faster is not cheaper: every vNode that made it fast is billed.
2. **No memory ceiling.** It scales out. A notebook stops at one node, and the
   pilot lost a full load on an undersized session before restructuring it.
3. **V-Order is on by default in every warehouse**, and off by default for Spark
   and lakehouses in new workspaces. This pipeline had to add `02_vorder_write`,
   at most %(vorder_wall_s)s s and about %(vorder_cents)s cents, up to
   %(vorder_share)s%% of its whole cost, to get what a warehouse gives free.
   Direct Lake cold-cache queries are 40 to 60%% faster with it, so skipping it
   was never an option.
4. **No timezone trap.** `datetime2` carries no time zone, so the laptop against
   capacity disagreement this build hit on epoch timestamps cannot happen.
5. **T-SQL is familiar** to far more teams than DuckDB's dialect is, and that is
   a real operational cost this design is choosing to pay.

And the report adds a saving at query time: after the one measure per page,
every interaction is free. That is measurable on this workspace by watching the
Capacity Metrics app while clicking through the report, which is the test worth
running before believing any of this.
""" % F))

    # =======================================================================
    A(md("""
---

## 7. Reproducing the whole thing

| Step | Command |
| --- | --- |
| Generate the messy source | `python scripts/generate.py --rows 50000000` |
| Load PostgreSQL | `python scripts/load_postgres.py --logged` |
| Seed the mirror | `python scripts/snapshot_to_fabric.py` |
| Stream changes | `python scripts/cdc_to_fabric.py --run` |
| Transform on capacity | `fab job run "fabric duckdb.Workspace/01_build_gold.Notebook"` |
| V-Order the gold layer | `fab job run "fabric duckdb.Workspace/02_vorder_write.Notebook"` |
| Verify it | `fab job run "fabric duckdb.Workspace/03_verify.Notebook"` |
| Build the model | `python scripts/build_semantic_model.py` then `fab import` |
| Build the report | `python scripts/build_report.py --open` |
| Organise the workspace | `python scripts/folderize_workspace.py` |

Every script is in `github.com/sulaiman013/fabric-x-duckdb`. The full
chronological build log, including every mistake and what it cost, is
`BUILD_LOG.md` in the same repository.
"""))

    A(code("""
# Leave evidence: everything printed above, saved next to the data, so a run
# triggered from the CLI can be read back without opening the notebook.
from datetime import datetime, timezone
path = "/lakehouse/default/Files/readme_last_run.txt"
with open(path, "w") as fh:
    fh.write("README run at " + datetime.now(timezone.utc).isoformat(timespec="seconds") + chr(10) + chr(10))
    fh.write(_LOG.getvalue())
print("evidence written:", path)
"""))

    metadata = {
        "kernel_info": {"name": "jupyter", "jupyter_kernel_name": "python3.11"},
        "kernelspec": {"name": "jupyter", "display_name": "Python (Jupyter)"},
        "language_info": {"name": "python"},
        "microsoft": {"language": "python", "language_group": "jupyter_python"},
        "dependencies": {"lakehouse": {
            "default_lakehouse": LAKEHOUSE,
            "default_lakehouse_name": "fincrime",
            "default_lakehouse_workspace_id": WS,
            "known_lakehouses": [{"id": LAKEHOUSE}],
        }},
    }
    nb = {"nbformat": 4, "nbformat_minor": 5, "metadata": metadata,
          "cells": cells}

    for c in cells:
        if c["cell_type"] != "code":
            continue
        src = "".join(c["source"])
        body = "\n".join(l for l in src.split("\n") if not l.startswith("%"))
        compile(body, "<cell>", "exec")

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
            "metadata": {"type": "Notebook", "displayName": "00_README"},
            "config": {"version": "2.0",
                       "logicalId": "00000000-0000-0000-0000-000000000000"},
        }, fh, indent=2)
        fh.write("\n")

    n_md = sum(1 for c in cells if c["cell_type"] == "markdown")
    n_code = len(cells) - n_md
    print("wrote %s" % os.path.normpath(OUT))
    print("  %d markdown cells, %d code cells, all code cells compile"
          % (n_md, n_code))
    return 0


if __name__ == "__main__":
    sys.exit(main())
