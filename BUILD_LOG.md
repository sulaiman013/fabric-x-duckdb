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

## 14. Current state

**Done**

- 50,000,000 rows x 100 messy text columns generated to `D:/duckdb-fabric-data/csv` (45.0 GB)
- Loaded into `landing.raw_txn` in PostgreSQL 16 (48 GB, all TEXT, LOGGED, on the `bigdata` tablespace)
- Integrity verified, mess and duplicates preserved
- Scripts and README pushed to `https://github.com/sulaiman013/fabric-x-duckdb`
- Fabric authenticated, workspace and mirrored database identified, open-mirroring spec confirmed
- azcopy installed, authenticated, and proven against OneLake

**Blocked / pending**

1. **PostgreSQL restart required.** `wal_level=logical`, `max_wal_size=4GB` and
   `checkpoint_timeout=15min` are staged via `ALTER SYSTEM` but need a restart,
   which needs Administrator:
   ```
   Restart-Service postgresql-x64-16 -Force
   ```
   Until then `wal_level` is still `replica` and logical replication is not possible.

2. **Initial snapshot to Fabric.** Export `landing.raw_txn` to zstd Parquet in
   mirroring-compliant files and azcopy them into
   `Files/LandingZone/raw_txn/`, with `_metadata.json` and no `__rowMarker__`.

3. **Open question: which column is the mirroring key.** `txn_id` has **593,209
   duplicates** by design. Duplicates are harmless for the initial load (inserts
   do not deduplicate), but they make `txn_id` unsafe as `keyColumns` for CDC
   upserts, since an update would be ambiguous across duplicate rows. Needs a
   decision before enabling incremental changes.
