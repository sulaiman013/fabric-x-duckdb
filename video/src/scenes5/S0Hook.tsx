/**
 * Scene 0. The hook. 150f / 5s.
 *
 * The guide's before and after is a dashboard page that arrives, clears, and
 * has one claim land on the empty stage. v4 opened on the problem, which asks
 * a viewer to invest two minutes before seeing anything worth having. This
 * opens on the finished thing, which buys the right to spend the two minutes.
 *
 * Beats 01 and 02 only. The rest of the six is spent on the page itself,
 * later, once the claim has been earned.
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { SixBeatPage } from "../motion/SixBeat";
import { OVERVIEW, REPORT_IW, REPORT_IH } from "./cards";
import { Room } from "../motion/Theatre";
import { move } from "../motion/library";
import { font } from "../theme";

/* Both captures are 16:9 (4258x2394 and 3840x2160), so the page IS the
   frame. No dark border around it. */
const BW = 1920;
const BH = 1080;

export const S0Hook: React.FC = () => {
  const frame = useCurrentFrame();
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
        clearAt={42}
        rebuildAt={100000}
        claim={
          <>
            Fifty million rows.{" "}
            <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", color: "#A8D98A" }}>
              Twenty-seven cents.
            </span>
          </>
        }
        claimSub={<>A laptop table, to a Direct Lake report. Every figure measured.</>}
      />

      {/* the file it comes from, stated once, so the claim has an address */}
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 54 }}>
        <div
          style={{
            fontFamily: font.mono,
            fontSize: 14,
            letterSpacing: 2.6,
            textTransform: "uppercase",
            color: "#8FBF6A",
            opacity: move(frame, 104, "highlightSweep"),
          }}
        >
          github.com/sulaiman013/fabric-x-duckdb
        </div>
      </AbsoluteFill>
    </Room>
  );
};
