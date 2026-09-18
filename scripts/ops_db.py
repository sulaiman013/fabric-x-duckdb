"""Create and inspect the operational write-back tables in `fincrime_ops`.

  python ops_db.py --ddl       create the schema and tables (idempotent)
  python ops_db.py --show      list tables and row counts
  python ops_db.py --sql "..." run one statement

Authentication
--------------
Reuses the token the Fabric CLI already holds rather than asking for a second
login. `fab auth login` writes an MSAL cache to `~/.config/fab/cache.bin`; this
reads that cache and silently acquires a token for the SQL audience, then hands
it to pyodbc through `SQL_COPT_SS_ACCESS_TOKEN`.

That keeps the credential out of this file, out of the command line and out of
the repository, which matters because the repository is public.
"""

import argparse
import json
import os
import struct
import sys

SQL_COPT_SS_ACCESS_TOKEN = 1256
SCOPE = "https://database.windows.net/.default"
FAB_DIR = os.path.join(os.path.expanduser("~"), ".config", "fab")

SERVER = ("6xdtv76wvqse5lz63juf6hq7gy-bvxa67rqg6pujc7gfpvoykcypm"
          ".database.fabric.microsoft.com,1433")
DATABASE = "fincrime_ops-446f966e-7df5-4284-a279-fdb32ef3b8a1"

# Grains and key columns follow APP_DESIGN.md section 9. `_mirror_row_id` is
# carried on the two tables that point at a specific source row, because no
# subset of the 100 business columns is unique and it is the only stable handle
# back to the mirrored record.
DDL = [
    "IF SCHEMA_ID('ops') IS NULL EXEC('CREATE SCHEMA ops')",

    """IF OBJECT_ID('ops.alert_disposition') IS NULL
       CREATE TABLE ops.alert_disposition (
         disposition_id  BIGINT IDENTITY(1,1) PRIMARY KEY,
         alert_id        VARCHAR(64)   NOT NULL,
         _mirror_row_id  BIGINT        NOT NULL,
         disposition     VARCHAR(32)   NOT NULL,
         reason          NVARCHAR(512) NULL,
         analyst         NVARCHAR(256) NOT NULL,
         decided_at      DATETIME2(3)  NOT NULL CONSTRAINT DF_disp_at DEFAULT SYSUTCDATETIME()
       )""",

    """IF OBJECT_ID('ops.[case]') IS NULL
       CREATE TABLE ops.[case] (
         case_id          VARCHAR(64)   NOT NULL PRIMARY KEY,
         _mirror_row_id   BIGINT        NOT NULL,
         state            VARCHAR(32)   NOT NULL,
         owner            NVARCHAR(256) NULL,
         sla_due_at       DATETIME2(3)  NULL,
         resolution       VARCHAR(64)   NULL,
         recovered_amount DECIMAL(18,2) NULL,
         opened_at        DATETIME2(3)  NOT NULL CONSTRAINT DF_case_at DEFAULT SYSUTCDATETIME()
       )""",

    # Append only on purpose: regulated casework needs how a case moved, not
    # just where it ended up, and it is what makes the SLA clock auditable.
    """IF OBJECT_ID('ops.case_event') IS NULL
       CREATE TABLE ops.case_event (
         event_id   BIGINT IDENTITY(1,1) PRIMARY KEY,
         case_id    VARCHAR(64)   NOT NULL,
         from_state VARCHAR(32)   NULL,
         to_state   VARCHAR(32)   NOT NULL,
         actor      NVARCHAR(256) NOT NULL,
         note       NVARCHAR(512) NULL,
         at         DATETIME2(3)  NOT NULL CONSTRAINT DF_evt_at DEFAULT SYSUTCDATETIME()
       )""",

    """IF OBJECT_ID('ops.kyc_action') IS NULL
       CREATE TABLE ops.kyc_action (
         action_id       BIGINT IDENTITY(1,1) PRIMARY KEY,
         customer_id     VARCHAR(64)   NOT NULL,
         action          VARCHAR(64)   NOT NULL,
         owner           NVARCHAR(256) NULL,
         next_review_due DATE          NULL,
         at              DATETIME2(3)  NOT NULL CONSTRAINT DF_kyc_at DEFAULT SYSUTCDATETIME()
       )""",

    # Current owner only. History of ownership lives in case_event for cases;
    # this table is deliberately a latest-state table so a queue can join to it
    # without a window function.
    """IF OBJECT_ID('ops.assignment') IS NULL
       CREATE TABLE ops.assignment (
         item_type   VARCHAR(32)   NOT NULL,
         item_id     VARCHAR(64)   NOT NULL,
         assignee    NVARCHAR(256) NOT NULL,
         assigned_at DATETIME2(3)  NOT NULL CONSTRAINT DF_asg_at DEFAULT SYSUTCDATETIME(),
         CONSTRAINT PK_assignment PRIMARY KEY (item_type, item_id)
       )""",

    "IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_disp_alert') "
    "CREATE INDEX IX_disp_alert ON ops.alert_disposition (alert_id)",
    "IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_evt_case') "
    "CREATE INDEX IX_evt_case ON ops.case_event (case_id, at)",
]

TABLES = ["ops.alert_disposition", "ops.[case]", "ops.case_event",
          "ops.kyc_action", "ops.assignment"]


def token():
    """Silently reuse the Fabric CLI's cached credential."""
    import msal
    from msal_extensions import (FilePersistenceWithDataProtection,
                                 PersistedTokenCache)

    with open(os.path.join(FAB_DIR, "auth.json"), encoding="utf-8") as fh:
        auth = json.load(fh)

    # cache.bin is DPAPI-encrypted, not JSON, so it has to be read through the
    # same persistence layer that wrote it.
    cache = PersistedTokenCache(
        FilePersistenceWithDataProtection(os.path.join(FAB_DIR, "cache.bin")))

    tenant = auth.get("fab_tenant_id") or auth.get("tenant_id")
    app = msal.PublicClientApplication(
        auth.get("client_id", "5814bfb4-2705-4994-b8d6-39aabeb5eaeb"),
        authority="https://login.microsoftonline.com/" + tenant,
        token_cache=cache)

    accounts = app.get_accounts()
    if not accounts:
        raise SystemExit("no cached account. Run: fab auth login")
    res = app.acquire_token_silent([SCOPE], account=accounts[0])
    if not res or "access_token" not in res:
        raise SystemExit("silent token failed for the SQL audience. "
                         "Run: fab auth login")
    return res["access_token"]


def connect():
    import pyodbc
    tok = token().encode("utf-16-le")
    packed = struct.pack("<i", len(tok)) + tok
    con = pyodbc.connect(
        "Driver={ODBC Driver 18 for SQL Server};Server=%s;Database=%s;"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=60"
        % (SERVER, DATABASE),
        attrs_before={SQL_COPT_SS_ACCESS_TOKEN: packed})
    con.autocommit = True
    return con


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ddl", action="store_true")
    p.add_argument("--show", action="store_true")
    p.add_argument("--sql")
    args = p.parse_args()

    con = connect()
    cur = con.cursor()

    if args.ddl:
        for stmt in DDL:
            cur.execute(stmt)
            print("ok: %s" % " ".join(stmt.split())[:76])
        print("\nDDL complete.")

    if args.sql:
        cur.execute(args.sql)
        if cur.description:
            cols = [d[0] for d in cur.description]
            print(" | ".join(cols))
            for row in cur.fetchall():
                print(" | ".join(str(v) for v in row))
        else:
            print("rows affected: %d" % cur.rowcount)

    if args.show:
        print("%-28s %s" % ("TABLE", "ROWS"))
        for t in TABLES:
            cur.execute("SELECT count(*) FROM " + t)
            print("%-28s %d" % (t, cur.fetchone()[0]))

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
