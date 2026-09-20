/**
 * Scene 1. The table. 420f / 14s.
 *
 * The old opening was an abstract grid of coloured squares and it meant
 * nothing, which is exactly what it was told. A grid is not data until you
 * have seen the data.
 *
 * So this is one object filmed at three distances, and the object is the real
 * table:
 *
 *   1. close enough to read. Real column names from scripts/schema.py, the
 *      declared type under each one, and the actual values the generator
 *      writes. Every type says text, including the dates and the money.
 *   2. two cells lifted out. 11/03/2024 and 03/11/2024 are the same eight
 *      characters under two conventions and eight months apart. That is what
 *      "it is all text" costs.
 *   3. pulled back until the rows stop being legible and become the quantity.
 *      The grid at the end is the same table. It was earned rather than
 *      asserted.
 *
 * Every format on screen is one scripts/schema.py actually writes, at the
 * weights it writes them. Nothing here is decoration.
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { Odometer, Grain, ramp, pop } from "../motion/bits";
import { SceneFrame, Head, STAGE_W, STAGE_H } from "../motion/layout";
import { c, font } from "../theme";

/* ------------------------------------------------------------------ canvas */

const COLW = 300;
const ROWH = 52;
const HEADH = 100;
const NROWS = 38;
const CANVAS_W = 20 * COLW; // 6000
const CANVAS_H = HEADH + NROWS * ROWH; // 2076, which is STAGE_H at Z_FAR
const Z_FAR = STAGE_W / CANVAS_W; // 0.288

/** beat boundaries */
const B_LIFT = 146;
const B_PULL = 252;
const PULL_DUR = 96;
const B_SCAN = 368;

/* ------------------------------------------------- the real table, as data */

type Kind =
  | "id"
  | "ref"
  | "acct"
  | "cust"
  | "name"
  | "type"
  | "chan"
  | "ts"
  | "date"
  | "money"
  | "ccy"
  | "status"
  | "mid"
  | "merch"
  | "mcc"
  | "kyc"
  | "risk"
  | "flag"
  | "score";

/** the twenty columns are real; the hundred-column table repeats these kinds */
const COLS: Array<{ n: string; k: Kind }> = [
  { n: "txn_id", k: "id" },
  { n: "txn_ref", k: "ref" },
  { n: "account_no", k: "acct" },
  { n: "customer_id", k: "cust" },
  { n: "full_name", k: "name" },
  { n: "txn_type", k: "type" },
  { n: "channel", k: "chan" },
  { n: "txn_datetime", k: "ts" },
  { n: "posting_date", k: "date" },
  { n: "value_date", k: "date" },
  { n: "txn_amount", k: "money" },
  { n: "account_currency", k: "ccy" },
  { n: "txn_status", k: "status" },
  { n: "merchant_id", k: "mid" },
  { n: "merchant_name", k: "merch" },
  { n: "merchant_mcc", k: "mcc" },
  { n: "kyc_status", k: "kyc" },
  { n: "risk_rating", k: "risk" },
  { n: "aml_flag", k: "flag" },
  { n: "aml_score", k: "score" },
];

/** tone: 0 the canonical form, 1 a competing form, 2 nothing usable */
type Tone = 0 | 1 | 2;

/** the eight strings scripts/schema.py writes when it means "missing" */
const JUNK = ["", "NULL", "N/A", "NA", "-", "unknown", "none", "#N/A"];
/** the four sentinel dates it writes instead of a null */
const SENTINEL = ["1900-01-01", "9999-12-31", "0000-00-00", "1970-01-01"];

/** the five date formats, at the weights the generator uses */
const DATES: Array<[string, Tone]> = [
  ["2024-03-11", 0],
  ["11/03/2024", 1],
  ["03/11/2024", 1],
  ["11-Mar-24", 1],
  ["11.03.2024", 1],
];
const DATE_W = [0.55, 0.75, 0.85, 0.93, 1.0];

const POOLS: Record<Kind, Array<[string, Tone]>> = {
  id: [["TXN00000015096963", 0], ["TXN00000031447108", 0], ["TXN00000008820914", 0]],
  ref: [["REF-8842-KL", 0], ["REF-1190-JB", 0], ["ref-4417-png", 1]],
  acct: [["8801234567", 0], ["8809934120", 0], ["880-114-8821", 1]],
  cust: [["CUS0004412", 0], ["CUS0198340", 0], ["CUS0044117", 0]],
  name: [["Nurul binti Hassan", 0], ["Wei Ming Tan", 0], ["rajesh a/l subramaniam", 1]],
  type: [["PURCHASE", 0], ["purchase", 1], ["Purchase", 1], ["TRANSFER", 0]],
  chan: [["POS", 0], ["pos", 1], ["ATM", 0], ["ECOM", 0]],
  ts: [
    ["2024-03-11 14:22:07", 0],
    ["2024-03-11T14:22:07", 1],
    ["2024-03-11T14:22:07+08:00", 1],
    ["11/03/2024 14:22", 1],
    ["1750529113", 1],
  ],
  date: DATES,
  money: [["312.40", 0], ["1,250.50", 1], ["RM99.00", 1], ["(45.00)", 1], ["88.00", 0]],
  ccy: [["MYR", 0], ["myr", 1], ["SGD", 0]],
  status: [["POSTED", 0], ["posted", 1], ["PENDING", 0]],
  mid: [["MER012043", 0], ["MER000884", 0], ["MER117220", 0]],
  merch: [["99 SPEEDMART", 0], ["  AEON BIG  ", 1], ["Shopee MY", 0], ["GRAB*RIDE", 0]],
  mcc: [["5411", 0], ["5814", 0], ["4121", 0]],
  kyc: [["VERIFIED", 0], ["verified", 1], ["PENDING", 0]],
  risk: [["LOW", 0], ["Medium", 1], ["HIGH", 0]],
  flag: [["N", 0], ["Y", 0], ["true", 1], ["0", 1], ["T", 1]],
  score: [["37%", 1], ["0.37", 0], ["82%", 1], ["0.04", 0]],
};

/**
 * A uniform roll per cell, deterministic in the cell's own coordinates.
 *
 * This used noise2D, and smooth noise is not uniform: it crowds the middle of
 * its range. Measured over the wall it gave 0.5% junk where the generator
 * writes 5%, and a format mix of 58/24/13/4/1 against the 55/20/10/8/7 the
 * bar underneath the wall states. A hash is flat, so the picture and the
 * caption are now the same distribution.
 */
const roll = (a: number, b: number, salt: number) => {
  const x = Math.sin((a + 1) * 127.1 + (b + 1) * 311.7 + salt * 74.7) * 43758.5453;
  return x - Math.floor(x);
};

/** one cell, decided once and the same on every frame */
const cellOf = (r: number, col: number): [string, Tone] => {
  const k = COLS[col].k;
  const miss = roll(r, col, 1);
  // 5% of a column is junk that means missing, 2% is a sentinel date
  if (miss < 0.05) return [JUNK[Math.floor(roll(r, col, 2) * JUNK.length) % JUNK.length], 2];
  if (k === "date" && miss < 0.07) {
    return [SENTINEL[Math.floor(roll(r, col, 3) * SENTINEL.length) % SENTINEL.length], 2];
  }
  const pool = POOLS[k];
  if (k === "date") {
    const u = roll(r, col, 4);
    for (let i = 0; i < DATE_W.length; i++) if (u < DATE_W[i]) return DATES[i];
    return DATES[0];
  }
  return pool[Math.floor(roll(r, col, 5) * pool.length) % pool.length];
};

/** the five date formats and the chip palette each is drawn in */
const FORMATS: Array<[string, number, [string, string, string]]> = [
  ["2024-03-11", 55, [c.greenBg, c.greenLine, c.greenInk]],
  ["11/03/2024", 20, [c.amberBg, c.amberLine, c.amberInk]],
  ["03/11/2024", 10, [c.redBg, "#F0C3C1", c.redInk]],
  ["11-Mar-24", 8, [c.amberBg, c.amberLine, c.amberInk]],
  ["11.03.2024", 7, [c.amberBg, c.amberLine, c.amberInk]],
];

const TONE_INK: Record<Tone, string> = { 0: c.body, 1: c.amberInk, 2: c.redInk };
const TONE_BG: Record<Tone, string> = { 0: "transparent", 1: c.amberBg, 2: c.redBg };

/* ------------------------------------------------------------------- scene */

export const S1Field: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  /* the camera: one continuous pull-back from readable to quantity */
  const z = ramp(frame, [B_PULL, B_PULL + PULL_DUR], [1, Z_FAR]);
  const tx = ramp(frame, [B_PULL, B_PULL + PULL_DUR], [-2100, 0]);
  const ty = ramp(frame, [B_PULL, B_PULL + PULL_DUR], [0, -1]);
  /* text survives only while the rows are tall enough to carry it */
  const legible = 1 - ramp(frame, [B_PULL + 24, B_PULL + 58]);

  /* the parse pass, once the whole table is in frame */
  const scanP = ramp(frame, [B_SCAN, B_SCAN + 46]);
  const scanCol = scanP * 20;

  const lift = pop(frame, fps, B_LIFT, { damping: 18, stiffness: 72 });
  const liftOut = 1 - ramp(frame, [B_PULL - 14, B_PULL]);
  const lifted = lift * liftOut;

  /* the rows, drawn once */
  const rows: React.ReactNode[] = [];
  for (let r = 0; r < NROWS; r++) {
    const born = 16 + r * 2.1;
    const appear = ramp(frame, [born, born + 12]);
    if (appear <= 0.004) continue;
    for (let col = 0; col < 20; col++) {
      const [v, t] = cellOf(r, col);
      const scanned = col < scanCol;
      const show = scanned ? t : (0 as Tone);
      rows.push(
        <div
          key={r * 20 + col}
          style={{
            position: "absolute",
            left: col * COLW,
            top: HEADH + r * ROWH,
            width: COLW,
            height: ROWH,
            display: "flex",
            alignItems: "center",
            paddingLeft: 18,
            paddingRight: 14,
            boxSizing: "border-box",
            overflow: "hidden",
            opacity: appear,
          }}
        >
          {/* the value's ink, which survives the pull-back as the texture */}
          <div
            style={{
              position: "absolute",
              left: 14,
              top: ROWH / 2 - 9,
              width: 20 + (v.length / 26) * (COLW - 60),
              height: 18,
              borderRadius: 4,
              background: TONE_INK[show],
              opacity: (1 - legible) * (show === 0 ? 0.42 : show === 1 ? 0.66 : 0.86),
            }}
          />
          <div
            style={{
              position: "absolute",
              left: 10,
              top: 6,
              right: 12,
              bottom: 6,
              borderRadius: 5,
              background: TONE_BG[show],
              opacity: legible * 0.95,
            }}
          />
          <span
            style={{
              position: "relative",
              fontFamily: font.mono,
              fontSize: 19,
              color: TONE_INK[show],
              opacity: legible,
              whiteSpace: "pre",
            }}
          >
            {v === "" ? " " : v}
          </span>
        </div>,
      );
    }
  }

  return (
    <AbsoluteFill style={{ background: c.paper, overflow: "hidden" }}>
      <Grain opacity={0.22} />

      <SceneFrame
        head={
          <Head
            at={4}
            kicker={
              frame < B_LIFT
                ? "postgresql · public.raw_txn · 100 columns"
                : frame < B_PULL
                  ? "the same eight characters, two conventions"
                  : "one parse pass over every row"
            }
          >
            {frame < B_LIFT ? (
              <>
                Every column is declared{" "}
                <span style={{ fontFamily: font.mono, fontSize: 44, color: c.greenInk }}>text</span>.
              </>
            ) : frame < B_PULL ? (
              <>
                03/11/2024 is{" "}
                <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", color: c.redInk }}>
                  two different days.
                </span>
              </>
            ) : (
              <>
                Fifty million rows{" "}
                <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", color: c.greenInk }}>
                  of this.
                </span>
              </>
            )}
          </Head>
        }
        stage={
          <div style={{ position: "relative", width: STAGE_W, height: STAGE_H, overflow: "hidden" }}>
            <div
              style={{
                position: "absolute",
                left: 0,
                top: 0,
                width: CANVAS_W,
                height: CANVAS_H,
                transform: `translate(${tx}px, ${ty}px) scale(${z})`,
                transformOrigin: "0 0",
                background: c.white,
                border: `1px solid ${c.border}`,
                borderRadius: 4,
              }}
            >
              {/* the header: the name, and the type underneath it */}
              {COLS.map((col, i) => {
                const p = pop(frame, fps, 4 + i * 1.4);
                return (
                  <div
                    key={col.n}
                    style={{
                      position: "absolute",
                      left: i * COLW,
                      top: 0,
                      width: COLW,
                      height: HEADH,
                      paddingLeft: 18,
                      paddingTop: 20,
                      boxSizing: "border-box",
                      opacity: p,
                      background: c.plate,
                      borderBottom: `2px solid ${c.border}`,
                    }}
                  >
                    <div
                      style={{
                        fontFamily: font.mono,
                        fontWeight: 700,
                        fontSize: 21,
                        color: c.ink,
                        opacity: legible,
                      }}
                    >
                      {col.n}
                    </div>
                    <div
                      style={{
                        display: "inline-block",
                        marginTop: 9,
                        padding: "3px 10px",
                        borderRadius: 4,
                        background: c.greenBg,
                        border: `1px solid ${c.greenLine}`,
                        fontFamily: font.mono,
                        fontSize: 15,
                        letterSpacing: 1.2,
                        color: c.greenInk,
                        opacity: legible,
                      }}
                    >
                      text
                    </div>
                    {/* what the header becomes once it is too small to read */}
                    <div
                      style={{
                        position: "absolute",
                        left: 14,
                        top: 36,
                        width: COLW - 46,
                        height: 22,
                        borderRadius: 4,
                        background: c.ink,
                        opacity: (1 - legible) * 0.42,
                      }}
                    />
                  </div>
                );
              })}

              {/* row banding, so the wall reads as rows rather than confetti */}
              {Array.from({ length: NROWS }).map((_, r) =>
                r % 2 === 1 ? (
                  <div
                    key={"b" + r}
                    style={{
                      position: "absolute",
                      left: 0,
                      top: HEADH + r * ROWH,
                      width: CANVAS_W,
                      height: ROWH,
                      background: c.rail,
                      opacity: 0.55,
                    }}
                  />
                ) : null,
              )}

              {rows}
            </div>

            {/* the parse head, in stage coordinates */}
            {frame >= B_SCAN && scanP < 0.999 ? (
              <div
                style={{
                  position: "absolute",
                  left: scanP * STAGE_W - 2,
                  top: 0,
                  width: 4,
                  height: STAGE_H,
                  background: c.greenStrong,
                  boxShadow: `0 0 90px 24px ${c.greenHi}55`,
                }}
              />
            ) : null}

            {/* two cells lifted out, because this is the whole argument */}
            {lifted > 0.01 ? (
              <div
                style={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  width: STAGE_W,
                  height: STAGE_H,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 96,
                  background: "rgba(231,240,219,.94)",
                  opacity: lifted,
                }}
              >
                {(
                  [
                    ["11/03/2024", "%d/%m/%Y", "11 March 2024", "20% of the column", c.greenInk],
                    ["03/11/2024", "%m/%d/%Y", "3 November 2024", "10% of the column", c.amberInk],
                  ] as Array<[string, string, string, string, string]>
                ).map((cell, i) => {
                  const p = pop(frame, fps, B_LIFT + 8 + i * 9, { damping: 17, stiffness: 84 });
                  return (
                    <div
                      key={cell[0]}
                      style={{
                        width: 640,
                        padding: "38px 44px 42px",
                        background: c.white,
                        border: `1px solid ${c.border}`,
                        borderRadius: 10,
                        boxShadow: "0 22px 54px rgba(22,29,17,.12)",
                        opacity: p,
                        transform: `translateY(${(1 - p) * 26}px)`,
                      }}
                    >
                      <div
                        style={{
                          fontFamily: font.mono,
                          fontSize: 13,
                          letterSpacing: 2,
                          textTransform: "uppercase",
                          color: c.faint,
                        }}
                      >
                        posting_date, as stored
                      </div>
                      <div
                        style={{
                          fontFamily: font.mono,
                          fontWeight: 700,
                          fontSize: 62,
                          color: c.ink,
                          margin: "16px 0 22px",
                        }}
                      >
                        {cell[0]}
                      </div>
                      <div
                        style={{
                          height: 1,
                          background: c.border,
                          transform: `scaleX(${ramp(frame, [B_LIFT + 22 + i * 9, B_LIFT + 46 + i * 9])})`,
                          transformOrigin: "left",
                        }}
                      />
                      <div
                        style={{
                          fontFamily: font.mono,
                          fontSize: 17,
                          color: c.muted,
                          marginTop: 20,
                        }}
                      >
                        {cell[1]}
                      </div>
                      <div
                        style={{
                          fontFamily: font.serif,
                          fontSize: 40,
                          color: cell[4],
                          marginTop: 8,
                          opacity: ramp(frame, [B_LIFT + 30 + i * 9, B_LIFT + 52 + i * 9]),
                        }}
                      >
                        {cell[2]}
                      </div>
                      <div
                        style={{
                          fontFamily: font.mono,
                          fontSize: 14,
                          letterSpacing: 1.4,
                          textTransform: "uppercase",
                          color: c.faint,
                          marginTop: 14,
                        }}
                      >
                        {cell[3]}
                      </div>
                    </div>
                  );
                })}

                <div
                  style={{
                    position: "absolute",
                    left: 0,
                    right: 0,
                    bottom: 2,
                    textAlign: "center",
                    fontFamily: font.serifItalic,
                    fontStyle: "italic",
                    fontSize: 30,
                    color: c.redInk,
                    opacity: ramp(frame, [B_LIFT + 58, B_LIFT + 80]),
                  }}
                >
                  Guess the wrong convention and the transaction moves eight months.
                </div>
              </div>
            ) : null}

            {/* the table continues below the frame, so it fades rather than
                ending on a cut edge */}
            <div
              style={{
                position: "absolute",
                left: 0,
                right: 0,
                bottom: 0,
                height: 72,
                background: `linear-gradient(180deg, rgba(231,240,219,0), ${c.paper})`,
                opacity: legible,
                pointerEvents: "none",
              }}
            />
          </div>
        }
        foot={
          <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
            <div
              style={{
                height: 1,
                background: c.border,
                marginBottom: 22,
                transform: `scaleX(${ramp(frame, [14, 42])})`,
                transformOrigin: "left",
              }}
            />
            <div style={{ display: "flex", alignItems: "flex-start", gap: 54 }}>
              <div style={{ opacity: pop(frame, fps, 20) }}>
                <div
                  style={{
                    fontFamily: font.mono,
                    fontWeight: 700,
                    fontSize: 52,
                    color: c.ink,
                    lineHeight: 1,
                  }}
                >
                  <Odometer to={50000001} at={22} dur={58} size={52} color={c.ink} />
                </div>
                <div
                  style={{
                    fontFamily: font.mono,
                    fontSize: 13,
                    letterSpacing: 1.7,
                    textTransform: "uppercase",
                    color: c.muted,
                    marginTop: 12,
                  }}
                >
                  rows in the source table
                </div>
              </div>

              {/* the five formats one date column is written in, at their
                  real weights, because inventing a share here would make the
                  film's own promise false */}
              <div style={{ flex: 1, opacity: ramp(frame, [34, 62]) }}>
                <div
                  style={{
                    fontFamily: font.mono,
                    fontSize: 13,
                    letterSpacing: 1.7,
                    textTransform: "uppercase",
                    color: c.muted,
                    marginBottom: 14,
                  }}
                >
                  one date column, five competing formats
                </div>
                <div style={{ display: "flex", gap: 5, height: 44 }}>
                  {FORMATS.map(([lab, pct, tone], i) => {
                    const p = ramp(frame, [40 + i * 7, 62 + i * 7]);
                    return (
                      <div
                        key={lab}
                        style={{
                          flex: pct,
                          background: tone[0],
                          border: `1px solid ${tone[1]}`,
                          borderRadius: 5,
                          boxSizing: "border-box",
                          transform: `scaleY(${p})`,
                          transformOrigin: "bottom",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          overflow: "hidden",
                        }}
                      >
                        <span
                          style={{
                            fontFamily: font.mono,
                            fontSize: 14,
                            color: tone[2],
                            whiteSpace: "nowrap",
                            opacity: p,
                          }}
                        >
                          {pct >= 15 ? lab + "  " + pct + "%" : pct + "%"}
                        </span>
                      </div>
                    );
                  })}
                </div>
                <div
                  style={{
                    fontFamily: font.mono,
                    fontSize: 13,
                    color: c.faint,
                    marginTop: 11,
                    opacity: ramp(frame, [64, 90]),
                  }}
                >
                  {FORMATS.map((f) => f[0]).join("   \u00b7   ")}
                </div>
              </div>

              <div
                style={{
                  width: 360,
                  textAlign: "right",
                  fontFamily: font.serifItalic,
                  fontStyle: "italic",
                  fontSize: 25,
                  lineHeight: 1.32,
                  color: c.greenInk,
                  opacity: ramp(frame, [60, 90]),
                }}
              >
                Plus four sentinel dates and eight strings that mean missing.
              </div>
            </div>
          </div>
        }
      />
    </AbsoluteFill>
  );
};
