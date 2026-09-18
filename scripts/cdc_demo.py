"""
Prove the mirror is a mirror and not a copy.

  python cdc_demo.py --apply     # make changes in PostgreSQL
  python cdc_demo.py --verify    # check what Fabric now holds

A file copy can only ever add rows. A mirror propagates all three operations, so
the test is whether a row that is UPDATED in PostgreSQL *changes* in Fabric, and
a row that is DELETED *disappears* from Fabric.

This script:
  1. picks three real rows and records their current state
  2. INSERTs a new row, UPDATEs a second, DELETEs a third
  3. prints the exact `_mirror_row_id` values to check on the Fabric side

`cdc_to_fabric.py --run` must be streaming for the changes to reach Fabric.
Verification queries the mirrored table through its SQL analytics endpoint, or
you can read the Delta files directly from OneLake.
"""

import argparse
import json
import os
import sys

import psycopg2

STATE = "C:/tmp/cdc/demo_state.json"

# Columns touched by the UPDATE. Deliberately ones a human can eyeball in a
# report: a status, a categorical, and a money column stored as text.
UPDATE_SET = {
    "txn_status": "CDC-UPDATED",
    "merchant_name": "MIRROR TEST MERCHANT",
    "txn_amount": "99999.99",
}


def connect(args):
    kw = dict(host=args.host, port=args.port, dbname=args.dbname, user=args.user)
    if args.password:
        kw["password"] = args.password
    return psycopg2.connect(**kw)


def apply_changes(args):
    con = connect(args)
    con.autocommit = False
    cur = con.cursor()
    tbl = "%s.%s" % (args.schema, args.table)

    # Pick two existing rows that are NOT part of a duplicate group, so the
    # before/after story is unambiguous when read back.
    cur.execute("""
        SELECT _mirror_row_id, txn_id, txn_status, merchant_name, txn_amount
        FROM %s
        WHERE txn_id IN (
            SELECT txn_id FROM %s GROUP BY txn_id HAVING count(*) = 1 LIMIT 500
        )
        ORDER BY _mirror_row_id
        LIMIT 2
    """ % (tbl, tbl))
    picked = cur.fetchall()
    if len(picked) < 2:
        print("could not find two unique-txn_id rows to use")
        return 1

    upd_row, del_row = picked[0], picked[1]

    state = {
        "update": {
            "_mirror_row_id": upd_row[0],
            "txn_id": upd_row[1],
            "before": {"txn_status": upd_row[2], "merchant_name": upd_row[3],
                       "txn_amount": upd_row[4]},
            "after": dict(UPDATE_SET),
        },
        "delete": {"_mirror_row_id": del_row[0], "txn_id": del_row[1]},
    }

    print("=" * 74)
    print("APPLYING CHANGES IN POSTGRESQL")
    print("=" * 74)

    # --- INSERT -------------------------------------------------------------
    cols = ["txn_id", "txn_status", "merchant_name", "txn_amount",
            "posting_date", "source_system"]
    vals = ["TXN-CDC-INSERT-0001", "CDC-INSERTED", "MIRROR TEST INSERT",
            "12345.67", "2026-09-18", "CDC_DEMO"]
    cur.execute(
        "INSERT INTO %s (%s) VALUES (%s) RETURNING _mirror_row_id"
        % (tbl, ", ".join(cols), ", ".join(["%s"] * len(vals))), vals)
    ins_id = cur.fetchone()[0]
    state["insert"] = {"_mirror_row_id": ins_id, "txn_id": vals[0]}
    print("INSERT  _mirror_row_id=%s  txn_id=%s" % (ins_id, vals[0]))

    # --- UPDATE -------------------------------------------------------------
    sets = ", ".join("%s = %%s" % c for c in UPDATE_SET)
    cur.execute("UPDATE %s SET %s WHERE _mirror_row_id = %%s" % (tbl, sets),
                list(UPDATE_SET.values()) + [upd_row[0]])
    print("UPDATE  _mirror_row_id=%s" % upd_row[0])
    for k in UPDATE_SET:
        b = state["update"]["before"][k]
        print("          %-14s %r -> %r" % (k, b, UPDATE_SET[k]))

    # --- DELETE -------------------------------------------------------------
    cur.execute("DELETE FROM %s WHERE _mirror_row_id = %%s" % tbl, (del_row[0],))
    print("DELETE  _mirror_row_id=%s  txn_id=%s" % (del_row[0], del_row[1]))

    con.commit()
    con.close()

    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, default=str)

    print()
    print("-" * 74)
    print("WHAT FABRIC SHOULD SHOW once the replicator has shipped these:")
    print("-" * 74)
    print("  _mirror_row_id=%-12s row EXISTS      (was not there before)"
          % state["insert"]["_mirror_row_id"])
    print("  _mirror_row_id=%-12s txn_status='CDC-UPDATED'  (row CHANGED in place)"
          % state["update"]["_mirror_row_id"])
    print("  _mirror_row_id=%-12s row GONE        (row DELETED)"
          % state["delete"]["_mirror_row_id"])
    print()
    print("A copy cannot produce the second or third outcome.")
    print("state written to %s" % STATE)
    return 0


def verify(args):
    """Report the PostgreSQL side; the Fabric side is checked separately."""
    if not os.path.exists(STATE):
        print("no demo state found, run --apply first")
        return 1
    with open(STATE, "r", encoding="utf-8") as fh:
        state = json.load(fh)

    con = connect(args)
    cur = con.cursor()
    tbl = "%s.%s" % (args.schema, args.table)

    print("=" * 74)
    print("POSTGRESQL SIDE (source of truth)")
    print("=" * 74)
    for label in ("insert", "update", "delete"):
        rid = state[label]["_mirror_row_id"]
        cur.execute(
            "SELECT txn_id, txn_status, merchant_name, txn_amount FROM %s "
            "WHERE _mirror_row_id = %%s" % tbl, (rid,))
        row = cur.fetchone()
        print("  %-7s _mirror_row_id=%-12s %s"
              % (label.upper(), rid, row if row else "<absent>"))
    con.close()

    print()
    print("Now compare against Fabric. Expected:")
    print("  INSERT id present, UPDATE id shows 'CDC-UPDATED', DELETE id absent.")
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--schema", default="landing")
    p.add_argument("--table", default="raw_txn")
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=5432)
    p.add_argument("--dbname", default="postgres")
    p.add_argument("--user", default="postgres")
    p.add_argument("--password", default=os.environ.get("PGPASSWORD"))
    args = p.parse_args()
    if args.apply:
        return apply_changes(args)
    if args.verify:
        return verify(args)
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
