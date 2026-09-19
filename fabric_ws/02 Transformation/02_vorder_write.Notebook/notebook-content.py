# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
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

# MARKDOWN ********************

# ## Write the gold tables as Delta with V-Order
# 
# DuckDB produced the gold parquet in `Files/gold`. It cannot produce V-Order,
# writes Delta INSERT-only with no MERGE, and never writes checkpoints, so the
# final write is handed to Spark. Deliberate split: DuckDB does the
# transformation, Spark does the write, because V-Order is what makes a Direct
# Lake model fast.

# CELL ********************

spark.conf.set("spark.sql.parquet.vorder.enabled", "true")
spark.conf.set("spark.microsoft.delta.optimizeWrite.enabled", "true")

TABLES = ["fact_transaction", "fact_alert", "dim_customer", "dim_merchant",
          "dim_channel", "dim_card", "dim_date", "dim_time", "dim_risk_rule"]

import time
for t in TABLES:
    t0 = time.time()
    df = spark.read.parquet(f"Files/gold/{t}.parquet")
    n = df.count()
    (df.write.mode("overwrite").format("delta")
       .option("parquet.vorder.enabled", "true")
       .saveAsTable(f"gold_{t}"))
    print(f"{t:<20} {n:>12,} rows  {time.time()-t0:6.1f}s")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Verify V-Order landed rather than assuming the conf took effect
for t in TABLES:
    d = spark.sql(f"DESCRIBE DETAIL gold_{t}").collect()[0]
    print(f"{t:<20} files={d['numFiles']:>5}  size={d['sizeInBytes']/1048576:>9,.1f} MB")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# The fact must reconcile, and no key may fail to resolve to a dimension
n = spark.sql("SELECT count(*) c FROM gold_fact_transaction").collect()[0]["c"]
print(f"fact_transaction rows: {n:,}")

o = spark.sql("""
  SELECT sum(CASE WHEN c.customer_key IS NULL THEN 1 ELSE 0 END) AS bad_customer,
         sum(CASE WHEN m.merchant_key IS NULL THEN 1 ELSE 0 END) AS bad_merchant,
         sum(CASE WHEN d.date_key     IS NULL THEN 1 ELSE 0 END) AS bad_date
  FROM gold_fact_transaction f
  LEFT JOIN gold_dim_customer c ON c.customer_key = f.customer_key
  LEFT JOIN gold_dim_merchant m ON m.merchant_key = f.merchant_key
  LEFT JOIN gold_dim_date     d ON d.date_key     = f.date_key
""").collect()[0]
print("orphan keys:", o.asDict())

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
