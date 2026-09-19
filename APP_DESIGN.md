# Financial Crime analytics: the model this pipeline is shaped by

What the reporting layer has to answer, written before the star schema was
built, so the model in Phase 2 is shaped by the questions rather than by
whatever was convenient in the source.

---

## 1. The questions the model has to answer

A retail bank's financial crime function needs to prove, continuously, that its
monitoring is working:

1. **Which rules earn their keep?** Alert volume and precision per rule, so the
   ones that only generate work can be retired.
2. **What does the current threshold cost?** Recall against analyst headcount,
   because every point of sensitivity is paid for in people.
3. **Where is the exposure?** Risk-score distribution, cross-border and
   card-not-present value, concentration by merchant and channel.
4. **Can the numbers be trusted?** Completeness, validity and duplicate rates by
   source, which in this data are genuinely real rather than simulated.

Those are the questions. The star schema exists to answer them at the grain they
are asked, which is why `fact_alert` is one row per rule firing and not one row
per transaction.

---

## 2. Who reads it

| Persona | What they need from the model |
| --- | --- |
| Fraud analyst (L1) | Which alerts are worth working first, and why each one fired |
| Rule owner | Precision and volume per rule, and what a threshold change would do |
| Compliance manager | Risk-rating mix, KYC currency, the PEP and sanctions population |
| Head of financial crime | Effectiveness, exposure, and the staffing the current cut-off implies |

---

## 3. Reporting surfaces

| Page | Answers |
| --- | --- |
| **Financial crime overview** | Alert volume and disposition over time, open vs closed, SLA breaches, exposure value |
| **Rule effectiveness** | Precision, false-positive rate and alert volume per rule; which rules earn their keep |
| **Risk and exposure** | Risk-score distribution, cross-border and card-not-present exposure, value at risk by segment |
| **Merchant and channel risk** | Concentration, high-risk MCCs, terminal and acquirer outliers |
| **Customer risk** | Risk-rating mix, KYC currency, PEP/sanctions population, exposure by segment |
| **Data trust** | Completeness, validity and duplicate rates by source system, genuinely real in this data |

---

## 4. Star schema

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
| `dim_time` | generated | hour buckets, required for the odd-hour signal |
| `dim_currency` | currency columns | with cross-border flag |
| `dim_country` | conformed from the 31 spellings of Malaysia | |
| `dim_risk_rule` | defined in Phase 2 | rule id, description, weight, owner |
| `dim_auth_response` | response codes | code, meaning, approved/declined |
| `dim_source_system` | `source_system` | drives the data-trust page |

---

## 5. The engineered risk signals

**This is the analytical heart of the project, and it exists because of a real
constraint.**

The source data has **no cross-column correlations**. Measured on the raw table:

| Check | Result |
| --- | --- |
| `fraud_score` by channel | 29.9 to 31.2 across every channel, flat |
| `txn_amount` by merchant category | 445 to 462 across every category, flat |

So the supplied `fraud_score` column is noise and is **deliberately not used**.
Any dashboard built on it would show fraud spread perfectly evenly across every
channel and country, which is visibly wrong.

Instead Phase 2 derives risk from columns that are genuinely informative, using
rules that a real financial crime team would recognise:

| Rule | Derivation | Fires on | Status |
| --- | --- | --- | --- |
| `R02 card_not_present` | `entry_mode in (ECOM, E-COMMERCE, KEYED, MANUAL)` | 20.48% | kept |
| `R03 amount_anomaly` | amount percentile **within that customer's own history**, customers with 5+ transactions only | 0.94% | kept |
| `R04 odd_hour` | `hour(txn_ts) between 01:00 and 05:00` | 20.63% | kept |
| `R05 velocity` | two or more transactions on one account inside a clock hour | 1.20% | recalibrated from three, which fired on 0.01% |
| `R06 new_merchant` | first use of a merchant, customers with 20+ transactions only | 1.12% | recalibrated; unrestricted it fired on 85.88% |
| `R07 high_risk_mcc` | MCC in {6011 ATM, 4829 money transfer, 7995 gambling} | 4.28% | kept |
| `R09 declined_streak` | `auth_response` not approved | 49.69% | kept, borderline |
| ~~`R01 cross_border`~~ | ~~currency differs from account currency~~ | ~~80.22%~~ | **dropped** |
| ~~`R08 round_amount`~~ | ~~amount is a round hundred~~ | ~~0.00%~~ | **dropped** |

Nine rules were specified. Four did not survive contact with the data, which is
the point of measuring rather than assuming. `R01` fires on four rows in five
because currency is uniform in this source, so it cannot rank anything. `R08`
never fires at all because amounts come from a continuous distribution and
essentially never land on exact hundreds. `R05` and `R06` were salvageable by
changing a threshold and by requiring enough customer history for "first time"
to mean a departure from a pattern rather than the normal case.

`risk_score` is the weighted sum of the fired rules.

**Why this produces real analytics.** Measured on a reproducible 2,000,000 row
slice, the score lands 83.3% low, 15.8% medium and 0.9% high, which is the
pyramid a risk score is supposed to make, and every rule fires at 0.0% in the
bottom decile so the separation is clean.

Against the source column, on a scale-normalised test of whether either score
separates groups at all: across entry modes the derived score's group means move
**67.59% of its scale**, the source `fraud_score`'s move **1.52%**. Comparing
raw standard deviations would be meaningless here, since the two sit on
different scales and the source column's is in fact the larger of the two.

### Outcome label

Rule effectiveness needs ground truth. There is none in the source, so Phase 2
generates a **simulated confirmed-fraud label** as a probabilistic function of
`risk_score` (higher score, higher probability), seeded deterministically from
`_mirror_row_id` so it is reproducible.

This is documented as simulated. It makes precision, recall and false-positive
rate measurable and different per rule, which is the entire point of the rule
effectiveness page. It is not presented as real fraud.

---

## 6. What is real and what is derived

Stated plainly, because a portfolio piece that blurs this is worse than useless.

**Genuinely present in the source data**

- transaction amount distribution, log-skewed with a realistic long tail
- customer and merchant concentration, deliberately skewed populations
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

- the supplied `fraud_score`, `aml_score`, `fraud_rule_hit` columns, uncorrelated noise
- `balance_before` / `balance_after` as a balance history, they do not form a
  coherent per-account series

---

## 7. How this drives Phase 2

The schema above is the specification for the DuckDB work:

1. **Clean**: trim, collapse null-lookalikes to real NULL, parse five date
   formats, strip currency symbols and parenthesised negatives, conform casing
2. **Conform**: 31 country spellings to one code, 34 `txn_type` values to a
   small set, MCC to category
3. **Deduplicate**: 593,209 exact duplicates, resolved using `_mirror_row_id`
4. **Derive**: the nine rules and `risk_score`
5. **Model**: build the facts and dimensions above
6. **Serve**: write gold Delta tables for the Direct Lake model in Phase 3

Note from the Phase 2 research: DuckDB Delta writes are INSERT-only, so any
merge or SCD logic goes through **delta-rs**, and V-Order is not available on the
Python kernel, which needs an explicit decision before Phase 3.

---
