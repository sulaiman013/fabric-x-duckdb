"""
Export the PostgreSQL landing table to Fabric open mirroring as an initial snapshot.

  python snapshot_to_fabric.py --stage D:/duckdb-fabric-data/snapshot

Pipeline
--------
  PostgreSQL  --(DuckDB postgres scanner)-->  zstd Parquet  --(azcopy)-->  OneLake LandingZone

Open mirroring rules this script implements (per Microsoft Learn,
https://learn.microsoft.com/fabric/mirroring/open-mirroring-landing-zone-format):

* `_metadata.json` declares `keyColumns`. Without it Fabric will not ingest a
  table folder at all -- which this script exploits deliberately: data files go
  up first and the metadata last, so ingestion is only armed once every parquet
  file is complete. Writing metadata first (as the docs suggest) races against
  the ~20s poll and produces a permanent "Parquet file size is 0 bytes" error.
* Data files are named with 20 zero-padded digits, continuously increasing:
  `00000000000000000001.parquet`, `00000000000000000002.parquet`, ...
* For an INITIAL load, `__rowMarker__` is omitted entirely. Fabric then treats
  every row in the file as an INSERT. It is only required for incremental
  changes, where it must be the FINAL column.
* Parquet needs valid logical/physical type pairs. Not a concern here: all 100
  columns are strings, which sidesteps the DATE-must-be-INT32 class of problem.

Note on duplicate keys
----------------------
`txn_id` contains deliberate duplicates (~1.18%). That is safe for this initial
snapshot because inserts do not deduplicate, but it makes `txn_id` unsuitable as
a key for later CDC upserts, where an update against a duplicated key would be
ambiguous. Choose a genuinely unique key before enabling incremental changes.
"""

import argparse
import json
import os
import subprocess
import sys
import time

import duckdb

WORKSPACE_ID = "7e0f6e0d-3730-449f-8be6-2beaec28587b"
MIRRORED_DB_ID = "5069602e-311c-417e-96c5-986f7b9b97d4"
ONELAKE = "https://onelake.dfs.fabric.microsoft.com"
TRUSTED = "onelake.dfs.fabric.microsoft.com"


def human(n):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return "%.1f %s" % (n, u)
        n /= 1024.0
    return "%.1f PB" % n


def dir_size(p):
    return sum(os.path.getsize(os.path.join(p, f)) for f in os.listdir(p)
               if os.path.isfile(os.path.join(p, f)))


def export(args):
    """Stream the Postgres table out to zstd Parquet, one file per thread."""
    os.makedirs(args.stage, exist_ok=True)
    for f in os.listdir(args.stage):
        os.remove(os.path.join(args.stage, f))

    con = duckdb.connect()
    con.execute("SET memory_limit='%s'" % args.memory_limit)
    con.execute("SET preserve_insertion_order=false")
    con.execute("INSTALL postgres")
    con.execute("LOAD postgres")
    # Omit password entirely when none was supplied, so libpq falls back to its
    # own resolution (%APPDATA%\postgresql\pgpass.conf on Windows). Keeps
    # credentials out of the source, the argv list and the process table.
    dsn = "host=%s port=%d dbname=%s user=%s" % (
        args.host, args.port, args.dbname, args.user)
    if args.password:
        dsn += " password=%s" % args.password
    con.execute("ATTACH '%s' AS pg (TYPE postgres, READ_ONLY)" % dsn)

    src = "pg.%s.%s" % (args.schema, args.table)
    total = con.execute("SELECT count(*) FROM %s" % src).fetchone()[0]
    print("source rows : {:,}".format(total))

    where = ""
    if args.limit:
        where = " USING SAMPLE %d ROWS" % args.limit
        print("LIMITED to {:,} rows (--limit)".format(args.limit))

    t0 = time.time()
    con.execute(
        "COPY (SELECT * FROM %s%s) TO '%s' "
        "(FORMAT PARQUET, COMPRESSION zstd, PER_THREAD_OUTPUT true)"
        % (src, where, args.stage.replace("\\", "/"))
    )
    dt = time.time() - t0
    con.close()

    files = sorted(f for f in os.listdir(args.stage) if f.endswith(".parquet"))
    size = dir_size(args.stage)
    rows = args.limit or total
    print("exported    : %d files, %s in %.1f min (%s rows/s)"
          % (len(files), human(size), dt / 60, "{:,.0f}".format(rows / dt)))
    return files


def rename_sequential(stage):
    """Rename to the 20-digit contiguous sequence open mirroring requires."""
    files = sorted(f for f in os.listdir(stage) if f.endswith(".parquet"))
    renamed = []
    # Two passes via a temp prefix, so a source name can't collide with a target.
    for i, f in enumerate(files):
        os.rename(os.path.join(stage, f), os.path.join(stage, "tmp_%05d" % i))
    for i in range(len(files)):
        target = "%020d.parquet" % (i + 1)
        os.rename(os.path.join(stage, "tmp_%05d" % i), os.path.join(stage, target))
        renamed.append(target)
    print("renamed     : %s .. %s" % (renamed[0], renamed[-1]))
    return renamed


def write_metadata(stage, key_columns):
    meta = {"keyColumns": key_columns}
    p = os.path.join(stage, "_metadata.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(meta, fh)
    print("metadata    : %s" % json.dumps(meta))
    return p


def azcopy(azcopy_exe, src, dst, recursive=False):
    cmd = [azcopy_exe, "copy", src, dst, "--overwrite=true",
           "--trusted-microsoft-suffixes=" + TRUSTED]
    if recursive:
        cmd.append("--recursive=true")
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout or "") + (r.returncode and (r.stderr or "") or "")
    status = "UNKNOWN"
    for line in out.splitlines():
        if "Final Job Status" in line or "Number of File Transfers Failed" in line:
            status = line.strip() if status == "UNKNOWN" else status + " | " + line.strip()
    if r.returncode != 0:
        print(out[-1500:])
    return r.returncode, status


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage", default="D:/duckdb-fabric-data/snapshot")
    p.add_argument("--schema", default="landing")
    p.add_argument("--table", default="raw_txn")
    p.add_argument("--target-table", default="raw_txn",
                   help="folder name under LandingZone/")
    p.add_argument("--key-columns", default="txn_id",
                   help="comma separated, written to _metadata.json")
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=5432)
    p.add_argument("--dbname", default="postgres")
    p.add_argument("--user", default="postgres")
    p.add_argument("--password", default=os.environ.get("PGPASSWORD"),
                   help="omit to let libpq use pgpass.conf")
    p.add_argument("--memory-limit", default="10GB")
    p.add_argument("--limit", type=int, default=0,
                   help="export only N sampled rows (for a quick trial run)")
    p.add_argument("--azcopy", default="C:/tmp/azcopy/azcopy.exe")
    p.add_argument("--skip-export", action="store_true",
                   help="reuse whatever is already staged")
    p.add_argument("--skip-upload", action="store_true")
    args = p.parse_args()

    base = "%s/%s/%s/Files/LandingZone/%s" % (
        ONELAKE, WORKSPACE_ID, MIRRORED_DB_ID, args.target_table)
    key_columns = [c.strip() for c in args.key_columns.split(",") if c.strip()]

    print("=" * 74)
    print("OPEN MIRRORING - INITIAL SNAPSHOT")
    print("=" * 74)
    print("source      : %s.%s" % (args.schema, args.table))
    print("stage       : %s" % args.stage)
    print("destination : LandingZone/%s" % args.target_table)
    print("keyColumns  : %s" % key_columns)
    print("-" * 74)

    if not args.skip_export:
        export(args)
        rename_sequential(args.stage)
    else:
        print("reusing staged files (--skip-export)")

    write_metadata(args.stage, key_columns)

    if args.skip_upload:
        print("upload skipped (--skip-upload)")
        return 0

    if not os.path.exists(args.azcopy):
        print("azcopy not found at %s" % args.azcopy)
        return 2

    print("-" * 74)
    # ORDER MATTERS. Fabric polls the landing zone roughly every 20 seconds and
    # will happily open a .parquet that azcopy is still writing, then fail with
    # "Parquet file size is 0 bytes" and latch that error permanently -- the
    # only documented recovery is to delete and recreate the table folder.
    #
    # Fabric ignores a table folder that has no _metadata.json, so uploading the
    # data files FIRST and the metadata LAST closes the race: by the time
    # ingestion is armed, every parquet file is complete.
    size = dir_size(args.stage)
    parquet = [f for f in os.listdir(args.stage) if f.endswith(".parquet")]
    t0 = time.time()

    print("uploading %s across %d parquet files ..." % (human(size), len(parquet)))
    rc, status = azcopy(args.azcopy, args.stage.rstrip("/\\") + "/*.parquet",
                        base + "/")
    dt = time.time() - t0
    print("data upload     : %s" % status)
    print("elapsed         : %.1f min  (%.1f MB/s)"
          % (dt / 60, size / 1048576 / dt if dt else 0))
    if rc != 0:
        print("data upload failed; NOT writing _metadata.json, so Fabric will")
        print("not try to ingest a partial set. Re-run to retry.")
        return 1

    print("arming ingestion with _metadata.json ...")
    rc, status = azcopy(args.azcopy, os.path.join(args.stage, "_metadata.json"),
                        base + "/_metadata.json")
    print("metadata upload : %s" % status)
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
