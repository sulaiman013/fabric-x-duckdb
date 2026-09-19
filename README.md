# Financial Crime Monitoring on Fabric: the README

**What this is.** A complete pipeline from an on-premises PostgreSQL database
to an interactive Power BI report, built on Microsoft Fabric, over
**49,406,792** card and account transactions. Every item in this workspace
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
| 03 Semantic Model | `fincrime_model` | Semantic model | Direct Lake, 9 tables, 8 relationships, 17 measures |
| 04 Application | `FinCrime` | Report | Four pages, each one HTML visual driven by one measure |
| Deprecated | `stage_lh` | Lakehouse | Empty. Created while investigating uploads, superseded |

The SQL analytics endpoints you see next to the lakehouses and databases are
created automatically with their parent and are not separate work.

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
re-measured by `scripts/uat.py` on every acceptance pass. The only two things
marked **modelled** are the Spark cost comparison and the price per CU-hour.

The page is generated from `parts/` by `assemble.py` and gated by `verify.py`,
which drives both views in a real browser and asserts that nothing overlaps,
nothing escapes its container, every declared wire is actually drawn, and the
packets are moving.

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
   table was loaded, because no combination of the 100 business
   columns is unique. That key is what later makes the 593,209 exact
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
| Source | 50,000,000 rows x 100 text columns, 45.0 GB CSV, 48 GB in PostgreSQL |
| Seed export, Postgres to zstd parquet | 16 files, 10.5 GB (4.3x smaller than the CSV) |
| Seed upload with azcopy | 29 minutes |

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

---

## 2. Transformation: DuckDB on a Python notebook (`01_build_gold`)

### Why DuckDB, and why a Python notebook

The landing table is 50,000,000 rows of **text**. Nothing was typed or
cleaned on the way in, deliberately: a landing zone that rejects rows is not a
landing zone. So all the real work happens here, and the shape of that work
decides the compute.

The work is a single-machine analytical job: parse five competing date formats,
turn `1,234.50` and `(45.00)` and `RM99.00` into numbers, collapse 32 spellings
of one country to one code, run seven risk rules with window functions, score,
deduplicate, and build a star. That is exactly what DuckDB is built for, and at
10.5 GB compressed it fits comfortably on one node.

A **Python notebook** in Fabric is a single node that bills at **1 CU per 2
vCores** (Microsoft Learn: *Choosing a notebook kernel*). At 8 vCores it costs
**4 CU** while it runs. A Spark starter pool, the default for a Spark notebook,
bills a minimum of **8 CU** once it scales up, and Spark would spend much of the
run coordinating a distributed engine for a job that does not need distributing.

### How it works

`01_build_gold` is generated from `scripts/build_gold_notebook.py`, which
embeds `transform.py`, `rules.py` and `star.py` verbatim. The code validated
against the full 50,000,000 rows is byte-for-byte the code that runs.

1. `%%configure {"vCores": 8}` sets the node size. It must be the first
   cell, and API-triggered runs honour it.
2. DuckDB reads the mirror through the shortcut: `delta_scan('/lakehouse/default/Tables/raw_txn')`.
3. `star.build()` runs the three SQL layers in one connection: **silver**
   (typing and conforming), **enriched** (the rule inputs, several of which are
   window functions over customer history), **scored** (rule weights summed
   into `risk_score` and banded LOW / MEDIUM / HIGH).
4. Exact duplicates are removed by keeping the lowest `_mirror_row_id` per
   business-column group: **593,209** rows, 1.19%.
5. Seven dimensions are built with an explicit **Unknown member at key -1**,
   so every fact row has a foreign key. Null foreign keys across all six
   relationships: **0**.
6. The nine tables are written to `Files/gold` as zstd parquet:
   **1.86 GB**, five times smaller than the 10.5 GB it
   derives from, because typed columns compress and text does not.

### What cleaning actually recovered

| Column | Raw landing zone | Gold |
| --- | --- | --- |
| `posting_date` parses as a date | 47.5% | **93.0%** |
| Country | 32 spellings | 1 code |
| KYC status | 11 variants | 5 |
| Card brand | 44 variants | 5 |

The 7% of dates that still do not parse are genuinely unrecoverable. They sit
on the Unknown date member and are **shown** on the report's trend, not
dropped.

### Two DuckDB lessons worth keeping

- **`SUMMARIZECOLUMNS` is not the only thing that behaves differently at
  scale.** Rule fire rates measured on a 2M-row sample did not hold at 50M:
  `new_merchant` went from 1.1% to 27.6% because window-dependent rules need
  the full history. Rules were recalibrated on the full data, and two were
  dropped for firing on almost everything or almost nothing.
- **DuckDB's temp directory follows the database file.** A surrogate key on
  `fact_alert` forced a global sort that spilled 38 GB, to the wrong disk. The
  key was removed and the spill target set explicitly. Both fixes are in the
  notebook.

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
**3 min 53 s** wall time for 49,406,792 rows across nine tables (the latest
run, from the jobs API; the cost cell in section 6 reads it live). The result is **36 files, 2.5 GB** of
Delta in OneLake.

`03_verify` then reads the Delta logs on capacity and writes `Files/verify.json`
with the row count, file count and size of every table. The transformation
cell above compares against it; a mismatch fails loudly.

One operational detail: after tables land, the lakehouse's SQL analytics
endpoint syncs its metadata **asynchronously**. Querying `gold_fact_transaction`
immediately returns `Invalid object name`. The fix is
`POST .../sqlEndpoints/{id}/refreshMetadata`, which the build does before the
model is touched.

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
9 tables, 8 relationships, 17
measures. Every measure was verified by DAX against DuckDB and reconciles to
the cent. Surrogate keys are hidden and set to `summarizeBy: none`, because a
summed key is a confident wrong number.

One measure is worth understanding, because the report rests on it:

    Alerts Raised = CALCULATE ( [Transactions], fact_transaction[risk_band] = "HIGH" )

An **alert** is the score crossing into the HIGH band. A **rule firing** is a
contribution to the score. Counting every firing as an alert gives an 80%
alert rate, about 317 full-time analysts. Counting alerts gives
**2.88%**, about 28 analyst-years across the period. The first is an
unstaffable queue that gets ignored; the second is a control that works.

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

A DAX measure holds roughly **2,100,000 characters**. Shipping 49,406,792
rows at grain would need about 1.7 billion. So the Overview measure aggregates
to month x channel x risk band x transaction type: **2,508** populated
cells, about **4%** of the ceiling, from a 49.4M-row table. Money
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

---

## 6. What it costs, and why this is cheaper than doing it in T-SQL

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

Capacity bills a notebook for its **session wall time**, startup included, not
for the seconds its cells were busy. So the cell below prices the wall time of
each notebook's most recent completed run, read live from the jobs API, and
prints the build's own in-notebook work time beside it so the startup overhead
is visible rather than hidden. Change `PRICE_PER_CU_HOUR` to your region's
pay-as-you-go rate (Azure pricing page: *Microsoft Fabric*; the default below
is a US list price and is an **assumption**).

### The comparison, and what is honest about it

The DuckDB run is **measured**. The alternative is **modelled**, and the model
is conservative in the alternative's favour:

- A Spark or Warehouse transformation of the same job is assumed to take the
  **same wall time** as DuckDB. In practice a distributed engine on a job that
  fits on one node is usually slower, not faster, because it spends time
  shuffling.
- It is charged at the **starter pool minimum of 8 CU**, twice the Python
  notebook's 4 CU. That is the documented floor, not a pessimistic guess.
- A Warehouse T-SQL path would also need the 49,406,792 rows **copied into
  warehouse storage first**, a second full copy of the data that Direct Lake
  over the lakehouse never makes. That copy is not priced here at all.

What is *not* claimed: that DuckDB beats Spark on every job. Above a single
node's memory, Spark wins. This job is 10.5 GB compressed and fits.

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
