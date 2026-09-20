/**
 * Scene 8, the close. Proof, the stack, then the person.
 *
 * The numbers are the ones an acceptance pass re-measures on every run, so the
 * film ends on evidence rather than on a claim. The portrait is last and is
 * given real size: the piece is a portfolio artefact, and a byline in 24px type
 * is not a signature.
 */
import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";
import { Paper, Mono, Display, Card, ramp } from "../components/Primitives";
import { Icon, IconKey } from "../components/Icon";
import { c, font } from "../theme";

const PROOF: Array<[string, string, boolean]> = [
  ["39 / 39", "acceptance checks pass", true],
  ["0", "orphan dimension keys", true],
  ["3 runs", "identical, rule by rule", true],
  ["$0.27", "per full rebuild", true],
];

const STACK: Array<[IconKey, string]> = [
  ["postgres", "PostgreSQL"],
  ["fabric", "Fabric"],
  ["duckdb", "DuckDB"],
  ["spark", "Spark"],
  ["semantic", "Direct Lake"],
  ["powerbi", "Power BI"],
];

export const S8Close: React.FC = () => {
  const frame = useCurrentFrame();
  const photo = ramp(frame, [96, 130]);

  return (
    <Paper drift={2800}>
      <AbsoluteFill style={{ padding: "96px 110px 88px", display: "flex", flexDirection: "column" }}>
        <Mono at={0} size={16} color={c.greenInk}>
          nothing here is asserted, all of it is measured
        </Mono>
        <div style={{ height: 22 }} />
        <Display text="Proved on every run." at={6} size={66} italicFrom={2} />

        <div style={{ display: "flex", gap: 18, marginTop: 34 }}>
          {PROOF.map(([n, l, good], i) => (
            <Card key={l} at={30 + i * 7} style={{ padding: "22px 26px", flex: 1 }}>
              <div
                style={{
                  fontFamily: font.mono,
                  fontWeight: 700,
                  fontSize: 44,
                  color: good ? c.greenInk : c.ink,
                  letterSpacing: -1,
                }}
              >
                {n}
              </div>
              <div
                style={{
                  fontFamily: font.mono,
                  fontSize: 14,
                  letterSpacing: 1.3,
                  textTransform: "uppercase",
                  color: c.muted,
                  marginTop: 5,
                }}
              >
                {l}
              </div>
            </Card>
          ))}
        </div>

        {/* the stack, in real vendor marks */}
        <div
          style={{
            display: "flex",
            gap: 40,
            marginTop: 44,
            alignItems: "center",
            paddingBottom: 40,
            borderBottom: `1px solid ${c.border}`,
          }}
        >
          {STACK.map(([k, label], i) => {
            const at = 64 + i * 5;
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
                <Icon name={k} size={34} />
                <span style={{ fontFamily: font.sans, fontSize: 21, color: c.body, fontWeight: 500 }}>
                  {label}
                </span>
              </div>
            );
          })}
        </div>

        <div style={{ height: 52 }} />

        {/* the signature */}
        <div style={{ display: "flex", alignItems: "flex-end", gap: 44 }}>
          <div
            style={{
              width: 240,
              height: 300,
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
                fontSize: 74,
                color: c.ink,
                lineHeight: 1,
                opacity: ramp(frame, [108, 132]),
                transform: `translateY(${ramp(frame, [108, 138], [18, 0])}px)`,
              }}
            >
              Sulaiman Ahmed
              <span style={{ color: c.green }}>.</span>
            </div>
            <div
              style={{
                fontFamily: font.sans,
                fontSize: 27,
                color: c.muted,
                marginTop: 14,
                opacity: ramp(frame, [118, 142]),
              }}
            >
              Analytics Engineer &middot; Microsoft Fabric, Power BI, DuckDB
            </div>
            <div
              style={{
                display: "flex",
                gap: 36,
                marginTop: 26,
                opacity: ramp(frame, [128, 152]),
              }}
            >
              <span style={{ fontFamily: font.mono, fontSize: 22, color: c.greenInk, fontWeight: 500 }}>
                github.com/sulaiman013/fabric-x-duckdb
              </span>
              <span style={{ fontFamily: font.mono, fontSize: 22, color: c.muted }}>
                sulaimanahmed.dev
              </span>
            </div>
          </div>
        </div>
      </AbsoluteFill>
    </Paper>
  );
};
