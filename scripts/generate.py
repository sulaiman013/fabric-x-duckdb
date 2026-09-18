"""
Generate a wide, raw, deliberately messy banking transaction extract as CSV.

  python generate.py --rows 50000000 --out D:/duckdb-fabric-data/csv

Design notes
------------
* 100 text columns. Nothing is typed, nothing is cleaned. This is a landing
  zone dump, so every value is emitted exactly as a source system would have
  written it, including junk.

* Entity attributes (customer name, merchant name, card brand, branch) are a
  deterministic hash of the entity id, so the same customer keeps the same
  underlying name across every one of their transactions. The mess layer then
  perturbs it, which produces the real-world pattern of one customer appearing
  as "Ahmad bin Abdullah", "AHMAD BIN ABDULLAH" and " ahmad  bin abdullah ".

* Exact duplicate rows are injected by materialising each chunk to a temp
  table and re-emitting a Bernoulli sample of it. They are appended at the end
  of each chunk file rather than interleaved, which keeps the generator single
  pass; with many chunk files the duplicates still land throughout the dataset.

* Chunks are written as independent CSV files so the Postgres load can run in
  parallel and resume after a failure.
"""

import argparse
import json
import os
import sys
import time

import duckdb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema  # noqa: E402


# Cardinalities of the simulated entity population.
N_CUSTOMERS = 4_000_000
N_MERCHANTS = 250_000
N_CARDS = 5_000_000
N_ACCOUNTS = 4_500_000


def build_base_cte(start, n):
    """
    The correlated core of each row.

    Anything that must stay consistent for a given entity is derived with
    hash(entity_id), not random(), so it is stable across chunks and runs.
    Anything that legitimately varies per transaction uses random().
    """
    return """
    SELECT
      gid,
      cust_n,
      1 + (hash(cust_n * 3  + 1) % {n_acct})  AS acct_n,
      1 + (hash(cust_n * 7  + 3) % {n_card})  AS card_n,
      1 + CAST(floor(pow(random(), 1.6) * {n_merch}) AS BIGINT) AS merch_n,

      -- entity-stable dates
      DATE '1955-01-01' + CAST(hash(cust_n * 11) % 16000 AS INTEGER) AS dob_dt,
      DATE '2005-01-01' + CAST(hash(cust_n * 13) % 6500 AS INTEGER) AS since_dt,
      DATE '2018-01-01' + CAST(hash(cust_n * 19) % 2200 AS INTEGER) AS addr_dt,
      DATE '2020-01-01' + CAST(hash(cust_n * 23) % 1600 AS INTEGER) AS kyc_dt,
      DATE '2008-01-01' + CAST(hash(cust_n * 29) % 5800 AS INTEGER) AS open_dt,

      -- transaction timeline: 2023-01-01 .. ~2025-06-30, business-hours skewed
      txn_ts,
      CAST(txn_ts AS DATE) + CAST(floor(random() * 4) AS INTEGER) AS post_dt,
      CAST(txn_ts AS DATE) + CAST(floor(random() * 6) AS INTEGER) AS val_dt,
      CAST(txn_ts AS DATE) + CAST(floor(random() * 8) AS INTEGER) AS settle_dt,
      txn_ts + INTERVAL (CAST(floor(random() * 72) AS INTEGER)) HOUR AS ing_ts,

      -- money: log-skewed so most transactions are small
      amt,
      fx,
      round(amt * fx, 2)                                   AS amt_local,
      round(amt * fx * 0.004 + 0.5, 2)                     AS fee,
      round(amt * fx * 0.004 * 0.06, 2)                    AS vat,
      round(amt * fx * 0.0015, 2)                          AS icfee,
      round(amt * fx * 0.0025, 2)                          AS mkfee,
      round(amt * fx * 1.0042 + 0.5, 2)                    AS total,
      bal_before,
      round(bal_before - (amt * fx * 1.0042 + 0.5), 2)     AS bal_after,
      round(bal_before - (amt * fx * 1.0042 + 0.5)
            - (random() * 500), 2)                         AS bal_avail,

      random()      AS aml_s,
      pow(random(), 3) AS fraud_s
    FROM (
      SELECT
        {start} + i AS gid,
        1 + CAST(floor(pow(random(), 2.0) * {n_cust}) AS BIGINT) AS cust_n,
        TIMESTAMP '2023-01-01 00:00:00'
          + INTERVAL (CAST(floor(random() * 78000000) AS BIGINT)) SECOND AS txn_ts,
        round(pow(10, 0.4 + random() * 3.1), 2) AS amt,
        CASE WHEN random() < 0.86 THEN 1.0
             ELSE round(0.28 + random() * 4.5, 6) END AS fx,
        round(random() * 90000, 2) AS bal_before
      FROM range(0, {n}) t(i)
    )
    """.format(
        start=start,
        n=n,
        n_cust=N_CUSTOMERS,
        n_merch=N_MERCHANTS,
        n_card=N_CARDS,
        n_acct=N_ACCOUNTS,
    )


def build_select(start, n):
    cols = ",\n      ".join(
        "%s AS %s" % (expr, name) for name, expr in schema.COLUMNS
    )
    return "WITH base AS MATERIALIZED (%s)\n    SELECT\n      %s\n    FROM base" % (
        build_base_cte(start, n),
        cols,
    )


def human_bytes(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return "%.1f %s" % (n, unit)
        n /= 1024.0
    return "%.1f PB" % n


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rows", type=int, default=50_000_000,
                   help="total rows to emit, duplicates included")
    p.add_argument("--chunk", type=int, default=1_000_000,
                   help="base rows per CSV file")
    p.add_argument("--out", default="D:/duckdb-fabric-data/csv")
    p.add_argument("--dup-rate", type=float, default=0.012,
                   help="fraction of each chunk re-emitted as exact duplicates")
    p.add_argument("--seed", type=float, default=0.4242)
    p.add_argument("--threads", type=int, default=0, help="0 = DuckDB default")
    p.add_argument("--memory-limit", default="10GB")
    p.add_argument("--resume", action="store_true",
                   help="skip chunk files that already exist")
    args = p.parse_args()

    os.makedirs(args.out, exist_ok=True)
    manifest_path = os.path.join(args.out, "_manifest.json")

    con = duckdb.connect()
    con.execute("SET memory_limit='%s'" % args.memory_limit)
    con.execute("SET preserve_insertion_order=false")
    if args.threads:
        con.execute("SET threads=%d" % args.threads)
    con.execute("SELECT setseed(%f)" % args.seed)

    threads = con.execute("SELECT current_setting('threads')").fetchone()[0]
    print("DuckDB %s | threads=%s | memory_limit=%s"
          % (duckdb.__version__, threads, args.memory_limit))
    print("target rows : {:,}".format(args.rows))
    print("columns     : %d" % len(schema.COLUMNS))
    print("output      : %s" % args.out)
    print("-" * 66)

    header = [c[0] for c in schema.COLUMNS]
    chunks = []
    emitted = 0
    gid = 1
    idx = 0
    t_start = time.time()

    while emitted < args.rows:
        remaining = args.rows - emitted
        base_n = min(args.chunk, remaining)
        path = os.path.join(args.out, "txn_part_%05d.csv" % idx)

        if args.resume and os.path.exists(path):
            # Trust a previously completed file and skip re-generating it.
            rows_in_file = con.execute(
                "SELECT count(*) FROM read_csv(?, header=true, "
                "all_varchar=true, quote='\"', escape='\"')", [path]
            ).fetchone()[0]
            print("[%3d] skip (resume) %-22s %12s rows"
                  % (idx, os.path.basename(path), "{:,}".format(rows_in_file)))
            chunks.append({"file": os.path.basename(path), "rows": rows_in_file})
            emitted += rows_in_file
            gid += base_n
            idx += 1
            continue

        t0 = time.time()
        con.execute("DROP TABLE IF EXISTS chunk_tmp")
        con.execute("CREATE TEMP TABLE chunk_tmp AS %s" % build_select(gid, base_n))

        # Exact duplicates: re-emit a Bernoulli sample of the materialised rows.
        # The sample is staged in its own table first; inserting into a table
        # while scanning that same table is not safe to rely on.
        if args.dup_rate > 0:
            con.execute("DROP TABLE IF EXISTS dup_tmp")
            con.execute(
                "CREATE TEMP TABLE dup_tmp AS SELECT * FROM chunk_tmp "
                "USING SAMPLE %f PERCENT (bernoulli)" % (args.dup_rate * 100)
            )
            con.execute("INSERT INTO chunk_tmp SELECT * FROM dup_tmp")
            con.execute("DROP TABLE IF EXISTS dup_tmp")

        available = con.execute("SELECT count(*) FROM chunk_tmp").fetchone()[0]
        take = min(available, remaining)

        con.execute(
            "COPY (SELECT * FROM chunk_tmp LIMIT %d) TO '%s' "
            "(FORMAT CSV, HEADER true, QUOTE '\"', ESCAPE '\"', NULLSTR '')"
            % (take, path.replace("\\", "/"))
        )
        con.execute("DROP TABLE IF EXISTS chunk_tmp")

        size = os.path.getsize(path)
        dt = time.time() - t0
        emitted += take
        gid += base_n
        chunks.append({"file": os.path.basename(path), "rows": take, "bytes": size})

        pct = 100.0 * emitted / args.rows
        rate = take / dt if dt else 0
        print("[%3d] %-22s %12s rows  %9s  %5.1fs  %8s rows/s  %5.1f%%"
              % (idx, os.path.basename(path), "{:,}".format(take),
                 human_bytes(size), dt, "{:,.0f}".format(rate), pct))
        idx += 1

    total_bytes = sum(c.get("bytes", 0) for c in chunks)
    elapsed = time.time() - t_start

    manifest = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rows": emitted,
        "columns": len(schema.COLUMNS),
        "column_names": header,
        "files": len(chunks),
        "total_bytes": total_bytes,
        "dup_rate": args.dup_rate,
        "seed": args.seed,
        "elapsed_seconds": round(elapsed, 1),
        "chunks": chunks,
    }
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    print("-" * 66)
    print("rows written : {:,}".format(emitted))
    print("files        : %d" % len(chunks))
    print("total size   : %s" % human_bytes(total_bytes))
    print("elapsed      : %.1f min" % (elapsed / 60))
    print("manifest     : %s" % manifest_path)


if __name__ == "__main__":
    main()
