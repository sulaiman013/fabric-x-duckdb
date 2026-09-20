/**
 * Scene 1. The open. 300f / 10s.
 *
 * Four real vendor marks, the size of the problem, and the sentence that says
 * what the whole thing is for. Nothing else: an opening that also tries to
 * explain the architecture is an opening nobody finishes.
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Paper, Mono, Display, CountUp, Line, ramp } from "../components/Primitives";
import { Icon, IconKey } from "../components/Icon";
import { c, font } from "../theme";

const STACK: IconKey[] = ["postgres", "fabric", "duckdb", "powerbi"];

export const S01Open: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <Paper>
      <AbsoluteFill
        style={{
          padding: "0 130px",
          justifyContent: "center",
          alignItems: "flex-start",
        }}
      >
        {/* the stack, resolving in */}
        <div style={{ display: "flex", alignItems: "center", gap: 36, marginBottom: 54 }}>
          {STACK.map((k, i) => {
            const at = 4 + i * 6;
            const p = ramp(frame, [at, at + 22]);
            return (
              <div
                key={k}
                style={{
                  opacity: p,
                  transform: `translateY(${(1 - p) * 18}px) scale(${0.86 + p * 0.14})`,
                }}
              >
                <Icon name={k} size={58} />
              </div>
            );
          })}
          <div
            style={{
              width: 1,
              height: 46,
              background: c.border,
              opacity: ramp(frame, [30, 44]),
            }}
          />
          <Mono at={34} size={17}>
            fabric-x-duckdb
          </Mono>
        </div>

        {/* the size of the problem */}
        <div style={{ display: "flex", alignItems: "baseline", gap: 30 }}>
          <CountUp to={50000001} at={26} dur={52} size={158} color={c.ink} />
          <div
            style={{
              fontFamily: font.serifItalic,
              fontStyle: "italic",
              fontSize: 86,
              color: c.greenInk,
              opacity: ramp(frame, [68, 88]),
              transform: `translateY(${ramp(frame, [68, 92], [22, 0])}px)`,
            }}
          >
            rows
          </div>
        </div>

        <div style={{ height: 26 }} />

        <Line at={92} size={34} color={c.body} style={{ maxWidth: 1180 }}>
          100 columns. Every one of them text.
        </Line>

        <div
          style={{
            width: 190,
            height: 2,
            background: c.green,
            margin: "40px 0 34px",
            transform: `scaleX(${ramp(frame, [118, 146])})`,
            transformOrigin: "left",
          }}
        />

        <Display
          text="From an on-premises database to a decision someone can act on."
          at={132}
          size={62}
          italicFrom={8}
          style={{ maxWidth: 1400 }}
        />
      </AbsoluteFill>
    </Paper>
  );
};
