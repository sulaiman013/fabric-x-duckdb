/**
 * Scene 4. Choice one: mirroring, not an export. 660f / 22s.
 *
 * v2 showed mirroring as a hop on a diagram and never said why it was there.
 * This puts the three alternatives on screen with what each one costs, greys
 * them out as their cost lands, and ends on the one number that can only be
 * produced by a working mirror: source to Delta, checked by value.
 */
import React from "react";
import { useCurrentFrame } from "remotion";
import { Paper, Mono, Display, Line, Stage, ramp } from "../components/Primitives";
import { DataTable, Badge, Caveat, Phase } from "../components/Blocks";
import { Icon } from "../components/Icon";
import { c, font } from "../theme";

const ROWS = [
  {
    cells: [
      "Nightly full export",
      "10.5 GB moved every night, about 3.8 TB a year. Up to 24 hours stale. A delete needs a full reload.",
    ],
    at: 54,
    out: 96,
  },
  {
    cells: [
      "Scheduled incremental copy",
      "Needs an inbound connection to the source, and a watermark you trust. Misses hard deletes entirely.",
    ],
    at: 78,
    out: 126,
  },
  {
    cells: [
      "Native mirroring for PostgreSQL",
      "Not available here. This source is on localhost. Fabric cannot reach it.",
    ],
    at: 102,
    out: 152,
  },
  {
    cells: [
      "Open mirroring",
      "The publisher pushes, so nothing connects inward. Seed once, then only changes move. Insert, update and delete, through __rowMarker__.",
    ],
    at: 126,
    hl: true,
  },
];

export const S04Mirror: React.FC = () => {
  const frame = useCurrentFrame();
  // the routes clear as the measurement arrives. Both halves are Phases, so
  // the headline leaves with the table it belongs to.
  const OUT = 372;
  const IN = 392;

  return (
    <Paper drift={1300}>
      <Stage n="03" label="Choice one" at={0} />

      <Phase out={OUT} style={{ padding: "156px 120px 90px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 18, marginBottom: 20 }}>
          <Icon name="postgres" size={44} />
          <div style={{ width: 46, height: 1, background: c.border }} />
          <Icon name="mirror" size={42} />
          <div style={{ width: 46, height: 1, background: c.border }} />
          <Icon name="lakehouse" size={42} />
        </div>

        <Display text="Mirror it. Don't export it." at={4} size={70} italicFrom={2} />

        <div style={{ marginTop: 34 }}>
          <Line at={22} size={27} color={c.muted} style={{ maxWidth: 1420, marginBottom: 26 }}>
            Four ways to get an on-premises table into OneLake, and what each one
            actually costs.
          </Line>

          <DataTable
            at={40}
            cols="440px 1fr"
            size={25}
            align={["left", "left"]}
            mono={[false, false]}
            head={["Route", "What it costs"]}
            rows={ROWS}
          />
        </div>
      </Phase>

      {/* the number only a working mirror can produce */}
      <Phase at={IN} style={{ padding: "200px 120px 90px" }}>
        <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
          <Mono at={400} size={16} color={c.greenInk}>
            source to delta, checked by value on every acceptance run
          </Mono>
          <div style={{ height: 22 }} />

          <div style={{ display: "flex", alignItems: "baseline", gap: 26 }}>
            <div
              style={{
                fontFamily: font.mono,
                fontWeight: 700,
                fontSize: 176,
                letterSpacing: -4,
                color: c.greenInk,
                opacity: ramp(frame, [406, 432]),
                transform: `translateY(${ramp(frame, [406, 440], [26, 0])}px)`,
              }}
            >
              151
            </div>
            <div
              style={{
                fontFamily: font.serifItalic,
                fontStyle: "italic",
                fontSize: 74,
                color: c.ink,
                opacity: ramp(frame, [424, 446]),
              }}
            >
              seconds
            </div>
            <div style={{ marginLeft: 14 }}>
              <Badge tone="measured" at={436} size={16}>
                measured
              </Badge>
            </div>
          </div>

          <Line at={450} size={30} color={c.body} style={{ maxWidth: 1340, marginTop: 20 }}>
            A row updated in PostgreSQL, carried through the write-ahead log into
            the landing zone, and read back out of a Delta table in OneLake by
            its value. Not by a row count. The acceptance pass writes a fresh
            token and looks for that token.
          </Line>

          <Caveat at={486} size={26} style={{ marginTop: 40, maxWidth: 1440 }}>
            <b>The scar.</b> Create the replication slot <b>before</b> the
            snapshot. Do it the other way and every change in the gap is lost
            with no error, and the row counts still match, so nothing tells you.
          </Caveat>

          <div
            style={{
              marginTop: "auto",
              paddingTop: 26,
              fontFamily: font.sans,
              fontSize: 22,
              color: c.faint,
              opacity: ramp(frame, [530, 556]),
            }}
          >
            Replication compute is free and does not draw on capacity. Mirrored
            storage is free to one terabyte per capacity unit purchased.
            Microsoft Learn, <i>What is Mirroring in Fabric</i>.
          </div>
        </div>
      </Phase>
    </Paper>
  );
};
