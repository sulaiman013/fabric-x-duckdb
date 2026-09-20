/**
 * Scene 7, the payoff.
 *
 * Showing four page thumbnails explains nothing: at 1080 tall they are
 * unreadable and the viewer learns only that a report exists. So this scene
 * zooms into the individual visuals and says what each one is for. The crop
 * rectangles are in the source images' own pixel space (4258 x 2394), so the
 * zoom is a real crop of the real capture rather than a redrawn mock-up.
 */
import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";
import { Paper, Display, Line, Stage, ramp } from "../components/Primitives";
import { Icon } from "../components/Icon";
import { c, font } from "../theme";

const IMG_W = 4258;
const IMG_H = 2394;

type Beat = {
  file: string;
  /** crop in source pixels: x, y, w, h */
  crop: [number, number, number, number];
  page: string;
  title: string;
  body: string;
  at: number;
  dur: number;
};

const BEATS: Beat[] = [
  {
    file: "report-overview.png",
    crop: [40, 380, 4180, 300],
    page: "Overview",
    title: "The KPI strip states its own denominator",
    body: "49,406,792 of 49,406,792 in scope. A 2.88% alert rate, the RM 1.5b behind it, and the 28.5 analyst-years it implies. A filtered page can never be mistaken for the whole population.",
    at: 0,
    dur: 74,
  },
  {
    file: "report-overview.png",
    crop: [40, 690, 2700, 900],
    page: "Overview",
    title: "Transactions by month, stacked by risk band",
    body: "31 months. The stub bar on the left is rows whose date never parsed: shown, not silently dropped, because that is what the data contains.",
    at: 74,
    dur: 70,
  },
  {
    file: "report-overview.png",
    crop: [2740, 1620, 1480, 740],
    page: "Overview",
    title: "Rule firings, with the caveat printed underneath",
    body: "A firing is not an alert. A firing contributes to a score; an alert is the score crossing the band. The two differ by a factor of 45, so the page says so rather than letting the reader assume.",
    at: 144,
    dur: 74,
  },
  {
    file: "report-rules.png",
    crop: [230, 500, 2080, 700],
    page: "Rule effectiveness",
    title: "Seven rules, by what they actually fire",
    body: "Weight and volume are different things and the table shows both, so a rule cannot hide behind either. declined fires 25m times at weight 10; velocity fires 865k times at weight 30.",
    at: 218,
    dur: 74,
  },
  {
    file: "report-rules.png",
    crop: [2300, 1300, 1920, 780],
    page: "Rule effectiveness",
    title: "What a threshold costs, in people",
    body: "At cut-off 40 you raise 7.1m alerts and need 57 analysts. At 60, 1.4m and 11. At 80, 184k and one. This is the decision the whole pipeline exists to support.",
    at: 292,
    dur: 84,
  },
  {
    file: "report-risk.png",
    crop: [2090, 500, 2050, 800],
    page: "Risk and exposure",
    title: "The dirt stays visible on purpose",
    body: "The currency list holds 458, NA and #N/A beside USD and MYR. This is a 100-column text extract, and a report that hid its own unreadable inputs would be lying about them.",
    at: 376,
    dur: 76,
  },
];

const TOTAL_BEATS = BEATS[BEATS.length - 1].at + BEATS[BEATS.length - 1].dur;

/** A real crop of a real capture, scaled to fill the frame box. */
const Crop: React.FC<{ beat: Beat; boxW: number; boxH: number }> = ({ beat, boxW, boxH }) => {
  const frame = useCurrentFrame();
  const [cx, cy, cw, ch] = beat.crop;
  // COVER the box with the crop, so the named visual fills the frame rather
  // than sitting inside it with its neighbours showing around the edges
  const k = Math.max(boxW / cw, boxH / ch);
  const t = Math.max(0, Math.min(frame - beat.at, beat.dur));
  const push = 1 + t * 0.00055;
  const scale = k * push;
  return (
    <div
      style={{
        width: boxW,
        height: boxH,
        overflow: "hidden",
        borderRadius: 14,
        border: `1px solid ${c.border}`,
        background: c.white,
        boxShadow: "0 2px 6px rgba(22,29,17,.06), 0 24px 56px rgba(22,29,17,.10)",
        position: "relative",
      }}
    >
      <Img
        src={staticFile(beat.file)}
        style={{
          position: "absolute",
          width: IMG_W * scale,
          height: IMG_H * scale,
          left: boxW / 2 - (cx + cw / 2) * scale,
          top: boxH / 2 - (cy + ch / 2) * scale,
          maxWidth: "none",
        }}
      />
    </div>
  );
};

const BeatPanel: React.FC<{ beat: Beat }> = ({ beat }) => {
  const frame = useCurrentFrame();
  const inP = ramp(frame, [beat.at, beat.at + 16]);
  const outP = 1 - ramp(frame, [beat.at + beat.dur - 12, beat.at + beat.dur + 2]);
  const o = inP * outP;
  if (o <= 0.001) return null;

  return (
    <AbsoluteFill
      style={{
        padding: "148px 100px 88px",
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        gap: 50,
        opacity: o,
      }}
    >
      <div style={{ width: 520, transform: `translateY(${(1 - inP) * 20}px)` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Icon name="report" size={22} />
          <span
            style={{
              fontFamily: font.mono,
              fontSize: 14,
              letterSpacing: 2.2,
              textTransform: "uppercase",
              color: c.muted,
              fontWeight: 600,
            }}
          >
            {beat.page}
          </span>
        </div>
        <div
          style={{
            fontFamily: font.serif,
            fontSize: 46,
            lineHeight: 1.12,
            color: c.ink,
            marginTop: 16,
          }}
        >
          {beat.title}
        </div>
        <div
          style={{
            fontFamily: font.sans,
            fontSize: 23,
            lineHeight: 1.5,
            color: c.body,
            marginTop: 18,
          }}
        >
          {beat.body}
        </div>
      </div>
      <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
        <Crop beat={beat} boxW={1130} boxH={700} />
      </div>
    </AbsoluteFill>
  );
};

export const S7Report: React.FC = () => {
  const frame = useCurrentFrame();
  const INTRO = 42;
  const introOut = 1 - ramp(frame, [INTRO - 14, INTRO + 4]);
  const closeAt = INTRO + TOTAL_BEATS;
  const close = ramp(frame, [closeAt - 10, closeAt + 22]);

  return (
    <Paper drift={2400}>
      <Stage n="06" label="The answer" at={0} />

      <AbsoluteFill
        style={{ padding: "0 110px", justifyContent: "center", opacity: introOut }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 18, marginBottom: 26 }}>
          <Icon name="powerbi" size={54} />
          <Icon name="semantic" size={50} />
        </div>
        <Display text="Four pages. One visual each." at={4} size={80} italicFrom={2} />
        <div style={{ height: 20 }} />
        <Line at={18} size={28} color={c.muted} style={{ maxWidth: 1180 }}>
          Each page is a single HTML visual driven by one DAX measure that ships
          its own cube and its own renderer. Every click re-aggregates in the
          browser and never queries the model again.
        </Line>
      </AbsoluteFill>

      {BEATS.map((b) => (
        <BeatPanel key={`${b.file}-${b.at}`} beat={{ ...b, at: b.at + INTRO }} />
      ))}

      <AbsoluteFill
        style={{
          padding: "0 110px",
          alignItems: "center",
          justifyContent: "center",
          opacity: close,
        }}
      >
        <Display
          text="Monitoring becomes a staffing decision."
          at={closeAt + 6}
          size={72}
          italicFrom={2}
          style={{ justifyContent: "center", textAlign: "center" }}
        />
      </AbsoluteFill>
    </Paper>
  );
};
