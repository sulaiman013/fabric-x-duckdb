# The film, v3. Plan for approval.

Nothing gets built until you approve this. Below: what I fact-checked and what
it changed, then the film scene by scene with the exact words and numbers that
will be on screen, then how it gets built and verified.

---

## Part 1. The fact-check, and what it broke

You asked for every claim to be correct. I re-read the artifacts and re-checked
every vendor claim against Microsoft Learn. Six things were wrong or overstated.
Two of them weaken the argument the last cut was making, so they change the
film rather than just correcting a caption.

### What was wrong

**1. The acceptance figure on screen was stale.**
The rendered film says `39 / 39`. `UAT.json` says **36 passed, 0 failed, 1
skipped**, run 2026-09-19 10:05:16Z. The count dropped when the write-back
checks were removed and the film was never re-rendered. Fixed everywhere.

**2. "Half the CU rate" is only true against the default starter pool.**
Microsoft Learn, *Choosing a notebook kernel*, lists three rates:

| Compute | CU while running |
| --- | --- |
| Python notebook, 8 vCores | 4 |
| Spark starter pool, default, after proactive scale-up | 8 minimum |
| Spark single node at 8 vCores, if you configure it | **4** |

So a single-node Spark session bills exactly what the Python kernel bills. The
saving is against the pool you get when you do not think about it, not against
Spark as such. The film now says that in those words.

**3. Microsoft's own benchmark band lands on this dataset.**
Learn says that at roughly **10 to 13 GB compressed**, Fabric Spark with the
Native Execution Engine is competitive with or faster than most single-machine
engines, and that single-machine Python engines can hit out-of-memory errors at
lower vCore counts. This dataset is **10.5 GB compressed**. It is sitting on
that boundary. It fit because the node had 67.4 GB of RAM and DuckDB was capped
at 47 GB. That is a precondition, not a victory, and the film says so.

**4. The "one copy versus two copies" badge was simply false.**
I had the Warehouse route holding two copies and this route holding one. Both
routes hold two. The mirror persists raw Delta; any gold layer persists a
second set of files, whether it lands in a lakehouse or in warehouse storage.
Dropped the badge. The copy that actually gets avoided is the **Import** copy,
and that is a Direct Lake argument, not a DuckDB one.

> This also means `README.md` section 6 is overstated. It says a T-SQL path
> leaves "the lakehouse copy and the warehouse copy" both persisting, which is
> only true if you keep a lakehouse gold you would not build. I will correct
> that paragraph in the repo as part of this work.

**5. V-Order is a point *against* this route, and the film never said it.**
Learn: "By default, V-Order is enabled on all warehouses." For Spark and
lakehouses it is the opposite, "disabled by default for all newly created
workspaces." So a Warehouse gets the Direct Lake read optimisation free, and
this pipeline had to add a second notebook, 233 seconds and about nine cents,
to get the same thing. Direct Lake cold-cache queries improve 40 to 60% with
it, so skipping it was not an option. The film now concedes this out loud.

**6. Warehouse compute cannot be pinned, which cuts both ways.**
Learn: warehouse consumption is "Active vNodes × Active Time" and it
"automatically scales compute resources in response to workload demand." You
cannot choose 4 CU. That makes the alternative's cost unpredictable rather than
expensive, which is a weaker claim than the one I was making, and a truer one.

### What checked out

| Claim | Verified against |
| --- | --- |
| 50,000,001 source rows, 49,406,792 after dedup, 593,209 removed | `UAT.json` → `build.recon` |
| 65,175,479 firings, and the seven per-rule counts sum to it exactly | `UAT.json` → `build.rule_firings` |
| 1,423,088 alerts, 2.88% | `UAT.json` → `verify.checks.risk_bands` |
| 36 gold Delta files, 2,535.8 MB, V-Order true on all 9 tables | `UAT.json` → `verify.tables` |
| 0 orphan customer, merchant and date keys | `UAT.json` → `verify.checks.orphan_keys` |
| 8 vCores, 67.4 GB RAM, DuckDB 1.2.2, 47 GB memory cap, no Spark in globals | `UAT.json` → `build.env` |
| 4 CU, 895 s wall, 0.994 CU-hours, $0.27 for the pipeline | `BUILD_LOG.md` cost table, wall time read live from the jobs API |
| 151 s from a PostgreSQL `UPDATE` to the value readable in OneLake | `BUILD_LOG.md`, the live UAT probe, token `UAT-20260919-091543` |
| 52.4% / 81.7% / 70.5% parse rates | `BUILD_LOG.md` profiling table |
| 10.5 GB zstd from 48 GB in PostgreSQL | `BUILD_LOG.md` |
| First query 11.18 s then 1.59 s; later runs 6.6 and 7.7 s cold | `BUILD_LOG.md` latency table |
| Threshold table 40 → 57, 50 → 29, 60 → 11, 70 → 4, 80 → 1, 90 → 0 | read off the report capture itself |
| 45.8 firings per alert, 80.2% of transactions touched, 39,613,511 | read off the report capture itself |
| Mirroring replication compute free, storage free to 1 TB per CU | Learn, *What is Mirroring in Fabric*, cost section |
| Import copies data, Direct Lake framing copies only metadata | Learn, *Direct Lake overview* |
| A mirrored database's SQL endpoint is read-only | Learn, *Open mirroring in Microsoft Fabric* |

### One number I will not put on screen

The mirror holds **50,000,002** rows against PostgreSQL's 50,000,001. That is
the known fidelity artifact, row 3870725, documented in the build log. The
counts still reconcile after dedup, but quoting "50,000,002" without two
sentences of context would be worse than not quoting it. The film says
50,000,001 for the source and 49,406,792 for the gold, both of which are exact.

---

## Part 2. What the film is now

The last cut was a tour. Eleven things happened and none was argued. This one
has a thesis and three arguments, and it concedes something in each.

> **Fifty million dirty rows, from a laptop's PostgreSQL to a decision a
> manager can act on, for twenty-seven cents. The stack is not the point. The
> three places I took the unfashionable option, and can show the measurement
> that justified it, are the point.**

The three choices, set up at 0:32 and paid off in order:

1. **Open mirroring**, not a nightly export.
2. **DuckDB on a Python notebook**, not Spark and not a T-SQL Warehouse.
3. **Direct Lake**, not Import.

Then a fourth thing that is really the argument underneath all three: every
number in the film is re-measured by an acceptance pass that is allowed to fail.

**Running time: about 2 minutes 50.** Roughly 2.4x the last cut for fewer ideas,
which is the only real fix for "too fast". I will also cut a **35-second
vertical edit** from the same scenes for LinkedIn, where nobody watches three
minutes. Same footage, no new work.

---

## Part 3. Scene by scene

Frame counts at 30fps. Every scene ends on a held frame of at least 45 frames
so a claim is still on screen when the viewer finishes reading it.

### ACT I. The problem. 0:00 to 0:38

---

**Scene 1. Open. 10s / 300f**

Four real vendor marks resolve in: PostgreSQL, Microsoft Fabric, DuckDB, Power
BI. A counter runs to **50,000,001**, the word "rows" arrives in Newsreader
italic underneath.

On screen, held 3s:
> 100 columns. Every one of them text.
> A bank's transaction monitoring, from an on-premises database to a decision
> someone can act on.

---

**Scene 2. The mess. 16s / 480f**

The real dirty values settle onto a grid, one family at a time, each labelled:

| On screen | Label |
| --- | --- |
| `2024-03-11` `11/03/2024` `Mar 11 2024` `2024.03.11` `20240311` | five date formats |
| `RM99.00` `(45.00)` `1,250.50` `USD 3.20` | four ways to write a number |
| `1750529113` | a Unix epoch hiding in a date column |
| `#N/A` `NA` `null` `NULL` `-` `(blank)` | six spellings of nothing |

Then three bars, counting up to their real values:

| Column | Parses cleanly |
| --- | --- |
| `posting_date` | **52.4%** |
| `txn_amount` | **81.7%** |
| `balance_after` | **70.5%** |

Held line:
> Half the dates do not parse. The cleaning step is the product, not a
> formality.

---

**Scene 3. Three choices. 12s / 360f**

The thesis, then three numbered cards arriving one at a time. This is the
contract with the viewer, and each one gets a matching label when it is paid
off later.

> 1. Move it without touching the source.
> 2. Transform it without paying for a cluster.
> 3. Serve it without keeping a third copy.

Held:
> Every number after this is measured on the running system. Where something is
> modelled or assumed, it says so while it is on screen.

### ACT II. The three choices. 0:38 to 2:14

---

**Scene 4. Choice one: mirroring, not an export. 22s / 660f**

Four routes build left to right, each with what it actually costs. The first
three grey out as their cost lands. The fourth stays.

| Route | What it costs |
| --- | --- |
| Nightly full export | 10.5 GB moved every night, about 3.8 TB a year. Up to 24 hours stale. A delete needs a full reload. |
| Scheduled incremental copy | Needs an inbound connection to the source, and a watermark you trust. Misses hard deletes entirely. |
| Native mirroring for PostgreSQL | Not available here. This source is on localhost. Fabric cannot reach it. |
| **Open mirroring** | The publisher pushes. No inbound connection. Seed once, then only changes move. Insert, update **and delete**, through `__rowMarker__`. |

Then the payoff, held 3s:

> **151 seconds.** A row updated in PostgreSQL, read back by value out of a
> Delta table in OneLake. Measured on every acceptance run, not once.

And the scar, in smaller type:
> Create the replication slot **before** the snapshot. Do it the other way and
> the changes in the gap vanish, and the row counts still match, so nothing
> tells you.

Footnote strip, cited: replication compute is free and does not consume
capacity; mirrored storage is free to 1 TB per capacity unit purchased.

---

**Scene 5. The architecture, as a live document. 24s / 720f**

**Real screen capture of `architecture-diagram/index.html`**, not a redrawn
lookalike. Framed in a light browser chrome so it reads as a page, with the
file path visible in the address bar.

What the capture shows, in order:
1. The two platform containers draw themselves, PostgreSQL on the left,
   Microsoft Fabric on the right.
2. Nodes land carrying their real vendor icons. Wires grow. Packets ride them.
3. The segmented control switches **Pipeline → Transformation** and the board
   rebuilds into the seven-rule detail.
4. A node is clicked and its explanation card opens over the board.
5. The card **flips** to the written back face.

Caption over the lower third:
> The same architecture as a page you can click through. It ships in the repo.
> Every figure on it is re-measured by the acceptance pass.

---

**Scene 6. Choice two: DuckDB, and where it loses. 36s / 1080f**

The longest scene in the film, because it is the one you said was missing. Five
beats.

**6a. The precondition. 6s.**
> 50,000,001 rows. 100 text columns. 10.5 GB compressed, 48 GB in PostgreSQL.
> One node: 8 vCores, 67.4 GB of RAM, DuckDB 1.2.2 capped at 47 GB.
> It fits on the node. Everything after this depends on that sentence.

**6b. The rate, with the concession attached. 7s.**
The three-row table above, animated in. The single-node Spark row lands last
and in the same weight as the others, not greyed.
> Against a single-node Spark session the rate is identical. The saving is
> against the default starter pool, which is what you get if you do not think
> about it.

**6c. The measurement. 8s.**
Bars with the real logos.

| Step | CU | Wall | CU-hours | at $0.18/CU-h |
| --- | --- | --- | --- | --- |
| DuckDB transform, Python kernel | 4 | 895 s | 0.994 | $0.18 |
| V-Order write, Spark starter pool | 8 | 233 s | 0.518 | $0.09 |
| **This pipeline** | | | **1.512** | **$0.27** |
| Modelled alternative at 8 CU, same wall time | 8 | 895 s | 1.989 | $0.36 |

Three badges stay on screen through the beat: **measured**, **modelled**,
**assumed rate**. The wall time is the billed number, startup included, read
live from the jobs API.

**6d. Where the Warehouse route wins. 8s.** The credibility beat.
> Fabric Warehouse turns V-Order on by default. This pipeline had to add a
> second notebook, 233 seconds and nine cents, to get the same thing.
> Warehouse compute autoscales, so you cannot pin it to 4 CU either way.
> And Microsoft's own guidance puts 10 to 13 GB compressed exactly where Spark
> with the Native Execution Engine catches up, and where single-machine engines
> start running out of memory.
>
> **This dataset is 10.5 GB. It is on that line.**

**6e. Why I still chose it. 7s.** The practitioner's argument.
Two code panes, same column, same problem, side by side:

- **T-SQL**: a `TRY_CONVERT` ladder, one branch per style code, and no
  equivalent for the epoch rows.
- **DuckDB**: one `coalesce(try_strptime(col, [...formats]))` chain, plus
  `make_timestamp` for the epoch rows.

Held:
> The job is parsing, not aggregation, and the dialect is built for parsing.
> The same file also runs on my laptop against the same fifty million rows.
> A warehouse stored procedure does not.

---

**Scene 7. What the choice produced. 16s / 480f**

50,000,001 scored. **593,209** duplicates visibly lift off the stack.
**49,406,792** land in the gold fact.

The seven rules light in firing order with their real counts:

| Rule | Weight | Firings |
| --- | --- | --- |
| `declined` | 10 | 24,580,346 |
| `new_merchant` | 10 | 13,697,031 |
| `card_not_present` | 25 | 10,164,144 |
| `odd_hour` | 15 | 10,118,821 |
| `amount_anomaly` | 30 | 3,624,172 |
| `high_risk_mcc` | 25 | 2,126,003 |
| `velocity` | 30 | 864,962 |

They total **65,175,479**, which is the alert fact's row count exactly.

Held:
> 12.8 minutes of work. Three consecutive runs on capacity, identical rule by
> rule. Getting there cost two real bugs: a timestamp that changed meaning
> between my laptop's timezone and the capacity's, and a window function whose
> tiebreak was not deterministic and quietly lost 87,000 firings a run.

### ACT III. The payoff. 2:14 to 2:50

---

**Scene 8. Choice three: Direct Lake, not Import. 14s / 420f**

Two paths, animated:

- **Import**: a third copy of the data, held in the model, rebuilt on a
  schedule, paying capacity on every refresh whether anything changed or not,
  and stale in between.
- **Direct Lake**: reads the Delta files the notebook wrote. A refresh copies
  only metadata. Framing takes seconds.

Then the measured latency:

| | Seconds |
| --- | --- |
| First query after a reframe, transcoding 49.4m rows into memory | **11.18** |
| The same query, warm | **1.59** |
| The page's own 2,508-cell cube, warm | **1.33** |

Held:
> After the first query, every page of the report is a one-second question
> against fifty million rows, and nothing was copied into a warehouse to make
> it so.

---

**Scene 9. The report, page by page. 30s / 900f**

**This is the scene that was broken.** The crops were cover-fit against guessed
boxes, so a 14-to-1 strip was blown up until a tenth of it filled the frame.
Every crop below is **measured off the card borders** in the capture's own
pixel space (4258 x 2394), and every one is **contain-fit**, never cover.

Layout adapts to the crop's shape, which is the actual fix:
- a wide crop gets the **full frame width**, with its sentence in a band above
- a tall or square crop sits **beside** its sentence

Each page opens whole for 1 second so you can see it is a page, then moves to
its one visual.

| # | Page | Crop `[x, y, w, h]` | What the line says |
| --- | --- | --- | --- |
| 1 | Overview | `[28, 394, 2120, 240]` then pan to `[2130, 394, 2100, 240]` | The strip states its own denominator: 49,406,792 of 49,406,792 in scope, 100%. A filtered page can never be mistaken for the whole population. |
| 2 | Overview | `[36, 668, 2684, 906]` | 31 months, stacked by risk band. The stub bar on the far left is rows whose date never parsed. Shown, not dropped. |
| 3 | Overview | `[2752, 1616, 1478, 740]` | A firing is not an alert. The card prints that underneath itself, because the two differ by 45.8x. |
| 4 | Rule effectiveness | `[44, 558, 2292, 886]` | Weight and volume are different things, so both are on the table. `declined` fires 25m times at weight 10. `velocity` fires 865k times at weight 30. |
| 5 | Rule effectiveness | `[2364, 1474, 1848, 886]` | What a threshold costs, in people. This is the decision the whole pipeline exists to support. |
| 6 | Risk and exposure | `[2130, 558, 2100, 890]` | The currency list holds `458`, `NA` and `#N/A` beside USD and MYR. RM 89m sits in currencies that cannot be resolved, and the header says so. |
| 7 | Guide | `[20, 300, 490, 630]`, portrait, beside its text | Seven sections shipped inside the report. The last one is called **What this cannot do**. |

---

**Scene 10. The decision it supports. 14s / 420f**

The chain, one step at a time, each holding:

> **65,175,479 firings → 1,423,088 alerts → a cut-off → 11 analysts.**

Then the threshold table, with row 60 highlighted as current:

| Cut-off | Alerts | Rate | Analysts |
| --- | --- | --- | --- |
| 40 | 7.1m | 14.38% | 57 |
| 50 | 3.6m | 7.22% | 29 |
| **60 (current)** | **1.4m** | **2.88%** | **11** |
| 70 | 450k | 0.91% | 4 |
| 80 | 184k | 0.37% | 1 |

Held, quoting the report's own footnote:
> Assumes 50,000 alerts cleared per analyst-year. Moving the cut-off is a
> staffing decision, not a preference.
>
> A queue of 317 analyst-loads is ignored. A queue of 11 is worked.

---

**Scene 11. Proof, and the close. 16s / 480f**

Four proof cards:

| | |
| --- | --- |
| **36 / 36** | acceptance checks pass, 1 skipped |
| **0** | orphan dimension keys across 49,406,792 rows |
| **3 runs** | identical, rule by rule |
| **$0.27** | per full rebuild |

Held:
> The pass re-measures the source, updates a probe row in PostgreSQL and reads
> it back out of OneLake by value, and is allowed to fail. It has failed. It
> caught a README that told the reader to build a broken mirror.

Then the stack in real marks, then your portrait at full size, your name in
Newsreader, "Analytics Engineer", and the two links.

---

## Part 4. How it gets built

**The diagram capture, scene 5.** The page already exposes `window.__setView()`
and has real buttons for the flip and the theme, which is how `verify.py`
drives it. A Playwright script opens `index.html` at 1920x1080, drives that
sequence on a timer, and writes a PNG per frame to the scratch directory.
ffmpeg 8.1.2 encodes them to a single mp4 that Remotion plays with
`<OffthreadVideo>`. The frames stay out of the repo. Only the mp4, a few MB,
goes into `video/public/`.

**Everything else** stays as it is: Remotion 4.0.526 on React 19, every
animation driven by `useCurrentFrame()` and `interpolate()`, no CSS transitions
or keyframes anywhere, so the render is deterministic.

**Brand.** Unchanged, and still taken from sulaimanahmed.dev: the sage cream
paper, leaf green, Newsreader italic for emphasis, Plus Jakarta Sans for body,
JetBrains Mono for anything numeric, the two easing curves. Vendor colour
appears only on vendor marks. That keeps the film, the diagram and the site
reading as one hand.

**Verification before I show it to you.** A script that:
1. re-reads `UAT.json` and asserts every number in the scene files matches it,
   so a stale figure like `39 / 39` cannot survive a render again
2. renders a still at the midpoint of all 11 scenes and at both edges of every
   report beat
3. asserts every report crop is fully inside the source image and that the
   rendered scale is contain, never cover
4. checks no text overlaps and nothing sits outside the title-safe area

## Part 5. Repo corrections this turns up

Separate from the film, and I will do them with it:

1. `README.md` section 6, the "two copies never get made" paragraph. Overstated
   for the reason in Part 1 item 4. Rewrite around the Import copy, which is the
   copy actually avoided.
2. `README.md` section 6 should name the single-node Spark rate, since it
   already quotes the other two rows from the same Learn table.
3. Add the 10 to 13 GB benchmark band as a stated caveat, next to "this job is
   10.5 GB compressed and fits", which currently reads as more confident than
   the evidence supports.

## Part 6. Two things I need from you

1. **Audio.** Still silent. Silent works muted on LinkedIn but is thin on its
   own. I would add a quiet music bed and soft marks on the count-ups and the
   scene cuts. Yes or no, and I will build it in from the start rather than
   bolt it on.
2. **The concession beats.** Scene 6d spends eight seconds saying where this
   design loses. I think it is the most valuable eight seconds in the film for
   the audience you are aiming at, because it is the thing a weak portfolio
   piece never does. Say if you would rather it were shorter.

---

## Part 7. As built

Kept for honesty. Where the finished film differs from the plan above, and why.

**Running time is 3:24, not 2:50.** The per-scene frame counts in Part 3 are
exactly what was built and what you approved. My summary line added them up
wrong. 300 + 480 + 360 + 660 + 720 + 1080 + 480 + 420 + 900 + 420 + 480 comes
to 6300 frames, less 160 frames of cross-dissolve, which is 6140 frames and
3 minutes 24.7 seconds at 30fps. I did not trim scenes to hit the number I had
written down, because the scene lengths were the thing being approved.

**Scene 9 carries seven crops, not eight.** The two halves of the KPI strip
were planned as a pan. One crop reads better than a pan across a strip, so the
left half is shown and the whole strip is visible a second earlier in the
page-establishing shot.

**The social cut is 4:5, at 1080 x 1350.** Scaling the master into a phone-width
column makes its tables small, so the caption above the footage carries the
message and the footage is evidence underneath it. 35.3 seconds.

**Three layout bugs were caught by the stills pass**, which is why it exists:
the diagram scene's browser frame was being flex-shrunk and clipping 90px off
the capture; the stage label and the page label were stacking on top of each
other in scene 9; and the portrait crop sat too far from the sentence it
belonged to. All three are now asserted rather than eyeballed.

**Four more stale claims turned up in the architecture diagram's back face**
after the first correction pass, in different words each time. Only watching the
rendered film caught them. The gate now scans the diagram's own text, since
scene 5 puts it on screen.

**Audio: none.** You said go without answering the question, so the film is
silent, which is what the plan defaulted to and what works muted in a feed. Say
the word and I will add a bed and sound marks.
