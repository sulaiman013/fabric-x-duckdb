/**
 * The theatre: a dark room with one lit surface in it.
 *
 * The two real artifacts of this project, the architecture page and the Power
 * BI report, were never in the film. They should not be dropped into the same
 * pale layout as everything else either, because that flattens them into more
 * diagram. They get a room: the paper recedes to a deep ink wash, a single
 * screen is lit and raised on a shadow, and the camera moves over it.
 *
 * The camera is the point. Showing a whole page tells you it exists. Pushing
 * into one card of it, slowly, and holding while a caption names what you are
 * looking at, is what makes a viewer actually read it.
 */
import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { c, font } from "../theme";
import { ramp, pop } from "./bits";

/** a rectangle in the source image's own pixels */
export type Rect = [number, number, number, number];

/** the lit screen the artifact is projected onto */
export const Stage: React.FC<{
  w: number;
  h: number;
  at?: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({ w, h, at = 0, children, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = pop(frame, fps, at, { damping: 18, stiffness: 80 });
  return (
    <div
      style={{
        width: w,
        height: h,
        position: "relative",
        overflow: "hidden",
        borderRadius: 10,
        background: "#0E1410",
        opacity: p,
        transform: `scale(${0.965 + p * 0.035})`,
        boxShadow:
          "0 0 0 1px rgba(182,227,166,.18), 0 40px 90px rgba(0,0,0,.55), 0 0 160px rgba(120,190,90,.13)",
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/** the room around the screen */
export const Room: React.FC<{ children: React.ReactNode; at?: number }> = ({ children, at = 0 }) => {
  const frame = useCurrentFrame();
  const dim = ramp(frame, [at, at + 22]);
  return (
    <AbsoluteFill style={{ background: c.paper }}>
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(130% 100% at 50% 34%, #24301F 0%, #161D14 55%, #0C110A 100%)",
          opacity: dim,
        }}
      />
      {children}
    </AbsoluteFill>
  );
};

/** fit a source rect into a box, returning the transform that shows it */
const fit = (r: Rect, bw: number, bh: number, iw: number, ih: number) => {
  const [x, y, w, h] = r;
  const s = Math.min(bw / w, bh / h);
  return { s, left: bw / 2 - (x + w / 2) * s, top: bh / 2 - (y + h / 2) * s, iw, ih };
};

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

/**
 * A camera move across one image: from one rectangle of it to another, eased.
 *
 * This is how a page becomes readable. The whole page establishes it, then the
 * camera travels into a single card and holds there.
 */
export const PanZoom: React.FC<{
  src: string;
  iw: number;
  ih: number;
  bw: number;
  bh: number;
  /** [frame, rect] stops. The camera eases from each to the next. */
  stops: Array<{ at: number; rect: Rect }>;
}> = ({ src, iw, ih, bw, bh, stops }) => {
  const frame = useCurrentFrame();

  let from = stops[0];
  let to = stops[0];
  for (let i = 0; i < stops.length - 1; i++) {
    if (frame >= stops[i].at) {
      from = stops[i];
      to = stops[i + 1];
    }
  }
  const t = from === to ? 0 : ramp(frame, [from.at, to.at]);

  const a = fit(from.rect, bw, bh, iw, ih);
  const b = fit(to.rect, bw, bh, iw, ih);
  const s = lerp(a.s, b.s, t);
  const left = lerp(a.left, b.left, t);
  const top = lerp(a.top, b.top, t);

  return (
    <Img
      src={staticFile(src)}
      style={{
        position: "absolute",
        width: iw * s,
        height: ih * s,
        left,
        top,
        maxWidth: "none",
      }}
    />
  );
};

/**
 * The caption, as a centred pill.
 *
 * An exploded page puts cards in every corner, so a caption pinned to one of
 * them lands on top of content. A single floating pill at the bottom centre
 * reads as a title card and never collides with anything.
 */
export const Marquee: React.FC<{
  at: number;
  until?: number;
  kicker?: string;
  title: string;
  body?: string;
  side?: "left" | "right";
}> = ({ at, until, kicker, title, body }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = pop(frame, fps, at, { damping: 17, stiffness: 90 });
  const out = until === undefined ? 1 : 1 - ramp(frame, [until - 12, until]);
  const o = Math.min(1, p * 1.25) * out;
  if (o <= 0.01) return null;
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 54,
        display: "flex",
        justifyContent: "center",
        pointerEvents: "none",
        opacity: o,
      }}
    >
      <div
        style={{
          maxWidth: 1180,
          padding: "22px 40px 24px",
          borderRadius: 18,
          background: "rgba(10,16,9,.90)",
          border: "1px solid rgba(143,191,106,.22)",
          boxShadow: "0 22px 60px rgba(0,0,0,.5)",
          textAlign: "center",
          transform: `translateY(${(1 - p) * 26}px) scale(${0.96 + p * 0.04})`,
        }}
      >
        {kicker ? (
          <div
            style={{
              fontFamily: font.mono,
              fontSize: 12,
              letterSpacing: 2.8,
              textTransform: "uppercase",
              color: "#8FBF6A",
              marginBottom: 10,
            }}
          >
            {kicker}
          </div>
        ) : null}
        <div style={{ fontFamily: font.serif, fontSize: 36, color: "#F2F8EC", lineHeight: 1.14 }}>
          {title}
        </div>
        {body ? (
          <div
            style={{
              fontFamily: font.sans,
              fontSize: 20,
              color: "rgba(238,246,230,.74)",
              marginTop: 11,
              lineHeight: 1.45,
            }}
          >
            {body}
          </div>
        ) : null}
      </div>
    </div>
  );
};
