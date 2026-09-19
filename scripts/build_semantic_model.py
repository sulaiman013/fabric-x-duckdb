"""
Generate the Direct Lake semantic model as TMDL, ready to import with `fab`.

  python build_semantic_model.py --out C:/tmp/nb/fincrime_model.SemanticModel

The bundled `create_direct_lake_model.py` helper builds a single-table model.
A star with nine tables, eight relationships and measures has to be authored,
so this emits the TMDL directly.

Direct Lake specifics
---------------------
* Every partition is `mode: directLake` with `expressionSource: DatabaseQuery`,
  pointing at the lakehouse SQL endpoint. No data is imported; the model reads
  the V-Ordered Delta files in place.
* Direct Lake is not optional here. The gold layer is rebuilt in place, and an
  import-mode model would only show a rebuild after a refresh while holding a
  second copy of 49.4M rows behind every report.
* `discourageImplicitMeasures` is set so report authors use the defined
  measures rather than dragging raw columns onto a visual, which is how a
  semantic model stays a contract instead of a pile of columns.
"""

import argparse
import io
import json
import os
import uuid

SQL_ENDPOINT = "6xdtv76wvqse5lz63juf6hq7gy-bvxa67rqg6pujc7gfpvoykcypm.datawarehouse.fabric.microsoft.com"
DATABASE = "fincrime"

RM = '"RM "#,0.00'
RM0 = '"RM "#,0'

# name, dataType, formatString or None, hidden
TABLES = {
    "fact_transaction": [
        ("_mirror_row_id", "int64", None, True), ("txn_id", "string", None, False),
        ("date_key", "int64", None, True), ("time_key", "int64", None, True),
        ("customer_key", "int64", None, True), ("merchant_key", "int64", None, True),
        ("channel_key", "int64", None, True), ("card_key", "int64", None, True),
        ("txn_ts", "dateTime", "General Date", False),
        ("txn_type", "string", None, False), ("txn_status", "string", None, False),
        ("txn_amount", "decimal", "#,0.00", False),
        ("txn_currency", "string", None, False),
        ("amount_local", "decimal", "#,0.00", False),
        ("fee_amount", "decimal", "#,0.00", False),
        ("auth_approved", "boolean", None, False),
        ("risk_score", "int64", "#,0", False),
        ("rules_fired", "int64", "#,0", False),
        ("risk_band", "string", None, False)],
    "fact_alert": [
        ("_mirror_row_id", "int64", None, True),
        ("rule_id", "string", None, False),
        ("weight", "int64", "#,0", False)],
    "dim_customer": [
        ("customer_key", "int64", None, True), ("customer_id", "string", None, False),
        ("first_name", "string", None, False), ("last_name", "string", None, False),
        ("gender", "string", None, False),
        ("date_of_birth", "dateTime", "Short Date", False),
        ("occupation", "string", None, False), ("addr_city", "string", None, False),
        ("addr_state", "string", None, False), ("nationality", "string", None, False),
        ("kyc_rank", "int64", None, True), ("ever_pep", "boolean", None, False),
        ("ever_sanctioned", "boolean", None, False),
        ("risk_rank", "int64", None, True), ("txn_count", "int64", "#,0", False)],
    "dim_merchant": [
        ("merchant_key", "int64", None, True), ("merchant_id", "string", None, False),
        ("merchant_name", "string", None, False),
        ("merchant_mcc", "string", None, False),
        ("merchant_country", "string", None, False),
        ("txn_count", "int64", "#,0", False),
        ("is_high_risk_mcc", "boolean", None, False)],
    "dim_channel": [
        ("channel_key", "int64", None, True), ("channel", "string", None, False),
        ("entry_mode", "string", None, False),
        ("is_card_not_present", "boolean", None, False)],
    "dim_card": [
        ("card_key", "int64", None, True), ("card_bin", "string", None, False),
        ("card_brand", "string", None, False)],
    "dim_date": [
        ("date_key", "int64", None, True),
        ("full_date", "dateTime", "Short Date", False),
        ("yr", "int64", None, False), ("qtr", "int64", None, False),
        ("mth", "int64", None, False), ("month_name", "string", None, False),
        ("day_of_month", "int64", None, False),
        ("day_of_week", "int64", None, True), ("day_name", "string", None, False),
        ("is_weekend", "boolean", None, False)],
    "dim_time": [
        ("time_key", "int64", None, True), ("hour_of_day", "int64", None, False),
        ("hour_label", "string", None, False), ("day_part", "string", None, False),
        ("is_odd_hour", "boolean", None, False)],
    "dim_risk_rule": [
        ("rule_id", "string", None, False), ("rule_name", "string", None, False),
        ("weight", "int64", "#,0", False)],
}

MEASURES = {
    "fact_transaction": [
        ("Transactions", "COUNTROWS ( fact_transaction )", "#,0"),
        ("Total Amount", "SUM ( fact_transaction[txn_amount] )", RM),
        ("Distinct Customers", "DISTINCTCOUNT ( fact_transaction[customer_key] )", "#,0"),
        ("Average Risk Score", "AVERAGE ( fact_transaction[risk_score] )", "#,0.0"),
        ("High Risk Transactions",
         'CALCULATE ( [Transactions], fact_transaction[risk_band] = "HIGH" )', "#,0"),
        ("High Risk Rate", "DIVIDE ( [High Risk Transactions], [Transactions] )", "0.00%"),
        ("Exposure at Risk",
         'CALCULATE ( [Total Amount], fact_transaction[risk_band] = "HIGH" )', RM0),
        # Kept on one line deliberately. TMDL is indentation sensitive and a
        # multi-line measure body must be tab indented past the measure itself;
        # mixing in spaces fails the import with a bare "Invalid indentation
        # was detected" and a line number, which is not much to go on.
        ("Approval Rate",
         "DIVIDE ( CALCULATE ( [Transactions], fact_transaction[auth_approved] = TRUE () ), "
         "CALCULATE ( [Transactions], NOT ISBLANK ( fact_transaction[auth_approved] ) ) )",
         "0.0%"),
        ("Cross Border Amount",
         'CALCULATE ( [Total Amount], fact_transaction[txn_currency] <> "MYR" )', RM0),
        # Score-driven alerting. This is the measure the triage queue is built
        # on, and the one that decides how many people the function needs.
        ("Alerts Raised",
         'CALCULATE ( [Transactions], fact_transaction[risk_band] = "HIGH" )', "#,0"),
        ("Alert Rate", "DIVIDE ( [Alerts Raised], [Transactions] )", "0.00%"),
        # Translate the queue into staffing. An analyst clears roughly 50,000
        # alerts a year, so this is the honest cost of a threshold choice, and
        # it is what makes a tuning decision arguable rather than aesthetic.
        ("Analyst Years to Clear", "DIVIDE ( [Alerts Raised], 50000 )", "#,0.0"),
    ],
    # An alert is what a human picks up and works. A rule firing is a
    # contribution to a score, not a work item. Conflating the two produced an
    # 80.18% alert rate, which is 39,614,364 alerts, roughly 792 analyst-years
    # at the ~50,000 alerts an analyst clears annually, or 317 full-time
    # analysts standing behind this dataset. Real transaction monitoring raises
    # an alert when the composite score crosses a threshold.
    "fact_alert": [
        ("Rule Firings", "COUNTROWS ( fact_alert )", "#,0"),
        ("Rule Firings per Transaction", "DIVIDE ( [Rule Firings], [Transactions] )", "#,0.00"),
        ("Transactions With Any Rule",
         "DISTINCTCOUNT ( fact_alert[_mirror_row_id] )", "#,0"),
        ("Any Rule Rate",
         "DIVIDE ( [Transactions With Any Rule], [Transactions] )", "0.0%"),
        # Noise ratio: how many rule firings the team absorbs per real alert.
        ("Rule Firings per Alert", "DIVIDE ( [Rule Firings], [Alerts Raised] )", "#,0.0"),
    ],
}

RELATIONSHIPS = [
    ("fact_transaction", "date_key", "dim_date", "date_key"),
    ("fact_transaction", "time_key", "dim_time", "time_key"),
    ("fact_transaction", "customer_key", "dim_customer", "customer_key"),
    ("fact_transaction", "merchant_key", "dim_merchant", "merchant_key"),
    ("fact_transaction", "channel_key", "dim_channel", "channel_key"),
    ("fact_transaction", "card_key", "dim_card", "card_key"),
    ("fact_alert", "_mirror_row_id", "fact_transaction", "_mirror_row_id"),
    ("fact_alert", "rule_id", "dim_risk_rule", "rule_id"),
]


def tag():
    return str(uuid.uuid4())


def emit_column(name, dtype, fmt, hidden):
    numeric = dtype in ("int64", "decimal")
    s = "\tcolumn %s\n\t\tdataType: %s\n" % (name, dtype)
    if fmt:
        s += "\t\tformatString: %s\n" % fmt
    if hidden:
        s += "\t\tisHidden\n"
    # Surrogate keys must not aggregate. Summing a key is meaningless and is a
    # classic way for a model to produce confident nonsense.
    summarize = "sum" if (numeric and not hidden) else "none"
    s += "\t\tlineageTag: %s\n\t\tsummarizeBy: %s\n\t\tsourceColumn: %s\n\n" % (
        tag(), summarize, name)
    s += "\t\tannotation SummarizationSetBy = Automatic\n\n"
    return s


def build(out):
    os.makedirs(os.path.join(out, "definition", "tables"), exist_ok=True)

    for table, cols in TABLES.items():
        body = "table %s\n\tlineageTag: %s\n\n" % (table, tag())
        for c in cols:
            body += emit_column(*c)
        for mname, expr, fmt in MEASURES.get(table, []):
            body += "\tmeasure '%s' =\n\t\t\t%s\n\t\tformatString: %s\n\t\tlineageTag: %s\n\n" % (
                mname, expr, fmt, tag())
        body += (
            "\tpartition %s = entity\n\t\tmode: directLake\n\t\tsource\n"
            "\t\t\tentityName: gold_%s\n\t\t\texpressionSource: DatabaseQuery\n\n"
            "\tannotation PBI_ResultType = Table\n\n" % (table, table))
        io.open(os.path.join(out, "definition", "tables", table + ".tmdl"),
                "w", encoding="utf-8").write(body)

    rel = ""
    for ft, fc, tt, tc in RELATIONSHIPS:
        rel += "relationship %s\n\tfromColumn: %s.%s\n\ttoColumn: %s.%s\n\n" % (
            tag(), ft, fc, tt, tc)
    io.open(os.path.join(out, "definition", "relationships.tmdl"),
            "w", encoding="utf-8").write(rel)

    io.open(os.path.join(out, "definition", "expressions.tmdl"),
            "w", encoding="utf-8").write(
        "expression DatabaseQuery =\n\t\tlet\n"
        '\t\t\tdatabase = Sql.Database("%s", "%s")\n'
        "\t\tin\n\t\t\tdatabase\n"
        "\tlineageTag: %s\n\n" % (SQL_ENDPOINT, DATABASE, tag()))

    io.open(os.path.join(out, "definition", "database.tmdl"),
            "w", encoding="utf-8").write("database\n\tcompatibilityLevel: 1604\n\n")

    model = ("model Model\n\tculture: en-US\n"
             "\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
             "\tdiscourageImplicitMeasures\n"
             "\tsourceQueryCulture: en-US\n\n"
             '\tannotation PBI_QueryOrder = ["DatabaseQuery"]\n\n')
    for t in TABLES:
        model += "ref table %s\n" % t
    io.open(os.path.join(out, "definition", "model.tmdl"),
            "w", encoding="utf-8").write(model)

    io.open(os.path.join(out, "definition.pbism"), "w", encoding="utf-8").write(
        json.dumps({"version": "4.2", "settings": {}}, indent=2))
    io.open(os.path.join(out, ".platform"), "w", encoding="utf-8").write(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/"
                   "platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": "fincrime_model"},
        "config": {"version": "2.0", "logicalId": tag()}}, indent=2))

    print("tables        : %d" % len(TABLES))
    print("relationships : %d" % len(RELATIONSHIPS))
    print("measures      : %d" % sum(len(v) for v in MEASURES.values()))
    print("written to    : %s" % out)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="C:/tmp/nb/fincrime_model.SemanticModel")
    build(p.parse_args().out)
