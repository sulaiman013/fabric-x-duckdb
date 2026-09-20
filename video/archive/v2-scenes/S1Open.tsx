/**
 * Scene 1, the hook. The number is the hook, so it arrives before any words do
 * and everything else is timed off it. Held still at the end: the research is
 * unanimous that constant motion reads as noise, and a frame that stops is what
 * makes the next cut land.
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Paper, Display, Line, CountUp, ramp } from "../components/Primitives";
import { Icon } from "../components/Icon";
import { c, font } from "../theme";

export const S1Open: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <Paper>
      <AbsoluteFill
        style={{
          padding: "96px 120px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
        }}
      >
        {/* the stack, in real vendor marks, before a single word is said */}
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          {(["postgres", "fabric", "duckdb", "powerbi"] as const).map((k, i) => {
            const p = ramp(frame, [i * 5, i * 5 + 18]);
            return (
              <React.Fragment key={k}>
                {i ? (
                  <span
                    style={{
                      fontFamily: font.mono,
                      fontSize: 22,
                      color: c.faint,
                      opacity: p,
                    }}
                  >
                    &rarr;
                  </span>
                ) : null}
                <div style={{ opacity: p, transform: `scale(${0.8 + p * 0.2})` }}>
                  <Icon name={k} size={46} />
                </div>
              </React.Fragment>
            );
          })}
        </div>

        <div style={{ height: 34 }} />

        <div style={{ display: "flex", alignItems: "baseline", gap: 26 }}>
          <CountUp to={50000000} at={8} dur={52} size={188} color={c.ink} />
          <div
            style={{
              fontFamily: font.serifItalic,
              fontStyle: "italic",
              fontSize: 78,
              color: c.greenInk,
              opacity: ramp(frame, [46, 64]),
              transform: `translateY(${ramp(frame, [46, 70], [22, 0])}px)`,
            }}
          >
            rows
          </div>
        </div>

        <div style={{ height: 18 }} />

        <Display
          text="100 columns. Every one of them text."
          at={60}
          size={62}
          italicFrom={4}
          style={{ maxWidth: 1180 }}
        />

        <div style={{ height: 26 }} />

        <Line at={84} size={30} color={c.muted} style={{ maxWidth: 900 }}>
          Nothing cleaned, nothing rejected. This is the landing zone, and it is
          the whole point.
        </Line>

        {/* a thin rule that draws itself, which gives the held tail some life */}
        <div
          style={{
            marginTop: 46,
            height: 2,
            width: `${ramp(frame, [70, 116], [0, 560])}px`,
            background: c.green,
          }}
        />
      </AbsoluteFill>
    </Paper>
  );
};
