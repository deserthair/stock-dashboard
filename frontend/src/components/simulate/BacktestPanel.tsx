import type {
  BacktestModelSummaryOut,
  BacktestPredictionOut,
  BacktestReportOut,
} from "@/lib/types";
import { Panel } from "@/components/ui/Panel";
import { StatTile } from "@/components/ui/StatTile";

const MODEL_BLURB: Record<string, string> = {
  gbm_1d: "GBM median 1D return. No earnings-jump term.",
  gbm_5d: "GBM median 5D return.",
  merton_1d_earnings: "Merton with an options-implied jump on earnings day.",
  bootstrap: "Median of score-conditional peer reactions (peers strictly before the event).",
  hypothesis_linear: "Dumb baseline: predicted = 3.0 × hypothesis_score. Any model that doesn't beat this isn't pulling its weight.",
};

function fmtR(r: number | null | undefined): string {
  if (r === null || r === undefined) return "—";
  return (r >= 0 ? "+" : "") + r.toFixed(3);
}
function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined) return "—";
  return `${(v * 100).toFixed(digits)}%`;
}
function fmtPctPoints(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}%pts`;
}

function toneForR(r: number | null | undefined): "green" | "red" | "amber" | "default" {
  if (r === null || r === undefined) return "default";
  if (r > 0.5) return "green";
  if (r > 0.2) return "amber";
  if (r < 0) return "red";
  return "default";
}

function ScatterByModel({ predictions, model }: { predictions: BacktestPredictionOut[]; model: string }) {
  const rows = predictions.filter((p) => p.model === model);
  if (rows.length === 0) return null;

  const WIDTH = 260;
  const HEIGHT = 180;
  const PAD = { top: 8, right: 8, bottom: 22, left: 32 };
  const xs = rows.map((r) => r.predicted);
  const ys = rows.map((r) => r.actual);
  const all = [...xs, ...ys, 0];
  const lo = Math.min(...all);
  const hi = Math.max(...all);
  const pad = (hi - lo) * 0.1 || 1;
  const dMin = lo - pad;
  const dMax = hi + pad;
  const plotW = WIDTH - PAD.left - PAD.right;
  const plotH = HEIGHT - PAD.top - PAD.bottom;
  const x = (v: number) => PAD.left + ((v - dMin) / (dMax - dMin)) * plotW;
  const y = (v: number) => PAD.top + plotH - ((v - dMin) / (dMax - dMin)) * plotH;

  return (
    <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full">
      <rect x={0} y={0} width={WIDTH} height={HEIGHT} fill="var(--bg-panel-2)" />
      {/* Axes */}
      <line x1={x(dMin)} x2={x(dMax)} y1={y(0)} y2={y(0)} stroke="var(--border)" />
      <line x1={x(0)} x2={x(0)} y1={y(dMin)} y2={y(dMax)} stroke="var(--border)" />
      {/* y=x diagonal (perfect prediction) */}
      <line
        x1={x(dMin)}
        y1={y(dMin)}
        x2={x(dMax)}
        y2={y(dMax)}
        stroke="var(--accent)"
        strokeDasharray="3,4"
        strokeOpacity={0.5}
      />
      {/* Points */}
      {rows.map((r, i) => (
        <circle
          key={i}
          cx={x(r.predicted)}
          cy={y(r.actual)}
          r={3}
          fill="var(--cyan)"
          fillOpacity={0.85}
        >
          <title>
            {r.ticker} · {r.report_date}
            {"\n"}pred: {r.predicted.toFixed(2)}% / actual: {r.actual.toFixed(2)}%
          </title>
        </circle>
      ))}
      {/* Axis labels */}
      <text x={x(dMax)} y={y(0) + 12} fontSize="9" fill="var(--text-dim)" textAnchor="end" fontFamily="var(--font-mono)">
        predicted %
      </text>
      <text x={x(0) + 2} y={y(dMax) + 2} fontSize="9" fill="var(--text-dim)" fontFamily="var(--font-mono)">
        actual %
      </text>
    </svg>
  );
}

export function BacktestPanel({ data }: { data: BacktestReportOut }) {
  if (data.n_events_evaluated === 0) {
    return (
      <Panel title="Backtest — no events">
        <p className="text-[11px] text-fg-dim">
          No past earnings events with confirmed post-earnings returns were
          found. Seed must include eps_actual + at least T+1 price data.
        </p>
      </Panel>
    );
  }

  const best = data.models[0];

  return (
    <div className="space-y-3">
      <Panel title="Backtest Leaderboard" meta={`${data.n_events_evaluated} EVENTS · RANKED BY PEARSON r`}>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <StatTile
            label="Best model"
            value={best.model}
            valueClass="text-accent"
            delta={MODEL_BLURB[best.model]?.slice(0, 60) ?? ""}
          />
          <StatTile
            label="Best correlation"
            value={fmtR(best.correlation_r)}
            valueClass={best.correlation_r && best.correlation_r > 0.3 ? "text-up" : "text-amber"}
            delta={`n = ${best.n}`}
          />
          <StatTile
            label="Best direction"
            value={fmtPct(best.direction_accuracy)}
            delta="% of events with right sign"
          />
          <StatTile
            label="Candidates"
            value={`${data.n_events_evaluated} / ${data.n_events_candidates}`}
            delta="with 1D returns / total past"
          />
        </div>

        <table className="mt-4 w-full text-[11px] tabular-nums">
          <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
            <tr>
              <th className="border-b border-border px-3 py-1.5 text-left font-medium">Model</th>
              <th className="border-b border-border px-3 py-1.5 text-right font-medium">n</th>
              <th className="border-b border-border px-3 py-1.5 text-right font-medium">Pearson r</th>
              <th className="border-b border-border px-3 py-1.5 text-right font-medium">Direction</th>
              <th className="border-b border-border px-3 py-1.5 text-right font-medium">MAE</th>
              <th className="border-b border-border px-3 py-1.5 text-right font-medium">Bias</th>
              <th className="border-b border-border px-3 py-1.5 text-right font-medium">90% cov</th>
              <th className="border-b border-border px-3 py-1.5 text-right font-medium">50% cov</th>
            </tr>
          </thead>
          <tbody>
            {data.models.map((m: BacktestModelSummaryOut) => (
              <tr key={m.model} className="hover:bg-panel-2 align-top">
                <td className="border-b border-border px-3 py-2">
                  <div className="font-semibold">{m.model}</div>
                  <div className="text-[10px] text-fg-faint">{MODEL_BLURB[m.model]}</div>
                </td>
                <td className="border-b border-border px-3 py-2 text-right">{m.n}</td>
                <td className={`border-b border-border px-3 py-2 text-right ${
                  m.correlation_r !== null && m.correlation_r !== undefined
                    ? m.correlation_r > 0 ? "text-up" : "text-down" : ""
                }`}>
                  {fmtR(m.correlation_r)}
                </td>
                <td className={`border-b border-border px-3 py-2 text-right ${
                  (m.direction_accuracy ?? 0) > 0.55 ? "text-up" : (m.direction_accuracy ?? 0) < 0.45 ? "text-down" : ""
                }`}>
                  {fmtPct(m.direction_accuracy)}
                </td>
                <td className="border-b border-border px-3 py-2 text-right">
                  {m.median_abs_error !== null && m.median_abs_error !== undefined
                    ? `${m.median_abs_error.toFixed(2)}%pts`
                    : "—"}
                </td>
                <td className="border-b border-border px-3 py-2 text-right">
                  {fmtPctPoints(m.bias)}
                </td>
                <td className="border-b border-border px-3 py-2 text-right">
                  {m.coverage_90 !== null && m.coverage_90 !== undefined ? fmtPct(m.coverage_90) : "—"}
                </td>
                <td className="border-b border-border px-3 py-2 text-right">
                  {m.coverage_50 !== null && m.coverage_50 !== undefined ? fmtPct(m.coverage_50) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <Panel title="Predicted vs Actual" meta="SCATTER PER MODEL · DIAGONAL = PERFECT" tight>
        <div className="grid grid-cols-1 gap-3 p-3 md:grid-cols-2 xl:grid-cols-3">
          {data.models.map((m) => (
            <div key={m.model} className="border border-border">
              <div className="flex items-center justify-between border-b border-border bg-panel-2 px-3 py-1.5 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
                <span className="text-fg">{m.model}</span>
                <span>r = {fmtR(m.correlation_r)}</span>
              </div>
              <ScatterByModel predictions={data.predictions} model={m.model} />
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="All predictions" meta={`${data.predictions.length} TOTAL (MODEL × EVENT)`} tight>
        <div className="max-h-[360px] overflow-auto">
          <table className="w-full text-[11px] tabular-nums">
            <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
              <tr>
                <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-left font-medium">Model</th>
                <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-left font-medium">Ticker</th>
                <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-left font-medium">Date</th>
                <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-right font-medium">Hyp</th>
                <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-right font-medium">Predicted</th>
                <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-right font-medium">Actual</th>
                <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-right font-medium">Error</th>
                <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-right font-medium">In 90%</th>
              </tr>
            </thead>
            <tbody>
              {data.predictions.map((p, i) => {
                const err = p.predicted - p.actual;
                return (
                  <tr key={i} className="hover:bg-panel-2">
                    <td className="border-b border-border px-3 py-1 text-fg-dim">{p.model}</td>
                    <td className="border-b border-border px-3 py-1 text-accent">{p.ticker}</td>
                    <td className="border-b border-border px-3 py-1 text-fg-dim">{p.report_date}</td>
                    <td className="border-b border-border px-3 py-1 text-right">
                      {p.hypothesis_score !== null && p.hypothesis_score !== undefined
                        ? (p.hypothesis_score > 0 ? "+" : "") + p.hypothesis_score.toFixed(2)
                        : "—"}
                    </td>
                    <td className={`border-b border-border px-3 py-1 text-right ${
                      p.predicted > 0 ? "text-up" : p.predicted < 0 ? "text-down" : ""
                    }`}>
                      {(p.predicted > 0 ? "+" : "") + p.predicted.toFixed(2)}%
                    </td>
                    <td className={`border-b border-border px-3 py-1 text-right ${
                      p.actual > 0 ? "text-up" : "text-down"
                    }`}>
                      {(p.actual > 0 ? "+" : "") + p.actual.toFixed(2)}%
                    </td>
                    <td className={`border-b border-border px-3 py-1 text-right ${
                      Math.abs(err) > 2 ? "text-amber" : "text-fg-dim"
                    }`}>
                      {(err > 0 ? "+" : "") + err.toFixed(2)}%pts
                    </td>
                    <td className="border-b border-border px-3 py-1 text-right">
                      {p.inside_90 === true ? <span className="text-up">✓</span>
                       : p.inside_90 === false ? <span className="text-down">✗</span>
                       : <span className="text-fg-faint">—</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
