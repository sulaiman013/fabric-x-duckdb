/**
 * The card rectangles, measured off the 2x captures.
 *
 * They TILE the capture: every pixel of the page belongs to exactly one card,
 * with no gaps at the edges or between them. That matters because the page is
 * drawn as cards rather than as one image, so any pixel no card claims shows
 * the dark room behind it. v6's first cut used rects measured tightly around
 * each visual, and the page's own margins turned into a black border around
 * the two artifacts the film exists to show.
 *
 * So each rect is snapped outward to the midline between its neighbours. The
 * card now carries its own gutter, which is also what makes it read as a real
 * card once the page pulls apart.
 */
import { Card } from "../motion/SixBeat";

export const REPORT_IW = 4258;
export const REPORT_IH = 2394;

/* y: 284 | 406 | 681 | 1624 | 2394     x: 2720 | 4258 */
export const OVERVIEW: Card[] = [
  { id: "title", rect: [0, 0, 4258, 284] },
  { id: "chips", rect: [0, 284, 4258, 122] },
  { id: "kpis", rect: [0, 406, 4258, 275] },
  { id: "months", rect: [0, 681, 2720, 943] },
  { id: "channel", rect: [2720, 681, 1538, 943] },
  { id: "composition", rect: [0, 1624, 2720, 770] },
  { id: "firings", rect: [2720, 1624, 1538, 770] },
];

/* y: 292 | 568 | 1482 | 2394           x: 2330 | 4258 */
export const RULES: Card[] = [
  { id: "title", rect: [0, 0, 4258, 292] },
  { id: "kpis", rect: [0, 292, 4258, 276] },
  { id: "volume", rect: [0, 568, 2330, 914] },
  { id: "together", rect: [2330, 568, 1928, 914] },
  { id: "dist", rect: [0, 1482, 2330, 912] },
  { id: "threshold", rect: [2330, 1482, 1928, 912] },
];

export const ARCH_IW = 3840;
export const ARCH_IH = 2160;

/* y: 500 | 1680 | 2160                 x: 1600 | 3840 */
export const PIPELINE: Card[] = [
  { id: "head", rect: [0, 0, 3840, 500] },
  { id: "onprem", rect: [0, 500, 1600, 1180] },
  { id: "fabric", rect: [1600, 500, 2240, 1180] },
  { id: "kpis", rect: [0, 1680, 3840, 480] },
];
