# v6 storyboard

Built to the Lukas Reese guide. Three gates before a render: storyboard, then
a frame sheet, then the MP4. Brand comes from `brand.md`. Every move in the new
work comes from `video/src/motion/library.ts` by name.

## What v6 changes from v5

**The pages are full bleed.** Both captures are 16:9, so a page shown whole is
the frame. v5 fitted them inside it, which put a black border around the two
artifacts the film exists to show.

The border turned out not to be a sizing problem. A page is drawn as *cards*,
not as one image, and the card rects were measured tightly around each visual.
The page's own outer margins and inner gutters belonged to no card, and every
pixel no card claims shows the dark room behind it. So the rects in
`scenes5/cards.tsx` now **tile** the capture: each is snapped outward to the
midline between its neighbours, every pixel belongs to exactly one card, and
each card carries its own gutter. That also fixed a second thing nobody had
noticed: the tight rects were cropping the page header and footer out of shot.

**v4's theatre move is back, as a beat inside the six rather than instead of
them.** The page arrives whole, clears, takes its claim, rebuilds card by card,
and then comes forward and pulls apart in 3D with tilt, depth and shadow.

The two ideas do different jobs and v6 keeps both. The clear-and-rebuild says
*which* card matters and in what order, because the eye follows what arrives.
The pull-apart says the page is a set of separate decisions rather than one
picture.

## The beats

| # | scene | frames | s | what happens |
|---|---|---|---|---|
| 1 | hook | 150 | 5.0 | the finished report arrives full bleed, clears, and the claim lands: *Fifty million rows. Twenty-seven cents.* |
| 2 | table | 420 | 14.0 | the real source table, readable. 11/03/2024 against 03/11/2024. pull back to the wall, sweep it. |
| 3 | mirror | 540 | 18.0 | the publisher pushes. parquet lands, `_metadata.json` last. |
| 4 | gap | 600 | 20.0 | a photograph and a recorder. the tape is the floor. two real rows fall through. |
| 5 | cluster | 420 | 14.0 | the cluster collapses to one node. 8 CU against 4 CU. |
| 6 | transform | 540 | 18.0 | seven rules score in place, 593,209 duplicates out, the star assembles. |
| 7 | **arch** | 540 | 18.0 | full six beats plus the pull-apart. holds on on-prem and on Fabric, then the panel. |
| 8 | serve | 420 | 14.0 | import against Direct Lake. three copies against two. |
| 9 | **report** | 660 | 22.0 | full six beats plus the pull-apart. holds on the KPI strip and on rule firings. the panel is the query times. |
| 10 | threshold | 450 | 15.0 | the cut-off slides and the analyst headcount moves with it. |
| 11 | close | 390 | 13.0 | 36 of 36 checks, the card, the concession. |

Transitions: 20 frames between each pair.

**Total: 4,930 frames at 30 fps = 2 min 44 s.** Inside the three-minute
ceiling.

## The order of beats inside a page

Learned the hard way on the first v6 cut: the pull-apart and the camera holds
were overlapping, so a hold landed on a card whose neighbours were scattered
and half cut by the frame edge. Each beat now takes its own turn.

| beat | arch | report |
|---|---|---|
| 01 page arrives | 2 | 2 |
| 02 clears, claim | 62 | 64 |
| 03 rebuilds | 150 | 185 |
| 05 sweep | 176 | 222 |
| 3b pulls apart | 224 | 270 |
| 3b closes | 290 | 340 |
| 04 hold one | 332 | 384 |
| 04 hold two | 396 | 448 |
| 06 panel | 470 | 530 |
| scene ends | 540 | 660 |

`spread` is 0.2, not v4's 0.46. A page that fills the frame has no room to
throw cards into, so the gaps come from the rig backing off 24% while the page
is open rather than from flinging cards outward.

## Render settings

30 fps, `yuv420p` so it plays on a phone, captures at 2x so the holds stay
sharp.
