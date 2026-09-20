/**
 * Brand truth for the film.
 *
 * The palette and type come from sulaimanahmed.dev, already converted from
 * OKLCH to hex for the architecture diagram in this repository, so the video,
 * the diagram and the site are the same hand. Green carries flow and good,
 * amber marks a one-off or scheduled path, red is reserved for bad, and vendor
 * colour appears only on vendor marks.
 */
import { loadFont as loadNewsreader } from "@remotion/google-fonts/Newsreader";
import { loadFont as loadJakarta } from "@remotion/google-fonts/PlusJakartaSans";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";

const newsreader = loadNewsreader("normal", {
  weights: ["400", "500", "600"],
  subsets: ["latin"],
});
const newsreaderItalic = loadNewsreader("italic", {
  weights: ["400", "500"],
  subsets: ["latin"],
});
const jakarta = loadJakarta("normal", {
  weights: ["400", "500", "600", "700"],
  subsets: ["latin"],
});
const mono = loadMono("normal", {
  weights: ["400", "500", "700"],
  subsets: ["latin"],
});

export const font = {
  serif: newsreader.fontFamily,
  serifItalic: newsreaderItalic.fontFamily,
  sans: jakarta.fontFamily,
  mono: mono.fontFamily,
};

/**
 * The palette was measured off the v6 render and corrected.
 *
 * Median relative luminance was 0.929 in nearly every scene, and the darkest
 * 5% of the frame still sat at 0.84: the film had almost no tonal range and
 * read as a flat bright wash. Worse, the structure was not there at all.
 * Borders were 1.34:1 against the paper, dividers 1.14:1, row bands 1.06:1.
 * Every card outline, table rule and gridline in the film was invisible, so
 * the eye had nothing to hold on to.
 *
 * Paper drops from 0.932 to 0.844 relative luminance, and the lines are
 * solved to real targets rather than picked by eye: borders 2.4:1, dividers
 * 1.7:1, chart lines 2.1:1, the accent green 3.5:1. Fills stay subtle on
 * purpose, around 1.2:1, because a row band that competes with a border is
 * noise.
 */
export const c = {
  paper: "#E7F0DB",
  white: "#FBFDF8",
  ink: "#131A0E",
  body: "#38432F",
  muted: "#55604A",
  faint: "#707B64",
  border: "#83A463",
  divider: "#A6C086",
  rail: "#C9DAB2",
  plate: "#D1E1BC",

  green: "#2B9000",
  greenStrong: "#008400",
  greenInk: "#175C00",
  greenBg: "#D2EFC4",
  greenLine: "#63B942",
  greenHi: "#57C427",

  amber: "#B36E00",
  amberInk: "#7E4D00",
  amberBg: "#F3E2C4",
  amberLine: "#D9B26E",

  red: "#C62E2B",
  redInk: "#9B201E",
  redBg: "#F5D6D5",

  pg: "#336791",
  wire: "#79935D",
};

/** The film's canvas. 30fps keeps the count-ups readable frame by frame. */
export const FPS = 30;
export const W = 1920;
export const H = 1080;

/**
 * One deceleration curve for everything that enters, one for everything that
 * settles. Using two curves across the whole film is what makes eight scenes
 * feel like one piece rather than eight.
 */
export const EASE_OUT = [0.16, 1, 0.3, 1] as const;
export const EASE_IN_OUT = [0.65, 0, 0.35, 1] as const;

/** Deterministic pseudo-random, because renders must be reproducible. */
export const rand = (seed: number) => {
  const x = Math.sin(seed * 12.9898) * 43758.5453;
  return x - Math.floor(x);
};
