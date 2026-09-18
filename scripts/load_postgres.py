"""
Load the raw CSV extract into local PostgreSQL, untransformed.

  set PGPASSWORD=...
  python load_postgres.py --path D:/duckdb-fabric-data/csv

What this does and does not do
------------------------------
DOES NOT transform. Every one of the 100 columns is created as TEXT and the
bytes land exactly as generated. This is deliberate: values like '1,234.50',
'(45.00)', 'N/A' and '9999-12-31' cannot be coerced into NUMERIC or DATE on
the way in, and a landing zone that rejects rows is not a landing zone. Typing
is a downstream concern.

Storage
-------
The PostgreSQL data directory is on C:, which does not have room for this
table. The script therefore creates a TABLESPACE on D: and puts the table
there. The Postgres service account (NT AUTHORITY\\NetworkService on this
machine) must be able to write to that directory.

NULL vs empty string
--------------------
DuckDB wrote SQL NULL as an unquoted empty field and a genuine empty string as
a quoted "". Postgres CSV COPY reads unquoted empty as NULL and "" as an empty
string, so the distinction survives the round trip intact.
"""

import argparse
import getpass
import glob
import os
import sys
import threading
import time

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema  # noqa: E402

TABLE = "raw_txn"
SCHEMA_NAME = "landing"
TABLESPACE = "bigdata"
LOG_TABLE = "_load_log"


def connect(args, dbname=None):
    return psycopg2.connect(
        host=args.host, port=args.port, dbname=dbname or args.dbname,
        user=args.user, password=args.password, connect_timeout=10,
    )


def human_bytes(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return "%.1f %s" % (n, unit)
        n /= 1024.0
    return "%.1f PB" % n


def ensure_tablespace(con, location, quiet=False):
    """Create the tablespace on D: if it is missing. Returns True on success."""
    con.autocommit = True
    cur = con.cursor()
    cur.execute("SELECT 1 FROM pg_tablespace WHERE spcname = %s", (TABLESPACE,))
    if cur.fetchone():
        if not quiet:
            print("tablespace '%s' already exists" % TABLESPACE)
        return True

    os.makedirs(location, exist_ok=True)
    # The directory must be empty for CREATE TABLESPACE to accept it.
    if os.listdir(location):
        print("  ! %s is not empty; CREATE TABLESPACE requires an empty directory"
              % location)
        return False

    # The service account needs write access to the location.
    os.system('icacls "%s" /grant "NT AUTHORITY\\NetworkService":(OI)(CI)F /T '
              '>nul 2>&1' % location)
    try:
        cur.execute("CREATE TABLESPACE %s LOCATION %%s" % TABLESPACE, (location,))
        print("created tablespace '%s' at %s" % (TABLESPACE, location))
        return True
    except psycopg2.Error as e:
        print("  ! could not create tablespace: %s" % str(e).strip())
        print("    The Postgres service runs as NT AUTHORITY\\NetworkService and")
        print("    needs full control of %s." % location)
        print("    From an ADMIN prompt:")
        print('      icacls "%s" /grant "NT AUTHORITY\\NetworkService":(OI)(CI)F /T'
              % location)
        print("    Then re-run, or pass --no-tablespace to use the default")
        print("    location on C: (not recommended, there is not enough room).")
        return False


def create_table(con, tablespace_ok, unlogged=True):
    con.autocommit = True
    cur = con.cursor()
    cur.execute("CREATE SCHEMA IF NOT EXISTS %s" % SCHEMA_NAME)

    cols = ",\n  ".join('"%s" TEXT' % c for c in schema.COLUMN_NAMES)
    ts = " TABLESPACE %s" % TABLESPACE if tablespace_ok else ""
    unl = "UNLOGGED " if unlogged else ""

    cur.execute("DROP TABLE IF EXISTS %s.%s" % (SCHEMA_NAME, TABLE))
    cur.execute("CREATE %sTABLE %s.%s (\n  %s\n)%s"
                % (unl, SCHEMA_NAME, TABLE, cols, ts))
    cur.execute("""
        CREATE TABLE IF NOT EXISTS %s.%s (
          file_name TEXT PRIMARY KEY,
          rows_loaded BIGINT,
          loaded_at TIMESTAMP DEFAULT now()
        )
    """ % (SCHEMA_NAME, LOG_TABLE))
    print("created %s%s.%s with %d TEXT columns%s"
          % ("UNLOGGED " if unlogged else "", SCHEMA_NAME, TABLE,
             len(schema.COLUMN_NAMES),
             " on tablespace '%s'" % TABLESPACE if tablespace_ok else ""))


def already_loaded(con):
    cur = con.cursor()
    try:
        cur.execute("SELECT file_name FROM %s.%s" % (SCHEMA_NAME, LOG_TABLE))
        return {r[0] for r in cur.fetchall()}
    except psycopg2.Error:
        con.rollback()
        return set()


_print_lock = threading.Lock()
_stats = {"files": 0, "rows": 0, "bytes": 0}


def load_file(args, path, idx, total_files):
    name = os.path.basename(path)
    size = os.path.getsize(path)
    t0 = time.time()
    con = connect(args)
    con.autocommit = False
    cur = con.cursor()
    # Bulk-load tuning, per session.
    cur.execute("SET synchronous_commit = off")
    cur.execute("SET maintenance_work_mem = '512MB'")

    collist = ", ".join('"%s"' % c for c in schema.COLUMN_NAMES)
    sql = ("COPY %s.%s (%s) FROM STDIN WITH (FORMAT csv, HEADER true, "
           "QUOTE '\"', ESCAPE '\"')" % (SCHEMA_NAME, TABLE, collist))

    with open(path, "r", encoding="utf-8", newline="") as fh:
        cur.copy_expert(sql, fh, size=1024 * 1024)
    rows = cur.rowcount
    cur.execute("INSERT INTO %s.%s (file_name, rows_loaded) VALUES (%%s, %%s) "
                "ON CONFLICT (file_name) DO UPDATE SET rows_loaded = EXCLUDED.rows_loaded"
                % (SCHEMA_NAME, LOG_TABLE), (name, rows))
    con.commit()
    con.close()

    dt = time.time() - t0
    with _print_lock:
        _stats["files"] += 1
        _stats["rows"] += rows
        _stats["bytes"] += size
        print("  [%3d/%d] %-22s %12s rows  %9s  %6.1fs  %9s rows/s"
              % (_stats["files"], total_files, name, "{:,}".format(rows),
                 human_bytes(size), dt, "{:,.0f}".format(rows / dt if dt else 0)))
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--path", default="D:/duckdb-fabric-data/csv")
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=5432)
    p.add_argument("--dbname", default="postgres")
    p.add_argument("--user", default="postgres")
    p.add_argument("--password", default=os.environ.get("PGPASSWORD"))
    p.add_argument("--tablespace-dir", default="D:/pgdata/banking_raw")
    p.add_argument("--no-tablespace", action="store_true",
                   help="use the default location on C: (will likely run out of space)")
    p.add_argument("--jobs", type=int, default=4, help="parallel COPY connections")
    p.add_argument("--logged", action="store_true",
                   help="create a LOGGED table (slower, WAL-protected)")
    p.add_argument("--resume", action="store_true",
                   help="keep the existing table and skip files already loaded")
    args = p.parse_args()

    if not args.password:
        args.password = getpass.getpass("Postgres password for user '%s': " % args.user)

    files = sorted(glob.glob(os.path.join(args.path, "txn_part_*.csv")))
    if not files:
        print("no CSV files found in %s" % args.path)
        return 1
    total_bytes = sum(os.path.getsize(f) for f in files)

    print("=" * 74)
    print("LOAD RAW EXTRACT INTO POSTGRESQL")
    print("=" * 74)
    print("source     : %s" % args.path)
    print("files      : %d  (%s)" % (len(files), human_bytes(total_bytes)))
    print("target     : %s.%s @ %s:%s/%s"
          % (SCHEMA_NAME, TABLE, args.host, args.port, args.dbname))
    print("parallelism: %d connections" % args.jobs)
    print("-" * 74)

    con = connect(args)
    ver = con.cursor()
    ver.execute("SELECT version()")
    print(ver.fetchone()[0].split(",")[0])

    ts_ok = False
    if not args.no_tablespace:
        ts_ok = ensure_tablespace(con, os.path.abspath(args.tablespace_dir))
        if not ts_ok:
            print()
            print("Refusing to continue: the table would land on C:, which has")
            print("far less free space than this load needs. Fix the permission")
            print("above, or re-run with --no-tablespace to override.")
            return 2

    skip = set()
    if args.resume:
        skip = already_loaded(con)
        print("resume: %d files already loaded, skipping them" % len(skip))
    else:
        create_table(con, ts_ok, unlogged=not args.logged)
    con.close()

    todo = [f for f in files if os.path.basename(f) not in skip]
    print("-" * 74)

    t0 = time.time()
    from concurrent.futures import ThreadPoolExecutor
    errors = []
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = {ex.submit(load_file, args, f, i, len(todo)): f
                for i, f in enumerate(todo)}
        for fut in futs:
            pass
        for fut, f in futs.items():
            try:
                fut.result()
            except Exception as e:
                errors.append((os.path.basename(f), str(e).strip()[:200]))

    elapsed = time.time() - t0
    print("-" * 74)
    if errors:
        print("FAILED FILES (%d):" % len(errors))
        for name, err in errors:
            print("  %-24s %s" % (name, err))

    con = connect(args)
    cur = con.cursor()
    cur.execute("SELECT count(*) FROM %s.%s" % (SCHEMA_NAME, TABLE))
    n = cur.fetchone()[0]
    cur.execute("SELECT pg_size_pretty(pg_total_relation_size('%s.%s'))"
                % (SCHEMA_NAME, TABLE))
    sz = cur.fetchone()[0]
    con.close()

    print("rows in table : {:,}".format(n))
    print("table size    : %s" % sz)
    print("csv read      : %s" % human_bytes(_stats["bytes"]))
    print("elapsed       : %.1f min  (%s rows/s)"
          % (elapsed / 60, "{:,.0f}".format(n / elapsed if elapsed else 0)))
    if not args.logged:
        print()
        print("Table is UNLOGGED (fast to load, not crash-safe and not replicated).")
        print("To convert once you are happy with it:")
        print("  ALTER TABLE %s.%s SET LOGGED;" % (SCHEMA_NAME, TABLE))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
