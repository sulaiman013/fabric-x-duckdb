/**
 * Scene 2. The mess. 480f / 16s.
 *
 * The values are the real ones from the generator, grouped by the family of
 * problem they cause, because "dirty data" as a phrase means nothing and four
 * date formats sitting next to each other means everything.
 *
 * Then the measured parse rates, which are the number that makes the rest of
 * the film necessary: half the dates do not parse.
 */
import React from "react";
import { useCurrentFrame } from "remotion";
import { Paper, Mono, Display, Chip, Line, Stage, ramp } from "../components/Primitives";
import { Bar, Phase } from "../components/Blocks";
import { c, font } from "../theme";

type Family = {
  label: string;
  values: string[];
  tone: "neutral" | "amber" | "red";
  at: number;
};

const FAMILIES: Family[] = [
  {
    label: "five ways to write one date",
    values: ["2024-03-11", "11/03/2024", "Mar 11 2024", "2024.03.11", "20240311"],
    tone: "neutral",
    at: 30,
  },
  {
    label: "four ways to write one number",
    values: ["RM99.00", "(45.00)", "1,250.50", "USD 3.20"],
    tone: "amber",
    at: 74,
  },
  {
    label: "a unix epoch hiding in a date column",
    values: ["1750529113"],
    tone: "amber",
    at: 112,
  },
  {
    label: "six spellings of nothing",
    values: ["#N/A", "NA", "null", "NULL", "-", "(blank)"],
    tone: "red",
    at: 138,
  },
];

const RATES: Array<[string, number, string]> = [
  ["posting_date", 0.524, "52.4%"],
  ["txn_amount", 0.817, "81.7%"],
  ["balance_after", 0.705, "70.5%"],
];

export const S02Mess: React.FC = () => {
  const frame = useCurrentFrame();
  // the values clear out as the measurement arrives, so the two halves of the
  // scene never compete for the eye. Both are Phases: the headline belongs to
  // the first half and leaves with it.
  const OUT = 212;
  const IN = 232;

  return (
    <Paper drift={400}>
      <Stage n="01" label="The source" at={0} />

      <Phase out={OUT} style={{ padding: "168px 130px 90px" }}>
        <Display text="It is all text." at={4} size={76} italicFrom={2} />
        <div style={{ height: 14 }} />
        <Line at={14} size={28} color={c.muted} style={{ maxWidth: 1300 }}>
          One table, 100 columns, every column declared as text in PostgreSQL,
          because that is what an extract from a real operational system looks
          like when nobody owned its types.
        </Line>

        {/* the dirty values */}
        <div style={{ marginTop: 46 }}>
          {FAMILIES.map((f) => (
            <div key={f.label} style={{ marginBottom: 26 }}>
              <div
                style={{
                  fontFamily: font.mono,
                  fontSize: 15,
                  letterSpacing: 2,
                  textTransform: "uppercase",
                  color: c.faint,
                  fontWeight: 600,
                  marginBottom: 12,
                  opacity: ramp(frame, [f.at, f.at + 14]),
                }}
              >
                {f.label}
              </div>
              <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
                {f.values.map((v, i) => (
                  <Chip key={v} at={f.at + 6 + i * 4} tone={f.tone} size={27}>
                    {v}
                  </Chip>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Phase>

      {/* what that actually costs, measured */}
      <Phase at={IN} style={{ padding: "180px 130px 90px" }}>
        <div>
          <Mono at={238} size={16} color={c.greenInk}>
            profiled on all 50,000,001 rows
          </Mono>
          <div style={{ height: 18 }} />
          <div
            style={{
              fontFamily: font.serif,
              fontSize: 52,
              color: c.ink,
              marginBottom: 40,
              opacity: ramp(frame, [244, 264]),
            }}
          >
            What actually parses
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 30, maxWidth: 1480 }}>
            {RATES.map(([name, v, disp], i) => (
              <Bar
                key={name}
                at={256 + i * 20}
                label={name}
                value={v}
                display={disp}
                tone={v < 0.6 ? "red" : "amber"}
                labelW={360}
                h={26}
                size={28}
              />
            ))}
          </div>

          <div
            style={{
              marginTop: 54,
              fontFamily: font.serifItalic,
              fontStyle: "italic",
              fontSize: 44,
              color: c.greenInk,
              maxWidth: 1400,
              lineHeight: 1.25,
              opacity: ramp(frame, [346, 372]),
              transform: `translateY(${ramp(frame, [346, 378], [18, 0])}px)`,
            }}
          >
            Half the dates do not parse. The cleaning step is the product, not a
            formality.
          </div>
        </div>
      </Phase>
    </Paper>
  );
};
