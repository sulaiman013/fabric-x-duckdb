/**
 * Scene 7. What the choice produced. 480f / 16s.
 *
 * The funnel, then the seven rules with the counts the build recorded, then
 * the two bugs it took to make those counts repeatable. The bugs are the point:
 * three identical runs is only interesting once you know what made them differ.
 */
import React from "react";
import { useCurrentFrame } from "remotion";
import { Paper, Mono, Display, Line, Stage, CountUp, ramp } from "../components/Primitives";
import { DataTable, Badge, Phase } from "../components/Blocks";
import { c, font } from "../theme";

const RULES = [
  ["declined", "10", "24,580,346"],
  ["new_merchant", "10", "13,697,031"],
  ["card_not_present", "25", "10,164,144"],
  ["odd_hour", "15", "10,118,821"],
  ["amount_anomaly", "30", "3,624,172"],
  ["high_risk_mcc", "25", "2,126,003"],
  ["velocity", "30", "864,962"],
];

export const S07Result: React.FC = () => {
  const frame = useCurrentFrame();
  const OUT = 150;
  const IN = 170;

  return (
    <Paper drift={2500}>
      <Stage n="06" label="The result" at={0} />

      <Phase out={OUT} style={{ padding: "156px 130px 90px" }}>
        <div>
          <Display text="Fifty million in. Forty-nine and a half out." at={4} size={62} italicFrom={4} />

          <div style={{ display: "flex", alignItems: "flex-end", gap: 74, marginTop: 64 }}>
            <div>
              <Mono at={38} size={15}>
                scored
              </Mono>
              <CountUp to={50000001} at={40} dur={34} size={86} />
            </div>
            <div
              style={{
                fontFamily: font.mono,
                fontSize: 52,
                color: c.border,
                paddingBottom: 14,
                opacity: ramp(frame, [72, 86]),
              }}
            >
              &minus;
            </div>
            <div>
              <Mono at={74} size={15} color={c.redInk}>
                duplicates resolved
              </Mono>
              <CountUp to={593209} at={78} dur={30} size={86} color={c.redInk} />
            </div>
            <div
              style={{
                fontFamily: font.mono,
                fontSize: 52,
                color: c.border,
                paddingBottom: 14,
                opacity: ramp(frame, [104, 118]),
              }}
            >
              =
            </div>
            <div>
              <Mono at={106} size={15} color={c.greenInk}>
                gold fact
              </Mono>
              <CountUp to={49406792} at={110} dur={32} size={86} color={c.greenInk} />
            </div>
          </div>
        </div>
      </Phase>

      {/* the seven rules */}
      <Phase at={IN} style={{ padding: "156px 130px 90px" }}>
        <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
          <Display text="Seven rules, and what each one fires." at={180} size={54} italicFrom={4} />
          <div style={{ height: 22 }} />

          <DataTable
            at={200}
            stagger={12}
            cols="1fr 130px 280px"
            size={25}
            head={["Rule", "Weight", "Firings"]}
            mono={[true, true, true]}
            rows={RULES.map((r) => ({ cells: r }))}
          />

          <div
            style={{
              marginTop: 18,
              paddingTop: 18,
              borderTop: `1px solid ${c.border}`,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "baseline",
              opacity: ramp(frame, [300, 322]),
            }}
          >
            <div style={{ fontFamily: font.sans, fontSize: 25, color: c.body }}>
              They total <b>65,175,479</b>, which is the alert fact's row count exactly.
            </div>
            <Badge tone="measured" at={306}>
              reconciled
            </Badge>
          </div>

          <div style={{ display: "flex", gap: 74, marginTop: "auto", alignItems: "flex-end" }}>
            <div>
              <div
                style={{
                  fontFamily: font.mono,
                  fontWeight: 700,
                  fontSize: 76,
                  color: c.greenInk,
                  opacity: ramp(frame, [334, 356]),
                }}
              >
                12.8 min
              </div>
              <Mono at={340} size={15}>
                of work on one node
              </Mono>
            </div>
            <div>
              <div
                style={{
                  fontFamily: font.mono,
                  fontWeight: 700,
                  fontSize: 76,
                  color: c.greenInk,
                  opacity: ramp(frame, [348, 370]),
                }}
              >
                3 runs
              </div>
              <Mono at={354} size={15}>
                identical, rule by rule
              </Mono>
            </div>
            <Line at={368} size={24} color={c.body} style={{ flex: 1, paddingBottom: 6 }}>
              Getting there cost two real bugs: a timestamp that changed meaning
              between my laptop's timezone and the capacity's, and a window
              function whose tiebreak was not deterministic and quietly lost
              87,000 firings a run.
            </Line>
          </div>
        </div>
      </Phase>
    </Paper>
  );
};
