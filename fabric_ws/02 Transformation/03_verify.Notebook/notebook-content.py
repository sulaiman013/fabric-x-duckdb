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

# CELL ********************

import json, traceback
TABLES = ["fact_transaction","fact_alert","dim_customer","dim_merchant",
          "dim_channel","dim_card","dim_date","dim_time","dim_risk_rule"]
out = {"tables": {}, "checks": {}, "errors": {}}

def attempt(name, fn):
    try:
        out["checks"][name] = fn()
    except Exception as e:
        out["errors"][name] = f"{type(e).__name__}: {e}"[:300]

for t in TABLES:
    try:
        d = spark.sql(f"DESCRIBE DETAIL gold_{t}").collect()[0].asDict()
        n = spark.sql(f"SELECT count(*) c FROM gold_{t}").collect()[0]["c"]
        out["tables"][t] = {"rows": n, "numFiles": d.get("numFiles"),
                            "sizeMB": round((d.get("sizeInBytes") or 0)/1048576,1)}
    except Exception as e:
        out["tables"][t] = {"error": f"{type(e).__name__}: {e}"[:200]}

def vorder_props():
    r = {}
    for t in TABLES:
        rows = spark.sql(f"SHOW TBLPROPERTIES gold_{t}").collect()
        hit = {x[0]: x[1] for x in rows if "vorder" in str(x[0]).lower()}
        r[t] = hit or "no vorder property listed"
    return r
attempt("vorder_tblproperties", vorder_props)

def session_conf():
    try:
        return spark.conf.get("spark.sql.parquet.vorder.enabled")
    except Exception:
        return "unset in this session"
attempt("vorder_session_conf", session_conf)

def orphans():
    return spark.sql("""
      SELECT sum(CASE WHEN c.customer_key IS NULL THEN 1 ELSE 0 END) bad_customer,
             sum(CASE WHEN m.merchant_key IS NULL THEN 1 ELSE 0 END) bad_merchant,
             sum(CASE WHEN d.date_key     IS NULL THEN 1 ELSE 0 END) bad_date,
             count(*) total
      FROM gold_fact_transaction f
      LEFT JOIN gold_dim_customer c ON c.customer_key = f.customer_key
      LEFT JOIN gold_dim_merchant m ON m.merchant_key = f.merchant_key
      LEFT JOIN gold_dim_date     d ON d.date_key     = f.date_key
    """).collect()[0].asDict()
attempt("orphan_keys", orphans)

def bands():
    return [r.asDict() for r in spark.sql(
      "SELECT risk_band, count(*) n FROM gold_fact_transaction GROUP BY 1 ORDER BY 2 DESC").collect()]
attempt("risk_bands", bands)

def cols():
    return [f.name for f in spark.table("gold_fact_transaction").schema.fields]
attempt("fact_columns", cols)

with open("/lakehouse/default/Files/verify.json","w") as f:
    json.dump(out, f, indent=1, default=str)
print("written. errors:", list(out["errors"].keys()))
print(json.dumps(out["tables"], indent=1, default=str))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
