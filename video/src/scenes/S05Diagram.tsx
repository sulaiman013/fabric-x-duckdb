/**
 * Scene 5. The architecture, as a live document. 720f / 24s.
 *
 * This is real captured footage of architecture-diagram/index.html, driven
 * through its own API by scripts/capture_arch.py. v2 redrew a lookalike in
 * React, which is the same as not showing it at all.
 *
 * Layout note. The first cut stacked a title, the browser and a caption in a
 * flex column that was taller than the frame, so flex quietly shrank the
 * browser and clipped 90px off the bottom of the capture. The header is one
 * row now, the browser carries flexShrink: 0 so it can never be squeezed
 * silently again, and verify_film.py asserts the stack fits inside 1080.
 */
import React from "react";
import { AbsoluteFill, OffthreadVideo, Sequence, staticFile, useCurrentFrame } from "remotion";
import { Paper, Display, ramp } from "../components/Primitives";
import { Browser } from "../components/Blocks";
import { c, font } from "../theme";

const VIDEO_FROM = 60;
/** frames actually present in public/arch.mp4, checked by scripts/verify_film.py */
export const VIDEO_FRAMES = 648;

/** Height budget, asserted by the verification pass. */
export const PAD_TOP = 96;
export const PAD_BOTTOM = 44;
export const HEADER_H = 70;
export const BROWSER_BAR = 54;

export const BOX_W = 1450;
/** kept at the capture's own 16:9 so the footage is never distorted */
export const BOX_H = Math.round((BOX_W / 1920) * 1080);

/** Captions timed to the beats the capture script drives. */
const CAPTIONS: Array<{ at: number; t: string }> = [
  { at: VIDEO_FROM + 10, t: "the board draws itself, and the packets are the flow" },
  { at: VIDEO_FROM + 150, t: "every component opens: this one is the notebook's own evidence" },
  { at: VIDEO_FROM + 270, t: "the second view is what the notebook actually does" },
  { at: VIDEO_FROM + 410, t: "the seven rules, with the counts the build recorded" },
  { at: VIDEO_FROM + 510, t: "and the whole page turns over to the written explanation" },
];

export const S05Diagram: React.FC = () => {
  const frame = useCurrentFrame();
  const caption = [...CAPTIONS].reverse().find((x) => frame >= x.at);

  return (
    <Paper drift={1700}>
      <AbsoluteFill
        style={{ padding: `${PAD_TOP}px 0 ${PAD_BOTTOM}px`, alignItems: "center" }}
      >
        {/* one header row: the stage label and title on the left, the rolling
            caption on the right. Stacking them was what overflowed the frame. */}
        <div
          style={{
            width: BOX_W,
            height: HEADER_H,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 40,
            flex: "0 0 auto",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div
              style={{
                fontFamily: font.mono,
                fontSize: 14,
                fontWeight: 700,
                color: c.greenInk,
                background: c.greenBg,
                border: `1px solid ${c.greenLine}`,
                borderRadius: 999,
                padding: "5px 11px",
                letterSpacing: 1.6,
                opacity: ramp(frame, [0, 14]),
                flex: "0 0 auto",
              }}
            >
              04
            </div>
            <Display text="Not a picture. A page you can click." at={4} size={44} italicFrom={3} />
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              flex: "0 0 auto",
              maxWidth: 620,
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: 999,
                background: c.green,
                flex: "0 0 auto",
                opacity: ramp(frame, [VIDEO_FROM, VIDEO_FROM + 14]),
              }}
            />
            {caption ? (
              <div
                key={caption.at}
                style={{
                  fontFamily: font.mono,
                  fontSize: 17,
                  letterSpacing: 1.1,
                  color: c.muted,
                  textAlign: "right",
                  lineHeight: 1.3,
                  opacity: ramp(frame, [caption.at, caption.at + 16]),
                  transform: `translateY(${ramp(frame, [caption.at, caption.at + 20], [8, 0])}px)`,
                }}
              >
                {caption.t}
              </div>
            ) : null}
          </div>
        </div>

        <Browser
          at={VIDEO_FROM - 22}
          url="architecture-diagram/index.html"
          w={BOX_W}
          h={BOX_H}
          style={{ flex: "0 0 auto" }}
        >
          <Sequence from={VIDEO_FROM} durationInFrames={VIDEO_FRAMES} name="capture">
            <OffthreadVideo
              src={staticFile("arch.mp4")}
              style={{ width: BOX_W, height: BOX_H, display: "block", objectFit: "fill" }}
              muted
            />
          </Sequence>
        </Browser>
      </AbsoluteFill>
    </Paper>
  );
};
