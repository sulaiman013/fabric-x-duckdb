/**
 * The poster frame.
 *
 * Not a lucky grab from the timeline. A thumbnail has one job, which is to be
 * read at 320px wide in a feed, and a frame that works at full size usually
 * does not survive that. So this is composed for the small size: two lines of
 * claim at a size that still reads when the image is a thumb, the real report
 * page angled behind it so the thing being claimed about is visible, and the
 * four measured figures along the bottom.
 *
 * Rendered with `npx remotion still src/index.ts Thumbnail out/v6-thumb.png`.
 */
import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { c, font } from "./theme";

const FIGURES: Array<[string, string]> = [
  ["49,406,792", "rows served"],
  ["12.8 min", "full rebuild"],
  ["$0.27", "per rebuild"],
  ["36 / 36", "checks"],
];

export const Thumbnail: React.FC = () => (
  <AbsoluteFill style={{ background: "#0C110A", overflow: "hidden" }}>
    {/* the room */}
    <AbsoluteFill
      style={{
        background: "radial-gradient(130% 110% at 28% 34%, #26331F 0%, #161D14 52%, #0A0F08 100%)",
      }}
    />

    {/* the artifact, angled, so the claim has something to be about */}
    <div
      style={{
        position: "absolute",
        right: -400,
        top: 118,
        width: 1460,
        height: 821,
        transform: "perspective(2200px) rotateY(-19deg) rotateX(5deg) rotateZ(-2deg)",
        borderRadius: 12,
        overflow: "hidden",
        boxShadow: "0 50px 130px rgba(0,0,0,.72)",
        opacity: 0.95,
      }}
    >
      <Img
        src={staticFile("report-overview.png")}
        style={{ width: "100%", height: "100%", display: "block" }}
      />
    </div>

    {/* it must not compete with the type on the left */}
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(100deg, rgba(10,15,8,.98) 0%, rgba(10,15,8,.96) 44%, rgba(10,15,8,.52) 68%, rgba(10,15,8,.04) 90%)",
      }}
    />

    <div style={{ position: "absolute", left: 104, top: 168, width: 1080 }}>
      <div
        style={{
          fontFamily: font.mono,
          fontSize: 25,
          letterSpacing: 3.6,
          textTransform: "uppercase",
          color: "#8FBF6A",
          marginBottom: 34,
        }}
      >
        postgres &middot; fabric &middot; duckdb &middot; direct lake
      </div>

      <div style={{ fontFamily: font.serif, fontSize: 118, color: "#F4FAEE", lineHeight: 1.02 }}>
        Fifty million rows.
      </div>
      <div
        style={{
          fontFamily: font.serifItalic,
          fontStyle: "italic",
          fontSize: 118,
          color: "#A8D98A",
          lineHeight: 1.06,
        }}
      >
        Twenty-seven cents.
      </div>

      <div
        style={{
          fontFamily: font.sans,
          fontSize: 31,
          color: "rgba(238,246,230,.76)",
          marginTop: 30,
          lineHeight: 1.4,
          maxWidth: 880,
        }}
      >
        One on-premises table, mirrored into Fabric and transformed by DuckDB on a Python
        notebook. No import copy, no refresh schedule.
      </div>
    </div>

    {/* the figures, which are the reason to believe the claim */}
    <div style={{ position: "absolute", left: 104, bottom: 92, display: "flex", gap: 80 }}>
      {FIGURES.map(([v, l]) => (
        <div key={l}>
          <div
            style={{
              fontFamily: font.mono,
              fontWeight: 700,
              fontSize: 52,
              color: "#F4FAEE",
              fontVariantNumeric: "tabular-nums",
              lineHeight: 1,
            }}
          >
            {v}
          </div>
          <div
            style={{
              fontFamily: font.mono,
              fontSize: 20,
              letterSpacing: 2.4,
              textTransform: "uppercase",
              color: "#8FBF6A",
              marginTop: 14,
            }}
          >
            {l}
          </div>
        </div>
      ))}
    </div>

    <div
      style={{
        position: "absolute",
        left: 104,
        bottom: 42,
        fontFamily: font.mono,
        fontSize: 20,
        letterSpacing: 2.4,
        color: "rgba(238,246,230,.5)",
      }}
    >
      github.com/sulaiman013/fabric-x-duckdb
    </div>

    {/* a hairline so the poster has an edge rather than bleeding to black */}
    <AbsoluteFill
      style={{ border: `1px solid ${c.greenLine}22`, pointerEvents: "none" }}
    />
  </AbsoluteFill>
);
