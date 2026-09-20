/**
 * Scene 6. Choice two: DuckDB, and where it loses. 1080f / 36s.
 *
 * The longest scene, because it is the one v2 never made. Five beats:
 * the precondition, the CU rate with its concession attached, the measurement,
 * where the Warehouse route genuinely wins, and the reason to take this one
 * anyway.
 *
 * The concession beat is not a disclaimer. It is the beat that makes the other
 * four believable.
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Paper, Mono, Display, Line, Stage, ramp } from "../components/Primitives";
import { DataTable, Badge, Caveat, Stat, CodePane } from "../components/Blocks";
import { Icon } from "../components/Icon";
import { c, font } from "../theme";

/** One beat of the argument, cross-faded against its neighbours. */
const Beat: React.FC<{
  at: number;
  dur: number;
  children: React.ReactNode;
  pad?: string;
}> = ({ at, dur, children, pad = "150px 120px 88px" }) => {
  const frame = useCurrentFrame();
  const inP = ramp(frame, [at, at + 18]);
  const outP = 1 - ramp(frame, [at + dur - 14, at + dur + 2]);
  const o = inP * outP;
  if (o <= 0.002) return null;
  return (
    <AbsoluteFill style={{ padding: pad, opacity: o }}>
      <div style={{ transform: `translateY(${(1 - inP) * 18}px)`, height: "100%", display: "flex", flexDirection: "column" }}>
        {children}
      </div>
    </AbsoluteFill>
  );
};

const A = 0;     // precondition
const B = 180;   // the rate
const C = 392;   // the measurement
const D = 632;   // where the warehouse wins
const E = 872;   // why this one anyway

const TSQL = [
  { t: "COALESCE(" },
  { t: "  TRY_CONVERT(date, v, 23),   -- 2024-03-11" },
  { t: "  TRY_CONVERT(date, v, 103),  -- 11/03/2024" },
  { t: "  TRY_CONVERT(date, v, 107),  -- Mar 11 2024" },
  { t: "  TRY_CONVERT(date, v, 102),  -- 2024.03.11" },
  { t: "  TRY_CONVERT(date, v, 112)   -- 20240311" },
  { t: ")" },
  { t: "-- one branch per format, and still" },
  { t: "-- nothing here for 1750529113", dim: true },
];

const DUCK = [
  { t: "COALESCE(" },
  { t: "  try_strptime(v, ['%Y-%m-%d', '%d/%m/%Y',", hl: true },
  { t: "                  '%b %d %Y', '%Y.%m.%d', '%Y%m%d']),", hl: true },
  { t: "  CASE WHEN regexp_matches(v, '^[0-9]{9,11}$')" },
  { t: "       THEN make_timestamp(" },
  { t: "              TRY_CAST(v AS BIGINT) * 1000000)" },
  { t: "  END" },
  { t: ")" },
  { t: "-- the format list is the spec, in one place", dim: true },
];

export const S06Duck: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <Paper drift={2100}>
      <Stage n="05" label="Choice two" at={0} />

      {/* ---------------------------------------------- 6a. the precondition */}
      <Beat at={A} dur={196}>
        <Display text="It fits on one node." at={A + 4} size={72} italicFrom={4} />
        <div style={{ height: 18 }} />
        <Line at={A + 16} size={28} color={c.muted} style={{ maxWidth: 1420 }}>
          Everything in this scene depends on that sentence being true, so it is
          the first thing measured, not the last.
        </Line>

        <div style={{ display: "flex", gap: 68, marginTop: 58, flexWrap: "wrap" }}>
          <Stat at={A + 36} value="8" label="vCores" size={68} />
          <Stat at={A + 46} value="67.4 GB" label="RAM on the node" size={68} />
          <Stat at={A + 56} value="47 GB" label="DuckDB memory cap" size={68} />
          <Stat at={A + 66} value="1.2.2" label="DuckDB version" size={68} />
        </div>

        <div style={{ display: "flex", gap: 68, marginTop: 52, flexWrap: "wrap" }}>
          <Stat at={A + 84} value="10.5 GB" label="compressed source" size={68} tone="green" />
          <Stat at={A + 94} value="48 GB" label="as held in PostgreSQL" size={68} />
          <Stat at={A + 104} value="100" label="text columns" size={68} />
          <Stat at={A + 114} value="false" label="spark in globals" size={68} tone="green" />
        </div>

        <div style={{ marginTop: "auto", display: "flex", gap: 12 }}>
          <Badge tone="measured" at={A + 130}>
            all read from the build's own evidence file
          </Badge>
        </div>
      </Beat>

      {/* ------------------------------------------------------ 6b. the rate */}
      <Beat at={B} dur={226}>
        <Display text="What each engine bills." at={B + 4} size={64} italicFrom={2} />
        <div style={{ height: 30 }} />

        <DataTable
          at={B + 20}
          stagger={26}
          cols="1fr 200px"
          size={27}
          head={["Compute", "CU while running"]}
          rows={[
            { cells: ["Python notebook, 8 vCores", "4"], hl: true },
            { cells: ["Spark starter pool, default, after scale-up", "8 minimum"] },
            { cells: ["Spark single node at 8 vCores, if configured", "4"] },
          ]}
        />

        <div
          style={{
            marginTop: 26,
            fontFamily: font.sans,
            fontSize: 21,
            color: c.faint,
            opacity: ramp(frame, [B + 96, B + 116]),
          }}
        >
          Microsoft Learn, <i>Choosing a notebook kernel</i>. One capacity unit per two vCores.
        </div>

        <Caveat at={B + 126} size={29} style={{ marginTop: 40, maxWidth: 1560 }}>
          Against a <b>single-node</b> Spark session the rate is identical. The
          saving is against the <b>default starter pool</b>, which is what you get
          if you do not think about it.
        </Caveat>
      </Beat>

      {/* ----------------------------------------------- 6c. the measurement */}
      <Beat at={C} dur={254}>
        <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 26 }}>
          <Icon name="duckdb" size={44} />
          <Icon name="spark" size={40} />
        </div>
        <Display text="What it actually cost." at={C + 4} size={64} italicFrom={2} />
        <div style={{ height: 26 }} />

        <DataTable
          at={C + 18}
          stagger={22}
          cols="1fr 110px 150px 190px 180px"
          size={26}
          head={["Step", "CU", "Wall", "CU-hours", "at $0.18/CU-h"]}
          rows={[
            { cells: ["DuckDB transform, Python kernel", "4", "895 s", "0.994", "$0.18"] },
            { cells: ["V-Order write, Spark starter pool", "8", "233 s", "0.518", "$0.09"] },
            { cells: ["This pipeline", "", "", "1.512", "$0.27"], total: true, hl: true },
            {
              cells: ["Modelled alternative at 8 CU, same wall", "8", "895 s", "1.989", "$0.36"],
              at: C + 118,
            },
          ]}
        />

        <div style={{ display: "flex", gap: 12, marginTop: 34 }}>
          <Badge tone="measured" at={C + 146}>
            rows 1 to 3 measured
          </Badge>
          <Badge tone="modelled" at={C + 154}>
            row 4 modelled
          </Badge>
          <Badge tone="assumed" at={C + 162}>
            the rate is an assumption
          </Badge>
        </div>

        <Line at={C + 176} size={25} color={c.muted} style={{ maxWidth: 1560, marginTop: 28 }}>
          Capacity bills the session's wall time, startup included, not the
          seconds the cells were busy. So the wall column is the billed number,
          read live from the jobs API rather than typed in.
        </Line>
      </Beat>

      {/* -------------------------------------- 6d. where the warehouse wins */}
      <Beat at={D} dur={254}>
        <Mono at={D + 2} size={16} color={c.amberInk}>
          the part a portfolio piece usually leaves out
        </Mono>
        <div style={{ height: 16 }} />
        <Display text="Where the Warehouse route wins." at={D + 8} size={62} italicFrom={3} />

        <div style={{ display: "flex", flexDirection: "column", gap: 20, marginTop: 40 }}>
          <Caveat at={D + 30} size={27} style={{ maxWidth: 1620 }}>
            <b>V-Order is on by default in every warehouse.</b> This pipeline had
            to add a second notebook, 233 seconds and about nine cents, to get
            the same thing. Direct Lake cold queries are 40 to 60% faster with
            it, so skipping it was never an option.
          </Caveat>
          <Caveat at={D + 62} size={27} style={{ maxWidth: 1620 }}>
            <b>Warehouse compute autoscales.</b> Consumption is active vNodes
            times active time. You cannot pin it to 4 CU, which makes the
            alternative unpredictable rather than simply expensive.
          </Caveat>
          <Caveat at={D + 94} size={27} style={{ maxWidth: 1620 }}>
            <b>Microsoft puts the crossover at 10 to 13 GB compressed.</b> There,
            Fabric Spark with the Native Execution Engine is competitive with or
            faster than most single-machine engines, and single-machine Python
            engines start running out of memory.
          </Caveat>
        </div>

        <div
          style={{
            marginTop: "auto",
            display: "flex",
            alignItems: "baseline",
            gap: 22,
            opacity: ramp(frame, [D + 150, D + 176]),
          }}
        >
          <div
            style={{
              fontFamily: font.serifItalic,
              fontStyle: "italic",
              fontSize: 54,
              color: c.ink,
            }}
          >
            This dataset is 10.5 GB. It is on that line.
          </div>
        </div>
      </Beat>

      {/* --------------------------------------------- 6e. why this one anyway */}
      <Beat at={E} dur={214}>
        <Display text="The job is parsing, not aggregation." at={E + 4} size={58} italicFrom={3} />
        <div style={{ height: 14 }} />
        <Line at={E + 16} size={25} color={c.muted} style={{ maxWidth: 1500 }}>
          One column. Five date formats, and an epoch integer that is not a date
          at all.
        </Line>

        <div style={{ display: "flex", gap: 34, marginTop: 30, alignItems: "flex-start" }}>
          <CodePane
            at={E + 28}
            title="T-SQL"
            sub="Fabric Warehouse"
            lines={TSQL}
            size={18}
            style={{ flex: 1 }}
          />
          <CodePane
            at={E + 44}
            title="DuckDB"
            sub="this pipeline"
            tone="green"
            lines={DUCK}
            size={18}
            style={{ flex: 1 }}
          />
        </div>

        <div
          style={{
            marginTop: "auto",
            paddingTop: 26,
            fontFamily: font.serifItalic,
            fontStyle: "italic",
            fontSize: 38,
            lineHeight: 1.3,
            color: c.greenInk,
            maxWidth: 1620,
            opacity: ramp(frame, [E + 140, E + 166]),
          }}
        >
          The dialect is built for this. And the same file runs on my laptop
          against the same fifty million rows. A warehouse stored procedure does
          not.
        </div>
      </Beat>
    </Paper>
  );
};
