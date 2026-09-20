/**
 * Real vendor icons, not approximations.
 *
 * The Fabric item icons (Lakehouse, Notebook, MirroredDatabase, SemanticModel,
 * Report) and the Fabric mark come from Microsoft's own @fabric-msft/svg-icons
 * package and keep their original gradients, so they are loaded as files.
 * PostgreSQL, DuckDB and Apache Spark come from simple-icons as single paths
 * and are inlined so they can be tinted with their documented brand colour.
 *
 * Power BI comes from microsoft/PowerBI-Icons.
 */
import React from "react";
import { Img, staticFile, useCurrentFrame } from "remotion";
import { MARKS, BRAND } from "./marks";
import { ramp } from "./Primitives";

export type IconKey =
  | "postgres"
  | "duckdb"
  | "spark"
  | "fabric"
  | "lakehouse"
  | "notebook"
  | "mirror"
  | "semantic"
  | "report"
  | "powerbi";

const FILES: Partial<Record<IconKey, string>> = {
  fabric: "icons/fabric_48_color.svg",
  lakehouse: "icons/lakehouse_32_item.svg",
  notebook: "icons/notebook_32_item.svg",
  mirror: "icons/mirrored_generic_database_32_item.svg",
  semantic: "icons/semantic_model_32_item.svg",
  report: "icons/report_32_item.svg",
  powerbi: "icons/pbi_Power-BI.svg",
};

export const Icon: React.FC<{ name: IconKey; size?: number; style?: React.CSSProperties }> = ({
  name,
  size = 44,
  style,
}) => {
  const mark = MARKS[name];
  if (mark) {
    return (
      <svg
        viewBox="0 0 24 24"
        width={size}
        height={size}
        style={{ display: "block", ...style }}
        aria-hidden
      >
        <path d={mark} fill={BRAND[name as keyof typeof BRAND]} />
      </svg>
    );
  }
  const file = FILES[name];
  if (!file) return null;
  return (
    <Img
      src={staticFile(file)}
      style={{ width: size, height: size, display: "block", ...style }}
    />
  );
};

/** An icon on the brand plate, which is how the diagram presents them. */
export const IconPlate: React.FC<{
  name: IconKey;
  at?: number;
  size?: number;
  plate?: number;
}> = ({ name, at = 0, size = 46, plate = 76 }) => {
  const frame = useCurrentFrame();
  const p = ramp(frame, [at, at + 20]);
  return (
    <div
      style={{
        width: plate,
        height: plate,
        borderRadius: plate * 0.26,
        background: "#D1E1BC",
        border: "1px solid #83A463",
        display: "grid",
        placeItems: "center",
        opacity: p,
        transform: `scale(${0.82 + p * 0.18})`,
        flex: "0 0 auto",
      }}
    >
      <Icon name={name} size={size} />
    </div>
  );
};
