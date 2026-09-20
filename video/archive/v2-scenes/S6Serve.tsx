/**
 * Scene 6, serving. Short on purpose: it is a hinge between the cost argument
 * and the payoff, and the one idea it carries is that nothing was copied. The
 * latency bar fills once and stops, so the eye reads "done" rather than "loading".
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Paper, Mono, Display, Line, Card, Stage, ramp } from "../components/Primitives";
import { Icon } from "../components/Icon";
import { c, font } from "../theme";

export const S6Serve: React.FC = () => {
  const frame = useCurrentFrame();
  const fill = ramp(frame, [78, 112]);
  const secs = ramp(frame, [78, 112], [0, 0.98]);

  return (
    <Paper drift={2000}>
      <Stage n="05" label="Serve" at={0} />
      <AbsoluteFill style={{ padding: "176px 120px 96px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          <div style={{ opacity: ramp(frame, [0, 16]), display: "flex", gap: 12 }}>
            <Icon name="lakehouse" size={54} />
            <Icon name="semantic" size={54} />
          </div>
          <Display text="One copy. No import." at={4} size={76} italicFrom={2} />
        </div>
        <div style={{ height: 18 }} />
        <Line at={24} size={28} color={c.muted} style={{ maxWidth: 1060 }}>
          Direct Lake reads the same Delta files the notebook wrote. Nothing is
          imported, nothing refreshes on a schedule, and the extra copy a
          warehouse path would need is never made.
        </Line>

        <div style={{ display: "flex", gap: 30, marginTop: 56 }}>
          {[
            ["9", "tables"],
            ["8", "relationships"],
            ["17", "measures"],
            ["0", "copies made"],
          ].map(([n, l], i) => (
            <Card key={l} at={44 + i * 7} style={{ padding: "26px 34px", minWidth: 210 }}>
              <div
                style={{
                  fontFamily: font.mono,
                  fontWeight: 700,
                  fontSize: 58,
                  color: l === "copies made" ? c.greenInk : c.ink,
                }}
              >
                {n}
              </div>
              <div
                style={{
                  fontFamily: font.mono,
                  fontSize: 15,
                  letterSpacing: 1.6,
                  textTransform: "uppercase",
                  color: c.muted,
                  marginTop: 4,
                }}
              >
                {l}
              </div>
            </Card>
          ))}
        </div>

        <div style={{ flex: 1 }} />

        {/* the query: one bar that fills and stops */}
        <Card at={70} tone="green" style={{ padding: "30px 36px", maxWidth: 1420 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <Mono at={74} size={15} color={c.greenInk}>
              a page of the report, warm, over the full fact
            </Mono>
            <div
              style={{
                fontFamily: font.mono,
                fontWeight: 700,
                fontSize: 46,
                color: c.greenInk,
                opacity: ramp(frame, [78, 92]),
              }}
            >
              {secs.toFixed(2)}s
            </div>
          </div>
          <div
            style={{
              marginTop: 16,
              height: 12,
              background: c.white,
              border: `1px solid ${c.greenLine}`,
              borderRadius: 999,
              overflow: "hidden",
            }}
          >
            <div style={{ height: 12, width: `${fill * 100}%`, background: c.green }} />
          </div>
          <div style={{ marginTop: 14 }}>
            <Line at={116} size={24} color={c.body}>
              49,406,792 rows. The first query after a reframe pays 7 to 11
              seconds to transcode; every one after that is about a second.
            </Line>
          </div>
        </Card>
      </AbsoluteFill>
    </Paper>
  );
};
