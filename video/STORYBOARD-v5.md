# v5 storyboard

Built to the Lukas Reese guide. Three gates before a render: storyboard, then
a frame sheet, then the MP4. A change at the storyboard costs a minute, at the
frame sheet three, after the render an hour.

Brand comes from `brand.md`. Every move in the new work comes from
`video/src/motion/library.ts` by name, and none runs longer than 1.2 s.

## What changes from v4, and what does not

v4 is right about the argument and wrong about the pacing. Against the guide's
library its moves run two to three seconds each, which is one move where there
should be three.

**Three things are new:**

1. **It opens on the finished report, not on the problem.** The guide's own
   before and after is a dashboard page that arrives, clears, and has one
   claim land on the empty stage. Showing the result first buys the right to
   spend two minutes on how it was built.
2. **The two real artifacts get the six-beat treatment** instead of v4's
   exploded view. Taking a page apart shows that it has parts. Clearing it and
   rebuilding it shows which part matters, and in what order, because the eye
   follows what arrives.
3. **A named motion library and a brand file**, so a scene no longer invents
   its own timing or its own colours.

**Eight scenes carry over from v4 unchanged.** Being honest about that: their
internal timing is tuned to their own length, so re-cutting them to library
durations is a rebuild of each scene, not a trim, and it is not what buys the
most. The saving comes from the two artifact scenes, which drop from 1,590
frames to 960 and say more.

## The beats

| # | scene | frames | s | what happens |
|---|---|---|---|---|
| 1 | hook | 150 | 5.0 | **new.** 01 the finished report arrives whole. 02 it clears, and the claim lands: *Fifty million rows. Twenty-seven cents.* |
| 2 | table | 420 | 14.0 | the real source table, readable. two date cells lift: 11/03/2024 against 03/11/2024. pull back to the wall, sweep it. |
| 3 | mirror | 540 | 18.0 | the publisher pushes. parquet lands, `_metadata.json` last. |
| 4 | gap | 600 | 20.0 | a photograph and a recorder. the tape is the floor. two real rows fall through. the counts match and the mirror is wrong. |
| 5 | cluster | 420 | 14.0 | the cluster collapses to one node. 8 CU against 4 CU. |
| 6 | transform | 540 | 18.0 | seven rules score in place, 593,209 duplicates lift out, the star assembles. |
| 7 | arch | 420 | 14.0 | **new.** the architecture page, six beats. holds on on-prem and on Fabric, then the panel. was 690. |
| 8 | serve | 420 | 14.0 | import against Direct Lake. three copies against two. |
| 9 | report | 540 | 18.0 | **new.** the report page, all six beats. holds on the KPI strip and on rule firings. the panel is the query times. was 900. |
| 10 | threshold | 450 | 15.0 | the cut-off slides and the analyst headcount moves with it. |
| 11 | close | 390 | 13.0 | 36 of 36 checks, the card, the concession. |

Transitions: 20 frames between each pair.

**Total: 4,690 frames at 30 fps = 2 min 36 s.** Inside the three-minute
ceiling, and 17 seconds shorter than v4 while carrying the same evidence and
opening on the result.

## The moves, by name

| move | duration | used in |
|---|---|---|
| count-up | 0.8 s | the rows behind the architecture page |
| bar-grow | 0.4 s each | the query-time bars in the report panel |
| highlight-sweep | 1.2 s | the sweep across both pages, the repo line in the hook |
| zoom-to-kpi | 0.6 s | every hold in scenes 7 and 9 |
| line-draw | 1.0 s | the page arriving |
| ring-fill | 0.9 s | held in reserve |
| card-stagger | 0.15 s apart | every rebuild, both panels, the filed pages |
| strip-back | 0.5 s | the page clearing, both panels arriving |
| cursor-click | 0.7 s | held in reserve |

Two moves are defined and unused. They stay in the library because the library
is the vocabulary, not a manifest of this one film.

## Render settings

From the guide's pitfalls: 30 fps, `yuv420p` so it plays on a phone, and the
page captures are 2x so the zoom-to-kpi holds stay sharp.
