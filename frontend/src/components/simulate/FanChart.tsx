import type { PricePathSimulationOut } from "@/lib/types";

const WIDTH = 720;
const HEIGHT = 320;
const PAD = { top: 18, right: 20, bottom: 36, left: 58 };

/** Five-band fan chart: 5/25/50/75/95 quantiles over the forecast horizon.
 *  Start price anchored at day 0. */
export function FanChart({ data }: { data: PricePathSimulationOut }) {
  if (data.bands.length === 0) {
    return (
      <div className="flex h-[320px] items-center justify-center border border-border bg-panel-2 text-[11px] text-fg-faint">
        No simulation output.
      </div>
    );
  }

  const all = data.bands.flatMap((b) => [b.p05, b.p25, b.p50, b.p75, b.p95]);
  all.push(data.start_price);
  const yMin = Math.min(...all);
  const yMax = Math.max(...all);
  const yPad = (yMax - yMin) * 0.06 || 1;
  const yDomainMin = yMin - yPad;
  const yDomainMax = yMax + yPad;

  const xMin = 0;
  const xMax = data.horizon_days;
  const plotW = WIDTH - PAD.left - PAD.right;
  const plotH = HEIGHT - PAD.top - PAD.bottom;

  const x = (day: number) =>
    PAD.left + ((day - xMin) / (xMax - xMin)) * plotW;
  const y = (price: number) =>
    PAD.top + plotH - ((price - yDomainMin) / (yDomainMax - yDomainMin)) * plotH;

  // Build a polygon for each band pair (p05↔p95, p25↔p75)
  const outer = [
    `${x(0)},${y(data.start_price)}`,
    ...data.bands.map((b) => `${x(b.day_offset)},${y(b.p95)}`),
    ...[...data.bands].reverse().map((b) => `${x(b.day_offset)},${y(b.p05)}`),
    `${x(0)},${y(data.start_price)}`,
  ].join(" ");

  const inner = [
    `${x(0)},${y(data.start_price)}`,
    ...data.bands.map((b) => `${x(b.day_offset)},${y(b.p75)}`),
    ...[...data.bands].reverse().map((b) => `${x(b.day_offset)},${y(b.p25)}`),
    `${x(0)},${y(data.start_price)}`,
  ].join(" ");

  const median = [
    `${x(0)},${y(data.start_price)}`,
    ...data.bands.map((b) => `${x(b.day_offset)},${y(b.p50)}`),
  ].join(" ");

  // Tick lines
  const yTickCount = 5;
  const yTicks = Array.from({ length: yTickCount + 1 }, (_, i) =>
    yDomainMin + ((yDomainMax - yDomainMin) * i) / yTickCount,
  );
  const xTickCount = Math.min(8, data.horizon_days);
  const xTicks = Array.from({ length: xTickCount + 1 }, (_, i) =>
    Math.round(((data.horizon_days * i) / xTickCount) * 10) / 10,
  );

  // Start-price reference line
  const startY = y(data.start_price);

  return (
    <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full" role="img">
      <rect x={0} y={0} width={WIDTH} height={HEIGHT} fill="var(--bg-panel-2)" />

      {/* Gridlines */}
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
            ${t.toFixed(2)}
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
            {Math.round(t)}d
          </text>
        </g>
      ))}

      {/* Bands */}
      <polygon points={outer} fill="rgba(92, 213, 255, 0.12)" stroke="none" />
      <polygon points={inner} fill="rgba(92, 213, 255, 0.22)" stroke="none" />
      <polyline points={median} fill="none" stroke="var(--accent)" strokeWidth={1.5} />

      {/* Start-price horizontal reference */}
      <line
        x1={PAD.left}
        x2={WIDTH - PAD.right}
        y1={startY}
        y2={startY}
        stroke="var(--text-faint)"
        strokeDasharray="3,3"
      />
      <text
        x={WIDTH - PAD.right - 4}
        y={startY - 4}
        fontSize="9"
        fill="var(--text-faint)"
        textAnchor="end"
        fontFamily="var(--font-mono)"
      >
        start ${data.start_price.toFixed(2)}
      </text>

      {/* Earnings markers */}
      {data.earnings_dates_in_window.map((d) => {
        const [yy, mm, dd] = d.split("-").map(Number);
        const target = new Date(Date.UTC(yy, mm - 1, dd));
        const [sy, sm, sd] = data.start_date.split("-").map(Number);
        const start = new Date(Date.UTC(sy, sm - 1, sd));
        const dayOffset =
          Math.round((target.getTime() - start.getTime()) / 86400000);
        if (dayOffset < 1 || dayOffset > data.horizon_days) return null;
        return (
          <g key={d}>
            <line
              x1={x(dayOffset)}
              x2={x(dayOffset)}
              y1={PAD.top}
              y2={HEIGHT - PAD.bottom}
              stroke="var(--amber)"
              strokeDasharray="4,4"
              strokeWidth={1}
            />
            <text
              x={x(dayOffset)}
              y={PAD.top - 4}
              fontSize="9"
              fill="var(--amber)"
              textAnchor="middle"
              fontFamily="var(--font-mono)"
            >
              ER {d.slice(5)}
            </text>
          </g>
        );
      })}

      {/* Legend */}
      <g transform={`translate(${PAD.left},${PAD.top - 10})`}>
        <rect x={0} y={-8} width={12} height={8} fill="rgba(92,213,255,0.12)" />
        <text x={18} y={-1} fontSize="9" fill="var(--text-dim)" fontFamily="var(--font-mono)">
          5-95%
        </text>
        <rect x={70} y={-8} width={12} height={8} fill="rgba(92,213,255,0.22)" />
        <text x={88} y={-1} fontSize="9" fill="var(--text-dim)" fontFamily="var(--font-mono)">
          25-75%
        </text>
        <line x1={140} y1={-4} x2={152} y2={-4} stroke="var(--accent)" strokeWidth={1.5} />
        <text x={158} y={-1} fontSize="9" fill="var(--text-dim)" fontFamily="var(--font-mono)">
          median
        </text>
      </g>
    </svg>
  );
}
