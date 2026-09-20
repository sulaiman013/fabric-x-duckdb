/**
 * Scene 2. The gap. 540f / 18s.
 *
 * The argument for open mirroring is spatial, so it is staged spatially: a
 * database on the left, OneLake on the right, and a boundary between them that
 * nothing may cross inward.
 *
 * Three routes are tried and visibly fail. A nightly export heaves one huge
 * block across and the year counter spins. An incremental copy and native
 * mirroring both reach back toward the source and bounce off the boundary.
 * Then the fourth route pushes small numbered packets outward, continuously,
 * and a Delta table grows out of them.
 *
 * Staging note: only ONE route is ever described at a time, in a single slot
 * under the boundary. The first cut floated a label per route and two of them
 * landed on the same spot. Retired routes become struck-through chips in the
 * corner instead of lingering as ghosts over the stage.
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { Wire, curve, TracedPacket } from "../motion/Wire";
import { Slab, Odometer, Caption, Grain, ramp, pop, bounce, Sparks } from "../motion/bits";
import { Icon } from "../components/Icon";
import { c, font } from "../theme";

const SW = 1760;
const SH = 600;
const LEFT_X = 20;
const RIGHT_X = 1220;
const BOX_W = 540;
const BOUNDARY = 800;
const LANE_Y = 286;

const T_EXPORT = 108;
const T_INCR = 208;
const T_NATIVE = 286;
const T_OPEN = 360;

type RouteDef = { n: string; title: string; cost: string; at: number; until: number; ok?: boolean };

const ROUTES: RouteDef[] = [
  { n: "01", title: "Nightly full export", cost: "3.8 TB a year, and up to 24 hours stale", at: T_EXPORT, until: T_INCR - 10 },
  { n: "02", title: "Scheduled incremental copy", cost: "has to reach in, and misses deletes", at: T_INCR, until: T_NATIVE - 10 },
  { n: "03", title: "Native mirroring", cost: "also connects inward. not available here.", at: T_NATIVE, until: T_OPEN - 10 },
  { n: "04", title: "Open mirroring", cost: "the publisher pushes. insert, update and delete.", at: T_OPEN, until: 9999, ok: true },
];

export const S2Mirror: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  /* route 1: one huge block heaves across, twice */
  const heave = (start: number) => (frame < start ? null : ramp(frame, [start, start + 52]));
  const blocks = [heave(T_EXPORT + 8), heave(T_EXPORT + 58)];

  /* routes 2 and 3: an arrow reaches inward and bounces off the boundary */
  const bounceAt = (start: number) => {
    const t = frame - start;
    if (t < 0 || t > 66) return null;
    const go = ramp(frame, [start, start + 32]);
    const back = ramp(frame, [start + 32, start + 54]);
    return {
      x: RIGHT_X - go * (RIGHT_X - BOUNDARY - 26) + back * 170,
      o: 1 - ramp(frame, [start + 46, start + 66]),
    };
  };
  const arrows = [
    { b: bounceAt(T_INCR + 6), hit: T_INCR + 38, seed: 3 },
    { b: bounceAt(T_NATIVE + 6), hit: T_NATIVE + 38, seed: 4 },
  ];

  /* route 4 */
  const openP = ramp(frame, [T_OPEN, T_OPEN + 36]);
  const rowsIn = Math.floor(ramp(frame, [T_OPEN + 42, T_OPEN + 156]) * 9);
  const lane = curve(LEFT_X + BOX_W, LANE_Y, RIGHT_X, LANE_Y, 0);
  // the traced packet stops short of the card, so its label never lands on
  // top of the card title
  const shortLane = curve(LEFT_X + BOX_W, LANE_Y, RIGHT_X - 96, LANE_Y, 0);

  const retired = ROUTES.filter((r) => frame >= r.until && !r.ok);

  return (
    <AbsoluteFill style={{ background: c.paper, overflow: "hidden" }}>
      <Grain opacity={0.2} />

      <Caption at={4} x={96} y={70} size={52} sub="an on-premises table, into onelake">
        Mirror it.{" "}
        <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", color: c.greenInk }}>
          Don&apos;t export it.
        </span>
      </Caption>

      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", paddingTop: 96, paddingBottom: 30 }}>
        <div style={{ position: "relative", width: SW, height: SH }}>
          {/* the boundary nothing may cross inward */}
          <div
            style={{
              position: "absolute",
              left: BOUNDARY,
              top: 20,
              height: SH - 40,
              width: 2,
              background: `repeating-linear-gradient(180deg, ${c.border} 0 10px, transparent 10px 20px)`,
              opacity: ramp(frame, [22, 44]),
            }}
          />
          <div
            style={{
              position: "absolute",
              left: BOUNDARY - 110,
              top: -8,
              width: 220,
              textAlign: "center",
              fontFamily: font.mono,
              fontSize: 12,
              letterSpacing: 2,
              textTransform: "uppercase",
              color: c.faint,
              opacity: ramp(frame, [30, 52]),
            }}
          >
            no inbound route
          </div>

          <Slab x={LEFT_X} y={LANE_Y - 186} w={BOX_W} h={372} at={0}>
            <div style={{ padding: "26px 28px" }}>
              <Icon name="postgres" size={54} />
              <div style={{ fontFamily: font.sans, fontSize: 34, fontWeight: 700, color: c.ink, marginTop: 20 }}>
                PostgreSQL
              </div>
              <div style={{ fontFamily: font.mono, fontSize: 18, color: c.muted, marginTop: 10 }}>
                on-premises, localhost
              </div>
              <div
                style={{
                  fontFamily: font.mono,
                  fontSize: 32,
                  fontWeight: 700,
                  color: c.greenInk,
                  marginTop: 36,
                }}
              >
                50,000,001
              </div>
              <div style={{ fontFamily: font.mono, fontSize: 15, color: c.muted, marginTop: 8 }}>
                rows, 100 text columns
              </div>
              <div style={{ fontFamily: font.mono, fontSize: 15, color: c.muted, marginTop: 30 }}>
                wal_level = logical
              </div>
            </div>
          </Slab>

          <Slab x={RIGHT_X} y={LANE_Y - 186} w={BOX_W} h={372} at={10}>
            <div style={{ padding: "26px 28px" }}>
              <Icon name="fabric" size={52} />
              <div style={{ fontFamily: font.sans, fontSize: 34, fontWeight: 700, color: c.ink, marginTop: 20 }}>
                OneLake
              </div>
              <div style={{ fontFamily: font.mono, fontSize: 18, color: c.muted, marginTop: 10 }}>
                landing zone, then Delta
              </div>
              <div
                style={{
                  fontFamily: font.mono,
                  fontSize: 24,
                  fontWeight: 700,
                  color: c.greenInk,
                  marginTop: 34,
                  opacity: ramp(frame, [T_OPEN + 58, T_OPEN + 82]),
                }}
              >
                replicating
              </div>
            </div>
          </Slab>

          {/* route 1: the heave */}
          {blocks.map((p, i) =>
            p === null ? null : (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: LEFT_X + BOX_W + p * (RIGHT_X - LEFT_X - BOX_W - 16),
                  top: LANE_Y - 190 - Math.sin(p * Math.PI) * 26,
                  width: 148,
                  height: 88,
                  borderRadius: 10,
                  background: c.amberBg,
                  border: `2px solid ${c.amberLine}`,
                  display: "grid",
                  placeItems: "center",
                  fontFamily: font.mono,
                  fontSize: 19,
                  fontWeight: 700,
                  color: c.amberInk,
                  opacity: (1 - ramp(frame, [T_INCR - 24, T_INCR])) * (p > 0.98 ? 0.2 : 1),
                  boxShadow: "0 8px 22px rgba(22,29,17,.13)",
                }}
              >
                10.5 GB
              </div>
            ),
          )}

          {/* routes 2 and 3: reach inward, bounce */}
          {arrows.map((a, i) =>
            a.b === null ? null : (
              <React.Fragment key={i}>
                <div
                  style={{
                    position: "absolute",
                    left: a.b.x,
                    top: LANE_Y + 140,
                    width: 48,
                    height: 36,
                    borderRadius: 7,
                    background: c.redBg,
                    border: `2px solid ${c.red}`,
                    display: "grid",
                    placeItems: "center",
                    fontFamily: font.mono,
                    fontSize: 20,
                    fontWeight: 700,
                    color: c.redInk,
                    opacity: a.b.o,
                  }}
                >
                  &lsaquo;
                </div>
                <Sparks x={BOUNDARY} y={LANE_Y + 158} at={a.hit} n={13} spread={86} color={c.red} seed={a.seed} life={24} />
              </React.Fragment>
            ),
          )}

          {/* route 4: it pushes */}
          <div style={{ opacity: openP }}>
            <Wire
              d={lane}
              drawAt={T_OPEN}
              drawDur={26}
              color={c.green}
              width={3.5}
              packets={6}
              packetAt={T_OPEN + 16}
              travel={76}
              mixed
              labelled
              packetSize={40}
            />
          </div>

          {/* the Delta table the packets build */}
          <div
            style={{
              position: "absolute",
              left: RIGHT_X + 8,
              top: LANE_Y + 206,
              width: 520,
              opacity: ramp(frame, [T_OPEN + 40, T_OPEN + 62]),
            }}
          >
            <div
              style={{
                fontFamily: font.mono,
                fontSize: 11,
                letterSpacing: 2,
                textTransform: "uppercase",
                color: c.faint,
                marginBottom: 8,
              }}
            >
              raw_txn &middot; delta
            </div>
            {Array.from({ length: 9 }).map((_, i) => {
              const on = i < rowsIn;
              const s = on ? bounce(frame, fps, T_OPEN + 46 + i * 11) : 0;
              return (
                <div
                  key={i}
                  style={{
                    height: 17,
                    marginBottom: 6,
                    borderRadius: 3,
                    background: c.green,
                    opacity: s * 0.5,
                    transform: `scaleX(${0.25 + s * 0.75})`,
                    transformOrigin: "left",
                  }}
                />
              );
            })}
          </div>

          {/* the landing zone: what the publisher is actually writing */}
          <div
            style={{
              position: "absolute",
              left: BOUNDARY - 250,
              top: LANE_Y + 96,
              width: 500,
              opacity: ramp(frame, [T_OPEN + 30, T_OPEN + 54]),
            }}
          >
            <div
              style={{
                fontFamily: font.mono,
                fontSize: 11,
                letterSpacing: 2,
                textTransform: "uppercase",
                color: c.faint,
                marginBottom: 10,
                textAlign: "center",
              }}
            >
              the landing zone
            </div>
            {["00000000000000000001.parquet", "00000000000000000002.parquet", "_metadata.json  written last"].map(
              (f, i) => {
                const at = T_OPEN + 40 + i * 14;
                const p = ramp(frame, [at, at + 18]);
                const last = i === 2;
                return (
                  <div
                    key={f}
                    style={{
                      fontFamily: font.mono,
                      fontSize: 13,
                      color: last ? c.amberInk : c.body,
                      background: last ? c.amberBg : c.white,
                      border: `1px solid ${last ? c.amberLine : c.border}`,
                      borderRadius: 7,
                      padding: "8px 14px",
                      marginBottom: 6,
                      opacity: p,
                      transform: `translateX(${(1 - p) * 16}px)`,
                    }}
                  >
                    {f}
                  </div>
                );
              },
            )}
          </div>

          <TracedPacket d={shortLane} at={T_OPEN + 96} dur={90} size={38} label="one committed change" />
        </div>
      </AbsoluteFill>

      {/* exactly one route is described at a time */}
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 168, textAlign: "center" }}>
        {ROUTES.map((r) => {
          const on = frame >= r.at && frame < r.until;
          const p = on ? pop(frame, fps, r.at) : 0;
          const out = 1 - ramp(frame, [r.until - 14, r.until]);
          if (!on) return null;
          return (
            <div key={r.n} style={{ opacity: p * out, transform: `translateY(${(1 - p) * 14}px)` }}>
              <div
                style={{
                  fontFamily: font.mono,
                  fontSize: 12,
                  letterSpacing: 2.2,
                  textTransform: "uppercase",
                  color: c.faint,
                }}
              >
                route {r.n}
              </div>
              <div
                style={{
                  fontFamily: font.sans,
                  fontSize: 30,
                  fontWeight: 700,
                  color: r.ok ? c.greenInk : c.ink,
                  marginTop: 6,
                }}
              >
                {r.title}
              </div>
              <div
                style={{
                  fontFamily: font.mono,
                  fontSize: 17,
                  color: r.ok ? c.greenInk : c.redInk,
                  marginTop: 7,
                }}
              >
                {r.cost}
              </div>
            </div>
          );
        })}
      </div>

      {/* what has already been ruled out */}
      <div style={{ position: "absolute", left: 96, bottom: 84, display: "flex", gap: 12 }}>
        {retired.map((r) => (
          <span
            key={r.n}
            style={{
              fontFamily: font.mono,
              fontSize: 13,
              color: c.faint,
              textDecoration: "line-through",
              border: `1px solid ${c.border}`,
              borderRadius: 999,
              padding: "6px 14px",
              opacity: ramp(frame, [r.until, r.until + 16]),
            }}
          >
            {r.title}
          </span>
        ))}
      </div>

      {/* the measured latency, arriving as the traced packet lands */}
      <div
        style={{
          position: "absolute",
          right: 96,
          top: 78,
          textAlign: "right",
          opacity: ramp(frame, [T_OPEN + 150, T_OPEN + 172]),
          transform: `translateY(${ramp(frame, [T_OPEN + 150, T_OPEN + 176], [16, 0])}px)`,
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 12, justifyContent: "flex-end" }}>
          <Odometer to={151} at={T_OPEN + 152} dur={40} size={82} color={c.greenInk} />
          <span style={{ fontFamily: font.serifItalic, fontStyle: "italic", fontSize: 36, color: c.ink }}>
            seconds
          </span>
        </div>
        <div
          style={{
            fontFamily: font.mono,
            fontSize: 12,
            letterSpacing: 1.8,
            textTransform: "uppercase",
            color: c.muted,
            marginTop: 6,
          }}
        >
          commit to a queryable delta row, measured
        </div>
      </div>
    </AbsoluteFill>
  );
};
