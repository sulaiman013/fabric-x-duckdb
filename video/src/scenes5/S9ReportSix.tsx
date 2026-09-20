/**
 * Scene 9. The report, in six beats. 540f / 18s.
 *
 * This is the page the guide's whole method is built for, so it gets all six:
 * the finished page, the clear, the claim, the rebuild card by card, two holds
 * with an outline, the sweep, and a panel of query times sliding in.
 *
 * v4 spent 900 frames taking two pages apart. This spends 540 on one page and
 * ends on the thing that actually settles the argument, which is how long the
 * page takes to answer.
 */
import React from "react";
import { Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { SixBeatPage } from "../motion/SixBeat";
import { OVERVIEW, REPORT_IW, REPORT_IH } from "./cards";
import { Room } from "../motion/Theatre";
import { move, stagger, barGrow } from "../motion/library";
import { font, c } from "../theme";

/* Both captures are 16:9 (4258x2394 and 3840x2160), so the page IS the
   frame. No dark border around it. */
const BW = 1920;
const BH = 1080;

const T_CLEAR = 64;
const T_REBUILD = 185;
const T_SWEEP = 222;
const T_EXPLODE = 270;
const T_CLOSE = 340;
const T_PANEL = 530;

/** the query times, from BUILD_LOG's own table */
const QUERIES: Array<[string, number, string, string]> = [
  ["Headline KPIs", 11.18, "11.18 s", "1.59 s"],
  ["Overview cube, 2,508 cells", 1.81, "1.81 s", "1.33 s"],
  ["Rules by band", 1.34, "1.34 s", "0.95 s"],
  ["Merchant category", 1.62, "1.62 s", "0.97 s"],
];

const Panel: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <div>
      <div
        style={{
          fontFamily: font.mono,
          fontSize: 13,
          letterSpacing: 2.4,
          textTransform: "uppercase",
          color: "#8FBF6A",
          marginBottom: 26,
        }}
      >
        how long the page takes to answer
      </div>
      {QUERIES.map(([label, cold, coldS, warmS], i) => {
        const p = stagger(frame, fps, T_PANEL + 8, i);
        const g = barGrow(frame, T_PANEL + 14, i);
        return (
          <div key={label} style={{ marginBottom: 24, opacity: p }}>
            <div style={{ fontFamily: font.sans, fontSize: 18, color: "#F2F8EC" }}>{label}</div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 9 }}>
              <div
                style={{
                  height: 10,
                  width: (cold / 11.18) * 250 * g,
                  borderRadius: 5,
                  background: i === 0 ? c.amber : c.green,
                  opacity: 0.85,
                }}
              />
              <span style={{ fontFamily: font.mono, fontSize: 16, color: "rgba(238,246,230,.8)" }}>
                {coldS}
              </span>
              <span style={{ fontFamily: font.mono, fontSize: 16, color: "#A8D98A" }}>
                {"→ " + warmS}
              </span>
            </div>
          </div>
        );
      })}
      <div
        style={{
          fontFamily: font.serifItalic,
          fontStyle: "italic",
          fontSize: 21,
          color: "#A8D98A",
          lineHeight: 1.36,
          marginTop: 20,
        }}
      >
        The eleven seconds is Direct Lake transcoding the fact's columns once. After that, every
        page is a one-second question against fifty million rows.
      </div>
    </div>
  );
};

export const S9ReportSix: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  /* the other three pages, filed in behind the panel rather than given
     eighteen seconds of their own */
  const rest = move(frame, T_PANEL + 40, "stripBack");

  return (
    <Room at={0}>
      <SixBeatPage
        src="report-overview.png"
        iw={REPORT_IW}
        ih={REPORT_IH}
        bw={BW}
        bh={BH}
        cards={OVERVIEW}
        at={2}
        clearAt={T_CLEAR}
        rebuildAt={T_REBUILD}
        order={["title", "kpis", "months", "firings", "channel", "composition", "chips"]}
        sweepAt={T_SWEEP}
        explodeAt={T_EXPLODE}
        explodeUntil={T_CLOSE}
        spread={0.2}
        seed="ov"
        claim={
          <>
            Every page is{" "}
            <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", color: "#A8D98A" }}>
              a single visual.
            </span>
          </>
        }
        claimSub={<>One measure. One renderer. A click never queries the model again.</>}
        holds={[
          {
            at: 384,
            id: "kpis",
            label: (
              <>
                It states its own denominator. 49,406,792 of 49,406,792 in scope, so a filtered
                page can never be mistaken for the whole population.
              </>
            ),
          },
          {
            at: 448,
            id: "firings",
            label: (
              <>
                A firing is not an alert, and the card prints that underneath itself. The two differ
                by a factor of 45.8.
              </>
            ),
          },
        ]}
        panelAt={T_PANEL}
        panel={<Panel />}
      />

      {/* the remaining three pages, as a filed stack */}
      {rest > 0.01 ? (
        <div
          style={{
            position: "absolute",
            left: 64,
            bottom: 52,
            display: "flex",
            gap: 14,
            opacity: rest,
          }}
        >
          {(["report-rules.png", "report-risk.png", "report-guide.png"] as const).map((src, i) => {
            const p = stagger(frame, fps, T_PANEL + 44, i);
            const w = 208;
            return (
              <div
                key={src}
                style={{
                  width: w,
                  height: Math.round((w / REPORT_IW) * REPORT_IH),
                  borderRadius: 6,
                  overflow: "hidden",
                  background: "#fff",
                  opacity: p,
                  transform: `translateY(${(1 - p) * 20}px)`,
                  boxShadow: "0 14px 34px rgba(0,0,0,.42)",
                }}
              >
                <Img src={staticFile(src)} style={{ width: "100%", height: "100%", display: "block" }} />
              </div>
            );
          })}
          <div
            style={{
              alignSelf: "flex-end",
              paddingBottom: 6,
              fontFamily: font.mono,
              fontSize: 13,
              letterSpacing: 1.8,
              textTransform: "uppercase",
              color: "rgba(238,246,230,.6)",
              maxWidth: 200,
              lineHeight: 1.5,
            }}
          >
            three more pages. the last one is a guide, and its last section is called what this
            cannot do.
          </div>
        </div>
      ) : null}
    </Room>
  );
};
