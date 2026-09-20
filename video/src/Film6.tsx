/**
 * The film, v6.
 *
 * Two changes from v5, both asked for after watching it.
 *
 * The pages are FULL BLEED. Both captures are 16:9, so a page shown whole is
 * the frame, with no dark border framing it. v5 fitted them to 1620 and 1660
 * inside a 1920 frame, which put a black surround around the two artifacts
 * that are the point of the film.
 *
 * And v4's theatre move is back, as a beat inside the six rather than instead
 * of them. The page arrives whole, clears, takes its claim, rebuilds card by
 * card, and THEN comes forward and pulls apart in 3D while the camera walks
 * among the pieces. The rebuild says which card matters and in what order. The
 * pull-apart says the page is a set of separate decisions. Those are different
 * jobs, so v6 does both.
 *
 * Total 4930 frames at 30 fps, which is 2:44, inside the three-minute ceiling.
 */
import React from "react";
import { AbsoluteFill } from "remotion";
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

export const SCENES6 = [
  { id: "hook", dur: 150, C: S0Hook },
  { id: "table", dur: 420, C: S1Field },
  { id: "mirror", dur: 540, C: S2Mirror },
  { id: "gap", dur: 600, C: S3Gap },
  { id: "cluster", dur: 420, C: S4Cluster },
  { id: "transform", dur: 540, C: S5Transform },
  { id: "arch", dur: 540, C: S7ArchSix },
  { id: "serve", dur: 420, C: S6Serve },
  { id: "report", dur: 660, C: S9ReportSix },
  { id: "threshold", dur: 450, C: S7Threshold },
  { id: "close", dur: 390, C: S8Close },
] as const;

const TRANS = 20;

export const TOTAL6 = SCENES6.reduce((a, s) => a + s.dur, 0) - TRANS * (SCENES6.length - 1);

type CutKind = "fade" | "slide" | "wipe";

/**
 * A cut, as an element rather than a component. TransitionSeries inspects its
 * children by type, so a <Cut /> wrapper is rejected at runtime even though it
 * renders a Transition.
 */
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

/**
 * The film grade.
 *
 * The palette fix handles the film's own scenes, but the two artifact pages
 * are real Power BI and HTML captures on white, and since v6 made them full
 * bleed they fill the frame at a median luminance of 0.98. They cannot be
 * recoloured without misrepresenting the artifact, so they get graded like
 * footage instead: the highlights come down, the colour comes up slightly so
 * the result reads rich rather than washed, and the dark room is barely
 * touched because a multiply on sRGB moves the bright end far more than the
 * dark end.
 */
const Grade: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill style={{ filter: "brightness(0.94) saturate(1.08)" }}>{children}</AbsoluteFill>
);

export const Film6: React.FC = () => (
  <Grade>
    <TransitionSeries>
    {SCENES6.flatMap((s, i) => {
      const C = s.C;
      const nodes = [
        <TransitionSeries.Sequence key={s.id} durationInFrames={s.dur}>
          <C />
        </TransitionSeries.Sequence>,
      ];
      if (i < SCENES6.length - 1) {
        nodes.push(cut(CUTS[i], s.id + "-cut"));
      }
      return nodes;
    })}
    </TransitionSeries>
  </Grade>
);
