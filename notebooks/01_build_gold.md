# Notebook: build the gold layer in Fabric

Cell-by-cell content for the Fabric **Python** notebook (not Spark) that runs
Phase 2 on capacity. The transformation logic is imported from `scripts/`
rather than pasted in, so the code that was validated against the real 50M rows
on a laptop is literally the code that runs here.

Attach the **`fincrime`** Lakehouse as the default lakehouse. The mirrored table
is already shortcut into it at `Tables/raw_txn`.

---

## Cell 1: compute

```python
%%configure
{
    "vCores": 8
}
```

The Python kernel defaults to 2 vCores / 16 GB and scales to 64. Eight is the
documented sweet spot for this data size, and it matters: Microsoft's own
benchmark bands put 10-13 GB compressed as the range where single-machine
engines start hitting out-of-memory at lower vCore counts. This dataset is
10.5 GB compressed.

---

## Cell 2: dependencies

```python
%pip install --quiet duckdb

import duckdb, time
print("duckdb", duckdb.__version__)
```

DuckDB, Polars and delta-rs are preinstalled in the Python runtime, but pinning
an explicit install avoids surprises when the runtime image moves.

---

## Cell 3: bring the validated logic in

```python
import sys, os
# scripts/ uploaded to the notebook's builtin resources folder
sys.path.insert(0, "/lakehouse/default/Files/scripts")

from transform import silver_sql
from rules import RULES, enriched_sql, scored_sql
from star import build

print("rules active:", [r[0] for r in RULES])
```

---

## Cell 4: read the mirror through the shortcut

```python
con = duckdb.connect()
con.execute("SET memory_limit='48GB'")        # 8 vCores carries ~64 GB
con.execute("SET preserve_insertion_order=false")
con.execute("SET temp_directory='/tmp/duckdb'")   # spill target
con.execute("INSTALL delta"); con.execute("LOAD delta")

SRC = "delta_scan('/lakehouse/default/Tables/raw_txn')"

t0 = time.time()
n = con.execute(f"SELECT count(*) FROM {SRC}").fetchone()[0]
print(f"source rows: {n:,}  ({time.time()-t0:.1f}s)")
```

The shortcut resolves to the mirrored database's Delta table. It is read-only,
which is correct: nothing in this notebook should be able to write back into
the mirror.

---

## Cell 5: build

```python
t0 = time.time()
build(con, SRC)
print(f"star built in {(time.time()-t0)/60:.1f} min")

for t in ("fact_transaction","fact_alert","dim_customer","dim_merchant",
          "dim_channel","dim_card","dim_date","dim_time","dim_risk_rule"):
    print(f"  {t:<18} {con.execute(f'SELECT count(*) FROM {t}').fetchone()[0]:>12,}")
```

---

## Cell 6: write gold as Parquet

```python
GOLD = "/lakehouse/default/Files/gold"
os.makedirs(GOLD, exist_ok=True)

for t in ("fact_transaction","fact_alert","dim_customer","dim_merchant",
          "dim_channel","dim_card","dim_date","dim_time","dim_risk_rule"):
    con.execute(f"COPY {t} TO '{GOLD}/{t}.parquet' (FORMAT PARQUET, COMPRESSION zstd)")
print("gold parquet written")
```

---

## Cell 7: the V-Order handoff

DuckDB cannot produce V-Order, and V-Order is what makes a Direct Lake model
fast. DuckDB also writes Delta **INSERT-only**, with no MERGE and no schema
evolution, and never writes checkpoints, so a table written entirely by DuckDB
accumulates an unbounded transaction log.

So the final write is handed to Spark. This is a deliberate split, not a
workaround: DuckDB does the transformation, which is the interesting and
CPU-bound part, and Spark does the write, which is where V-Order lives.

Run this in a **separate Spark notebook** against the same lakehouse:

```python
spark.conf.set("spark.sql.parquet.vorder.enabled", "true")

for t in ["fact_transaction","fact_alert","dim_customer","dim_merchant",
          "dim_channel","dim_card","dim_date","dim_time","dim_risk_rule"]:
    (spark.read.parquet(f"Files/gold/{t}.parquet")
          .write.mode("overwrite").format("delta")
          .save(f"Tables/gold_{t}"))
    print(t, "written with V-Order")
```

The alternative, accepting non-V-Ordered gold tables, is defensible for a small
model but should be a measured decision rather than an accident. Worth
benchmarking both before Phase 3 commits.

---

## What this notebook deliberately does not do

* **No write-back.** The mirror is read-only and the gold tables are derived.
  Analyst decisions go to a Fabric SQL database through user data functions,
  per section 9 of `APP_DESIGN.md`.
* **No cleaning of the landing table.** `raw_txn` stays exactly as PostgreSQL
  holds it, mess included. Every correction happens downstream where it can be
  inspected and reversed.
