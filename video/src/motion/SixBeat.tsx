/**
 * The page, in beats. The guide's six, plus v4's theatre move.
 *
 *   01  the finished page arrives, FULL BLEED. both captures are 16:9, so the
 *       page is the frame and there is no dark border around it.
 *   02  the page is cleared and one claim lands on the empty stage
 *   03  the cards come back, one by one
 *   3b  the page comes forward and PULLS APART in 3D  (v4's theatre move)
 *   04  the camera lands on a card, outlined, and returns
 *   05  a sweep travels the page
 *   06  a panel slides in, and the page gives back exactly its width
 *
 * The clear-and-rebuild says which card matters and in what order, because the
 * eye follows what arrives. The pull-apart says the page is a set of separate
 * decisions rather than one picture. Those are different jobs, so v6 keeps
 * both rather than choosing between them.
 *
 * One source capture and a list of rectangles naming the cards inside it. Each
 * card shows only its own crop at its page coordinates, so at rest the set is
 * indistinguishable from the whole page.
 */
import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { noise2D } from "@remotion/noise";
import { D, move, land, stagger, sweep } from "./library";
import { c, font } from "../theme";

/** x, y, w, h in the source capture's own pixels */
export type Card = { id: string; rect: [number, number, number, number] };

export type SixBeatProps = {
  src: string;
  iw: number;
  ih: number;
  bw: number;
  bh: number;
  cards: Card[];
  /** 01 the page arrives */
  at?: number;
  /** 02 the page clears, and the claim that lands on it */
  clearAt: number;
  claim: React.ReactNode;
  claimSub?: React.ReactNode;
  /** 03 the cards come back, in this order. ids not listed return last. */
  rebuildAt: number;
  order?: string[];
  /** 3b the page pulls apart, and closes again at explodeUntil */
  explodeAt?: number;
  explodeUntil?: number;
  spread?: number;
  /** 04 the camera lands on these, in turn */
  holds?: Array<{ at: number; id: string; label?: React.ReactNode }>;
  /** 05 a sweep across the page */
  sweepAt?: number;
  /** 06 a panel slides in from the right */
  panelAt?: number;
  panel?: React.ReactNode;
  /** how wide the panel is, so the page can give back exactly that */
  panelW?: number;
  seed?: string;
};

export const SixBeatPage: React.FC<SixBeatProps> = ({
  src,
  iw,
  ih,
  bw,
  bh,
  cards,
  at = 0,
  clearAt,
  claim,
  claimSub,
  rebuildAt,
  order = [],
  explodeAt,
  explodeUntil,
  spread = 0.4,
  holds = [],
  sweepAt,
  panelAt,
  panel,
  panelW = 470,
  seed = "pg",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const S = Math.min(bw / iw, bh / ih);
  const pw = iw * S;
  const ph = ih * S;

  /* 01 the page arrives whole */
  const arrive = land(frame, fps, at, "lineDraw");

  /* 02 it clears */
  const cleared = move(frame, clearAt, "stripBack");

  /* 03 the cards come back, in the order the argument needs them */
  const rank = (id: string) => {
    const i = order.indexOf(id);
    return i === -1 ? order.length + cards.findIndex((k) => k.id === id) : i;
  };

  /* 3b the pull-apart, opened and closed over the same move */
  const boom =
    explodeAt === undefined
      ? 0
      : move(frame, explodeAt, "lineDraw") *
        (explodeUntil === undefined ? 1 : 1 - move(frame, explodeUntil, "lineDraw"));

  /** where each card sits once the page is open */
  const placed = cards.map((k) => {
    const [x, y, w, h] = k.rect;
    const cx = x + w / 2 - iw / 2;
    const cy = y + h / 2 - ih / 2;
    const n = noise2D(seed + k.id, 1, 2);
    return {
      ...k,
      // outward from the page centre, plus depth and yaw, so the set reads as
      // objects in a room rather than tiles on a wall
      dx: cx * S * spread,
      dy: cy * S * spread * 0.72,
      dz: 40 + Math.abs(n) * 130,
      ry: n * 7,
      rx: noise2D(seed + k.id, 3, 4) * 4,
    };
  });

  /* 04 the camera lands on one card at a time, and RETURNS. A hold needs an
     end as much as a start, or the panel beat plays against a zoomed crop. */
  const HOLD_LEN = D.zoomToKpi + D.highlightSweep;
  const spans = holds.map((h, i) => ({
    ...h,
    until: holds[i + 1] ? holds[i + 1].at : h.at + HOLD_LEN,
  }));
  const active = spans.find((k) => frame >= k.at && frame < k.until) ?? null;
  const prev = [...spans].reverse().find((k) => frame >= k.until) ?? null;

  const HOME = { x: 0, y: 0, s: 1 };
  const camFor = (id: string | null) => {
    if (!id) return HOME;
    const k = placed.find((p) => p.id === id);
    if (!k) return HOME;
    const [x, y, w, h] = k.rect;
    // a hold always moves IN. Fitting a full-width strip to the box width
    // scaled it to 0.83, which is a zoom-to-kpi that zooms out.
    const s = Math.max(1.25, Math.min((bw * 0.66) / (w * S), (bh * 0.66) / (h * S), 1.95));
    const cx = (x + w / 2) * S + k.dx * boom - pw / 2;
    const cy = (y + h / 2) * S + k.dy * boom - ph / 2;
    return { x: -cx * s, y: -cy * s, s };
  };
  const lerp = (u: number, v: number, k: number) => u + (v - u) * k;

  let cam = HOME;
  if (active) {
    const from = prev ? camFor(prev.id) : HOME;
    const to = camFor(active.id);
    const k = move(frame, active.at, "zoomToKpi");
    cam = { x: lerp(from.x, to.x, k), y: lerp(from.y, to.y, k), s: lerp(from.s, to.s, k) };
  } else if (prev) {
    const from = camFor(prev.id);
    const k = move(frame, prev.until, "zoomToKpi");
    cam = { x: lerp(from.x, 0, k), y: lerp(from.y, 0, k), s: lerp(from.s, 1, k) };
  }

  /* 05 the sweep */
  const sw = sweepAt === undefined ? null : sweep(frame, sweepAt, pw);

  /* 06 the panel. The page is full bleed, so it gives back exactly the
     panel's width rather than sliding under it or off the left edge. */
  const pan = panelAt === undefined ? 0 : move(frame, panelAt, "stripBack");
  const panScale = (bw - panelW) / bw;
  const camX = cam.x - pan * (panelW / 2);
  const camY = cam.y;
  // the pull-apart needs room, so the rig backs off while the page is open
  const camS = cam.s * (1 - pan * (1 - panScale)) * (1 - boom * 0.24);

  /* the rig tilts as it opens, which is what makes it read as a room */
  const tiltY = boom * 3;
  const tiltX = boom * 4;

  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
      {/* 02 the claim, on the cleared stage */}
      {cleared > 0.05 ? (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            textAlign: "center",
            padding: "0 180px",
            opacity: cleared * (1 - move(frame, rebuildAt - D.stripBack, "stripBack")),
            transform: `translateY(${(1 - cleared) * 22}px)`,
            zIndex: 2,
          }}
        >
          <div style={{ fontFamily: font.serif, fontSize: 62, color: "#F2F8EC", lineHeight: 1.1 }}>
            {claim}
          </div>
          {claimSub ? (
            <div
              style={{
                fontFamily: font.sans,
                fontSize: 27,
                color: "rgba(238,246,230,.72)",
                marginTop: 20,
                lineHeight: 1.4,
                opacity: move(frame, clearAt + D.cardStagger * 2, "stripBack"),
              }}
            >
              {claimSub}
            </div>
          ) : null}
        </div>
      ) : null}

      <div style={{ perspective: 2600, perspectiveOrigin: "50% 45%" }}>
        <div
          style={{
            width: pw,
            height: ph,
            position: "relative",
            transformStyle: "preserve-3d",
            transform: `translate(${camX}px, ${camY}px) scale(${camS}) rotateX(${tiltX}deg) rotateY(${tiltY}deg)`,
            opacity: Math.min(1, arrive * 1.5),
          }}
        >
          {placed.map((k) => {
            const [x, y, w, h] = k.rect;
            const i = rank(k.id);
            const back = stagger(frame, fps, rebuildAt, i);
            const here = frame < rebuildAt ? 1 - cleared : back;
            if (here <= 0.01) return null;

            const e = boom;
            const focused = active?.id === k.id;
            const lit = sw ? sw.lit((x + w / 2) * S) : 0;

            return (
              <div
                key={k.id}
                style={{
                  position: "absolute",
                  left: x * S,
                  top: y * S,
                  width: w * S,
                  height: h * S,
                  overflow: "hidden",
                  // square at rest, so a full-bleed page has no rounded gap at
                  // the frame edge. rounded only once it is a separate object.
                  borderRadius: e * 10,
                  background: "#fff",
                  opacity: here,
                  transform: `translate3d(${k.dx * e}px, ${k.dy * e + (1 - here) * 34}px, ${k.dz * e}px)
                              rotateY(${k.ry * e}deg) rotateX(${k.rx * e}deg)
                              scale(${0.94 + here * 0.06})`,
                  boxShadow:
                    e > 0.02
                      ? `0 ${16 * e}px ${52 * e}px rgba(0,0,0,${0.34 * e})`
                      : focused
                        ? "0 20px 60px rgba(0,0,0,.45)"
                        : lit > 0.02
                          ? `0 ${8 + lit * 10}px ${24 + lit * 26}px rgba(0,0,0,${0.18 + lit * 0.18})`
                          : "none",
                  outline: focused ? "2px solid rgba(143,191,106,.85)" : "none",
                  filter: lit > 0.02 ? `brightness(${1 + lit * 0.1})` : undefined,
                }}
              >
                <Img
                  src={staticFile(src)}
                  style={{
                    position: "absolute",
                    left: -x * S,
                    top: -y * S,
                    width: pw,
                    height: ph,
                    maxWidth: "none",
                  }}
                />
              </div>
            );
          })}

          {/* 05 the sweep itself, a band rather than a hard line */}
          {sw && sw.running && boom < 0.05 ? (
            <div
              style={{
                position: "absolute",
                left: sw.x - 90,
                top: -14,
                width: 180,
                height: ph + 28,
                background:
                  "linear-gradient(90deg, rgba(143,191,106,0), rgba(143,191,106,.28), rgba(143,191,106,0))",
                pointerEvents: "none",
              }}
            />
          ) : null}
        </div>
      </div>

      {/* 04 what the camera is on */}
      {active?.label ? (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 52,
            display: "flex",
            justifyContent: "center",
            zIndex: 3,
            opacity:
              move(frame, active.at, "zoomToKpi") *
              (1 - move(frame, active.until - D.zoomToKpi, "zoomToKpi")),
          }}
        >
          <div
            style={{
              maxWidth: 1120,
              padding: "20px 38px 22px",
              borderRadius: 16,
              background: "rgba(10,16,9,.92)",
              border: "1px solid rgba(143,191,106,.24)",
              textAlign: "center",
              fontFamily: font.sans,
              fontSize: 26,
              lineHeight: 1.36,
              color: "#F2F8EC",
            }}
          >
            {active.label}
          </div>
        </div>
      ) : null}

      {/* 06 the panel */}
      {pan > 0.01 && panel ? (
        <div
          style={{
            position: "absolute",
            right: 0,
            top: 0,
            bottom: 0,
            width: panelW,
            padding: "52px 42px",
            boxSizing: "border-box",
            background: "rgba(8,13,7,.96)",
            borderLeft: `1px solid ${c.greenLine}33`,
            zIndex: 3,
            transform: `translateX(${(1 - pan) * panelW}px)`,
          }}
        >
          {panel}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
