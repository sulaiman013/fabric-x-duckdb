/**
 * Scene 3, the architecture, built live.
 *
 * This is the architecture diagram from this repository, assembled on screen
 * rather than shown as a picture: the two platform containers draw themselves,
 * each node lands with its real vendor icon, and the wires grow between them
 * with packets riding the flow. Same palette, same node language, same rule
 * that vendor colour appears only on vendor marks.
 *
 * Everything is positioned on an 1800 x 560 stage so the coordinates read the
 * same way the diagram's own view files do.
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Paper, Mono, Display, Stage, ramp } from "../components/Primitives";
import { Icon, IconKey } from "../components/Icon";
import { c, font } from "../theme";

type NodeDef = {
  id: string;
  x: number;
  y: number;
  w: number;
  icon: IconKey;
  title: string;
  sub: string;
  at: number;
};

const NODES: NodeDef[] = [
  { id: "pg", x: 40, y: 96, w: 230, icon: "postgres", title: "PostgreSQL", sub: "50,000,001 rows", at: 30 },
  { id: "cdc", x: 330, y: 96, w: 230, icon: "mirror", title: "Open mirroring", sub: "WAL · __rowMarker__", at: 48 },
  { id: "lake", x: 620, y: 96, w: 230, icon: "lakehouse", title: "OneLake", sub: "raw_txn · Delta", at: 66 },
  { id: "duck", x: 910, y: 96, w: 250, icon: "duckdb", title: "01_build_gold", sub: "DuckDB · 8 vCores", at: 84 },
  { id: "spark", x: 910, y: 336, w: 250, icon: "spark", title: "02_vorder_write", sub: "V-Order · 233 s", at: 112 },
  { id: "model", x: 1220, y: 96, w: 230, icon: "semantic", title: "Direct Lake", sub: "9 tables · 17 measures", at: 138 },
  { id: "report", x: 1510, y: 96, w: 230, icon: "report", title: "FinCrime", sub: "4 pages", at: 158 },
];

/** Wires, as {from, to} pairs measured off the node boxes. */
const WIRES: Array<{ a: string; b: string; at: number; down?: boolean; up?: boolean }> = [
  { a: "pg", b: "cdc", at: 46 },
  { a: "cdc", b: "lake", at: 64 },
  { a: "lake", b: "duck", at: 82 },
  { a: "duck", b: "spark", at: 108, down: true },
  { a: "spark", b: "model", at: 134, up: true },
  { a: "model", b: "report", at: 156 },
];

const byId = (id: string) => NODES.find((n) => n.id === id)!;
const NODE_H = 132;

const Node: React.FC<{ n: NodeDef }> = ({ n }) => {
  const frame = useCurrentFrame();
  const p = ramp(frame, [n.at, n.at + 24]);
  return (
    <div
      style={{
        position: "absolute",
        left: n.x,
        top: n.y,
        width: n.w,
        height: NODE_H,
        background: c.white,
        border: `1px solid ${c.border}`,
        borderRadius: 16,
        padding: "16px 18px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        gap: 10,
        opacity: p,
        transform: `translateY(${(1 - p) * 20}px) scale(${0.95 + p * 0.05})`,
        boxShadow: "0 1px 2px rgba(22,29,17,.04), 0 10px 24px rgba(22,29,17,.05)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <div
          style={{
            width: 46,
            height: 46,
            borderRadius: 12,
            background: c.plate,
            border: `1px solid ${c.border}`,
            display: "grid",
            placeItems: "center",
            flex: "0 0 auto",
          }}
        >
          <Icon name={n.icon} size={28} />
        </div>
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              fontFamily: font.sans,
              fontSize: 21,
              fontWeight: 700,
              color: c.ink,
              whiteSpace: "nowrap",
            }}
          >
            {n.title}
          </div>
          <div
            style={{
              fontFamily: font.mono,
              fontSize: 14,
              color: c.muted,
              whiteSpace: "nowrap",
              marginTop: 2,
            }}
          >
            {n.sub}
          </div>
        </div>
      </div>
    </div>
  );
};

/** A wire that grows, marches, and carries packets. */
const Wire: React.FC<{ w: (typeof WIRES)[number] }> = ({ w }) => {
  const frame = useCurrentFrame();
  const A = byId(w.a);
  const B = byId(w.b);
  const grow = ramp(frame, [w.at, w.at + 24]);
  const t = Math.max(0, frame - w.at);

  if (w.down) {
    // straight drop from the DuckDB row into the Spark row
    const x = A.x + A.w / 2;
    const top = A.y + NODE_H;
    const h = B.y - top;
    return (
      <>
        <div
          style={{
            position: "absolute",
            left: x - 1,
            top,
            width: 2,
            height: h * grow,
            background: c.green,
          }}
        />
        {Array.from({ length: 2 }).map((_, i) => {
          const ph = (t / 46 + i / 2) % 1;
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: x - 5,
                top: top + h * grow * ph - 5,
                width: 10,
                height: 10,
                borderRadius: 999,
                background: c.green,
                border: `1.6px solid ${c.paper}`,
                opacity: grow,
              }}
            />
          );
        })}
      </>
    );
  }

  if (w.up) {
    // Spark sits a row below the model, so this wire is an L: out to the right
    // along Spark's own row, then up into the model's underside. Routing it
    // through the node row instead put the whole leg behind a card, which is
    // the same as not drawing it.
    const y = A.y + NODE_H / 2;
    const x1 = A.x + A.w;
    const xUp = B.x + B.w / 2;
    const hLen = xUp - x1;
    const vLen = y - (B.y + NODE_H);
    const total = hLen + vLen;
    const drawn = total * grow;
    return (
      <>
        <div
          style={{
            position: "absolute",
            left: x1,
            top: y - 1,
            width: Math.min(drawn, hLen),
            height: 2,
            background: c.green,
          }}
        />
        <div
          style={{
            position: "absolute",
            left: xUp - 1,
            top: y - Math.max(0, drawn - hLen),
            width: 2,
            height: Math.max(0, drawn - hLen),
            background: c.green,
          }}
        />
        {Array.from({ length: 2 }).map((_, i) => {
          const ph = (t / 52 + i / 2) % 1;
          const d = total * ph;
          const onH = d < hLen;
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: (onH ? x1 + d : xUp) - 5,
                top: (onH ? y : y - (d - hLen)) - 5,
                width: 10,
                height: 10,
                borderRadius: 999,
                background: c.green,
                border: `1.6px solid ${c.paper}`,
                opacity: grow,
              }}
            />
          );
        })}
      </>
    );
  }

  // horizontal run between two node boxes on the same row
  const x1 = A.x + A.w;
  const x2 = B.x;
  const y = A.y + NODE_H / 2;
  const len = x2 - x1;
  return (
    <>
      <div
        style={{
          position: "absolute",
          left: x1,
          top: y - 1,
          width: len * grow,
          height: 2,
          background: c.green,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: x1,
          top: y - 1,
          width: len * grow,
          height: 2,
          backgroundImage: `repeating-linear-gradient(90deg, ${c.greenHi} 0 10px, transparent 10px 22px)`,
          backgroundPositionX: `${-((t * 1.1) % 22)}px`,
        }}
      />
      {Array.from({ length: 2 }).map((_, i) => {
        const ph = (t / 40 + i / 2) % 1;
        const fade = ph < 0.1 ? ph / 0.1 : ph > 0.9 ? (1 - ph) / 0.1 : 1;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x1 + len * grow * ph - 5,
              top: y - 6,
              width: 10,
              height: 10,
              borderRadius: 999,
              background: c.green,
              border: `1.6px solid ${c.paper}`,
              opacity: grow * fade,
            }}
          />
        );
      })}
    </>
  );
};

/** One of the two platform containers the nodes sit inside. */
const Platform: React.FC<{
  x: number;
  y: number;
  w: number;
  h: number;
  at: number;
  icon: IconKey;
  label: string;
}> = ({ x, y, w, h, at, icon, label }) => {
  const frame = useCurrentFrame();
  const p = ramp(frame, [at, at + 26]);
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: w,
        height: h,
        border: `1px solid ${c.border}`,
        borderRadius: 20,
        background: "rgba(255,255,255,.34)",
        opacity: p,
        transform: `scale(${0.985 + p * 0.015})`,
      }}
    >
      <div
        style={{
          position: "absolute",
          left: 20,
          top: -14,
          display: "flex",
          alignItems: "center",
          gap: 9,
          background: c.paper,
          padding: "0 12px",
        }}
      >
        <Icon name={icon} size={20} />
        <span
          style={{
            fontFamily: font.mono,
            fontSize: 14,
            letterSpacing: 2,
            textTransform: "uppercase",
            color: c.muted,
            fontWeight: 600,
          }}
        >
          {label}
        </span>
      </div>
    </div>
  );
};

export const S3Arch: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <Paper drift={800}>
      <Stage n="02" label="The architecture" at={0} />

      <AbsoluteFill style={{ padding: "150px 60px 90px" }}>
        <div style={{ paddingLeft: 60 }}>
          <Display text="Mirror it. Don't export it." at={4} size={64} italicFrom={3} />
        </div>

        {/* the 1800-wide stage the diagram's own coordinates are written against */}
        <div
          style={{
            position: "relative",
            width: 1800,
            height: 640,
            marginTop: 46,
            marginLeft: -30,
          }}
        >
          <Platform x={10} y={60} at={16} w={860} h={228} icon="postgres" label="On-premises" />
          <Platform x={890} y={60} at={22} w={890} h={438} icon="fabric" label="Microsoft Fabric" />

          {WIRES.map((w) => (
            <Wire key={`${w.a}-${w.b}`} w={w} />
          ))}
          {NODES.map((n) => (
            <Node key={n.id} n={n} />
          ))}

          {/* the one number the ingestion leg is judged on */}
          <div
            style={{
              position: "absolute",
              left: 40,
              top: 330,
              opacity: ramp(frame, [178, 196]),
            }}
          >
            <Mono at={178} size={14}>commit to delta, measured</Mono>
            <div
              style={{
                fontFamily: font.mono,
                fontWeight: 700,
                fontSize: 62,
                color: c.greenInk,
                marginTop: 6,
              }}
            >
              151 s
            </div>
            <div
              style={{
                fontFamily: font.sans,
                fontSize: 21,
                color: c.body,
                maxWidth: 500,
                marginTop: 8,
              }}
            >
              An insert, update or delete in PostgreSQL, applied to a Delta table
              in OneLake. Create the slot before the snapshot, or the gap
              swallows changes silently.
            </div>
          </div>

          {/* what the Fabric half is actually holding, so the right side of the
              board is not dead space while the left side carries a number */}
          <div
            style={{
              position: "absolute",
              left: 950,
              top: 532,
              display: "flex",
              gap: 44,
              opacity: ramp(frame, [196, 214]),
            }}
          >
            {[
              ["9", "gold Delta tables"],
              ["2.5 GB", "V-Ordered"],
              ["1", "copy of the data"],
            ].map(([n, l], i) => (
              <div key={l}>
                <div
                  style={{
                    fontFamily: font.mono,
                    fontWeight: 700,
                    fontSize: 40,
                    color: i === 2 ? c.greenInk : c.ink,
                  }}
                >
                  {n}
                </div>
                <div
                  style={{
                    fontFamily: font.mono,
                    fontSize: 13,
                    letterSpacing: 1.3,
                    textTransform: "uppercase",
                    color: c.muted,
                    marginTop: 5,
                  }}
                >
                  {l}
                </div>
              </div>
            ))}
          </div>
        </div>
      </AbsoluteFill>
    </Paper>
  );
};
