/**
 * Scene 9. The report, page by page. 900f / 30s.
 *
 * This is the scene v2 broke. It cover-fitted guessed crop boxes, so a strip
 * 14 times wider than it is tall was blown up until a tenth of it filled the
 * frame. Two rules fix it:
 *
 *   1. Every crop below is measured off the card borders in the capture's own
 *      pixel space, 4258 x 2394. Nothing is guessed.
 *   2. Every crop is CONTAIN fitted, never cover, so the whole named visual is
 *      always in frame. verify_film.py asserts both.
 *
 * Each page also opens whole, so the viewer sees it is a page before being
 * shown one piece of it.
 */
import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";
import { Paper, Display, Line, Stage, ramp } from "../components/Primitives";
import { Icon } from "../components/Icon";
import { c, font } from "../theme";

export const IMG_W = 4258;
export const IMG_H = 2394;

/** A full-width crop box, used for anything wider than it is tall. */
const WIDE_W = 1700;
const WIDE_H = 620;
/** A side-by-side box, used for portrait crops. */
const TALL_W = 1050;
const TALL_H = 780;

export type Shot =
  | { kind: "page"; file: string; page: string; dur: number }
  | {
      kind: "crop";
      file: string;
      page: string;
      /** x, y, w, h in the capture's own pixels */
      crop: [number, number, number, number];
      title: string;
      body: string;
      dur: number;
    };

const INTRO = 50;

/**
 * Exported so the verification pass can assert every crop is inside the source
 * image and that nothing is scaled beyond contain.
 */
export const SHOTS: Shot[] = [
  { kind: "page", file: "report-overview.png", page: "Overview", dur: 37 },
  {
    kind: "crop",
    file: "report-overview.png",
    page: "Overview",
    crop: [28, 394, 2120, 240],
    title: "The strip states its own denominator",
    body: "49,406,792 of 49,406,792 in scope, 100%. A filtered page can never be mistaken for the whole population.",
    dur: 100,
  },
  {
    kind: "crop",
    file: "report-overview.png",
    page: "Overview",
    crop: [36, 668, 2684, 906],
    title: "Thirty-one months, stacked by risk band",
    body: "The stub bar on the far left is every row whose date never parsed. Shown, not quietly dropped, because that is what the data contains.",
    dur: 100,
  },
  {
    kind: "crop",
    file: "report-overview.png",
    page: "Overview",
    crop: [2752, 1616, 1478, 740],
    title: "A firing is not an alert",
    body: "The card prints that underneath itself. The two differ by a factor of 45.8, so the page says so rather than letting the reader assume.",
    dur: 100,
  },
  { kind: "page", file: "report-rules.png", page: "Rule effectiveness", dur: 37 },
  {
    kind: "crop",
    file: "report-rules.png",
    page: "Rule effectiveness",
    crop: [44, 558, 2292, 886],
    title: "Weight and volume are different things",
    body: "So both are on the table and a rule cannot hide behind either. declined fires 25m times at weight 10. velocity fires 865k times at weight 30.",
    dur: 100,
  },
  {
    kind: "crop",
    file: "report-rules.png",
    page: "Rule effectiveness",
    crop: [2364, 1474, 1848, 886],
    title: "What a threshold costs, in people",
    body: "Most monitoring reports stop at the alert count. This one carries the staffing consequence in the same table, because that is the decision being made.",
    dur: 100,
  },
  { kind: "page", file: "report-risk.png", page: "Risk and exposure", dur: 37 },
  {
    kind: "crop",
    file: "report-risk.png",
    page: "Risk and exposure",
    crop: [2130, 558, 2100, 890],
    title: "The dirt stays visible on purpose",
    body: "The currency list holds 458, NA and #N/A beside USD and MYR. The header says RM 89m sits in currencies that cannot be resolved.",
    dur: 100,
  },
  { kind: "page", file: "report-guide.png", page: "Guide", dur: 37 },
  {
    kind: "crop",
    file: "report-guide.png",
    page: "Guide",
    crop: [20, 300, 490, 630],
    title: "Seven sections, shipped inside the report",
    body: "So the explanation cannot go stale beside it. The last section is called What this cannot do.",
    dur: 100,
  },
];

/** Cumulative start frame of each shot. Exported for the verification pass. */
export const SHOT_AT: number[] = SHOTS.reduce<number[]>((acc, s, i) => {
  acc.push(i === 0 ? INTRO : acc[i - 1] + SHOTS[i - 1].dur);
  return acc;
}, []);

export const SCENE_END = SHOT_AT[SHOT_AT.length - 1] + SHOTS[SHOTS.length - 1].dur;

/** true when the crop should sit beside its text rather than under it */
export const isTall = (crop: [number, number, number, number]) => crop[2] / crop[3] < 1.2;

/**
 * A real crop of a real capture, CONTAIN fitted into the box.
 *
 * Math.min, not Math.max. Cover is what over-zoomed v2: with a box of aspect
 * 1.6 and a crop of aspect 8.8, cover scales by the height ratio and throws
 * away 90% of the width.
 */
const Crop: React.FC<{
  file: string;
  crop: [number, number, number, number];
  boxW: number;
  boxH: number;
  at: number;
  dur: number;
}> = ({ file, crop, boxW, boxH, at, dur }) => {
  const frame = useCurrentFrame();
  const [cx, cy, cw, ch] = crop;
  const k = Math.min(boxW / cw, boxH / ch);
  const t = Math.max(0, Math.min(frame - at, dur));
  // a very slow push, well under 2% over the whole shot, so the frame breathes
  // without the crop creeping outside the card it was measured from
  const scale = k * (1 + t * 0.00018);
  const w = cw * scale;
  const h = ch * scale;
  const p = ramp(frame, [at, at + 18]);

  return (
    <div
      style={{
        width: w,
        height: h,
        overflow: "hidden",
        borderRadius: 12,
        border: `1px solid ${c.border}`,
        background: c.white,
        boxShadow: "0 2px 6px rgba(22,29,17,.06), 0 24px 56px rgba(22,29,17,.10)",
        position: "relative",
        opacity: p,
        transform: `translateY(${(1 - p) * 16}px)`,
      }}
    >
      <Img
        src={staticFile(file)}
        style={{
          position: "absolute",
          width: IMG_W * scale,
          height: IMG_H * scale,
          left: -cx * scale,
          top: -cy * scale,
          maxWidth: "none",
        }}
      />
    </div>
  );
};

const PageLabel: React.FC<{ page: string; at: number }> = ({ page, at }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
    <Icon name="report" size={22} />
    <span
      style={{
        fontFamily: font.mono,
        fontSize: 15,
        letterSpacing: 2.2,
        textTransform: "uppercase",
        color: c.muted,
        fontWeight: 600,
      }}
    >
      {page}
    </span>
  </div>
);

const ShotPanel: React.FC<{ shot: Shot; at: number }> = ({ shot, at }) => {
  const frame = useCurrentFrame();
  const inP = ramp(frame, [at, at + 14]);
  const outP = 1 - ramp(frame, [at + shot.dur - 12, at + shot.dur + 2]);
  const o = inP * outP;
  if (o <= 0.002) return null;

  if (shot.kind === "page") {
    // the whole page, contained, so the viewer sees it is a page
    const k = Math.min(1560 / IMG_W, 876 / IMG_H);
    return (
      <AbsoluteFill
        style={{
          padding: "132px 0 70px",
          alignItems: "center",
          justifyContent: "center",
          opacity: o,
        }}
      >
        <div style={{ width: IMG_W * k, marginBottom: 16 }}>
          <PageLabel page={shot.page} at={at} />
        </div>
        <div
          style={{
            width: IMG_W * k,
            height: IMG_H * k,
            borderRadius: 12,
            overflow: "hidden",
            border: `1px solid ${c.border}`,
            boxShadow: "0 2px 6px rgba(22,29,17,.06), 0 26px 60px rgba(22,29,17,.12)",
            transform: `scale(${0.985 + inP * 0.015})`,
          }}
        >
          <Img
            src={staticFile(shot.file)}
            style={{ width: "100%", height: "100%", display: "block" }}
          />
        </div>
      </AbsoluteFill>
    );
  }

  const tall = isTall(shot.crop);

  if (tall) {
    return (
      <AbsoluteFill
        style={{
          padding: "150px 130px 90px",
          flexDirection: "row",
          alignItems: "center",
          gap: 60,
          opacity: o,
        }}
      >
        <div style={{ width: 620, transform: `translateY(${(1 - inP) * 16}px)` }}>
          <PageLabel page={shot.page} at={at} />
          <div
            style={{
              fontFamily: font.serif,
              fontSize: 46,
              lineHeight: 1.14,
              color: c.ink,
              marginTop: 16,
            }}
          >
            {shot.title}
          </div>
          <Line at={at + 8} size={25} style={{ marginTop: 18 }}>
            {shot.body}
          </Line>
        </div>
        <div style={{ flex: 1, display: "flex", justifyContent: "flex-start" }}>
          <Crop
            file={shot.file}
            crop={shot.crop}
            boxW={TALL_W}
            boxH={TALL_H}
            at={at}
            dur={shot.dur}
          />
        </div>
      </AbsoluteFill>
    );
  }

  // wide: the text sits in a band above and the crop gets the full width, which
  // is what keeps the axis labels legible
  return (
    <AbsoluteFill
      style={{
        padding: "128px 110px 70px",
        alignItems: "center",
        justifyContent: "center",
        opacity: o,
      }}
    >
      <div style={{ width: WIDE_W, transform: `translateY(${(1 - inP) * 14}px)` }}>
        <PageLabel page={shot.page} at={at} />
        <div
          style={{
            fontFamily: font.serif,
            fontSize: 46,
            lineHeight: 1.14,
            color: c.ink,
            marginTop: 12,
          }}
        >
          {shot.title}
        </div>
        <Line at={at + 8} size={24} style={{ marginTop: 12, maxWidth: 1560 }}>
          {shot.body}
        </Line>
      </div>
      <div
        style={{
          width: WIDE_W,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginTop: 34,
        }}
      >
        <Crop
          file={shot.file}
          crop={shot.crop}
          boxW={WIDE_W}
          boxH={WIDE_H}
          at={at}
          dur={shot.dur}
        />
      </div>
    </AbsoluteFill>
  );
};

export const S09Report: React.FC = () => {
  const frame = useCurrentFrame();
  const introOut = 1 - ramp(frame, [INTRO - 16, INTRO + 2]);

  return (
    <Paper drift={3300}>
      <div style={{ opacity: introOut }}>
        <Stage n="08" label="The answer" at={0} />
      </div>

      <AbsoluteFill
        style={{ padding: "0 130px", justifyContent: "center", opacity: introOut }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 18, marginBottom: 26 }}>
          <Icon name="powerbi" size={52} />
          <Icon name="semantic" size={48} />
        </div>
        <Display text="Four pages. One visual each." at={4} size={78} italicFrom={2} />
        <div style={{ height: 20 }} />
        <Line at={16} size={27} color={c.muted} style={{ maxWidth: 1240 }}>
          Every page is a single HTML visual driven by one DAX measure that ships
          its own cube and its own renderer. Every click re-aggregates in the
          browser and never queries the model again.
        </Line>
      </AbsoluteFill>

      {SHOTS.map((s, i) => (
        <ShotPanel key={`${s.kind}-${i}`} shot={s} at={SHOT_AT[i]} />
      ))}
    </Paper>
  );
};
