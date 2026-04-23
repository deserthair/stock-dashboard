import type { CommodityPricePoint } from "@/lib/types";

/** Pure-SVG price sparkline for a commodity series. */
export function CommoditySparkline({
  data,
  width = 240,
  height = 56,
  color = "#5cd5ff",
}: {
  data: CommodityPricePoint[];
  width?: number;
  height?: number;
  color?: string;
}) {
  const obs = data.filter((o) => o.close !== null);
  if (obs.length === 0) {
    return <div className="h-14 w-full bg-panel-2" />;
  }
  const values = obs.map((o) => o.close as number);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const pad = { top: 3, right: 2, bottom: 3, left: 2 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const points = obs
    .map((o, i) => {
      const x = pad.left + (i / Math.max(1, obs.length - 1)) * plotW;
      const y = pad.top + plotH - (((o.close as number) - min) / range) * plotH;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height}>
      <rect x={0} y={0} width={width} height={height} fill="var(--bg-panel-2)" />
      <polyline points={points} fill="none" stroke={color} strokeWidth={1.25} />
    </svg>
  );
}
