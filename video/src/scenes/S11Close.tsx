/**
 * Scene 11. Proof, and the close. 480f / 16s.
 *
 * The acceptance figure here is read from UAT.json by verify_film.py, which is
 * the whole point: v2 shipped with 39 / 39 on screen months after the real
 * number became 36, because nothing checked.
 */
import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";
import { Paper, Mono, Display, Line, ramp } from "../components/Primitives";
import { Stat } from "../components/Blocks";
import { Icon, IconKey } from "../components/Icon";
import { c, font } from "../theme";

/**
 * Checked against UAT.json on every build. Do not edit by hand: change the
 * pipeline, re-run the pass, and let the verifier tell you these are stale.
 */
export const PROOF: Array<[string, string]> = [
  ["36 / 36", "acceptance checks pass, 1 skipped"],
  ["0", "orphan dimension keys"],
  ["3 runs", "identical, rule by rule"],
  ["$0.27", "per full rebuild"],
];

const STACK: Array<[IconKey, string]> = [
  ["postgres", "PostgreSQL"],
  ["fabric", "Fabric"],
  ["duckdb", "DuckDB"],
  ["spark", "Spark"],
  ["semantic", "Direct Lake"],
  ["powerbi", "Power BI"],
];

export const S11Close: React.FC = () => {
  const frame = useCurrentFrame();
  const photo = ramp(frame, [206, 240]);

  return (
    <Paper drift={4100}>
      <AbsoluteFill
        style={{ padding: "84px 110px 76px", display: "flex", flexDirection: "column" }}
      >
        <Mono at={0} size={16} color={c.greenInk}>
          nothing here is asserted, all of it is measured
        </Mono>
        <div style={{ height: 18 }} />
        <Display text="Proved on every run." at={6} size={62} italicFrom={2} />

        <div style={{ display: "flex", gap: 18, marginTop: 30 }}>
          {PROOF.map(([n, l], i) => (
            <div
              key={l}
              style={{
                flex: 1,
                background: c.white,
                border: `1px solid ${c.border}`,
                borderRadius: 16,
                padding: "22px 26px",
                opacity: ramp(frame, [30 + i * 8, 52 + i * 8]),
                transform: `translateY(${ramp(frame, [30 + i * 8, 56 + i * 8], [22, 0])}px)`,
                boxShadow: "0 1px 2px rgba(22,29,17,.04), 0 12px 28px rgba(22,29,17,.05)",
              }}
            >
              <Stat value={n} label={l} at={30 + i * 8} size={42} tone="green" />
            </div>
          ))}
        </div>

        <Line at={72} size={24} color={c.body} style={{ marginTop: 26, maxWidth: 1640 }}>
          The pass re-measures the source, pushes a real UPDATE through the
          write-ahead log and reads it back out of OneLake by value, and is
          allowed to fail. It has failed. It caught a README that told the reader
          to build a broken mirror.
        </Line>

        {/* the stack, in real vendor marks */}
        <div
          style={{
            display: "flex",
            gap: 38,
            marginTop: 34,
            alignItems: "center",
            paddingBottom: 32,
            borderBottom: `1px solid ${c.border}`,
          }}
        >
          {STACK.map(([k, label], i) => {
            const at = 108 + i * 5;
            const p = ramp(frame, [at, at + 18]);
            return (
              <div
                key={k}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 11,
                  opacity: p,
                  transform: `translateY(${(1 - p) * 12}px)`,
                }}
              >
                <Icon name={k} size={32} />
                <span
                  style={{ fontFamily: font.sans, fontSize: 20, color: c.body, fontWeight: 500 }}
                >
                  {label}
                </span>
              </div>
            );
          })}
        </div>

        <div style={{ flex: 1 }} />

        {/* the signature */}
        <div style={{ display: "flex", alignItems: "flex-end", gap: 44 }}>
          <div
            style={{
              width: 234,
              height: 292,
              borderRadius: 20,
              overflow: "hidden",
              border: `1px solid ${c.border}`,
              flex: "0 0 auto",
              opacity: photo,
              transform: `translateY(${(1 - photo) * 26}px) scale(${0.96 + photo * 0.04})`,
              boxShadow: "0 2px 6px rgba(22,29,17,.06), 0 22px 48px rgba(22,29,17,.12)",
            }}
          >
            <Img
              src={staticFile("me/sulaiman-portrait.jpeg")}
              style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
            />
          </div>

          <div style={{ flex: 1, paddingBottom: 6 }}>
            <div
              style={{
                fontFamily: font.serif,
                fontSize: 72,
                color: c.ink,
                lineHeight: 1,
                opacity: ramp(frame, [220, 244]),
                transform: `translateY(${ramp(frame, [220, 250], [18, 0])}px)`,
              }}
            >
              Sulaiman Ahmed
              <span style={{ color: c.green }}>.</span>
            </div>
            <div
              style={{
                fontFamily: font.sans,
                fontSize: 26,
                color: c.muted,
                marginTop: 14,
                opacity: ramp(frame, [230, 254]),
              }}
            >
              Analytics Engineer &middot; Microsoft Fabric, Power BI, DuckDB
            </div>
            <div
              style={{
                display: "flex",
                gap: 36,
                marginTop: 24,
                opacity: ramp(frame, [240, 264]),
              }}
            >
              <span
                style={{ fontFamily: font.mono, fontSize: 21, color: c.greenInk, fontWeight: 500 }}
              >
                github.com/sulaiman013/fabric-x-duckdb
              </span>
              <span style={{ fontFamily: font.mono, fontSize: 21, color: c.muted }}>
                sulaimanahmed.dev
              </span>
            </div>
          </div>
        </div>
      </AbsoluteFill>
    </Paper>
  );
};
