/**
 * Scene 7. The architecture page, in six beats. 420f / 14s.
 *
 * v4 gave this 690 frames: a live capture, a three-card 3D fan that turned,
 * then an exploded view, then four holds. Handsome, and it took 23 seconds to
 * say two things. The six beats say the same two things in fourteen, because
 * clearing the page and rebuilding it names the two halves in the order the
 * argument needs them, rather than separating everything at once and hoping
 * the eye picks the right piece.
 */
import React from "react";
import { useCurrentFrame } from "remotion";
import { SixBeatPage } from "../motion/SixBeat";
import { PIPELINE, ARCH_IW, ARCH_IH } from "./cards";
import { Room } from "../motion/Theatre";
import { stagger } from "../motion/library";
import { font } from "../theme";
import { useVideoConfig } from "remotion";

/* Both captures are 16:9 (4258x2394 and 3840x2160), so the page IS the
   frame. No dark border around it. */
const BW = 1920;
const BH = 1080;

const T_CLEAR = 62;
const T_REBUILD = 150;
const T_SWEEP = 176;
const T_EXPLODE = 224;
const T_CLOSE = 290;
const T_PANEL = 470;

const Panel: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const rows: Array<[string, React.ReactNode]> = [
    ["49,406,792", "rows in the gold fact"],
    ["12.8 min", "transformation, end to end"],
    ["$0.27", "total capacity cost"],
    ["36 / 36", "acceptance checks, 1 skipped"],
  ];
  return (
    <div>
      <div
        style={{
          fontFamily: font.mono,
          fontSize: 13,
          letterSpacing: 2.4,
          textTransform: "uppercase",
          color: "#8FBF6A",
          marginBottom: 28,
        }}
      >
        measured, not asserted
      </div>
      {rows.map(([v, l], i) => {
        const p = stagger(frame, fps, T_PANEL + 8, i);
        return (
          <div key={l as string} style={{ marginBottom: 30, opacity: p, transform: `translateY(${(1 - p) * 14}px)` }}>
            <div
              style={{
                fontFamily: font.mono,
                fontWeight: 700,
                fontSize: 38,
                color: "#F2F8EC",
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {v}
            </div>
            <div
              style={{
                fontFamily: font.mono,
                fontSize: 13,
                letterSpacing: 1.6,
                textTransform: "uppercase",
                color: "rgba(238,246,230,.6)",
                marginTop: 8,
              }}
            >
              {l}
            </div>
          </div>
        );
      })}
      <div
        style={{
          fontFamily: font.serifItalic,
          fontStyle: "italic",
          fontSize: 22,
          color: "#A8D98A",
          lineHeight: 1.36,
          marginTop: 10,
        }}
      >
        Each one read from the run's evidence file rather than typed onto the page.
      </div>
    </div>
  );
};

export const S7ArchSix: React.FC = () => {
  return (
    <Room at={0}>
      <SixBeatPage
        src="arch/pipeline.png"
        iw={ARCH_IW}
        ih={ARCH_IH}
        bw={BW}
        bh={BH}
        cards={PIPELINE}
        at={2}
        clearAt={T_CLEAR}
        rebuildAt={T_REBUILD}
        order={["head", "onprem", "fabric", "kpis"]}
        sweepAt={T_SWEEP}
        explodeAt={T_EXPLODE}
        explodeUntil={T_CLOSE}
        spread={0.2}
        seed="arch"
        claim={
          <>
            Not a picture.{" "}
            <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", color: "#A8D98A" }}>
              A page you can click.
            </span>
          </>
        }
        claimSub={<>It ships in the repo. The acceptance pass re-measures every figure on it.</>}
        holds={[
          {
            at: 332,
            id: "onprem",
            label: (
              <>
                On-premises. A seeder and a change feed, and both of them push outward. That is the
                only reason a database on localhost can be mirrored at all.
              </>
            ),
          },
          {
            at: 396,
            id: "fabric",
            label: (
              <>
                On capacity. Mirror, shortcut, a DuckDB notebook, a V-Order write, Direct Lake.
                Nothing reaches back across the line.
              </>
            ),
          },
        ]}
        panelAt={T_PANEL}
        panel={<Panel />}
      />
    </Room>
  );
};
