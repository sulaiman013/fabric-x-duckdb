# PRODUCT.md

register: product

## Product purpose

Sentinel is the financial crime operations console for a Malaysian retail bank.
It is the working surface for the people who triage fraud alerts, drive disputes
through a regulatory clock, and keep KYC reviews current. It reads a transaction
table mirrored continuously from on-premises PostgreSQL into Fabric OneLake.

Its single job: get the right alert in front of the right analyst, with enough
context to decide, and record that decision.

## Users

| Who | What they do here | What they need |
| --- | --- | --- |
| Fraud analyst (L1) | Works the alert queue for a whole shift | Density, fast scanning, keyboard-first, no ceremony |
| AML investigator | Reviews sanctions and PEP hits | Full context on one subject, escalation trail |
| Dispute officer | Moves chargebacks through the lifecycle | State and elapsed time against SLA, at a glance |
| Compliance manager | Chases expired and pending reviews | Population counts, what is overdue and by how much |
| Head of financial crime | Judges whether the function works | Rule effectiveness, exposure, SLA breaches |

The primary user is the L1 analyst. Everything else yields to their throughput.

## Tone

Procedural, unexcitable, precise. This is a system of record for regulated work.
It states what is true and what was decided. It never congratulates, never
exclaims, and never softens a number. Terms of art are used correctly and not
explained away: chargeback, disposition, MCC, entry mode, PEP, SLA breach.

## Anti-references

Explicitly not:

- A security operations centre. No threat-map theatrics, no glowing dark console,
  no red pulsing. This is casework, not an incident bridge.
- A consumer fintech app. No celebratory colour, no rounded friendliness, no
  oversized figures that flatter the reader.
- A BI dashboard. The point is to act on a row, not to admire an aggregate.

## Strategic principles

1. **The queue is the product.** Every pixel not serving "which alert next, and
   what do I do with it" is overhead.
2. **Show the raw bytes.** The mirrored table is untyped on purpose. Analysts see
   the value exactly as the source holds it, mess included, because the mess is
   evidence and hiding it is how bad decisions get made.
3. **Derived risk is explainable or it is not shown.** Every score decomposes
   into named rules with weights. No opaque model output.
4. **State is visible in form, not only in words.** Severity and lifecycle read
   at a glance without parsing text.
5. **Nothing is invented.** Figures on screen are measured from the real mirrored
   dataset. Example rows are marked as examples.

## Scene

A fraud analyst works this queue for a full shift on a 24-inch monitor in a bank
operations floor, under bright overhead light, with a compliance manager reading
the same screen over their shoulder in a mid-morning review.

That scene forces a light interface. A dark console would be the category reflex
and would be wrong for a brightly lit room and for shared reading.
