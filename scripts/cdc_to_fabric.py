"""
Continuous CDC replicator: PostgreSQL WAL -> Fabric open mirroring.

  python cdc_to_fabric.py --setup      # create the replication slot, once
  python cdc_to_fabric.py --run        # stream changes until stopped
  python cdc_to_fabric.py --status     # slot lag and file sequence

This is change data capture, not a bulk copy. It reads committed changes out of
the PostgreSQL write-ahead log through a logical replication slot and lands one
small Parquet file per batch in the mirrored database's landing zone. Fabric's
replication engine then APPLIES those changes to the Delta table: an UPDATE in
Postgres rewrites the row in Fabric, a DELETE removes it. A file copy can only
ever add rows; this cannot be reproduced by copying.

  postgres INSERT/UPDATE/DELETE
        -> WAL
        -> logical replication slot (test_decoding)
        -> parse
        -> parquet with __rowMarker__ as the FINAL column
        -> azcopy into Files/LandingZone/<table>/NNNNNNNNNNNNNNNNNNNN.parquet
        -> Fabric applies insert / update / delete to the Delta table

__rowMarker__ mapping (per Microsoft Learn):
  0 = insert, 1 = update, 2 = delete, 4 = upsert

Requirements this script depends on, and why:
* wal_level = logical. Without it no logical slot can exist.
* A REPLICA IDENTITY on the table, i.e. a PRIMARY KEY (or REPLICA IDENTITY
  FULL). Without one PostgreSQL emits NOTHING for UPDATE and DELETE, so the
  mirror would silently degrade into an insert-only feed.
* keyColumns in _metadata.json must be genuinely unique, or an UPDATE cannot be
  matched to a single row on the Fabric side.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

import psycopg2
import pyarrow as pa
import pyarrow.parquet as pq

WORKSPACE_ID = "7e0f6e0d-3730-449f-8be6-2beaec28587b"
MIRRORED_DB_ID = "5069602e-311c-417e-96c5-986f7b9b97d4"
ONELAKE = "https://onelake.dfs.fabric.microsoft.com"
TRUSTED = "onelake.dfs.fabric.microsoft.com"

ROW_MARKER = "__rowMarker__"
OP_MARKER = {"INSERT": "0", "UPDATE": "1", "DELETE": "2"}

CHANGE_RE = re.compile(r"^table ([^.]+)\.([^:]+): (INSERT|UPDATE|DELETE): (.*)$")


# ---------------------------------------------------------------------------
# test_decoding parsing
# ---------------------------------------------------------------------------

def parse_tuple(s):
    """
    Parse a test_decoding change payload into {column: value_or_None}.

    The payload is a space separated list of `name[type]:value`, where a text
    value is single quoted with internal quotes doubled, and an absent value is
    the bare token `null`. Doing this character by character rather than with a
    regex matters here: the data deliberately contains commas, quotes and
    whitespace inside values.
    """
    out = {}
    i, n = 0, len(s)
    while i < n:
        # column name, optionally double quoted
        if s[i] == '"':
            i += 1
            buf = []
            while True:
                if s[i] == '"':
                    if i + 1 < n and s[i + 1] == '"':
                        buf.append('"')
                        i += 2
                        continue
                    i += 1
                    break
                buf.append(s[i])
                i += 1
            name = "".join(buf)
        else:
            j = s.find("[", i)
            if j == -1:
                break
            name = s[i:j]
            i = j
        # [type]:
        k = s.find("]:", i)
        if k == -1:
            break
        i = k + 2
        # value
        if i < n and s[i] == "'":
            i += 1
            buf = []
            while i < n:
                if s[i] == "'":
                    if i + 1 < n and s[i + 1] == "'":
                        buf.append("'")
                        i += 2
                        continue
                    i += 1
                    break
                buf.append(s[i])
                i += 1
            val = "".join(buf)
        else:
            j2 = s.find(" ", i)
            if j2 == -1:
                j2 = n
            tok = s[i:j2]
            i = j2
            val = None if tok == "null" else tok
        out[name] = val
        while i < n and s[i] == " ":
            i += 1
    return out


# ---------------------------------------------------------------------------
# Postgres
# ---------------------------------------------------------------------------

def connect(args):
    kw = dict(host=args.host, port=args.port, dbname=args.dbname, user=args.user)
    if args.password:
        kw["password"] = args.password
    return psycopg2.connect(**kw)


# PostgreSQL type -> pyarrow type. The CDC files MUST match the Delta table's
# existing schema exactly. The seed was written by DuckDB, which mapped the
# bigint surrogate key to int64, so Delta holds it as 'long'. Writing every
# column as string here produces:
#   SchemaMergeFailure ... Incoming type: 'string', existing type: 'long'
# and the change file is rejected. Everything else in this landing table really
# is text, but deriving the mapping keeps it correct if that ever changes.
PG_TO_ARROW = {
    "bigint": pa.int64(),
    "integer": pa.int32(),
    "smallint": pa.int16(),
    "boolean": pa.bool_(),
    "double precision": pa.float64(),
    "real": pa.float32(),
}


def table_columns(con, schema, table):
    """Return [(column_name, arrow_type), ...] in ordinal position order."""
    cur = con.cursor()
    cur.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position",
        (schema, table))
    return [(r[0], PG_TO_ARROW.get(r[1], pa.string())) for r in cur.fetchall()]


def coerce(value, arrow_type):
    """test_decoding hands back text; cast it to the column's real type."""
    if value is None:
        return None
    if arrow_type == pa.string():
        return value
    try:
        if arrow_type in (pa.int64(), pa.int32(), pa.int16()):
            return int(value)
        if arrow_type in (pa.float64(), pa.float32()):
            return float(value)
        if arrow_type == pa.bool_():
            return value in ("t", "true", "TRUE", "1")
    except (TypeError, ValueError):
        return None
    return value


def setup(args):
    con = connect(args)
    con.autocommit = True
    cur = con.cursor()

    cur.execute("SHOW wal_level")
    lvl = cur.fetchone()[0]
    if lvl != "logical":
        print("wal_level is '%s', must be 'logical'. Restart Postgres first." % lvl)
        return 2

    cur.execute("SELECT relreplident FROM pg_class WHERE relname=%s", (args.table,))
    row = cur.fetchone()
    if not row:
        print("table %s not found" % args.table)
        return 2
    if row[0] == "d":
        cur.execute(
            "SELECT count(*) FROM pg_index i JOIN pg_class c ON c.oid=i.indrelid "
            "WHERE c.relname=%s AND i.indisprimary", (args.table,))
        if cur.fetchone()[0] == 0:
            print("table has REPLICA IDENTITY 'default' but no PRIMARY KEY.")
            print("UPDATE and DELETE would emit nothing. Add a PK, or set")
            print("REPLICA IDENTITY FULL, before starting CDC.")
            return 2

    cur.execute("SELECT 1 FROM pg_replication_slots WHERE slot_name=%s", (args.slot,))
    if cur.fetchone():
        print("slot '%s' already exists" % args.slot)
    else:
        cur.execute("SELECT pg_create_logical_replication_slot(%s, 'test_decoding')",
                    (args.slot,))
        print("created logical replication slot '%s' (test_decoding)" % args.slot)

    cols = table_columns(con, args.schema, args.table)
    print("table columns : %d (+ %s appended at write time)" % (len(cols), ROW_MARKER))
    print("key columns   : %s" % args.key_columns)
    con.close()
    return 0


def status(args):
    con = connect(args)
    cur = con.cursor()
    cur.execute("""
        SELECT slot_name, active,
               pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained
        FROM pg_replication_slots WHERE slot_name=%s
    """, (args.slot,))
    r = cur.fetchone()
    print("slot          : %s" % (r,) if r else "slot not found")
    con.close()
    print("next file seq : %020d" % (next_sequence(args) ,))
    return 0


# ---------------------------------------------------------------------------
# OneLake
# ---------------------------------------------------------------------------

def landing_base(args):
    return "%s/%s/%s/Files/LandingZone/%s" % (
        ONELAKE, WORKSPACE_ID, MIRRORED_DB_ID, args.target_table)


def list_landing(args):
    """Return the parquet file names currently in the table's landing folder."""
    cmd = ["fab", "api", "-A", "storage",
           "%s/%s/Files" % (WORKSPACE_ID, MIRRORED_DB_ID),
           "-P", "resource=filesystem,recursive=true",
           "-q", "text.paths[].name"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    names = []
    marker = "LandingZone/%s/" % args.target_table
    for line in (r.stdout or "").splitlines():
        line = line.strip().strip('",')
        if marker in line and line.endswith(".parquet"):
            names.append(line.rsplit("/", 1)[-1])
    return names


def seq_state_path(args):
    return os.path.join(args.work, "%s.seq" % args.target_table)


def read_seq_state(args):
    try:
        with open(seq_state_path(args), "r", encoding="utf-8") as fh:
            return int(fh.read().strip())
    except Exception:
        return 0


def write_seq_state(args, seq):
    os.makedirs(args.work, exist_ok=True)
    with open(seq_state_path(args), "w", encoding="utf-8") as fh:
        fh.write(str(seq))


def next_sequence(args):
    """
    Next file number in the 20-digit sequence.

    Fabric MOVES processed files out of the table folder into _ProcessedFiles /
    _FilesReadyToDelete, so the folder is not a reliable record of how far the
    sequence has got. The docs say the most recent file is deliberately left
    behind for publishers to read, but relying on that alone means a single
    deletion or a cleanup pass silently resets the sequence to 1 and starts
    overwriting. So take the high-water mark of what is remote AND what this
    process last wrote locally.
    """
    best = 0
    for nme in list_landing(args):
        stem = nme.split(".")[0]
        if stem.isdigit():
            best = max(best, int(stem))
    return max(best, read_seq_state(args)) + 1


def azcopy_put(args, local, remote):
    cmd = [args.azcopy, "copy", local, remote, "--overwrite=true",
           "--trusted-microsoft-suffixes=" + TRUSTED]
    r = subprocess.run(cmd, capture_output=True, text=True)
    ok = "Final Job Status: Completed" in (r.stdout or "")
    if not ok:
        print((r.stdout or "")[-800:])
        print((r.stderr or "")[-400:])
    return ok


def ensure_metadata(args, columns):
    """Write _metadata.json once, so Fabric knows the key columns."""
    names = list_landing(args)
    if names:
        return True  # folder already live
    meta = {"keyColumns": [c.strip() for c in args.key_columns.split(",")]}
    tmp = os.path.join(args.work, "_metadata.json")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(meta, fh)
    return azcopy_put(args, tmp, landing_base(args) + "/_metadata.json")


# ---------------------------------------------------------------------------
# CDC loop
# ---------------------------------------------------------------------------

def drain(con, args, columns):
    """Pull one batch of committed changes out of the slot."""
    cur = con.cursor()
    cur.execute(
        "SELECT data FROM pg_logical_slot_get_changes(%s, NULL, %s)",
        (args.slot, args.max_changes))
    records = []
    want = "%s.%s" % (args.schema, args.table)
    for (data,) in cur.fetchall():
        m = CHANGE_RE.match(data)
        if not m:
            continue  # BEGIN / COMMIT lines
        schema, table, op, payload = m.groups()
        if "%s.%s" % (schema, table) != want:
            continue
        vals = parse_tuple(payload)
        rec = {c: coerce(vals.get(c), t) for c, t in columns}
        rec[ROW_MARKER] = OP_MARKER[op]
        records.append(rec)
    return records


def write_parquet(records, columns, path):
    """
    __rowMarker__ MUST be the final column, and every other column must match
    the Delta table's existing type or Fabric rejects the file with
    SchemaMergeFailure.
    """
    names = [c for c, _ in columns] + [ROW_MARKER]
    arrays = [pa.array([r.get(c) for r in records], t) for c, t in columns]
    arrays.append(pa.array([r.get(ROW_MARKER) for r in records], pa.string()))
    pq.write_table(pa.table(arrays, names=names), path, compression="zstd")


def run(args):
    con = connect(args)
    con.autocommit = True
    columns = table_columns(con, args.schema, args.table)
    os.makedirs(args.work, exist_ok=True)

    if not ensure_metadata(args, columns):
        print("could not write _metadata.json")
        return 1

    seq = next_sequence(args)
    print("streaming changes from slot '%s'" % args.slot)
    print("landing  : LandingZone/%s" % args.target_table)
    print("next file: %020d.parquet" % seq)
    print("columns  : %d + %s" % (len(columns), ROW_MARKER))
    print("typed    : %s" % ", ".join("%s=%s" % (c, t) for c, t in columns
                                      if t != pa.string()))
    print("-" * 70)

    idle = 0
    try:
        while True:
            recs = drain(con, args, columns)
            if not recs:
                idle += 1
                if idle % 10 == 0:
                    print("  ... no changes (%ds idle)" % (idle * args.interval))
                time.sleep(args.interval)
                continue
            idle = 0
            counts = {}
            for r in recs:
                counts[r[ROW_MARKER]] = counts.get(r[ROW_MARKER], 0) + 1
            name = "%020d.parquet" % seq
            local = os.path.join(args.work, name)
            write_parquet(recs, columns, local)
            size = os.path.getsize(local)
            if azcopy_put(args, local, landing_base(args) + "/" + name):
                print("  %s  %5d changes  (ins=%s upd=%s del=%s)  %.1f KB"
                      % (name, len(recs), counts.get("0", 0), counts.get("1", 0),
                         counts.get("2", 0), size / 1024.0))
                write_seq_state(args, seq)
                seq += 1
                os.remove(local)
            else:
                print("  upload failed for %s, will retry" % name)
                time.sleep(args.interval)
            if args.once:
                break
    except KeyboardInterrupt:
        print("\nstopped")
    con.close()
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--setup", action="store_true")
    p.add_argument("--run", action="store_true")
    p.add_argument("--status", action="store_true")
    p.add_argument("--once", action="store_true", help="drain one batch and exit")
    p.add_argument("--slot", default="fabric_cdc")
    p.add_argument("--schema", default="landing")
    p.add_argument("--table", default="raw_txn")
    p.add_argument("--target-table", default="raw_txn")
    p.add_argument("--key-columns", default="_mirror_row_id")
    p.add_argument("--interval", type=float, default=5.0)
    p.add_argument("--max-changes", type=int, default=50000)
    p.add_argument("--work", default="C:/tmp/cdc")
    p.add_argument("--azcopy", default="C:/tmp/azcopy/azcopy.exe")
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=5432)
    p.add_argument("--dbname", default="postgres")
    p.add_argument("--user", default="postgres")
    p.add_argument("--password", default=os.environ.get("PGPASSWORD"))
    args = p.parse_args()

    if args.setup:
        return setup(args)
    if args.status:
        return status(args)
    if args.run or args.once:
        return run(args)
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
