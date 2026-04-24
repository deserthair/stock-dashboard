"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { FanChart } from "@/components/simulate/FanChart";
import { Histogram } from "@/components/simulate/Histogram";
import { Panel } from "@/components/ui/Panel";
import { Pill } from "@/components/ui/Pill";
import { StatTile } from "@/components/ui/StatTile";
import type {
  EarningsBootstrapOut,
  PricePathSimulationOut,
  UniverseRow,
} from "@/lib/types";

type Model = "gbm" | "merton";

export function SimulatePanel({
  universe,
  initialTicker,
  initialPrice,
  initialBootstrap,
}: {
  universe: UniverseRow[];
  initialTicker: string;
  initialPrice: PricePathSimulationOut;
  initialBootstrap: EarningsBootstrapOut;
}) {
  const [ticker, setTicker] = useState(initialTicker);
  const [horizon, setHorizon] = useState(initialPrice.horizon_days);
  const [model, setModel] = useState<Model>(initialPrice.model as Model);
  const [nPaths, setNPaths] = useState(initialPrice.n_paths);

  const [price, setPrice] = useState<PricePathSimulationOut>(initialPrice);
  const [boot, setBoot] = useState<EarningsBootstrapOut>(initialBootstrap);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Only refetch when one of the params actually differs from the initial.
    const matchesInitial =
      ticker === initialTicker &&
      horizon === initialPrice.horizon_days &&
      model === initialPrice.model &&
      nPaths === initialPrice.n_paths;
    if (matchesInitial) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([
      api.simulatePricePaths(ticker, {
        horizon_days: horizon,
        n_paths: nPaths,
        model,
        seed: 42,
      }),
      api.simulateEarningsBootstrap(ticker, { seed: 42 }),
    ])
      .then(([p, b]) => {
        if (cancelled) return;
        setPrice(p);
        setBoot(b);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker, horizon, model, nPaths]);

  const ts = price.terminal_stats;
  const priceHighlights = [
    { x: price.start_price, label: "start", color: "var(--text-faint)" },
    { x: ts.p05, label: "p5", color: "var(--down)" },
    { x: ts.p50, label: "median", color: "var(--accent)" },
    { x: ts.p95, label: "p95", color: "var(--up)" },
  ];

  const q = boot.quantiles;
  const bootHighlights = [
    { x: 0, label: "0%", color: "var(--text-faint)" },
    { x: q.p05, label: "p5", color: "var(--down)" },
    { x: q.mean, label: "mean", color: "var(--accent)" },
    { x: q.p95, label: "p95", color: "var(--up)" },
  ];

  return (
    <div className="space-y-3">
      {/* Controls */}
      <Panel title="Controls" meta={loading ? "COMPUTING…" : "RESEED · 42"} tight>
        <div className="grid grid-cols-2 gap-3 p-3 md:grid-cols-4">
          <Picker label="Ticker" value={ticker} onChange={setTicker}
            options={universe.map((u) => u.ticker)} />
          <Picker
            label="Model"
            value={model}
            onChange={(v) => setModel(v as Model)}
            options={["gbm", "merton"]}
          />
          <NumPicker
            label="Horizon (days)"
            value={horizon}
            onChange={setHorizon}
            options={[7, 14, 30, 60, 90, 180]}
          />
          <NumPicker
            label="Paths"
            value={nPaths}
            onChange={setNPaths}
            options={[1000, 5000, 10000, 25000]}
          />
        </div>
        {error && <div className="px-3 pb-3 text-[11px] text-down">{error}</div>}
      </Panel>

      {/* Monte Carlo price paths */}
      <Panel
        title={`Monte Carlo Price Paths · ${price.ticker}`}
        meta={`${price.model.toUpperCase()} · μ ${price.annual_drift_pct}%/yr · σ ${price.annual_volatility_pct}%/yr · fit on ${price.fit_observations} days`}
      >
        <FanChart data={price} />
        {price.notes.length > 0 && (
          <div className="mt-2 text-[10px] text-fg-faint">
            Notes: {price.notes.join(" · ")}
          </div>
        )}

        <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
          <StatTile
            label={`Median @ T+${price.horizon_days}d`}
            value={`$${ts.p50.toFixed(2)}`}
            delta={`vs start $${price.start_price.toFixed(2)}`}
          />
          <StatTile
            label="90% range"
            value={`$${ts.p05.toFixed(2)}–$${ts.p95.toFixed(2)}`}
            delta={`p5 · p95 (n=${price.n_paths.toLocaleString()})`}
          />
          <StatTile
            label="P(positive return)"
            value={`${(ts.prob_positive_return * 100).toFixed(1)}%`}
            valueClass={ts.prob_positive_return > 0.5 ? "text-up" : "text-down"}
          />
          <StatTile
            label="P(±10%)"
            value={`${(ts.prob_up_10pct * 100).toFixed(1)}% / ${(ts.prob_down_10pct * 100).toFixed(1)}%`}
            delta="up / down"
          />
        </div>

        <div className="mt-3">
          <div className="mb-2 text-[10px] uppercase tracking-[0.15em] text-fg-faint">
            Terminal-value distribution (T+{price.horizon_days}d)
          </div>
          <Histogram
            bins={price.terminal_histogram}
            highlights={priceHighlights}
            valueFormatter={(v) => `$${v.toFixed(2)}`}
          />
        </div>
      </Panel>

      {/* Earnings bootstrap */}
      <Panel
        title={`Earnings-Reaction Bootstrap · ${boot.target_ticker}`}
        meta={`METHOD ${boot.method.toUpperCase()} · ${boot.n_peers} PEERS · n=${boot.n_bootstrap.toLocaleString()}`}
      >
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <StatTile
            label="Target score"
            value={
              boot.target_hypothesis_score !== null && boot.target_hypothesis_score !== undefined
                ? (boot.target_hypothesis_score > 0 ? "+" : "") +
                  boot.target_hypothesis_score.toFixed(2)
                : "—"
            }
            delta={boot.target_fiscal_period ?? ""}
          />
          <StatTile
            label="Mean 1D reaction"
            value={`${q.mean > 0 ? "+" : ""}${q.mean.toFixed(2)}%`}
            valueClass={q.mean > 0 ? "text-up" : "text-down"}
            delta={`σ ${q.stdev.toFixed(2)}%`}
          />
          <StatTile
            label="90% range"
            value={`${q.p05.toFixed(2)}% to ${q.p95.toFixed(2)}%`}
          />
          <StatTile
            label="P(positive)"
            value={`${(boot.prob_positive_return * 100).toFixed(1)}%`}
            valueClass={boot.prob_positive_return > 0.5 ? "text-up" : "text-down"}
            delta={`P(+2%) ${(boot.prob_up_2pct * 100).toFixed(1)}% · P(-2%) ${(boot.prob_down_2pct * 100).toFixed(1)}%`}
          />
        </div>

        <div className="mt-3">
          <div className="mb-2 text-[10px] uppercase tracking-[0.15em] text-fg-faint">
            Bootstrap distribution of post-earnings 1D return (%)
          </div>
          <Histogram
            bins={boot.histogram}
            highlights={bootHighlights}
            valueFormatter={(v) => `${v.toFixed(1)}%`}
          />
        </div>

        {boot.peers.length > 0 && (
          <div className="mt-3">
            <div className="mb-1 text-[10px] uppercase tracking-[0.15em] text-fg-faint">
              Peer events (up to 40)
            </div>
            <div className="max-h-60 overflow-auto">
              <table className="w-full text-[11px] tabular-nums">
                <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
                  <tr>
                    <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-left font-medium">Ticker</th>
                    <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-left font-medium">Date</th>
                    <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-right font-medium">Hypothesis</th>
                    <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-right font-medium">Surprise</th>
                    <th className="sticky top-0 border-b border-border bg-panel-2 px-3 py-1.5 text-right font-medium">1D Reaction</th>
                  </tr>
                </thead>
                <tbody>
                  {boot.peers.map((p) => (
                    <tr key={p.earnings_id} className="hover:bg-panel-2">
                      <td className="border-b border-border px-3 py-1.5 text-accent">{p.ticker}</td>
                      <td className="border-b border-border px-3 py-1.5 text-fg-dim">{p.report_date}</td>
                      <td className="border-b border-border px-3 py-1.5 text-right">
                        {p.hypothesis_score !== null && p.hypothesis_score !== undefined
                          ? (p.hypothesis_score > 0 ? "+" : "") + p.hypothesis_score.toFixed(2)
                          : "—"}
                      </td>
                      <td className="border-b border-border px-3 py-1.5 text-right">
                        {p.eps_surprise_pct !== null && p.eps_surprise_pct !== undefined
                          ? (p.eps_surprise_pct > 0 ? "+" : "") + p.eps_surprise_pct.toFixed(1) + "%"
                          : "—"}
                      </td>
                      <td className={`border-b border-border px-3 py-1.5 text-right ${
                        p.actual_1d_return !== null && p.actual_1d_return !== undefined
                          ? p.actual_1d_return > 0 ? "text-up" : "text-down"
                          : ""
                      }`}>
                        {p.actual_1d_return !== null && p.actual_1d_return !== undefined
                          ? (p.actual_1d_return > 0 ? "+" : "") + p.actual_1d_return.toFixed(2) + "%"
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {boot.notes.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {boot.notes.map((n) => (
              <Pill key={n} tone="amber">
                {n}
              </Pill>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

function Picker({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-[0.15em] text-fg-faint">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-sm border border-border bg-panel-2 px-2 py-1.5 font-mono text-[11px] text-fg focus:border-accent focus:outline-none"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}

function NumPicker({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  options: number[];
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-[0.15em] text-fg-faint">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="rounded-sm border border-border bg-panel-2 px-2 py-1.5 font-mono text-[11px] text-fg focus:border-accent focus:outline-none"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o.toLocaleString()}
          </option>
        ))}
      </select>
    </label>
  );
}
