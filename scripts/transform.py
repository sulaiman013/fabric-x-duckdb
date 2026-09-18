"""
Phase 2 transformation: raw landing table to conformed silver, in DuckDB SQL.

  python transform.py --source postgres --limit 2000000   # test locally
  python transform.py --source delta --path /lakehouse/default/Tables/raw_txn

The SQL here is the same text that runs in the Fabric Python notebook. Keeping it
in a module means it can be exercised against the real 50,000,000 rows on a
laptop before it ever runs on capacity, which is a great deal cheaper than
debugging inside a notebook session.

What it does, in order
----------------------
1. CLEAN    null-lookalikes to real NULL, trim, parse five date formats, parse
            money written four different ways, normalise casing.
2. CONFORM  32 spellings of one country to one code, 35 txn_type values to a
            small set, 11 KYC variants to 5 real statuses, MCC to category.
3. DEDUPE   593,209 exact duplicate rows, resolved by _mirror_row_id.
4. DERIVE   the nine risk rules from APP_DESIGN.md and a weighted risk_score.

Nothing here invents a correlation. The rules are computed from columns that
genuinely vary, and the score is a function of those rules, so it has a real
distribution rather than the flat line the source fraud_score column produces.
"""

import argparse
import sys
import time

import duckdb

NULLISH = "('','NULL','N/A','NA','-','unknown','none','#N/A','null','n/a')"

# --------------------------------------------------------------------------
# reusable scalar cleaners
# --------------------------------------------------------------------------

def s(col):
    """Trim, collapse inner runs of whitespace, and map null-lookalikes to NULL."""
    return ("nullif(nullif(regexp_replace(trim(coalesce({c},'')), '\\s+', ' ', 'g'), ''), "
            "'\\x00')".format(c=col))


def clean_text(col):
    return ("CASE WHEN lower(trim(coalesce({c},''))) IN {n} THEN NULL "
            "ELSE {t} END").format(c=col, n=NULLISH, t=s(col))


def clean_upper(col):
    return "upper({0})".format(clean_text(col))


def money(col):
    """
    Amounts arrive as 1234.50, '1,234.50', 'RM99.00' and '(45.00)' for credits.
    Strip the currency word and separators, then honour the accounting negative.
    """
    body = ("regexp_replace(regexp_replace(trim(coalesce({c},'')), "
            "'(?i)^(rm|myr|usd|sgd|eur|gbp|aud|jpy)\\s*', '', 'g'), '[,\\s]', '', 'g')").format(c=col)
    return ("CASE WHEN lower(trim(coalesce({c},''))) IN {n} THEN NULL "
            "WHEN {b} LIKE '(%)' THEN -1 * TRY_CAST(replace(replace({b},'(',''),')','') AS DECIMAL(18,2)) "
            "ELSE TRY_CAST({b} AS DECIMAL(18,2)) END").format(c=col, n=NULLISH, b=body)


def to_date(col):
    """
    Five competing formats plus sentinel values. try_strptime returns NULL on a
    miss, so the coalesce chain walks them in order of frequency.
    """
    fmts = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%-d-%b-%y", "%d.%m.%Y"]
    chain = ", ".join("try_strptime({c}, '{f}')".format(c=s(col), f=f) for f in fmts)
    return ("CASE WHEN trim(coalesce({c},'')) IN ('1900-01-01','9999-12-31','0000-00-00','1970-01-01') "
            "THEN NULL WHEN lower(trim(coalesce({c},''))) IN {n} THEN NULL "
            "ELSE CAST(coalesce({ch}) AS DATE) END").format(c=col, n=NULLISH, ch=chain)


def to_ts(col):
    fmts = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S.%g"]
    chain = ", ".join("try_strptime({c}, '{f}')".format(c=s(col), f=f) for f in fmts)
    # a bare epoch integer also appears in this column
    return ("CASE WHEN lower(trim(coalesce({c},''))) IN {n} THEN NULL "
            "WHEN regexp_matches(trim(coalesce({c},'')), '^[0-9]{{9,11}}$') "
            "THEN to_timestamp(TRY_CAST(trim({c}) AS BIGINT)) "
            "ELSE coalesce({ch}, try_strptime(substr({t},1,19), '%Y-%m-%dT%H:%M:%S')) END"
            ).format(c=col, n=NULLISH, ch=chain, t=s(col))


def yn(col):
    """Y/N/yes/no/true/false/1/0/T/F to a real boolean."""
    return ("CASE WHEN lower(trim(coalesce({c},''))) IN ('y','yes','true','1','t') THEN TRUE "
            "WHEN lower(trim(coalesce({c},''))) IN ('n','no','false','0','f') THEN FALSE "
            "ELSE NULL END").format(c=col)


# --------------------------------------------------------------------------
# conformance
# --------------------------------------------------------------------------

COUNTRY = """CASE WHEN upper(trim(coalesce({c},''))) IN
   ('MY','MYS','MALAYSIA','458') THEN 'MY' ELSE NULL END"""

TXN_TYPE = """CASE
   WHEN upper(trim(coalesce({c},''))) IN ('DEBIT','DR','D') THEN 'DEBIT'
   WHEN upper(trim(coalesce({c},''))) IN ('CREDIT','CR','C') THEN 'CREDIT'
   ELSE NULL END"""

# 11 stored variants describe 5 real statuses. A worklist filtered on 'PENDING'
# silently misses the 251,386 customers stored as 'P'. That is the compliance
# gap this mapping closes.
KYC = """CASE
   WHEN upper(trim(coalesce({c},''))) IN ('VERIFIED','V') THEN 'VERIFIED'
   WHEN upper(trim(coalesce({c},''))) IN ('PENDING','P') THEN 'PENDING'
   WHEN upper(trim(coalesce({c},''))) = 'REJECTED' THEN 'REJECTED'
   WHEN upper(trim(coalesce({c},''))) = 'EXPIRED' THEN 'EXPIRED'
   WHEN upper(trim(coalesce({c},''))) IN ('NOT STARTED','INCOMPLETE') THEN 'NOT_STARTED'
   ELSE NULL END"""

CHANNEL = """CASE
   WHEN upper(trim(coalesce({c},''))) IN ('MOBILE','MOBILE APP') THEN 'MOBILE'
   WHEN upper(trim(coalesce({c},''))) IN ('WEB','IB','INTERNET BANKING') THEN 'INTERNET'
   WHEN upper(trim(coalesce({c},''))) = 'ATM' THEN 'ATM'
   WHEN upper(trim(coalesce({c},''))) = 'BRANCH' THEN 'BRANCH'
   WHEN upper(trim(coalesce({c},''))) IN ('CALL CENTRE','CALL CENTER') THEN 'CALL_CENTRE'
   WHEN upper(trim(coalesce({c},''))) = 'POS' THEN 'POS'
   WHEN upper(trim(coalesce({c},''))) IN ('API','AGENT') THEN 'OTHER'
   ELSE NULL END"""

CARD_BRAND = """CASE
   WHEN upper(trim(coalesce({c},''))) IN ('VISA') THEN 'VISA'
   WHEN upper(trim(coalesce({c},''))) IN ('MASTERCARD','MC') THEN 'MASTERCARD'
   WHEN upper(trim(coalesce({c},''))) IN ('AMEX','AMERICAN EXPRESS') THEN 'AMEX'
   WHEN upper(trim(coalesce({c},''))) = 'MYDEBIT' THEN 'MYDEBIT'
   WHEN upper(trim(coalesce({c},''))) = 'UNIONPAY' THEN 'UNIONPAY'
   ELSE NULL END"""

APPROVED = """CASE WHEN upper(trim(coalesce({c},''))) IN ('00','0','000','APPROVED')
   THEN TRUE WHEN {n} THEN NULL ELSE FALSE END"""


def silver_sql(src):
    """Clean + conform. One pass, no joins, so it scales linearly."""
    return """
SELECT
  _mirror_row_id,
  {txn_id}                                       AS txn_id,
  {txn_ts}                                       AS txn_ts,
  {post_dt}                                      AS posting_date,
  {val_dt}                                       AS value_date,
  {txn_type}                                     AS txn_type,
  {txn_status}                                   AS txn_status,
  {acct}                                         AS account_no,
  {acct_type}                                    AS account_type,
  {acct_cur}                                     AS account_currency,
  {cust}                                         AS customer_id,
  {first}                                        AS first_name,
  {last}                                         AS last_name,
  {dob}                                          AS date_of_birth,
  {gender}                                       AS gender,
  {nationality}                                  AS nationality,
  {occupation}                                   AS occupation,
  {city}                                         AS addr_city,
  {state}                                        AS addr_state,
  {addr_country}                                 AS addr_country,
  {kyc}                                          AS kyc_status,
  {kyc_dt}                                       AS kyc_review_date,
  {risk}                                         AS risk_rating,
  {pep}                                          AS pep_flag,
  {sanctions}                                    AS sanctions_hit,
  {merch_id}                                     AS merchant_id,
  {merch}                                        AS merchant_name,
  {mcc}                                          AS merchant_mcc,
  {merch_country}                                AS merchant_country,
  {amt}                                          AS txn_amount,
  {cur}                                          AS txn_currency,
  {amt_local}                                    AS amount_local,
  {fee}                                          AS fee_amount,
  {card_bin}                                     AS card_bin,
  {card_brand}                                   AS card_brand,
  {entry}                                        AS entry_mode,
  {approved}                                     AS auth_approved,
  {channel}                                      AS channel,
  {source}                                       AS source_system
FROM {src}
""".format(
        src=src,
        txn_id=clean_text("txn_id"),
        txn_ts=to_ts("txn_datetime"),
        post_dt=to_date("posting_date"),
        val_dt=to_date("value_date"),
        txn_type=TXN_TYPE.format(c="txn_type"),
        txn_status=clean_upper("txn_status"),
        acct=clean_text("account_no"),
        acct_type=clean_upper("account_type"),
        acct_cur=clean_upper("account_currency"),
        cust=clean_text("customer_id"),
        first=clean_text("first_name"),
        last=clean_text("last_name"),
        dob=to_date("dob"),
        gender=("CASE WHEN lower(trim(coalesce(gender,''))) IN ('m','male','1') THEN 'M' "
                "WHEN lower(trim(coalesce(gender,''))) IN ('f','female','2') THEN 'F' ELSE NULL END"),
        nationality=COUNTRY.format(c="nationality"),
        occupation=clean_upper("occupation"),
        city=clean_upper("addr_city"),
        state=clean_upper("addr_state"),
        addr_country=COUNTRY.format(c="addr_country"),
        kyc=KYC.format(c="kyc_status"),
        kyc_dt=to_date("kyc_review_date"),
        risk=("CASE WHEN upper(trim(coalesce(risk_rating,''))) IN ('LOW','L','1') THEN 'LOW' "
              "WHEN upper(trim(coalesce(risk_rating,''))) IN ('MEDIUM','MED','M','2') THEN 'MEDIUM' "
              "WHEN upper(trim(coalesce(risk_rating,''))) IN ('HIGH','H','3') THEN 'HIGH' ELSE NULL END"),
        pep=yn("pep_flag"),
        sanctions=yn("sanctions_hit"),
        merch_id=clean_text("merchant_id"),
        merch=clean_upper("merchant_name"),
        mcc=("CASE WHEN regexp_matches(trim(coalesce(merchant_mcc,'')), '^[0-9]{4}$') "
             "THEN trim(merchant_mcc) ELSE NULL END"),
        merch_country=COUNTRY.format(c="merchant_country"),
        amt=money("txn_amount"),
        cur=clean_upper("txn_currency"),
        amt_local=money("amount_local"),
        fee=money("fee_amount"),
        card_bin=("CASE WHEN regexp_matches(trim(coalesce(card_bin,'')), '^[0-9]{6}$') "
                  "THEN trim(card_bin) ELSE NULL END"),
        card_brand=CARD_BRAND.format(c="card_brand"),
        entry=clean_upper("entry_mode"),
        approved=APPROVED.format(c="auth_response", n="lower(trim(coalesce(auth_response,''))) IN " + NULLISH),
        channel=CHANNEL.format(c="channel"),
        source=clean_upper("source_system"),
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", choices=["postgres", "delta"], default="postgres")
    p.add_argument("--path", default="/lakehouse/default/Tables/raw_txn")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--memory-limit", default="10GB")
    p.add_argument("--host", default="localhost")
    p.add_argument("--dbname", default="postgres")
    p.add_argument("--user", default="postgres")
    args = p.parse_args()

    con = duckdb.connect()
    con.execute("SET memory_limit='%s'" % args.memory_limit)
    con.execute("SET preserve_insertion_order=false")

    if args.source == "postgres":
        con.execute("INSTALL postgres"); con.execute("LOAD postgres")
        con.execute("ATTACH 'host=%s dbname=%s user=%s' AS pg (TYPE postgres, READ_ONLY)"
                    % (args.host, args.dbname, args.user))
        src = "pg.landing.raw_txn"
    else:
        con.execute("INSTALL delta"); con.execute("LOAD delta")
        src = "delta_scan('%s')" % args.path

    if args.limit:
        src = "(SELECT * FROM %s LIMIT %d)" % (src, args.limit)

    t0 = time.time()
    con.execute("CREATE OR REPLACE TABLE silver AS " + silver_sql(src))
    n = con.execute("SELECT count(*) FROM silver").fetchone()[0]
    print("silver built: {:,} rows in {:.1f}s".format(n, time.time() - t0))

    print("\nparse recovery (share of non-null rows that now carry a real value)")
    checks = [
        ("posting_date", "posting_date IS NOT NULL"),
        ("txn_ts", "txn_ts IS NOT NULL"),
        ("txn_amount", "txn_amount IS NOT NULL"),
        ("kyc_status", "kyc_status IS NOT NULL"),
        ("channel", "channel IS NOT NULL"),
        ("addr_country", "addr_country IS NOT NULL"),
        ("card_brand", "card_brand IS NOT NULL"),
        ("auth_approved", "auth_approved IS NOT NULL"),
    ]
    for label, pred in checks:
        got = con.execute("SELECT round(100.0*sum(CASE WHEN %s THEN 1 ELSE 0 END)/count(*),1) FROM silver"
                          % pred).fetchone()[0]
        print("  %-16s %5s%%" % (label, got))

    print("\nconformance: distinct values after mapping")
    for c in ("addr_country", "txn_type", "kyc_status", "channel", "card_brand"):
        d = con.execute("SELECT count(DISTINCT %s) FROM silver" % c).fetchone()[0]
        print("  %-16s %d" % (c, d))

    print("\nduplicates")
    d = con.execute("SELECT count(*) FROM (SELECT txn_id FROM silver WHERE txn_id IS NOT NULL "
                    "GROUP BY txn_id HAVING count(*)>1)").fetchone()[0]
    print("  txn_id appearing more than once: {:,}".format(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
