/**
 * Scene 4, the transformation. This is the first of the film's three load-bearing
 * moments, so it gets the longest hold and the only two-stage count: the source
 * total arrives, then 593,209 duplicates are visibly taken off it. The seven
 * rules light in descending fire order, which is the order the report shows them.
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Paper, Mono, Display, Line, Card, Stage, CountUp, ramp } from "../components/Primitives";
import { Icon } from "../components/Icon";
import { c, font } from "../theme";

const RULES: Array<[string, string, number]> = [
  ["declined", "24.6m", 1],
  ["new_merchant", "13.7m", 0.56],
  ["odd_hour", "10.2m", 0.41],
  ["card_not_present", "10.1m", 0.41],
  ["amount_anomaly", "3.6m", 0.15],
  ["high_risk_mcc", "2.1m", 0.09],
  ["velocity", "865k", 0.04],
];

export const S4Transform: React.FC = () => {
  const frame = useCurrentFrame();
  const dedupe = ramp(frame, [96, 134]);

  return (
    <Paper drift={1200}>
      <Stage n="03" label="Transformation" at={0} />

      <AbsoluteFill style={{ padding: "176px 120px 96px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div style={{ opacity: ramp(frame, [0, 16]) }}>
            <Icon name="duckdb" size={62} />
          </div>
          <Display text="One node. No cluster." at={4} size={76} italicFrom={2} />
        </div>
        <div style={{ height: 18 }} />
        <Line at={24} size={28} color={c.muted} style={{ maxWidth: 1000 }}>
          DuckDB on a Fabric Python notebook, 8 vCores. The job fits on one
          machine, so it runs on one.
        </Line>

        <div style={{ display: "flex", gap: 48, marginTop: 52, alignItems: "flex-start" }}>
          {/* left: the count, and the duplicates coming off it */}
          <div style={{ width: 760 }}>
            <Mono at={46} size={15}>rows scored</Mono>
            <CountUp to={50000001} at={48} dur={44} size={96} />

            <div
              style={{
                marginTop: 26,
                display: "flex",
                alignItems: "center",
                gap: 16,
                opacity: dedupe,
                transform: `translateX(${(1 - dedupe) * -22}px)`,
              }}
            >
              <div
                style={{
                  fontFamily: font.mono,
                  fontSize: 30,
                  fontWeight: 700,
                  color: c.redInk,
                  background: c.redBg,
                  border: `1px solid #F0C3C1`,
                  borderRadius: 10,
                  padding: "8px 16px",
                }}
              >
                &minus; 593,209
              </div>
              <div style={{ fontFamily: font.sans, fontSize: 24, color: c.body }}>
                exact duplicate rows resolved
              </div>
            </div>

            <div style={{ height: 30 }} />
            <Mono at={140} size={15} color={c.greenInk}>
              rows in the gold fact
            </Mono>
            <CountUp to={49406792} at={142} dur={40} size={104} color={c.greenInk} />

            <div style={{ height: 22 }} />
            <Line at={186} size={24} color={c.body} style={{ maxWidth: 700 }}>
              Identical across three consecutive runs, rule by rule.
            </Line>
          </div>

          {/* right: the seven rules */}
          <Card at={72} style={{ padding: "26px 30px", flex: 1 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontFamily: font.mono,
                fontSize: 14,
                letterSpacing: 1.8,
                textTransform: "uppercase",
                color: c.faint,
                borderBottom: `1px solid ${c.divider}`,
                paddingBottom: 12,
                marginBottom: 6,
              }}
            >
              <span>seven measured rules</span>
              <span>firings</span>
            </div>
            {RULES.map(([name, count, w], i) => {
              const at = 86 + i * 7;
              const p = ramp(frame, [at, at + 26]);
              return (
                <div key={name} style={{ padding: "11px 0", opacity: p }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "baseline",
                      marginBottom: 7,
                    }}
                  >
                    <span style={{ fontFamily: font.mono, fontSize: 21, color: c.body }}>
                      {name}
                    </span>
                    <span
                      style={{
                        fontFamily: font.mono,
                        fontSize: 21,
                        fontWeight: 700,
                        color: c.greenInk,
                      }}
                    >
                      {count}
                    </span>
                  </div>
                  <div style={{ height: 6, background: c.rail, borderRadius: 999 }}>
                    <div
                      style={{
                        height: 6,
                        width: `${w * 100 * p}%`,
                        background: c.green,
                        borderRadius: 999,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </Card>
        </div>

        <div style={{ marginTop: 34, display: "flex", gap: 24, alignItems: "baseline" }}>
          <Line at={206} size={34} color={c.ink} weight={700}>
            12.8 minutes
          </Line>
          <Line at={212} size={25} color={c.muted}>
            clean, conform, score, deduplicate, build the star, write parquet
          </Line>
        </div>
      </AbsoluteFill>
    </Paper>
  );
};
