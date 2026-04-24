import type { HistogramBinOut } from "@/lib/types";

const WIDTH = 480;
const HEIGHT = 180;
const PAD = { top: 8, right: 12, bottom: 28, left: 44 };

export function Histogram({
  bins,
  highlights = [],
  unit = "",
  valueFormatter,
}: {
  bins: HistogramBinOut[];
  highlights?: { x: number; label: string; color?: string }[];
  unit?: string;
  valueFormatter?: (v: number) => string;
}) {
  if (bins.length === 0) {
    return (
      <div className="flex h-[180px] items-center justify-center border border-border bg-panel-2 text-[11px] text-fg-faint">
        No samples.
      </div>
    );
  }

  const plotW = WIDTH - PAD.left - PAD.right;
  const plotH = HEIGHT - PAD.top - PAD.bottom;
  const xMin = bins[0].low;
  const xMax = bins[bins.length - 1].high;
  const xRange = xMax - xMin || 1;
  const yMax = Math.max(...bins.map((b) => b.count)) || 1;

  const x = (v: number) => PAD.left + ((v - xMin) / xRange) * plotW;
  const y = (v: number) => PAD.top + plotH - (v / yMax) * plotH;
  const fmt = valueFormatter ?? ((v: number) => `${v.toFixed(2)}${unit}`);

  return (
    <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full" role="img">
      <rect x={0} y={0} width={WIDTH} height={HEIGHT} fill="var(--bg-panel-2)" />

      {/* Bars */}
      {bins.map((b, i) => {
        const bw = x(b.high) - x(b.low);
        return (
          <rect
            key={i}
            x={x(b.low)}
            y={y(b.count)}
            width={Math.max(0.5, bw - 0.5)}
            height={PAD.top + plotH - y(b.count)}
            fill="rgba(92,213,255,0.6)"
          />
        );
      })}

      {/* Highlight verticals (quantiles, current price, etc.) */}
      {highlights.map((h, i) => {
        if (h.x < xMin || h.x > xMax) return null;
        return (
          <g key={`hl-${i}`}>
            <line
              x1={x(h.x)}
              x2={x(h.x)}
              y1={PAD.top}
              y2={HEIGHT - PAD.bottom}
              stroke={h.color ?? "var(--accent)"}
              strokeDasharray="3,3"
              strokeWidth={1}
            />
            <text
              x={x(h.x)}
              y={PAD.top + 9}
              fontSize="9"
              fill={h.color ?? "var(--accent)"}
              textAnchor="middle"
              fontFamily="var(--font-mono)"
            >
              {h.label}
            </text>
          </g>
        );
      })}

      {/* X axis ticks: min / mid / max */}
      {[xMin, (xMin + xMax) / 2, xMax].map((t) => (
        <text
          key={t}
          x={x(t)}
          y={HEIGHT - PAD.bottom + 14}
          fontSize="9"
          fill="var(--text-dim)"
          textAnchor="middle"
          fontFamily="var(--font-mono)"
        >
          {fmt(t)}
        </text>
      ))}

      {/* Y axis label */}
      <text
        x={PAD.left - 6}
        y={y(yMax)}
        fontSize="9"
        fill="var(--text-dim)"
        textAnchor="end"
        dominantBaseline="central"
        fontFamily="var(--font-mono)"
      >
        {yMax}
      </text>
      <text
        x={PAD.left - 6}
        y={y(0)}
        fontSize="9"
        fill="var(--text-dim)"
        textAnchor="end"
        dominantBaseline="central"
        fontFamily="var(--font-mono)"
      >
        0
      </text>
    </svg>
  );
}
