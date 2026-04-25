"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { Panel } from "@/components/ui/Panel";
import { Pill } from "@/components/ui/Pill";
import { ScatterPlot } from "./ScatterPlot";
import type { AnalysisAxesResponse, ScatterResponse } from "@/lib/types";
import type { DateRange } from "@/lib/dateRange";
import { fmtSigned } from "@/lib/format";
import { INFO } from "@/lib/info";

export function CorrelationLab({
  axes,
  initialFeature,
  initialTarget,
  initial,
}: {
  axes: AnalysisAxesResponse;
  initialFeature: string;
  initialTarget: string;
  initial: ScatterResponse;
}) {
  const searchParams = useSearchParams();
  const range: DateRange = {
    from: searchParams.get("from") || undefined,
    to: searchParams.get("to") || undefined,
  };
  const rangeKey = `${range.from ?? ""}|${range.to ?? ""}`;

  const [feature, setFeature] = useState(initialFeature);
  const [target, setTarget] = useState(initialTarget);
  const [data, setData] = useState<ScatterResponse>(initial);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const initialKey = `${range.from ?? ""}|${range.to ?? ""}`;
    // Skip the initial render — the server already returned exactly this pair/range.
    if (
      feature === initial.feature &&
      target === initial.target &&
      initialKey === rangeKey
    )
      return;
    let cancelled = false;
    setLoading(true);
    api
      .scatter(feature, target, range)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch(() => {
        if (!cancelled) setData({ ...data, points: [], line: null });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [feature, target, rangeKey]);

  const line = data.line;
  const significant = line?.pearson_p !== null && line?.pearson_p !== undefined && line.pearson_p < 0.05;

  return (
    <Panel
      title="Correlation Lab"
      meta={`${data.points.length} observations`}
      info={INFO.correlations_scatter}
    >
      <div className="mb-3 grid grid-cols-1 gap-2 md:grid-cols-[1fr_1fr]">
        <Picker
          label="Feature (x)"
          value={feature}
          onChange={setFeature}
          options={axes.features}
        />
        <Picker
          label="Target (y)"
          value={target}
          onChange={setTarget}
          options={axes.targets}
        />
      </div>

      <div className="relative">
        <ScatterPlot data={data} />
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-panel/60 text-[11px] uppercase tracking-[0.15em] text-fg-dim">
            Recomputing…
          </div>
        )}
      </div>

      {line && (
        <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-5">
          <Stat label="Pearson r" value={fmtSigned(line.pearson_r, 3)} tone={significant ? "accent" : "dim"} />
          <Stat label="p (Pearson)" value={line.pearson_p !== null ? line.pearson_p.toFixed(4) : "—"} tone={significant ? "green" : "dim"} />
          <Stat label="Spearman r" value={fmtSigned(line.spearman_r, 3)} />
          <Stat label="R²" value={line.r_squared.toFixed(3)} />
          <Stat label="Slope" value={fmtSigned(line.slope, 3)} />
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px]">
        <Pill tone="cyan">n = {data.points.length}</Pill>
        {line && (
          <>
            <Pill tone={significant ? "green" : "default"}>
              {significant ? "p &lt; 0.05" : "p ≥ 0.05"}
            </Pill>
            <Pill tone="default">
              fit: y = {line.slope.toFixed(3)}·x {line.intercept >= 0 ? "+" : "−"} {Math.abs(line.intercept).toFixed(3)}
            </Pill>
          </>
        )}
        <span className="ml-auto text-[10px] text-fg-faint">
          95% CI from 500 bootstrap resamples · hover dots for ticker + date
        </span>
      </div>
    </Panel>
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

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "accent" | "green" | "dim";
}) {
  const color =
    tone === "accent"
      ? "text-accent"
      : tone === "green"
      ? "text-up"
      : tone === "dim"
      ? "text-fg-dim"
      : "text-fg";
  return (
    <div className="border border-border bg-panel-2 p-2">
      <div className="text-[10px] uppercase tracking-[0.15em] text-fg-faint">{label}</div>
      <div className={`mt-1 font-serif text-[18px] tabular-nums ${color}`}>{value}</div>
    </div>
  );
}
