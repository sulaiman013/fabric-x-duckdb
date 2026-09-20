/**
 * The report, taken apart. 900f / 30s.
 *
 * Two pages, each given the same treatment: the whole page comes forward and
 * holds so you can see it is a page, then it pulls apart into its own visuals
 * and the camera walks among them, holding on the two or three that are worth
 * reading.
 *
 * The other two pages are shown whole at the end, so the set is complete
 * without spending thirty seconds on cards nobody needs to read.
 */
import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { ExplodedPage, Piece } from "../motion/Exploded";
import { Room, Marquee } from "../motion/Theatre";
import { ramp, pop } from "../motion/bits";
import { font } from "../theme";

const IW = 4258;
const IH = 2394;
const BW = 1440;
const BH = Math.round((BW / IW) * IH);

const OVERVIEW: Piece[] = [
  { id: "title", rect: [40, 176, 4190, 97] },
  { id: "chips", rect: [40, 284, 4190, 102] },
  { id: "kpis", rect: [40, 406, 4190, 219] },
  { id: "months", rect: [40, 681, 2680, 897] },
  { id: "channel", rect: [2759, 681, 1465, 897] },
  { id: "composition", rect: [40, 1624, 2680, 727] },
  { id: "firings", rect: [2759, 1624, 1465, 727] },
];

const RULES: Piece[] = [
  { id: "title", rect: [40, 176, 4190, 97] },
  { id: "kpis", rect: [40, 292, 4190, 219] },
  { id: "volume", rect: [51, 568, 2282, 874] },
  { id: "together", rect: [2373, 568, 1834, 874] },
  { id: "dist", rect: [51, 1482, 2282, 869] },
  { id: "threshold", rect: [2373, 1482, 1834, 869] },
];

/* page one: overview */
const A = 0;
const A_END = 430;
/* page two: rule effectiveness */
const B = 430;
const B_END = 760;
/* the remaining two pages, shown whole */
const C = 760;

export const S10Report: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const pageA = frame < A_END ? 1 : 1 - ramp(frame, [A_END - 16, A_END]);
  const pageB = frame < B ? 0 : frame < B_END ? ramp(frame, [B, B + 16]) : 1 - ramp(frame, [B_END - 16, B_END]);
  const pageC = frame < C ? 0 : ramp(frame, [C, C + 18]);

  const name = frame < B ? "Overview" : frame < C ? "Rule effectiveness" : "Risk and exposure, Guide";

  return (
    <Room at={0}>
      {/* ---------------------------------------------------- page one */}
      {pageA > 0.01 ? (
        <AbsoluteFill style={{ opacity: pageA }}>
          <ExplodedPage
            src="report-overview.png"
            iw={IW}
            ih={IH}
            bw={BW}
            bh={BH}
            pieces={OVERVIEW}
            arriveAt={A + 2}
            explodeAt={A + 96}
            explodeDur={52}
            spread={0.46}
            seed="ov"
            focus={[
              { at: A, id: null },
              { at: A + 150, id: null },
              { at: A + 196, id: "kpis" },
              { at: A + 252, id: "kpis" },
              { at: A + 300, id: "months" },
              { at: A + 348, id: "months" },
              { at: A + 392, id: "firings" },
            ]}
          />
        </AbsoluteFill>
      ) : null}

      {/* ---------------------------------------------------- page two */}
      {pageB > 0.01 ? (
        <AbsoluteFill style={{ opacity: pageB }}>
          <ExplodedPage
            src="report-rules.png"
            iw={IW}
            ih={IH}
            bw={BW}
            bh={BH}
            pieces={RULES}
            arriveAt={B + 2}
            explodeAt={B + 74}
            explodeDur={50}
            spread={0.46}
            seed="rl"
            focus={[
              { at: B, id: null },
              { at: B + 126, id: null },
              { at: B + 168, id: "volume" },
              { at: B + 218, id: "volume" },
              { at: B + 262, id: "threshold" },
            ]}
          />
        </AbsoluteFill>
      ) : null}

      {/* ------------------------------------- the other two, shown whole */}
      {pageC > 0.01 ? (
        <AbsoluteFill
          style={{
            opacity: pageC,
            alignItems: "center",
            justifyContent: "center",
            gap: 46,
            flexDirection: "row",
            perspective: 2400,
          }}
        >
          {(["report-risk.png", "report-guide.png"] as const).map((src, i) => {
            const p = pop(frame, fps, C + 10 + i * 12, { damping: 18, stiffness: 66 });
            const w = 780;
            return (
              <div
                key={src}
                style={{
                  width: w,
                  height: Math.round((w / IW) * IH),
                  borderRadius: 10,
                  overflow: "hidden",
                  opacity: p,
                  transform: `rotateY(${(i === 0 ? 13 : -13) * (2 - p)}deg) translateZ(${(1 - p) * -260}px)`,
                  boxShadow: "0 26px 70px rgba(0,0,0,.45)",
                  background: "#fff",
                }}
              >
                <Img
                  src={staticFile(src)}
                  style={{ width: "100%", height: "100%", display: "block" }}
                />
              </div>
            );
          })}
        </AbsoluteFill>
      ) : null}

      {/* the header, tracking the page */}
      <div
        style={{
          position: "absolute",
          left: 96,
          top: 56,
          // it retires once the page opens, because a card now stands here
          opacity: ramp(frame, [6, 30]) * (1 - ramp(frame, [86, 116])) +
            ramp(frame, [B - 10, B + 10]) * (1 - ramp(frame, [B + 64, B + 94])),
        }}
      >
        <div
          style={{
            fontFamily: font.mono,
            fontSize: 14,
            letterSpacing: 2.6,
            textTransform: "uppercase",
            color: "#8FBF6A",
            marginBottom: 11,
          }}
        >
          fincrime &middot; direct lake &middot; {name}
        </div>
        <div style={{ fontFamily: font.serif, fontSize: 48, color: "#EEF6E6", lineHeight: 1.06 }}>
          Four pages.{" "}
          <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", color: "#A8D98A" }}>
            One visual each.
          </span>
        </div>
      </div>

      {/* what the camera is on */}
      <Marquee at={A + 16} until={A + 92} kicker="the whole page"
        title="Every page is a single HTML visual."
        body="One DAX measure ships a pre-aggregated cube and its own renderer. Every click re-aggregates in the browser and never queries the model again." />
      <Marquee at={A + 104} until={A + 188} kicker="pulled apart"
        title="Which is why it can be taken to pieces."
        body="Seven regions, one measure, no cross-filtering between them because the page is the visual." />
      <Marquee at={A + 202} until={A + 292} kicker="the kpi strip"
        title="It states its own denominator."
        body="49,406,792 of 49,406,792 in scope. A filtered page can never be mistaken for the whole population." />
      <Marquee at={A + 306} until={A + 384} kicker="transactions by month"
        title="The stub bar on the far left is every row whose date never parsed."
        body="Shown, not quietly dropped, because that is what the data contains." side="right" />
      <Marquee at={A + 398} until={A_END - 4} kicker="rule firings"
        title="A firing is not an alert, and the card prints that underneath itself."
        body="The two differ by a factor of 45.8." side="right" />

      <Marquee at={B + 16} until={B + 120} kicker="rule effectiveness"
        title="The second page, and the same treatment."
        body="Six regions: the header, the measures, and four visuals that each answer one question." />
      <Marquee at={B + 174} until={B + 256} kicker="rules by firing volume"
        title="Weight and volume are different things, so both are on the table."
        body="declined fires 25m times at weight 10. velocity fires 865k times at weight 30. Neither hides behind the other." />
      <Marquee at={B + 268} until={B_END - 4} kicker="what a threshold costs"
        title="The cut-off, converted into people."
        body="Most monitoring packs stop at the alert count. This one carries the staffing consequence in the same table." side="right" />

      <Marquee at={C + 24} kicker="and the other two"
        title="Risk and exposure, and a guide that ships inside the report."
        body="The guide's last section is called What this cannot do." />
    </Room>
  );
};
