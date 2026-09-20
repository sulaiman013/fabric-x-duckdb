/**
 * The film, assembled. v3.
 *
 * v2 was a tour: eleven things happened, none was argued, and the whole thing
 * ran 70 seconds. This one has a thesis and three arguments, and it concedes
 * something inside each of them. Scene 6, the DuckDB argument, is deliberately
 * the longest thing in the film at 36 seconds, because it is the one a viewer
 * would otherwise have to take on trust.
 *
 * Scenes cross-dissolve by OVERLAP frames. A hard cut between two pale green
 * frames reads as a glitch; a short dissolve reads as a page turn.
 */
import React from "react";
import { AbsoluteFill, Sequence, interpolate, useCurrentFrame } from "remotion";
import { c } from "./theme";
import { S01Open } from "./scenes/S01Open";
import { S02Mess } from "./scenes/S02Mess";
import { S03Choices } from "./scenes/S03Choices";
import { S04Mirror } from "./scenes/S04Mirror";
import { S05Diagram } from "./scenes/S05Diagram";
import { S06Duck } from "./scenes/S06Duck";
import { S07Result } from "./scenes/S07Result";
import { S08DirectLake } from "./scenes/S08DirectLake";
import { S09Report } from "./scenes/S09Report";
import { S10Decision } from "./scenes/S10Decision";
import { S11Close } from "./scenes/S11Close";

/** Frames of cross-dissolve between consecutive scenes. */
export const OVERLAP = 16;

export type Scene = { id: string; dur: number; C: React.FC; act: 1 | 2 | 3 };

export const SCENES: Scene[] = [
  { id: "open", dur: 300, C: S01Open, act: 1 },
  { id: "mess", dur: 480, C: S02Mess, act: 1 },
  { id: "choices", dur: 360, C: S03Choices, act: 1 },

  { id: "mirror", dur: 660, C: S04Mirror, act: 2 },
  { id: "diagram", dur: 720, C: S05Diagram, act: 2 },
  { id: "duckdb", dur: 1080, C: S06Duck, act: 2 },
  { id: "result", dur: 480, C: S07Result, act: 2 },

  { id: "directlake", dur: 420, C: S08DirectLake, act: 3 },
  { id: "report", dur: 900, C: S09Report, act: 3 },
  { id: "decision", dur: 420, C: S10Decision, act: 3 },
  { id: "close", dur: 480, C: S11Close, act: 3 },
];

/** Start frame of each scene, accounting for the overlap. */
export const starts = SCENES.reduce<number[]>((acc, s, i) => {
  acc.push(i === 0 ? 0 : acc[i - 1] + SCENES[i - 1].dur - OVERLAP);
  return acc;
}, []);

export const TOTAL = starts[starts.length - 1] + SCENES[SCENES.length - 1].dur;

/** Fades a scene in and out at its own edges. */
const Dissolve: React.FC<{
  dur: number;
  first: boolean;
  last: boolean;
  children: React.ReactNode;
}> = ({ dur, first, last, children }) => {
  const frame = useCurrentFrame();
  const fadeIn = first
    ? 1
    : interpolate(frame, [0, OVERLAP], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
  const fadeOut = last
    ? 1
    : interpolate(frame, [dur - OVERLAP, dur], [1, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
  return <AbsoluteFill style={{ opacity: fadeIn * fadeOut }}>{children}</AbsoluteFill>;
};

export const Film: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: c.paper }}>
      {SCENES.map((s, i) => (
        <Sequence key={s.id} from={starts[i]} durationInFrames={s.dur} name={s.id}>
          <Dissolve dur={s.dur} first={i === 0} last={i === SCENES.length - 1}>
            <s.C />
          </Dissolve>
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
