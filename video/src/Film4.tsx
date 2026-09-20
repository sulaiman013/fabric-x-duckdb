/**
 * The film, v4. Motion graphics, not an animated slide deck.
 *
 * v3 was eleven scenes of headline, paragraph and table. Every idea was
 * STATED. In v4 every scene owns one object that MOVES and that IS the idea:
 * a field of rows being scanned, packets crossing a boundary, events falling
 * through a hole in a timeline, a cluster imploding into one node, a star
 * schema assembling itself, a threshold sliding while people disappear.
 *
 * Scenes are joined with @remotion/transitions rather than opacity
 * cross-fades, so a cut is a move rather than a dissolve. TransitionSeries
 * shortens the total by the length of each transition, which is accounted for
 * in TOTAL below.
 */
import React from "react";
import { TransitionSeries, linearTiming, springTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";

import { S1Field } from "./scenes4/S1Field";
import { S2Mirror } from "./scenes4/S2Mirror";
import { S3Gap } from "./scenes4/S3Gap";
import { S4Cluster } from "./scenes4/S4Cluster";
import { S5Transform } from "./scenes4/S5Transform";
import { S6Serve } from "./scenes4/S6Serve";
import { S7Threshold } from "./scenes4/S7Threshold";
import { S8Close } from "./scenes4/S8Close";
import { S9Arch } from "./scenes4/S9Arch";
import { S10Report } from "./scenes4/S10Report";

export const SCENES = [
  { id: "field", dur: 420, C: S1Field },
  { id: "mirror", dur: 540, C: S2Mirror },
  { id: "gap", dur: 600, C: S3Gap },
  { id: "cluster", dur: 420, C: S4Cluster },
  { id: "transform", dur: 540, C: S5Transform },
  { id: "arch", dur: 690, C: S9Arch },
  { id: "serve", dur: 420, C: S6Serve },
  { id: "report", dur: 900, C: S10Report },
  { id: "threshold", dur: 450, C: S7Threshold },
  { id: "close", dur: 390, C: S8Close },
] as const;

/** one transition between each pair, in frames */
const TRANS = 20;

export const TOTAL =
  SCENES.reduce((a, s) => a + s.dur, 0) - TRANS * (SCENES.length - 1);

export const Film4: React.FC = () => (
  <TransitionSeries>
    <TransitionSeries.Sequence durationInFrames={SCENES[0].dur}>
      <S1Field />
    </TransitionSeries.Sequence>

    {/* into the gap: a slide, because we are travelling somewhere */}
    <TransitionSeries.Transition
      timing={springTiming({ config: { damping: 200 }, durationInFrames: TRANS })}
      presentation={slide({ direction: "from-right" })}
    />
    <TransitionSeries.Sequence durationInFrames={SCENES[1].dur}>
      <S2Mirror />
    </TransitionSeries.Sequence>

    {/* into the trap: a wipe, because we are cutting the same story open */}
    <TransitionSeries.Transition
      timing={linearTiming({ durationInFrames: TRANS })}
      presentation={wipe({ direction: "from-bottom" })}
    />
    <TransitionSeries.Sequence durationInFrames={SCENES[2].dur}>
      <S3Gap />
    </TransitionSeries.Sequence>

    <TransitionSeries.Transition
      timing={springTiming({ config: { damping: 200 }, durationInFrames: TRANS })}
      presentation={slide({ direction: "from-right" })}
    />
    <TransitionSeries.Sequence durationInFrames={SCENES[3].dur}>
      <S4Cluster />
    </TransitionSeries.Sequence>

    <TransitionSeries.Transition
      timing={linearTiming({ durationInFrames: TRANS })}
      presentation={fade()}
    />
    <TransitionSeries.Sequence durationInFrames={SCENES[4].dur}>
      <S5Transform />
    </TransitionSeries.Sequence>

    <TransitionSeries.Transition
      timing={springTiming({ config: { damping: 200 }, durationInFrames: TRANS })}
      presentation={slide({ direction: "from-right" })}
    />
    <TransitionSeries.Sequence durationInFrames={SCENES[5].dur}>
      <S9Arch />
    </TransitionSeries.Sequence>

    <TransitionSeries.Transition
      timing={linearTiming({ durationInFrames: TRANS })}
      presentation={fade()}
    />
    <TransitionSeries.Sequence durationInFrames={SCENES[6].dur}>
      <S6Serve />
    </TransitionSeries.Sequence>

    <TransitionSeries.Transition
      timing={linearTiming({ durationInFrames: TRANS })}
      presentation={fade()}
    />
    <TransitionSeries.Sequence durationInFrames={SCENES[7].dur}>
      <S10Report />
    </TransitionSeries.Sequence>

    <TransitionSeries.Transition
      timing={linearTiming({ durationInFrames: TRANS })}
      presentation={wipe({ direction: "from-bottom" })}
    />
    <TransitionSeries.Sequence durationInFrames={SCENES[8].dur}>
      <S7Threshold />
    </TransitionSeries.Sequence>

    <TransitionSeries.Transition
      timing={linearTiming({ durationInFrames: TRANS })}
      presentation={fade()}
    />
    <TransitionSeries.Sequence durationInFrames={SCENES[9].dur}>
      <S8Close />
    </TransitionSeries.Sequence>
  </TransitionSeries>
);
