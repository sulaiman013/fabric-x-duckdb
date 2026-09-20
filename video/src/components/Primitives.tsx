/**
 * The film's vocabulary: eight scenes are built from these six pieces, which is
 * what keeps them looking like one document rather than eight slides.
 *
 * Every animation is driven by useCurrentFrame() and interpolate(). No CSS
 * transitions or keyframes anywhere: they do not render deterministically.
 */
import React from "react";
import { AbsoluteFill, interpolate, Easing, useCurrentFrame } from "remotion";
import { c, font, EASE_OUT, rand } from "../theme";

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

/* ------------------------------------------------------------------ paper */

/**
 * The ground every scene sits on: the brand paper, a soft leaf wash that drifts
 * so a held frame never looks frozen, and a hairline grid that reads as graph
 * paper rather than decoration.
 */
export const Paper: React.FC<{ children: React.ReactNode; drift?: number }> = ({
  children,
  drift = 0,
}) => {
  const frame = useCurrentFrame();
  const x = Math.sin((frame + drift) / 190) * 26;
  const y = Math.cos((frame + drift) / 240) * 20;
  return (
    <AbsoluteFill style={{ background: c.paper, overflow: "hidden" }}>
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(${c.divider} 1px, transparent 1px),
                            linear-gradient(90deg, ${c.divider} 1px, transparent 1px)`,
          backgroundSize: "80px 80px",
          opacity: 0.5,
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(760px 520px at ${50 + x / 6}% ${38 + y / 8}%, ${c.greenBg} 0%, transparent 70%)`,
          opacity: 0.85,
        }}
      />
      {children}
      {/* a held edge, so the frame has a boundary rather than bleeding out */}
      <AbsoluteFill
        style={{
          boxShadow: `inset 0 0 0 1px ${c.border}, inset 0 0 200px rgba(22,29,17,.035)`,
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------- type */

/** The mono micro-label. Always uppercase, always tracked out. */
export const Mono: React.FC<{
  children: React.ReactNode;
  at?: number;
  size?: number;
  color?: string;
  style?: React.CSSProperties;
}> = ({ children, at = 0, size = 18, color = c.muted, style }) => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        fontFamily: font.mono,
        fontSize: size,
        letterSpacing: size * 0.13,
        textTransform: "uppercase",
        fontWeight: 500,
        color,
        opacity: ramp(frame, [at, at + 12]),
        transform: `translateY(${ramp(frame, [at, at + 16], [8, 0])}px)`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/**
 * The serif headline, revealed word by word. Word-level stagger reads as
 * someone speaking; character-level reads as a machine typing, which is the
 * wrong register for this film.
 */
export const Display: React.FC<{
  text: string;
  at?: number;
  size?: number;
  color?: string;
  italicFrom?: number;
  stagger?: number;
  style?: React.CSSProperties;
}> = ({ text, at = 0, size = 96, color = c.ink, italicFrom, stagger = 3.2, style }) => {
  const frame = useCurrentFrame();
  const words = text.split(" ");
  return (
    <div
      style={{
        fontFamily: font.serif,
        fontSize: size,
        lineHeight: 1.08,
        fontWeight: 400,
        color,
        letterSpacing: -size * 0.012,
        display: "flex",
        flexWrap: "wrap",
        gap: `0 ${size * 0.26}px`,
        ...style,
      }}
    >
      {words.map((w, i) => {
        const t = at + i * stagger;
        const italic = italicFrom !== undefined && i >= italicFrom;
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              opacity: ramp(frame, [t, t + 18]),
              transform: `translateY(${ramp(frame, [t, t + 24], [30, 0])}px)`,
              fontFamily: italic ? font.serifItalic : font.serif,
              fontStyle: italic ? "italic" : "normal",
              color: italic ? c.greenInk : color,
            }}
          >
            {w}
          </span>
        );
      })}
    </div>
  );
};

/** Body copy, one line at a time. */
export const Line: React.FC<{
  children: React.ReactNode;
  at?: number;
  size?: number;
  color?: string;
  weight?: number;
  style?: React.CSSProperties;
}> = ({ children, at = 0, size = 28, color = c.body, weight = 400, style }) => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        fontFamily: font.sans,
        fontSize: size,
        lineHeight: 1.45,
        fontWeight: weight,
        color,
        opacity: ramp(frame, [at, at + 14]),
        transform: `translateY(${ramp(frame, [at, at + 20], [14, 0])}px)`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/* ---------------------------------------------------------------- numbers */

/**
 * A number that counts to its value. The count is the point of several scenes,
 * so it eases out hard and lands early, then holds: a counter still ticking
 * when the eye has moved on reads as a loading spinner.
 */
export const CountUp: React.FC<{
  to: number;
  at?: number;
  dur?: number;
  size?: number;
  color?: string;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  style?: React.CSSProperties;
}> = ({
  to,
  at = 0,
  dur = 40,
  size = 110,
  color = c.ink,
  prefix = "",
  suffix = "",
  decimals = 0,
  style,
}) => {
  const frame = useCurrentFrame();
  const v = ramp(frame, [at, at + dur], [0, to]);
  const shown =
    decimals > 0
      ? v.toFixed(decimals)
      : Math.round(v).toLocaleString("en-GB");
  return (
    <div
      style={{
        fontFamily: font.mono,
        fontWeight: 700,
        fontSize: size,
        letterSpacing: -size * 0.02,
        color,
        fontVariantNumeric: "tabular-nums",
        opacity: ramp(frame, [at, at + 10]),
        ...style,
      }}
    >
      {prefix}
      {shown}
      {suffix}
    </div>
  );
};

/* ------------------------------------------------------------------ chips */

/** A pill. Used for dirty values, rule names and stage labels. */
export const Chip: React.FC<{
  children: React.ReactNode;
  at?: number;
  tone?: "neutral" | "green" | "amber" | "red";
  size?: number;
  mono?: boolean;
  style?: React.CSSProperties;
}> = ({ children, at = 0, tone = "neutral", size = 26, mono = true, style }) => {
  const frame = useCurrentFrame();
  const tones = {
    neutral: { bg: c.white, bd: c.border, fg: c.body },
    green: { bg: c.greenBg, bd: c.greenLine, fg: c.greenInk },
    amber: { bg: c.amberBg, bd: c.amberLine, fg: c.amberInk },
    red: { bg: c.redBg, bd: "#F0C3C1", fg: c.redInk },
  }[tone];
  const p = ramp(frame, [at, at + 18]);
  return (
    <div
      style={{
        fontFamily: mono ? font.mono : font.sans,
        fontSize: size,
        fontWeight: 500,
        color: tones.fg,
        background: tones.bg,
        border: `1px solid ${tones.bd}`,
        borderRadius: 999,
        padding: `${size * 0.38}px ${size * 0.82}px`,
        whiteSpace: "nowrap",
        opacity: p,
        transform: `scale(${0.88 + p * 0.12})`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/** A framed card, the same one the diagram and the report use. */
export const Card: React.FC<{
  children: React.ReactNode;
  at?: number;
  style?: React.CSSProperties;
  tone?: "white" | "green";
}> = ({ children, at = 0, style, tone = "white" }) => {
  const frame = useCurrentFrame();
  const p = ramp(frame, [at, at + 22]);
  return (
    <div
      style={{
        background: tone === "green" ? c.greenBg : c.white,
        border: `1px solid ${tone === "green" ? c.greenLine : c.border}`,
        borderRadius: 18,
        opacity: p,
        transform: `translateY(${(1 - p) * 26}px)`,
        boxShadow: "0 1px 2px rgba(22,29,17,.04), 0 12px 28px rgba(22,29,17,.05)",
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/* ------------------------------------------------------------------ flow */

/**
 * A horizontal flow line with packets riding it, the same language as the
 * architecture diagram: a solid base, a marching dash on top, dots in motion.
 */
export const Flow: React.FC<{
  x: number;
  y: number;
  w: number;
  at?: number;
  dots?: number;
  color?: string;
  speed?: number;
}> = ({ x, y, w, at = 0, dots = 3, color = c.green, speed = 90 }) => {
  const frame = useCurrentFrame();
  const grow = ramp(frame, [at, at + 26]);
  const t = Math.max(0, frame - at);
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, height: 2 }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          width: w * grow,
          background: color,
          opacity: 0.9,
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          width: w * grow,
          backgroundImage: `repeating-linear-gradient(90deg, ${c.greenHi} 0 12px, transparent 12px 26px)`,
          backgroundPositionX: `${-((t * 0.9) % 26)}px`,
          opacity: 0.95,
        }}
      />
      {Array.from({ length: dots }).map((_, i) => {
        const phase = (t / speed + i / dots + rand(i + 7) * 0.1) % 1;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: w * grow * phase - 5,
              top: -4,
              width: 10,
              height: 10,
              borderRadius: 999,
              background: color,
              border: `1.6px solid ${c.paper}`,
              opacity: grow * (phase < 0.06 ? phase / 0.06 : phase > 0.94 ? (1 - phase) / 0.06 : 1),
            }}
          />
        );
      })}
    </div>
  );
};

/** The film's lower-third label: a step number and its name. */
export const Stage: React.FC<{ n: string; label: string; at?: number }> = ({
  n,
  label,
  at = 0,
}) => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        position: "absolute",
        left: 96,
        top: 92,
        display: "flex",
        alignItems: "center",
        gap: 14,
        opacity: ramp(frame, [at, at + 14]),
        transform: `translateX(${ramp(frame, [at, at + 20], [-14, 0])}px)`,
      }}
    >
      <div
        style={{
          fontFamily: font.mono,
          fontSize: 15,
          fontWeight: 700,
          color: c.greenInk,
          background: c.greenBg,
          border: `1px solid ${c.greenLine}`,
          borderRadius: 999,
          padding: "5px 12px",
          letterSpacing: 1.6,
        }}
      >
        {n}
      </div>
      <div
        style={{
          fontFamily: font.mono,
          fontSize: 15,
          letterSpacing: 2.2,
          textTransform: "uppercase",
          color: c.muted,
          fontWeight: 500,
        }}
      >
        {label}
      </div>
    </div>
  );
};
