/**
 * The film, v5. Cut to the guide's method.
 *
 * Three things change from v4.
 *
 * It opens on the finished report rather than on the problem. The guide's own
 * before and after is a dashboard page that arrives, clears, and has one claim
 * land on it. Showing the result first buys the right to spend two minutes on
 * how it was built.
 *
 * The two real artifacts get the six-beat treatment instead of the exploded
 * view. Taking a page apart shows that it has parts. Clearing it and
 * rebuilding it shows which part matters, and in what order, because the eye
 * follows what arrives. That is 630 frames shorter and says more.
 *
 * And every move in the new work comes from src/motion/library.ts by name,
 * with the guide's durations, so nothing runs longer than 1.2 seconds.
 *
 * Total 4690 frames at 30 fps, which is 2:36, inside the three-minute ceiling.
 */
import React from "react";
import { TransitionSeries, linearTiming, springTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";

import { S0Hook } from "./scenes5/S0Hook";
import { S7ArchSix } from "./scenes5/S7ArchSix";
import { S9ReportSix } from "./scenes5/S9ReportSix";

import { S1Field } from "./scenes4/S1Field";
import { S2Mirror } from "./scenes4/S2Mirror";
import { S3Gap } from "./scenes4/S3Gap";
import { S4Cluster } from "./scenes4/S4Cluster";
import { S5Transform } from "./scenes4/S5Transform";
import { S6Serve } from "./scenes4/S6Serve";
import { S7Threshold } from "./scenes4/S7Threshold";
import { S8Close } from "./scenes4/S8Close";

export const SCENES5 = [
  { id: "hook", dur: 150, C: S0Hook },
  { id: "table", dur: 420, C: S1Field },
  { id: "mirror", dur: 540, C: S2Mirror },
  { id: "gap", dur: 600, C: S3Gap },
  { id: "cluster", dur: 420, C: S4Cluster },
  { id: "transform", dur: 540, C: S5Transform },
  { id: "arch", dur: 420, C: S7ArchSix },
  { id: "serve", dur: 420, C: S6Serve },
  { id: "report", dur: 540, C: S9ReportSix },
  { id: "threshold", dur: 450, C: S7Threshold },
  { id: "close", dur: 390, C: S8Close },
] as const;

const TRANS = 20;

export const TOTAL5 = SCENES5.reduce((a, s) => a + s.dur, 0) - TRANS * (SCENES5.length - 1);

/**
 * A cut, as an element rather than a component.
 *
 * TransitionSeries inspects its children by type, so a <Cut /> wrapper is
 * rejected at runtime even though it renders a Transition. The factory has to
 * return the Transition itself.
 */
type CutKind = "fade" | "slide" | "wipe";

const cut = (kind: CutKind, key: string) =>
  kind === "slide" ? (
    <TransitionSeries.Transition
      key={key}
      timing={springTiming({ config: { damping: 200 }, durationInFrames: TRANS })}
      presentation={slide({ direction: "from-right" })}
    />
  ) : kind === "wipe" ? (
    <TransitionSeries.Transition
      key={key}
      timing={linearTiming({ durationInFrames: TRANS })}
      presentation={wipe({ direction: "from-bottom" })}
    />
  ) : (
    <TransitionSeries.Transition
      key={key}
      timing={linearTiming({ durationInFrames: TRANS })}
      presentation={fade()}
    />
  );

/** which cut joins each pair, in order */
const CUTS: CutKind[] = [
  "fade", // hook to table: the claim dissolves into what it cost
  "slide", // table to mirror: we are travelling somewhere
  "wipe", // mirror to gap: cutting the same story open
  "slide",
  "fade",
  "slide", // transform to arch
  "fade",
  "fade", // serve to report
  "wipe",
  "fade",
];

export const Film5: React.FC = () => (
  <TransitionSeries>
    {SCENES5.flatMap((s, i) => {
      const C = s.C;
      const nodes = [
        <TransitionSeries.Sequence key={s.id} durationInFrames={s.dur}>
          <C />
        </TransitionSeries.Sequence>,
      ];
      if (i < SCENES5.length - 1) {
        nodes.push(cut(CUTS[i], s.id + "-cut"));
      }
      return nodes;
    })}
  </TransitionSeries>
);
