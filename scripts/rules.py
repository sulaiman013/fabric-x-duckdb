"""
Phase 2 risk layer: the nine rules from APP_DESIGN.md, over conformed silver.

  python rules.py --limit 2000000

Why these rules exist at all
---------------------------
The source `fraud_score` column is uncorrelated with everything. Measured on the
raw table it sits between 29.9 and 31.2 across every single channel, so a chart
built on it shows fraud spread perfectly evenly and is worthless.

These rules are computed instead, from columns that genuinely vary. The score is
their weighted sum, so it has a real distribution and correlates with its own
drivers by construction.

A rule that fires on most rows carries no information, however sound it sounds.
This module measures each rule's fire rate and lift so that can be judged rather
than assumed, and reports which rules should be dropped.
"""

import argparse
import os
import sys
import time

import duckdb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from transform import silver_sql  # noqa: E402

# Weight is how much a firing rule adds to the score. Rare, specific signals are
# worth more than common ones; these are starting weights, recalibrated below
# against the fire rates this module measures.
# Four of the original nine were measured against the real data and dropped or
# recalibrated. A rule that fires on four rows in five cannot rank anything,
# however sound it sounds in a policy document.
#   R01 cross_border  fired on 80.22%. Currency is uniform in this source, so
#                     the rule carries no information. DROPPED.
#   R06 new_merchant  fired on 85.88%. Most customer/merchant pairs here are
#                     unique, so "first time" is the normal case. Restricted to
#                     customers with enough history for it to mean something.
#   R05 velocity      fired on 0.01% at three per account-hour. Lowered to two.
#   R08 round_amount  fired on 0.00%. Amounts come from a continuous
#                     distribution and are essentially never exact hundreds.
#                     DROPPED.
RULES = [
    ("R02", "card_not_present",  "entry_mode IN ('ECOM','E-COMMERCE','KEYED','MANUAL')", 25),
    ("R03", "amount_anomaly",    "amt_pct_in_customer >= 0.95", 30),
    ("R04", "odd_hour",          "txn_hour BETWEEN 1 AND 5", 15),
    ("R05", "velocity",          "acct_txns_same_hour >= 2", 30),
    ("R06", "new_merchant",      "first_seen_merchant AND cust_txn_count >= 20", 10),
    ("R07", "high_risk_mcc",     "merchant_mcc IN ('6011','4829','7995')", 25),
    ("R09", "declined",          "auth_approved = FALSE", 10),
]


def enriched_sql(silver):
    """Window features the rules need. One pass over the silver table."""
    return """
SELECT *,
  hour(txn_ts) AS txn_hour,
  -- where this amount sits inside this customer's own spending history.
  -- NULL for a customer with a single transaction, which correctly means
  -- "no basis to call it anomalous" rather than "not anomalous".
  CASE WHEN customer_id IS NULL OR txn_amount IS NULL THEN NULL
       WHEN count(*) OVER (PARTITION BY customer_id) < 5 THEN NULL
       ELSE percent_rank() OVER (PARTITION BY customer_id ORDER BY txn_amount)
  END AS amt_pct_in_customer,
  -- transactions on the same account inside the same clock hour
  count(*) OVER (PARTITION BY account_no, date_trunc('hour', txn_ts))
       AS acct_txns_same_hour,
  -- how much history this customer has, so "first time at this merchant" is
  -- only treated as a signal where there was a pattern to depart from
  count(*) OVER (PARTITION BY customer_id) AS cust_txn_count,
  -- first time this customer transacted at this merchant
  CASE WHEN customer_id IS NULL OR merchant_id IS NULL THEN FALSE
       ELSE row_number() OVER (PARTITION BY customer_id, merchant_id ORDER BY txn_ts) = 1
  END AS first_seen_merchant
FROM ({s})
""".format(s=silver)


def scored_sql(enriched):
    flags = ",\n  ".join(
        "CASE WHEN {c} THEN TRUE ELSE FALSE END AS {n}".format(c=cond, n=name)
        for _, name, cond, _ in RULES)
    score = " + ".join(
        "CASE WHEN {c} THEN {w} ELSE 0 END".format(c=cond, w=w)
        for _, _, cond, w in RULES)
    fired = " + ".join(
        "CASE WHEN {c} THEN 1 ELSE 0 END".format(c=cond) for _, _, cond, _ in RULES)
    return """
SELECT *,
  {flags},
  ({score}) AS risk_score,
  ({fired}) AS rules_fired
FROM ({e})
""".format(flags=flags, score=score, fired=fired, e=enriched)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=2000000)
    p.add_argument("--memory-limit", default="10GB")
    p.add_argument("--host", default="localhost")
    p.add_argument("--dbname", default="postgres")
    p.add_argument("--user", default="postgres")
    args = p.parse_args()

    con = duckdb.connect()
    con.execute("SET memory_limit='%s'" % args.memory_limit)
    con.execute("SET preserve_insertion_order=false")
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
    con.execute("CREATE OR REPLACE TABLE scored AS "
                + scored_sql(enriched_sql(silver_sql(src))))
    n = con.execute("SELECT count(*) FROM scored").fetchone()[0]
    print("scored: {:,} rows in {:.1f}s".format(n, time.time() - t0))

    print("\nRULE FIRE RATES")
    print("  a rule firing on most rows cannot discriminate, however sensible it sounds")
    rates = {}
    for rid, name, _, w in RULES:
        r = con.execute("SELECT round(100.0*sum(CASE WHEN {n} THEN 1 ELSE 0 END)/count(*),2) "
                        "FROM scored".format(n=name)).fetchone()[0]
        rates[rid] = r
        verdict = "too common" if r > 50 else ("too rare" if r < 0.5 else "usable")
        print("  %-4s %-18s %7s%%  weight %-3s  %s" % (rid, name, r, w, verdict))

    print("\nRISK SCORE DISTRIBUTION")
    rows = con.execute("""
      SELECT CASE WHEN risk_score < 20 THEN '  0-19' WHEN risk_score < 40 THEN ' 20-39'
                  WHEN risk_score < 60 THEN ' 40-59' WHEN risk_score < 80 THEN ' 60-79'
                  ELSE '80+' END AS band,
             count(*) n, round(100.0*count(*)/sum(count(*)) OVER (),1) pct
      FROM scored GROUP BY 1 ORDER BY 1""").fetchall()
    for b, c, pct in rows:
        bar = "#" * int(round(pct / 2))
        print("  %-6s %9s  %5s%%  %s" % (b, "{:,}".format(c), pct, bar))

    stats = con.execute("SELECT min(risk_score), round(avg(risk_score),1), "
                        "max(risk_score), round(stddev(risk_score),1) FROM scored").fetchone()
    print("  min %s  mean %s  max %s  stddev %s" % stats)

    print("\nDOES THE SCORE CORRELATE WITH ITS OWN DRIVERS?")
    print("  share of each rule firing, inside the top decile vs the bottom decile")
    for rid, name, _, _ in RULES:
        hi, lo = con.execute("""
          SELECT round(100.0*avg(CASE WHEN {n} THEN 1.0 ELSE 0 END) FILTER (WHERE risk_score >= h),1),
                 round(100.0*avg(CASE WHEN {n} THEN 1.0 ELSE 0 END) FILTER (WHERE risk_score <= l),1)
          FROM scored, (SELECT quantile_cont(risk_score,0.9) h, quantile_cont(risk_score,0.1) l FROM scored)
        """.format(n=name)).fetchone()
        print("  %-4s %-18s top %6s%%   bottom %6s%%" % (rid, name, hi, lo))

    print("\nDISCRIMINATION: DERIVED SCORE vs THE SOURCE fraud_score COLUMN")
    print("  Raw spread is not comparable, the two sit on different scales.")
    print("  What matters is whether a score separates groups at all, so this")
    print("  measures how far the per-group means move, relative to the scale.")
    con.execute("""CREATE OR REPLACE TABLE src_cmp AS
      SELECT upper(trim(entry_mode)) AS entry_mode,
             TRY_CAST(regexp_replace(coalesce(fraud_score,''),'[^0-9.]','','g') AS DOUBLE) AS fs
      FROM pg.landing.raw_txn LIMIT %d""" % args.limit)
    for label, expr, tbl in [("derived risk_score", "risk_score", "scored"),
                             ("source fraud_score", "fs", "src_cmp")]:
        sd, mean = con.execute("""
          SELECT round(stddev(m),3), round(avg(m),3) FROM (
            SELECT avg({e}) m FROM {t}
            WHERE entry_mode IS NOT NULL AND trim(entry_mode) <> ''
            GROUP BY entry_mode HAVING count(*) > 1000)""".format(e=expr, t=tbl)).fetchone()
        sd = sd or 0.0; mean = mean or 0.0
        cv = round(100.0 * sd / mean, 2) if mean else 0
        print("    %-18s group means vary by %8s around %9s  =  %5s%% of scale"
              % (label, sd, mean, cv))
    print("  A score whose group means barely move cannot rank anything.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
