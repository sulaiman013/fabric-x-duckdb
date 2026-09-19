# Architecture diagram

Interactive, animated, single-file HTML covering the whole pipeline: how 50
million rows get from an on-premises PostgreSQL table to a Power BI report on
Microsoft Fabric, and what each hop cost. `index.html` is the deliverable; open
it directly, no server.

Built in the same design language as the reference architecture deck next door,
so the two read as one hand. The theme comes from
[sulaimanahmed.dev](https://sulaimanahmed.dev).

## The two views

One shell, one design language, two views behind the segmented control top
right. The choice is remembered in `localStorage` (`arch-view`).

| View | Question it answers |
| --- | --- |
| **Pipeline** | How does data get from PostgreSQL to a report? Open mirroring with a seed and a live change feed on the left, the DuckDB transformation, the Spark V-Order write, Direct Lake and the report on the right. |
| **Transformation** | What does the notebook actually do? Read the mirror in place, conform 100 text columns, score seven measured rules, resolve 593,209 duplicates, build the star. Plus the three rules that make the build reproducible. |

The card also flips (top right) to a written explanation: how to identify the
architecture, thirteen steps source to report, a guarantees table with what
enforces each one, the arguments worth having, and the numbers.

## Every figure is measured

Nothing on the page is an estimate except the two things that say **modelled**:
the Spark cost comparison, and the price per CU-hour. Everything else was
observed on the running system and is recorded in
[`../BUILD_LOG.md`](../BUILD_LOG.md), then re-measured by
[`../scripts/uat.py`](../scripts/uat.py) on every acceptance pass.

| | |
| --- | --- |
| Source | 50,000,001 rows, 100 TEXT columns, 48 GB as loaded |
| Gold | 49,406,792 rows after 593,209 duplicates resolved |
| Rebuild | 770 s of DuckDB work inside an 895 s billed session, 8 vCores |
| V-Order | 233 s, the only Spark in the pipeline |
| Compute | 1.512 CU-hours, about $0.27, against 2.507 modelled for Spark |
| Query | about a second warm, 7 to 11 s for the first after a reframe |

## Files

| File | What |
| --- | --- |
| `index.html` | **The diagram, and the only file you need to share.** Built output, self-contained: icons inlined as an SVG sprite, no web fonts, no network. Do not edit by hand. |
| `template.html` | Build input, assembled from `parts/`. Generated, and a second full copy of the page, so do not hand it out. |
| `parts/` | **The source. Edit here.** |
| `assemble.py` | Concatenates `parts/` into `template.html`, then runs `build.py`. This is the whole edit loop: `python assemble.py`. |
| `build.py` | Inlines `icons/*.svg` into a `<symbol>` sprite and writes `index.html`. |
| `verify.py` | **The gate.** Run after any layout edit: `python verify.py`. |
| `icons/` | Vendor SVGs: Fabric item icons and the Fabric mark from Microsoft's `@fabric-msft/svg-icons`, Power BI from `microsoft/PowerBI-Icons`, PostgreSQL, DuckDB and Apache Spark from simple-icons. |
| `shot-*.png` | Playwright renders written by `verify.py`. |

### Inside `parts/`

| Part | What |
| --- | --- |
| `style.css.html` | The brand stylesheet, lifted verbatim. `assemble.py` refuses to build if a theme token has drifted. |
| `style-add.css` | The only additions: the view switcher position, the line-glyph stroke, the grouping band, the back-face sub-headings. |
| `shell-front.html` | Brand bar, header, switcher, containers mount point, KPI row, footer, modal. |
| `back-face.html` | The written explanation. |
| `glyphs.js` | Line glyphs for the parts of this pipeline that are not a vendor product. |
| `view-pipeline.js`, `view-transform.js` | One file per view: containers, nodes, chips, flow strip, KPIs, edges, and the detail card behind every one of them. |
| `renderer.js` | Builds a view into the DOM. |
| `wires.js` | Declarative edges: `{from, to, style}` measured from the live DOM, plus the animation loop. |
| `boot.js` | Modal, view switching, night mode, flip, scale-to-fit. |

## Design rules it follows

**Vendor colour appears only on vendor glyphs.** The Fabric item icons keep
their real gradients; PostgreSQL, DuckDB and Spark are monochrome marks as
simple-icons ships them; everything this pipeline is made of is drawn as line
art in brand green. That rule is what keeps two views looking like one
document.

Amber marks a one-off or scheduled path (the seed) and green marks the
continuous one (the change feed). **Night mode** uses the source site's own dark
ramp and is remembered in `localStorage` (`arch-theme`).

## Verification (do this after any layout edit)

```
python assemble.py     # parts -> template.html -> index.html
python verify.py       # the gate
```

`assemble.py` refuses to build if a theme token has drifted or if any
identifier from another engagement, or an account UPN, has found its way into
the assembled output.

`verify.py` drives both views and asserts, per view: no two interactive
elements overlap, nothing escapes its container or the stage, **the expected
number of wires is actually drawn**, packets move (sampled twice under
`reduced_motion="reduce"`, which the page deliberately ignores), night mode
applies, and the card flips. It then writes the screenshots.

This is not optional ceremony. It caught five real collisions on the first
build of this deck, including a chip sitting on top of two nodes and a flow
strip overlapping a card. The wire-count assertion exists because a box check
cannot see a wire that is *missing*.

## Things that will bite the next editor

- **The canvas is 1800 x 1000 and is declared in three places** that must stay
  in sync: `--W`/`--H` in the CSS, `var W,H` in the script, and the `#wires`
  viewBox.
- **Every card object needs `kv` and `pts`.** The modal renderer maps over both
  with no guard, so a missing one throws when that card is opened.
- **Keys must be unique across all collections in a view** (nodes, chips,
  tiles, flow steps and KPIs share one flat map). `assemble.py` warns on
  repeats.
- **`boot.js` decides the default view by name.** It shipped from the reference
  deck defaulting to a view that does not exist here, which renders an empty
  stage on a fresh open and is invisible to the gate, because the gate sets the
  view explicitly before it looks.
- **Several Fabric icons ship with `width`/`height` and no `viewBox`.**
  A `<symbol>` scales by its viewBox, so `build.py` synthesises one from the
  declared size; without it the icon renders at a fixed pixel size and ignores
  the stylesheet.
- **`draw()` reads `offsetLeft` from the live DOM**, so it must run after
  layout.
- **The animation ignores `prefers-reduced-motion` on purpose.** This machine
  reports it, which made an earlier build look completely static.
- **Spacing is bounded by the KPI row.** Containers run 226 to 786 and the
  footer text inside a container sits at its bottom edge, so cards must stop
  about 20px short of it. The gate asserts containers do not touch the page
  chrome.
- **Wire routing has a rule, and it is load-bearing.** Every wire is a short
  horizontal, a short vertical, or one gentle diagonal through empty space, and
  no wire crosses a card or another wire. That constraint decides where nodes
  sit, not the other way round. If a layout needs a wire to bend around
  something, use `dRaw` with an explicit path rather than forcing a curve
  through a card.
