/**
 * Scene 7. What a threshold costs, in people. 450f / 15s.
 *
 * The payoff, and the one beat that must not be a table. A score histogram is
 * drawn, a threshold line slides across it, and as it moves the alert count
 * falls and analysts physically disappear from a row.
 *
 * On the shared grid: the chart and the analyst row together fill the stage,
 * and the read-out is live in the foot from the moment the line starts moving.
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { Grain, ramp, pop } from "../motion/bits";
import { SceneFrame, Head, Readout, STAGE_W, STAGE_H } from "../motion/layout";
import { c, font } from "../theme";

const BARS = 34;
const CHART_W = STAGE_W - 440;
const CHART_H = 350;
const CHART_TOP = 44;
const ANALYST_TOP = CHART_TOP + CHART_H + 110;

const STOPS = [
  { cut: 40, alerts: "7.1m", analysts: 57, rate: "14.38%" },
  { cut: 50, alerts: "3.6m", analysts: 29, rate: "7.22%" },
  { cut: 60, alerts: "1.4m", analysts: 11, rate: "2.88%" },
  { cut: 70, alerts: "450k", analysts: 4, rate: "0.91%" },
  { cut: 80, alerts: "184k", analysts: 1, rate: "0.37%" },
];

const T_CHART = 16;
const T_SLIDE = 96;
const SLIDE_DUR = 240;

const HEIGHTS = Array.from({ length: BARS }).map((_, i) => {
  const x = i / (BARS - 1);
  const v = Math.exp(-Math.pow((x - 0.13) / 0.16, 2)) + 0.32 * Math.exp(-Math.pow((x - 0.4) / 0.2, 2));
  return Math.max(0.03, v);
});
const MAXH = Math.max(...HEIGHTS);

export const S7Threshold: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const t = ramp(frame, [T_SLIDE, T_SLIDE + SLIDE_DUR]);
  const idx = Math.min(STOPS.length - 1, Math.round(t * (STOPS.length - 1)));
  const stop = STOPS[idx];
  const cutX = (stop.cut / 145) * CHART_W;

  return (
    <AbsoluteFill style={{ background: c.paper, overflow: "hidden" }}>
      <Grain opacity={0.16} />

      <SceneFrame
        head={
          <Head at={4} kicker="scores run 0 to 145. the band is where you put it.">
            Move the cut-off, and the{" "}
            <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", color: c.greenInk }}>
              headcount moves with it.
            </span>
          </Head>
        }
        stage={
          <div style={{ position: "relative", width: STAGE_W, height: STAGE_H }}>
            {/* the histogram */}
            <div style={{ position: "absolute", left: 0, top: CHART_TOP, width: CHART_W, height: CHART_H }}>
              {HEIGHTS.map((h, i) => {
                const p = pop(frame, fps, T_CHART + i * 2);
                const bw = CHART_W / BARS;
                const above = (i / (BARS - 1)) * 145 >= stop.cut;
                return (
                  <div
                    key={i}
                    style={{
                      position: "absolute",
                      left: i * bw + 2,
                      bottom: 0,
                      width: bw - 4,
                      height: (h / MAXH) * CHART_H * p,
                      borderRadius: "5px 5px 0 0",
                      background: above ? c.red : c.green,
                      opacity: above ? 0.78 : 0.34,
                    }}
                  />
                );
              })}

              <div style={{ position: "absolute", left: 0, bottom: -1, width: CHART_W, height: 1, background: c.border }} />
              {[0, 40, 80, 120, 145].map((s) => (
                <div
                  key={s}
                  style={{
                    position: "absolute",
                    left: (s / 145) * CHART_W - 22,
                    bottom: -32,
                    width: 44,
                    textAlign: "center",
                    fontFamily: font.mono,
                    fontSize: 13,
                    color: c.faint,
                    opacity: ramp(frame, [T_CHART + 20, T_CHART + 40]),
                  }}
                >
                  {s}
                </div>
              ))}

              <div
                style={{
                  position: "absolute",
                  left: cutX - 2.5,
                  bottom: -16,
                  width: 5,
                  height: CHART_H + 62,
                  background: c.red,
                  opacity: ramp(frame, [T_SLIDE - 24, T_SLIDE - 6]),
                  boxShadow: `0 0 18px ${c.red}88`,
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: cutX - 70,
                  top: -74,
                  width: 140,
                  textAlign: "center",
                  opacity: ramp(frame, [T_SLIDE - 24, T_SLIDE - 6]),
                }}
              >
                <div
                  style={{
                    fontFamily: font.mono,
                    fontWeight: 700,
                    fontSize: 46,
                    color: c.redInk,
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {stop.cut}
                </div>
                <div
                  style={{
                    fontFamily: font.mono,
                    fontSize: 11,
                    letterSpacing: 1.8,
                    textTransform: "uppercase",
                    color: c.muted,
                  }}
                >
                  cut-off
                </div>
              </div>
            </div>

            {/* the people, who leave as the line rises */}
            <div style={{ position: "absolute", left: 0, top: ANALYST_TOP, width: CHART_W }}>
              <div
                style={{
                  fontFamily: font.mono,
                  fontSize: 13,
                  letterSpacing: 2,
                  textTransform: "uppercase",
                  color: c.faint,
                  marginBottom: 16,
                }}
              >
                analysts needed, at 50,000 alerts cleared each a year
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", width: CHART_W }}>
                {Array.from({ length: 57 }).map((_, i) => {
                  const on = i < stop.analysts;
                  return (
                    <div
                      key={i}
                      style={{
                        width: 17,
                        height: 30,
                        borderRadius: "8px 8px 3px 3px",
                        background: on ? c.greenInk : c.rail,
                        border: `1px solid ${on ? "transparent" : c.divider}`,
                        opacity: on ? 1 : 0.5,
                        transform: `scaleY(${on ? 1 : 0.66})`,
                        transformOrigin: "bottom",
                      }}
                    />
                  );
                })}
              </div>
            </div>

            {/* the read-out, inside the stage beside the chart */}
            <div style={{ position: "absolute", right: 0, top: 40, width: 380, textAlign: "right" }}>
              {([
                ["alerts raised", stop.alerts, c.ink, 52],
                ["share of transactions", stop.rate, c.ink, 52],
                ["analysts", String(stop.analysts), c.greenInk, 96],
              ] as Array<[string, string, string, number]>).map(([l, v, col, size], i) => (
                <div
                  key={l}
                  style={{ marginBottom: 40, opacity: ramp(frame, [T_SLIDE - 22 + i * 8, T_SLIDE + i * 8]) }}
                >
                  <div
                    style={{
                      fontFamily: font.mono,
                      fontSize: 13,
                      letterSpacing: 1.8,
                      textTransform: "uppercase",
                      color: c.muted,
                      marginBottom: 8,
                    }}
                  >
                    {l}
                  </div>
                  <div
                    style={{
                      fontFamily: font.mono,
                      fontWeight: 700,
                      fontSize: size,
                      color: col,
                      fontVariantNumeric: "tabular-nums",
                      lineHeight: 1,
                    }}
                  >
                    {v}
                  </div>
                </div>
              ))}
            </div>
          </div>
        }
        foot={
          <Readout
            at={T_SLIDE}
            stats={[
              { v: "65,175,479", l: "rule firings", at: T_SLIDE },
              { v: "1,423,088", l: "alerts at the current band", at: T_SLIDE + 8 },
              { v: "45.8", l: "firings per alert", at: T_SLIDE + 16, small: true },
            ]}
            note={<>A queue of 317 analyst-loads is ignored. A queue of 11 is worked.</>}
          />
        }
      />
    </AbsoluteFill>
  );
};
