"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { Histogram } from "@/components/simulate/Histogram";
import { Panel } from "@/components/ui/Panel";
import { Pill } from "@/components/ui/Pill";
import { StatTile } from "@/components/ui/StatTile";
import type { DCFResultOut } from "@/lib/types";

function fmtMoney(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  if (Math.abs(v) >= 1e3) return `$${v.toFixed(0)}`;
  return `$${v.toFixed(2)}`;
}

export function DCFPanel({
  ticker,
  initial,
}: {
  ticker: string;
  initial: DCFResultOut;
}) {
  const [wacc, setWacc] = useState(initial.wacc_mean_pct);
  const [terminal, setTerminal] = useState(initial.terminal_growth_pct);
  const [years, setYears] = useState(initial.years_explicit);

  const [data, setData] = useState<DCFResultOut>(initial);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const matchesInitial =
      wacc === initial.wacc_mean_pct &&
      terminal === initial.terminal_growth_pct &&
      years === initial.years_explicit;
    if (matchesInitial) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .simulateDCF(ticker, {
        wacc_mean: wacc / 100,
        terminal_growth: terminal / 100,
        years_explicit: years,
        seed: 42,
      })
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((e) => !cancelled && setError(String(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wacc, terminal, years, ticker]);

  const s = data.intrinsic_value_stats;
  const current = data.current_price ?? 0;
  const highlights = [
    { x: current, label: "price", color: "var(--text-faint)" },
    { x: s.p05, label: "p5", color: "var(--down)" },
    { x: s.p50, label: "p50", color: "var(--accent)" },
    { x: s.p95, label: "p95", color: "var(--up)" },
  ];
  const mos = data.margin_of_safety_at_p50_pct;

  return (
    <div className="space-y-3">
      <Panel title="DCF Inputs" meta={loading ? "COMPUTING…" : "MC=10K · SEED=42"} tight>
        <div className="grid grid-cols-1 gap-3 p-3 md:grid-cols-3">
          <NumInput
            label="WACC %"
            value={wacc}
            step={0.25}
            onChange={setWacc}
            help="Discount rate μ. σ=1% by default"
          />
          <NumInput
            label="Terminal growth %"
            value={terminal}
            step={0.25}
            onChange={setTerminal}
            help="Gordon-growth terminal rate; must be < WACC"
          />
          <NumInput
            label="Explicit years"
            value={years}
            step={1}
            onChange={setYears}
            help="Projection horizon before terminal value kicks in"
          />
        </div>
        <div className="border-t border-border px-3 py-2 text-[10px] text-fg-faint">
          Fitted from {data.fit_quarters} quarters: revenue growth μ={" "}
          <span className="text-fg">{data.revenue_growth_mean_pct}%</span> σ={" "}
          <span className="text-fg">{data.revenue_growth_std_pct}%</span>  ·  FCF
          margin μ={" "}
          <span className="text-fg">{data.fcf_margin_mean_pct}%</span> σ={" "}
          <span className="text-fg">{data.fcf_margin_std_pct}%</span>
        </div>
        {error && <div className="px-3 pb-2 text-[11px] text-down">{error}</div>}
      </Panel>

      <Panel
        title={`Probabilistic DCF · ${data.ticker}`}
        meta={`${data.n_valid.toLocaleString()} valid draws out of ${data.n_simulations.toLocaleString()}`}
      >
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <StatTile
            label="Current price"
            value={fmtMoney(data.current_price)}
            delta={`${(data.shares_diluted ?? 0) / 1e6}M shares`}
          />
          <StatTile
            label="Intrinsic p50"
            value={fmtMoney(s.p50)}
            valueClass="text-accent"
            delta={`p5 ${fmtMoney(s.p05)} · p95 ${fmtMoney(s.p95)}`}
          />
          <StatTile
            label="P(undervalued)"
            value={
              data.prob_undervalued !== null && data.prob_undervalued !== undefined
                ? `${(data.prob_undervalued * 100).toFixed(1)}%`
                : "—"
            }
            valueClass={
              (data.prob_undervalued ?? 0) > 0.7
                ? "text-up"
                : (data.prob_undervalued ?? 0) < 0.3
                ? "text-down"
                : "text-amber"
            }
          />
          <StatTile
            label="Margin of Safety @ p50"
            value={mos !== null && mos !== undefined ? `${mos > 0 ? "+" : ""}${mos.toFixed(1)}%` : "—"}
            valueClass={(mos ?? 0) > 0 ? "text-up" : "text-down"}
          />
        </div>

        <div className="mt-3">
          <div className="mb-2 text-[10px] uppercase tracking-[0.15em] text-fg-faint">
            Intrinsic value per share — distribution
          </div>
          <Histogram
            bins={data.intrinsic_value_histogram}
            highlights={highlights}
            valueFormatter={(v) => fmtMoney(v)}
          />
        </div>

        {data.notes.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {data.notes.map((n) => (
              <Pill key={n} tone="amber">
                {n}
              </Pill>
            ))}
          </div>
        )}

        <div className="mt-3 text-[10px] text-fg-faint">
          Model: 10yr FCF projection at sampled growth × margin, discounted at
          sampled WACC, with a Gordon-growth terminal value. Simplifying
          assumption: equity value ≈ enterprise value (net debt ignored). The
          dollar magnitudes are a function of the seeded share count — in a
          production deployment with real shares_outstanding from yfinance the
          per-share values normalize.
        </div>
      </Panel>
    </div>
  );
}

function NumInput({
  label,
  value,
  step,
  onChange,
  help,
}: {
  label: string;
  value: number;
  step: number;
  onChange: (v: number) => void;
  help?: string;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-[0.15em] text-fg-faint">
        {label}
      </span>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="rounded-sm border border-border bg-panel-2 px-2 py-1.5 font-mono text-[11px] text-fg focus:border-accent focus:outline-none"
      />
      {help && <span className="text-[10px] text-fg-faint">{help}</span>}
    </label>
  );
}
