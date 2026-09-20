/**
 * Scene 3. The three choices. 360f / 12s.
 *
 * The contract with the viewer. v2 had no scene like this, which is why it
 * played as a tour: the viewer never knew what they were being asked to judge.
 * Each of these three is paid off later and labelled when it lands.
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Paper, Mono, Display, Stage, ramp } from "../components/Primitives";
import { Badge } from "../components/Blocks";
import { c, font } from "../theme";

const CHOICES: Array<{ n: string; q: string; s: string; at: number }> = [
  {
    n: "01",
    q: "Move it without touching the source.",
    s: "The database is on-premises. Nothing may connect inward to it.",
    at: 54,
  },
  {
    n: "02",
    q: "Transform it without paying for a cluster.",
    s: "The job fits on one node. A cluster would be a decision, not a default.",
    at: 96,
  },
  {
    n: "03",
    q: "Serve it without keeping a third copy.",
    s: "Fifty million rows should not be imported and refreshed on a timer.",
    at: 138,
  },
];

export const S03Choices: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <Paper drift={900}>
      <Stage n="02" label="The argument" at={0} />

      <AbsoluteFill style={{ padding: "160px 130px 90px" }}>
        <Display text="Three choices, and the evidence for each." at={4} size={66} italicFrom={4} />

        <div style={{ height: 50 }} />

        <div style={{ display: "flex", flexDirection: "column", gap: 26 }}>
          {CHOICES.map((ch) => {
            const p = ramp(frame, [ch.at, ch.at + 24]);
            return (
              <div
                key={ch.n}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 30,
                  opacity: p,
                  transform: `translateX(${(1 - p) * 34}px)`,
                }}
              >
                <div
                  style={{
                    fontFamily: font.mono,
                    fontSize: 22,
                    fontWeight: 700,
                    color: c.greenInk,
                    background: c.greenBg,
                    border: `1px solid ${c.greenLine}`,
                    borderRadius: 12,
                    padding: "12px 16px",
                    flex: "0 0 auto",
                    letterSpacing: 1,
                  }}
                >
                  {ch.n}
                </div>
                <div style={{ paddingTop: 2 }}>
                  <div
                    style={{
                      fontFamily: font.serif,
                      fontSize: 50,
                      color: c.ink,
                      lineHeight: 1.16,
                    }}
                  >
                    {ch.q}
                  </div>
                  <div
                    style={{
                      fontFamily: font.sans,
                      fontSize: 26,
                      color: c.muted,
                      marginTop: 10,
                    }}
                  >
                    {ch.s}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* the rule the rest of the film plays by */}
        <div
          style={{
            marginTop: "auto",
            paddingTop: 40,
            borderTop: `1px solid ${c.border}`,
            opacity: ramp(frame, [198, 222]),
          }}
        >
          <div style={{ display: "flex", gap: 12, marginBottom: 18 }}>
            <Badge tone="measured" at={202}>
              measured
            </Badge>
            <Badge tone="modelled" at={208}>
              modelled
            </Badge>
            <Badge tone="assumed" at={214}>
              assumed rate
            </Badge>
          </div>
          <Mono at={206} size={17} color={c.body} style={{ letterSpacing: 1.4 }}>
            every figure after this is read off the running system, or says which of these it is
          </Mono>
        </div>
      </AbsoluteFill>
    </Paper>
  );
};
