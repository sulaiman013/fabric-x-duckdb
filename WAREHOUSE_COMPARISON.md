# DuckDB on a Python notebook, against Fabric Data Warehouse

The same job two ways: turn mirrored rows of text into a V-Ordered star schema
that Direct Lake can serve.

- **The DuckDB route**, which this repository built: a Python notebook runs
  DuckDB over the mirror and writes parquet, and a Spark job rewrites that
  parquet as V-Ordered Delta.
- **The Warehouse route**: a Fabric Warehouse reads the mirror with a
  cross-database query and builds the same tables in T-SQL.

Researched 21 September 2026. Rates are quoted from Microsoft Learn and the
Azure retail prices API, linked at the end. The Warehouse measurements come
from a separate production pilot, described below and anonymised.

---

## The short answer

**For this kind of workload the Warehouse costs roughly an order of magnitude
more, and that is measured, not modelled.**

A production pilot ran the same transformations both ways on one capacity, for
the same tables, in September 2026, after Microsoft's August repricing of
Warehouse compute. Per engine-second the Warehouse billed about **60 CU-s**
against the notebook's **4**. Rebuilding three fact tables from scratch cost
about **9,800 CU-s** on the Warehouse and **260** in the notebook.

The reason is not the rate. Since August a Warehouse vCore costs 0.538 CU, close
to a notebook's 0.5, and most published comparisons that predate the change
overstate the Warehouse's price about 3.7 times. The reason is **what gets
billed**:

- **The notebook bills the vCores you chose, and only while it executes.**
  Session start is not billed (Microsoft Learn, and observed in the pilot).
- **The Warehouse bills every vNode the engine chooses to allocate, per second,
  idle included.** In the pilot a 6-second run that did nothing cost about
  370 CU-s, and a warehouse that merely existed billed about 840 CU-s an hour in
  background work.

The Warehouse is faster on a large whole-table build, and it has no memory
ceiling. For scoped rebuilds and a daily full load that fit on one node, those
advantages do not pay for what it holds.

This repository's own job has not been run on a Warehouse. At the pilot's
~60 CU-s per engine-second, a Warehouse would have to do the whole of it in
**82 engine-seconds** to match what the DuckDB route billed.

---

## The evidence, and how much weight each part carries

| | status | source |
|---|---|---|
| DuckDB route, this repository | **measured** | `UAT.json`, and job wall times from the jobs API |
| Warehouse against DuckDB, same tables, same capacity | **measured, elsewhere** | a production pilot, anonymised, below |
| Price per CU-hour | **quoted** | Azure retail prices API, 21 Sep 2026 |
| CU per vCore, and what each engine bills | **quoted** | Microsoft Learn |
| This repository's job on a Warehouse | **not run** | the pilot is the nearest measurement |

### The pilot

A production data platform, anonymised here: an F16 capacity, several dozen
transformation models over about fifty mirrored tables, incremental loads every
five minutes and one full rebuild a day. It ran first as T-SQL stored
procedures in a Fabric Warehouse, then as DuckDB in a Python notebook, on the
same capacity for the same tables, in September 2026.

| measured in the pilot | Warehouse, T-SQL | DuckDB, Python notebook | ratio |
|---|---|---|---|
| CU-s per engine-second | about 50 to 65 | 4, at 8 vCores | about 15x |
| three fact tables, one 5-minute cycle | about 1,260 CU-s | 82 to 123 CU-s | 10 to 15x |
| three fact tables, rebuilt from scratch | about 9,800 CU-s | about 260 CU-s | about 38x |
| every table every 5 minutes, one day | about 2.1 million CU-s, 150% of the F16, projected | 174,940 CU-s, 12.7% of the F16, measured | about 12x |
| a run that did nothing | about 370 CU-s for 6 seconds | nothing between runs | |
| existing, idle | about 840 CU-s an hour | nothing | |
| one large whole-table build | **14 s** | 84 to 90 s | the Warehouse is faster |

Two things from the pilot's history matter as much as the table. The
Warehouse could not meet the brief: 60% of the F16 bought about 40 to 48 engine
seconds per five-minute cycle for every table together, and every-table
freshness would have needed about four times that. And one night, a full
rebuild of every fact every five minutes ran at 225 to 260% of the F16 and
throttled every report on the capacity. The notebook then ran 351 times in a
day with none failed and no throttling.

---

## How each engine bills

| | Python notebook | Spark notebook | Fabric Warehouse |
|---|---|---|---|
| unit | vCores you choose | vCores in the pool | vNodes the engine allocates (1 vNode = 4 vCores) |
| CU per vCore | 0.5 | 0.5 | 0.538, and 2.0 before August 2026 |
| billed while | executing; session start is not billed | executing | a vNode is allocated, busy or waiting |
| minimum | none observed between runs | none | a one-minute allocation window per workspace |
| who sizes it | you | you | the engine |
| costs while idle | nothing | nothing | background work while the warehouse exists |
| type, smoothing | background, 24 hours | background, 24 hours | background, 24 hours |
| price, UK South | $0.21 / CU-h | $0.21 / CU-h | $0.21 / CU-h |

Every meter in a region costs the same per CU-hour, so price never decides
this. CU-hours consumed does, and what each engine counts as consumed is the
whole difference.

Microsoft Learn says Warehouse compute is "allocated using a one-minute baseline
allocation window" and "measured and reported per second based on the number of
allocated vNodes". For notebooks it says billing covers the time "the notebook
session is active" and excludes "the time taken to personalize the session".

---

## The DuckDB route, measured

| step | CU | billed time | CU-seconds | CU-hours |
|---|---|---|---|---|
| DuckDB transformation, Python, 8 vCores | 4 | 770.6 s executing | 3,082 | 0.856 |
| V-Order write, Spark starter pool | 8 | at most 233 s | at most 1,864 | at most 0.518 |
| **route total** | | | **at most 4,946** | **at most 1.374** |

| region | per full rebuild |
|---|---|
| UK South, where this capacity runs | **at most $0.29** |
| East US | at most $0.25 |

The V-Order figure is an upper bound because the only time recorded for that
job is its wall time, which includes a start that is not billed.

The V-Order step is up to 38% of the route's cost, and the Warehouse would not
need it. DuckDB 1.2.2 cannot write V-Order and Direct Lake depends on it, so
this route pays a second engine to rewrite files the first engine already
wrote. It is still far cheaper than a Warehouse doing the whole job at the
pilot's rate.

---

## Capacity usage

Both routes are background operations, so Fabric spreads a run's CU across the
following 24 hours. As a share of each SKU's daily budget:

| SKU | this route, one rebuild | rebuilds before the day is spent | a parked Warehouse, per day, at the pilot's rate |
|---|---|---|---|
| F2 | 2.86% | 34 | **11.7%** |
| F4 | 1.43% | 69 | 5.8% |
| F8 | 0.72% | 139 | 2.9% |
| F16 | 0.36% | 279 | 1.5% |
| F64 | 0.09% | 1,117 | 0.4% |

The last column is the cost of a Warehouse doing nothing. On the smallest SKU a
parked Warehouse, at the pilot's observed rate, costs four times this whole
pipeline's nightly rebuild. That background work depends on what the warehouse
holds, so the figure is the pilot's, not a prediction for this data.

**Both routes fit on an F2.** An F2 bursts Spark to 20 vCores, enough for the
8-vCore notebook and, separately, the 16-vCore V-Order job. A Warehouse on an F2
may burst to 32 times its baseline for one query, which is how it can run at
several times a capacity's rate and throttle everything else on it.

---

## Time

| | DuckDB route | Warehouse |
|---|---|---|
| this repository's transformation | 770.6 s executing, measured | not run |
| one large whole-table build, pilot | 84 to 90 s | **14 s** |
| a scoped 5-minute rebuild, pilot | 16 to 25 s for a table pair | not a scoped operation there |

The Warehouse wins on raw speed: a distributed engine is faster on brute
force. Under allocation billing faster is not cheaper, because every vNode that
made it fast is billed. The pilot's conclusion was cheap beats fast when the
work is small, and most five-minute work is small.

---

## Efficiency, this repository

| | |
|---|---|
| rows per second, transformation | 64,885 |
| CU-seconds per million source rows, whole route | at most 98.9 |
| cost per million source rows, UK South | at most $0.0058 |

---

## Beyond cost

### Where the Warehouse is stronger

- **Raw speed on large whole-table builds**, measured in the pilot.
- **No memory ceiling.** It scales out. A notebook stops at 64 vCores on one
  node, and the pilot lost a full load on a 16 GB session before restructuring
  it.
- **One engine.** V-Order is on by default for every Warehouse write, so there
  is no second job and no intermediate parquet.
- **No timezone trap.** This repository lost a night to DuckDB's `to_timestamp`
  returning `TIMESTAMPTZ`, which made laptop and Fabric builds disagree by six
  hours on epoch rows (BUILD_LOG section 40). `datetime2` has no time zone.
- **Governance and skills.** Row-level and column-level security, dynamic data
  masking, and T-SQL, which most BI teams already write.

### Where DuckDB is stronger

- **It bills like a program, not a database.** Executing time at a size you
  chose, nothing between runs, nothing while idle.
- **It reads the lake directly.** DuckDB reads the mirror's Delta files with a
  pinned snapshot per run, and can read the Delta log itself to find what
  changed: the pilot read the newest change stamp for fifty tables from Delta
  statistics in 1.6 seconds, without scanning a row. Through a Warehouse every
  read of the mirror is billed as warehouse time.
- **It makes incremental design possible.** Scope tables, date-bounded
  semi-joins, pinned snapshots and Delta merges pruned to the dates involved
  are things a program can do and a stored procedure cannot. They are why a
  five-minute run in the pilot touches a few thousand rows and not hundreds of
  millions.
- **Modern SQL.** The pilot hit these Warehouse T-SQL limits on the way: no
  `FORMAT()`, no `regexp_replace`, `STRING_AGG` that cannot correlate, an
  unreliable `@@DATEFIRST`, system views refused in distributed mode, and DDL
  silently rolled back without autocommit. Microsoft Learn lists the `REGEXP_*`
  family for SQL database in Fabric but not for Warehouse.
- **It runs on a laptop.** `transform.py` was developed locally at no capacity
  cost. Every iteration of a T-SQL port spends capacity.

### DuckDB's honest limits

One process means one run at a time. There is a memory ceiling to respect: in
the pilot a sorted write once peaked at 13.2 GB. And there is no scale-out: if
the source grew several times over, the answer is a bigger session or a split
load, not a cluster.

### What ports from this repository's DuckDB to T-SQL

| DuckDB | T-SQL on Warehouse |
|---|---|
| `try_strptime` over five date formats | `TRY_CONVERT(date, x, style)` with styles 23, 103, 101, 104, and 6 after swapping dashes for spaces. **Ports.** |
| strip `RM`, `USD` and other prefixes by regex | `SUBSTRING(x, PATINDEX('%[0-9(-]%', x), 50)`. **Ports.** |
| detect a bare epoch with `^[0-9]{9,11}$` | `x NOT LIKE '%[^0-9]%' AND LEN(x) BETWEEN 9 AND 11`. **Ports.** |
| collapse runs of whitespace with `\s+` | a nested `REPLACE` idiom that handles spaces, not tabs or newlines. **Ports, with a gap.** |
| `make_timestamp` from an epoch | `DATEADD(second, x, '1970-01-01')`. **Ports, and safer.** |
| `ROW_NUMBER()` deduplication | identical. |

---

## Corrections this research forces on the repository

1. **BUILD_LOG.md**: *"A Warehouse T-SQL path would also need the rows copied
   into warehouse storage first."* **False.** A Warehouse reads a mirrored
   database in the same workspace through a three-part name, with no copy.
2. **"Capacity bills a notebook for its session wall time, startup
   included"**, in README section 6 and BUILD_LOG. **False.** Microsoft Learn
   excludes session start, and the pilot observed the same. The cost table
   priced 895 s for a transformation that billed 770.6. `UAT.json` already had
   the right figure: 3,082.4 CU-seconds.
3. **$0.27 per rebuild**, in the README, the architecture diagram, the film and
   its thumbnail. It priced wall time at the East US rate. Corrected for both,
   this capacity's figure is **at most $0.29**. The two errors pull in opposite
   directions and nearly cancel, which is luck, not accuracy. Corrected since in
   the README, the architecture diagram, and the website's blog post and case
   study. The film and its thumbnail still show $0.27.
4. **"Why this is cheaper than doing it in T-SQL"**, the heading of README
   section 6. It was only ever modelled against Spark. It is now supported, but
   by the pilot's measurements rather than this repository's.

---

## Sources

- [Fabric operations](https://learn.microsoft.com/fabric/enterprise/fabric-operations): 1 Warehouse core = 0.538 CU; 2 Spark vCores = 1 CU; both are background operations.
- [Warehouse consumption and utilization](https://learn.microsoft.com/fabric/data-warehouse/usage-reporting): vNode = 4 vCores; consumption is allocated vNodes per second; one-minute baseline allocation window; background system work is billed.
- [Apache Spark billing and utilization](https://learn.microsoft.com/fabric/data-engineering/billing-capacity-management-for-spark) and [Apache Spark compute overview](https://learn.microsoft.com/fabric/data-engineering/spark-compute#starter-pools): billed only while the session is active, excluding session personalization and idle pool time.
- [Burstable capacity in Fabric Data Warehouse](https://learn.microsoft.com/fabric/data-warehouse/burstable-capacity): F2 bursts 32x, F4 16x, F8 and above 12x.
- [Fabric capacity throttling policy](https://learn.microsoft.com/fabric/enterprise/throttling): 24-hour smoothing of background operations.
- [Choosing a notebook kernel](https://learn.microsoft.com/fabric/data-engineering/fabric-notebook-selection-guide): Python kernel 2 vCores = 1 CU, up to 64 vCores.
- [Concurrency limits and queueing in Apache Spark](https://learn.microsoft.com/fabric/data-engineering/spark-job-concurrency-and-queueing): F2 bursts to 20 Spark vCores.
- [Query the warehouse: cross-database queries](https://learn.microsoft.com/fabric/data-warehouse/query-warehouse#write-a-cross-database-query): three-part names across databases in one workspace.
- [Understand V-Order for Fabric Warehouse](https://learn.microsoft.com/fabric/data-warehouse/v-order): on by default; Direct Lake depends on it.
- [REGEXP_REPLACE (Transact-SQL)](https://learn.microsoft.com/sql/t-sql/functions/regexp-replace-transact-sql): applies-to list excludes Fabric Warehouse.
- [Azure retail prices API](https://prices.azure.com/api/retail/prices), queried 21 September 2026: $0.21 per CU-hour in UK South, $0.18 in East US, on every Fabric meter.
- [The One-Minute Trap](https://dev.to/gilbert_lelon_8352bf20997/the-one-minute-trap-what-microsoft-fabrics-new-warehouse-billing-model-means-for-your-workloads-1ojb), Gilbert Lelon: the repricing took effect in August 2026.
- A production pilot, anonymised: Warehouse and DuckDB measured on one F16 capacity for the same tables, September 2026.
