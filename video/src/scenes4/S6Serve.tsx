/**
 * Scene 6. Import clones, Direct Lake points. 420f / 14s.
 *
 * Two stacks of plates. On the Import side a third plate is cloned out of the
 * second, goes stale, and is rebuilt, on a loop, because that is the cost that
 * never stops. On the Direct Lake side nothing is cloned: a metadata token
 * runs up the outside to the model and the plates stay put.
 *
 * Laid out on the shared grid, with the plates sized to fill the stage rather
 * than huddling in its top third.
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { Wire, curve } from "../motion/Wire";
import { Grain, Slab, ramp, pop } from "../motion/bits";
import { SceneFrame, Head, Readout, STAGE_W, STAGE_H } from "../motion/layout";
import { Icon } from "../components/Icon";
import { c, font } from "../theme";

const T_IMPORT = 24;
const T_DL = 120;
const T_QUERY = 236;

const COL_W = 560;
const LX = 40;
const RX = STAGE_W - COL_W - 40;
const PLATE_H = 84;
const STEP = 106;
const TOP = 150;

const Plate: React.FC<{
  x: number;
  y: number;
  at: number;
  label: string;
  tone?: "white" | "amber" | "green";
}> = ({ x, y, at, label, tone = "white" }) => (
  <Slab x={x} y={y} w={COL_W} h={PLATE_H} at={at} tone={tone}>
    <div
      style={{
        display: "flex",
        alignItems: "center",
        height: "100%",
        padding: "0 24px",
        fontFamily: font.mono,
        fontSize: 19,
        color: tone === "amber" ? c.amberInk : tone === "green" ? c.greenInk : c.body,
      }}
    >
      {label}
    </div>
  </Slab>
);

export const S6Serve: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  /* build, go stale, rebuild. it never stops. */
  const cycle = 90;
  const ct = Math.max(0, frame - (T_IMPORT + 40));
  const phase = (ct % cycle) / cycle;
  const build = Math.min(1, phase / 0.3);
  const stale = Math.max(0, (phase - 0.45) / 0.45);

  const q1 = ramp(frame, [T_QUERY, T_QUERY + 54]);
  const q2 = ramp(frame, [T_QUERY + 84, T_QUERY + 100]);

  const metaPath = curve(RX + COL_W + 34, TOP - 64, RX + COL_W + 34, TOP + STEP + PLATE_H / 2, 140);

  return (
    <AbsoluteFill style={{ background: c.paper, overflow: "hidden" }}>
      <Grain opacity={0.18} />

      <SceneFrame
        head={
          <Head at={4} kicker="a gold layer is materialised either way">
            The copy worth arguing about is{" "}
            <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", color: c.greenInk }}>
              the third one.
            </span>
          </Head>
        }
        stage={
          <div style={{ position: "relative", width: STAGE_W, height: STAGE_H }}>
            {/* column headings */}
            {([
              [LX, "import", c.amberInk, T_IMPORT],
              [RX, "direct lake", c.greenInk, T_DL],
            ] as Array<[number, string, string, number]>).map(([x, label, col, at]) => (
              <div
                key={label}
                style={{
                  position: "absolute",
                  left: x,
                  top: TOP - 52,
                  fontFamily: font.mono,
                  fontSize: 14,
                  letterSpacing: 2.4,
                  textTransform: "uppercase",
                  color: col,
                  opacity: pop(frame, fps, at),
                }}
              >
                {label}
              </div>
            ))}

            <Plate x={LX} y={TOP} at={T_IMPORT + 4} label="1   mirrored raw Delta" />
            <Plate x={LX} y={TOP + STEP} at={T_IMPORT + 14} label="2   gold Delta" />

            {/* the third plate, cloned out of the second, over and over */}
            <div
              style={{
                position: "absolute",
                left: LX,
                top: TOP + STEP * 2,
                opacity: frame > T_IMPORT + 40 ? 1 : 0,
                transform: `translateY(${(1 - build) * -STEP}px) scale(${0.9 + build * 0.1})`,
              }}
            >
              <div
                style={{
                  width: COL_W,
                  height: PLATE_H,
                  borderRadius: 14,
                  background: c.amberBg,
                  border: `1px solid ${c.amberLine}`,
                  display: "flex",
                  alignItems: "center",
                  padding: "0 24px",
                  fontFamily: font.mono,
                  fontSize: 19,
                  color: c.amberInk,
                  opacity: build * (1 - stale * 0.55),
                  filter: `grayscale(${stale})`,
                  boxShadow: "0 8px 22px rgba(22,29,17,.11)",
                }}
              >
                3&nbsp;&nbsp;&nbsp;a cached copy in the model
              </div>
            </div>

            <div
              style={{
                position: "absolute",
                left: LX,
                top: TOP + STEP * 2 + PLATE_H + 26,
                width: COL_W,
                textAlign: "center",
                fontFamily: font.mono,
                fontSize: 15,
                color: stale > 0.5 ? c.redInk : c.amberInk,
                opacity: ramp(frame, [T_IMPORT + 56, T_IMPORT + 80]),
              }}
            >
              {stale > 0.5 ? "stale. rebuild it, and pay again." : "refreshing on a schedule"}
            </div>

            <Plate x={RX} y={TOP} at={T_DL + 4} label="1   mirrored raw Delta" />
            <Plate x={RX} y={TOP + STEP} at={T_DL + 14} label="2   gold Delta, read in place" tone="green" />

            <Wire
              d={metaPath}
              drawAt={T_DL + 28}
              drawDur={20}
              color={c.greenLine}
              width={2}
              packets={1}
              packetAt={T_DL + 34}
              travel={66}
              packetSize={20}
            />

            <div
              style={{
                position: "absolute",
                left: RX,
                top: TOP + STEP * 2 + PLATE_H + 26,
                width: COL_W,
                textAlign: "center",
                fontFamily: font.mono,
                fontSize: 15,
                color: c.greenInk,
                opacity: ramp(frame, [T_DL + 44, T_DL + 68]),
              }}
            >
              a refresh copies metadata, not data
            </div>

            {/* the model the metadata goes to */}
            <div
              style={{
                position: "absolute",
                left: RX + COL_W - 16,
                top: TOP - 148,
                opacity: pop(frame, fps, T_DL + 18),
              }}
            >
              <div
                style={{
                  width: 100,
                  height: 76,
                  borderRadius: 14,
                  background: c.white,
                  border: `1px solid ${c.border}`,
                  display: "grid",
                  placeItems: "center",
                  boxShadow: "0 6px 18px rgba(22,29,17,.09)",
                }}
              >
                <Icon name="semantic" size={38} />
              </div>
            </div>

            {/* the count of persisted copies, under each column */}
            {([
              [LX, 3, c.amberInk, T_IMPORT + 70],
              [RX, 2, c.greenInk, T_DL + 60],
            ] as Array<[number, number, string, number]>).map(([x, n, col, at]) => (
              <div
                key={x}
                style={{
                  position: "absolute",
                  left: x,
                  top: TOP + STEP * 2 + PLATE_H + 62,
                  width: COL_W,
                  textAlign: "center",
                  opacity: ramp(frame, [at, at + 24]),
                }}
              >
                <span
                  style={{
                    fontFamily: font.mono,
                    fontWeight: 700,
                    fontSize: 46,
                    color: col,
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {n}
                </span>
                <span style={{ fontFamily: font.sans, fontSize: 19, color: c.muted, marginLeft: 12 }}>
                  copies persisted
                </span>
              </div>
            ))}
          </div>
        }
        foot={
          <Readout
            at={T_QUERY - 60}
            stats={[
              {
                v: (q1 * 11.18).toFixed(2) + " s",
                l: "first query, transcoding the fact",
                tone: "amber",
                at: T_QUERY - 60,
              },
              {
                v: (q2 * 1.59).toFixed(2) + " s",
                l: "the same query, warm",
                tone: "green",
                at: T_QUERY - 50,
              },
              { v: "49,406,792", l: "rows behind both", at: T_QUERY - 40, small: true },
            ]}
            note={<>Nothing is imported, so nothing goes stale between refreshes.</>}
          />
        }
      />
    </AbsoluteFill>
  );
};
