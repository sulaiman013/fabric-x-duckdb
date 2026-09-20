/**
 * Scene 2, the mess. Every string on screen is a real value from the extract,
 * not an illustration of one. They arrive scattered and slightly rotated, then
 * settle onto a grid: the motion is the argument, which is that this looks like
 * noise until something conforms it.
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Paper, Mono, Display, Line, Chip, Stage, ramp } from "../components/Primitives";
import { c, rand } from "../theme";

/** Real values from the generated extract: dates, money, nulls, timestamps. */
const DIRTY: Array<[string, "neutral" | "amber" | "red"]> = [
  ["2024-03-05", "neutral"],
  ["05/03/2024", "amber"],
  ["03/05/2024", "amber"],
  ["5-Mar-24", "amber"],
  ["05.03.2024", "amber"],
  ["9999-12-31", "red"],
  ["1,234.50", "neutral"],
  ["RM99.00", "amber"],
  ["(45.00)", "red"],
  ["1750529113", "amber"],
  ["2023-12-04T06:27:31+08:00", "neutral"],
  ["N/A", "red"],
  ["#N/A", "red"],
  ["unknown", "red"],
  ["Ahmad bin Abdullah", "neutral"],
  ["AHMAD BIN ABDULLAH", "amber"],
  ["Abdullah, Ahmad", "amber"],
  ["MALAYSIA", "neutral"],
  ["Msia", "amber"],
  ["my", "amber"],
];

export const S2Mess: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <Paper drift={400}>
      <Stage n="01" label="The source" at={0} />

      <AbsoluteFill style={{ padding: "180px 120px 96px" }}>
        <Display text="None of it parses." at={6} size={78} italicFrom={2} />

        <div style={{ height: 40 }} />

        {/* the values: scattered in, then settling to a flow layout */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 14,
            maxWidth: 1400,
          }}
        >
          {DIRTY.map(([v, tone], i) => {
            const at = 26 + i * 4.2;
            const settle = ramp(frame, [at, at + 34]);
            const jx = (rand(i + 1) - 0.5) * 220 * (1 - settle);
            const jy = (rand(i + 31) - 0.5) * 150 * (1 - settle);
            const rot = (rand(i + 61) - 0.5) * 16 * (1 - settle);
            return (
              <div
                key={i}
                style={{
                  transform: `translate(${jx}px, ${jy}px) rotate(${rot}deg)`,
                }}
              >
                <Chip at={at} tone={tone} size={25}>
                  {v}
                </Chip>
              </div>
            );
          })}
        </div>

        <div style={{ flex: 1 }} />

        <div style={{ display: "flex", gap: 64, alignItems: "flex-end" }}>
          <Line at={150} size={29} color={c.body} style={{ maxWidth: 760 }}>
            Five date formats in one column. Money as text, with currency
            prefixes and parenthesised negatives. Epoch integers beside ISO
            timestamps.
          </Line>
          <div style={{ flex: 1 }} />
          <div style={{ textAlign: "right" }}>
            <Mono at={162} size={15} color={c.faint}>
              measured on a 300k sample
            </Mono>
            <div style={{ height: 10 }} />
            <Line at={166} size={26} color={c.redInk} weight={600}>
              posting_date parses 52.4% of the time
            </Line>
          </div>
        </div>
      </AbsoluteFill>
    </Paper>
  );
};
