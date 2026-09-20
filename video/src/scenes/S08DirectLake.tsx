/**
 * Scene 8. Choice three: Direct Lake, not Import. 420f / 14s.
 *
 * This is where the copy argument actually lives. Both this route and a T-SQL
 * route persist a mirror and a gold layer, so neither is "one copy". What
 * Direct Lake removes is the third copy, the one Import holds in the model,
 * and the refresh window that comes with it.
 */
import React from "react";
import { useCurrentFrame } from "remotion";
import { Paper, Mono, Display, Line, Stage, ramp } from "../components/Primitives";
import { DataTable, Badge, Phase } from "../components/Blocks";
import { Icon } from "../components/Icon";
import { c, font } from "../theme";

/** A stack of copies, drawn as plates. */
const Copies: React.FC<{
  x: number;
  title: string;
  sub: string;
  plates: Array<{ t: string; third?: boolean }>;
  at: number;
  tone: "amber" | "green";
}> = ({ title, sub, plates, at, tone }) => {
  const frame = useCurrentFrame();
  const p = ramp(frame, [at, at + 22]);
  const accent = tone === "green" ? c.greenInk : c.amberInk;
  return (
    <div
      style={{
        flex: 1,
        opacity: p,
        transform: `translateY(${(1 - p) * 20}px)`,
      }}
    >
      <div
        style={{
          fontFamily: font.mono,
          fontSize: 17,
          letterSpacing: 2,
          textTransform: "uppercase",
          fontWeight: 700,
          color: accent,
          marginBottom: 6,
        }}
      >
        {title}
      </div>
      <div style={{ fontFamily: font.sans, fontSize: 22, color: c.muted, marginBottom: 20 }}>
        {sub}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {plates.map((pl, i) => {
          const t = at + 20 + i * 14;
          const pp = ramp(frame, [t, t + 18]);
          return (
            <div
              key={pl.t}
              style={{
                background: pl.third ? c.amberBg : c.white,
                border: `1px solid ${pl.third ? c.amberLine : c.border}`,
                borderRadius: 12,
                padding: "18px 22px",
                fontFamily: font.mono,
                fontSize: 23,
                color: pl.third ? c.amberInk : c.body,
                fontWeight: pl.third ? 700 : 500,
                opacity: pp,
                transform: `translateX(${(1 - pp) * 14}px)`,
              }}
            >
              {pl.t}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export const S08DirectLake: React.FC = () => {
  const frame = useCurrentFrame();
  const OUT = 188;
  const IN = 208;

  return (
    <Paper drift={2900}>
      <Stage n="07" label="Choice three" at={0} />

      <Phase out={OUT} style={{ padding: "156px 130px 90px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 18, marginBottom: 18 }}>
          <Icon name="semantic" size={42} />
          <Icon name="powerbi" size={40} />
        </div>

        <Display text="The copy worth arguing about is the third one." at={4} size={58} italicFrom={5} />

        <div>
          <Line at={22} size={25} color={c.muted} style={{ maxWidth: 1500, marginTop: 16 }}>
            A gold layer gets materialised either way, into a lakehouse here or
            into warehouse storage there. Both persist. This is the one that does
            not have to exist.
          </Line>

          <div style={{ display: "flex", gap: 70, marginTop: 44 }}>
            <Copies
              x={0}
              at={48}
              tone="amber"
              title="Import"
              sub="rebuilt on a schedule, stale in between"
              plates={[
                { t: "1  mirrored raw Delta" },
                { t: "2  gold Delta" },
                { t: "3  a cached copy inside the model", third: true },
              ]}
            />
            <Copies
              x={0}
              at={86}
              tone="green"
              title="Direct Lake"
              sub="framing copies metadata, not data"
              plates={[
                { t: "1  mirrored raw Delta" },
                { t: "2  gold Delta, read in place" },
              ]}
            />
          </div>
        </div>
      </Phase>

      {/* what that costs to query */}
      <Phase at={IN} style={{ padding: "200px 130px 90px" }}>
        <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
          <Mono at={214} size={16} color={c.greenInk}>
            the report's own measures, over the full 49,406,792-row fact
          </Mono>
          <div style={{ height: 20 }} />

          <DataTable
            at={224}
            stagger={20}
            cols="1fr 200px"
            size={27}
            head={["Query", "Seconds"]}
            rows={[
              { cells: ["First query after a reframe, transcoding the fact into memory", "11.18"] },
              { cells: ["The same query, warm", "1.59"], hl: true },
              { cells: ["The page's own 2,508-cell cube, warm", "1.33"] },
            ]}
          />

          <div style={{ display: "flex", gap: 12, marginTop: 26 }}>
            <Badge tone="measured" at={292}>
              measured with sempy on the live model
            </Badge>
          </div>

          <div
            style={{
              marginTop: "auto",
              fontFamily: font.serifItalic,
              fontStyle: "italic",
              fontSize: 42,
              lineHeight: 1.28,
              color: c.greenInk,
              maxWidth: 1520,
              opacity: ramp(frame, [316, 344]),
              transform: `translateY(${ramp(frame, [316, 350], [18, 0])}px)`,
            }}
          >
            After the first query, every page of the report is a one-second
            question against fifty million rows.
          </div>
        </div>
      </Phase>
    </Paper>
  );
};
