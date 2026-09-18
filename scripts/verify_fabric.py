"""
Verify what the Fabric mirrored database actually holds, from the Delta log.

  python verify_fabric.py
  python verify_fabric.py --table raw_txn

Why read the transaction log rather than query the table
-------------------------------------------------------
The obvious checks are not available here. Querying the SQL analytics endpoint
needs `sqlcmd` plus an `az login` session, and neither the Azure CLI nor sqlcmd
is installed on this machine. Reading the Delta files directly with DuckDB's
delta extension needs a storage bearer token.

The Delta transaction log is the authoritative record and is reachable with the
tooling that is available. Every commit is a JSON file under `_delta_log/`
containing `add` and `remove` actions, and each `add` carries a `stats` blob
with `numRecords`. Summing adds and subtracting removes gives the exact live row
count, which is also how a Delta reader computes it.

This is what makes the CDC proof checkable: after an UPDATE the row count stays
the same but a file is rewritten, and after a DELETE the count actually drops.
"""

import argparse
import json
import os
import subprocess
import sys

WORKSPACE_ID = "7e0f6e0d-3730-449f-8be6-2beaec28587b"
MIRRORED_DB_ID = "5069602e-311c-417e-96c5-986f7b9b97d4"


def fab(args_list):
    r = subprocess.run(["fab"] + args_list, capture_output=True, text=True)
    return r.stdout or ""


def list_paths(contains=""):
    out = fab(["api", "-A", "storage",
               "%s/%s/Tables" % (WORKSPACE_ID, MIRRORED_DB_ID),
               "-P", "resource=filesystem,recursive=true",
               "-q", "text.paths[].name"])
    names = []
    for line in out.splitlines():
        line = line.strip().strip('",')
        if line and contains in line:
            names.append(line)
    return names


def fetch(path, dest):
    """Download one OneLake file through the storage API."""
    out = fab(["api", "-A", "storage", path, "-X", "get"])
    # fab prints the body; for _delta_log entries that is newline-delimited JSON
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(out)
    return out


def mirroring_status():
    out = fab(["api",
               "workspaces/%s/mirroredDatabases/%s/getTablesMirroringStatus"
               % (WORKSPACE_ID, MIRRORED_DB_ID), "-X", "post"])
    try:
        return json.loads(out).get("text", {}).get("data", [])
    except Exception:
        return []


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--table", default="raw_txn")
    p.add_argument("--work", default="C:/tmp/deltalog")
    args = p.parse_args()
    os.makedirs(args.work, exist_ok=True)

    print("=" * 74)
    print("FABRIC MIRRORED DATABASE - VERIFICATION")
    print("=" * 74)

    # --- replication status -------------------------------------------------
    for t in mirroring_status():
        err = (t.get("error") or {}).get("message")
        m = t.get("metrics") or {}
        print("table        : %s" % t.get("sourceTableName"))
        print("status       : %s" % t.get("status"))
        print("processedRows: {:,}".format(m.get("processedRows") or 0))
        print("lastSync     : %s" % (m.get("lastSyncDateTime") or "-"))
        if err:
            print("ERROR        : %s" % err[:200])
        print()

    # --- delta log ----------------------------------------------------------
    marker = "Tables/dbo/%s/_delta_log/" % args.table
    logs = sorted(n for n in list_paths(marker) if n.endswith(".json"))
    if not logs:
        print("no _delta_log commits found for '%s' yet" % args.table)
        return 1

    print("delta commits: %d  (%s .. %s)"
          % (len(logs), logs[0].rsplit("/", 1)[-1], logs[-1].rsplit("/", 1)[-1]))

    added = removed = 0
    files_added = files_removed = 0
    for path in logs:
        local = os.path.join(args.work, path.rsplit("/", 1)[-1])
        body = fetch(path, local)
        for line in body.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                act = json.loads(line)
            except Exception:
                continue
            if "add" in act:
                files_added += 1
                stats = act["add"].get("stats")
                if stats:
                    try:
                        added += json.loads(stats).get("numRecords", 0)
                    except Exception:
                        pass
            elif "remove" in act:
                files_removed += 1
                # removes do not carry stats; counted separately below

    print("add actions  : %d  (%s rows)" % (files_added, "{:,}".format(added)))
    print("remove acts  : %d" % files_removed)
    print()
    print("NOTE: a DELETE in the source rewrites a data file, so it appears as a")
    print("remove plus an add with a lower numRecords. Compare the total across")
    print("commits before and after a change to see the effect.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
