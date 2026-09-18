# Financial Crime Operations — target application design

The end product this whole pipeline exists to serve. Designed first, deliberately,
so the star schema in Phase 2 is shaped by what the application actually needs
rather than by what happened to be convenient in the source.

---

## 1. The problem the app solves

A retail bank's financial crime function has to do four things every day, on the
same transaction stream:

1. **Triage alerts** — something scored high; is it fraud or noise?
2. **Work cases** — a customer disputed a charge; move it through to resolution
   inside a regulatory clock.
3. **Keep KYC current** — reviews expire; expired reviews on high-risk customers
   are a regulatory finding.
4. **Prove the function works** — alert volumes, false-positive rates, rule
   effectiveness, SLA breaches, exposure.

Points 1-3 are **operational** (people take actions, state changes). Point 4 is
**analytical**. A Fabric App can carry both, which is why this domain was chosen.

---

## 2. Who uses it

| Persona | What they do | Primary surface |
| --- | --- | --- |
| Fraud analyst (L1) | Triage the alert queue, disposition each alert | Alert Triage |
| AML investigator | Review sanctions / PEP hits, escalate | Sanctions & PEP Review |
| Dispute officer | Drive chargebacks through the lifecycle | Case Management |
| Compliance manager | Chase expired and pending KYC | KYC Remediation |
| Head of financial crime | Effectiveness, SLA, exposure, staffing | Analytics pages |

---

## 3. Operational surfaces (state-changing)

These are what make it an application rather than a report. Each writes back.

### 3.1 Alert triage queue
Ranked list of open alerts. Analyst picks one, sees the transaction in full
context (customer, card, merchant, recent history, which rules fired and why),
and dispositions it.

- Actions: **assign**, **request info**, **confirm fraud**, **mark false positive**
- Writes: `alert_status`, `assigned_to`, `disposition`, `disposition_reason`, `dispositioned_at`
- Ranking: engineered `risk_score` descending, then amount, then age

### 3.2 Case management (disputes)
Full dispute lifecycle with a regulatory clock.

- States: `raised → evidence_requested → under_review → chargeback_filed → resolved`
- Writes: `case_status`, `owner`, `sla_due_at`, `resolution`, `recovered_amount`
- Surfaces: ageing buckets, breached SLAs, cases by reason

### 3.3 KYC remediation worklist
Customers whose review is expired, pending or missing, prioritised by risk rating
and exposure.

- Actions: **outreach sent**, **documents received**, **review complete**, **escalate**
- Writes: `kyc_review_status`, `next_review_due`, `remediation_owner`

### 3.4 Sanctions and PEP review
Queue of customers flagged `sanctions_hit` or `pep_flag`, with an escalation path
and a four-eyes confirmation step.

---

## 4. Analytics surfaces

| Page | Answers |
| --- | --- |
| **Financial crime overview** | Alert volume and disposition over time, open vs closed, SLA breaches, exposure value |
| **Rule effectiveness** | Precision, false-positive rate and alert volume per rule; which rules earn their keep |
| **Risk and exposure** | Risk-score distribution, cross-border and card-not-present exposure, value at risk by segment |
| **Merchant and channel risk** | Concentration, high-risk MCCs, terminal and acquirer outliers |
| **Customer risk** | Risk-rating mix, KYC currency, PEP/sanctions population, exposure by segment |
| **Data trust** | Completeness, validity and duplicate rates by source system — genuinely real in this data |

---

## 5. Star schema

Shaped to serve section 3 and 4, not to mirror the source.

### Facts

| Fact | Grain | Approx rows | Notes |
| --- | --- | --- | --- |
| `fact_transaction` | one transaction | 50,000,000 | the spine; conformed keys, typed measures |
| `fact_alert` | one rule firing on one transaction | derived | a transaction can raise several alerts |
| `fact_case` | one dispute or AML case | derived | lifecycle states + SLA |
| `fact_kyc_review` | one review obligation per customer | derived | drives the remediation queue |

### Dimensions

| Dimension | Source of truth | Notes |
| --- | --- | --- |
| `dim_customer` | customer columns | deduplicated on `_mirror_row_id` lineage; the 3-spellings problem resolved here |
| `dim_account` | account columns | |
| `dim_card` | card columns | BIN, brand, type, issue country |
| `dim_merchant` | merchant columns | MCC conformed, high-risk flag |
| `dim_channel` | channel + entry mode | the 34 spellings of `txn_type` collapse here |
| `dim_date` | generated | fiscal, weekday, holiday |
| `dim_time` | generated | hour buckets — required for the odd-hour signal |
| `dim_currency` | currency columns | with cross-border flag |
| `dim_country` | conformed from the 31 spellings of Malaysia | |
| `dim_risk_rule` | defined in Phase 2 | rule id, description, weight, owner |
| `dim_auth_response` | response codes | code, meaning, approved/declined |
| `dim_source_system` | `source_system` | drives the data-trust page |

---

## 6. The engineered risk signals

**This is the analytical heart of the project, and it exists because of a real
constraint.**

The source data has **no cross-column correlations**. Measured on the raw table:

| Check | Result |
| --- | --- |
| `fraud_score` by channel | 29.9 to 31.2 across every channel — flat |
| `txn_amount` by merchant category | 445 to 462 across every category — flat |

So the supplied `fraud_score` column is noise and is **deliberately not used**.
Any dashboard built on it would show fraud spread perfectly evenly across every
channel and country, which is visibly wrong.

Instead Phase 2 derives risk from columns that are genuinely informative, using
rules that a real financial crime team would recognise:

| Rule | Derivation | Why it is sound here |
| --- | --- | --- |
| `R01 cross_border` | `txn_currency <> account_currency` | both columns real; ~14% of rows are non-MYR |
| `R02 card_not_present` | `entry_mode in (ECOM, E-COMMERCE, KEYED, MANUAL)` | real categorical |
| `R03 amount_anomaly` | transaction amount percentile **within that customer's own history** | amounts are genuinely log-skewed, so percentiles are meaningful |
| `R04 odd_hour` | `hour(txn_ts) between 01:00 and 05:00` | timestamps are real |
| `R05 velocity` | transactions per card per rolling hour | works on the heavy tail: customer selection is `pow(random, 2.0)` skewed, so active customers really do cluster |
| `R06 new_merchant` | first time this customer transacts at this merchant | derived from real ids |
| `R07 high_risk_mcc` | MCC in {6011 ATM, 4829 money transfer, 7995 gambling} | real MCC values |
| `R08 round_amount` | amount is a round hundred | real |
| `R09 declined_streak` | consecutive non-approved `auth_response` per card | real categorical |

`risk_score` is the weighted sum of the fired rules.

**Why this produces real analytics.** The score is a function of varying inputs,
so it has a genuine distribution rather than a flat line, and it correlates with
its own drivers *by construction*. "High-risk transactions skew cross-border and
card-not-present" becomes a true, explainable statement about this data instead
of an artefact.

### Outcome label

Rule effectiveness needs ground truth. There is none in the source, so Phase 2
generates a **simulated confirmed-fraud label** as a probabilistic function of
`risk_score` (higher score, higher probability), seeded deterministically from
`_mirror_row_id` so it is reproducible.

This is documented as simulated. It makes precision, recall and false-positive
rate measurable and different per rule, which is the entire point of the rule
effectiveness page. It is not presented as real fraud.

---

## 7. What is real and what is derived

Stated plainly, because a portfolio piece that blurs this is worse than useless.

**Genuinely present in the source data**

- transaction amount distribution — log-skewed with a realistic long tail
- customer and merchant concentration — deliberately skewed populations
- 593,209 exact duplicate rows
- 18.4% mess rate, five competing date formats, 31 spellings of Malaysia
- NULL versus empty-string distinction, preserved end to end
- entity consistency: one customer keeps one underlying identity across all rows

**Derived in Phase 2, and labelled as such**

- `risk_score` and all nine rule flags
- the confirmed-fraud outcome label
- alert, case and KYC-review facts
- SLA clocks and ageing

**Deliberately unused**

- the supplied `fraud_score`, `aml_score`, `fraud_rule_hit` columns — uncorrelated noise
- `balance_before` / `balance_after` as a balance history — they do not form a
  coherent per-account series

---

## 8. How this drives Phase 2

The schema above is the specification for the DuckDB work:

1. **Clean** — trim, collapse null-lookalikes to real NULL, parse five date
   formats, strip currency symbols and parenthesised negatives, conform casing
2. **Conform** — 31 country spellings to one code, 34 `txn_type` values to a
   small set, MCC to category
3. **Deduplicate** — 593,209 exact duplicates, resolved using `_mirror_row_id`
4. **Derive** — the nine rules and `risk_score`
5. **Model** — build the facts and dimensions above
6. **Serve** — write gold Delta tables for the Direct Lake model in Phase 3

Note from the Phase 2 research: DuckDB Delta writes are INSERT-only, so any
merge or SCD logic goes through **delta-rs**, and V-Order is not available on the
Python kernel, which needs an explicit decision before Phase 3.

---

## 9. Write-back: how the operational surfaces persist

The four surfaces in section 3 change state. That state has to go somewhere, and
the obvious target is closed off.

**The mirror is read-only.** The documentation is explicit that user data
functions get "read-only access to mirrored database data", and that mirrored
databases cannot carry calculated columns or tables. So a disposition cannot be
written into `raw_txn`. That constraint is correct rather than inconvenient: the
mirror is the bank's source data, and an analyst's decision is not. Writing
decisions into the replica would corrupt the lineage that makes the mirror
trustworthy.

### The documented pattern

Fabric's answer is **translytical task flows**. A button in a Power BI report
calls a **user data function**, which writes to a read-write Fabric data source.
User data functions have native connection management for Fabric SQL databases,
warehouses, and lakehouse files, and the guidance is explicit: "For most
write-back scenarios, we recommend using SQL database as your underlying data
source. SQL databases perform well with the heavy read/write operations required
in reporting scenarios."

```
READ PATH
  mirrored raw_txn (read-only)
    -> Lakehouse shortcut
    -> DuckDB transformation (Phase 2)
    -> gold Delta tables
    -> Direct Lake semantic model
    -> report

WRITE PATH
  report button / input slicer
    -> user data function (Python, pyodbc)
    -> Fabric SQL database
    -> Lakehouse shortcut
    -> Direct Lake
    -> the same report reflects the change
```

### Why the surrogate key earns its keep twice

`_mirror_row_id` was added so PostgreSQL would emit UPDATE and DELETE at all. It
is also the join key between an analyst's decision and the transaction it was
made against. Every write-back row references it, which is what allows an
operational decision taken in Fabric to be traced back to a specific row that
originated on premises.

### Operational tables (Fabric SQL database, read-write)

| Table | Grain | Key columns |
| --- | --- | --- |
| `ops.alert_disposition` | one decision on one alert | `alert_id`, `_mirror_row_id`, `disposition`, `reason`, `analyst`, `decided_at` |
| `ops.case` | one dispute case | `case_id`, `_mirror_row_id`, `state`, `owner`, `sla_due_at`, `resolution`, `recovered_amount` |
| `ops.case_event` | one state transition, append only | `case_id`, `from_state`, `to_state`, `actor`, `at` |
| `ops.kyc_action` | one remediation action | `customer_id`, `action`, `owner`, `next_review_due`, `at` |
| `ops.assignment` | current owner of a work item | `item_type`, `item_id`, `assignee`, `assigned_at` |

`ops.case_event` is append-only on purpose. Regulated casework needs the history
of how a case moved, not just where it ended up, and an append-only event table
is also what makes the SLA clock auditable.

### Functions to implement

| Function | Called from | Writes |
| --- | --- | --- |
| `disposition_alert(alert_id, verdict, reason)` | Alert triage buttons | `ops.alert_disposition` |
| `assign_item(item_type, item_id, assignee)` | Any queue | `ops.assignment` |
| `advance_case(case_id, to_state, note)` | Case management | `ops.case`, `ops.case_event` |
| `record_kyc_action(customer_id, action)` | KYC remediation | `ops.kyc_action` |

Each returns a string, which is what a Power BI data function button requires.

### One constraint this places on the reports

Write-back visibility depends on storage mode: updated values appear immediately
for **Direct Lake or DirectQuery**, but an import-mode report only reflects them
after a refresh the task flow triggers. The operational surfaces must therefore
be Direct Lake, not import. That is a design constraint on Phase 3, not a
detail to discover later.

### What the HTML demo does instead

`app-demo/index.html` mutates local JavaScript state when an alert is
dispositioned. It is a prototype of the interaction, not of the persistence, and
it makes no network call. The table above is the specification for replacing
that with real write-back.
