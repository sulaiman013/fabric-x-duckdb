/**
 * Scene 5. The transformation. 540f / 18s.
 *
 * Three things happen to the same field, in view:
 *
 *   1. Seven rules sweep it, each firing sparks and racing its own counter.
 *   2. 593,209 duplicate cells lift off the plane and float away.
 *   3. What is left reorganises into a star schema, with the dimensions
 *      snapping into orbit on wires that draw themselves.
 *
 * The v3 film put all of that in a table of seven rows.
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { noise2D } from "@remotion/noise";
import { Field, fieldSize } from "../motion/Field";
import { Wire, curve } from "../motion/Wire";
import { Caption, Grain, Odometer, ScanHead, Slab, Sparks, ramp, pop } from "../motion/bits";
import { c, font } from "../theme";

const COLS = 56;
const ROWS = 15;
const CELL = 28;
const GAP = 5;
const { w: FW, h: FH } = fieldSize(COLS, ROWS, CELL, GAP);

const T_RULES = 40;
const RULE_EVERY = 26;
const T_DEDUP = 240;
const T_STAR = 330;

const RULES: Array<[string, number]> = [
  ["declined", 24580346],
  ["new_merchant", 13697031],
  ["card_not_present", 10164144],
  ["odd_hour", 10118821],
  ["amount_anomaly", 3624172],
  ["high_risk_mcc", 2126003],
  ["velocity", 864962],
];

const DIMS = ["customer", "merchant", "card", "channel", "date", "time", "risk rule"];

export const S5Transform: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const rulesDone = Math.min(RULES.length, Math.floor((frame - T_RULES) / RULE_EVERY) + 1);
  const firedTotal = RULES.slice(0, Math.max(0, rulesDone)).reduce((a, r) => a + r[1], 0);

  const scanP = ramp(frame, [T_RULES, T_RULES + RULES.length * RULE_EVERY]);
  const scanning = frame >= T_RULES && frame <= T_RULES + RULES.length * RULE_EVERY + 8;

  // a MOVE, not a cross-fade: the field slides out left as the star slides
  // in from the right, so the stage is never momentarily empty
  // a SHORT handover. 34 frames of two half-transparent layers is a
  // washed-out hole, not a transition.
  const swap = ramp(frame, [T_STAR, T_STAR + 14]);
  const starUp = ramp(frame, [T_STAR, T_STAR + 10]);

  return (
    <AbsoluteFill style={{ background: c.paper, overflow: "hidden" }}>
      <Grain opacity={0.18} />

      <Caption at={4} x={96} y={70} size={50} sub="one node, one session, 12.8 minutes of work">
        Seven rules,{" "}
        <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", color: c.greenInk }}>
          scored in place.
        </span>
      </Caption>

      {/* the field being scored and thinned */}
      <AbsoluteFill
        style={{ alignItems: "center", justifyContent: "center", paddingTop: 110, paddingBottom: 150,
          transform: `scale(${1 - swap * 0.62})`, opacity: 1 - swap }}
      >
        <div style={{ position: "relative", width: FW, height: FH }}>
          <Field
            cols={COLS}
            rows={ROWS}
            cell={CELL}
            gap={GAP}
            revealAt={0}
            revealDur={30}
            scanAt={T_RULES}
            scanDur={RULES.length * RULE_EVERY}
            dirtyRate={0.3}
            alertRate={0.06}
            liftAt={T_DEDUP}
            liftRate={0.12}
            seed="transform"
          />
          {scanning ? <ScanHead x={scanP * FW} height={FH} color={c.greenStrong} glow={110} /> : null}

          {/* each rule fires where the head is */}
          {RULES.map(([name], i) => {
            const at = T_RULES + i * RULE_EVERY;
            return (
              <Sparks
                key={name}
                x={((i + 0.6) / RULES.length) * FW}
                y={FH * (0.25 + Math.abs(noise2D("ry", i, 0)) * 0.5)}
                at={at}
                n={16}
                spread={140}
                color={c.amber}
                seed={i + 10}
                life={26}
              />
            );
          })}
        </div>
      </AbsoluteFill>

      {/* the rules ticking off as they fire */}
      <div style={{ position: "absolute", left: 96, bottom: 74, opacity: 1 - swap }}>
        <div
          style={{
            fontFamily: font.mono,
            fontSize: 12,
            letterSpacing: 2,
            textTransform: "uppercase",
            color: c.faint,
            marginBottom: 12,
          }}
        >
          rule firings, cumulative
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
          <span
            style={{
              fontFamily: font.mono,
              fontWeight: 700,
              fontSize: 64,
              color: c.greenInk,
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {firedTotal.toLocaleString("en-GB")}
          </span>
        </div>
        <div style={{ display: "flex", gap: 9, marginTop: 16, flexWrap: "wrap", maxWidth: 900 }}>
          {RULES.map(([name], i) => {
            const on = i < rulesDone;
            const p = on ? pop(frame, fps, T_RULES + i * RULE_EVERY) : 0;
            return (
              <span
                key={name}
                style={{
                  fontFamily: font.mono,
                  fontSize: 13,
                  color: on ? c.greenInk : c.faint,
                  background: on ? c.greenBg : "transparent",
                  border: `1px solid ${on ? c.greenLine : c.border}`,
                  borderRadius: 999,
                  padding: "6px 13px",
                  opacity: 0.35 + p * 0.65,
                  transform: `scale(${0.94 + p * 0.06})`,
                }}
              >
                {name}
              </span>
            );
          })}
        </div>
      </div>

      {/* the dedup, counted as the cells lift away */}
      <div
        style={{
          position: "absolute",
          right: 96,
          bottom: 74,
          textAlign: "right",
          opacity: ramp(frame, [T_DEDUP, T_DEDUP + 24]) * (1 - swap),
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 10, justifyContent: "flex-end" }}>
          <span style={{ fontFamily: font.mono, fontSize: 30, color: c.redInk }}>&minus;</span>
          <Odometer to={593209} at={T_DEDUP + 4} dur={40} size={64} color={c.redInk} />
        </div>
        <div
          style={{
            fontFamily: font.mono,
            fontSize: 12,
            letterSpacing: 1.8,
            textTransform: "uppercase",
            color: c.muted,
            marginTop: 8,
          }}
        >
          exact duplicates, lifted out
        </div>
      </div>

      {/* what is left, assembled into a star */}
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center",
        transform: `scale(${0.72 + starUp * 0.28})`, opacity: starUp }}>
        <div style={{ position: "relative", width: 1500, height: 720 }}>
          {DIMS.map((dname, i) => {
            const a = (i / DIMS.length) * Math.PI * 2 - Math.PI / 2;
            const x = 750 + Math.cos(a) * 620;
            const y = 350 + Math.sin(a) * 320;
            const at = T_STAR + 4 + i * 4;
            return (
              <React.Fragment key={dname}>
                <Wire
                  d={curve(750, 350, x, y, 0)}
                  drawAt={at}
                  drawDur={18}
                  color={c.greenLine}
                  width={1.8}
                />
                <Slab x={x - 108} y={y - 36} w={216} h={72} at={at + 6} tone="white">
                  <div
                    style={{
                      display: "grid",
                      placeItems: "center",
                      height: "100%",
                      fontFamily: font.mono,
                      fontSize: 19,
                      color: c.body,
                    }}
                  >
                    {dname}
                  </div>
                </Slab>
              </React.Fragment>
            );
          })}

          <Slab x={750 - 210} y={350 - 88} w={420} h={176} at={T_STAR + 6} tone="green">
            <div style={{ display: "grid", placeItems: "center", height: "100%" }}>
              <div
                style={{
                  fontFamily: font.mono,
                  fontWeight: 700,
                  fontSize: 40,
                  color: c.greenInk,
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                49,406,792
              </div>
              <div style={{ fontFamily: font.mono, fontSize: 12, color: c.muted, marginTop: -14 }}>
                fact_transaction
              </div>
            </div>
          </Slab>
        </div>
      </AbsoluteFill>

      {/* the gold layer, stated under the shape it produced, from early */}
      <div
        style={{
          position: "absolute",
          left: 96,
          right: 96,
          bottom: 62,
          display: "flex",
          alignItems: "flex-end",
          gap: 58,
          opacity: swap,
        }}
      >
        {([
          ["9", "gold delta tables"],
          ["36", "files, 2.5 GB"],
          ["0", "orphan dimension keys"],
          ["3 runs", "identical, rule by rule"],
        ]).map(([v, l], i) => (
          <div key={l} style={{ opacity: ramp(frame, [T_STAR + 26 + i * 8, T_STAR + 50 + i * 8]) }}>
            <div
              style={{
                fontFamily: font.mono,
                fontWeight: 700,
                fontSize: 52,
                color: c.greenInk,
                fontVariantNumeric: "tabular-nums",
                lineHeight: 1,
              }}
            >
              {v}
            </div>
            <div
              style={{
                fontFamily: font.mono,
                fontSize: 13,
                letterSpacing: 1.7,
                textTransform: "uppercase",
                color: c.muted,
                marginTop: 11,
              }}
            >
              {l}
            </div>
          </div>
        ))}
        <span
          style={{
            marginLeft: "auto",
            maxWidth: 560,
            textAlign: "right",
            fontFamily: font.serifItalic,
            fontStyle: "italic",
            fontSize: 30,
            lineHeight: 1.3,
            color: c.greenInk,
            opacity: ramp(frame, [T_STAR + 70, T_STAR + 96]),
          }}
        >
          Written as parquet, then rewritten as V-Ordered Delta by Spark.
        </span>
      </div>
    </AbsoluteFill>
  );
};
