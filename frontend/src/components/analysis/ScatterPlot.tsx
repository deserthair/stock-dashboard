"use client";

import { useMemo } from "react";

import type { ScatterResponse } from "@/lib/types";

const WIDTH = 620;
const HEIGHT = 320;
const PAD = { top: 16, right: 20, bottom: 36, left: 54 };

export function ScatterPlot({ data }: { data: ScatterResponse }) {
  const { points, line } = data;

  const { x, y, xTicks, yTicks, xLabel, yLabel } = useMemo(() => {
    if (points.length === 0) {
      return { x: (_: number) => 0, y: (_: number) => 0, xTicks: [], yTicks: [], xLabel: 0, yLabel: 0 };
    }
    const xs = points.map((p) => p.x);
    const ys = points.map((p) => p.y);
    const xMin = Math.min(...xs, line?.x_min ?? xs[0]);
    const xMax = Math.max(...xs, line?.x_max ?? xs[0]);
    const yMin = Math.min(...ys);
    const yMax = Math.max(...ys);
    // pad the domain a little so dots don't sit on the axis
    const xPad = (xMax - xMin) * 0.05 || 0.1;
    const yPad = (yMax - yMin) * 0.08 || 0.1;
    const xDomainMin = xMin - xPad;
    const xDomainMax = xMax + xPad;
    const yDomainMin = yMin - yPad;
    const yDomainMax = yMax + yPad;

    const plotW = WIDTH - PAD.left - PAD.right;
    const plotH = HEIGHT - PAD.top - PAD.bottom;
    const xScale = (v: number) =>
      PAD.left + ((v - xDomainMin) / (xDomainMax - xDomainMin)) * plotW;
    const yScale = (v: number) =>
      PAD.top + plotH - ((v - yDomainMin) / (yDomainMax - yDomainMin)) * plotH;

    const tick = (a: number, b: number, n = 4) =>
      Array.from({ length: n + 1 }, (_, i) => a + ((b - a) * i) / n);

    return {
      x: xScale,
      y: yScale,
      xTicks: tick(xDomainMin, xDomainMax),
      yTicks: tick(yDomainMin, yDomainMax),
      xLabel: xScale,
      yLabel: yScale,
    };
  }, [points, line]);

  if (points.length === 0) {
    return (
      <div className="flex h-[320px] items-center justify-center border border-border bg-panel-2 text-[11px] text-fg-faint">
        No paired observations for this pair yet — ingest features first.
      </div>
    );
  }

  return (
    <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full" role="img">
      <rect x={0} y={0} width={WIDTH} height={HEIGHT} fill="var(--bg-panel-2)" />

      {/* gridlines */}
      {yTicks.map((t) => (
        <g key={`y-${t}`}>
          <line
            x1={PAD.left}
            x2={WIDTH - PAD.right}
            y1={y(t)}
            y2={y(t)}
            stroke="var(--border)"
            strokeDasharray="2,4"
          />
          <text
            x={PAD.left - 6}
            y={y(t)}
            fontSize="9"
            fill="var(--text-dim)"
            textAnchor="end"
            dominantBaseline="central"
            fontFamily="var(--font-mono)"
          >
            {t.toFixed(2)}
          </text>
        </g>
      ))}
      {xTicks.map((t) => (
        <g key={`x-${t}`}>
          <line
            x1={x(t)}
            x2={x(t)}
            y1={PAD.top}
            y2={HEIGHT - PAD.bottom}
            stroke="var(--border)"
            strokeDasharray="2,4"
          />
          <text
            x={x(t)}
            y={HEIGHT - PAD.bottom + 14}
            fontSize="9"
            fill="var(--text-dim)"
            textAnchor="middle"
            fontFamily="var(--font-mono)"
          >
            {t.toFixed(2)}
          </text>
        </g>
      ))}

      {/* CI band (if bootstrap yielded bounds) */}
      {line && line.ci_low_at_min !== null && line.ci_high_at_max !== null && (
        <polygon
          points={[
            `${x(line.x_min)},${y(line.ci_low_at_min!)}`,
            `${x(line.x_max)},${y(line.ci_low_at_max!)}`,
            `${x(line.x_max)},${y(line.ci_high_at_max!)}`,
            `${x(line.x_min)},${y(line.ci_high_at_min!)}`,
          ].join(" ")}
          fill="rgba(200, 232, 90, 0.1)"
          stroke="none"
        />
      )}

      {/* regression line */}
      {line && (
        <line
          x1={x(line.x_min)}
          y1={y(line.slope * line.x_min + line.intercept)}
          x2={x(line.x_max)}
          y2={y(line.slope * line.x_max + line.intercept)}
          stroke="var(--accent)"
          strokeWidth={1.5}
        />
      )}

      {/* points */}
      {points.map((p, idx) => (
        <g key={`${p.earnings_id}-${idx}`}>
          <circle
            cx={x(p.x)}
            cy={y(p.y)}
            r={3.5}
            fill="var(--cyan)"
            fillOpacity={0.9}
            stroke="var(--bg)"
            strokeWidth={0.5}
          >
            <title>
              {p.ticker} · {p.report_date}
              {"\n"}
              {data.feature}: {p.x.toFixed(3)}
              {"\n"}
              {data.target}: {p.y.toFixed(3)}
            </title>
          </circle>
        </g>
      ))}

      {/* axis labels */}
      <text
        x={PAD.left + (WIDTH - PAD.left - PAD.right) / 2}
        y={HEIGHT - 4}
        fontSize="10"
        fill="var(--text-dim)"
        textAnchor="middle"
        fontFamily="var(--font-mono)"
      >
        {data.feature}
      </text>
      <text
        transform={`translate(14,${PAD.top + (HEIGHT - PAD.top - PAD.bottom) / 2}) rotate(-90)`}
        fontSize="10"
        fill="var(--text-dim)"
        textAnchor="middle"
        fontFamily="var(--font-mono)"
      >
        {data.target}
      </text>
    </svg>
  );
}
