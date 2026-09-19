"""Organise the Fabric workspace into folders that match the pipeline phases.

  python folderize_workspace.py --dry-run     show the plan, change nothing
  python folderize_workspace.py               create folders and move items

Layout
------
The workspace mirrors the four phases the project is actually built in, so the
item list reads the same way the README and BUILD_LOG do:

  01 Ingestion        the mirrored database: on-prem Postgres landing in OneLake
  02 Transformation   the gold lakehouse and the notebooks that build and check it
  03 Semantic Model   the Direct Lake model
  04 Application      the report that consumes the model
  Deprecated          items superseded or left over from investigation

What counts as deprecated
-------------------------
Only items that are genuinely unused, evidenced rather than assumed:

  stage_lh   An empty Lakehouse. It has no tables and no files, nothing in the
             repo references it, and BUILD_LOG section 11 records it as created
             during the azcopy investigation and redundant once azcopy was shown
             to write to the MirroredDatabase directly.

Nothing is deleted. Deprecated items keep their data and can be moved back.

SQL endpoints
-------------
A Lakehouse, MirroredDatabase and SQLDatabase each auto-create a SQLEndpoint
child. Those are not independently movable in the API, so they are left alone
and the run reports them rather than failing.
"""

import argparse
import json
import re
import subprocess
import sys

WS = "7e0f6e0d-3730-449f-8be6-2beaec28587b"

# folder -> [(item name, item type), ...]
PLAN = [
    ("01 Ingestion", [
        ("sulaiman-postgres", "MirroredDatabase"),
    ]),
    ("02 Transformation", [
        ("fincrime", "Lakehouse"),
        ("01_build_gold", "Notebook"),
        ("02_vorder_write", "Notebook"),
        ("03_verify", "Notebook"),
    ]),
    ("03 Semantic Model", [
        ("fincrime_model", "SemanticModel"),
    ]),
    ("04 Application", [
        ("FinCrime", "Report"),
    ]),
    ("Deprecated", [
        ("stage_lh", "Lakehouse"),
    ]),
]

# Auto-created children that follow their parent and cannot be moved alone.
CHILD_TYPES = ("SQLEndpoint",)

# Items that belong at the workspace root on purpose. The README is the entry
# point and should be the first thing a reader sees, above the phase folders.
ROOT_ITEMS = {("00_README", "Notebook")}


def fab(*args, **kw):
    out = subprocess.run(["fab"] + list(args), capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=120)
    body = out.stdout or ""
    i = body.find("{")
    if i < 0:
        return None, body.strip()
    try:
        d = json.loads(body[i:])
    except ValueError:
        return None, body.strip()[:300]
    return d, None


def items():
    d, err = fab("api", "workspaces/%s/items" % WS)
    if err:
        raise SystemExit("could not list items: %s" % err)
    return d.get("text", d).get("value", [])


def folders():
    d, err = fab("api", "workspaces/%s/folders" % WS)
    if err:
        return {}
    return {f["displayName"]: f["id"]
            for f in d.get("text", d).get("value", [])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    live = items()
    by_key = {}
    for r in live:
        by_key[(r.get("displayName"), r.get("type"))] = r

    planned = set()
    for _f, entries in PLAN:
        for e in entries:
            planned.add(e)

    print("PLAN")
    missing = []
    for folder, entries in PLAN:
        print("\n  %s" % folder)
        for name, typ in entries:
            if (name, typ) in by_key:
                print("    %-22s %s" % (name, typ))
            else:
                print("    %-22s %s   NOT FOUND" % (name, typ))
                missing.append((name, typ))

    # Anything live that the plan does not mention, so nothing is silently left
    # behind at the root.
    leftover = [r for r in live
                if (r.get("displayName"), r.get("type")) not in planned
                and (r.get("displayName"), r.get("type")) not in ROOT_ITEMS
                and r.get("type") not in CHILD_TYPES]
    children = [r for r in live if r.get("type") in CHILD_TYPES]

    if leftover:
        print("\n  UNPLANNED (left at the workspace root)")
        for r in leftover:
            print("    %-22s %s" % (r.get("displayName"), r.get("type")))
    if children:
        print("\n  AUTO-CREATED CHILDREN (follow their parent, not moved)")
        for r in children:
            print("    %-22s %s" % (r.get("displayName"), r.get("type")))
    if missing:
        print("\n  %d planned item(s) not present in the workspace" % len(missing))

    if args.dry_run:
        print("\ndry run: nothing changed")
        return 0

    print("\nAPPLYING")
    have = folders()
    moved = skipped = 0
    for folder, entries in PLAN:
        fid = have.get(folder)
        if not fid:
            d, err = fab("api", "workspaces/%s/folders" % WS, "-X", "post",
                         "-i", json.dumps({"displayName": folder}))
            if err or not d:
                print("  FAILED to create %r: %s" % (folder, err))
                continue
            t = d.get("text", d)
            fid = t.get("id")
            if not fid:
                print("  FAILED to create %r: %s" % (folder, json.dumps(t)[:160]))
                continue
            print("  created folder  %s" % folder)
            have[folder] = fid
        else:
            print("  folder exists   %s" % folder)

        for name, typ in entries:
            r = by_key.get((name, typ))
            if not r:
                continue
            if r.get("folderId") == fid:
                skipped += 1
                continue
            d, err = fab("api",
                         "workspaces/%s/items/%s/move" % (WS, r["id"]),
                         "-X", "post",
                         "-i", json.dumps({"targetFolderId": fid}))
            code = (d or {}).get("status_code")
            if err or code not in (200, 201):
                msg = err or json.dumps((d or {}).get("text", {}))[:140]
                print("    FAILED  %-20s %s" % (name, msg))
            else:
                print("    moved   %-20s -> %s" % (name, folder))
                moved += 1

    print("\n%d moved, %d already in place" % (moved, skipped))

    print("\nRESULT")
    fmap = {v: k for k, v in folders().items()}
    for r in sorted(items(), key=lambda x: (fmap.get(x.get("folderId"), "~root"),
                                            x.get("type", ""),
                                            x.get("displayName", ""))):
        print("  %-20s %-18s %s" % (r.get("displayName"), r.get("type"),
                                    fmap.get(r.get("folderId"), "(root)")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
