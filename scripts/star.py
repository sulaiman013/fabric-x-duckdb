"""
Phase 2 gold layer: dimensions and facts for the Financial Crime Ops model.

  python star.py --limit 2000000            # build and profile locally
  python star.py --limit 2000000 --out D:/duckdb-fabric-data/gold

Grain decisions, which are the part worth arguing about
-------------------------------------------------------
* `fact_transaction` is one row per `_mirror_row_id`. That is the surrogate key
  added so PostgreSQL would emit UPDATE and DELETE, and it is also the join key
  the write-back layer uses to tie an analyst's decision to a transaction. Using
  anything else would break that chain.
* `fact_alert` is one row per rule firing, not per transaction. A transaction
  that trips three rules produces three alert rows. That is what makes "which
  rules earn their keep" answerable without unpivoting at query time.
* Duplicates are resolved here, not earlier. The 593,209 exact duplicate rows
  are real source behaviour and belong in the landing layer untouched; the fact
  table is where a defensible single version is chosen.
"""

import argparse
import os
import sys
import time

import duckdb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from transform import silver_sql          # noqa: E402
from rules import RULES, enriched_sql, scored_sql  # noqa: E402


def export_source(con, table):
    """
    What COPY reads when a gold table is exported to parquet.

    Naive TIMESTAMP columns are cast to TIMESTAMPTZ. The session is pinned to
    UTC, so the instant equals the naive value read as UTC, and the parquet
    carries isAdjustedToUTC=true. Spark reads that as an ordinary timestamp; a
    naive column it reads as TIMESTAMP_NTZ, which the existing Delta tables do
    not accept and Direct Lake does not serve. BUILD_LOG section 40.
    """
    cols = [r[0] for r in con.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = ? AND data_type = 'TIMESTAMP' ORDER BY ordinal_position",
        [table]).fetchall()]
    if not cols:
        return table
    rep = ", ".join("CAST(%s AS TIMESTAMPTZ) AS %s" % (c, c) for c in cols)
    return "(SELECT * REPLACE (%s) FROM %s)" % (rep, table)


def build(con, src):
    con.execute("CREATE OR REPLACE TABLE scored AS "
                + scored_sql(enriched_sql(silver_sql(src))))

    # ---- deduplicate -----------------------------------------------------
    # Exact duplicates share every business column. Keep the lowest
    # _mirror_row_id as the survivor: it is stable, reproducible, and points at
    # the first time the row was seen.
    con.execute("""
      CREATE OR REPLACE TABLE deduped AS
      SELECT * EXCLUDE (rn) FROM (
        SELECT *, row_number() OVER (
          PARTITION BY txn_id, txn_amount, merchant_name, txn_ts
          ORDER BY _mirror_row_id) AS rn
        FROM scored)
      WHERE rn = 1
    """)

    # ---- dimensions ------------------------------------------------------
    con.execute("""
      CREATE OR REPLACE TABLE dim_date AS
      SELECT row_number() OVER (ORDER BY d) AS date_key, d AS full_date,
             year(d) AS yr, quarter(d) AS qtr, month(d) AS mth,
             strftime(d,'%b') AS month_name, day(d) AS day_of_month,
             dayofweek(d) AS day_of_week, strftime(d,'%a') AS day_name,
             CASE WHEN dayofweek(d) IN (0,6) THEN TRUE ELSE FALSE END AS is_weekend
      FROM (SELECT DISTINCT CAST(txn_ts AS DATE) d FROM deduped WHERE txn_ts IS NOT NULL)
      ORDER BY d
    """)
    con.execute("""
      CREATE OR REPLACE TABLE dim_time AS
      SELECT h AS time_key, h AS hour_of_day,
             printf('%02d:00', h) AS hour_label,
             CASE WHEN h BETWEEN 1 AND 5 THEN 'Overnight'
                  WHEN h BETWEEN 6 AND 11 THEN 'Morning'
                  WHEN h BETWEEN 12 AND 17 THEN 'Afternoon'
                  ELSE 'Evening' END AS day_part,
             CASE WHEN h BETWEEN 1 AND 5 THEN TRUE ELSE FALSE END AS is_odd_hour
      FROM range(0,24) t(h)
    """)
    con.execute("""
      CREATE OR REPLACE TABLE dim_customer AS
      SELECT row_number() OVER (ORDER BY customer_id) AS customer_key, *
      FROM (
        SELECT customer_id,
               any_value(first_name) AS first_name,
               any_value(last_name)  AS last_name,
               any_value(gender)     AS gender,
               any_value(date_of_birth) AS date_of_birth,
               any_value(occupation) AS occupation,
               any_value(addr_city)  AS addr_city,
               any_value(addr_state) AS addr_state,
               any_value(nationality) AS nationality,
               -- worst-case wins: a customer flagged once stays flagged
               max(CASE WHEN kyc_status='VERIFIED' THEN 0 WHEN kyc_status IS NULL THEN 1
                        ELSE 2 END) AS kyc_rank,
               max(CASE WHEN pep_flag THEN 1 ELSE 0 END)::BOOLEAN AS ever_pep,
               max(CASE WHEN sanctions_hit THEN 1 ELSE 0 END)::BOOLEAN AS ever_sanctioned,
               max(CASE WHEN risk_rating='HIGH' THEN 3 WHEN risk_rating='MEDIUM' THEN 2
                        WHEN risk_rating='LOW' THEN 1 ELSE 0 END) AS risk_rank,
               count(*) AS txn_count
        FROM deduped WHERE customer_id IS NOT NULL GROUP BY customer_id)
    """)
    con.execute("""
      CREATE OR REPLACE TABLE dim_merchant AS
      SELECT row_number() OVER (ORDER BY merchant_id) AS merchant_key, *,
             CASE WHEN merchant_mcc IN ('6011','4829','7995') THEN TRUE ELSE FALSE END
               AS is_high_risk_mcc
      FROM (
        SELECT merchant_id,
               any_value(merchant_name) AS merchant_name,
               any_value(merchant_mcc)  AS merchant_mcc,
               any_value(merchant_country) AS merchant_country,
               count(*) AS txn_count
        FROM deduped WHERE merchant_id IS NOT NULL GROUP BY merchant_id)
    """)
    con.execute("""
      CREATE OR REPLACE TABLE dim_channel AS
      SELECT row_number() OVER (ORDER BY channel, entry_mode) AS channel_key,
             channel, entry_mode,
             CASE WHEN entry_mode IN ('ECOM','E-COMMERCE','KEYED','MANUAL')
                  THEN TRUE ELSE FALSE END AS is_card_not_present
      FROM (SELECT DISTINCT channel, entry_mode FROM deduped
            WHERE channel IS NOT NULL OR entry_mode IS NOT NULL)
    """)
    con.execute("""
      CREATE OR REPLACE TABLE dim_card AS
      SELECT row_number() OVER (ORDER BY card_bin, card_brand) AS card_key,
             card_bin, card_brand
      FROM (SELECT DISTINCT card_bin, card_brand FROM deduped
            WHERE card_bin IS NOT NULL OR card_brand IS NOT NULL)
    """)
    rule_rows = ",".join("('%s','%s',%d)" % (rid, name, w) for rid, name, _, w in RULES)
    con.execute("""
      CREATE OR REPLACE TABLE dim_risk_rule AS
      SELECT * FROM (VALUES %s) AS t(rule_id, rule_name, weight)
    """ % rule_rows)


    # ---- unknown members -------------------------------------------------
    # A NULL foreign key silently drops the row out of any aggregate that
    # filters on that dimension, so 14% of transactions would disappear from a
    # merchant-sliced total without anyone noticing. Every dimension gets an
    # explicit Unknown member at key -1 and the fact coalesces to it.
    con.execute("INSERT INTO dim_customer SELECT -1,'UNKNOWN',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,1,FALSE,FALSE,0,0")
    con.execute("INSERT INTO dim_merchant SELECT -1,'UNKNOWN','Unknown merchant',NULL,NULL,0,FALSE")
    con.execute("INSERT INTO dim_channel  SELECT -1,'UNKNOWN','UNKNOWN',FALSE")
    con.execute("INSERT INTO dim_card     SELECT -1,'UNKNOWN','UNKNOWN'")
    con.execute("INSERT INTO dim_date     SELECT -1,NULL,NULL,NULL,NULL,'Unknown',NULL,NULL,'Unknown',FALSE")
    con.execute("INSERT INTO dim_time     SELECT -1,-1,'Unknown','Unknown',FALSE")

    # ---- facts -----------------------------------------------------------
    con.execute("""
      CREATE OR REPLACE TABLE fact_transaction AS
      SELECT
        d._mirror_row_id,
        d.txn_id,
        coalesce(dd.date_key,   -1) AS date_key,
        coalesce(dt.time_key,   -1) AS time_key,
        coalesce(c.customer_key,-1) AS customer_key,
        coalesce(m.merchant_key,-1) AS merchant_key,
        coalesce(ch.channel_key,-1) AS channel_key,
        coalesce(cd.card_key,   -1) AS card_key,
        d.txn_ts, d.txn_type, d.txn_status,
        d.txn_amount, d.txn_currency, d.amount_local, d.fee_amount,
        d.auth_approved, d.risk_score, d.rules_fired,
        CASE WHEN d.risk_score >= 60 THEN 'HIGH'
             WHEN d.risk_score >= 30 THEN 'MEDIUM' ELSE 'LOW' END AS risk_band
      FROM deduped d
      LEFT JOIN dim_date     dd ON dd.full_date = CAST(d.txn_ts AS DATE)
      LEFT JOIN dim_time     dt ON dt.time_key  = hour(d.txn_ts)
      LEFT JOIN dim_customer c  ON c.customer_id = d.customer_id
      LEFT JOIN dim_merchant m  ON m.merchant_id = d.merchant_id
      LEFT JOIN dim_channel  ch ON ch.channel IS NOT DISTINCT FROM d.channel
                               AND ch.entry_mode IS NOT DISTINCT FROM d.entry_mode
      LEFT JOIN dim_card     cd ON cd.card_bin IS NOT DISTINCT FROM d.card_bin
                               AND cd.card_brand IS NOT DISTINCT FROM d.card_brand
    """)

    # one row per rule firing, so rule effectiveness is a group-by not an unpivot
    union = "\n UNION ALL ".join(
        "SELECT _mirror_row_id, '%s' AS rule_id, %d AS weight FROM deduped WHERE %s"
        % (rid, w, name) for rid, name, _, w in RULES)
    # No surrogate key here. (_mirror_row_id, rule_id) is already unique by
    # construction, and minting an ordered alert_key meant a global sort over
    # ~48,000,000 rows, which exhausted 38 GiB of spill space and killed the
    # build. A surrogate that costs a full sort and identifies nothing the
    # natural key does not is not worth having.
    con.execute("CREATE OR REPLACE TABLE fact_alert AS SELECT * FROM (%s)" % union)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=2000000)
    p.add_argument("--out", default="")
    p.add_argument("--memory-limit", default="10GB")
    p.add_argument("--temp-dir", default="D:/duckdb-fabric-data/tmp")
    p.add_argument("--host", default="localhost")
    p.add_argument("--dbname", default="postgres")
    p.add_argument("--user", default="postgres")
    args = p.parse_args()

    con = duckdb.connect()
    con.execute("SET memory_limit='%s'" % args.memory_limit)
    con.execute("SET preserve_insertion_order=false")
    con.execute("SET TimeZone='UTC'")   # results must not depend on where this runs
    # Spill to D:. The default temp directory follows the database file, which
    # here means C: with 43 GB free against D:'s 479 GB.
    con.execute("SET temp_directory='%s'" % args.temp_dir)
    con.execute("INSTALL postgres"); con.execute("LOAD postgres")
    con.execute("ATTACH 'host=%s dbname=%s user=%s' AS pg (TYPE postgres, READ_ONLY)"
                % (args.host, args.dbname, args.user))
    src = "pg.landing.raw_txn"
    if args.limit:
        # Deterministic slice. LIMIT without ORDER BY is nondeterministic over a
        # parallel scan: two runs returned samples differing by 23,008 duplicate
        # txn_ids, which made every measurement irreproducible. Ranging over the
        # surrogate key gives the same rows every time.
        src = "(SELECT * FROM %s WHERE _mirror_row_id <= %d)" % (src, args.limit)

    t0 = time.time()
    build(con, src)
    print("star built in %.1f s" % (time.time() - t0))

    print("\nTABLE SIZES")
    for t in ("fact_transaction", "fact_alert", "dim_customer", "dim_merchant",
              "dim_channel", "dim_card", "dim_date", "dim_time", "dim_risk_rule"):
        n = con.execute("SELECT count(*) FROM %s" % t).fetchone()[0]
        print("  %-18s %12s" % (t, "{:,}".format(n)))

    raw, ded = con.execute("SELECT (SELECT count(*) FROM scored), "
                           "(SELECT count(*) FROM deduped)").fetchone()
    print("\nDEDUPLICATION\n  scored {:,} -> deduped {:,}, removed {:,} ({:.2f}%)".format(
        raw, ded, raw - ded, 100.0 * (raw - ded) / raw))

    print("\nREFERENTIAL INTEGRITY (unmatched dimension keys in the fact)")
    for k in ("date_key", "time_key", "customer_key", "merchant_key", "channel_key", "card_key"):
        miss = con.execute("SELECT round(100.0*sum(CASE WHEN %s = -1 THEN 1 ELSE 0 END)"
                           "/count(*),2) FROM fact_transaction" % k).fetchone()[0]
        nulls = con.execute("SELECT sum(CASE WHEN %s IS NULL THEN 1 ELSE 0 END) "
                            "FROM fact_transaction" % k).fetchone()[0]
        print("  %-14s %6s%% unknown, %s null FKs" % (k, miss, nulls))

    print("\nRISK BAND MIX")
    for b, n, pct in con.execute("""
        SELECT risk_band, count(*), round(100.0*count(*)/sum(count(*)) OVER (),1)
        FROM fact_transaction GROUP BY 1 ORDER BY 2 DESC""").fetchall():
        print("  %-7s %10s  %5s%%" % (b, "{:,}".format(n), pct))

    print("\nRULE EFFECTIVENESS (from fact_alert, a group-by not an unpivot)")
    for rid, name, n, pct in con.execute("""
        SELECT a.rule_id, r.rule_name, count(*),
               round(100.0*count(*)/(SELECT count(*) FROM fact_transaction),2)
        FROM fact_alert a JOIN dim_risk_rule r USING (rule_id)
        GROUP BY 1,2 ORDER BY 3 DESC""").fetchall():
        print("  %-5s %-18s %10s alerts  %6s%% of txns" % (rid, name, "{:,}".format(n), pct))

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        for t in ("fact_transaction", "fact_alert", "dim_customer", "dim_merchant",
                  "dim_channel", "dim_card", "dim_date", "dim_time", "dim_risk_rule"):
            con.execute("COPY %s TO '%s/%s.parquet' (FORMAT PARQUET, COMPRESSION zstd)"
                        % (export_source(con, t), args.out.replace('\\', '/'), t))
        print("\ngold written to %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
