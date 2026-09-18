# Raw Banking Extract: 50M x 100 columns

A synthetic but deliberately *ungoverned* transaction extract, generated with
DuckDB and landed untransformed in PostgreSQL. It exists to give downstream
work something honest to chew on: a single wide flat table that looks like
what a core banking system, a card switch and a CRM actually produce when
nobody has cleaned up after them.

**50,000,000 rows. 100 columns. Every column is text. Nothing is cleaned.**

## What this project is

An end-to-end demonstration of getting **on-premises PostgreSQL data into Fabric
OneLake using open mirroring**, and then doing something real with it.

| Phase | What | Layer |
| --- | --- | --- |
| **1** | On-prem PostgreSQL to OneLake via open mirroring: initial seed plus continuous CDC from the write-ahead log | Bronze (raw, all TEXT) |
| **2** | DuckDB on a Fabric Python notebook (8 vCores): cleaning, typing, conforming, seven measured risk rules, dedupe, star schema; Spark for the V-Ordered write | Silver to Gold |
| **3** | Direct Lake semantic model over the gold tables: 9 tables, 8 relationships, 17 measures, verified by DAX | Semantic |
| **4** | Fabric App: operational activities, reporting and analytics on the banking data | Application |

Each phase is deliberately constrained so the next one has something honest to
do. The bronze layer is text-only and genuinely dirty, which is what makes the
Phase 2 cleaning work meaningful rather than decorative. The surrogate key added
for mirroring (`_mirror_row_id`) is also what makes the 593,209 exact duplicate
rows resolvable downstream, since no subset of the 100 business columns is
unique.

### Why open mirroring, and why a seed plus CDC

Fabric's **native** database mirroring connects directly to the source with no
file transfer, but it supports Azure SQL Database, SQL Server, Cosmos DB, Oracle,
SAP and **Azure Database for PostgreSQL**. A PostgreSQL instance on `localhost`
is not reachable by Fabric and is not a supported native source, so **open
mirroring** is the correct mechanism: the publisher writes change files into a
landing zone and Fabric's replication engine applies them to Delta tables.

Mirroring is seed-then-stream. The seed establishes the baseline; CDC keeps it
live. A change feed with no seed would leave Fabric holding only rows that
changed after the slot was created, which is not a mirror and gives Phase 2
nothing to model.

## Why nothing is transformed

This is a landing zone, not a model. The extract contains values like
`1,234.50`, `(45.00)`, `RM99.00`, `N/A`, `9999-12-31` and `05/03/2024`. None
of those survive a cast to `NUMERIC` or `DATE` on the way in, and a landing
zone that rejects rows is not a landing zone. So all 100 columns are created
as `TEXT` and the bytes land exactly as generated. Typing, parsing and
conforming are downstream concerns, which is the whole point: the mess has to
still be there when you go looking for it.

## Layout

```
duckdb in fabric/
  README.md
  BUILD_LOG.md            chronological record of how this was built
  .gitignore              data, credentials and __pycache__ never committed
  scripts/
    schema.py             the 100 column definitions + mess injection
    generate.py           DuckDB generator, chunked and resumable
    validate.py           profiles the output and proves the mess is real
    load_postgres.py      parallel COPY into a raw TEXT landing table
    snapshot_to_fabric.py seeds the mirror: Postgres -> parquet -> OneLake
    transform.py          clean + conform: 5 date formats, money as text, 32 spellings of MY
    rules.py              7 risk rules, measured and recalibrated against real fire rates
    star.py               2 facts + 7 dimensions, explicit Unknown members, 0 null FKs
    build_semantic_model.py  authored Direct Lake TMDL, importable with fab
    threshold_analysis.py precision, recall and analyst headcount per alert threshold
    cdc_to_fabric.py      continuous CDC: WAL -> __rowMarker__ parquet -> OneLake
    cdc_demo.py           proves update/delete propagate, not just inserts
    verify_fabric.py      reads the Delta transaction log to check what landed
    test_cdc_parser.py    tests for the test_decoding payload parser
    ops_db.py             the five ops tables for write-back, DDL in one place
    build_ops_notebook.py generates 04_ops_ddl from that DDL (SQL token exists only on capacity)
    build_gold_notebook.py generates 01_build_gold: the DuckDB transformation as a Python notebook
    build_probe_mirror.py generates zz_probe_mirror: checks the mirror against PostgreSQL row by row (a probe, not a step)
    build_readme_notebook.py generates 00_README: workspace documentation that measures itself
    build_report.py       generates the four-page PBIP report, live on the Direct Lake model
    bisect_measure.py     bisects a report measure against Desktop through the bridge
    folderize_workspace.py files every workspace item into its phase folder
  notebooks/
    00_README.Notebook    what every item is, how the pipeline works, what it costs
    01_build_gold.Notebook DuckDB on 8 vCores: clean, conform, score, dedupe, star
    02_vorder_write.Notebook Spark: rewrite gold parquet as V-Ordered Delta
    04_ops_ddl.Notebook   create the ops tables in fincrime_ops
  udf/                    the write-back user data functions
  report/                 the PBIP: FinCrime.pbip + FinCrime.Report

D:/duckdb-fabric-data/
  csv/                    50 chunks, 45 GB    <- generated raw data
  snapshot/               16 parquet, 10.5 GB <- mirror seed
  gold/                   9 parquet, 1.9 GB   <- star schema, uploaded to the lakehouse
```

### Pipeline at a glance

```
generate.py    50M x 100 messy text columns            -> CSV on D:
load_postgres.py   parallel COPY, all TEXT, LOGGED     -> landing.raw_txn (48 GB)
                   + surrogate key _mirror_row_id
snapshot_to_fabric.py  DuckDB reads Postgres -> zstd parquet -> azcopy -> LandingZone
cdc_to_fabric.py       WAL -> logical slot -> parquet + __rowMarker__ -> LandingZone
                   Fabric applies insert / update / delete to the Delta table
01_build_gold.Notebook     DuckDB, Python kernel, 8 vCores, over a lakehouse shortcut to the mirror -> gold parquet
02_vorder_write.Notebook   Spark rewrites gold as V-Ordered Delta (DuckDB cannot)
build_semantic_model.py    Direct Lake model, 17 measures, alerts priced in analyst headcount
```

### Where the data lives, and why not here

The CSV is roughly **45 GB** and the PostgreSQL table is roughly **55 GB**.
This machine has ~61 GB free on `C:` and ~583 GB free on `D:`, and the
PostgreSQL data directory sits on `C:` under `C:\Program Files\PostgreSQL\16\data`.

Both artefacts therefore live on `D:`:

* CSV output goes to `D:/duckdb-fabric-data/csv`
* the Postgres table goes on a **tablespace** at `D:/pgdata/banking_raw`, so
  the load does not fill the system drive

Only the scripts live in this folder. That also keeps 45 GB of CSV out of a
git repository, which the `.gitignore` enforces.

## Usage

### Generate

```bash
python scripts/generate.py --rows 50000000 --chunk 1000000 --out D:/duckdb-fabric-data/csv
```

Useful flags:

| flag | meaning |
| --- | --- |
| `--rows` | total rows, duplicates included. Lands on the number exactly. |
| `--chunk` | base rows per CSV file. 1M gives ~921 MB files. |
| `--dup-rate` | fraction re-emitted as exact duplicate rows (default 1.2%) |
| `--resume` | skip chunk files that already exist |
| `--seed` | reproducibility |
| `--threads`, `--memory-limit` | DuckDB tuning |

Measured on this machine (16 threads, 31 GB RAM): **~42,500 rows/s**,
**921 MB per million rows**, so 50M takes roughly 20 minutes and ~45 GB.

Chunk size matters. At 25k rows per chunk the throughput collapses to ~6,000
rows/s because compiling the very large 100-column SQL statement dominates.
Keep chunks at 1M.

### Validate

```bash
python scripts/validate.py --path D:/duckdb-fabric-data/csv
```

### Load into PostgreSQL

Put the password in libpq's password file so it never appears on a command
line or in a shell history. On Windows that is
`%APPDATA%\postgresql\pgpass.conf`, one line:

```
localhost:5432:*:postgres:YOUR_PASSWORD
```

Then:

```bash
python scripts/load_postgres.py --path D:/duckdb-fabric-data/csv --jobs 6 --logged
```

**Pass `--logged`.** The default is UNLOGGED, which is faster to load but is
never captured by logical replication, so the mirror's CDC would silently see
nothing. Loading LOGGED also avoids rewriting a 48 GB table with
`ALTER TABLE ... SET LOGGED` later. Measured: 50,000,000 rows in 10.9 minutes
at 76,465 rows/s with six connections.

`--resume` skips files already recorded in `landing._load_log`, so an
interrupted load picks up where it stopped.

## The data

100 columns in nine groups, modelled on a Malaysian retail bank:

| group | cols | examples |
| --- | --- | --- |
| transaction core | 10 | `txn_id`, `txn_datetime`, `posting_date`, `txn_type`, `narrative` |
| account | 11 | `account_no`, `iban`, `product_name`, `branch_name` |
| customer | 17 | `full_name`, `nric_passport`, `dob`, `occupation`, `income_band` |
| address | 6 | `addr_line1`, `addr_city`, `addr_state`, `addr_postcode` |
| KYC / compliance | 10 | `kyc_status`, `risk_rating`, `pep_flag`, `aml_score` |
| merchant | 9 | `merchant_name`, `merchant_mcc`, `terminal_id` |
| amounts | 12 | `txn_amount`, `fx_rate`, `fee_amount`, `balance_after` |
| card | 10 | `card_no_masked`, `card_brand`, `card_expiry`, `auth_response` |
| channel / device | 8 | `channel`, `device_id`, `ip_address`, `user_agent` |
| ops / audit | 7 | `reversal_flag`, `settlement_batch`, `source_system`, `record_hash` |

### Entities stay coherent

Attributes that belong to an entity rather than to a transaction are chosen by
`hash(entity_id)`, not `random()`. A customer therefore keeps the same
underlying name, date of birth, occupation and address across every one of
their rows, and a merchant keeps the same MCC.

The mess is applied *on top* of that. The result is the real problem you want
to practise on: one customer appearing as `Ahmad bin Abdullah`,
`AHMAD BIN ABDULLAH`, ` ahmad  bin abdullah `, and `Abdullah, Ahmad` -- rather
than the useless alternative where every row is a different person and no
join or dedupe exercise means anything.

### The mess catalogue

Measured on a 300k-row sample:

* **mean 18.4%** of values per column are null, null-like or whitespace-padded
* null lookalikes: `NULL`, `N/A`, `NA`, `-`, `unknown`, `none`, `#N/A`, `''`
* **five date formats** in the same column: `2024-03-05`, `05/03/2024`,
  `03/05/2024`, `5-Mar-24`, `05.03.2024`
* sentinel dates: `1900-01-01`, `9999-12-31`, `0000-00-00`, `1970-01-01`
* money as text: `1,234.50`, `RM99.00`, `(45.00)` for negatives, bare floats
* timestamps with, without and half-with timezone, plus raw epoch integers
* leading-zero loss and float artefacts in `account_no` and `card_last4`
* casing and abbreviation drift everywhere
* **1.18% exact duplicate rows**
* typos seeded into categoricals (`Enginer`, `Techer`, `TRANSFERR`, `PO S`)
* free text containing commas and quotes, correctly CSV-quoted

Which produces, on the 300k sample:

| column | parses cleanly |
| --- | --- |
| `posting_date` as a date | 52.4% |
| `txn_amount` as a number | 81.7% |
| `balance_after` as a number | 70.5% |
| `txn_datetime` as a timestamp | 95.8% |

and 31 distinct spellings of the country Malaysia, 34 of `txn_type`, 43 of
`card_brand`.

### NULL vs empty string

DuckDB writes SQL `NULL` as an unquoted empty field and a genuine empty string
as a quoted `""`. Postgres CSV `COPY` reads unquoted empty as `NULL` and `""`
as an empty string, so the distinction survives the round trip. Both are
present in the data on purpose.

## Notes and gotchas

* `strftime` in DuckDB requires a **constant** format string, so mixed date
  formats are built with `CASE`, not by indexing a list of formats.
* Print anything through `PYTHONIOENCODING=utf-8` on Windows; the default
  cp1252 console encoding cannot render DuckDB's box-drawing output.
* Duplicates are appended at the end of each chunk file rather than
  interleaved. Across 50 files they still land throughout the dataset.
* Generating into a temp table before writing is what makes *exact* duplicates
  possible; a re-scan would re-roll `random()` and produce near-duplicates.
