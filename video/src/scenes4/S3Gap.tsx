/**
 * Scene 3. Slot before snapshot. 600f / 20s.
 *
 * The old version of this scene drew two abstract "tracks" labelled Snapshot
 * first and Slot first, which only means something to someone who already
 * knows what a replication slot is. That is the wrong way round, and it was
 * told so.
 *
 * So the two things are drawn as what they physically are:
 *
 *   a SNAPSHOT is a photograph. It freezes every row at one instant, and
 *   uploading the photograph takes 29 minutes.
 *
 *   a SLOT is a recorder. PostgreSQL keeps every change from the moment the
 *   slot is created, and not one instant earlier.
 *
 * The tape the recorder lays down is drawn as the FLOOR under the timeline.
 * Changes fall onto it and stick. Where the recorder has not started yet
 * there is no floor, so the changes fall straight through and are gone. That
 * picture is the whole rule: switch the recorder on before you take the
 * photograph, or there is a hole under the 29 minutes in between.
 *
 * The two rows that fall through are the two this project actually lost:
 * 3,870,725 and 50,000,004, from README "What the row count did not show".
 * Both counts matched exactly while the mirror was wrong by two rows, which
 * is why the scene ends on the check that did find it.
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { noise2D } from "@remotion/noise";
import { Grain, ramp, pop } from "../motion/bits";
import { SceneFrame, Head, Readout, STAGE_W, STAGE_H } from "../motion/layout";
import { c, font } from "../theme";

/* -------------------------------------------------------------- the clock */

const T0 = 40;
const T1 = 1680;
const MINS = 35;
const X = (m: number) => T0 + (Math.max(0, Math.min(MINS, m)) / MINS) * (T1 - T0);
const UPLOAD_MIN = 29;

/* vertical bands inside the 1728 x 596 stage */
const PHOTO_Y = 14;
const PHOTO_H = 92;
const BAR_Y = 122;
const AXIS_Y = 186;
const TAPE_Y = 276;
const TAPE_H = 44;
const TRAY_Y = 386;
const TRAY_H = 96;
const BORN_Y = 222;
/** the captions sit below the tray, not on top of the chips that are in it */
const WHY_Y = 496;

/* -------------------------------------------------------------- the beats */

const T_PHOTO = 30;
const T_UPLOAD = 96;
const T_SLOT = 148;
const T_HOLE = 206;
const T_FALL1 = 240;
const T_FALL2 = 300;
const T_SAFE = 356;
const T_PANEL = 404;
const T_FIX = 500;

/** the two rows this run actually lost, and two that were caught */
type Change = { m: number; op: string; row: string; at: number; why: string };
const LOST: Change[] = [
  {
    m: 11.5,
    op: "DELETE",
    row: "row 3,870,725",
    at: T_FALL1,
    why: "The photograph still has this row. The feed never carries the delete. The mirror keeps it forever.",
  },
  {
    m: 19,
    op: "INSERT",
    row: "row 50,000,004",
    at: T_FALL2,
    why: "The photograph does not have this row. The feed never carries the insert. The mirror never gets it.",
  },
];
const SAFE: Change[] = [
  { m: 31.5, op: "UPDATE", row: "row 12,345,678", at: T_SAFE, why: "" },
];

/* ------------------------------------------------------------------ pieces */

const Hatch: React.FC<{
  left: number;
  top: number;
  width: number;
  height: number;
  colour: string;
  opacity?: number;
  radius?: number;
}> = ({ left, top, width, height, colour, opacity = 1, radius = 6 }) => (
  <div
    style={{
      position: "absolute",
      left,
      top,
      width: Math.max(0, width),
      height,
      borderRadius: radius,
      opacity,
      background: `repeating-linear-gradient(-45deg, ${colour} 0 4px, transparent 4px 11px)`,
    }}
  />
);

/** a change, falling. It sticks to the tape or it does not. */
const Chip: React.FC<{ ch: Change; slotM: number }> = ({ ch, slotM }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame < ch.at) return null;

  const caught = ch.m >= slotM;
  const fall = ramp(frame, [ch.at, ch.at + (caught ? 20 : 34)]);
  const land = caught ? TAPE_Y - 16 : TRAY_Y + 14;
  const y = BORN_Y + (land - BORN_Y) * fall;
  const born = pop(frame, fps, ch.at, { damping: 15, stiffness: 120 });
  const ink = caught ? c.greenInk : c.redInk;
  const bg = caught ? c.greenBg : c.redBg;
  const line = caught ? c.greenLine : "#F0C3C1";
  const settle = caught ? pop(frame, fps, ch.at + 18, { damping: 11, stiffness: 150 }) : 0;

  return (
    <div
      style={{
        position: "absolute",
        left: X(ch.m) - 118,
        top: y,
        width: 236,
        opacity: born,
        transform: `rotate(${caught ? 0 : noise2D("chip", ch.m, 3) * 9 * fall}deg)`,
      }}
    >
      <div
        style={{
          background: bg,
          border: `1px solid ${line}`,
          borderRadius: 7,
          padding: "9px 14px",
          textAlign: "center",
          boxShadow: `0 ${6 + settle * 4}px ${16 + settle * 10}px rgba(22,29,17,.10)`,
        }}
      >
        <div
          style={{
            fontFamily: font.mono,
            fontWeight: 700,
            fontSize: 16,
            letterSpacing: 1.4,
            color: ink,
          }}
        >
          {ch.op}
        </div>
        <div style={{ fontFamily: font.mono, fontSize: 14, color: c.body, marginTop: 4 }}>
          {ch.row}
        </div>
      </div>
      {caught && settle > 0.3 ? (
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: -26,
            transform: "translateX(-50%)",
            fontFamily: font.mono,
            fontSize: 19,
            color: c.greenStrong,
            opacity: settle,
          }}
        >
          &#10003;
        </div>
      ) : null}
    </div>
  );
};

/* ------------------------------------------------------------------- scene */

export const S3Gap: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  /* the recorder starts at 09:29 in the take that goes wrong, and slides
     back past the shutter once the rule is stated */
  const slotM = ramp(frame, [T_FIX, T_FIX + 30], [UPLOAD_MIN, -0.6]);
  const slotX = X(Math.max(0, slotM));
  const fixed = ramp(frame, [T_FIX, T_FIX + 30]);

  const axis = ramp(frame, [6, 40]);
  const photo = pop(frame, fps, T_PHOTO, { damping: 17, stiffness: 80 });
  const flash = 1 - ramp(frame, [T_PHOTO, T_PHOTO + 14]);
  const upload = ramp(frame, [T_UPLOAD, T_UPLOAD + 52]);
  const tape = ramp(frame, [T_SLOT, T_SLOT + 46]);
  const hole = ramp(frame, [T_HOLE, T_HOLE + 22]) * (1 - fixed);
  const tray = ramp(frame, [T_HOLE + 10, T_HOLE + 36]) * (1 - fixed);

  const panel = ramp(frame, [T_PANEL, T_PANEL + 22]) * (1 - ramp(frame, [T_FIX - 18, T_FIX]));

  /* the two lost changes are cleared before the take is run again */
  const takeA = 1 - ramp(frame, [T_PANEL - 16, T_PANEL]);
  const takeB = ramp(frame, [T_FIX + 24, T_FIX + 36]);

  return (
    <AbsoluteFill style={{ background: c.paper, overflow: "hidden" }}>
      <Grain opacity={0.18} />

      <SceneFrame
        head={
          <Head
            at={4}
            kicker={
              frame < T_SLOT
                ? "a photograph, and a recorder"
                : frame < T_PANEL
                  ? "29 minutes with no floor under them"
                  : frame < T_FIX
                    ? "both counts matched. the mirror was wrong by two rows"
                    : "the rule, and it costs nothing to follow"
            }
          >
            {frame < T_SLOT ? (
              <>
                The snapshot is a{" "}
                <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", color: c.greenInk }}>
                  photograph.
                </span>{" "}
                The slot is a recorder.
              </>
            ) : frame < T_PANEL ? (
              <>
                A change here lands in{" "}
                <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", color: c.redInk }}>
                  neither.
                </span>
              </>
            ) : frame < T_FIX ? (
              <>
                One row too many,{" "}
                <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", color: c.redInk }}>
                  one row too few.
                </span>
              </>
            ) : (
              <>
                Switch the recorder on{" "}
                <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", color: c.greenInk }}>
                  first.
                </span>
              </>
            )}
          </Head>
        }
        stage={
          <div style={{ position: "relative", width: STAGE_W, height: STAGE_H }}>
            {/* ------------------------------------------- the photograph */}
            <div
              style={{
                position: "absolute",
                left: T0,
                top: PHOTO_Y,
                width: 250,
                height: PHOTO_H,
                background: c.white,
                border: `1px solid ${c.border}`,
                borderRadius: 4,
                padding: "12px 14px",
                boxSizing: "border-box",
                opacity: photo,
                transform: `scale(${0.9 + photo * 0.1}) rotate(${(1 - photo) * -3}deg)`,
                boxShadow: "0 14px 34px rgba(22,29,17,.14)",
              }}
            >
              {Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={i}
                  style={{
                    height: 8,
                    marginBottom: 6,
                    borderRadius: 2,
                    background: c.border,
                    width: [96, 78, 88, 62, 92, 70][i] + "%",
                    opacity: 0.85,
                  }}
                />
              ))}
              <div
                style={{
                  position: "absolute",
                  right: 0,
                  bottom: 0,
                  width: 22,
                  height: 22,
                  background: c.paper,
                  borderTop: `1px solid ${c.border}`,
                  borderLeft: `1px solid ${c.border}`,
                }}
              />
            </div>

            {/* the shutter flash, at the instant it is taken */}
            {flash > 0.01 ? (
              <div
                style={{
                  position: "absolute",
                  left: T0 - 40,
                  top: PHOTO_Y - 40,
                  width: 330,
                  height: PHOTO_H + 80,
                  borderRadius: 14,
                  background: "#FFFFFF",
                  opacity: flash * 0.85,
                }}
              />
            ) : null}

            <div
              style={{
                position: "absolute",
                left: T0 + 280,
                top: PHOTO_Y + 4,
                width: 620,
                opacity: ramp(frame, [T_PHOTO + 10, T_PHOTO + 34]),
              }}
            >
              <div
                style={{
                  fontFamily: font.mono,
                  fontSize: 13,
                  letterSpacing: 2.2,
                  textTransform: "uppercase",
                  color: c.greenInk,
                }}
              >
                snapshot &middot; taken 09:00:00
              </div>
              <div style={{ fontFamily: font.sans, fontSize: 26, color: c.ink, marginTop: 8, lineHeight: 1.34 }}>
                Every row, exactly as it is at one instant.
              </div>
              <div style={{ fontFamily: font.sans, fontSize: 21, color: c.muted, marginTop: 6 }}>
                50,000,001 rows. Uploading them takes 29 minutes.
              </div>
            </div>

            {/* the upload, running across those 29 minutes */}
            <div
              style={{
                position: "absolute",
                left: X(0),
                top: BAR_Y,
                width: X(UPLOAD_MIN) - X(0),
                height: 26,
                borderRadius: 13,
                background: c.plate,
                border: `1px solid ${c.border}`,
                opacity: ramp(frame, [T_UPLOAD - 10, T_UPLOAD + 6]),
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: (X(UPLOAD_MIN) - X(0)) * upload,
                  height: "100%",
                  background: c.greenLine,
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: 16,
                  top: 4,
                  fontFamily: font.mono,
                  fontSize: 14,
                  color: c.greenInk,
                }}
              >
                uploading to the landing zone
              </div>
            </div>

            {/* --------------------------------------------- the time axis */}
            <div
              style={{
                position: "absolute",
                left: T0,
                top: AXIS_Y,
                width: (T1 - T0) * axis,
                height: 3,
                background: c.ink,
                opacity: 0.55,
              }}
            />
            {Array.from({ length: 8 }).map((_, i) => {
              const m = i * 5;
              const p = ramp(frame, [8 + i * 3, 26 + i * 3]);
              return (
                <div key={m} style={{ position: "absolute", left: X(m), top: AXIS_Y, opacity: p }}>
                  <div style={{ width: 1, height: 9, background: c.faint }} />
                  <div
                    style={{
                      position: "absolute",
                      left: -30,
                      top: 14,
                      width: 60,
                      textAlign: "center",
                      fontFamily: font.mono,
                      fontSize: 13,
                      color: c.faint,
                    }}
                  >
                    {"09:" + String(m).padStart(2, "0")}
                  </div>
                </div>
              );
            })}

            {/* the feed's track, empty, so the lower half is occupied from
                the start and the tape has somewhere to arrive */}
            <div
              style={{
                position: "absolute",
                left: X(0),
                top: TAPE_Y,
                width: (T1 - X(0)) * ramp(frame, [18, 46]),
                height: TAPE_H,
                borderRadius: 8,
                border: `1px dashed ${c.border}`,
                opacity: (1 - hole) * (1 - tape * 0.4),
              }}
            />
            <div
              style={{
                position: "absolute",
                left: X(0) + 18,
                top: TAPE_Y + 14,
                fontFamily: font.mono,
                fontSize: 14,
                letterSpacing: 1.6,
                color: c.faint,
                opacity: ramp(frame, [26, 48]) * (1 - ramp(frame, [T_SLOT - 20, T_SLOT])),
              }}
            >
              the change feed &#183; nothing is being recorded yet
            </div>

            {/* what a slot is, said plainly, in the band that was empty */}
            <div
              style={{
                position: "absolute",
                left: X(0),
                top: TRAY_Y + 6,
                width: 1080,
                opacity:
                  ramp(frame, [T_SLOT - 32, T_SLOT - 8]) * (1 - ramp(frame, [T_HOLE - 4, T_HOLE + 14])),
              }}
            >
              <div
                style={{
                  fontFamily: font.mono,
                  fontSize: 13,
                  letterSpacing: 2.2,
                  textTransform: "uppercase",
                  color: c.redInk,
                }}
              >
                slot &#183; created 09:29, after the upload finished
              </div>
              <div style={{ fontFamily: font.sans, fontSize: 26, color: c.ink, marginTop: 8, lineHeight: 1.34 }}>
                PostgreSQL keeps every change from the moment the slot is created.
              </div>
              <div style={{ fontFamily: font.sans, fontSize: 21, color: c.muted, marginTop: 6 }}>
                Nothing before it. There is no way to ask for earlier.
              </div>
            </div>

            {/* ------------------------------ the tape, which is the floor */}
            <div
              style={{
                position: "absolute",
                left: slotX,
                top: TAPE_Y,
                width: (T1 - slotX) * tape,
                height: TAPE_H,
                borderRadius: 8,
                background: c.greenBg,
                border: `1px solid ${c.greenLine}`,
                overflow: "hidden",
              }}
            >
              <Hatch left={0} top={0} width={T1 - slotX} height={TAPE_H} colour={c.green} opacity={0.34} radius={0} />
              <div
                style={{
                  position: "absolute",
                  left: 18,
                  top: 13,
                  fontFamily: font.mono,
                  fontSize: 15,
                  letterSpacing: 1.6,
                  color: c.greenInk,
                }}
              >
                &#9679; RECORDING
              </div>
            </div>

            {/* the recorder's own mark, where it was switched on */}
            <div
              style={{
                position: "absolute",
                left: slotX - 1.5,
                top: AXIS_Y + 6,
                width: 3,
                height: TAPE_Y - AXIS_Y - 6,
                background: fixed > 0.5 ? c.greenStrong : c.redInk,
                opacity: tape,
              }}
            />
            <div
              style={{
                position: "absolute",
                left: Math.max(0, Math.min(STAGE_W - 340, slotX - 170)),
                top: TAPE_Y + TAPE_H + 12,
                width: 340,
                textAlign: "center",
                fontFamily: font.mono,
                fontSize: 13,
                letterSpacing: 1.6,
                textTransform: "uppercase",
                color: fixed > 0.5 ? c.greenInk : c.redInk,
                opacity: tape,
              }}
            >
              slot created {fixed > 0.5 ? "09:00" : "09:29"} &#183; everything after this line is kept
            </div>

            {/* ------------------- the hole: 29 minutes with no floor in them */}
            {hole > 0.01 ? (
              <>
                <div
                  style={{
                    position: "absolute",
                    left: X(0),
                    top: TAPE_Y,
                    width: slotX - X(0),
                    height: TAPE_H,
                    borderRadius: 8,
                    border: `2px dashed ${c.red}`,
                    opacity: hole * 0.8,
                  }}
                />
                <Hatch
                  left={X(0)}
                  top={TAPE_Y}
                  width={slotX - X(0)}
                  height={TAPE_H}
                  colour={c.red}
                  opacity={hole * 0.3}
                />
                <div
                  style={{
                    position: "absolute",
                    left: X(0),
                    top: TAPE_Y + 13,
                    width: slotX - X(0),
                    textAlign: "center",
                    fontFamily: font.mono,
                    fontSize: 15,
                    letterSpacing: 1.6,
                    color: c.redInk,
                    opacity: hole,
                  }}
                >
                  no tape here &#183; after the photograph, before the recorder
                </div>
              </>
            ) : null}

            {/* the tray the lost changes settle in */}
            {tray > 0.01 ? (
              <div
                style={{
                  position: "absolute",
                  left: X(0),
                  top: TRAY_Y,
                  width: slotX - X(0),
                  height: TRAY_H,
                  borderRadius: 10,
                  border: `1px dashed ${c.red}`,
                  background: c.redBg,
                  opacity: tray * 0.55,
                }}
              />
            ) : null}
            {tray > 0.01 ? (
              <div
                style={{
                  position: "absolute",
                  top: TRAY_Y + TRAY_H - 22,
                  left: X(0) + 16,
                  width: 460,
                  textAlign: "left",
                  fontFamily: font.mono,
                  fontSize: 13,
                  letterSpacing: 1.8,
                  textTransform: "uppercase",
                  color: c.redInk,
                  opacity: tray * 0.85,
                }}
              >
                lost &#183; in neither the photograph nor the feed
              </div>
            ) : null}

            {/* ------------------------------------------- the changes fall */}
            <div style={{ opacity: takeA }}>
              {frame < T_PANEL
                ? LOST.map((ch) => <Chip key={ch.row} ch={ch} slotM={slotM} />)
                : null}
              {frame < T_PANEL ? SAFE.map((ch) => <Chip key={ch.row} ch={ch} slotM={slotM} />) : null}
            </div>

            {/* what each lost change means, written under it */}
            <div style={{ opacity: takeA }}>
              {LOST.map((ch, i) => {
                const p = ramp(frame, [ch.at + 34, ch.at + 56]);
                if (p <= 0.01 || frame >= T_PANEL) return null;
                return (
                  <div
                    key={ch.row}
                    style={{
                      position: "absolute",
                      left: X(ch.m) - 150 + (i === 0 ? -24 : 24),
                      top: WHY_Y,
                      width: 300,
                      fontFamily: font.sans,
                      fontSize: 17,
                      lineHeight: 1.38,
                      color: c.redInk,
                      textAlign: "center",
                      opacity: p,
                    }}
                  >
                    {ch.why}
                  </div>
                );
              })}
            </div>

            <div style={{ opacity: takeB }}>
              {frame >= T_FIX + 26
                ? LOST.map((ch, i) => (
                    <Chip
                      key={"b" + ch.row}
                      ch={{ ...ch, at: T_FIX + 30 + i * 12 }}
                      slotM={slotM}
                    />
                  ))
                : null}
            </div>

            {/* the rule, stated once the hole has closed */}
            {takeB > 0.01 ? (
              <div
                style={{
                  position: "absolute",
                  left: T0,
                  top: TRAY_Y + 30,
                  width: T1 - T0,
                  opacity: takeB,
                }}
              >
                <div
                  style={{
                    fontFamily: font.serif,
                    fontSize: 34,
                    color: c.ink,
                    lineHeight: 1.3,
                    opacity: ramp(frame, [T_FIX + 30, T_FIX + 50]),
                  }}
                >
                  Create the replication slot, then take the snapshot.{" "}
                  <span style={{ color: c.greenInk }}>The overlap is free.</span>
                </div>
                <div
                  style={{
                    fontFamily: font.sans,
                    fontSize: 22,
                    color: c.muted,
                    marginTop: 14,
                    opacity: ramp(frame, [T_FIX + 42, T_FIX + 62]),
                  }}
                >
                  An insert seen twice is an upsert. A delete of a row the snapshot never had is a
                  no-op. A change that falls in the gap is lost silently.
                </div>
              </div>
            ) : null}

            {/* ------------------- what the counts said, and what found it */}
            {panel > 0.01 ? (
              <div
                style={{
                  position: "absolute",
                  left: 0,
                  top: 214,
                  width: STAGE_W,
                  height: STAGE_H - 214,
                  background: c.paper,
                  opacity: panel,
                  transform: `translateY(${(1 - panel) * 34}px)`,
                  display: "flex",
                  gap: 56,
                  alignItems: "flex-start",
                  paddingTop: 22,
                  boxSizing: "border-box",
                }}
              >
                {/* the two counts, which agreed */}
                <div style={{ width: 720 }}>
                  <div
                    style={{
                      fontFamily: font.mono,
                      fontSize: 13,
                      letterSpacing: 2,
                      textTransform: "uppercase",
                      color: c.muted,
                      marginBottom: 20,
                    }}
                  >
                    every count-based check on this mirror passed
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 28 }}>
                    {["source", "mirror"].map((side, i) => (
                      <React.Fragment key={side}>
                        {i === 1 ? (
                          <div
                            style={{
                              fontFamily: font.mono,
                              fontSize: 46,
                              color: ramp(frame, [T_PANEL + 44, T_PANEL + 56]) > 0.5 ? c.redInk : c.greenStrong,
                            }}
                          >
                            =
                          </div>
                        ) : null}
                        <div style={{ opacity: pop(frame, fps, T_PANEL + 8 + i * 10) }}>
                          <div
                            style={{
                              fontFamily: font.mono,
                              fontWeight: 700,
                              fontSize: 54,
                              color: c.ink,
                              fontVariantNumeric: "tabular-nums",
                            }}
                          >
                            50,000,001
                          </div>
                          <div
                            style={{
                              fontFamily: font.mono,
                              fontSize: 13,
                              letterSpacing: 1.7,
                              textTransform: "uppercase",
                              color: c.muted,
                              marginTop: 10,
                            }}
                          >
                            rows in the {side}
                          </div>
                        </div>
                      </React.Fragment>
                    ))}
                  </div>
                  <div
                    style={{
                      display: "flex",
                      gap: 18,
                      marginTop: 30,
                      opacity: ramp(frame, [T_PANEL + 46, T_PANEL + 66]),
                    }}
                  >
                    {(
                      [
                        ["+1", "the delete that never happened"],
                        ["−1", "the insert that never arrived"],
                      ] as Array<[string, string]>
                    ).map(([v, l]) => (
                      <div
                        key={l}
                        style={{
                          background: c.redBg,
                          border: "1px solid #F0C3C1",
                          borderRadius: 8,
                          padding: "12px 18px",
                        }}
                      >
                        <span
                          style={{
                            fontFamily: font.mono,
                            fontWeight: 700,
                            fontSize: 30,
                            color: c.redInk,
                          }}
                        >
                          {v}
                        </span>
                        <span
                          style={{
                            fontFamily: font.sans,
                            fontSize: 17,
                            color: c.body,
                            marginLeft: 12,
                          }}
                        >
                          {l}
                        </span>
                      </div>
                    ))}
                  </div>
                  <div
                    style={{
                      fontFamily: font.serifItalic,
                      fontStyle: "italic",
                      fontSize: 26,
                      color: c.redInk,
                      marginTop: 30,
                      opacity: ramp(frame, [T_PANEL + 56, T_PANEL + 76]),
                    }}
                  >
                    Two errors of opposite sign, and a row count that matched exactly.
                  </div>
                </div>

                {/* what did find it */}
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      fontFamily: font.mono,
                      fontSize: 13,
                      letterSpacing: 2,
                      textTransform: "uppercase",
                      color: c.muted,
                      marginBottom: 20,
                    }}
                  >
                    ids bucketed by md5, both sides
                  </div>
                  <div style={{ display: "flex", gap: 4, alignItems: "flex-end", height: 156 }}>
                    {Array.from({ length: 44 }).map((_, i) => {
                      const at = T_PANEL + 12 + i * 1.1;
                      const p = ramp(frame, [at, at + 14]);
                      const odd = i === 27;
                      const h = 50 + Math.abs(noise2D("bk", i, 0)) * 92;
                      return (
                        <div
                          key={i}
                          style={{
                            flex: 1,
                            height: (odd ? h + 24 : h) * p,
                            borderRadius: "3px 3px 0 0",
                            background: odd ? c.red : c.green,
                            opacity: odd ? 0.92 : 0.28,
                          }}
                        />
                      );
                    })}
                  </div>
                  <div
                    style={{
                      fontFamily: font.sans,
                      fontSize: 20,
                      color: c.body,
                      marginTop: 20,
                      lineHeight: 1.4,
                      opacity: ramp(frame, [T_PANEL + 56, T_PANEL + 76]),
                    }}
                  >
                    One bucket disagrees, and it names the row:{" "}
                    <span style={{ fontFamily: font.mono, color: c.redInk }}>3,870,725</span>. A few
                    thousand ids to read, not fifty million.
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        }
        foot={
          <Readout
            at={24}
            stats={[
              { v: "50,000,002", l: "rows in the mirror, measured this run", at: 24 },
              { v: "50,000,001", l: "rows in the source", at: 32 },
              {
                v: "+1",
                l: "row 3,870,725, deleted before the slot existed",
                tone: "red",
                at: 40,
                small: true,
              },
            ]}
            note={<>A row that predates the slot is only removable by re-seeding.</>}
          />
        }
      />
    </AbsoluteFill>
  );
};
