/**
 * Scene 4. The cluster collapses. 420f / 14s.
 *
 * Eight Spark workers spin up on a ring and shuffle between themselves with
 * the meter pinned at 8. Then they implode into a single node, every shuffle
 * line goes with them, and the meter halves.
 *
 * Then the honest beat: a third configuration bills the same 4, so the saving
 * was never against Spark. It was against the default.
 *
 * On the shared grid, with the ring sized to fill the stage and the meter
 * living beside it rather than floating in the margin.
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { noise2D } from "@remotion/noise";
import { Grain, ramp, pop } from "../motion/bits";
import { SceneFrame, Head, Readout, STAGE_W, STAGE_H } from "../motion/layout";
import { Icon } from "../components/Icon";
import { c, font } from "../theme";

/* the ring occupies the left two thirds of the stage, the meter the right */
const RING_W = STAGE_W * 0.58;
const CX = RING_W / 2;
const CY = STAGE_H / 2 - 10;
const RX = 268;
const RY = 214;
const NODE = 112;

const T_SPAWN = 24;
const T_SHUFFLE = 70;
const T_COLLAPSE = 180;
const T_HONEST = 290;

const SEATS = Array.from({ length: 8 }).map((_, i) => {
  const a = (i / 8) * Math.PI * 2 - Math.PI / 2;
  return { x: CX + Math.cos(a) * RX - NODE / 2, y: CY + Math.sin(a) * RY - NODE / 2, i };
});

export const S4Cluster: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const collapse = ramp(frame, [T_COLLAPSE, T_COLLAPSE + 44]);
  const shuffle = ramp(frame, [T_SHUFFLE, T_SHUFFLE + 20]) * (1 - collapse);
  const cu = 8 - collapse * 4;
  const cx = CX - NODE / 2;
  const cy = CY - NODE / 2;

  return (
    <AbsoluteFill style={{ background: c.paper, overflow: "hidden" }}>
      <Grain opacity={0.18} />

      <SceneFrame
        head={
          <Head at={4} kicker="the job fits on one machine, so it gets one machine">
            One node.{" "}
            <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", color: c.greenInk }}>
              No cluster.
            </span>
          </Head>
        }
        stage={
          <div style={{ position: "relative", width: STAGE_W, height: STAGE_H }}>
            {/* the shuffle */}
            <svg
              style={{ position: "absolute", left: 0, top: 0, width: RING_W, height: STAGE_H }}
              width={RING_W}
              height={STAGE_H}
            >
              {SEATS.map((a, i) =>
                SEATS.slice(i + 1).map((b, j) => {
                  const pulse = (Math.sin((frame + (i * 8 + j) * 9) / 11) + 1) / 2;
                  return (
                    <line
                      key={`${i}-${j}`}
                      x1={a.x + NODE / 2 - collapse * (a.x - cx)}
                      y1={a.y + NODE / 2 - collapse * (a.y - cy)}
                      x2={b.x + NODE / 2 - collapse * (b.x - cx)}
                      y2={b.y + NODE / 2 - collapse * (b.y - cy)}
                      stroke={c.amber}
                      strokeWidth={1.3}
                      opacity={shuffle * (0.1 + pulse * 0.32)}
                    />
                  );
                }),
              )}
            </svg>

            {/* the shape the cluster is heading for, ghosted in the centre
                from the start, so the middle of the ring is never a hole */}
            <div
              style={{
                position: "absolute",
                left: cx - 26,
                top: cy - 26,
                width: NODE + 52,
                height: NODE + 52,
                borderRadius: 24,
                border: `2px dashed ${c.border}`,
                opacity: (1 - collapse) * ramp(frame, [T_SHUFFLE, T_SHUFFLE + 24]) * 0.9,
              }}
            />
            <div
              style={{
                position: "absolute",
                left: cx - 90,
                top: cy + NODE + 40,
                width: NODE + 180,
                textAlign: "center",
                fontFamily: font.mono,
                fontSize: 12,
                letterSpacing: 1.6,
                textTransform: "uppercase",
                color: c.faint,
                opacity: (1 - collapse) * ramp(frame, [T_SHUFFLE + 12, T_SHUFFLE + 36]),
              }}
            >
              what this becomes
            </div>

            {SEATS.map((s) => {
              const p = pop(frame, fps, T_SPAWN + s.i * 4);
              const x = s.x - collapse * (s.x - cx);
              const y = s.y - collapse * (s.y - cy);
              const fade = s.i === 0 ? 1 : 1 - collapse;
              const jit = shuffle * noise2D("jit", s.i, frame * 0.05) * 3;
              const isOne = s.i === 0 && collapse > 0.5;
              return (
                <div
                  key={s.i}
                  style={{
                    position: "absolute",
                    left: x + jit,
                    top: y + jit,
                    width: NODE,
                    height: NODE,
                    borderRadius: 18,
                    background: isOne ? c.greenBg : c.white,
                    border: `1.5px solid ${isOne ? c.greenLine : c.border}`,
                    display: "grid",
                    placeItems: "center",
                    opacity: p * fade,
                    transform: `scale(${(0.9 + p * 0.1) * (1 + collapse * (s.i === 0 ? 1.85 : 0))})`,
                    boxShadow: "0 6px 20px rgba(22,29,17,.11)",
                    zIndex: s.i === 0 ? 3 : 1,
                  }}
                >
                  <Icon name={isOne ? "duckdb" : "spark"} size={isOne ? 64 : 40} />
                </div>
              );
            })}

            {/* what the one node is actually running, filling the space the
                ring used to occupy */}
            <div
              style={{
                position: "absolute",
                left: 0,
                top: CY + 156,
                width: RING_W,
                display: "flex",
                justifyContent: "center",
                gap: 48,
                opacity: collapse * ramp(frame, [T_COLLAPSE + 40, T_COLLAPSE + 66]),
              }}
            >
              {([
                ["DuckDB 1.2.2", "engine"],
                ["12.8 min", "of work"],
                ["no shuffle", "nothing to move"],
              ]).map(([v, l]) => (
                <div key={v} style={{ textAlign: "center" }}>
                  <div style={{ fontFamily: font.mono, fontWeight: 700, fontSize: 30, color: c.greenInk }}>
                    {v}
                  </div>
                  <div
                    style={{
                      fontFamily: font.mono,
                      fontSize: 12,
                      letterSpacing: 1.6,
                      textTransform: "uppercase",
                      color: c.muted,
                      marginTop: 8,
                    }}
                  >
                    {l}
                  </div>
                </div>
              ))}
            </div>

            <div
              style={{
                position: "absolute",
                left: 0,
                top: STAGE_H - 44,
                width: RING_W,
                textAlign: "center",
              }}
            >
              <span
                style={{
                  fontFamily: font.sans,
                  fontSize: 27,
                  fontWeight: 700,
                  color: collapse > 0.5 ? c.greenInk : c.ink,
                  opacity: ramp(frame, [T_SHUFFLE, T_SHUFFLE + 20]),
                }}
              >
                {collapse > 0.5 ? "Python notebook, 8 vCores" : "Spark starter pool"}
              </span>
              <span
                style={{
                  fontFamily: font.mono,
                  fontSize: 15,
                  color: c.muted,
                  marginLeft: 16,
                  opacity: ramp(frame, [T_SHUFFLE + 10, T_SHUFFLE + 30]),
                }}
              >
                {collapse > 0.5 ? "no shuffle, no cluster start" : "eight workers, and a shuffle"}
              </span>
            </div>

            {/* the meter, inside the stage */}
            <div style={{ position: "absolute", left: RING_W + 60, top: 26, width: STAGE_W - RING_W - 60 }}>
              <div
                style={{
                  fontFamily: font.mono,
                  fontSize: 13,
                  letterSpacing: 2.2,
                  textTransform: "uppercase",
                  color: c.muted,
                  opacity: ramp(frame, [T_SHUFFLE, T_SHUFFLE + 18]),
                }}
              >
                capacity units, while running
              </div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginTop: 14 }}>
                <span
                  style={{
                    fontFamily: font.mono,
                    fontWeight: 700,
                    fontSize: 138,
                    color: collapse > 0.5 ? c.greenInk : c.amberInk,
                    fontVariantNumeric: "tabular-nums",
                    opacity: ramp(frame, [T_SHUFFLE, T_SHUFFLE + 18]),
                    lineHeight: 1,
                  }}
                >
                  {cu.toFixed(0)}
                </span>
                <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", fontSize: 46, color: c.ink }}>
                  CU
                </span>
              </div>

              <div style={{ display: "flex", gap: 7, marginTop: 26 }}>
                {Array.from({ length: 8 }).map((_, i) => (
                  <div
                    key={i}
                    style={{
                      flex: 1,
                      height: 34,
                      borderRadius: 5,
                      background: i < cu ? (collapse > 0.5 ? c.green : c.amber) : c.rail,
                      border: `1px solid ${i < cu ? "transparent" : c.divider}`,
                      opacity: ramp(frame, [T_SHUFFLE, T_SHUFFLE + 18]),
                    }}
                  />
                ))}
              </div>

              <div
                style={{
                  marginTop: 46,
                  padding: "22px 24px",
                  borderRadius: 16,
                  background: c.amberBg,
                  border: `1px solid ${c.amberLine}`,
                  opacity: ramp(frame, [T_HONEST, T_HONEST + 26]),
                  transform: `translateY(${ramp(frame, [T_HONEST, T_HONEST + 30], [18, 0])}px)`,
                }}
              >
                <div
                  style={{
                    fontFamily: font.mono,
                    fontSize: 12,
                    letterSpacing: 1.8,
                    textTransform: "uppercase",
                    color: c.amberInk,
                    marginBottom: 10,
                  }}
                >
                  and the row most comparisons skip
                </div>
                <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
                  <span
                    style={{
                      fontFamily: font.mono,
                      fontWeight: 700,
                      fontSize: 48,
                      color: c.amberInk,
                    }}
                  >
                    4
                  </span>
                  <span style={{ fontFamily: font.sans, fontSize: 20, color: c.body, lineHeight: 1.35 }}>
                    CU for a single-node Spark session, if you configure one
                  </span>
                </div>
              </div>
            </div>
          </div>
        }
        foot={
          <Readout
            at={T_SHUFFLE + 24}
            stats={[
              { v: "8 vCores", l: "the size this job was given", at: T_SHUFFLE + 24 },
              { v: "67.4 GB", l: "ram on the node", at: T_SHUFFLE + 32 },
              { v: "47 GB", l: "duckdb memory cap", at: T_SHUFFLE + 40 },
              { v: "10.5 GB", l: "compressed source", tone: "green", at: T_SHUFFLE + 48 },
            ]}
            note={<>So the saving is against the default, not against Spark.</>}
          />
        }
      />
    </AbsoluteFill>
  );
};
