"""
Column definitions for the raw banking / fintech transaction extract.

This models a WIDE, UNGOVERNED landing-zone export: the kind of file a core
banking system, a card switch and a CRM all dump into, which then gets handed
to the data team as-is. Every column is emitted as text and the mess is
injected at generation time, so nothing downstream has to pretend the data
is clean.

Mess profile = "realistic": roughly 10-20% of values are affected by nulls,
null-lookalikes, casing drift, whitespace, mixed date formats, numbers stored
as text and inconsistent code sets.
"""

# ---------------------------------------------------------------------------
# SQL building helpers
# ---------------------------------------------------------------------------


def q(s):
    """Quote a python string as a SQL literal."""
    return "'" + str(s).replace("'", "''") + "'"


def pick(vals, r=None):
    """Pick uniformly from a literal list. DuckDB lists are 1-indexed."""
    r = r or "random()"
    lit = ",".join(q(v) for v in vals)
    return "([" + lit + "])[1+CAST(floor(" + r + "*" + str(len(vals)) + ") AS INTEGER)]"


def pick_det(vals, key, salt=1):
    """
    Pick from a literal list deterministically, keyed on an entity id.

    Used for anything that belongs to an entity rather than to a single
    transaction: a customer's name, a merchant's category, a card's brand.
    Because the choice is hash(entity_id) rather than random(), the same
    customer resolves to the same underlying value on every one of their
    rows, across chunks and across runs. The mess layer is applied on top,
    which is what produces the real-world "same customer, three spellings"
    problem instead of "same customer, three different people".
    """
    lit = ",".join(q(v) for v in vals)
    return ("([" + lit + "])[1+CAST((hash(" + key + "*" + str(salt) + ") % "
            + str(len(vals)) + ") AS INTEGER)]")


def weighted(pairs, r=None):
    """pairs = [(threshold, sql_expr), ...] ascending; the last is the ELSE branch."""
    r = r or "random()"
    out = "CASE"
    for thr, expr in pairs[:-1]:
        out += " WHEN " + r + " < " + str(thr) + " THEN " + expr
    out += " ELSE " + pairs[-1][1] + " END"
    return out


NULL_JUNK = ["", "NULL", "N/A", "NA", "-", "unknown", "none", "#N/A"]


def messy(expr, null_rate=0.06, pad_rate=0.02):
    """Wrap a clean expression with null-ish junk and stray whitespace."""
    e = expr
    if pad_rate:
        e = (
            "CASE WHEN random()<" + str(pad_rate) + " THEN ' '||(" + e + ")||'  ' "
            "WHEN random()<" + str(pad_rate / 2) + " THEN (" + e + ")||' ' "
            "ELSE " + e + " END"
        )
    if null_rate:
        e = (
            "CASE WHEN random()<" + str(null_rate) + " THEN " + pick(NULL_JUNK) + " "
            "WHEN random()<" + str(null_rate * 0.3) + " THEN NULL "
            "ELSE " + e + " END"
        )
    return e


def money(col, null_rate=0.02):
    """Numbers that arrived as text, in several incompatible conventions."""
    e = weighted([
        (0.05, "format('{:,.2f}', " + col + ")"),
        (0.08, "'RM'||format('{:.2f}', " + col + ")"),
        (0.10, "'('||format('{:.2f}', abs(" + col + "))||')'"),
        (0.12, "CAST(" + col + " AS VARCHAR)"),
        (1.0, "format('{:.2f}', " + col + ")"),
    ])
    return messy(e, null_rate=null_rate, pad_rate=0.01)


def mixed_date(col, null_rate=0.05, sentinel_rate=0.02):
    """The same date written five different ways, plus sentinel values."""
    e = weighted([
        (0.55, "strftime(" + col + ",'%Y-%m-%d')"),
        (0.75, "strftime(" + col + ",'%d/%m/%Y')"),
        (0.85, "strftime(" + col + ",'%m/%d/%Y')"),
        (0.93, "strftime(" + col + ",'%-d-%b-%y')"),
        (1.0, "strftime(" + col + ",'%d.%m.%Y')"),
    ])
    if sentinel_rate:
        e = (
            "CASE WHEN random()<" + str(sentinel_rate) + " THEN "
            + pick(["1900-01-01", "9999-12-31", "0000-00-00", "1970-01-01"])
            + " ELSE " + e + " END"
        )
    return messy(e, null_rate=null_rate, pad_rate=0.01)


def mixed_ts(col, null_rate=0.03):
    """Timestamps with and without timezone, plus separator drift and epochs."""
    e = weighted([
        (0.50, "strftime(" + col + ",'%Y-%m-%d %H:%M:%S')"),
        (0.70, "strftime(" + col + ",'%Y-%m-%dT%H:%M:%S')"),
        (0.80, "strftime(" + col + ",'%Y-%m-%dT%H:%M:%S')||'+08:00'"),
        (0.88, "strftime(" + col + ",'%d/%m/%Y %H:%M')"),
        (0.94, "CAST(CAST(epoch(" + col + ") AS BIGINT) AS VARCHAR)"),
        (1.0, "strftime(" + col + ",'%Y-%m-%d %H:%M:%S.000')"),
    ])
    return messy(e, null_rate=null_rate, pad_rate=0.01)


# ---------------------------------------------------------------------------
# Value pools - Malaysia / SEA retail banking flavour
# ---------------------------------------------------------------------------

FIRST = ["Ahmad", "Muhammad", "Nurul", "Siti", "Mohd", "Wei Ming", "Li Hua", "Jian",
         "Rajesh", "Priya", "Kumar", "Farah", "Aisyah", "Hafiz", "Zainal", "Chong",
         "Tan", "Lim", "Suresh", "Devi", "Amirul", "Syafiq", "Mei Ling", "Kok Wai"]

LAST = ["bin Abdullah", "binti Hassan", "Tan", "Lim", "Wong", "Chong", "Ng", "Lee",
        "a/l Subramaniam", "a/p Krishnan", "Ibrahim", "Ismail", "Yusof", "Rahman",
        "Cheah", "Goh", "Teoh", "Nair", "Pillai", "Osman"]

CITIES = ["KUALA LUMPUR", "kuala lumpur", "Kuala Lumpur", "K.Lumpur", "KL",
          "PETALING JAYA", "Petaling Jaya", "PJ", "Shah Alam", "SHAH ALAM",
          "Johor Bahru", "JOHOR BAHRU", "JB", "Penang", "PENANG", "George Town",
          "Ipoh", "IPOH", "Melaka", "Malacca", "Kota Kinabalu", "Kuching",
          "Seremban", "Cyberjaya", "Putrajaya", "Subang Jaya"]

STATES = ["Selangor", "SELANGOR", "selangor", "W.P. Kuala Lumpur", "WP KL",
          "Kuala Lumpur", "Johor", "JOHOR", "Pulau Pinang", "Penang", "PENANG",
          "Perak", "Melaka", "Sabah", "Sarawak", "Negeri Sembilan", "N.Sembilan",
          "Kedah", "Pahang"]

COUNTRY = ["MY", "MYS", "Malaysia", "malaysia", "MALAYSIA", "458", "My", " MY"]

MERCHANTS = ["TESCO STORES", "Tesco Stores Sdn Bhd", "LOTUSS   ", "AEON CO (M) BHD",
             "99 SPEEDMART", "7-ELEVEN MALAYSIA", "SHELL MALAYSIA", "PETRONAS DAGANGAN",
             "GRAB RIDES", "GrabFood", "grab*food", "FOODPANDA MY", "Shopee Pay",
             "SHOPEE MOBILE MY", "LAZADA MALAYSIA", "Lazada", "TOUCH N GO EWALLET",
             "TNG DIGITAL", "MCDONALDS MALAYSIA", "McDonald's", "STARBUCKS COFFEE",
             "ZUS Coffee", "WATSONS", "GUARDIAN HEALTH", "MYDIN MOHAMED", "JAYA GROCER",
             "VILLAGE GROCER", "UNIQLO MALAYSIA", "H&M MALAYSIA", "PADINI CONCEPT",
             "AIRASIA BHD", "MALAYSIA AIRLINES", "AGODA.COM", "BOOKING.COM",
             "NETFLIX.COM", "SPOTIFY AB", "APPLE.COM/BILL", "GOOGLE *SERVICES",
             "TENAGA NASIONAL", "SYABAS", "MAXIS BERHAD", "CELCOM AXIATA",
             "DIGI TELECOM", "TIME DOTCOM", "ASTRO MALAYSIA", "MBB ATM WITHDRAWAL",
             "CIMB CLICKS TRF"]

MCC = ["5411", "5541", "5812", "5814", "5912", "5691", "4722", "4899", "4814",
       "6011", "6012", "7011", "5311", "5999", "4816", "5045", "5732", "0000", "9999"]

MCC_DESC = ["Grocery Stores", "grocery stores", "Service Stations", "Eating Places",
            "FAST FOOD", "Drug Stores", "Travel Agencies", "Cable/Telecom",
            "Telecom Services", "Financial Institution", "FINANCIAL INST",
            "Hotels", "Department Stores", "Misc Retail", "MISC", "Computer Stores"]

BANKS = ["MBB", "CIMB", "PBB", "RHB", "HLB", "AMB", "BIMB", "OCBC", "HSBC", "SCB", "UOB"]

BRANCH = ["KL Main", "KL MAIN", "Bukit Bintang", "BUKIT BINTANG", "Mid Valley",
          "MID VALLEY", "PJ State", "SS15 Subang", "Damansara Utama", "Cheras",
          "Ampang Point", "KLCC", "Bangsar", "Setapak", "Wangsa Maju", "Puchong"]

CURRENCIES = ["MYR", "myr", "RM", "USD", "usd", "SGD", "EUR", "GBP", "AUD", "JPY", "458"]

TXN_TYPE = ["DEBIT", "debit", "Debit", "DR", "CREDIT", "credit", "CR", "D", "C"]

TXN_SUBTYPE = ["POS", "pos", "POS PURCHASE", "ATM", "ATM WITHDRAWAL", "TRANSFER",
               "TRF", "FPX", "DUITNOW", "DuitNow", "duitnow", "IBG", "INSTANT TRF",
               "STANDING INSTR", "SI", "DIRECT DEBIT", "DD", "FEE", "INTEREST",
               "REVERSAL", "REFUND", "CASHBACK", "TRANSFERR", "PO S"]

TXN_STATUS = ["POSTED", "posted", "Posted", "PENDING", "pending", "SETTLED",
              "REVERSED", "FAILED", "failed", "DECLINED", "P", "S"]

ACCT_TYPE = ["SAVINGS", "savings", "Savings Account", "SA", "CURRENT", "current",
             "Current Account", "CA", "FIXED DEPOSIT", "FD", "CREDIT CARD", "CC",
             "SAVING", "Saving"]

ACCT_STATUS = ["ACTIVE", "active", "Active", "A", "DORMANT", "dormant", "CLOSED",
               "closed", "FROZEN", "SUSPENDED", "BLOCKED"]

PRODUCTS = ["Basic Savings", "BASIC SAVINGS", "Premier Current", "eSaver Plus",
            "Youth Account", "Salary Account", "SALARY ACCT", "Islamic Savings-i",
            "Wadiah Savings", "Platinum Credit", "Gold Credit", "Cashback Card"]

GENDER = ["M", "F", "Male", "female", "MALE", "FEMALE", "m", "f", "U", "Unknown", "1", "2"]

MARITAL = ["SINGLE", "single", "Married", "MARRIED", "M", "S", "Divorced",
           "DIVORCED", "Widowed", "W", "D"]

RESIDENCY = ["RESIDENT", "resident", "NON-RESIDENT", "Non Resident", "NR", "R",
             "CITIZEN", "PR", "EXPATRIATE", "Expat"]

OCCUPATION = ["Engineer", "ENGINEER", "engineer", "Software Engineer", "Teacher",
              "TEACHER", "Doctor", "Accountant", "ACCOUNTANT", "Clerk", "Manager",
              "MANAGER", "Sales Executive", "Businessman", "Self Employed",
              "SELF-EMPLOYED", "Student", "STUDENT", "Retired", "Housewife",
              "Enginer", "Techer", "Acountant"]

INCOME_BAND = ["<3000", "3000-5000", "5000-10000", ">10000", "B40", "M40", "T20",
               "3K-5K", "5K-10K", "Below 3000", "10000+", "0-2999"]

EMPLOYERS = ["PETRONAS", "Petronas Nasional Bhd", "MAYBANK", "Maybank Berhad",
             "TENAGA NASIONAL", "TNB", "SIME DARBY", "GENTING", "AIRASIA",
             "Intel Malaysia", "INTEL MSIA", "Dell Global", "SHELL",
             "Nestle Malaysia", "Public Bank", "Grab Holdings", "Shopee MY",
             "Self Employed", "N/A"]

KYC_STATUS = ["VERIFIED", "verified", "Verified", "PENDING", "pending", "EXPIRED",
              "REJECTED", "INCOMPLETE", "V", "P", "NOT STARTED"]

RISK = ["LOW", "Low", "low", "L", "1", "MEDIUM", "Medium", "MED", "M", "2",
        "HIGH", "High", "H", "3"]

YN = ["Y", "N", "y", "n", "YES", "NO", "TRUE", "FALSE", "true", "false",
      "1", "0", "T", "F"]

CARD_BRAND = ["VISA", "Visa", "visa", "MASTERCARD", "MasterCard", "MC",
              "mastercard", "AMEX", "American Express", "MyDebit", "UNIONPAY",
              "UnionPay"]

CARD_TYPE = ["DEBIT", "debit", "CREDIT", "credit", "PREPAID", "prepaid", "CHARGE"]

ENTRY_MODE = ["CHIP", "chip", "SWIPE", "MAGSTRIPE", "CONTACTLESS", "NFC",
              "contactless", "MANUAL", "KEYED", "ECOM", "E-COMMERCE", "QR",
              "qr code", "FALLBACK"]

AUTH_RESP = ["00", "05", "51", "14", "91", "approved", "APPROVED", "declined",
             "DECLINED", "Insufficient Funds", "0", "000"]

AUTH_METHOD = ["PIN", "pin", "SIGNATURE", "OTP", "otp", "BIOMETRIC", "FaceID",
               "FINGERPRINT", "NONE", "CVV", "3DS", "3-D Secure"]

CHANNEL = ["ATM", "atm", "MOBILE", "mobile", "Mobile App", "MOBILE APP", "WEB",
           "web", "INTERNET BANKING", "IB", "BRANCH", "branch", "POS",
           "CALL CENTRE", "CALL CENTER", "API", "AGENT"]

SUB_CHANNEL = ["iOS", "ios", "IOS", "Android", "android", "ANDROID", "Web",
               "Chrome", "Safari", "Firefox", "Edge", "Native", "Teller",
               "Self Service", ""]

DEVICE_TYPE = ["MOBILE", "mobile", "Phone", "TABLET", "DESKTOP", "desktop",
               "POS TERMINAL", "ATM", "Unknown", "UNKNOWN"]

OS_VER = ["iOS 17.4", "iOS 16.6.1", "ios 17.2", "Android 14", "Android 13",
          "android 12", "Windows 11", "Windows 10", "macOS 14.3", "Ubuntu 22.04", ""]

APP_VER = ["4.12.0", "4.11.3", "v4.10.1", "4.9", "3.88.2", "4.12", "4.13.0-beta", ""]

LANG = ["EN", "en", "English", "BM", "MS", "Bahasa Malaysia", "ZH", "Chinese",
        "TA", "Tamil"]

SOURCE_SYS = ["CORE_BANKING", "core_banking", "CBS", "CARD_SWITCH", "cardswitch",
              "CRM", "crm_export", "ATM_SWITCH", "MOBILE_GW", "LEGACY_AS400"]

DISPUTE_REASON = ["FRAUD", "Fraud", "DUPLICATE", "duplicate charge",
                  "NOT RECEIVED", "Goods not received", "UNAUTHORISED",
                  "unauthorized", "AMOUNT INCORRECT"]

STREETS = ["Ampang", "Tun Razak", "Bukit Bintang", "SS15/4", "PJU 8/5",
           "Damansara", "Cheras 9", "Kepong Baru", "Sri Hartamas 3"]

TAMANS = ["Melati", "Desa", "Sri Rampai", "Megah", "Connaught", "OUG", "Bukit Indah"]

ADDR_TYPE = ["HOME", "home", "MAILING", "Mailing", "OFFICE", "WORK", "PERMANENT"]

EMAIL_DOM = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "company.com.my"]

USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 Chrome/122.0",
    "MyBankApp/4.12.0 (iOS 17.4; iPhone14,3)",
    "MyBankApp/4.11.3 (Android 13; Pixel 7)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36",
    "okhttp/4.12.0",
    "-",
    "",
]

NARRATIVE = [
    "POS PURCHASE, KUALA LUMPUR MY",
    'ATM CASH WD "MBB KLCC"',
    "DuitNow TRF to 0123456789 - rent, utilities",
    "FPX PAYMENT, SHOPEE MY",
    "Salary credit - MARCH 2024",
    "Reversal of txn dated 03/02/2024, ref#88213",
    "INTEREST CREDIT Q1",
    "Service charge, monthly",
    "Transfer to savings a/c (auto)",
    "REFUND - order #SP-99210, partial",
    "Standing instruction: insurance premium",
    "Cross-border purchase, USD settled @ 4.72",
    "",
    "   ",
    "CARD PAYMENT",
]


# ---------------------------------------------------------------------------
# The 100 columns
# ---------------------------------------------------------------------------


def build_columns():
    C = []
    a = C.append

    # -- transaction core (10) ----------------------------------------------
    a(("txn_id", "'TXN'||lpad(CAST(gid AS VARCHAR),14,'0')"))
    a(("txn_ref", messy("upper(md5(CAST(gid AS VARCHAR))[1:10])", null_rate=0.08)))
    a(("txn_datetime", mixed_ts("txn_ts", null_rate=0.01)))
    a(("posting_date", mixed_date("post_dt", null_rate=0.04)))
    a(("value_date", mixed_date("val_dt", null_rate=0.07, sentinel_rate=0.03)))
    a(("txn_type", messy(pick(TXN_TYPE), null_rate=0.02)))
    a(("txn_subtype", messy(pick(TXN_SUBTYPE), null_rate=0.05)))
    a(("txn_status", messy(pick(TXN_STATUS), null_rate=0.03)))
    a(("txn_description", messy(pick(NARRATIVE), null_rate=0.09, pad_rate=0.05)))
    a(("narrative", messy(pick(NARRATIVE) + "||' ref:'||CAST(gid%99999 AS VARCHAR)",
                          null_rate=0.18)))

    # -- account (12) --------------------------------------------------------
    a(("account_no", weighted([
        (0.04, "CAST(CAST(acct_n AS DOUBLE)*1000 AS VARCHAR)"),
        (0.10, "CAST(acct_n AS VARCHAR)"),
        (1.0, "lpad(CAST(acct_n AS VARCHAR),12,'0')")])))
    a(("iban", messy("'MY'||lpad(CAST(acct_n%99 AS VARCHAR),2,'0')||"
                     + pick_det(BANKS, "acct_n", 61)
                     + "||lpad(CAST(acct_n AS VARCHAR),12,'0')",
                     null_rate=0.22)))
    a(("account_type", messy(pick_det(ACCT_TYPE, "acct_n", 31), null_rate=0.03)))
    a(("account_status", messy(pick_det(ACCT_STATUS, "acct_n", 37), null_rate=0.04)))
    a(("product_code", messy("'PRD-'||lpad(CAST(acct_n%400 AS VARCHAR),4,'0')",
                             null_rate=0.06)))
    a(("product_name", messy(pick_det(PRODUCTS, "acct_n", 41), null_rate=0.07)))
    a(("branch_code", messy("'BR'||lpad(CAST(acct_n%850 AS VARCHAR),4,'0')",
                            null_rate=0.05)))
    a(("branch_name", messy(pick_det(BRANCH, "acct_n", 43), null_rate=0.08,
                            pad_rate=0.04)))
    a(("account_open_date", mixed_date("open_dt", null_rate=0.06, sentinel_rate=0.03)))
    a(("account_currency", messy(pick_det(CURRENCIES, "acct_n", 47), null_rate=0.02)))
    a(("relationship_mgr", messy(pick_det(FIRST, "acct_n", 53) + "||' '||"
                                 + pick_det(LAST, "acct_n", 59), null_rate=0.35)))
    a(("bank_code", messy(pick_det(BANKS, "acct_n", 61), null_rate=0.03)))

    # -- customer (18) -------------------------------------------------------
    a(("customer_id", weighted([
        (0.03, "CAST(CAST(cust_n AS DOUBLE) AS VARCHAR)"),
        (1.0, "'CUST'||lpad(CAST(cust_n AS VARCHAR),10,'0')")])))
    a(("customer_since", mixed_date("since_dt", null_rate=0.09, sentinel_rate=0.02)))
    a(("nric_passport", weighted([
        (0.30, "lpad(CAST(cust_n%999999 AS VARCHAR),6,'0')||'-'||"
               "lpad(CAST(cust_n%14 AS VARCHAR),2,'0')||'-'||"
               "lpad(CAST(cust_n%9999 AS VARCHAR),4,'0')"),
        (0.55, "lpad(CAST(cust_n%999999 AS VARCHAR),6,'0')||"
               "lpad(CAST(cust_n%14 AS VARCHAR),2,'0')||"
               "lpad(CAST(cust_n%9999 AS VARCHAR),4,'0')"),
        (0.70, "'A'||lpad(CAST(cust_n%9999999 AS VARCHAR),8,'0')"),
        (0.80, "'XXXXXX-XX-'||lpad(CAST(cust_n%9999 AS VARCHAR),4,'0')"),
        (1.0, "lpad(CAST(cust_n%999999 AS VARCHAR),6,'0')||'-'||"
              "lpad(CAST(cust_n%14 AS VARCHAR),2,'0')||'-'||"
              "lpad(CAST(cust_n%9999 AS VARCHAR),4,'0')")])))
    # One stable first/last pair per customer. full_name, first_name,
    # last_name and email are all composed from these two, so they agree with
    # each other; only the presentation (casing, order, spacing) drifts.
    fn = pick_det(FIRST, "cust_n", 101)
    ln = pick_det(LAST, "cust_n", 103)

    a(("full_name", messy(weighted([
        (0.15, "upper(" + fn + "||' '||" + ln + ")"),
        (0.25, "lower(" + fn + "||' '||" + ln + ")"),
        (0.32, "(" + ln + ")||', '||(" + fn + ")"),
        (0.38, "(" + fn + ")||'  '||(" + ln + ")"),
        (1.0, "(" + fn + ")||' '||(" + ln + ")")]),
        null_rate=0.02, pad_rate=0.05)))
    a(("first_name", messy(fn, null_rate=0.05, pad_rate=0.04)))
    a(("last_name", messy(ln, null_rate=0.05, pad_rate=0.04)))
    a(("dob", mixed_date("dob_dt", null_rate=0.07, sentinel_rate=0.04)))
    a(("gender", messy(pick_det(GENDER, "cust_n", 107), null_rate=0.06)))
    a(("nationality", messy(pick_det(COUNTRY, "cust_n", 109), null_rate=0.05)))
    a(("residency_status", messy(pick_det(RESIDENCY, "cust_n", 113), null_rate=0.10)))
    a(("marital_status", messy(pick_det(MARITAL, "cust_n", 127), null_rate=0.15)))
    a(("occupation", messy(pick_det(OCCUPATION, "cust_n", 131), null_rate=0.12,
                           pad_rate=0.04)))
    a(("employer_name", messy(pick_det(EMPLOYERS, "cust_n", 137), null_rate=0.20,
                              pad_rate=0.04)))
    a(("income_band", messy(pick_det(INCOME_BAND, "cust_n", 139), null_rate=0.14)))
    a(("email", messy(weighted([
        (0.06, "lower(" + fn + ")||'@@'||" + pick_det(EMAIL_DOM, "cust_n", 149)),
        (0.10, "upper(lower(" + fn + ")||'.'||"
               "CAST(cust_n%9999 AS VARCHAR)||'@gmail.com')"),
        (0.14, "lower(" + fn + ")||CAST(cust_n%999 AS VARCHAR)||'@'"),
        (1.0, "lower(replace(" + fn + ",' ',''))||'.'||"
              "CAST(cust_n%9999 AS VARCHAR)||'@'||"
              + pick_det(EMAIL_DOM, "cust_n", 149))]),
        null_rate=0.11, pad_rate=0.03)))
    a(("mobile_no", messy(weighted([
        (0.25, "'+60'||CAST(100000000+(cust_n%899999999) AS VARCHAR)"),
        (0.45, "'0'||CAST(100000000+(cust_n%899999999) AS VARCHAR)"),
        (0.58, "'60-'||CAST(10+(cust_n%9) AS VARCHAR)||'-'||"
               "CAST(1000000+(cust_n%8999999) AS VARCHAR)"),
        (0.66, "'01'||CAST(10000000+(cust_n%89999999) AS VARCHAR)||' '"),
        (1.0, "'01'||CAST(10000000+(cust_n%89999999) AS VARCHAR)")]),
        null_rate=0.08)))
    a(("phone_home", messy("'03-'||CAST(10000000+(cust_n%89999999) AS VARCHAR)",
                          null_rate=0.45)))
    a(("preferred_language", messy(pick_det(LANG, "cust_n", 151), null_rate=0.18)))

    # -- address (8) ---------------------------------------------------------
    a(("addr_line1", messy("'No. '||CAST(cust_n%299 AS VARCHAR)||', Jalan '||"
                           + pick_det(STREETS, "cust_n", 157), null_rate=0.06, pad_rate=0.05)))
    a(("addr_line2", messy("'Taman '||" + pick_det(TAMANS, "cust_n", 163), null_rate=0.42)))
    a(("addr_city", messy(pick_det(CITIES, "cust_n", 167), null_rate=0.05, pad_rate=0.05)))
    a(("addr_state", messy(pick_det(STATES, "cust_n", 173), null_rate=0.07)))
    a(("addr_postcode", weighted([
        (0.12, "CAST(1000+(cust_n%88999) AS VARCHAR)"),
        (0.18, "lpad(CAST(cust_n%99999 AS VARCHAR),5,'0')||'-'"),
        (1.0, "lpad(CAST(cust_n%99999 AS VARCHAR),5,'0')")])))
    a(("addr_country", messy(pick_det(COUNTRY, "cust_n", 179), null_rate=0.04)))
    a(("addr_type", messy(pick_det(ADDR_TYPE, "cust_n", 181), null_rate=0.20)))
    a(("addr_last_updated", mixed_date("addr_dt", null_rate=0.16, sentinel_rate=0.03)))

    # -- kyc / compliance (11) ----------------------------------------------
    a(("kyc_status", messy(pick_det(KYC_STATUS, "cust_n", 191), null_rate=0.06)))
    a(("kyc_review_date", mixed_date("kyc_dt", null_rate=0.19, sentinel_rate=0.03)))
    a(("risk_rating", messy(pick_det(RISK, "cust_n", 193), null_rate=0.07)))
    a(("pep_flag", messy(pick_det(YN, "cust_n", 197), null_rate=0.09)))
    a(("sanctions_hit", messy(pick_det(YN, "cust_n", 199), null_rate=0.12)))
    a(("aml_flag", messy(pick_det(YN, "cust_n", 211), null_rate=0.10)))
    a(("aml_score", messy(weighted([
        (0.10, "format('{:.4f}', aml_s)"),
        (0.18, "CAST(CAST(aml_s*100 AS INTEGER) AS VARCHAR)||'%'"),
        (1.0, "format('{:.2f}', aml_s*100)")]), null_rate=0.15)))
    a(("fraud_score", messy(weighted([
        (0.12, "CAST(CAST(fraud_s*1000 AS INTEGER) AS VARCHAR)"),
        (1.0, "format('{:.3f}', fraud_s)")]), null_rate=0.13)))
    a(("fraud_rule_hit", messy(
        "'R'||lpad(CAST(gid%40 AS VARCHAR),2,'0')||"
        "CASE WHEN random()<0.3 THEN ';R'||lpad(CAST(gid%17 AS VARCHAR),2,'0') "
        "ELSE '' END", null_rate=0.72)))
    a(("dispute_id", messy("'DSP'||lpad(CAST(gid%999999 AS VARCHAR),8,'0')",
                          null_rate=0.88)))
    a(("dispute_reason", messy(pick(DISPUTE_REASON), null_rate=0.90)))

    # -- merchant (10) -------------------------------------------------------
    a(("merchant_id", messy("'MID'||lpad(CAST(merch_n AS VARCHAR),10,'0')",
                           null_rate=0.14)))
    a(("merchant_name", messy(pick_det(MERCHANTS, "merch_n", 223), null_rate=0.12, pad_rate=0.08)))
    a(("merchant_mcc", messy(pick_det(MCC, "merch_n", 227), null_rate=0.15)))
    a(("merchant_category", messy(pick_det(MCC_DESC, "merch_n", 229), null_rate=0.17)))
    a(("merchant_city", messy(pick_det(CITIES, "merch_n", 233), null_rate=0.18, pad_rate=0.05)))
    a(("merchant_state", messy(pick_det(STATES, "merch_n", 239), null_rate=0.25)))
    a(("merchant_country", messy(pick_det(COUNTRY, "merch_n", 241), null_rate=0.13)))
    a(("terminal_id", messy("'TRM'||lpad(CAST(merch_n%99999 AS VARCHAR),8,'0')",
                           null_rate=0.21)))
    a(("acquirer_id", messy("'ACQ'||lpad(CAST(merch_n%9999 AS VARCHAR),6,'0')",
                           null_rate=0.24)))
    a(("acquirer_country", messy(pick_det(COUNTRY, "merch_n", 251), null_rate=0.26)))

    # -- amounts (12) --------------------------------------------------------
    a(("txn_amount", money("amt", null_rate=0.01)))
    a(("txn_currency", messy(pick(CURRENCIES), null_rate=0.02)))
    a(("fx_rate", messy(weighted([
        (0.08, "CAST(fx AS VARCHAR)"),
        (0.14, "format('{:.2f}', fx)"),
        (1.0, "format('{:.6f}', fx)")]), null_rate=0.30)))
    a(("amount_local", money("amt_local", null_rate=0.03)))
    a(("fee_amount", money("fee", null_rate=0.22)))
    a(("vat_amount", money("vat", null_rate=0.34)))
    a(("interchange_fee", money("icfee", null_rate=0.40)))
    a(("markup_fee", money("mkfee", null_rate=0.55)))
    a(("total_charged", money("total", null_rate=0.06)))
    a(("balance_before", money("bal_before", null_rate=0.08)))
    a(("balance_after", money("bal_after", null_rate=0.08)))
    a(("available_balance", money("bal_avail", null_rate=0.12)))

    # -- card / instrument (10) ---------------------------------------------
    a(("card_no_masked", messy(weighted([
        (0.35, "CAST(400000+(card_n%99999) AS VARCHAR)||'******'||"
               "lpad(CAST(card_n%9999 AS VARCHAR),4,'0')"),
        (0.55, "CAST(400000+(card_n%99999) AS VARCHAR)||'XXXXXX'||"
               "lpad(CAST(card_n%9999 AS VARCHAR),4,'0')"),
        (1.0, "'**** **** **** '||lpad(CAST(card_n%9999 AS VARCHAR),4,'0')")]),
        null_rate=0.28)))
    a(("card_bin", messy("CAST(400000+(card_n%99999) AS VARCHAR)", null_rate=0.30)))
    a(("card_last4", weighted([
        (0.25, "CAST(card_n%9999 AS VARCHAR)"),
        (1.0, "lpad(CAST(card_n%9999 AS VARCHAR),4,'0')")])))
    a(("card_brand", messy(pick_det(CARD_BRAND, "card_n", 257), null_rate=0.27)))
    a(("card_type", messy(pick_det(CARD_TYPE, "card_n", 263), null_rate=0.29)))
    a(("card_expiry", messy(weighted([
        (0.30, "lpad(CAST(1+(card_n%12) AS VARCHAR),2,'0')||'/'||"
               "CAST(25+(card_n%6) AS VARCHAR)"),
        (0.50, "'20'||CAST(25+(card_n%6) AS VARCHAR)||'-'||"
               "lpad(CAST(1+(card_n%12) AS VARCHAR),2,'0')"),
        (0.65, "lpad(CAST(1+(card_n%12) AS VARCHAR),2,'0')||"
               "CAST(25+(card_n%6) AS VARCHAR)"),
        (1.0, "lpad(CAST(1+(card_n%12) AS VARCHAR),2,'0')||'/20'||"
              "CAST(25+(card_n%6) AS VARCHAR)")]), null_rate=0.31)))
    a(("card_issue_country", messy(pick_det(COUNTRY, "card_n", 269), null_rate=0.32)))
    a(("auth_code", messy("upper(md5(CAST(gid*7 AS VARCHAR))[1:6])", null_rate=0.20)))
    a(("auth_response", messy(pick(AUTH_RESP), null_rate=0.18)))
    a(("entry_mode", messy(pick(ENTRY_MODE), null_rate=0.23)))

    # -- channel / device (11) ----------------------------------------------
    a(("channel", messy(pick(CHANNEL), null_rate=0.04)))
    a(("sub_channel", messy(pick(SUB_CHANNEL), null_rate=0.15)))
    a(("device_id", messy("upper(md5(CAST(cust_n*13 AS VARCHAR))[1:16])",
                         null_rate=0.33)))
    a(("device_type", messy(pick(DEVICE_TYPE), null_rate=0.19)))
    a(("os_version", messy(pick(OS_VER), null_rate=0.26)))
    a(("app_version", messy(pick(APP_VER), null_rate=0.24)))
    a(("ip_address", messy(weighted([
        (0.06, "CAST(gid%999 AS VARCHAR)||'.'||CAST(gid%255 AS VARCHAR)"),
        (0.12, "'2001:0db8:85a3::'||CAST(gid%9999 AS VARCHAR)"),
        (1.0, "CAST(1+(gid%223) AS VARCHAR)||'.'||CAST(gid%255 AS VARCHAR)||'.'||"
              "CAST((gid*3)%255 AS VARCHAR)||'.'||CAST((gid*7)%255 AS VARCHAR)")]),
        null_rate=0.17)))
    a(("user_agent", messy(pick(USER_AGENTS), null_rate=0.29)))
    a(("session_id", messy("md5(CAST(gid/7 AS VARCHAR))", null_rate=0.25)))
    a(("auth_method", messy(pick(AUTH_METHOD), null_rate=0.21)))
    a(("geo_location", messy(
        "format('{:.5f}', 2.9+(CAST(gid%400 AS DOUBLE)/1000))||','||"
        "format('{:.5f}', 101.5+(CAST(gid%300 AS DOUBLE)/1000))", null_rate=0.38)))

    # -- ops / audit (8) -----------------------------------------------------
    a(("reversal_flag", messy(pick(YN), null_rate=0.11)))
    a(("original_txn_id", messy(
        "'TXN'||lpad(CAST(CASE WHEN gid>10 THEN gid-10 ELSE gid END AS VARCHAR),14,'0')",
        null_rate=0.86)))
    a(("settlement_date", mixed_date("settle_dt", null_rate=0.13, sentinel_rate=0.02)))
    a(("settlement_batch", messy("'BATCH'||lpad(CAST(gid%9999 AS VARCHAR),6,'0')",
                                null_rate=0.16)))
    a(("source_system", messy(pick(SOURCE_SYS), null_rate=0.03)))
    a(("src_file_name", messy(
        "'extract_'||strftime(post_dt,'%Y%m%d')||'_'||CAST(gid%24 AS VARCHAR)||'.csv'",
        null_rate=0.05)))
    a(("ingested_at", mixed_ts("ing_ts", null_rate=0.02)))
    a(("record_hash", messy("md5(CAST(gid AS VARCHAR)||CAST(cust_n AS VARCHAR))",
                           null_rate=0.04)))

    return C


# build_columns() defines a 110-column catalogue. The extract is specified at
# exactly 100 columns, so the 10 below are excluded. Each was chosen because it
# duplicates signal already carried by another column, which means dropping it
# costs no distinct mess pattern:
#   bank_code          -> already encoded in iban
#   phone_home         -> mobile_no covers phone-format mess
#   acquirer_country   -> merchant_country covers country-code drift
#   dispute_reason     -> dispute_id already marks disputed rows
#   sub_channel        -> channel covers channel casing drift
#   markup_fee         -> interchange_fee covers sparse money-as-text
#   app_version        -> os_version covers version-string mess
#   preferred_language, addr_type, geo_location -> low signal, no unique mess
EXCLUDED = {
    "bank_code",
    "phone_home",
    "preferred_language",
    "addr_type",
    "acquirer_country",
    "dispute_reason",
    "geo_location",
    "sub_channel",
    "markup_fee",
    "app_version",
}

COLUMNS = [c for c in build_columns() if c[0] not in EXCLUDED]
COLUMN_NAMES = [c[0] for c in COLUMNS]

assert len(COLUMNS) == 100, "expected exactly 100 columns, got %d" % len(COLUMNS)
assert len(set(COLUMN_NAMES)) == 100, "duplicate column names in schema"
