/**
 * Motion primitives. The v3 film failed because every scene was a headline, a
 * paragraph and a table: an animated slide deck, not motion graphics.
 *
 * The rule for v4 is that every scene owns one central object that MOVES and
 * that IS the idea. Text becomes a caption on that object rather than the
 * subject of the frame. These are the pieces those objects are built from.
 *
 * Everything is driven by useCurrentFrame(). Entrances use spring() rather than
 * linear interpolation, because a spring accelerates and settles like a real
 * object and linear motion reads as robotic.
 */
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig, Easing } from "remotion";
import { noise2D } from "@remotion/noise";
import { c, font, EASE_OUT } from "../theme";

const ease = Easing.bezier(...EASE_OUT);

/** interpolate with the house curve and clamped ends. */
export const ramp = (
  frame: number,
  range: readonly [number, number],
  out: readonly [number, number] = [0, 1],
) =>
  interpolate(frame, range as unknown as number[], out as unknown as number[], {
    easing: ease,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

/** A spring that starts at `at` and returns 0 to 1. The default is the house
 *  entrance: snappy, almost no overshoot, settles fast. */
export const pop = (
  frame: number,
  fps: number,
  at: number,
  cfg: { damping?: number; stiffness?: number; mass?: number } = {},
) =>
  spring({
    frame: frame - at,
    fps,
    config: { damping: cfg.damping ?? 14, stiffness: cfg.stiffness ?? 110, mass: cfg.mass ?? 0.7 },
  });

/** A bouncier spring, for things that should feel physical: packets landing,
 *  plates stacking, a cluster collapsing. */
export const bounce = (frame: number, fps: number, at: number) =>
  spring({ frame: frame - at, fps, config: { damping: 9, stiffness: 140, mass: 0.8 } });

/* ------------------------------------------------------------------ camera */

/**
 * A camera. Scenes are composed at a fixed size and the camera moves over them,
 * which is what makes a frame feel filmed rather than laid out.
 *
 * Push in, pull back and pan are the three moves used. transform-origin is the
 * focus point in scene coordinates, so a push-in can target one cell of a grid.
 */
export const Camera: React.FC<{
  children: React.ReactNode;
  /** [zoomAt, zoomTo] pairs applied over [from, to] frames */
  moves?: Array<{ from: number; to: number; scale: number; x?: number; y?: number }>;
  origin?: string;
  style?: React.CSSProperties;
}> = ({ children, moves = [], origin = "50% 50%", style }) => {
  const frame = useCurrentFrame();

  let scale = 1;
  let tx = 0;
  let ty = 0;
  for (const m of moves) {
    const p = ramp(frame, [m.from, m.to]);
    scale = scale + (m.scale - 1) * p;
    tx += (m.x ?? 0) * p;
    ty += (m.y ?? 0) * p;
  }

  return (
    <AbsoluteFill
      style={{
        transform: `translate(${tx}px, ${ty}px) scale(${scale})`,
        transformOrigin: origin,
        ...style,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

/* ----------------------------------------------------------------- counter */

/**
 * A number that races to its value on a spring and then holds. A counter still
 * ticking after the eye has moved on reads as a loading spinner, so this lands
 * early and stops.
 */
export const Odometer: React.FC<{
  to: number;
  at?: number;
  size?: number;
  color?: string;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  /** frames over which the count runs */
  dur?: number;
  style?: React.CSSProperties;
}> = ({ to, at = 0, size = 120, color = c.ink, prefix = "", suffix = "", decimals = 0, dur = 45, style }) => {
  const frame = useCurrentFrame();
  const p = ramp(frame, [at, at + dur]);
  const v = p * to;
  const shown = decimals > 0 ? v.toFixed(decimals) : Math.round(v).toLocaleString("en-GB");
  return (
    <span
      style={{
        fontFamily: font.mono,
        fontWeight: 700,
        fontSize: size,
        letterSpacing: -size * 0.025,
        color,
        fontVariantNumeric: "tabular-nums",
        lineHeight: 1,
        display: "inline-block",
        ...style,
      }}
    >
      {prefix}
      {shown}
      {suffix}
    </span>
  );
};

/* ------------------------------------------------------------------ sparks */

/**
 * A burst of particles from a point. Used when a rule fires over the data
 * field: the firing is an event, so it should look like one.
 */
export const Sparks: React.FC<{
  x: number;
  y: number;
  at: number;
  n?: number;
  spread?: number;
  color?: string;
  seed?: number;
  life?: number;
}> = ({ x, y, at, n = 14, spread = 120, color = c.amber, seed = 1, life = 26 }) => {
  const frame = useCurrentFrame();
  const t = frame - at;
  if (t < 0 || t > life) return null;
  const p = t / life;
  return (
    <>
      {Array.from({ length: n }).map((_, i) => {
        const a = noise2D(`spark-a-${seed}`, i, 0) * Math.PI * 2;
        const d = (0.45 + Math.abs(noise2D(`spark-d-${seed}`, i, 1)) * 0.55) * spread;
        const ease2 = 1 - Math.pow(1 - p, 3);
        const px = x + Math.cos(a) * d * ease2;
        const py = y + Math.sin(a) * d * ease2 - p * p * 14;
        const size = 4 + Math.abs(noise2D(`spark-s-${seed}`, i, 2)) * 4;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: px - size / 2,
              top: py - size / 2,
              width: size,
              height: size,
              borderRadius: 999,
              background: color,
              opacity: (1 - p) * 0.9,
            }}
          />
        );
      })}
    </>
  );
};

/* --------------------------------------------------------------- scan line */

/**
 * A vertical read head that sweeps across a region. Everything it passes has
 * been processed. This is how parsing, scoring and reading are shown: as a
 * pass over data rather than as a sentence about a pass over data.
 */
export const ScanHead: React.FC<{
  x: number;
  height: number;
  color?: string;
  glow?: number;
  opacity?: number;
}> = ({ x, height, color = c.green, glow = 90, opacity = 1 }) => (
  <>
    <div
      style={{
        position: "absolute",
        left: x - glow,
        top: 0,
        width: glow,
        height,
        background: `linear-gradient(90deg, transparent, ${color}22)`,
        opacity,
      }}
    />
    <div
      style={{
        position: "absolute",
        left: x - 1.5,
        top: 0,
        width: 3,
        height,
        background: color,
        boxShadow: `0 0 18px ${color}`,
        opacity,
      }}
    />
  </>
);

/* ------------------------------------------------------------------- label */

/** A caption pinned to the motion, not a headline competing with it. */
export const Caption: React.FC<{
  at: number;
  children: React.ReactNode;
  sub?: React.ReactNode;
  x?: number;
  y?: number;
  size?: number;
  align?: "left" | "center";
  tone?: "ink" | "green" | "amber" | "red";
  style?: React.CSSProperties;
}> = ({ at, children, sub, x, y, size = 46, align = "left", tone = "ink", style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = pop(frame, fps, at);
  const col = { ink: c.ink, green: c.greenInk, amber: c.amberInk, red: c.redInk }[tone];
  return (
    <div
      style={{
        position: x !== undefined || y !== undefined ? "absolute" : "relative",
        left: x,
        top: y,
        textAlign: align,
        opacity: Math.min(1, p * 1.2),
        transform: `translateY(${(1 - p) * 22}px)`,
        ...style,
      }}
    >
      <div
        style={{
          fontFamily: font.serif,
          fontSize: size,
          lineHeight: 1.1,
          color: col,
          letterSpacing: -size * 0.012,
        }}
      >
        {children}
      </div>
      {sub ? (
        <div
          style={{
            fontFamily: font.mono,
            fontSize: Math.max(13, size * 0.3),
            letterSpacing: 1.8,
            textTransform: "uppercase",
            color: c.muted,
            marginTop: 12,
          }}
        >
          {sub}
        </div>
      ) : null}
    </div>
  );
};

/* -------------------------------------------------------------------- slab */

/** A hardware-ish box: a node, a worker, a table, a plate. Springs in. */
export const Slab: React.FC<{
  x: number;
  y: number;
  w: number;
  h: number;
  at: number;
  tone?: "white" | "green" | "amber" | "red" | "ghost";
  children?: React.ReactNode;
  style?: React.CSSProperties;
  /** 0 to 1, dims the slab without removing it */
  dim?: number;
}> = ({ x, y, w, h, at, tone = "white", children, style, dim = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = pop(frame, fps, at);
  const tones = {
    white: { bg: c.white, bd: c.border },
    green: { bg: c.greenBg, bd: c.greenLine },
    amber: { bg: c.amberBg, bd: c.amberLine },
    red: { bg: c.redBg, bd: "#F0C3C1" },
    ghost: { bg: "rgba(255,255,255,.45)", bd: c.border },
  }[tone];
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: w,
        height: h,
        background: tones.bg,
        border: `1px solid ${tones.bd}`,
        borderRadius: 14,
        opacity: p * (1 - dim * 0.72),
        transform: `translateY(${(1 - p) * 18}px) scale(${0.92 + p * 0.08})`,
        boxShadow: "0 1px 2px rgba(22,29,17,.04), 0 12px 30px rgba(22,29,17,.07)",
        filter: dim > 0 ? `grayscale(${dim})` : undefined,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/** Fine shimmering texture, layered under a field so a few thousand visible
 *  cells read as many millions. */
export const Grain: React.FC<{ opacity?: number; speed?: number }> = ({
  opacity = 1,
  speed = 0.35,
}) => {
  const frame = useCurrentFrame();
  const shift = (frame * speed) % 96;
  return (
    <>
      {/* a fine weave, plus a coarser rule every 96px, so the paper reads as a
          drawing surface. The frame should never contain a region that is
          simply nothing. */}
      <AbsoluteFill
        style={{
          backgroundImage: `repeating-linear-gradient(90deg, ${c.greenLine}66 0 1px, transparent 1px 12px),
                            repeating-linear-gradient(0deg, ${c.greenLine}55 0 1px, transparent 1px 12px)`,
          opacity: 0.55 * opacity,
          pointerEvents: "none",
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage: `repeating-linear-gradient(90deg, ${c.border} 0 1px, transparent 1px 96px),
                            repeating-linear-gradient(0deg, ${c.border} 0 1px, transparent 1px 96px)`,
          backgroundPosition: `${shift}px ${-shift}px`,
          opacity: 0.5 * opacity,
          pointerEvents: "none",
        }}
      />
    </>
  );
};
