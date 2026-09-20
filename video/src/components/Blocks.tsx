/**
 * The v3 vocabulary: the pieces the argument scenes are built from.
 *
 * v2 was a tour, so it only needed type and a flow line. v3 argues, and an
 * argument needs tables you can read, a way to mark what is measured against
 * what is modelled, and code you can compare side by side.
 *
 * Same rule as Primitives: every animation is useCurrentFrame() + interpolate().
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { ramp } from "./Primitives";
import { c, font } from "../theme";

/* ----------------------------------------------------------------- badges */

export type BadgeTone = "measured" | "modelled" | "assumed" | "neutral";

const BADGE: Record<BadgeTone, { bg: string; bd: string; fg: string }> = {
  measured: { bg: c.greenBg, bd: c.greenLine, fg: c.greenInk },
  modelled: { bg: c.amberBg, bd: c.amberLine, fg: c.amberInk },
  assumed: { bg: c.amberBg, bd: c.amberLine, fg: c.amberInk },
  neutral: { bg: c.white, bd: c.border, fg: c.muted },
};

/**
 * The film's honesty marker. Any figure that is not read off the running
 * system carries one of these while it is on screen, which is the difference
 * between a portfolio piece and an advert.
 */
export const Badge: React.FC<{
  tone: BadgeTone;
  children: React.ReactNode;
  at?: number;
  size?: number;
  style?: React.CSSProperties;
}> = ({ tone, children, at = 0, size = 15, style }) => {
  const frame = useCurrentFrame();
  const t = BADGE[tone];
  const p = ramp(frame, [at, at + 16]);
  return (
    <span
      style={{
        fontFamily: font.mono,
        fontSize: size,
        fontWeight: 600,
        letterSpacing: size * 0.12,
        textTransform: "uppercase",
        color: t.fg,
        background: t.bg,
        border: `1px solid ${t.bd}`,
        borderRadius: 999,
        padding: `${size * 0.32}px ${size * 0.78}px`,
        whiteSpace: "nowrap",
        opacity: p,
        transform: `scale(${0.9 + p * 0.1})`,
        display: "inline-block",
        ...style,
      }}
    >
      {children}
    </span>
  );
};

/* ------------------------------------------------------------------ table */

export type Cell = React.ReactNode;

export type Row = {
  cells: Cell[];
  /** the current or winning row, drawn on the green plate */
  hl?: boolean;
  /** a route that has been ruled out: greys back once its cost lands */
  out?: number;
  /** a totals row: rule above, heavier type */
  total?: boolean;
  at?: number;
};

/**
 * A table that arrives row by row. Used for the four ingestion routes, the CU
 * rates, the cost comparison and the threshold cost, so those four beats read
 * as the same kind of evidence rather than four inventions.
 */
export const DataTable: React.FC<{
  head: Cell[];
  rows: Row[];
  at?: number;
  stagger?: number;
  /** grid-template-columns */
  cols: string;
  size?: number;
  headSize?: number;
  align?: Array<"left" | "right">;
  /** per column: true for tabular data, false for prose. Default: first column
   *  is prose, the rest are data. A sentence set in mono reads as a log line. */
  mono?: boolean[];
  style?: React.CSSProperties;
}> = ({ head, rows, at = 0, stagger = 14, cols, size = 26, headSize = 15, align, mono, style }) => {
  const frame = useCurrentFrame();
  const headP = ramp(frame, [at, at + 14]);
  const al = (i: number) => (align && align[i]) || (i === 0 ? "left" : "right");
  const isMono = (i: number) => (mono ? mono[i] : i !== 0);

  return (
    <div style={{ width: "100%", ...style }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: cols,
          gap: "0 28px",
          padding: "0 22px 12px",
          opacity: headP,
          borderBottom: `1px solid ${c.border}`,
        }}
      >
        {head.map((h, i) => (
          <div
            key={i}
            style={{
              fontFamily: font.mono,
              fontSize: headSize,
              letterSpacing: headSize * 0.14,
              textTransform: "uppercase",
              color: c.faint,
              fontWeight: 600,
              textAlign: al(i),
            }}
          >
            {h}
          </div>
        ))}
      </div>

      {rows.map((r, ri) => {
        const t = r.at !== undefined ? r.at : at + 16 + ri * stagger;
        const p = ramp(frame, [t, t + 20]);
        // a ruled-out route fades back rather than disappearing, so the viewer
        // can still see what was considered
        const dim = r.out !== undefined ? 1 - ramp(frame, [r.out, r.out + 20], [0, 0.58]) : 1;
        return (
          <div
            key={ri}
            style={{
              display: "grid",
              gridTemplateColumns: cols,
              gap: "0 28px",
              alignItems: "center",
              padding: "16px 22px",
              background: r.hl ? c.greenBg : "transparent",
              borderRadius: r.hl ? 12 : 0,
              borderTop: r.total ? `1px solid ${c.border}` : "none",
              marginTop: r.total ? 6 : 0,
              opacity: p * dim,
              transform: `translateY(${(1 - p) * 16}px)`,
            }}
          >
            {r.cells.map((cell, ci) => (
              <div
                key={ci}
                style={{
                  fontFamily: isMono(ci) && !r.total ? font.mono : font.sans,
                  fontSize: size,
                  fontWeight: r.total || r.hl ? 700 : ci === 0 ? 500 : 500,
                  color: r.hl ? c.greenInk : r.total ? c.ink : ci === 0 ? c.ink : c.body,
                  textAlign: al(ci),
                  lineHeight: 1.35,
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {cell}
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
};

/* -------------------------------------------------------------------- bar */

/** A horizontal bar that grows to a share, with its value at the end. */
export const Bar: React.FC<{
  label: React.ReactNode;
  /** 0 to 1 */
  value: number;
  display: string;
  at?: number;
  tone?: "green" | "amber" | "red" | "ink";
  labelW?: number;
  h?: number;
  size?: number;
  sub?: string;
}> = ({ label, value, display, at = 0, tone = "green", labelW = 300, h = 22, size = 24, sub }) => {
  const frame = useCurrentFrame();
  const grow = ramp(frame, [at, at + 34]);
  const p = ramp(frame, [at, at + 14]);
  const fill = { green: c.green, amber: c.amber, red: c.red, ink: c.ink }[tone];
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 22,
        opacity: p,
        transform: `translateY(${(1 - p) * 12}px)`,
      }}
    >
      <div style={{ width: labelW, flex: "0 0 auto" }}>
        <div style={{ fontFamily: font.mono, fontSize: size, color: c.ink, fontWeight: 500 }}>
          {label}
        </div>
        {sub ? (
          <div style={{ fontFamily: font.sans, fontSize: size * 0.66, color: c.muted, marginTop: 3 }}>
            {sub}
          </div>
        ) : null}
      </div>
      <div
        style={{
          flex: 1,
          height: h,
          background: c.rail,
          borderRadius: 999,
          border: `1px solid ${c.divider}`,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${Math.max(0, Math.min(1, value)) * grow * 100}%`,
            height: "100%",
            background: fill,
            borderRadius: 999,
          }}
        />
      </div>
      <div
        style={{
          width: 190,
          flex: "0 0 auto",
          textAlign: "right",
          fontFamily: font.mono,
          fontWeight: 700,
          fontSize: size * 1.06,
          color: tone === "green" ? c.greenInk : tone === "amber" ? c.amberInk : c.ink,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {display}
      </div>
    </div>
  );
};

/* --------------------------------------------------------------- code pane */

export type CodeLine = { t: string; hl?: boolean; dim?: boolean };

/**
 * A code pane for the one beat that compares dialects. Deliberately plain: the
 * argument is the shape of the code, so syntax colour would be noise. The
 * highlighted lines carry the green plate instead.
 */
export const CodePane: React.FC<{
  title: React.ReactNode;
  sub?: string;
  lines: CodeLine[];
  at?: number;
  size?: number;
  tone?: "neutral" | "green";
  style?: React.CSSProperties;
}> = ({ title, sub, lines, at = 0, size = 19, tone = "neutral", style }) => {
  const frame = useCurrentFrame();
  const p = ramp(frame, [at, at + 22]);
  return (
    <div
      style={{
        background: c.white,
        border: `1px solid ${tone === "green" ? c.greenLine : c.border}`,
        borderRadius: 16,
        overflow: "hidden",
        opacity: p,
        transform: `translateY(${(1 - p) * 22}px)`,
        boxShadow: "0 1px 2px rgba(22,29,17,.04), 0 14px 32px rgba(22,29,17,.06)",
        ...style,
      }}
    >
      <div
        style={{
          padding: "16px 22px",
          borderBottom: `1px solid ${c.divider}`,
          background: tone === "green" ? c.greenBg : c.plate,
          display: "flex",
          alignItems: "baseline",
          gap: 12,
        }}
      >
        <span
          style={{
            fontFamily: font.mono,
            fontSize: 17,
            fontWeight: 700,
            letterSpacing: 1.6,
            textTransform: "uppercase",
            color: tone === "green" ? c.greenInk : c.ink,
          }}
        >
          {title}
        </span>
        {sub ? (
          <span style={{ fontFamily: font.sans, fontSize: 17, color: c.muted }}>{sub}</span>
        ) : null}
      </div>
      <div style={{ padding: "18px 22px" }}>
        {lines.map((l, i) => {
          const lt = at + 16 + i * 3;
          const lp = ramp(frame, [lt, lt + 14]);
          return (
            <div
              key={i}
              style={{
                fontFamily: font.mono,
                fontSize: size,
                lineHeight: 1.62,
                whiteSpace: "pre",
                color: l.dim ? c.faint : l.hl ? c.greenInk : c.body,
                fontWeight: l.hl ? 700 : 400,
                background: l.hl ? c.greenBg : "transparent",
                borderRadius: l.hl ? 6 : 0,
                padding: l.hl ? "1px 8px" : "1px 0",
                margin: l.hl ? "0 -8px" : 0,
                opacity: lp,
              }}
            >
              {l.t}
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* ---------------------------------------------------------------- browser */

/**
 * Light browser chrome for the one scene that plays real captured footage.
 * Without a frame the capture reads as a rendered slide, which defeats the
 * point of capturing the real page.
 */
export const Browser: React.FC<{
  url: string;
  children: React.ReactNode;
  at?: number;
  w: number;
  h: number;
  style?: React.CSSProperties;
}> = ({ url, children, at = 0, w, h, style }) => {
  const frame = useCurrentFrame();
  const p = ramp(frame, [at, at + 26]);
  const BAR = 54;
  return (
    <div
      style={{
        width: w,
        height: h + BAR,
        background: c.white,
        border: `1px solid ${c.border}`,
        borderRadius: 16,
        overflow: "hidden",
        opacity: p,
        transform: `translateY(${(1 - p) * 26}px) scale(${0.985 + p * 0.015})`,
        boxShadow: "0 3px 8px rgba(22,29,17,.07), 0 30px 70px rgba(22,29,17,.14)",
        ...style,
      }}
    >
      <div
        style={{
          height: BAR,
          background: c.plate,
          borderBottom: `1px solid ${c.divider}`,
          display: "flex",
          alignItems: "center",
          gap: 14,
          padding: "0 18px",
        }}
      >
        {[c.faint, c.faint, c.faint].map((_, i) => (
          <div
            key={i}
            style={{
              width: 11,
              height: 11,
              borderRadius: 999,
              background: c.border,
              flex: "0 0 auto",
            }}
          />
        ))}
        <div
          style={{
            flex: 1,
            height: 30,
            background: c.white,
            border: `1px solid ${c.border}`,
            borderRadius: 999,
            display: "flex",
            alignItems: "center",
            padding: "0 14px",
            marginLeft: 8,
          }}
        >
          <span style={{ fontFamily: font.mono, fontSize: 15, color: c.muted }}>{url}</span>
        </div>
      </div>
      <div style={{ width: w, height: h, overflow: "hidden", position: "relative" }}>
        {children}
      </div>
    </div>
  );
};

/* -------------------------------------------------------------------- kpi */

/** A number with its label under it. The film's default way to state a fact. */
export const Stat: React.FC<{
  value: React.ReactNode;
  label: React.ReactNode;
  at?: number;
  size?: number;
  tone?: "ink" | "green" | "amber" | "red";
  style?: React.CSSProperties;
}> = ({ value, label, at = 0, size = 52, tone = "ink", style }) => {
  const frame = useCurrentFrame();
  const p = ramp(frame, [at, at + 20]);
  const col = { ink: c.ink, green: c.greenInk, amber: c.amberInk, red: c.redInk }[tone];
  return (
    <div style={{ opacity: p, transform: `translateY(${(1 - p) * 14}px)`, ...style }}>
      <div
        style={{
          fontFamily: font.mono,
          fontWeight: 700,
          fontSize: size,
          color: col,
          letterSpacing: -size * 0.02,
          fontVariantNumeric: "tabular-nums",
          lineHeight: 1.05,
        }}
      >
        {value}
      </div>
      <div
        style={{
          fontFamily: font.mono,
          fontSize: Math.max(12, size * 0.26),
          letterSpacing: size * 0.035,
          textTransform: "uppercase",
          color: c.muted,
          marginTop: 7,
        }}
      >
        {label}
      </div>
    </div>
  );
};

/**
 * The line the film uses to concede something. Set apart from body copy on
 * purpose: a caveat that looks like body copy reads as filler.
 */
export const Caveat: React.FC<{
  children: React.ReactNode;
  at?: number;
  size?: number;
  style?: React.CSSProperties;
}> = ({ children, at = 0, size = 25, style }) => {
  const frame = useCurrentFrame();
  const p = ramp(frame, [at, at + 20]);
  return (
    <div
      style={{
        background: c.amberBg,
        border: `1px solid ${c.amberLine}`,
        borderRadius: 14,
        padding: "20px 26px",
        fontFamily: font.sans,
        fontSize: size,
        lineHeight: 1.45,
        color: c.amberInk,
        opacity: p,
        transform: `translateY(${(1 - p) * 16}px)`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/* ------------------------------------------------------------------ phase */

/**
 * One half of a two-part scene.
 *
 * Several scenes state a thing, clear it, and then state a measurement. The
 * first cut did that by wrapping only the *lower* half in a fading div and
 * leaving the headline outside it, so the headline stayed at full opacity
 * underneath the second half and the two collided. Scene 8 read as a double
 * exposure for six seconds and nothing caught it until the film was watched.
 *
 * So a phase owns everything it shows, including its headline, and returns
 * null once it is invisible. The short overlap while one dissolves into the
 * next is a dissolve; a headline that never leaves is a bug.
 */
export const Phase: React.FC<{
  /** frame this phase starts fading in */
  at?: number;
  /** frame it starts fading out. Omit for a phase that stays to the end. */
  out?: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({ at = 0, out, children, style }) => {
  const frame = useCurrentFrame();
  const inP = at === 0 ? 1 : ramp(frame, [at, at + 18]);
  const outP = out === undefined ? 1 : 1 - ramp(frame, [out, out + 24]);
  const o = inP * outP;
  if (o <= 0.002) return null;
  return (
    <AbsoluteFill style={{ opacity: o, ...style }}>{children}</AbsoluteFill>
  );
};
