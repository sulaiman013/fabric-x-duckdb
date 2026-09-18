# Build Log

Chronological record of how this project was built: decisions, measurements,
bugs found and fixed, and what remains. Newest entries at the bottom.

Session date: 2026-09-18

---

## 1. Environment survey

Before generating anything, checked what the machine could actually hold.

| Finding | Value |
| --- | --- |
| `C:` free | 61 GB |
| `D:` free | 583 GB |
| PostgreSQL | 16.14, service running as `NT AUTHORITY\NetworkService` |
| PostgreSQL data dir | `C:\Program Files\PostgreSQL\16\data` (on the **system drive**) |
| CPU / RAM | 16 threads / 31.3 GB |
| Already installed | `psycopg2-binary`, `pyarrow`, `numpy`, `pandas`, `fab` 1.6.1 |
| Missing | `duckdb` (installed), `uv`, `az` |

**Key constraint identified early:** the Postgres data directory sits on `C:`,
which cannot hold a dataset this size. Everything large had to go to `D:`.

---

## 2. Scope negotiation

The request started at **1 billion rows** and moved twice:

1. **1B rows**: flagged that this meant ~100 GB CSV plus ~100 GB in Postgres,
   and that `C:` could not hold either.
2. **250M rows**: then the shape changed: no star schema, no transformation,
   a single wide flat table of ~100 columns of raw messy data.
3. **50M rows**: final. At 100 columns this is ~45 GB CSV, which fits
   comfortably on `D:`.

Domain and mess profile were chosen by the user:

- **Domain:** banking / fintech transactions (Malaysian retail bank flavour)
- **Mess profile:** "realistic", roughly 10-20% of values affected
- **Shape:** one flat table, exactly 100 columns, every column text

---

## 3. Schema design (`scripts/schema.py`)

Built a 110-column catalogue, then excluded 10 redundant columns to land on
exactly 100. Each exclusion was chosen because another column already carried
the same *kind* of mess, so no distinct pattern was lost (`bank_code` is in
`iban`, `phone_home` duplicates `mobile_no`, and so on).

Mess is injected at generation time, not bolted on afterwards:

- null lookalikes: `NULL`, `N/A`, `NA`, `-`, `unknown`, `none`, `#N/A`, `''`
- five competing date formats in the same column
- sentinel dates `1900-01-01`, `9999-12-31`, `0000-00-00`, `1970-01-01`
- money as text: `1,234.50`, `RM99.00`, `(45.00)`, bare floats
- timestamps with, without and half-with timezone, plus raw epoch integers
- casing drift, whitespace padding, seeded typos (`Enginer`, `TRANSFERR`)

---

## 4. DuckDB gotchas found while building

1. **`strftime` requires a constant format string.** Indexing a list of format
   strings fails with `Invalid Input Error: strftime format must be a constant`.
   Mixed date formats had to be built with `CASE`.
2. **Windows console encoding.** Printing DuckDB's box-drawing output through
   the default cp1252 console raises `UnicodeEncodeError`. Everything runs with
   `PYTHONIOENCODING=utf-8`.
3. **Heredoc fragility.** Writing a large Python file through a bash heredoc
   mangled backslash escapes and broke quoting; switched to direct file writes.

---

## 5. Bugs found and fixed

### 5.1 `%%` left literal by `.format()`

The base-CTE builder used `.format()`, where `%` is literal. Modulo operators
written as `%%` stayed as `%%` and produced invalid SQL. Fixed to single `%`.

### 5.2 Self-referential INSERT for duplicate injection

`INSERT INTO chunk_tmp SELECT * FROM chunk_tmp USING SAMPLE ...` reads and
writes the same table. Replaced with a staged `dup_tmp` table.

### 5.3 Entity incoherence: the important one

The first 50k smoke test produced a row where:

```
full_name  = 'Li Hua Lim'
first_name = 'Ahmad'
last_name  = 'a/p Krishnan'
```

Every attribute was an independent `random()` pick, so the same customer became
a different person on every row. That would make the data useless for any join,
dedupe or entity-resolution exercise.

**Fix:** added `pick_det()`, which selects from a value pool using
`hash(entity_id)` instead of `random()`. Applied across 22 call sites so
customer, account, merchant and card attributes are stable per entity. The mess
layer then sits *on top*, which produces the realistic problem:

> one customer appearing as `Ahmad bin Abdullah`, `AHMAD BIN ABDULLAH`,
> ` ahmad  bin abdullah ` and `Abdullah, Ahmad`

rather than four different people.

### 5.4 Loader opened a transaction before setting autocommit

The first full load run crashed immediately:

```
psycopg2.ProgrammingError: set_session cannot be used inside a transaction
```

`SELECT version()` opened an implicit transaction, then `ensure_tablespace`
tried to flip `autocommit`. Fixed by setting `autocommit` right after connect.

### 5.5 Loader would block on a hidden password prompt

`getpass` would hang forever in an unattended background run. Changed to try a
passwordless connect first (letting libpq resolve `pgpass.conf`) and only
prompt when attached to a TTY.

---

## 6. Validation of the generated data

Profiled a 300k-row sample with `scripts/validate.py`:

| Check | Result |
| --- | --- |
| Columns | 100, all text, header matches schema |
| Mean mess rate across 100 columns | **18.4%** |
| Exact duplicate rows | **1.18%** |
| Customers with conflicting names | **0** (fix 5.3 verified) |
| `posting_date` parses as a date | **52.4%** |
| `txn_amount` parses as a number | **81.7%** |
| `balance_after` parses as a number | **70.5%** |
| Distinct spellings of "Malaysia" | **31** |
| Distinct `txn_type` values | **34** |
| Distinct `card_brand` values | **43** |

---

## 7. Git setup, and a near-miss

Created a nested git repo scoped to this folder (the parent portfolio folder is
a separate repo pointing at an unrelated remote, so it was deliberately not
touched) and pushed to `https://github.com/sulaiman013/fabric-x-duckdb`.

**Near-miss:** the first `git add -A` staged a file named
`fabric id and pass.md` that was sitting in this folder. The target repo is
**public**. Caught before any commit or push. Nothing left the machine.

Response:
- unstaged everything, staged the six intended files explicitly
- hardened `.gitignore` with credential patterns (`*id and pass*`, `*password*`,
  `*secret*`, `*credential*`, `.env`, `*.pem`, `*.key`) plus `__pycache__/`
- verified with `git check-ignore -v` and confirmed the file is absent from the
  remote tree

Standing recommendation: move that file out of the project folder entirely. A
gitignore rule protects this repo, not the file.

---

## 8. Generation run

```
python scripts/generate.py --rows 50000000 --chunk 1000000 --out D:/duckdb-fabric-data/csv
```

| Metric | Value |
| --- | --- |
| Rows | 50,000,000 (exact) |
| Columns | 100 |
| Files | 50 chunks |
| Total size | **45.0 GB** |
| Elapsed | **35.0 min** |
| Throughput | ~42,500 rows/s on 16 threads |
| Row width | ~966 bytes |

Chunk size matters: at 25k rows/chunk throughput collapsed to ~6,000 rows/s
because compiling the 100-column SQL dominated. At 1M rows/chunk it reached
~42,500 rows/s.

---

## 9. PostgreSQL load

Storage decision: the table cannot live on `C:`, so a tablespace was created on
`D:` and the service account granted access.

```sql
CREATE TABLESPACE bigdata LOCATION 'D:/pgdata/banking_raw';
```

```
icacls D:\pgdata\banking_raw /grant "NT AUTHORITY\NetworkService":(OI)(CI)F /T
```

Then loaded with 6 parallel COPY connections into an all-TEXT `LOGGED` table.
`LOGGED` was chosen deliberately: logical replication does not capture UNLOGGED
tables, and converting a 48 GB table later would force a full rewrite.

| Metric | Value |
| --- | --- |
| Rows in table | **50,000,000** |
| Columns | 100, all `text` (1 distinct type) |
| Table size | **48 GB** |
| Tablespace | `bigdata` (on `D:`) |
| Persistence | `p` (LOGGED, CDC-ready) |
| Elapsed | **10.9 min** |
| Aggregate throughput | **76,465 rows/s** |

Integrity verified after load:

| Check | Result |
| --- | --- |
| `posting_date` IS NULL | 575,736 |
| `posting_date` = `''` | 250,359 |
| Duplicate `txn_id`s | 593,209 |

The NULL vs empty-string split confirms the round trip is lossless: DuckDB
writes SQL `NULL` as an unquoted empty field and a real empty string as quoted
`""`; Postgres CSV `COPY` reads those back as `NULL` and `''` respectively.

---

## 10. Fabric: workspace and open mirroring

Authenticated with `fab auth login` (device flow; `fab` cannot use a username
and password, since `-u`/`-p` are a service principal client ID and secret).

Target workspace: **`fabric duckdb`** (`7e0f6e0d-...`), which already contained:

- `sulaiman-postgres.MirroredDatabase` (`5069602e-...`), status **Running**
- `sulaiman-postgres.SQLEndpoint`, provisioned

Pulled the authoritative open-mirroring spec from Microsoft Learn rather than
assuming. The rules that matter:

1. `_metadata.json` in each table folder declaring `keyColumns`. Without it,
   Fabric will not ingest.
2. Data files named `00000000000000000001.parquet`, 20 digits, zero padded,
   continuously increasing.
3. `__rowMarker__` must be the **final column**: `0`=insert, `1`=update,
   `2`=delete, `4`=upsert.
4. For the **initial load**, `__rowMarker__` should be omitted entirely; the
   whole file is then treated as INSERT.
5. Parquet must use valid logical/physical type pairs (e.g. DATE must be INT32).
   Not a concern here, since all 100 columns are strings.
6. Processed files are moved to `_ProcessedFiles` and deleted after 7 days.

---

## 11. Upload path investigation

This took several attempts and is worth recording.

| Attempt | Result |
| --- | --- |
| `fab cp` local to MirroredDatabase | **Fails**: `Source and destination must be of the same type` |
| `fab api -A storage` with a full OneLake URL | **Fails**: `artifact type is unknown` |
| `fab api -A storage` with `ws.Workspace/item.MirroredDatabase` | **Fails**: resolves internally to `MountedRelationalDatabase`, not found |
| `fab api -A storage` with `{workspaceId}/{itemId}` GUIDs | **Works**: 200, lists and deletes fine |
| `fab api` three-step ADLS create/append/flush | Create 201, append 202, but **flush fails**; `-i` does not send binary file contents |
| `fab cp` to a Lakehouse | **Works**, byte-exact (627 = 627) |
| `fab cp` of a 216 MB file | **Times out after 246s**: single-shot upload, no chunking |
| **azcopy** with `--trusted-microsoft-suffixes` | **Works**: 216 MB in **40s** |

Parquet compression measured on one 931.8 MB CSV chunk:

| Codec | Size | Ratio | Time |
| --- | --- | --- | --- |
| snappy | 330.1 MB | 2.8x | 6.5s |
| **zstd** | **216.1 MB** | **4.3x** | 6.8s |

So the full 50M snapshot is roughly **10.8 GB** as zstd Parquet, not 45 GB. At
azcopy's measured ~5.4 MB/s that is about **33 minutes**, which makes mirroring
the complete dataset practical.

azcopy needed two non-obvious things:
- `--login-type=device` (interactive browser code) since `az` CLI is absent
- `--trusted-microsoft-suffixes="onelake.dfs.fabric.microsoft.com"`, otherwise
  it refuses to send an Entra token to OneLake

Confirmed azcopy can write directly to the **MirroredDatabase** item, so no
Lakehouse staging hop is needed. A `stage_lh.Lakehouse` was created during
investigation and is now redundant.

All probe files were removed; the landing zone is clean.

---

## 12. Snapshot exporter, and the poll race

Built `scripts/snapshot_to_fabric.py`:

```
PostgreSQL --(DuckDB postgres scanner)--> zstd Parquet --(azcopy)--> OneLake LandingZone
```

DuckDB reads Postgres directly via the `postgres` extension at ~41,780 rows/s,
writing one file per thread with `PER_THREAD_OUTPUT`, then renaming to the
20-digit contiguous sequence open mirroring requires.

### The race that costs you the table

First trial run (200k rows) uploaded cleanly, azcopy reported
`Final Job Status: Completed` with zero failures, and the file on OneLake
measured **46,541,460 bytes, byte-identical to local**. Fabric still failed:

```
We encountered an error while opening the Parquet file
'.../00000000000000000001.parquet' ...
'Invalid: Parquet file size is 0 bytes'
```

Fabric polls the landing zone roughly **every 20 seconds** and had opened the
file while azcopy was still writing it. Worse, the failure **latches**: the
error persisted at `SequenceNumber: 0` and Fabric never retried, even once the
file was complete. The documented recovery is to delete and recreate the table
folder.

Attempted fix via ADLS atomic rename (upload as `.tmp`, then
`x-ms-rename-source`) failed, because `fab` parses the header value as a Fabric
item path and rejects it:

```
Required item type extension is missing in the item name.
Expected format {itemname}.{itemtype}
```

**Working fix: invert the documented order.** Fabric ignores a table folder that
has no `_metadata.json`, so:

1. upload every `.parquet` first and verify the sizes landed
2. upload `_metadata.json` last, which arms ingestion

By the time Fabric looks, every file is complete. The script also refuses to
write `_metadata.json` if the data upload fails, so a partial set is never
ingested.

---

## 13. Open mirroring verified end to end

With the corrected ordering, the 200k-row trial ingested cleanly:

| Field | Value |
| --- | --- |
| `status` | **Replicating** |
| `processedRows` | **200,000** |
| `processedBytes` | 341,250,566 |
| `lastSyncDateTime` | 2026-09-18T06:39:26Z |
| Errors | none |

A real Delta table materialized in OneLake:

```
Tables/dbo/raw_txn_test/_delta_log/00000000000000000000.json
Tables/dbo/raw_txn_test/_delta_log/00000000000000000001.json
Tables/dbo/raw_txn_test/part-00000-....c000.zstd.parquet
Tables/dbo/raw_txn_test/_index_bin/part-00000-....c000.zstd.ibin
```

The `_index_bin` file is Fabric's V-Order index, and processed landing-zone
files were moved to `_FilesReadyToDelete` as documented.

The full chain is therefore proven:

> PostgreSQL -> DuckDB -> zstd Parquet -> azcopy -> OneLake LandingZone -> Fabric Delta table

---

## 14. Full-scale snapshot export and upload

Exported the whole table from PostgreSQL to mirroring-ready Parquet:

| Metric | Value |
| --- | --- |
| Files | 16 (one per DuckDB thread) |
| Size | **10.5 GB** zstd (from 48 GB in Postgres) |
| Elapsed | **5.5 min** |
| Throughput | **151,331 rows/s** |

The earlier 41,780 rows/s figure was a measurement artifact: the trial run used
`USING SAMPLE`, which forces a full scan of all 50M rows to draw the sample.

Upload reached **36% at ~9.4 MB/s** before being deliberately stopped, for the
reason in the next section. Note that `contentLength` reads 0 for every file
while azcopy is mid-flight: it uploads all 16 in parallel via ADLS
append/flush, and nothing is visible until each file's final flush. That looks
identical to a stall and is not one. Progress is only visible in azcopy's own
log (`~/.azcopy/*.log`).

---

## 15. Direction change: CDC, not a bulk copy

The approach was challenged, correctly: a 10.5 GB one-shot upload is a copy, not
a mirror. Checked the documentation rather than arguing from memory. What it
establishes:

* **Open mirroring is a file-drop protocol by design.** "Open mirroring enables
  any application to write change data directly into a mirrored database in
  Fabric... Use your own application to write data into the open mirroring
  landing zone." The file transfer is the transport; the *mirroring* is what
  Fabric's replication engine does afterwards, applying `__rowMarker__`
  semantics to maintain the Delta table.
* **Native database mirroring** (no file drop, Fabric connects to the source)
  supports Azure SQL DB, SQL Server, Cosmos DB, Oracle, SAP and
  **Azure Database for PostgreSQL**. This PostgreSQL is on `localhost`. Fabric
  cannot reach a laptop, and local PostgreSQL is not a supported native source.
* **Metadata mirroring via shortcuts** applies to Databricks, Snowflake and
  Dremio. Not applicable to PostgreSQL.

Conclusion: for this source, open mirroring driven by logical replication is the
only real CDC path. **Decision: drop the bulk snapshot entirely** and stream
changes only. The in-flight upload was stopped and the landing zone cleared, to
avoid spending ~7 GB more bandwidth on files that would have been deleted anyway
once the key column changed.

---

## 16. Logical replication enabled

`Restart-Service` from a normal shell fails with
`Cannot open postgresql-x64-16 service on computer '.'`. Elevating through
`Start-Process -Verb RunAs` triggers a UAC prompt and works.

After restart:

| Setting | Value |
| --- | --- |
| `wal_level` | **logical** |
| `max_wal_size` | 4GB |
| `checkpoint_timeout` | 15min |
| Rows still present | 50,000,000 |

---

## 17. The replica identity blocker

Checked what PostgreSQL would actually emit before writing any CDC code:

```
replica identity : d   (default = use the primary key)
indexes on table : 0
```

`relreplident = 'd'` with **no primary key** means PostgreSQL emits **nothing at
all** for UPDATE and DELETE. Logical replication would have silently produced an
insert-only feed, which would look like it was working while quietly being
wrong. This is exactly the failure mode that makes a mirror indistinguishable
from a copy.

Separately, the mirroring `keyColumns` has to be genuinely unique or Fabric
cannot match an UPDATE to one row. `txn_id` has **593,209 duplicates**, and
because those duplicates are **exact full-row copies**, no subset of the 100
columns is unique either. A composite natural key is mathematically impossible
here.

**Decision: add a surrogate key.** It is landing-layer metadata, so all 100
business columns stay byte-identical and untransformed:

```sql
ALTER TABLE landing.raw_txn ADD COLUMN _mirror_row_id bigint GENERATED ALWAYS AS IDENTITY;
ALTER TABLE landing.raw_txn ADD CONSTRAINT raw_txn_pk PRIMARY KEY (_mirror_row_id);
```

This rewrites all 48 GB, so it is slow, and the tablespace temporarily holds two
copies (observed growing 48 -> 64 GB and climbing). Ordering matters: the
replication slot must be created **after** this completes, because a slot would
retain every byte of rewrite WAL and could fill `C:`.

---

## 18. The CDC replicator

`scripts/cdc_to_fabric.py` streams committed changes out of the WAL and lands
them as change files:

```
postgres INSERT/UPDATE/DELETE
  -> WAL
  -> logical replication slot (test_decoding)
  -> parse
  -> parquet with __rowMarker__ as the FINAL column
  -> LandingZone/<table>/NNNNNNNNNNNNNNNNNNNN.parquet
  -> Fabric applies insert / update / delete to the Delta table
```

Implementation notes:

* `wal2json` is not available on this machine; `pgoutput` and `test_decoding`
  are. `test_decoding` is used via `pg_logical_slot_get_changes()`, which avoids
  implementing the streaming replication protocol.
* Parsing `test_decoding` output is done character by character, not with a
  regex. The payload format is `name[type]:value` where text is single quoted
  with doubled internal quotes, and this dataset deliberately contains commas,
  quotes and whitespace inside values.
* `__rowMarker__` is written as the final column, per the spec.
* File sequence numbers continue from whatever is already in the landing zone.

The testable difference from a copy: an `UPDATE` in PostgreSQL makes the row
**change** in Fabric, and a `DELETE` makes it **disappear**. Copying files can
only ever append.

---

## 19. Tuning for this machine

Defaults were the stock PostgreSQL install. Applied for 16 cores / 31 GB:

| Setting | Before | After | Notes |
| --- | --- | --- | --- |
| `maintenance_work_mem` | 64 MB | **2047 MB** | big win for the PK build |
| `max_parallel_maintenance_workers` | 2 | 4 | capped by `max_worker_processes` |
| `max_parallel_workers` | 8 | 16 | |
| `work_mem` | 4 MB | 256 MB | |
| `effective_cache_size` | 4 GB | 24 GB | |
| `random_page_cost` | 4 | 1.1 | SSD |
| `wal_compression` | off | **zstd** | cuts rewrite WAL volume |
| `synchronous_commit` | on | off | |
| `shared_buffers` | 128 MB | 8 GB | **needs restart** |
| `max_worker_processes` | 8 | 20 | **needs restart** |

Two platform limits worth remembering:

* `maintenance_work_mem` maxes out at **2097151 kB**, so `'2GB'` (2097152 kB) is
  rejected by exactly one kilobyte. Use `'2047MB'`.
* `effective_io_concurrency` must be **0 on Windows**; any other value is
  rejected outright.

---

## 20. Service limits checked before committing to the seed

Checked the documented mirroring limits rather than discovering them mid-upload:

| Limit | Documented value | This project |
| --- | --- | --- |
| Change data per mirrored database per day | **1 TB** | 10.5 GB seed, well under |
| Maximum tables per mirrored database | 500-1000 depending on source | 1 |
| Mirrored databases are **read-only** | no calculated columns or tables | affects Phase 3 |

The read-only constraint shapes the rest of the roadmap. The documentation is
explicit: "To add calculated columns, create a Lakehouse and use shortcuts to
reference the mirrored data, then create your calculated columns in the
Lakehouse using notebooks or SQL." So Phase 2's DuckDB transformation work
lands in a Lakehouse shortcutted to the mirrored data, and the Direct Lake
model in Phase 3 is built over those gold tables, not over the mirror itself.

Throttling, if the 1 TB/day ceiling is ever hit, surfaces as:
`"The replication is being throttled and expected to continue at ..."`.

---

## 21. Surrogate key build

| Step | Elapsed |
| --- | --- |
| `ADD COLUMN _mirror_row_id ... GENERATED ALWAYS AS IDENTITY` | **19.5 min** |
| `ADD CONSTRAINT raw_txn_pk PRIMARY KEY` | with 4 parallel workers |

The tablespace grew 48 -> 97 GB while both copies existed, then dropped back to
49 GB once PostgreSQL released the original. Peak disk requirement for this
operation is therefore a little over 2x the table size, which is worth knowing
before running it on a volume with less headroom.

The parallel workers on the index build are a direct result of the tuning in
section 19; at the stock `maintenance_work_mem` of 64 MB this would have been a
single-threaded external sort.

---

## 22. Hardening found while waiting

Two defects fixed before the replicator ever ran:

1. **File sequence could silently reset.** `next_sequence()` derived the next
   20-digit file number from the landing-zone listing, but Fabric *moves*
   processed files into `_ProcessedFiles` / `_FilesReadyToDelete`. The docs say
   the most recent file is deliberately left behind for publishers to read, but
   depending on that alone means one cleanup pass resets the sequence to 1 and
   starts overwriting unconsumed changes. Now takes the high-water mark of the
   remote listing and a locally persisted counter.

2. **The `test_decoding` parser is the riskiest component**, because this
   dataset is built to break naive parsers. Added `scripts/test_cdc_parser.py`,
   8 cases covering escaped quotes (`''`), commas and padding inside values, the
   empty-string versus NULL distinction that has survived the whole pipeline, a
   value that itself looks like a column spec (`'weird[text]:value'`), and the
   key-only payload a DELETE emits. All pass.

---

## 23. CDC verified at the source, and the synchronous_commit trap

Created the slot **before** exporting the seed, so any change made during the
export is captured and there is no gap between baseline and stream:

```sql
SELECT pg_create_logical_replication_slot('fabric_cdc', 'test_decoding');
```

The first probe then returned **zero changes** despite an INSERT, an UPDATE and
a DELETE having just been committed. A non-consuming
`pg_logical_slot_peek_changes` a moment later showed all of them, and a freshly
inserted row did *not* raise the peek count.

**Cause: `synchronous_commit = off`**, set earlier to speed up the bulk load.
With asynchronous commit a transaction returns to the client *before* its WAL is
flushed to disk, and logical decoding only reads flushed WAL. So changes exist
but are invisible to the slot for a short window.

This is a nasty failure mode for CDC because it is intermittent and silent: a
poll that happens to run inside that window sees nothing and looks exactly like
"no changes occurred". The bulk load was finished, so the setting was reverted:

```sql
ALTER SYSTEM SET synchronous_commit = 'on';
```

With that fixed, all three operations decode correctly:

| Operation | `__rowMarker__` | Payload emitted |
| --- | --- | --- |
| INSERT | `0` | full row |
| UPDATE | `1` | full row with new values |
| DELETE | `2` | key columns only, as the spec allows |

The messy data also survives decoding intact. A probe value of
`MERCHANT, "quoted", 1,234.50` came back through the parser byte for byte,
commas and double quotes included, which is exactly what the parser tests in
section 22 were written to guarantee.

Table returned to exactly 50,000,000 rows after the probe rows were removed.

Note: the elevated restart for `shared_buffers = 8 GB` was declined at the UAC
prompt, so PostgreSQL is still running with the stock 128 MB. Not a blocker,
since the export is DuckDB-side and previously ran at 151,331 rows/s.

---

## 24. Phase 2 engine research, done early on purpose

Researched the Fabric Python notebook and DuckDB while the seed uploaded,
rather than discovering the constraints during Phase 2.

**Confirmed and good:**

* Fabric Python notebooks are a genuine non-Spark kernel and ship with
  **DuckDB, Polars and delta-rs preinstalled**.
* The Python kernel defaults to 2 vCores / 16 GB but **scales to 64 vCores**,
  set with `%%configure`. The planned 8 vCores is directly supported.
* Lakehouse, Warehouse and SQL analytics endpoints are all reachable from the
  Python kernel, and `notebookutils.data` allows T-SQL from Python.

**Three constraints that change how Phase 2 and 3 should be built:**

| Constraint | Consequence |
| --- | --- |
| **V-Order is Spark-only.** The kernel comparison table lists "V-order for fast Direct Lake semantic models" as supported on Spark and **not** on the Python kernel. | Gold tables written from a Python notebook are not V-Ordered, and V-Order is precisely what makes Direct Lake fast. Phase 3 needs a deliberate decision here. |
| **DuckDB Delta writes are INSERT-only.** It requires `ATTACH ... (TYPE delta, READ_WRITE)`, has no UPDATE / DELETE / MERGE, and no schema evolution on insert. | Any SCD or merge logic in the star-schema build has to go through **delta-rs**, not DuckDB. |
| **DuckDB INSERT never writes checkpoints**, so "the Delta transaction log grows unbounded". | Tables written by DuckDB need periodic delta-rs maintenance, otherwise reads degrade over time. |

**Scale band.** Microsoft's published benchmark guidance:

| Compressed data | Faster engine |
| --- | --- |
| under ~140 MB | single-machine Python (DuckDB, Polars) |
| ~1-2 GB | Python still ahead |
| **~10-13 GB** | **Spark with NEE competitive or faster; single-machine Python engines can hit out-of-memory at lower vCore counts** |
| ~100 GB+ | Spark |

This dataset is 10.5 GB compressed Parquet, 48 GB in PostgreSQL, 50M rows x 101
columns. That lands squarely in the band where the documentation explicitly
warns about OOM on single-machine engines. At 8 vCores the Python kernel gets
roughly 64 GB, so DuckDB will spill to disk. Workable, but it is the edge of
the envelope rather than the sweet spot.

The honest framing for the portfolio piece is therefore "DuckDB pushed to the
edge of its comfort zone, with delta-rs for writes and an explicit V-Order
decision for Direct Lake", not "DuckDB is simply the better engine here". That
is a more interesting and more defensible story anyway.

---

## 25. Seed ingested at full scale

The seed landed and Fabric materialised it:

| Metric | Value |
| --- | --- |
| Export | 16 files, 10.5 GB, **5.6 min** (149,140 rows/s) |
| Upload | **28.6 min** at 6.3 MB/s, 0 failures |
| Ingestion | **50,000,000 / 50,000,000 rows** |
| Delta table | 6 commits, 4 data files, `_delta_log` + V-Order `_index_bin` |

Two behaviours confirmed exactly as documented:

* Files 1-15 were consumed and moved to `_FilesReadyToDelete`, with
  `00000000000000000016.parquet` **left behind** as the sequence reference.
* That validated the sequencing fix from section 22: the remote listing showed
  only file 16 and the persisted local counter also said 16, so both agreed on
  17 as next. Relying on the folder listing alone would have been fine here, but
  only by luck.

The CDC replicator then shipped its first change file correctly:

```
00000000000000000017.parquet   3 changes  (ins=1 upd=1 del=1)   29.0 KB
```

29 KB against the seed's 700 MB files. That size difference is the whole point:
the seed is a one-off baseline, the stream is incremental.

---

## 26. Two expensive lessons

### 26.1 The CDC parquet schema must match the seed's schema exactly

Fabric rejected file 17:

```
ErrorCode: SchemaMergeFailure ... Type mismatch for column '_mirror_row_id'.
Incoming type: 'string', existing type: 'long'
```

The seed went through DuckDB, which mapped the `bigint` surrogate key to
`int64`, so Delta holds it as `long`. The replicator wrote **every** column as
`pa.string()`, including the key. Delta refused to merge.

Fixed by deriving arrow types from `information_schema.columns` rather than
assuming everything is text, and coercing decoded values accordingly. All 100
business columns genuinely are text; only the surrogate key is not, but
deriving the mapping keeps it correct if that ever changes.

**The general rule: an open-mirroring change file must match the materialised
table's schema exactly, not just its column names.** The seed decides the types,
and everything after it has to agree.

### 26.2 stopMirroring / startMirroring DROPS the mirrored tables

This one cost a full re-upload.

The earlier latched `PathNotFound` error was cleared by stopping and starting
the mirroring engine, and that looked like a cheap, clever recovery. It worked
because **no table had been materialised yet**: the engine simply re-read the
landing zone and built one.

Using the same trick to clear the `SchemaMergeFailure` **deleted the
50,000,000-row Delta table**: 0 data files, 0 `_delta_log` commits. The already
consumed seed files had been removed from `_FilesReadyToDelete`, so there was
nothing left in the landing zone to rebuild from.

**`stopMirroring` is not an error-recovery mechanism. It is destructive once
data is materialised.** The documented recovery for a latched error is to delete
and recreate the table folder, which also implies re-uploading. Both routes cost
a full re-seed, so the real lesson is to avoid the error in the first place.

Which is now enforced: the schemas are compared **locally**, before any upload.

```
SEED parquet : 101 fields, non-string: [('_mirror_row_id','int64')]
CDC writer   : 101 fields + __rowMarker__, non-string: [('_mirror_row_id','int64')]
MISMATCHES   : NONE
ORDER MATCHES: True
```

Recovery was possible only because the 11 GB of staged parquet still existed on
`D:`. Keeping the staging directory until the mirror is verified is not
optional.

### 26.3 Sequence gaps

Deleting the rejected file 17 left a gap, and the replicator moved on to 18.
The spec requires continuous numbering, and Fabric did not consume 18. The
documented escape hatch is `"fileDetectionStrategy": "LastUpdateTimeFileDetection"`
in `_metadata.json`, which reads files by timestamp instead. Here the sequence
counter was simply reset to 16 so the re-seed occupies 1-16 and CDC resumes at
17 with no gap.

---

## 27. Phase 1 proven end to end

Re-seeded and verified. The engine restart was safe this time because the Delta
table was confirmed **empty first** (0 data files, 0 log commits) rather than
assumed to be.

| Step | Result |
| --- | --- |
| Re-upload | 10.5 GB, 29.1 min, 0 failures |
| Schema preflight | `--check-schema` OK: 101 fields, `int64` key, order matches |
| Re-seed ingested | **50,000,000 rows** |
| CDC file 17 | 3 changes (ins=1 upd=1 del=1), 29.0 KB |
| CDC file 18 | 1 change (upd=1), 29.1 KB |
| Mirroring errors | **0** |
| `processedRows` | 50,000,000 -> **50,000,003** |

### The proof

Reading the mirrored table through `delta_scan()`, which applies the
transaction log:

```
TOTAL LIVE ROWS: 50,000,000

7777777   PROOF-UPDATE-MERCHANT  424242.42  PROOF-CHANGED   <- UPDATED in place
50000005  MIRROR TEST INSERT     12345.67   CDC-INSERTED    <- INSERTED
3870726   (absent)                                          <- DELETED
```

Arithmetic closes exactly: 50,000,000 seed + 1 insert - 1 delete = 50,000,000.

**The update and the delete are the entire argument.** A file copy can only
append. It cannot make an existing row change its values, and it cannot make a
row disappear. Both happened, driven by the PostgreSQL write-ahead log.

### Reading a Delta table wrong, and how it looks

Worth recording because it produces a convincing false negative. The first
verification read the **raw parquet files** and appeared to show the mirror
broken:

```
7777777  PROOF-UPDATE-MERCHANT ...   <- new version
7777777  AGODA.COM ...               <- old version STILL THERE
3870726  ... SETTLED                 <- "deleted" row STILL THERE
```

Nothing was wrong. Delta keeps superseded files on disk until `VACUUM`, and the
`_delta_log` is the only thing that says which are live. Reading the parquet
directly bypasses the log and returns every version ever written. `delta_scan()`
applies the log and returns the correct 50,000,000.

Anyone validating a lakehouse by globbing parquet files will conclude their
pipeline is duplicating and failing to delete, and will be wrong.

---

## 28. Phase 1 summary

```
on-prem PostgreSQL 16
  -> logical replication slot (test_decoding)
  -> parse WAL changes
  -> zstd parquet with __rowMarker__ as the final column
  -> azcopy into the open mirroring landing zone
  -> Fabric replication engine
  -> Delta table in OneLake, insert / update / delete applied
```

| Stage | Measurement |
| --- | --- |
| Generate | 50,000,000 x 100 messy text columns, 45.0 GB, 35 min, 42,500 rows/s |
| Load to PostgreSQL | 48 GB, 10.9 min, 76,465 rows/s |
| Surrogate key + PK | 21.5 min (19.5 rewrite + 1.4 index, 4 parallel workers) |
| Export to parquet | 10.5 GB, 5.6 min, 149,140 rows/s, 4.3x zstd |
| Upload to OneLake | 29 min, ~6.3 MB/s via azcopy |
| Fabric ingestion | 50,000,000 rows |
| CDC latency | change visible in Fabric within ~2 min of commit |
| CDC file size | 29 KB per batch against 700 MB seed files |

---

## 29. Current state

**Done**

- 50,000,000 rows x 100 messy text columns generated (45.0 GB, 35 min)
- Loaded into `landing.raw_txn` (48 GB, all TEXT, LOGGED, `bigdata` tablespace on `D:`), 10.9 min at 76,465 rows/s
- Integrity verified: exact row count, NULL vs empty string preserved, 593,209 duplicate `txn_id`s intact
- Open mirroring proven end to end on a 200k trial: `Replicating`, real Delta table with `_delta_log` and V-Order index
- `wal_level = logical` active, PostgreSQL tuned
- azcopy installed, authenticated, ~9.4 MB/s to OneLake
- `cdc_to_fabric.py` written
- Everything pushed to `https://github.com/sulaiman013/fabric-x-duckdb`

**In progress**

- `ALTER TABLE ... ADD COLUMN _mirror_row_id` rewriting 48 GB

**Next**

1. Restart PostgreSQL to pick up `shared_buffers = 8GB` and `max_worker_processes = 20`
2. `cdc_to_fabric.py --setup` to create the `fabric_cdc` slot (only after the rewrite, so the slot does not pin rewrite WAL)
3. `cdc_to_fabric.py --run` to start streaming
4. Issue INSERT / UPDATE / DELETE in PostgreSQL and verify in Fabric that rows appear, change and disappear

---

## 30. Phase 2: gold layer at full scale

Built the complete star schema over all 50,000,000 rows.

| Metric | Value |
| --- | --- |
| Scored | 50,000,000 |
| Deduped | 49,406,790 |
| Removed | **593,210 (1.19%)** |
| Null foreign keys | **0** across all six dimensions |
| Gold output | 1.9 GB parquet, 9 tables |
| Risk bands | 73.2% low, 23.9% medium, 2.9% high |

The deduplication count is an independent validation: 593,210 rows removed
against the 593,209 duplicate `txn_id` values measured directly in PostgreSQL.
The extra one is the insert made during the CDC proof.

### Two failures worth keeping

**A surrogate key that cost 38 GiB.** The first full run died with
`OutOfMemoryException` after exhausting 38.3 GiB of spill. `fact_alert` minted an
`alert_key` using `row_number() OVER (ORDER BY _mirror_row_id, rule_id)`, which
is a global sort over roughly 48,000,000 alert rows. On the 2M test slice that
sort is trivial; at full scale it is fatal. `(_mirror_row_id, rule_id)` was
already unique by construction, so the surrogate identified nothing the natural
key did not and cost a full sort to produce. Removed.

The general lesson: adding a surrogate key is a reflex in dimensional modelling,
and it is the wrong reflex when the natural key is already unique and the
surrogate requires ordering the whole table to generate.

**DuckDB's temp directory follows the database file.** That meant spilling to
`C:` with 43 GB free rather than `D:` with 479 GB. Fine on a single-volume
machine, wrong here, and it only shows up once a query spills more than the
smaller volume holds. Now set explicitly.

### Rule calibration does not survive a change of scale

Fire rates measured on 2,000,000 rows did not hold at 50,000,000:

| Rule | 2M | 50M | Window dependent |
| --- | --- | --- | --- |
| R06 new_merchant | 1.12% | **27.55%** | yes |
| R03 amount_anomaly | 0.94% | **7.34%** | yes |
| R05 velocity | 1.20% | 1.75% | yes |
| R02 card_not_present | 20.48% | 20.48% | no |
| R04 odd_hour | 20.63% | 20.57% | no |
| R07 high_risk_mcc | 4.28% | 4.30% | no |
| R09 declined | 49.69% | 49.75% | no |

The four rules with no window dependency held to two decimal places. The three
that depend on per-customer history moved, and R06 moved 25 times over.

The cause is structural rather than statistical. R06 and R03 are gated on
history depth, `cust_txn_count >= 20` and five or more transactions
respectively, and history depth is a function of how much of the population is
in the sample. On 2M rows almost no customer had twenty transactions; on 50M
many do.

Which means the earlier recalibration of R06, from 85.88% down to a comfortable
1.12%, was measured on a sample that could not support the rule being tested.
At full scale it is back to 27.55% and is arguably too common again.

**Any rule whose definition references a window over an entity must be
calibrated on the full population, not a slice.** Row-level rules can be tuned
on a sample; history-dependent ones cannot.

---

## 31. Gold layer landed in Fabric

| Step | Result |
| --- | --- |
| Gold parquet uploaded | 9 files, **1.86 GB in 4.0 min**, 0 failures |
| Spark V-Order write | **3 min 22 s** on capacity |
| Delta tables in OneLake | 9 tables, 79 files, **2.5 GB** |

The upload is worth comparing against the bronze seed: 1.86 GB in four minutes
here, against 10.5 GB in twenty-nine minutes for the raw landing data. The gold
layer is roughly five times smaller than the bronze it derives from, because
typing and conforming lets the parquet encoder do its job on columns that were
previously all strings.

### Deploying a notebook through the CLI

Two failures worth recording, both of which produce an opaque error.

**Fabric's import expects `.ipynb` JSON.** The `notebook-content.py` source
format that appears in git-integrated workspaces is rejected outright:

```
InvalidNotebookContent: Failed to cast json string to type: IPythonNotebook
```

**The default lakehouse must be declared in notebook metadata.** Under
`metadata.dependencies.lakehouse`, giving `default_lakehouse`,
`default_lakehouse_name` and `default_lakehouse_workspace_id`. Without it an
API-triggered run has no lakehouse context, so every relative path such as
`Files/gold` and every `saveAsTable` fails. The notebook only works if a human
opens it and attaches a lakehouse by hand, which defeats the point of triggering
it from CI.

### The V-Order split, in practice

DuckDB cannot produce V-Order, writes Delta INSERT-only with no MERGE or schema
evolution, and never writes checkpoints, so a table written entirely by DuckDB
accumulates an unbounded transaction log. Splitting on that boundary, DuckDB for
the transformation and Spark for the write, took **3 minutes 22 seconds** of
Spark time for 49.4M rows across nine tables. That is a small price for keeping
the analytical work in DuckDB while still getting a Direct Lake ready layout.

---

## 32. Gold verified on capacity, not assumed

Setting `spark.sql.parquet.vorder.enabled` and seeing the write succeed does not
prove V-Order landed. `fab job run` returns job status rather than cell output,
so a verification notebook writes its findings to `Files/verify.json`, which is
then read back over the storage API. That pattern is worth keeping: it is the
only way to get real output out of a CLI-triggered notebook run.

| Table | Rows | Files | Size |
| --- | --- | --- | --- |
| `gold_fact_transaction` | **49,406,790** | 13 | 2,103.8 MB |
| `gold_fact_alert` | 65,088,689 | 8 | 354.7 MB |
| `gold_dim_customer` | 5,112,692 | 8 | 80.4 MB |
| `gold_dim_card` | 588,132 | 1 | 3.9 MB |
| `gold_dim_merchant` | 250,003 | 1 | 2.9 MB |
| `gold_dim_channel` | 120 | 1 | 0.0 MB |
| `gold_dim_date` | 905 | 1 | 0.0 MB |
| `gold_dim_time` | 25 | 1 | 0.0 MB |
| `gold_dim_risk_rule` | 7 | 1 | 0.0 MB |

**V-Order confirmed.** `delta.parquet.vorder.enabled = "true"` is present as a
table property on all nine tables. Note that `spark.conf.get` for the session
setting returned `null` in the verifying session, which is the point: the
session that wrote the tables is gone, and the only durable evidence is the
property recorded on the table itself. Checking the session conf would have
proved nothing.

**Referential integrity across 49,406,790 rows: 0 orphan customer keys, 0
merchant, 0 date.** The Unknown members added in section 30 are doing their job.

Risk bands survived the write intact: 36,165,109 low, 11,832,925 medium,
1,408,756 high.

### Making a CLI-run notebook fail safely

The first verification run died with
`System_Cancelled_Session_Statements_Failed`: one statement raised, and Spark
cancelled the whole session, so every other check was lost along with it.
Rewritten so each check runs inside its own `attempt()` wrapper and records its
own error. A verification script that cannot survive one failing check verifies
nothing.

---

## 33. Phase 3: Direct Lake semantic model

Authored as TMDL rather than generated. The bundled `create_direct_lake_model.py`
helper builds a single-table model; a nine-table star with relationships and
measures has to be written.

| Element | Count |
| --- | --- |
| Tables, all `mode: directLake` | 9 |
| Relationships | 8 |
| Measures | 13 |

Direct Lake is not a preference here. The write-back design in section 9 of
`APP_DESIGN.md` depends on an analyst's disposition being visible immediately,
and an import-mode model only reflects a write after a refresh.

`discourageImplicitMeasures` is set so authors use the defined measures instead
of dragging raw columns onto visuals. Surrogate keys are `summarizeBy: none`,
because summing a key is meaningless and is a reliable way for a model to
produce confident nonsense.

### Three failures getting it deployed

**TMDL is indentation sensitive.** A multi-line DAX measure body indented with
spaces rather than tabs fails the whole import with nothing but
`Invalid indentation was detected` and a line number. The measure was collapsed
onto one line.

**The SQL endpoint lags Delta table creation.** The first DAX query failed with
`Invalid object name 'gold_fact_transaction'` even though the Delta tables were
visibly present in OneLake. Direct Lake resolves entity names through the
lakehouse SQL endpoint, and that endpoint syncs its metadata asynchronously.
`POST /workspaces/{ws}/sqlEndpoints/{id}/refreshMetadata` forces it; the call
itself timed out at 240 seconds but the sync completed and the next query
returned.

**`fab get` is not supported on a SQLEndpoint item.** Endpoint properties have
to be read from the parent lakehouse's `sqlEndpointProperties` instead.

### Verified over Direct Lake, no import

| Measure | Value |
| --- | --- |
| Transactions | **49,406,790** |
| High Risk Transactions | 1,408,756 |
| High Risk Rate | 2.85% |
| Alerts | 65,088,689 |
| Alert Fire Rate | **80.18%** |
| Distinct Customers | 5,112,692 |
| Average Risk Score | 19.74 |
| Approval Rate | 39.38% |

### An 80% alert rate is a finding, not a success

The model is computing correctly. The rules are not fit for purpose.

An alert fire rate of 80.18% means four transactions in five raise at least one
alert. No financial crime function can triage that; it is the definition of
alert fatigue, and in a real bank it would bury the 2.85% that are genuinely
high risk.

The cause is the two loosest rules: `R09 declined` fires on 49.75% and
`R06 new_merchant` on 27.55% at full scale. Both were judged acceptable on a
2,000,000 row slice and neither is acceptable now.

Fixing this properly means raising thresholds until the alert rate lands
somewhere a team could actually work, conventionally a low single-digit
percentage, and then measuring what that costs in missed high-risk
transactions. That is a precision and recall trade-off, and it needs the
simulated outcome label from section 6 of `APP_DESIGN.md` to be measurable at
all. Recorded here rather than quietly tuned away.

---

## 34. Fixing the alert rate: it was a modelling error, not a threshold

Researched how the industry measures this before touching the thresholds.

Published benchmarks put rule-based transaction monitoring at **90-95% false
positives**, a PwC figure cited consistently since 2018, with legacy rule-only
systems running 97-99% and well-tuned AI-augmented systems reaching 80-85%. A
compliance analyst clears roughly **50,000 alerts per year**.

That last number is the useful one, because it converts a percentage into
headcount:

| Design | Alert rate | Alerts | Analyst-years | FTE analysts |
| --- | --- | --- | --- | --- |
| Any rule fires | 80.18% | 39,614,364 | 792 | **317** |
| Score >= 60 | 2.85% | 1,408,756 | 28.2 | **11** |

**The defect was conceptual, not numeric.** I had defined an alert as "any rule
fired". Real transaction monitoring raises an alert when the composite score
crosses a threshold; an individual rule firing is a contribution to that score,
not a work item someone picks up. `fact_alert` was conflating the two, so every
rule contribution was being counted as a piece of work.

Raising rule thresholds would have treated the symptom. The fix is to alert on
the score.

### Measures after the fix

| Measure | Value |
| --- | --- |
| Alerts Raised | 1,408,756 |
| Alert Rate | **2.85%** |
| Analyst Years to Clear | **28.2** |
| Rule Firings | 65,088,689 |
| Rule Firings per Alert | **46.2** |
| Any Rule Rate | 80.18% |

The 80.18% figure is kept, renamed **Any Rule Rate**, because it is a real
property of the rule set and hiding it would be dishonest. It just is not the
alert rate. `Rule Firings per Alert` at 46.2 quantifies what the scoring absorbs:
46 rule contributions distilled into one work item.

### Analyst Years to Clear

Added deliberately. A threshold argument conducted in percentages is aesthetic;
conducted in headcount it is decidable. 2.85% sounds acceptable and 80% sounds
bad, but the sentence that settles a tuning decision is "this threshold needs
eleven analysts and that one needs three hundred and seventeen".

Sources: PwC false positive benchmark via FluxForce and Tookitaki industry
reviews, analyst throughput figure from the same.

---

## 35. Pricing the threshold: precision, recall and headcount

Rule effectiveness needs ground truth and this source has none, so
`scripts/threshold_analysis.py` generates a simulated confirmed-fraud label as a
probabilistic function of `risk_score`, seeded from `_mirror_row_id` so the same
row always draws the same outcome. Calibrated to a 0.083% overall fraud rate,
which is the order of magnitude usually quoted for card fraud.

Stated as simulated wherever it appears. Without it, precision and recall are not
computable and a threshold can only be asserted.

| Threshold | Alerts | Alert % | Precision | Recall | FP rate | Analyst-yrs | FTE |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 39,613,473 | 80.18% | 0.101% | 97.2% | 99.9% | 792.3 | 317 |
| 20 | 23,528,614 | 47.62% | 0.160% | 91.4% | 99.8% | 470.6 | 188 |
| 30 | 13,241,681 | 26.80% | 0.250% | **80.5%** | 99.8% | 264.8 | **106** |
| 40 | 7,078,109 | 14.33% | 0.367% | 63.3% | 99.6% | 141.6 | 57 |
| 50 | 3,533,239 | 7.15% | 0.534% | 46.0% | 99.5% | 70.7 | 28 |
| **60** | **1,408,756** | **2.85%** | 0.806% | **27.6%** | 99.2% | 28.2 | **11** |
| 70 | 441,474 | 0.89% | 1.173% | 12.6% | 98.8% | 8.8 | 4 |
| 80 | 181,393 | 0.37% | 1.487% | 6.6% | 98.5% | 3.6 | 1 |
| 90 | 50,937 | 0.10% | 2.122% | 2.6% | 97.9% | 1.0 | 0 |

### What the curve says

**A 99% false-positive rate is normal here, not a defect.** Published benchmarks
put legacy rule-only transaction monitoring at 97-99% false positives, and every
threshold in this table lands in that band. The model is behaving like the real
thing rather than failing.

**The threshold chosen earlier catches 27.6% of fraud.** That is the honest price
of an eleven-analyst function. Catching 80% means dropping to threshold 30, which
needs 106 analysts: roughly ten times the people for three times the detection.

**There is no comfortable answer**, which is the actual finding. Every row of
this table is a real institution's staffing decision, and the reason AML teams
run at 90-95% false positives is that the alternative is missing most of the
fraud.

### Caveat that belongs next to the numbers

Precision never exceeds 2.1%, and that ceiling is partly a property of the
simulated label: it was calibrated to a 0.083% base rate, so absolute precision
is bounded by that choice rather than measured from reality.

What is trustworthy is the **shape**. Precision rises monotonically with the
threshold, recall falls, and the headcount curve is steeply non-linear. Those
relationships are what a threshold decision turns on, and they would hold under
any sensible base rate. The absolute precision figures would not.

---

## 36. End-to-end UAT

A structured pass over every phase, with each check either passing on evidence
or producing a fix. Nothing was taken from an earlier section on trust.

### Phase 1: mirroring

| Check | Result |
| --- | --- |
| Replicator process alive | PASS: one genuine `python.exe` (pid 29456) |
| Replication slot | PASS: `fabric_cdc`, 56 bytes WAL retained |
| `wal_level` / `synchronous_commit` | PASS: `logical` / `on` |
| Mirror status | PASS: `Replicating`, no error |
| **Live change propagates** | **PASS**: one UPDATE plus one INSERT in PostgreSQL, `processedRows` 50,000,004 to **50,000,006** in Fabric |

A first process check matched eight PIDs and looked like eight competing
replicators, which would have been a serious defect: multiple consumers of one
slot produce duplicate sequence numbers or lost changes. Filtering by
executable showed seven were shell wrappers. The check now filters on
`Name='python.exe'`.

### Phase 2: transformation

| Check | Result |
| --- | --- |
| Parser tests | PASS: 8/8 |
| All 14 scripts parse | PASS |
| `--check-schema` preflight | PASS |
| Gold row parity | PASS: 49,406,790 = 50,000,000 minus 593,210, exact |
| Orphan merchant keys in gold | PASS: 0 |
| Deleted proof row absent from gold | PASS: 3870726 absent |
| Inserted proof row present | PASS, with an explanation below |

Row 50000005 was missing from gold and looked like a defect. It is correct
behaviour: the first CDC demo attempt inserted an identical
`TXN-CDC-INSERT-0001` as row 50000004, so 50000005 is an exact duplicate on
every business column and dedup kept the lower id. The test expectation was
wrong, not the pipeline.

### Phase 3: semantic model

| Check | Result |
| --- | --- |
| All 17 measures resolve | PASS |
| Relationships filter | PASS: per-rule breakdown matches `star.py` to the row |
| **Direct Lake reconciles to DuckDB** | **PASS**: Total Amount 17,808,657,055.84 on both, to the cent |
| Rule firings | PASS: 65,088,689 on both |

Filtering High Risk Rate by `channel` is flat, 2.850% to 2.851% across every
channel. That is the uniform source data, not the model: channel and entry
mode are independent draws, and the rules key on entry mode. Already recorded
in `APP_DESIGN.md` section 7. The demo must not chart risk by channel.

### Phase 4: application

| Check | Result |
| --- | --- |
| HTML demo figures | **FAIL, fixed**: predated the score-driven alerting fix |

The demo still carried the pre-fix numbers and had no representation of the
corrected model. Now shows the DAX-verified measures (1,408,756 alerts raised,
2.85%, 28.2 analyst-years, 80.18% labelled as any-rule rate) and the threshold
table with recall and headcount per cut-off.

### Documentation

| Check | Result |
| --- | --- |
| `APP_DESIGN.md` rule table | PASS: seven active, two struck through |
| `README.md` rule count and script inventory | **FAIL, fixed**: said nine rules, omitted `transform.py`, `rules.py`, `star.py`, `build_semantic_model.py`, `threshold_analysis.py`, no Phase 3 |
| **`README.md` load instructions** | **FAIL, fixed**: said the table is created **UNLOGGED** |

The UNLOGGED claim was the most dangerous finding of the pass. The table was
loaded `--logged` deliberately, because logical replication never captures an
UNLOGGED table. Anyone following the README as written would have built a
mirror whose CDC silently saw nothing.

### Repository hygiene

| Check | Result |
| --- | --- |
| Credentials file ignored | PASS |
| Secrets in tracked files | PASS: 0 |
| Uncommitted changes before UAT | PASS: 0 |

### One more catch, from checking before publishing

The demo edits were run through `node --check` before republishing rather than
trusting them. That found an unescaped apostrophe in `institution's` inside a
single-quoted JavaScript string, which would have shipped a page that renders
nothing. Rephrased to avoid the quote. Cheap check, real save.

### Verdict

Every functional check passed on live evidence. Three defects were found, all
documentation or presentation rather than pipeline, and all fixed: a stale
demo, a stale README inventory, and one README instruction that would have
broken CDC for a reader.

## 37. Phase 4 research: the Fabric App is region-blocked, and the probe proved it

Researched how to build a Fabric App, then stopped reading and probed the
tenant, because a note in memory from June said East US was blocked for Fabric
Apps and East US is now supported. Region tables go stale.

### The probe

Four `POST /workspaces/{ws}/items` calls with different type names:

| Type | Response |
| --- | --- |
| `App` | 400 `InvalidItemType` |
| `FabricApp` | 400 `InvalidItemType` |
| `DataApp` | 400 `InvalidItemType` |
| **`AppBackend`** | **403 `FeatureNotAvailable`** |

That contrast is the entire diagnostic, and it is worth more than the docs. Three
invented names are rejected as *invalid types*. The fourth is recognised as a
real type and then refused as an *unavailable feature*. So the item type is
`AppBackend`, the name is right, and something other than naming is refusing it.

### Ruling out the tenant settings

Both settings the docs name as prerequisites were already on:

| Setting | State |
| --- | --- |
| `AppBackendTenant` (Enable Fabric App Items, preview) | enabled |
| `DatasetExecuteQueries` (Semantic Model Execute Queries REST API) | enabled |

So the 403 is not a tenant setting. It is the region. `capacityRegion` is
**UK South**, which the published table lists as "Not available: Fabric App
(preview)". Both capacities on the tenant are UK South, and the trial capacity
was created today, so starting a fresh trial would land in UK South again: trial
region follows tenant home region. There is no free way around it.

### What is available here, also by probe

| Type | Response |
| --- | --- |
| `UserDataFunction` | 201 Created |
| `SQLDatabase` | 202 Accepted |

Both probe items were deleted immediately after the test. This is the finding
that matters, because the write-back design in `APP_DESIGN.md` section 9 needs
exactly those two item types and they work here today. The operational half of
Phase 4 is not blocked. Only the application shell is.

### The consequence, which turned out to be good news

The `dataapp` template reads its semantic model over the Execute DAX Queries
REST API. That is an authenticated network call, not a OneLake-local read, so
the app does not have to sit in the same region as the data. An `AppBackend` in
a supported region can query `fincrime_model` in UK South.

Only the thin shell moves. The 49.4M-row gold layer, the Direct Lake model and
the mirror stay where they are, and the 29-minute seed is never repeated.

### Plan

Written up in `FABRIC_APP_PLAN.md`: nine steps, of which steps 1 to 4 (Fabric
SQL database, User Data Functions, proving write-back, confirming the automatic
OneLake mirror) are unblocked and can start now. Step 5 is a capacity in a
supported region and is the only step gated on a decision.

The part worth building is the closed loop. A Fabric SQL database auto-mirrors
to OneLake as Delta with no configuration, so a disposition written through a
User Data Function becomes data in the lake, which the next gold rebuild can
join back to `fact_alert`. Alert precision then stops being simulated against a
seeded label and starts being measured against what analysts actually decided.
