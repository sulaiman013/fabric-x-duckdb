"""Write-back functions for the financial crime console.

Each function is invoked from an operational surface in the app and writes to
`fincrime_ops`, the Fabric SQL database. The mirrored database is read-only by
design, so this is where analyst decisions live.

Two conventions are forced by the platform rather than chosen:

* **Parameter names are camelCase.** User data functions reject underscores in
  parameter names, so `alertId` rather than `alert_id`.
* **Every function returns a string.** A Power BI translytical button surfaces
  the return value as its result message, and a string is what it can display.

`UserThrownError` is used for business-rule failures, which reach the caller as
a clean message instead of a stack trace.
"""

import datetime
import logging

import fabric.functions as fn

udf = fn.UserDataFunctions()

# NOTE: the alias is repeated as a literal in every @udf.connection below.
# It cannot be a constant: Fabric parses the decorator statically rather
# than evaluating it, so `alias=ALIAS` is read as the alias "ALIAS" and
# fails at invocation with AliasDoesNotExist.

# Closed vocabularies. Validating here rather than in the UI means an invocation
# from a pipeline or the REST endpoint cannot write a state the reports do not
# know how to display.
VERDICTS = ("CONFIRMED_FRAUD", "FALSE_POSITIVE", "ESCALATED", "PENDING_INFO")
CASE_STATES = ("OPEN", "INVESTIGATING", "AWAITING_CUSTOMER", "RESOLVED", "CLOSED")
ITEM_TYPES = ("ALERT", "CASE", "KYC")
KYC_ACTIONS = ("REVIEW_STARTED", "DOCS_REQUESTED", "DOCS_RECEIVED",
               "RISK_RERATED", "REVIEW_COMPLETED", "ESCALATED_TO_MLRO")


def _one_of(value, allowed, label):
    """Validate against a closed vocabulary, or fail with a usable message."""
    if value not in allowed:
        raise fn.UserThrownError(
            "%s must be one of: %s" % (label, ", ".join(allowed)),
            {label: value})
    return value


@udf.connection(argName="sqlDb", alias="fincrimeops")
@udf.function()
def disposition_alert(sqlDb: fn.FabricSqlConnection, alertId: str,
                      mirrorRowId: int, verdict: str, reason: str,
                      analyst: str) -> str:
    """Record an analyst decision on one alert."""
    _one_of(verdict, VERDICTS, "verdict")
    if verdict == "CONFIRMED_FRAUD" and not (reason or "").strip():
        raise fn.UserThrownError(
            "A confirmed fraud decision requires a reason.", {"alertId": alertId})

    con = sqlDb.connect()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO ops.alert_disposition "
        "(alert_id, _mirror_row_id, disposition, reason, analyst) "
        "VALUES (?, ?, ?, ?, ?)",
        alertId, mirrorRowId, verdict, reason, analyst)
    con.commit()
    cur.close()
    con.close()

    logging.info("alert %s dispositioned %s by %s", alertId, verdict, analyst)
    return "Alert %s recorded as %s." % (alertId, verdict)


@udf.connection(argName="sqlDb", alias="fincrimeops")
@udf.function()
def assign_item(sqlDb: fn.FabricSqlConnection, itemType: str, itemId: str,
                assignee: str) -> str:
    """Set the current owner of a work item, replacing any existing owner."""
    _one_of(itemType, ITEM_TYPES, "itemType")

    con = sqlDb.connect()
    cur = con.cursor()
    # Latest-state table, so an upsert rather than an append. MERGE keeps it to
    # one round trip and one statement.
    cur.execute(
        "MERGE ops.assignment AS t "
        "USING (SELECT ? AS item_type, ? AS item_id, ? AS assignee) AS s "
        "ON t.item_type = s.item_type AND t.item_id = s.item_id "
        "WHEN MATCHED THEN UPDATE SET assignee = s.assignee, "
        "  assigned_at = SYSUTCDATETIME() "
        "WHEN NOT MATCHED THEN INSERT (item_type, item_id, assignee) "
        "  VALUES (s.item_type, s.item_id, s.assignee);",
        itemType, itemId, assignee)
    con.commit()
    cur.close()
    con.close()

    return "%s %s assigned to %s." % (itemType.title(), itemId, assignee)


@udf.connection(argName="sqlDb", alias="fincrimeops")
@udf.function()
def advance_case(sqlDb: fn.FabricSqlConnection, caseId: str, toState: str,
                 actor: str, note: str = "") -> str:
    """Move a case to a new state and append the transition to its history."""
    _one_of(toState, CASE_STATES, "toState")

    con = sqlDb.connect()
    cur = con.cursor()

    cur.execute("SELECT state FROM ops.[case] WHERE case_id = ?", caseId)
    row = cur.fetchone()
    if row is None:
        cur.close()
        con.close()
        raise fn.UserThrownError("No such case: %s" % caseId, {"caseId": caseId})

    from_state = row[0]
    if from_state == toState:
        cur.close()
        con.close()
        return "Case %s is already %s." % (caseId, toState)

    # The update and the event are one transaction on purpose. A state change
    # with no event, or an event with no state change, would make the SLA clock
    # unauditable, which is the whole reason the event table exists.
    cur.execute("UPDATE ops.[case] SET state = ? WHERE case_id = ?",
                toState, caseId)
    cur.execute(
        "INSERT INTO ops.case_event (case_id, from_state, to_state, actor, note) "
        "VALUES (?, ?, ?, ?, ?)",
        caseId, from_state, toState, actor, note)
    con.commit()
    cur.close()
    con.close()

    return "Case %s moved from %s to %s." % (caseId, from_state, toState)


@udf.connection(argName="sqlDb", alias="fincrimeops")
@udf.function()
def record_kyc_action(sqlDb: fn.FabricSqlConnection, customerId: str,
                      action: str, owner: str,
                      nextReviewDue: str = "") -> str:
    """Record one KYC remediation action against a customer."""
    _one_of(action, KYC_ACTIONS, "action")

    due = None
    if nextReviewDue:
        try:
            due = datetime.date.fromisoformat(nextReviewDue[:10])
        except ValueError:
            raise fn.UserThrownError(
                "nextReviewDue must be ISO format, for example 2026-12-31.",
                {"nextReviewDue": nextReviewDue})

    con = sqlDb.connect()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO ops.kyc_action (customer_id, action, owner, next_review_due) "
        "VALUES (?, ?, ?, ?)",
        customerId, action, owner, due)
    con.commit()
    cur.close()
    con.close()

    tail = " Next review %s." % due if due else ""
    return "Recorded %s for customer %s.%s" % (action, customerId, tail)


@udf.connection(argName="sqlDb", alias="fincrimeops")
@udf.function()
def ops_health(sqlDb: fn.FabricSqlConnection) -> str:
    """Row counts per operational table. Used to prove write-back end to end."""
    con = sqlDb.connect()
    cur = con.cursor()
    out = []
    for t in ("ops.alert_disposition", "ops.[case]", "ops.case_event",
              "ops.kyc_action", "ops.assignment"):
        cur.execute("SELECT count(*) FROM " + t)
        out.append("%s=%d" % (t.replace("ops.", "").strip("[]"),
                              cur.fetchone()[0]))
    cur.close()
    con.close()
    return ", ".join(out)
