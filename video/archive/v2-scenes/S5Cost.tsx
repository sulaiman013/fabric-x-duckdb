/**
 * Scene 5, the cost. The film's second load-bearing moment. Two bars race and
 * one stops at half, which is the entire argument in one gesture. The modelled
 * bar is labelled modelled on screen, because the comparison is only worth
 * anything if the film is honest about which half was measured.
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Paper, Mono, Display, Line, Stage, CountUp, ramp } from "../components/Primitives";
import { Icon, IconKey } from "../components/Icon";
import { c, font } from "../theme";

const Bar: React.FC<{
  at: number;
  icon: IconKey;
  label: string;
  sub: string;
  cuh: number;
  max: number;
  color: string;
  track: string;
  tag?: string;
}> = ({ at, icon, label, sub, cuh, max, color, track, tag }) => {
  const frame = useCurrentFrame();
  const grow = ramp(frame, [at, at + 46]);
  return (
    <div style={{ marginBottom: 40, opacity: ramp(frame, [at - 8, at + 8]) }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <Icon name={icon} size={34} />
          <span style={{ fontFamily: font.sans, fontSize: 30, fontWeight: 700, color: c.ink }}>
            {label}
          </span>
          <span style={{ fontFamily: font.mono, fontSize: 19, color: c.muted }}>{sub}</span>
          {tag ? (
            <span
              style={{
                fontFamily: font.mono,
                fontSize: 14,
                letterSpacing: 1.4,
                textTransform: "uppercase",
                color: c.amberInk,
                background: c.amberBg,
                border: `1px solid ${c.amberLine}`,
                borderRadius: 999,
                padding: "3px 10px",
              }}
            >
              {tag}
            </span>
          ) : null}
        </div>
        <span style={{ fontFamily: font.mono, fontSize: 26, fontWeight: 700, color }}>
          {(cuh * grow).toFixed(3)} CU-h
        </span>
      </div>
      <div style={{ height: 40, background: track, borderRadius: 8, overflow: "hidden" }}>
        <div style={{ height: 40, width: `${(cuh / max) * 100 * grow}%`, background: color }} />
      </div>
    </div>
  );
};

export const S5Cost: React.FC = () => {
  return (
    <Paper drift={1600}>
      <Stage n="04" label="What it costs" at={0} />
      <AbsoluteFill style={{ padding: "176px 120px 96px" }}>
        <Display text="Half the rate. No shuffle." at={4} size={76} italicFrom={2} />
        <div style={{ height: 18 }} />
        <Line at={24} size={28} color={c.muted} style={{ maxWidth: 1080 }}>
          A Python notebook at 8 vCores bills 4 CU. The Spark starter pool bills
          a documented minimum of 8. Same work, half the rate.
        </Line>

        <div style={{ marginTop: 58, maxWidth: 1420 }}>
          <Bar
            at={44}
            icon="duckdb"
            label="DuckDB"
            sub="Python notebook · 8 vCores · 4 CU"
            cuh={0.994}
            max={1.989}
            color={c.green}
            track={c.greenBg}
          />
          <Bar
            at={80}
            icon="spark"
            label="Spark"
            sub="starter pool · 8 CU · same wall time"
            cuh={1.989}
            max={1.989}
            color={c.amber}
            track={c.amberBg}
            tag="modelled"
          />
        </div>

        <div style={{ flex: 1 }} />

        <div style={{ display: "flex", alignItems: "flex-end", gap: 70 }}>
          <div>
            <Mono at={140} size={15}>a full rebuild, end to end</Mono>
            <div style={{ height: 6 }} />
            <CountUp to={0.27} at={142} dur={40} decimals={2} prefix="$" size={126} color={c.greenInk} />
          </div>
          <Line at={168} size={26} color={c.body} style={{ maxWidth: 760, paddingBottom: 18 }}>
            1.512 CU-hours for the whole pipeline. The alternative is modelled,
            and deliberately tilted in its favour: it assumes Spark matches
            DuckDB's wall time, when a distributed engine on a single-node job is
            usually slower.
          </Line>
        </div>
      </AbsoluteFill>
    </Paper>
  );
};
