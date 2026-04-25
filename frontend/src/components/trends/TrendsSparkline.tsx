import type { TrendsSeriesOut } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";
import { directionClass, fmtPct, fmtSigned } from "@/lib/format";
import { INFO } from "@/lib/info";

/** Pure-SVG sparkline for a Google Trends series. */
export function TrendsSparkline({
  series,
  height = 80,
  width = 320,
}: {
  series: TrendsSeriesOut;
  height?: number;
  width?: number;
}) {
  const obs = series.observations.filter((o) => o.value !== null);
  if (obs.length === 0) return null;

  const values = obs.map((o) => o.value as number);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const pad = { top: 4, right: 4, bottom: 4, left: 4 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const points = obs
    .map((o, i) => {
      const x = pad.left + (i / Math.max(1, obs.length - 1)) * plotW;
      const y = pad.top + plotH - (((o.value as number) - min) / range) * plotH;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  const fillPath =
    `M ${pad.left},${pad.top + plotH} ` +
    points.split(" ").map((p) => `L ${p}`).join(" ") +
    ` L ${pad.left + plotW},${pad.top + plotH} Z`;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height}>
      <rect x={0} y={0} width={width} height={height} fill="var(--bg-panel-2)" />
      <path d={fillPath} fill="rgba(92,213,255,0.18)" stroke="none" />
      <polyline points={points} fill="none" stroke="var(--cyan)" strokeWidth={1.5} />
    </svg>
  );
}

export function TrendsCard({ series }: { series: TrendsSeriesOut }) {
  const q = series.query;
  const latest = series.latest;
  return (
    <Panel
      title={q.label}
      meta={q.category.toUpperCase()}
      tight
      info={{
        ...INFO.trends_card,
        title: q.label,
        pageContext: `query="${q.query}"; category=${q.category}; latest=${latest}; 30d_change=${series.change_30d_pct}%; 90d_change=${series.change_90d_pct}%`,
      }}
    >
      <div className="flex items-baseline gap-3 border-b border-border px-3 py-2">
        <div className="font-serif text-[20px] font-medium leading-none">
          {latest !== null && latest !== undefined ? latest.toFixed(0) : "—"}
        </div>
        <span className="text-[10px] uppercase tracking-[0.15em] text-fg-faint">
          trends index (0-100)
        </span>
        <span className="ml-auto text-[11px] tabular-nums">
          <span className={directionClass(series.change_30d_pct)}>
            30d {fmtPct(series.change_30d_pct ?? null, { digits: 1 })}
          </span>{" "}
          <span className="text-fg-faint">·</span>{" "}
          <span className={directionClass(series.change_90d_pct)}>
            90d {fmtPct(series.change_90d_pct ?? null, { digits: 1 })}
          </span>
        </span>
      </div>
      <div className="flex items-center justify-center p-3">
        <TrendsSparkline series={series} width={320} height={80} />
      </div>
      <div className="border-t border-border px-3 py-1.5 text-[10px] text-fg-faint">
        Query: <span className="text-fg-dim">&ldquo;{q.query}&rdquo;</span> ·{" "}
        {series.observations.length} weekly obs
        {q.last_fetched_at && ` · fetched ${new Date(q.last_fetched_at).toISOString().slice(0, 10)}`}
      </div>
    </Panel>
  );
}
