/**
 * A page that comes forward, pulls apart into its own visuals, and lets the
 * camera walk among them.
 *
 * This is the treatment the brief asked for, and it is better than panning a
 * flat screenshot because it says something true about the artifact: a report
 * page is not one picture, it is a set of separate visuals that were each
 * decided on. Taking it apart in view is the argument.
 *
 * How it works. One source capture, and a list of rectangles naming the cards
 * inside it. Each card is its own element showing only its own crop of that
 * capture, laid out at exactly its page position, so at rest the set is
 * indistinguishable from the whole page. Then each card is pushed outward
 * along the vector from the page centre, given a little depth and yaw, and the
 * page becomes an exploded view.
 *
 * Focusing is a move of the whole rig, not of one card: the rig translates and
 * scales so the chosen card lands in the middle of the frame at size, which
 * keeps its neighbours drifting at the edges instead of cutting to a crop.
 */
import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { noise2D } from "@remotion/noise";
import { ramp, pop } from "./bits";

/** x, y, w, h in the source capture's own pixels */
export type Piece = { id: string; rect: [number, number, number, number] };

export type ExplodedProps = {
  src: string;
  iw: number;
  ih: number;
  /** the box the assembled page is fitted into */
  bw: number;
  bh: number;
  pieces: Piece[];
  /** the page arrives, tilted, and settles */
  arriveAt?: number;
  /** the cards separate */
  explodeAt?: number;
  explodeDur?: number;
  /** how far the cards travel, as a multiple of their offset from centre */
  spread?: number;
  /** camera stops: hold on a card by id, or null for the whole rig */
  focus?: Array<{ at: number; id: string | null; scale?: number }>;
  seed?: string;
};

export const ExplodedPage: React.FC<ExplodedProps> = ({
  src,
  iw,
  ih,
  bw,
  bh,
  pieces,
  arriveAt = 0,
  explodeAt = 70,
  explodeDur = 46,
  spread = 0.42,
  focus = [],
  seed = "ex",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const S = Math.min(bw / iw, bh / ih);
  const pw = iw * S;
  const ph = ih * S;

  const arrive = pop(frame, fps, arriveAt, { damping: 20, stiffness: 62 });
  const boom = ramp(frame, [explodeAt, explodeAt + explodeDur]);

  /* the rig tilts as it arrives and relaxes as it opens */
  const tiltY = (1 - arrive) * -14 + boom * 2;
  const tiltX = (1 - arrive) * 9 + 3 - boom * 1.5;

  /* where each card ends up once the page is open */
  const placed = pieces.map((p) => {
    const [x, y, w, h] = p.rect;
    const cx = x + w / 2 - iw / 2;
    const cy = y + h / 2 - ih / 2;
    const n = noise2D(seed + p.id, 1, 2);
    return {
      ...p,
      left: x * S,
      top: y * S,
      w: w * S,
      h: h * S,
      // outward from the page centre, plus a little depth and yaw so the set
      // reads as objects in a space rather than tiles on a wall
      dx: cx * S * spread,
      dy: cy * S * spread * 0.72,
      dz: 40 + Math.abs(n) * 130,
      ry: n * 7,
      rx: noise2D(seed + p.id, 3, 4) * 4,
    };
  });

  /* the camera: which card is being held, and how hard */
  let f = focus.length ? focus[0] : { at: 0, id: null as string | null, scale: 1 };
  let g = f;
  for (let i = 0; i < focus.length - 1; i++) {
    if (frame >= focus[i].at) {
      f = focus[i];
      g = focus[i + 1];
    }
  }
  if (focus.length && frame >= focus[focus.length - 1].at) {
    f = focus[focus.length - 1];
    g = f;
  }
  const ft = f === g ? 0 : ramp(frame, [f.at, g.at]);

  const camFor = (id: string | null, wanted?: number) => {
    if (!id) return { x: 0, y: 0, s: 1 };
    const t = placed.find((p) => p.id === id);
    if (!t) return { x: 0, y: 0, s: 1 };
    // the card's centre once the page has opened, in rig coordinates
    const cx = t.left + t.w / 2 + t.dx * boom - pw / 2;
    const cy = t.top + t.h / 2 + t.dy * boom - ph / 2;
    const s = wanted ?? Math.min((bw * 0.88) / t.w, (bh * 0.80) / t.h);
    return { x: -cx * s, y: -cy * s, s };
  };

  const a = camFor(f.id, f.scale);
  const b = camFor(g.id, g.scale);
  const camX = a.x + (b.x - a.x) * ft;
  const camY = a.y + (b.y - a.y) * ft;
  const camS = a.s + (b.s - a.s) * ft;

  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ perspective: 2600, perspectiveOrigin: "50% 45%" }}>
        <div
          style={{
            width: pw,
            height: ph,
            position: "relative",
            transformStyle: "preserve-3d",
            transform: `translate(${camX}px, ${camY}px) scale(${camS}) rotateX(${tiltX}deg) rotateY(${tiltY}deg)`,
            opacity: Math.min(1, arrive * 1.4),
          }}
        >
          {placed.map((p, i) => {
            const lift = pop(frame, fps, explodeAt + i * 2, { damping: 16, stiffness: 70 });
            const e = boom * lift;
            const focused = f.id === p.id || g.id === p.id;
            return (
              <div
                key={p.id}
                style={{
                  position: "absolute",
                  left: p.left,
                  top: p.top,
                  width: p.w,
                  height: p.h,
                  overflow: "hidden",
                  borderRadius: 8 + e * 6,
                  transform: `translate3d(${p.dx * e}px, ${p.dy * e}px, ${p.dz * e}px)
                              rotateY(${p.ry * e}deg) rotateX(${p.rx * e}deg)`,
                  boxShadow: e > 0.02
                    ? `0 ${16 * e}px ${52 * e}px rgba(0,0,0,${0.34 * e})`
                    : "none",
                  outline: focused && e > 0.4 ? "2px solid rgba(143,191,106,.75)" : "none",
                  background: "#fff",
                }}
              >
                <Img
                  src={staticFile(src)}
                  style={{
                    position: "absolute",
                    left: -p.left,
                    top: -p.top,
                    width: pw,
                    height: ph,
                    maxWidth: "none",
                  }}
                />
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
