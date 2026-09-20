/**
 * Wires that draw themselves, and packets that ride them.
 *
 * v3 drew connections as div rectangles whose width grew. That is a bar chart
 * pretending to be a cable. This uses @remotion/paths: evolvePath() turns a
 * progress value into strokeDasharray and strokeDashoffset so an arbitrary
 * curve draws itself, and getPointAtLength() puts a real object at a real
 * position along that same curve.
 *
 * The result is that a packet travels the path the wire actually took, round
 * corners and all, which is the difference between a diagram and a system.
 */
import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { evolvePath, getLength, getPointAtLength } from "@remotion/paths";
import { c } from "../theme";
import { ramp, pop } from "./bits";

/** A smooth cubic between two points, bowed by `bow` pixels. */
export const curve = (
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  bow = 0,
): string => {
  const mx = (x1 + x2) / 2;
  return `M ${x1} ${y1} C ${mx} ${y1 + bow} ${mx} ${y2 + bow} ${x2} ${y2}`;
};

/** An elbow: out horizontally, then vertically, with rounded corners. */
export const elbow = (x1: number, y1: number, x2: number, y2: number, r = 18): string => {
  const dir = y2 > y1 ? 1 : -1;
  const sx = x2 > x1 ? 1 : -1;
  return [
    `M ${x1} ${y1}`,
    `H ${x2 - r * sx}`,
    `Q ${x2} ${y1} ${x2} ${y1 + r * dir}`,
    `V ${y2}`,
  ].join(" ");
};

export type PacketGlyph = "insert" | "update" | "delete" | "plain";

const GLYPH: Record<PacketGlyph, { ch: string; bg: string; fg: string }> = {
  insert: { ch: "+", bg: c.greenBg, fg: c.greenInk },
  update: { ch: "~", bg: c.amberBg, fg: c.amberInk },
  delete: { ch: "x", bg: c.redBg, fg: c.redInk },
  plain: { ch: "", bg: c.white, fg: c.body },
};

/**
 * A self-drawing wire with packets riding it.
 *
 * `drawAt`/`drawDur` control the line drawing itself. Packets then depart on a
 * loop, each one a real element placed with getPointAtLength.
 */
export const Wire: React.FC<{
  d: string;
  drawAt?: number;
  drawDur?: number;
  color?: string;
  width?: number;
  dashed?: boolean;
  /** number of packets in flight at once. 0 draws the wire only. */
  packets?: number;
  packetAt?: number;
  /** frames for one packet to travel the whole wire */
  travel?: number;
  glyph?: PacketGlyph;
  /** cycles the glyph across insert, update and delete */
  mixed?: boolean;
  packetSize?: number;
  labelled?: boolean;
  opacity?: number;
}> = ({
  d,
  drawAt = 0,
  drawDur = 26,
  color = c.green,
  width = 2.5,
  dashed = false,
  packets = 0,
  packetAt,
  travel = 60,
  glyph = "plain",
  mixed = false,
  packetSize = 26,
  labelled = false,
  opacity = 1,
}) => {
  const frame = useCurrentFrame();
  const grow = ramp(frame, [drawAt, drawAt + drawDur]);
  const evolution = evolvePath(grow, d);
  const len = getLength(d);
  const pStart = packetAt ?? drawAt + drawDur * 0.6;

  return (
    <>
      <svg
        style={{ position: "absolute", inset: 0, overflow: "visible", pointerEvents: "none" }}
        width="100%"
        height="100%"
      >
        <path
          d={d}
          fill="none"
          stroke={color}
          strokeWidth={width}
          strokeLinecap="round"
          // a dashed wire marches instead of drawing itself: it is a scheduled
          // path, not a live one, and the difference should be visible
          strokeDasharray={dashed ? "9 9" : evolution.strokeDasharray}
          strokeDashoffset={dashed ? -((frame * 0.8) % 18) : evolution.strokeDashoffset}
          opacity={opacity * (dashed ? 0.45 : 0.9) * (dashed ? 1 : grow > 0 ? 1 : 0)}
        />
      </svg>

      {Array.from({ length: packets }).map((_, i) => {
        const t = frame - pStart - (i * travel) / packets;
        if (t < 0) return null;
        const phase = (t % travel) / travel;
        const at = getPointAtLength(d, phase * len);
        if (!at) return null;
        const fade = phase < 0.06 ? phase / 0.06 : phase > 0.94 ? (1 - phase) / 0.06 : 1;
        const g = GLYPH[mixed ? (["insert", "update", "delete"] as PacketGlyph[])[i % 3] : glyph];
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: at.x - packetSize / 2,
              top: at.y - packetSize / 2,
              width: packetSize,
              height: packetSize,
              borderRadius: 6,
              background: g.bg,
              border: `1.5px solid ${color}`,
              display: "grid",
              placeItems: "center",
              fontFamily: "monospace",
              fontSize: packetSize * 0.52,
              fontWeight: 700,
              color: g.fg,
              opacity: opacity * fade,
              boxShadow: `0 2px 8px rgba(22,29,17,.12)`,
            }}
          >
            {labelled ? g.ch : null}
          </div>
        );
      })}
    </>
  );
};

/**
 * One packet whose journey we follow, rather than an anonymous loop. Used for
 * the beat where a single committed change is chased from the write-ahead log
 * into a Delta table and timed.
 */
export const TracedPacket: React.FC<{
  d: string;
  at: number;
  dur: number;
  size?: number;
  color?: string;
  label?: string;
}> = ({ d, at, dur, size = 34, color = c.greenInk, label }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const len = getLength(d);
  const p = ramp(frame, [at, at + dur]);
  if (frame < at) return null;
  const point = getPointAtLength(d, p * len);
  if (!point) return null;
  const s = pop(frame, fps, at);

  return (
    <div
      style={{
        position: "absolute",
        left: point.x - size / 2,
        top: point.y - size / 2,
        width: size,
        height: size,
        borderRadius: 8,
        background: c.greenBg,
        border: `2px solid ${color}`,
        display: "grid",
        placeItems: "center",
        transform: `scale(${s})`,
        boxShadow: `0 0 0 6px ${c.green}22, 0 4px 14px rgba(22,29,17,.18)`,
        zIndex: 5,
      }}
    >
      {label ? (
        <span
          style={{
            position: "absolute",
            top: -26,
            left: "50%",
            transform: "translateX(-50%)",
            fontFamily: "monospace",
            fontSize: 13,
            whiteSpace: "nowrap",
            color: c.greenInk,
            fontWeight: 700,
          }}
        >
          {label}
        </span>
      ) : null}
    </div>
  );
};
