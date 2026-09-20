/**
 * The 35-second social cut. 1080 x 1350, which is the 4:5 LinkedIn favours.
 *
 * No new scenes. Eight windows are lifted out of the master film and replayed
 * in order, which is possible because every scene is a pure function of its
 * frame: a Sequence with a negative offset makes the child see any frame of
 * the master, so this is a genuine edit rather than a second build that can
 * drift from the first.
 *
 * The film sits in the middle at 1080 wide, which makes its body type small.
 * So the caption above it carries the message and the footage is evidence
 * underneath it. That is how the cut stays readable on a phone in a feed,
 * where nobody watches three minutes of anything.
 */
import React from "react";
import { AbsoluteFill, Sequence, interpolate, useCurrentFrame } from "remotion";
import { Film4 } from "./Film4";
import { c, font, EASE_OUT } from "./theme";
import { Easing } from "remotion";

export const SHORT_W = 1080;
export const SHORT_H = 1350;

/** the master is 1920 wide, so this is the scale that fits it to the column */
const SCALE = SHORT_W / 1920;
const FILM_H = Math.round(1080 * SCALE);

type Seg = {
  /** first frame of the window in the master film */
  from: number;
  /** how many frames to play */
  len: number;
  kicker: string;
  line: string;
};

/**
 * Eight windows, chosen so the cut states the thesis, pays off all three
 * choices, concedes once, and signs off.
 */
export const SEGMENTS: Seg[] = [
  { from: 120, len: 130, kicker: "the problem", line: "One table. A hundred columns. Every one of them text." },
  { from: 560, len: 130, kicker: "choice one", line: "Open mirroring. The publisher pushes, so nothing reaches into the source." },
  { from: 1150, len: 135, kicker: "the trap", line: "Create the slot before the snapshot, or the changes fall through a hole." },
  { from: 1610, len: 125, kicker: "choice two", line: "The cluster collapses. One node, and half the capacity units." },
  { from: 2120, len: 130, kicker: "the work", line: "Seven rules, 593,209 duplicates out, and a star schema." },
  { from: 3590, len: 140, kicker: "the report", line: "Each page is one HTML visual. Pulled apart, it is seven." },
  { from: 4450, len: 135, kicker: "the point", line: "Move the cut-off and the analyst headcount moves with it." },
  { from: 4900, len: 135, kicker: "proved", line: "36 acceptance checks, re-measured on every run." },
];

export const SEG_AT: number[] = SEGMENTS.reduce<number[]>((acc, s, i) => {
  acc.push(i === 0 ? 0 : acc[i - 1] + SEGMENTS[i - 1].len);
  return acc;
}, []);

export const SHORT_TOTAL = SEG_AT[SEG_AT.length - 1] + SEGMENTS[SEGMENTS.length - 1].len;

const ease = Easing.bezier(...EASE_OUT);

/** One window of the master, with its caption. */
const Window: React.FC<{ seg: Seg; at: number }> = ({ seg, at }) => (
  <Sequence from={at} durationInFrames={seg.len} name={seg.kicker}>
    <Caption seg={seg} />
    <div
      style={{
        position: "absolute",
        left: 0,
        top: (SHORT_H - FILM_H) / 2 + 70,
        width: SHORT_W,
        height: FILM_H,
        overflow: "hidden",
        borderTop: `1px solid ${c.border}`,
        borderBottom: `1px solid ${c.border}`,
      }}
    >
      <div
        style={{
          width: 1920,
          height: 1080,
          transform: `scale(${SCALE})`,
          transformOrigin: "top left",
        }}
      >
        {/* a negative offset seeks the master to this window's first frame */}
        <Sequence from={-seg.from} name="master">
          <Film4 />
        </Sequence>
      </div>
    </div>
  </Sequence>
);

const Caption: React.FC<{ seg: Seg }> = ({ seg }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [0, 16], [0, 1], {
    easing: ease,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        position: "absolute",
        left: 64,
        right: 64,
        top: 96,
        opacity: p,
        transform: `translateY(${(1 - p) * 18}px)`,
      }}
    >
      <div
        style={{
          fontFamily: font.mono,
          fontSize: 22,
          letterSpacing: 3.4,
          textTransform: "uppercase",
          color: c.greenInk,
          fontWeight: 700,
          marginBottom: 20,
        }}
      >
        {seg.kicker}
      </div>
      <div
        style={{
          fontFamily: font.serif,
          fontSize: 56,
          lineHeight: 1.14,
          color: c.ink,
        }}
      >
        {seg.line}
      </div>
    </div>
  );
};

export const Short: React.FC = () => {
  const frame = useCurrentFrame();
  const progress = frame / SHORT_TOTAL;

  return (
    <AbsoluteFill style={{ background: c.paper }}>
      {SEGMENTS.map((s, i) => (
        <Window key={i} seg={s} at={SEG_AT[i]} />
      ))}

      {/* a progress hairline, so a feed viewer knows how much is left */}
      <div
        style={{
          position: "absolute",
          left: 0,
          bottom: 0,
          height: 6,
          width: SHORT_W * progress,
          background: c.green,
        }}
      />

      {/* the signature, always present, because a feed clip gets seen out of
          context far more often than the master does */}
      <div
        style={{
          position: "absolute",
          left: 64,
          right: 64,
          bottom: 52,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
        }}
      >
        <span style={{ fontFamily: font.serif, fontSize: 32, color: c.ink }}>
          Sulaiman Ahmed<span style={{ color: c.green }}>.</span>
        </span>
        <span style={{ fontFamily: font.mono, fontSize: 20, color: c.muted }}>
          github.com/sulaiman013/fabric-x-duckdb
        </span>
      </div>
    </AbsoluteFill>
  );
};
