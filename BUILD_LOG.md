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

1. **1B rows** — flagged that this meant ~100 GB CSV plus ~100 GB in Postgres,
   and that `C:` could not hold either.
2. **250M rows** — then the shape changed: no star schema, no transformation,
   a single wide flat table of ~100 columns of raw messy data.
3. **50M rows** — final. At 100 columns this is ~45 GB CSV, which fits
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

### 5.3 Entity incoherence — the important one

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
**public**. Caught before any commit or push — nothing left the machine.

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

- `sulaiman-postgres.MirroredDatabase` (`5069602e-...`) — status **Running**
- `sulaiman-postgres.SQLEndpoint` — provisioned

Pulled the authoritative open-mirroring spec from Microsoft Learn rather than
assuming. The rules that matter:

1. `_metadata.json` in each table folder declaring `keyColumns`. Without it,
   Fabric will not ingest.
2. Data files named `00000000000000000001.parquet` — 20 digits, zero padded,
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
| `fab cp` local to MirroredDatabase | **Fails** — `Source and destination must be of the same type` |
| `fab api -A storage` with a full OneLake URL | **Fails** — `artifact type is unknown` |
| `fab api -A storage` with `ws.Workspace/item.MirroredDatabase` | **Fails** — resolves internally to `MountedRelationalDatabase`, not found |
| `fab api -A storage` with `{workspaceId}/{itemId}` GUIDs | **Works** — 200, lists and deletes fine |
| `fab api` three-step ADLS create/append/flush | Create 201, append 202, but **flush fails**; `-i` does not send binary file contents |
| `fab cp` to a Lakehouse | **Works**, byte-exact (627 = 627) |
| `fab cp` of a 216 MB file | **Times out after 246s** — single-shot upload, no chunking |
| **azcopy** with `--trusted-microsoft-suffixes` | **Works** — 216 MB in **40s** |

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
measured **46,541,460 bytes — byte-identical to local**. Fabric still failed:

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

## 24. Current state

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
