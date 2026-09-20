/**
 * The architecture, in a theatre. 690f / 23s.
 *
 * Four beats, the same treatment the report gets:
 *
 *   1. the page alive, so you see the wires draw and the packets ride
 *   2. all three views at once, fanned in 3D, and the set turns through them
 *   3. the pipeline view comes forward and pulls apart into its regions
 *   4. the camera holds on the two that carry the argument
 */
import React from "react";
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { ExplodedPage, Piece } from "../motion/Exploded";
import { Room, Marquee } from "../motion/Theatre";
import { ramp, pop } from "../motion/bits";
import { font } from "../theme";

const IW = 3840;
const IH = 2160;
const BW = 1440;
const BH = Math.round((BW / IW) * IH);

/** the pipeline view, in regions, measured off the 2x capture */
const PIPELINE: Piece[] = [
  { id: "head", rect: [110, 250, 3620, 250] },
  { id: "onprem", rect: [150, 540, 1400, 1120] },
  { id: "fabric", rect: [1610, 540, 2120, 1120] },
  { id: "kpis", rect: [150, 1720, 3580, 300] },
];

const T_LIVE = 0;
const LIVE_LEN = 168;
const T_FAN = 162;
const T_PAGE = 330;

const VIEWS = [
  { src: "arch/pipeline.png", label: "pipeline" },
  { src: "arch/transform.png", label: "transformation" },
  { src: "arch/explained.png", label: "explained" },
];

export const S9Arch: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const liveOut = 1 - ramp(frame, [T_FAN - 12, T_FAN + 6]);
  const fan = ramp(frame, [T_FAN, T_FAN + 40]);
  /* the set turns so each view faces front in turn */
  const turn = ramp(frame, [T_FAN + 52, T_PAGE - 30]) * 2;
  const fanOut = 1 - ramp(frame, [T_PAGE - 26, T_PAGE - 4]);
  const pageIn = ramp(frame, [T_PAGE - 10, T_PAGE + 8]);

  return (
    <Room at={0}>
      {/* 1. the page, alive */}
      {liveOut > 0.01 ? (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: liveOut }}>
          <div
            style={{
              width: BW,
              height: BH,
              borderRadius: 10,
              overflow: "hidden",
              boxShadow: "0 30px 80px rgba(0,0,0,.5)",
              background: "#fff",
              transform: `scale(${0.96 + pop(frame, fps, 2, { damping: 20, stiffness: 60 }) * 0.04})`,
            }}
          >
            <Sequence from={T_LIVE} durationInFrames={LIVE_LEN} name="live">
              <OffthreadVideo
                src={staticFile("arch.mp4")}
                style={{ width: BW, height: BH, display: "block", objectFit: "cover" }}
                muted
              />
            </Sequence>
          </div>
        </AbsoluteFill>
      ) : null}

      {/* 2. all three views, fanned, turning */}
      {fan > 0.01 && fanOut > 0.01 ? (
        <AbsoluteFill
          style={{
            alignItems: "center",
            justifyContent: "center",
            perspective: 2600,
            opacity: fan * fanOut,
          }}
        >
          <div style={{ position: "relative", width: 1, height: 1, transformStyle: "preserve-3d" }}>
            {VIEWS.map((v, i) => {
              /* a shallow arc: the front card is flat, its neighbours angle in */
              const slot = i - turn;
              const w = 1180;
              const h = Math.round((w / IW) * IH);
              const near = Math.max(0, 1 - Math.abs(slot) * 0.42);
              return (
                <div
                  key={v.src}
                  style={{
                    position: "absolute",
                    left: -w / 2,
                    top: -h / 2,
                    width: w,
                    height: h,
                    transform: `translate3d(${slot * 700}px, 0px, ${-Math.abs(slot) * 420}px)
                                rotateY(${-slot * 30}deg)`,
                    borderRadius: 10,
                    overflow: "hidden",
                    background: "#fff",
                    boxShadow: `0 30px ${60 + near * 40}px rgba(0,0,0,${0.35 + near * 0.2})`,
                    opacity: 0.42 + near * 0.58,
                    zIndex: Math.round(near * 10),
                  }}
                >
                  <Img
                    src={staticFile(v.src)}
                    style={{ width: "100%", height: "100%", display: "block" }}
                  />
                  <div
                    style={{
                      position: "absolute",
                      left: 0,
                      right: 0,
                      bottom: 0,
                      padding: "28px 0 14px",
                      textAlign: "center",
                      fontFamily: font.mono,
                      fontSize: 15,
                      letterSpacing: 2.4,
                      textTransform: "uppercase",
                      color: "#EEF6E6",
                      background: "linear-gradient(0deg, rgba(8,12,7,.92), rgba(8,12,7,0))",
                    }}
                  >
                    {v.label}
                  </div>
                </div>
              );
            })}
          </div>
        </AbsoluteFill>
      ) : null}

      {/* 3 and 4. the pipeline view comes forward and pulls apart */}
      {pageIn > 0.01 ? (
        <AbsoluteFill style={{ opacity: pageIn }}>
          <ExplodedPage
            src="arch/pipeline.png"
            iw={IW}
            ih={IH}
            bw={BW}
            bh={BH}
            pieces={PIPELINE}
            arriveAt={T_PAGE}
            explodeAt={T_PAGE + 64}
            explodeDur={46}
            spread={0.5}
            seed="arch"
            focus={[
              { at: T_PAGE, id: null },
              { at: T_PAGE + 122, id: null },
              { at: T_PAGE + 166, id: "onprem" },
              { at: T_PAGE + 214, id: "onprem" },
              { at: T_PAGE + 258, id: "fabric" },
              { at: T_PAGE + 306, id: "fabric" },
              { at: T_PAGE + 346, id: "kpis" },
            ]}
          />
        </AbsoluteFill>
      ) : null}

      {/* the header retires once the set fans out */}
      <div
        style={{
          position: "absolute",
          left: 96,
          top: 60,
          opacity: ramp(frame, [6, 30]) * (1 - ramp(frame, [T_FAN - 20, T_FAN])),
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
          architecture-diagram/index.html, in the repository
        </div>
        <div style={{ fontFamily: font.serif, fontSize: 48, color: "#EEF6E6", lineHeight: 1.06 }}>
          Not a picture.{" "}
          <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", color: "#A8D98A" }}>
            A page you can click.
          </span>
        </div>
      </div>

      <Marquee
        at={14}
        until={T_FAN - 14}
        kicker="live"
        title="The wires draw themselves, and the packets are the flow."
        body="It ships in the repository. Every figure on it is re-measured by the acceptance pass."
      />
      <Marquee
        at={T_FAN + 16}
        until={T_PAGE - 30}
        kicker="three views"
        title="The pipeline, what the notebook does, and the written explanation."
        body="The reasoning travels with the picture instead of living in someone's head."
      />
      <Marquee
        at={T_PAGE + 74}
        until={T_PAGE + 158}
        kicker="pulled apart"
        title="Two platforms, and the measurements underneath them."
        body="Everything on the left is on-premises. Everything on the right is Fabric. Nothing crosses inward."
      />
      <Marquee
        at={T_PAGE + 172}
        until={T_PAGE + 250}
        kicker="on-premises"
        title="One PostgreSQL table, a seeder, and a change feed."
        body="Both scripts push outward. That is the only reason a database on localhost can be mirrored at all."
      />
      <Marquee
        at={T_PAGE + 264}
        until={T_PAGE + 338}
        kicker="on capacity"
        title="Mirror, shortcut, DuckDB notebook, V-Order write, Direct Lake, report."
        body="The notebook card carries its own evidence: billed 4 CU, 770 s of work inside an 895 s session."
      />
      <Marquee
        at={T_PAGE + 352}
        kicker="measured, not asserted"
        title="49.4M rows. 12.8 minutes. 27 cents. 36 of 36 checks."
        body="Each one read from the run's own evidence file rather than typed onto the page."
      />
    </Room>
  );
};
