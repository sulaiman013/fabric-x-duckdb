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
    "gold_rows": "49,406,790",
    "dupes": "593,210",
    "gold_parquet_gb": "1.86",
    "gold_delta_gb": "2.5",
    "gold_files": "79",
    "vorder_s": "202",
    "vorder_txt": "3 min 22 s",
    "model_tables": "9",
    "model_rels": "8",
    "model_measures": "17",
    "cube_cells": "2,508",
    "cube_pct": "4%",
    "ceiling": "2,100,000",
    "alerts": "1,408,756",
    "alert_rate": "2.85%",
    "firings": "65,088,689",
    "customers": "5,112,692",
    "posting_before": "47.5%",
    "posting_after": "93.0%",
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
| 04 Application | `fincrime_ops` | SQL database | Read-write store for analyst decisions |
| 04 Application | `fincrime_fn` | User data functions | Write-back functions the report's operational surfaces call |
| 04 Application | `04_ops_ddl` | Spark notebook | Creates the `ops` tables in `fincrime_ops` |
| Deprecated | `stage_lh` | Lakehouse | Empty. Created while investigating uploads, superseded |

The SQL analytics endpoints you see next to the lakehouses and databases are
created automatically with their parent and are not separate work.
""" % F))

    A(code("""
# Live inventory, so this table can never go stale.
%pip install -q semantic-link
import sempy.fabric as fabric
items = fabric.list_items()
display(items[["Display Name", "Type", "Id"]].sort_values(["Type", "Display Name"]))
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
**%(vorder_txt)s** for %(gold_rows)s rows across nine tables (measured, BUILD_LOG
section 31). The result is **%(gold_files)s files, %(gold_delta_gb)s GB** of
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

### The technique

Each page is a **single HTML Content visual** driven by **one DAX measure**.
The measure aggregates in the model and ships a compact cube as JavaScript;
the browser does layout, ranking and filtering. Clicking a chip or a bar
re-aggregates the cube **in the browser** and never queries the model again.

Why not twenty visuals per page? A custom visual cannot cross-filter its
neighbours unless its own compiled code implements selection, which this one
does not. Rather than fight that, the page *is* the visual, so there is nothing
to cross-filter to. Report-level filters still apply, because the measure is
evaluated in filter context.

### Why the measure ships a cube and not rows

A DAX measure holds roughly **%(ceiling)s characters**. Shipping %(gold_rows)s
rows at grain would need about 1.7 billion. So the Overview measure aggregates
to month x channel x risk band x transaction type: **%(cube_cells)s** populated
cells, about **%(cube_pct)s** of the ceiling, from a 49.4M-row table. Money
crosses as integer sen so no locale can corrupt the payload. The renderer is
inlined into the measure, so the visual fetches nothing from the internet.

### The pages

| Page | Answers | Ships |
| --- | --- | --- |
| Overview | Alert volume and value over time, by channel, band and type | month x channel x band x type |
| Rule effectiveness | What fires, how rules overlap, what a threshold costs in analysts | rules, rules-fired x band, score histogram |
| Risk and exposure | Merchant category, currency, card brand, entry mode, by band | four dimension x band grids |
| Guide | How to read all of the above, with a live threshold demonstrator | the score histogram |

### What it costs to use

The report issues **one** DAX query per page when it opens (the measure), and
**zero** for every filter, chip and bar click after that. A conventional page
of fifteen visuals issues fifteen queries on open and up to fifteen more on
every interaction. The latency cell above is the whole per-page cost.
""" % F))

    # =======================================================================
    A(md("""
---

## 6. Write-back: `fincrime_ops`, `fincrime_fn`, `04_ops_ddl`

A mirrored database is **read-only**, and the gold tables are derived. So the
report's operational surfaces (alert triage, case management, KYC actions) need
somewhere to *write*. That is `fincrime_ops`, a Fabric SQL database with five
`ops.*` tables created by `04_ops_ddl`, and `fincrime_fn`, five user data
functions the report calls: `disposition_alert`, `assign_item`, `advance_case`,
`record_kyc_action`, `ops_health`.

The part worth showing: a Fabric SQL database **mirrors itself to OneLake as
Delta automatically**, with no configuration. An analyst decision written
through a function lands in `fincrime_ops/Tables/ops/alert_disposition` as
parquet, where the next gold rebuild can join it to `fact_transaction` on
`_mirror_row_id`. This was proven end to end: write through the function, read
the row back from OneLake with DuckDB. That closes the loop most pipelines leave
open.
"""))

    A(code("""
# MEASURED: the write-back store's own mirror, as it sits in OneLake.
opsdb = items[items["Display Name"].eq("fincrime_ops") & items["Type"].eq("SQLDatabase")]["Id"].iloc[0]
resp = fabric.FabricRestClient().get(f"v1/workspaces/{ws}/items/{opsdb}")
print("fincrime_ops:", resp.json().get("displayName"), "|", resp.json().get("type"))
try:
    import notebookutils
    paths = notebookutils.fs.ls(f"abfss://{ws}@onelake.dfs.fabric.microsoft.com/{opsdb}/Tables/ops")
    for p in paths:
        print("  mirrored Delta table:", p.name)
except Exception as e:
    print("  (listing the mirror needs the OneLake path to be mounted:", str(e)[:80], ")")
"""))

    # =======================================================================
    A(md("""
---

## 7. What it costs, and why this is cheaper than doing it in T-SQL

### The unit of money in Fabric

Everything runs against **capacity units (CU)**. A capacity is a fixed number
of CU per hour (an F2 is 2, an F64 is 64, this trial is an FTL64), billed by the
second while it is running. Workloads draw from that pool. The relevant rates,
from Microsoft Learn:

| Compute | CU while running | Source |
| --- | --- | --- |
| Python notebook, 8 vCores | **4 CU** | *Choosing a notebook kernel*: 1 CU per 2 vCores, default 2 vCores = 1 CU |
| Spark starter pool (default Spark notebook) | **8 CU** minimum after scale-up | same article |
| Spark single-node 8 vCore, if configured | 4 CU | same article |

### The build, measured

The cell below reads the build's own record and prices it. Change
`PRICE_PER_CU_HOUR` to your region's pay-as-you-go rate (Azure pricing page:
*Microsoft Fabric*; the default below is a US list price and is an
**assumption**).

### The comparison, and what is honest about it

The DuckDB run is **measured**. The alternative is **modelled**, and the model
is conservative in the alternative's favour:

- A Spark or Warehouse transformation of the same job is assumed to take the
  **same wall time** as DuckDB. In practice a distributed engine on a job that
  fits on one node is usually slower, not faster, because it spends time
  shuffling.
- It is charged at the **starter pool minimum of 8 CU**, twice the Python
  notebook's 4 CU. That is the documented floor, not a pessimistic guess.
- A Warehouse T-SQL path would also need the %(gold_rows)s rows **copied into
  warehouse storage first**, a second full copy of the data that Direct Lake
  over the lakehouse never makes. That copy is not priced here at all.

What is *not* claimed: that DuckDB beats Spark on every job. Above a single
node's memory, Spark wins. This job is %(seed_gb)s GB compressed and fits.
""" % F))

    A(code("""
# MEASURED cost of the pipeline's compute, and a MODELLED alternative.
PRICE_PER_CU_HOUR = 0.18   # USD, pay-as-you-go, US list price. ASSUMPTION: set yours.

cu_python = 4                       # 8 vCores on the Python kernel (Microsoft Learn)
cu_spark_starter = 8                # starter pool minimum after scale-up (Microsoft Learn)
vorder_s = %(vorder_s)s             # measured, BUILD_LOG section 31

build_s = T["total_s"]              # measured, this workspace, build_gold.json

def cost(cu, seconds):
    return cu * seconds / 3600 * PRICE_PER_CU_HOUR

rows = [
    ("DuckDB transform, Python 8 vCores", "measured", cu_python, build_s),
    ("V-Order write, Spark starter pool",  "measured time, documented CU", cu_spark_starter, vorder_s),
]
alt = [
    ("Same transform on Spark starter pool", "modelled: same wall time, 8 CU", cu_spark_starter, build_s),
    ("V-Order write, Spark starter pool",    "measured time, documented CU", cu_spark_starter, vorder_s),
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
print(f"compute saved on the transformation step: {(1 - a_cuh/b_cuh)*100:.0f}%%  "
      f"({b_cuh - a_cuh:.3f} CU-h, ${b_usd - a_usd:.3f} at ${PRICE_PER_CU_HOUR}/CU-h)")
print()
print("Not priced, in the alternative's favour: a Warehouse T-SQL path would first copy")
print(f"{B['counts']['fact_transaction']:,} rows into warehouse storage. Direct Lake over the")
print("lakehouse reads the Delta files the notebook wrote, so this pipeline holds ONE copy.")
""" % F))

    A(md("""
### The bigger saving is structural, not per-run

Two copies of the data never get made:

1. **No warehouse copy.** Direct Lake reads the gold Delta tables where Spark
   wrote them. A T-SQL transformation path lands its output in warehouse
   storage, and the semantic model reads that; the lakehouse copy and the
   warehouse copy both persist and both cost storage.
2. **No import copy.** An Import-mode model would hold a third copy in memory
   and refresh it on a schedule, paying CU on every refresh whether or not
   anything changed. Direct Lake's framing reads the Delta log instead and
   costs seconds.

And the report adds a third, at query time: after the one measure per page,
every interaction is free. That is measurable on this workspace by watching the
Capacity Metrics app while clicking through the report, which is the test worth
running before believing any of this.
"""))

    # =======================================================================
    A(md("""
---

## 8. Reproducing the whole thing

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
