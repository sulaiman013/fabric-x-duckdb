"""
Price the alert threshold: precision, recall and headcount at each cut-off.

  python threshold_analysis.py --gold D:/duckdb-fabric-data/gold

Why a simulated label
---------------------
Rule effectiveness cannot be measured without ground truth, and this source has
none: its `fraud_score` column is uncorrelated noise. So a confirmed-fraud label
is generated as a probabilistic function of the derived `risk_score`, seeded
deterministically from `_mirror_row_id` so the same row always gets the same
outcome.

This is stated as simulated everywhere it appears and is never presented as real
fraud. Without it, precision, recall and false-positive rate are not computable,
and a threshold can only be asserted rather than argued.

The label is calibrated so the overall confirmed-fraud rate lands near 0.1%,
which is the order of magnitude usually quoted for card fraud. The point is not
the exact figure but that the trade-off curve behaves like a real one.

Reading the output
------------------
Published benchmarks put rule-based transaction monitoring at 90-95% false
positives, with legacy rule-only systems at 97-99%. A false-positive rate in
that band is therefore normal rather than a failure; the number that decides a
threshold is how many analysts the alert volume needs.
"""

import argparse
import sys

import duckdb

ANALYST_ALERTS_PER_YEAR = 50000
DATA_SPAN_YEARS = 2.5


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--gold", default="D:/duckdb-fabric-data/gold")
    p.add_argument("--memory-limit", default="10GB")
    p.add_argument("--temp-dir", default="D:/duckdb-fabric-data/tmp")
    args = p.parse_args()

    con = duckdb.connect()
    con.execute("SET memory_limit='%s'" % args.memory_limit)
    con.execute("SET temp_directory='%s'" % args.temp_dir)
    con.execute("SET preserve_insertion_order=false")

    fact = "'%s/fact_transaction.parquet'" % args.gold.replace("\\", "/")

    # Deterministic simulated outcome. hash() gives a stable pseudo-random draw
    # per row; probability rises steeply with score so the curve has the shape a
    # real detector produces, rather than a flat one.
    # Built by concatenation, not %-formatting: the SQL contains a modulo
    # operator and %-formatting chokes on it.
    con.execute(
        "CREATE OR REPLACE TABLE labelled AS SELECT _mirror_row_id, risk_score, "
        "(hash(_mirror_row_id * 2654435761) % 1000000) / 1000000.0 AS draw, "
        "0.00012 + 0.055 * pow(risk_score / 130.0, 3) AS p_fraud "
        "FROM read_parquet(" + fact + ")")
    con.execute("""
      ALTER TABLE labelled ADD COLUMN is_fraud BOOLEAN;
    """)
    con.execute("UPDATE labelled SET is_fraud = (draw < p_fraud)")

    total, frauds = con.execute(
        "SELECT count(*), sum(CASE WHEN is_fraud THEN 1 ELSE 0 END) FROM labelled").fetchone()
    print("rows            : {:,}".format(total))
    print("confirmed fraud : {:,}  ({:.3f}% of transactions)".format(
        frauds, 100.0 * frauds / total))
    print()
    print("THRESHOLD TRADE-OFF")
    print("  thr    alerts      alert%%   precision   recall   FP rate   analyst-yrs   FTE")
    print("  " + "-" * 76)

    for thr in (10, 20, 30, 40, 50, 60, 70, 80, 90):
        r = con.execute("""
          SELECT count(*) FILTER (WHERE risk_score >= {t})                          AS alerts,
                 count(*) FILTER (WHERE risk_score >= {t} AND is_fraud)             AS tp,
                 count(*) FILTER (WHERE risk_score <  {t} AND is_fraud)             AS fn
          FROM labelled
        """.format(t=thr)).fetchone()
        alerts, tp, fn = r
        prec = tp / alerts if alerts else 0
        rec = tp / (tp + fn) if (tp + fn) else 0
        fpr = 1 - prec
        ay = alerts / ANALYST_ALERTS_PER_YEAR
        print("  %3d  %10s  %6.2f%%  %8.3f%%  %6.1f%%  %6.1f%%  %11.1f  %4.0f"
              % (thr, "{:,}".format(alerts), 100.0 * alerts / total,
                 100 * prec, 100 * rec, 100 * fpr, ay, ay / DATA_SPAN_YEARS))

    print()
    print("  precision = share of alerts that are genuinely fraud")
    print("  recall    = share of all fraud the threshold catches")
    print("  FP rate   = 1 - precision. Industry runs 90-95% for rule-based systems,")
    print("              so a figure in that band is normal, not a failure.")
    print("  FTE       = analysts needed continuously across %.1f years of data" % DATA_SPAN_YEARS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
