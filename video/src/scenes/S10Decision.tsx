/**
 * Scene 10. The decision it supports. 420f / 14s.
 *
 * The whole pipeline exists so that one number can be moved and the
 * consequence of moving it can be seen. Without this scene the film is a
 * competent stack demo; with it, it is a piece of work with a purpose.
 */
import React from "react";
import { useCurrentFrame } from "remotion";
import { Paper, Mono, Display, Stage, ramp } from "../components/Primitives";
import { DataTable, Phase } from "../components/Blocks";
import { c, font } from "../theme";

const CHAIN: Array<{ v: string; l: string; at: number; tone?: "green" | "ink" }> = [
  { v: "65,175,479", l: "rule firings", at: 24 },
  { v: "1,423,088", l: "alerts", at: 52 },
  { v: "a cut-off", l: "set at 60 of a possible 145", at: 80 },
  { v: "11", l: "analysts", at: 108, tone: "green" },
];

export const S10Decision: React.FC = () => {
  const frame = useCurrentFrame();
  const OUT = 162;
  const IN = 182;

  return (
    <Paper drift={3700}>
      <Stage n="09" label="The decision" at={0} />

      <Phase out={OUT} style={{ padding: "160px 120px 90px" }}>
        <Display text="This is what the pipeline is for." at={4} size={66} italicFrom={4} />

        {/* the chain */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 30,
            marginTop: 70,
          }}
        >
          {CHAIN.map((s, i) => (
            <React.Fragment key={s.l}>
              {i > 0 ? (
                <div
                  style={{
                    fontFamily: font.mono,
                    fontSize: 40,
                    color: c.border,
                    opacity: ramp(frame, [s.at - 10, s.at + 4]),
                  }}
                >
                  &rsaquo;
                </div>
              ) : null}
              <div
                style={{
                  opacity: ramp(frame, [s.at, s.at + 22]),
                  transform: `translateY(${ramp(frame, [s.at, s.at + 26], [18, 0])}px)`,
                }}
              >
                <div
                  style={{
                    fontFamily: font.mono,
                    fontWeight: 700,
                    fontSize: s.v.length > 6 ? 54 : 84,
                    color: s.tone === "green" ? c.greenInk : c.ink,
                    letterSpacing: -1,
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {s.v}
                </div>
                <div
                  style={{
                    fontFamily: font.mono,
                    fontSize: 15,
                    letterSpacing: 1.8,
                    textTransform: "uppercase",
                    color: c.muted,
                    marginTop: 8,
                  }}
                >
                  {s.l}
                </div>
              </div>
            </React.Fragment>
          ))}
        </div>
      </Phase>

      {/* the table that makes it a decision */}
      <Phase at={IN} style={{ padding: "190px 120px 90px" }}>
        <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
          <Mono at={188} size={16} color={c.greenInk}>
            move the cut-off, and watch the headcount move with it
          </Mono>
          <div style={{ height: 24 }} />

          <DataTable
            at={198}
            stagger={15}
            cols="1fr 240px 200px 220px"
            size={28}
            head={["Cut-off", "Alerts", "Rate", "Analysts"]}
            rows={[
              { cells: ["40", "7.1m", "14.38%", "57"] },
              { cells: ["50", "3.6m", "7.22%", "29"] },
              { cells: ["60, current", "1.4m", "2.88%", "11"], hl: true },
              { cells: ["70", "450k", "0.91%", "4"] },
              { cells: ["80", "184k", "0.37%", "1"] },
            ]}
          />

          <div
            style={{
              marginTop: 22,
              fontFamily: font.sans,
              fontSize: 21,
              color: c.faint,
              opacity: ramp(frame, [284, 306]),
            }}
          >
            The report's own footnote: assumes 50,000 alerts cleared per
            analyst-year across the period.
          </div>

          <div
            style={{
              marginTop: "auto",
              fontFamily: font.serifItalic,
              fontStyle: "italic",
              fontSize: 46,
              lineHeight: 1.26,
              color: c.greenInk,
              maxWidth: 1540,
              opacity: ramp(frame, [318, 346]),
              transform: `translateY(${ramp(frame, [318, 352], [20, 0])}px)`,
            }}
          >
            A queue of 317 analyst-loads is ignored. A queue of 11 is worked.
            Moving the cut-off is a staffing decision, not a preference.
          </div>
        </div>
      </Phase>
    </Paper>
  );
};
