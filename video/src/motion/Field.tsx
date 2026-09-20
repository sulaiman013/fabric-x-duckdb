/**
 * The data field: fifty million rows as something you can actually look at.
 *
 * The v3 film said "50,000,001 rows" in large type and expected that to land.
 * It does not. A number is not a quantity until you see it as a texture, so
 * the field is a dense grid of cells that fills the frame, reveals as a
 * noise-ordered wave, and can then be operated on in view: scanned, scored,
 * thinned, reorganised.
 *
 * A few thousand cells are drawn. Underneath them sits a much finer static
 * weave (see Grain in bits.tsx) so the eye reads density rather than a count.
 */
import React from "react";
import { useCurrentFrame } from "remotion";
import { noise2D } from "@remotion/noise";
import { c } from "../theme";
import { ramp } from "./bits";

export type FieldTone = "raw" | "clean" | "dirty" | "alert";

/**
 * Tones carry an alpha as well as a colour, because a field where every state
 * is fully saturated reads as a candy grid rather than as data. Clean recedes
 * toward the paper, damage advances. Red is the only vivid tone and it stays
 * rare, so a failure is an event rather than a texture.
 */
const TONE: Record<FieldTone, { hex: string; a: number }> = {
  raw: { hex: "#B9CCA8", a: 0.66 },
  clean: { hex: "#8FBF6A", a: 0.42 },
  dirty: { hex: c.amber, a: 0.8 },
  alert: { hex: c.red, a: 0.95 },
};

export type FieldProps = {
  cols?: number;
  rows?: number;
  cell?: number;
  gap?: number;
  /** when the field starts appearing, and over how many frames */
  revealAt?: number;
  revealDur?: number;
  /**
   * A scan head sweeping left to right between these frames. Cells behind the
   * head are "processed" and take their processed tone.
   */
  scanAt?: number;
  scanDur?: number;
  /** share of processed cells that fail, drawn in the dirty tone */
  dirtyRate?: number;
  /** share of processed cells that go to the alert tone instead */
  alertRate?: number;
  /** cells matching this lift off and float away, used for the dedup beat */
  liftAt?: number;
  liftRate?: number;
  /** the whole field drifts, so a held frame is never frozen */
  drift?: boolean;
  seed?: string;
  style?: React.CSSProperties;
  /** reports the scan head position so a caller can put a counter on it */
  onScanX?: (x: number) => void;
};

export const fieldSize = (cols: number, rows: number, cell: number, gap: number) => ({
  w: cols * (cell + gap) - gap,
  h: rows * (cell + gap) - gap,
});

export const Field: React.FC<FieldProps> = ({
  cols = 58,
  rows = 30,
  cell = 26,
  gap = 4,
  revealAt = 0,
  revealDur = 46,
  scanAt,
  scanDur = 90,
  dirtyRate = 0,
  alertRate = 0,
  liftAt,
  liftRate = 0,
  drift = true,
  seed = "field",
  style,
}) => {
  const frame = useCurrentFrame();
  const { w, h } = fieldSize(cols, rows, cell, gap);

  // the scan head, in cell columns
  const scanP = scanAt === undefined ? 0 : ramp(frame, [scanAt, scanAt + scanDur]);
  const scanCol = scanP * cols;

  const cells: React.ReactNode[] = [];

  for (let r = 0; r < rows; r++) {
    for (let col = 0; col < cols; col++) {
      const i = r * cols + col;

      // reveal order: noise, so the field fills in organically rather than
      // sweeping like a progress bar
      const order = (noise2D(seed + "-order", col * 0.09, r * 0.09) + 1) / 2;
      const start = revealAt + order * revealDur * 0.75;
      const appear = ramp(frame, [start, start + 10]);
      if (appear <= 0.002) continue;

      // classification is deterministic per cell
      const roll = (noise2D(seed + "-roll", col * 0.31, r * 0.27) + 1) / 2;
      const processed = scanAt !== undefined && col < scanCol;
      let tone: FieldTone = "raw";
      if (processed) {
        if (roll < alertRate) tone = "alert";
        else if (roll < alertRate + dirtyRate) tone = "dirty";
        else tone = "clean";
      }

      // cells that lift off during the dedup beat
      let lift = 0;
      if (liftAt !== undefined && roll > 1 - liftRate) {
        lift = ramp(frame, [liftAt + order * 18, liftAt + 40 + order * 18]);
      }
      if (lift >= 0.995) continue;

      // how recently the head passed, used for a bright leading edge
      const edge = processed ? Math.max(0, 1 - (scanCol - col) / 5) : 0;

      const dx = drift ? noise2D(seed + "-dx", col * 0.2, r * 0.2 + frame * 0.004) * 1.6 : 0;
      const dy = drift ? noise2D(seed + "-dy", col * 0.2 + 40, r * 0.2 + frame * 0.004) * 1.6 : 0;

      cells.push(
        <div
          key={i}
          style={{
            position: "absolute",
            left: col * (cell + gap),
            top: r * (cell + gap),
            width: cell,
            height: cell,
            borderRadius: 3,
            background: TONE[tone].hex,
            opacity: appear * TONE[tone].a * (1 - lift),
            transform: `translate(${dx + lift * (noise2D(seed + "-lx", col, r) * 160)}px, ${
              dy - lift * (120 + Math.abs(noise2D(seed + "-ly", col, r)) * 160)
            }px) scale(${(0.86 + appear * 0.14) * (1 + edge * 0.5) * (1 - lift * 0.5)})`,
            boxShadow: edge > 0.05 ? `0 0 ${edge * 14}px ${TONE[tone].hex}` : undefined,
          }}
        />,
      );
    }
  }

  return (
    <div style={{ position: "relative", width: w, height: h, ...style }}>{cells}</div>
  );
};
