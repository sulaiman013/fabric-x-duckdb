# The film

Three and a half minutes on the whole pipeline: fifty million ungoverned rows in
PostgreSQL, mirrored into OneLake, transformed by DuckDB on a Fabric Python
notebook, V-Ordered by Spark, served by Direct Lake, and answered in a four-page
Power BI report.

Built with [Remotion](https://www.remotion.dev), so the video is a React
component and its source is part of the work rather than a by-product of it.

```bash
npm install
npx remotion studio                                       # scrub the timeline
python scripts/capture_arch.py                            # re-record scene 5
python scripts/verify_film.py                             # the gate
npx remotion render src/index.ts FabricXDuckDB out/fabric-x-duckdb.mp4 --crf=18
npx remotion render src/index.ts Social out/fabric-x-duckdb-social.mp4 --crf=18
```

## Two cuts, one build

| Composition | Size | Length | For |
| --- | --- | --- | --- |
| `FabricXDuckDB` | 1920 x 1080 | 3:24 | watched on purpose, from the repository or a portfolio page |
| `Social` | 1080 x 1350 | 0:35 | a LinkedIn feed, where the master's running time is the wrong ask |

`Social` is a genuine edit, not a second build. Every scene is a pure function
of its frame, so a `Sequence` with a negative offset lets the short seek any
frame of the master. There is no second copy of a scene that can drift from the
first.

## What it argues

The first version was a tour. Eleven things happened, none of them was argued,
and the whole thing ran seventy seconds. This one has a thesis and three
arguments, and it concedes something inside each of them.

> Fifty million dirty rows, from an on-premises PostgreSQL to a decision a
> manager can act on, for twenty-seven cents. The stack is not the point. The
> three places I took the unfashionable option, and can show the measurement
> that justified it, are the point.

1. **Open mirroring, not a nightly export.** Scene 4 puts three alternatives on
   screen with what each one costs, and ends on 151 measured seconds from a
   PostgreSQL `UPDATE` to that value being readable out of Delta.
2. **DuckDB on a Python notebook, not Spark and not a T-SQL Warehouse.** Scene
   6, the longest in the film at 36 seconds, and the only one with a beat whose
   whole job is to say where this design loses.
3. **Direct Lake, not Import.** Scene 8, which is where the copy argument
   actually lives.

## The concession beat

Scene 6d spends eight seconds on three things that favour the Warehouse route:
V-Order is on by default in every warehouse and this pipeline had to add a Spark
step to match it; warehouse compute autoscales so it cannot be pinned to a rate
either way; and Microsoft's own guidance puts the 10 to 13 GB compressed band
where Spark with the Native Execution Engine catches up and single-machine
engines start running out of memory. This dataset is 10.5 GB. It is on that
line.

It is the most valuable eight seconds in the film. A comparison that only runs
one way is an advert.

## Scene 5 is real footage

`scripts/capture_arch.py` drives `architecture-diagram/index.html` through its
own `window.__setView` API in a real browser and records it: the board drawing
itself, a component card opening, the view switching, and the whole page turning
over to its written face. Playwright's recorder is used rather than a screenshot
loop, because a screenshot loop advances the page's own animation clock by
however long each capture took and the packets end up riding three times too
fast.

The output is `public/arch.mp4`, about 22 seconds at 1920 x 1080 and 30fps,
played back with `<OffthreadVideo>`.

## The gate

`scripts/verify_film.py`, 110 checks, run before every render.

The first version of this film shipped with **39 / 39** burned into its last
scene long after the real acceptance figure had become 36, because nothing
compared the film against the artifact it claims to be reporting. So:

| Group | What it asserts |
| --- | --- |
| Numbers | every figure on screen is compared against `UAT.json` or `BUILD_LOG.md`. Retracted claims are banned by pattern, not by memory |
| Crops | every report crop lies inside the source image, is **contain** fitted, stays legible, and never creeps outside the card it was measured from |
| Footage | `arch.mp4` is 1920 x 1080 at 30fps, is long enough for the scene that plays it, and is newer than the diagram it captures |
| Diagram | the diagram's own words are scanned too, because scene 5 puts them on screen |
| Layers | a scene that replaces its own content owns its headline, so nothing is left at full opacity underneath the next thing |
| Social | every window lies inside the master, and the cut seeks rather than rebuilds |
| Text | no em or en dashes anywhere |

Two rounds of correction still left stale claims in the diagram's back face,
and only watching the rendered film caught them. That is the argument for
scanning rather than trusting a reviewer.

## Why the report crops were rebuilt

The previous cut fitted its crop boxes with `Math.max`, which is cover. With a
box of aspect 1.6 and a KPI strip of aspect 8.8, cover scales by the height
ratio and throws away ninety per cent of the width, so the viewer saw a tenth of
a card blown up past legibility.

Every crop is now measured off the card borders in the capture's own pixel space
of 4258 x 2394, fitted with `Math.min`, and given a layout chosen from its own
shape: wide crops take the full frame width with their sentence in a band above,
portrait crops sit beside their sentence.

## House rules

- Every animation is `useCurrentFrame()` and `interpolate()`. No CSS transitions
  or keyframes anywhere: they do not render deterministically.
- Palette, type and the two easing curves come from sulaimanahmed.dev, so the
  film, the architecture diagram and the site read as one hand.
- Vendor colour appears only on vendor marks. Real icons throughout: Fabric item
  icons from Microsoft's own package, PostgreSQL, DuckDB and Spark from
  simple-icons, Power BI from microsoft/PowerBI-Icons.
- Green carries flow and good, amber marks a caveat or a modelled figure, red is
  reserved for bad.
- Any figure that is not read off the running system carries a badge saying
  whether it is measured, modelled, or an assumed rate, while it is on screen.

## Layout

```
src/
  Film.tsx            the master: eleven scenes, 16-frame cross-dissolves
  Short.tsx           the 35-second 4:5 cut, seeking into the master
  Root.tsx            both compositions
  theme.ts            palette, type, the two easings, the seeded random
  components/
    Primitives.tsx    paper, type, count-ups, chips, cards, flow lines
    Blocks.tsx        badges, tables, bars, code panes, browser chrome, stats
    Icon.tsx          real vendor marks
  scenes/             S01 to S11
scripts/
  capture_arch.py     records the architecture diagram for scene 5
  verify_film.py      the gate
public/
  arch.mp4            the capture
  report-*.png        four Power BI Desktop captures at 4258 x 2394
archive/v2-scenes/    the previous cut's scenes, kept for reference
```
