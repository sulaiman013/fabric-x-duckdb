/**
 * The frame, divided once, for every scene.
 *
 * v4 read as half empty and an audit proved it: coverage between 20% and 60%
 * with dead bands up to 63% of the height. The cause was that each scene
 * hand-placed absolute coordinates, every stage was sized far smaller than the
 * frame, and the bottom third only received content in the last few seconds.
 *
 * So the frame is now divided once, here, and every scene fills all three
 * bands for its whole duration:
 *
 *   HEAD    the caption. one or two lines, never more.
 *   STAGE   the moving object. it must FILL this box, not sit in the middle
 *           of it. 1728 x 596 is the working area.
 *   FOOT    a live read-out strip. present from early in the scene, not
 *           delivered as a punchline at the end, because a bottom band that is
 *           empty for twelve seconds is what the eye reads as waste.
 *
 * scripts/space_audit.py is the gate that keeps it honest.
 */
import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { c, font } from "../theme";
import { ramp, pop } from "./bits";

export const SAFE = 96;
export const FRAME_W = 1920;
export const FRAME_H = 1080;

export const HEAD_Y = 62;
export const HEAD_H = 148;

export const STAGE_Y = 226;
export const STAGE_H = 596;
export const STAGE_W = FRAME_W - SAFE * 2;

export const FOOT_Y = 852;
export const FOOT_H = 164;

/** A scene, laid out into the three bands. */
export const SceneFrame: React.FC<{
  head?: React.ReactNode;
  stage: React.ReactNode;
  foot?: React.ReactNode;
  /** draws the bands, for checking the layout while building */
  debug?: boolean;
}> = ({ head, stage, foot, debug = false }) => (
  <>
    {debug ? (
      <>
        {[
          [HEAD_Y, HEAD_H, "head"],
          [STAGE_Y, STAGE_H, "stage"],
          [FOOT_Y, FOOT_H, "foot"],
        ].map(([y, h, n]) => (
          <div
            key={n as string}
            style={{
              position: "absolute",
              left: SAFE,
              top: y as number,
              width: STAGE_W,
              height: h as number,
              border: "1px dashed rgba(215,52,49,.5)",
            }}
          />
        ))}
      </>
    ) : null}

    {head ? (
      <div style={{ position: "absolute", left: SAFE, top: HEAD_Y, width: STAGE_W, height: HEAD_H }}>
        {head}
      </div>
    ) : null}

    <div
      style={{
        position: "absolute",
        left: SAFE,
        top: STAGE_Y,
        width: STAGE_W,
        height: STAGE_H,
      }}
    >
      {stage}
    </div>

    {foot ? (
      <div style={{ position: "absolute", left: SAFE, top: FOOT_Y, width: STAGE_W, height: FOOT_H }}>
        {foot}
      </div>
    ) : null}
  </>
);

/** The caption that lives in the head band. */
export const Head: React.FC<{
  at?: number;
  kicker?: React.ReactNode;
  children: React.ReactNode;
  size?: number;
}> = ({ at = 4, kicker, children, size = 54 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = pop(frame, fps, at);
  return (
    <div style={{ opacity: Math.min(1, p * 1.2), transform: `translateY(${(1 - p) * 20}px)` }}>
      {kicker ? (
        <div
          style={{
            fontFamily: font.mono,
            fontSize: 14,
            letterSpacing: 2.6,
            textTransform: "uppercase",
            color: c.muted,
            marginBottom: 12,
          }}
        >
          {kicker}
        </div>
      ) : null}
      <div style={{ fontFamily: font.serif, fontSize: size, color: c.ink, lineHeight: 1.06 }}>
        {children}
      </div>
    </div>
  );
};

export type Stat = {
  /** the big value */
  v: React.ReactNode;
  /** what it is */
  l: React.ReactNode;
  tone?: "ink" | "green" | "amber" | "red";
  at?: number;
  /** renders smaller, for supporting numbers */
  small?: boolean;
};

/**
 * The read-out strip that fills the foot band.
 *
 * Every scene has one and it appears early, because the whole reason the film
 * looked empty is that this band was blank for most of every scene.
 */
export const Readout: React.FC<{
  stats: Stat[];
  note?: React.ReactNode;
  at?: number;
  /** a rule above the strip, which anchors it to the frame */
  rule?: boolean;
}> = ({ stats, note, at = 20, rule = true }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = pop(frame, fps, at);

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {rule ? (
        <div
          style={{
            height: 1,
            background: c.border,
            marginBottom: 26,
            transform: `scaleX(${ramp(frame, [at, at + 26])})`,
            transformOrigin: "left",
          }}
        />
      ) : null}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 62, flex: 1 }}>
        {stats.map((s, i) => {
          const sp = pop(frame, fps, (s.at ?? at) + i * 4);
          const col = { ink: c.ink, green: c.greenInk, amber: c.amberInk, red: c.redInk }[
            s.tone ?? "ink"
          ];
          return (
            <div
              key={i}
              style={{
                opacity: sp,
                transform: `translateY(${(1 - sp) * 14}px)`,
                flex: "0 0 auto",
              }}
            >
              <div
                style={{
                  fontFamily: font.mono,
                  fontWeight: 700,
                  fontSize: s.small ? 38 : 56,
                  color: col,
                  fontVariantNumeric: "tabular-nums",
                  lineHeight: 1,
                }}
              >
                {s.v}
              </div>
              <div
                style={{
                  fontFamily: font.mono,
                  fontSize: 13,
                  letterSpacing: 1.7,
                  textTransform: "uppercase",
                  color: c.muted,
                  marginTop: 11,
                  maxWidth: 260,
                  lineHeight: 1.4,
                }}
              >
                {s.l}
              </div>
            </div>
          );
        })}

        {note ? (
          <div
            style={{
              marginLeft: "auto",
              maxWidth: 620,
              textAlign: "right",
              alignSelf: "center",
              opacity: p,
              fontFamily: font.serifItalic,
              fontStyle: "italic",
              fontSize: 27,
              lineHeight: 1.32,
              color: c.greenInk,
            }}
          >
            {note}
          </div>
        ) : null}
      </div>
    </div>
  );
};
