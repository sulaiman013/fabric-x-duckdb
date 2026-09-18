"""
Profile the generated raw extract and prove the mess is what it claims to be.

  python validate.py --path D:/duckdb-fabric-data/csv

Reads the CSV with all_varchar=true, so DuckDB does no type inference and we
see the bytes exactly as Postgres will receive them.
"""

import argparse
import glob
import os
import sys

import duckdb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema  # noqa: E402

JUNK = ("", "NULL", "N/A", "NA", "-", "unknown", "none", "#N/A")


def rel(con, pattern):
    return ("read_csv('%s', header=true, all_varchar=true, quote='\"', "
            "escape='\"', sample_size=-1)" % pattern.replace("\\", "/"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--path", default="D:/duckdb-fabric-data/csv")
    p.add_argument("--limit-files", type=int, default=0,
                   help="profile only the first N files (0 = all)")
    args = p.parse_args()

    files = sorted(glob.glob(os.path.join(args.path, "txn_part_*.csv")))
    if not files:
        print("no CSV files found in %s" % args.path)
        return 1
    if args.limit_files:
        files = files[:args.limit_files]

    pattern = (os.path.join(args.path, "txn_part_*.csv")
               if not args.limit_files else files[0])
    if args.limit_files and len(files) > 1:
        pattern = os.path.join(args.path, "txn_part_*.csv")

    con = duckdb.connect()
    con.execute("SET memory_limit='8GB'")
    src = rel(con, pattern)

    print("=" * 74)
    print("RAW EXTRACT PROFILE")
    print("=" * 74)
    print("files scanned : %d" % len(files))

    # -- structure -----------------------------------------------------------
    cols = [r[0] for r in con.execute("DESCRIBE SELECT * FROM %s" % src).fetchall()]
    expected = schema.COLUMN_NAMES
    print("columns       : %d" % len(cols))
    print("header match  : %s" % ("OK" if cols == expected
                                  else "MISMATCH -> %s" % set(cols) ^ set(expected)))

    types = con.execute("DESCRIBE SELECT * FROM %s" % src).fetchall()
    non_text = [t[0] for t in types if t[1] != "VARCHAR"]
    print("all text      : %s" % ("OK" if not non_text else "NOT TEXT: %s" % non_text))

    total = con.execute("SELECT count(*) FROM %s" % src).fetchone()[0]
    print("rows          : {:,}".format(total))

    # -- duplicates ----------------------------------------------------------
    dup = con.execute(
        "SELECT count(*) FROM (SELECT txn_id, count(*) c FROM %s "
        "GROUP BY txn_id HAVING c > 1)" % src
    ).fetchone()[0]
    dup_rows = con.execute(
        "SELECT coalesce(sum(c-1),0) FROM (SELECT txn_id, count(*) c FROM %s "
        "GROUP BY txn_id HAVING c > 1)" % src
    ).fetchone()[0]
    print("dup txn_ids   : {:,}  ({:,} surplus rows, {:.2f}%)".format(
        dup, dup_rows, 100.0 * dup_rows / total if total else 0))

    # -- entity coherence ----------------------------------------------------
    # The same customer must resolve to one underlying first name once casing
    # and whitespace are normalised. If this is > 1 the generator is producing
    # a different person per row, which would make the data useless for joins.
    junk_list = ",".join("'%s'" % j for j in JUNK)
    incoherent = con.execute("""
        SELECT count(*) FROM (
          SELECT customer_id,
                 count(DISTINCT lower(trim(first_name))) AS variants
          FROM %s
          WHERE customer_id IS NOT NULL
            AND trim(customer_id) NOT IN (%s)
            AND first_name IS NOT NULL
            AND trim(first_name) NOT IN (%s)
          GROUP BY customer_id
          HAVING variants > 1
        )
    """ % (src, junk_list, junk_list)).fetchone()[0]
    print("customers with >1 first-name variant : %s"
          % ("{:,}".format(incoherent) + ("  <-- PROBLEM" if incoherent else "  OK")))

    # -- mess rates ----------------------------------------------------------
    print()
    print("-" * 74)
    print("MESS RATE BY COLUMN  (null + null-lookalike + padded)")
    print("-" * 74)
    parts = []
    for c in expected:
        parts.append(
            "sum(CASE WHEN \"{c}\" IS NULL OR trim(\"{c}\") IN ({j}) THEN 1 ELSE 0 END)"
            "::DOUBLE / count(*) AS \"{c}\"".format(c=c, j=junk_list)
        )
    rates = con.execute("SELECT %s FROM %s" % (", ".join(parts), src)).fetchone()
    pairs = sorted(zip(expected, rates), key=lambda x: -x[1])
    print("  highest 12:")
    for name, r in pairs[:12]:
        print("    %-24s %5.1f%%" % (name, r * 100))
    print("  lowest 5:")
    for name, r in pairs[-5:]:
        print("    %-24s %5.1f%%" % (name, r * 100))
    avg = sum(rates) / len(rates)
    print("  mean across 100 columns: %.1f%%" % (avg * 100))

    # -- format drift --------------------------------------------------------
    print()
    print("-" * 74)
    print("FORMAT DRIFT (the reason this cannot be loaded as typed columns)")
    print("-" * 74)

    checks = [
        ("posting_date parses as ISO date",
         "sum(CASE WHEN try_cast(posting_date AS DATE) IS NOT NULL THEN 1 ELSE 0 END)"),
        ("txn_amount parses as number",
         "sum(CASE WHEN try_cast(txn_amount AS DOUBLE) IS NOT NULL THEN 1 ELSE 0 END)"),
        ("balance_after parses as number",
         "sum(CASE WHEN try_cast(balance_after AS DOUBLE) IS NOT NULL THEN 1 ELSE 0 END)"),
        ("txn_datetime parses as timestamp",
         "sum(CASE WHEN try_cast(txn_datetime AS TIMESTAMP) IS NOT NULL THEN 1 ELSE 0 END)"),
    ]
    sel = ", ".join("%s AS c%d" % (e, i) for i, (_, e) in enumerate(checks))
    res = con.execute("SELECT %s, count(*) FROM %s" % (sel, src)).fetchone()
    n = res[-1]
    for i, (label, _) in enumerate(checks):
        ok = res[i]
        print("  %-36s %6.1f%% parse cleanly" % (label, 100.0 * ok / n))

    print()
    print("  distinct spellings of a single concept:")
    for col in ("addr_country", "txn_type", "card_brand", "account_currency"):
        d = con.execute("SELECT count(DISTINCT \"%s\") FROM %s" % (col, src)).fetchone()[0]
        vals = con.execute(
            "SELECT \"%s\" FROM %s WHERE \"%s\" IS NOT NULL GROUP BY 1 "
            "ORDER BY count(*) DESC LIMIT 6" % (col, src, col)).fetchall()
        shown = ", ".join(repr(v[0]) for v in vals)
        print("    %-20s %3d distinct | %s" % (col, d, shown))

    print()
    print("-" * 74)
    print("SAMPLE VALUES")
    print("-" * 74)
    for col in ("posting_date", "txn_amount", "full_name", "merchant_name",
                "mobile_no", "card_expiry", "aml_score"):
        vals = con.execute(
            "SELECT DISTINCT \"%s\" FROM %s WHERE \"%s\" IS NOT NULL LIMIT 8"
            % (col, src, col)).fetchall()
        print("  %-16s %s" % (col, " | ".join(repr(v[0])[:22] for v in vals)))

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
