/**
 * Scene 8. Proof, then the signature. 390f / 13s.
 *
 * Thirty-seven checks fly in and stamp. Then the signature.
 *
 * The handover between the two is a MOVE, not a cross-fade. The first cut
 * faded one out while fading the other in, and the space audit caught the
 * result: at the midpoint both were near invisible and the frame measured 0%
 * coverage. Now the chips slide up and out while the signature slides in from
 * below, so something solid is always on screen.
 */
import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { noise2D } from "@remotion/noise";
import { Grain, ramp, pop, bounce } from "../motion/bits";
import { SceneFrame, Head, Readout, STAGE_W, STAGE_H } from "../motion/layout";
import { Icon, IconKey } from "../components/Icon";
import { c, font } from "../theme";

const TOTAL_CHECKS = 37;
const SKIPPED_INDEX = 12;
const T_CHIPS = 14;
const CHIP_EVERY = 4;
const T_SIGN = 196;
const SWAP = 22;

const STACK: Array<[IconKey, string]> = [
  ["postgres", "PostgreSQL"],
  ["fabric", "Fabric"],
  ["duckdb", "DuckDB"],
  ["spark", "Spark"],
  ["semantic", "Direct Lake"],
  ["powerbi", "Power BI"],
];

export const S8Close: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const landed = Math.max(0, Math.min(TOTAL_CHECKS, Math.floor((frame - T_CHIPS) / CHIP_EVERY) + 1));
  const passed = Math.max(0, landed - (landed > SKIPPED_INDEX ? 1 : 0));

  /* the swap is a slide, so the stage is never empty */
  const swap = ramp(frame, [T_SIGN, T_SIGN + SWAP]);

  return (
    <AbsoluteFill style={{ background: c.paper, overflow: "hidden" }}>
      <Grain opacity={0.16} />

      <SceneFrame
        head={
          <Head at={4} kicker="re-measured on every run, and allowed to fail">
            {swap < 0.5 ? (
              <>
                Nothing here is asserted.{" "}
                <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", color: c.greenInk }}>
                  All of it is measured.
                </span>
              </>
            ) : (
              <>
                Fifty million rows,{" "}
                <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", color: c.greenInk }}>
                  for twenty-seven cents.
                </span>
              </>
            )}
          </Head>
        }
        stage={
          <div style={{ position: "relative", width: STAGE_W, height: STAGE_H, overflow: "hidden" }}>
            {/* the checks, which slide up and out */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                transform: `translateY(${-swap * (STAGE_H + 40)}px)`,
              }}
            >
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 22,
                  width: 1150,
                  alignContent: "flex-start",
                }}
              >
                {Array.from({ length: TOTAL_CHECKS }).map((_, i) => {
                  const on = i < landed;
                  const s = on ? bounce(frame, fps, T_CHIPS + i * CHIP_EVERY) : 0;
                  const skip = i === SKIPPED_INDEX;
                  return (
                    <div
                      key={i}
                      style={{
                        width: 96,
                        height: 96,
                        borderRadius: 16,
                        background: skip ? c.amberBg : c.greenBg,
                        border: `1.5px solid ${skip ? c.amberLine : c.greenLine}`,
                        display: "grid",
                        placeItems: "center",
                        fontFamily: font.mono,
                        fontSize: 38,
                        fontWeight: 700,
                        color: skip ? c.amberInk : c.greenInk,
                        opacity: s,
                        transform: `scale(${0.6 + s * 0.4}) rotate(${(1 - s) * noise2D("chip", i, 0) * 26}deg)`,
                      }}
                    >
                      {skip ? "~" : "✓"}
                    </div>
                  );
                })}
              </div>

              <div style={{ position: "absolute", right: 0, top: 4, textAlign: "right", width: 470 }}>
                <div style={{ display: "flex", alignItems: "baseline", gap: 14, justifyContent: "flex-end" }}>
                  <span
                    style={{
                      fontFamily: font.mono,
                      fontWeight: 700,
                      fontSize: 150,
                      color: c.greenInk,
                      fontVariantNumeric: "tabular-nums",
                      lineHeight: 1,
                    }}
                  >
                    {passed}
                  </span>
                  <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", fontSize: 58, color: c.ink }}>
                    / 36
                  </span>
                </div>
                <div
                  style={{
                    fontFamily: font.mono,
                    fontSize: 14,
                    letterSpacing: 1.8,
                    textTransform: "uppercase",
                    color: c.muted,
                    marginTop: 14,
                  }}
                >
                  acceptance checks pass, 1 skipped
                </div>
                <div
                  style={{
                    fontFamily: font.sans,
                    fontSize: 21,
                    color: c.body,
                    marginTop: 34,
                    lineHeight: 1.5,
                    opacity: ramp(frame, [140, 168]),
                  }}
                >
                  It pushes a real UPDATE through the write-ahead log and reads
                  it back out of OneLake by value. It has failed before, and
                  caught a README that told the reader to build a broken mirror.
                </div>
              </div>
            </div>

            {/* the signature, which slides in from below */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                transform: `translateY(${(1 - swap) * (STAGE_H + 40)}px)`,
                display: "flex",
                alignItems: "center",
                gap: 52,
              }}
            >
              <div
                style={{
                  width: 330,
                  height: 414,
                  borderRadius: 22,
                  overflow: "hidden",
                  border: `1px solid ${c.border}`,
                  flex: "0 0 auto",
                  boxShadow: "0 2px 6px rgba(22,29,17,.06), 0 24px 52px rgba(22,29,17,.13)",
                }}
              >
                <Img
                  src={staticFile("me/sulaiman-portrait.jpeg")}
                  style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                />
              </div>

              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: font.serif, fontSize: 90, color: c.ink, lineHeight: 1 }}>
                  Sulaiman Ahmed<span style={{ color: c.green }}>.</span>
                </div>
                <div style={{ fontFamily: font.sans, fontSize: 30, color: c.muted, marginTop: 20 }}>
                  Analytics Engineer &middot; Microsoft Fabric, Power BI, DuckDB
                </div>

                <div style={{ display: "flex", gap: 34, marginTop: 42, flexWrap: "wrap" }}>
                  {STACK.map(([k, label], i) => {
                    const p = pop(frame, fps, T_SIGN + 16 + i * 5);
                    return (
                      <div
                        key={k}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 10,
                          opacity: p,
                          transform: `translateY(${(1 - p) * 12}px)`,
                        }}
                      >
                        <Icon name={k} size={34} />
                        <span style={{ fontFamily: font.sans, fontSize: 20, color: c.body }}>{label}</span>
                      </div>
                    );
                  })}
                </div>

                <div style={{ display: "flex", gap: 40, marginTop: 40 }}>
                  <span style={{ fontFamily: font.mono, fontSize: 23, color: c.greenInk, fontWeight: 500 }}>
                    github.com/sulaiman013/fabric-x-duckdb
                  </span>
                  <span style={{ fontFamily: font.mono, fontSize: 23, color: c.muted }}>
                    sulaimanahmed.dev
                  </span>
                </div>
              </div>
            </div>
          </div>
        }
        foot={
          <Readout
            at={90}
            stats={[
              { v: "0", l: "orphan dimension keys", tone: "green", at: 90 },
              { v: "3 runs", l: "identical, rule by rule", tone: "green", at: 100 },
              { v: "$0.27", l: "per full rebuild", tone: "green", at: 110 },
              { v: "1:51", l: "source to decision, on a trial capacity", at: 120, small: true },
            ]}
          />
        }
      />
    </AbsoluteFill>
  );
};
