/**
 * The motion library.
 *
 * Nine named moves, each with the duration the guide gives it. The point of
 * naming them is that a scene no longer invents its own timing: it says which
 * move it is using, and the move decides how long it takes. That is what makes
 * twelve scenes feel like one piece.
 *
 *   count-up         number rises to its value          0.8 s
 *   bar-grow         bars rise one by one               0.4 s each
 *   highlight-sweep  a band travels across a row         1.2 s
 *   zoom-to-kpi      the camera lands on one card        0.6 s
 *   line-draw        a path draws itself                 1.0 s
 *   ring-fill        a ring closes to its share          0.9 s
 *   card-stagger     cards return, one after another     0.15 s apart
 *   strip-back       chrome slides away                  0.5 s
 *   cursor-click     a cursor moves and presses          0.7 s
 *
 * v4's moves ran two to three seconds each. Against this library that is not
 * slow-and-considered, it is one move where there should have been three, and
 * it is why the film needed twenty seconds to make a point the guide makes in
 * seven.
 */
import { interpolate, spring, Easing } from "remotion";
import { EASE_OUT, FPS } from "../theme";

const ease = Easing.bezier(...EASE_OUT);

/** seconds to frames, at the film's own rate */
export const s = (sec: number) => Math.round(sec * FPS);

/** every duration in the library, in frames */
export const D = {
  countUp: s(0.8), // 24
  barGrow: s(0.4), // 12, per bar
  highlightSweep: s(1.2), // 36
  zoomToKpi: s(0.6), // 18
  lineDraw: s(1.0), // 30
  ringFill: s(0.9), // 27
  cardStagger: s(0.15), // 5, between cards
  stripBack: s(0.5), // 15
  cursorClick: s(0.7), // 21
} as const;

export type MoveName = keyof typeof D;

/**
 * A move: 0 before it starts, 1 once it is done, eased in between.
 *
 * Everything in the film is built out of this, so changing a duration in D
 * changes it everywhere it is used rather than in nine hand-tuned places.
 */
export const move = (frame: number, at: number, name: MoveName, mul = 1) =>
  interpolate(frame, [at, at + D[name] * mul], [0, 1], {
    easing: ease,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

/** the same, but arriving like an object rather than a value */
export const land = (frame: number, fps: number, at: number, name: MoveName = "zoomToKpi") =>
  spring({
    frame: frame - at,
    fps,
    durationInFrames: D[name],
    config: { damping: 18, stiffness: 100, mass: 0.7 },
  });

/** card n of a staggered set: when it starts, and how far along it is */
export const stagger = (frame: number, fps: number, at: number, i: number) =>
  land(frame, fps, at + i * D.cardStagger, "zoomToKpi");

/** count-up: a number that rises to its value and stops */
export const countUp = (frame: number, at: number, to: number, mul = 1) =>
  move(frame, at, "countUp", mul) * to;

/** bar n of a set that rises one by one */
export const barGrow = (frame: number, at: number, i: number) =>
  move(frame, at + i * D.barGrow, "barGrow");

/**
 * highlight-sweep: a band travelling left to right across a width.
 * Returns the band's centre, and how lit a point at x is as it passes.
 */
export const sweep = (frame: number, at: number, width: number) => {
  const p = move(frame, at, "highlightSweep");
  const x = p * width;
  return {
    p,
    x,
    lit: (px: number, falloff = 110) => Math.max(0, 1 - Math.abs(px - x) / falloff),
    passed: (px: number) => px < x,
    running: p > 0.001 && p < 0.999,
  };
};

/** ring-fill: a ring closing to its share, for a dasharray */
export const ringFill = (frame: number, at: number, share: number, circumference: number) => {
  const p = move(frame, at, "ringFill");
  return circumference * (1 - p * share);
};

/** strip-back: chrome sliding away, returning its offset and opacity */
export const stripBack = (frame: number, at: number, distance: number) => {
  const p = move(frame, at, "stripBack");
  return { offset: p * distance, opacity: 1 - p };
};
