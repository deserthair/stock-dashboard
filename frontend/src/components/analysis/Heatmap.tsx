"use client";

import type { HeatmapResponse } from "@/lib/types";

/** Map r ∈ [-1, 1] to an RGB colour:
 *   -1 → red, 0 → panel-2, +1 → green. Blends linearly. */
function cellColor(v: number | null): string {
  if (v === null || Number.isNaN(v)) return "var(--bg-panel-2)";
  const t = Math.max(-1, Math.min(1, v));
  if (t >= 0) {
    const alpha = t;
    return `rgba(63, 217, 123, ${alpha.toFixed(3)})`;
  }
  const alpha = -t;
  return `rgba(255, 92, 92, ${alpha.toFixed(3)})`;
}

export function Heatmap({ data }: { data: HeatmapResponse }) {
  const features = data.features;
  const n = features.length;
  if (n === 0) {
    return (
      <div className="flex h-48 items-center justify-center border border-border bg-panel-2 text-[11px] text-fg-faint">
        No features — ingest first.
      </div>
    );
  }
  // Truncate feature names to first 12 chars for the axis tick labels.
  const short = (s: string) => (s.length > 18 ? `${s.slice(0, 15)}…` : s);

  const cellPx = 22;
  const labelW = 168;

  return (
    <div className="overflow-auto">
      <div
        className="inline-grid"
        style={{
          gridTemplateColumns: `${labelW}px repeat(${n}, ${cellPx}px)`,
        }}
      >
        {/* top-left corner */}
        <div />
        {/* column headers */}
        {features.map((f) => (
          <div
            key={`ch-${f}`}
            className="origin-bottom-left -rotate-45 whitespace-nowrap font-mono text-[9px] text-fg-dim"
            style={{
              width: cellPx,
              height: labelW,
              paddingLeft: 4,
              display: "flex",
              alignItems: "flex-end",
              justifyContent: "flex-start",
            }}
            title={f}
          >
            {short(f)}
          </div>
        ))}

        {/* rows */}
        {features.map((rowFeat, i) => (
          <div key={`row-${rowFeat}`} className="contents">
            <div
              className="flex items-center justify-end truncate pr-2 font-mono text-[10px] text-fg-dim"
              style={{ width: labelW, height: cellPx }}
              title={rowFeat}
            >
              {short(rowFeat)}
            </div>
            {data.matrix[i].map((v, j) => (
              <div
                key={`cell-${i}-${j}`}
                className="flex items-center justify-center border border-[color:rgba(0,0,0,0.3)] font-mono text-[8.5px]"
                style={{
                  width: cellPx,
                  height: cellPx,
                  background: cellColor(v),
                  color: v !== null && Math.abs(v) > 0.5 ? "var(--bg)" : "var(--text-dim)",
                }}
                title={`${rowFeat} × ${features[j]}\nr = ${
                  v === null ? "—" : v.toFixed(3)
                }\nn = ${data.sample_sizes?.[i]?.[j] ?? 0}`}
              >
                {v === null ? "—" : v.toFixed(1).replace("0.", ".")}
              </div>
            ))}
          </div>
        ))}
      </div>

      <div className="mt-3 flex items-center gap-2 text-[10px] text-fg-dim">
        <span>−1.0</span>
        <div
          className="h-2 w-40 rounded-sm"
          style={{
            background:
              "linear-gradient(to right, rgba(255,92,92,1), rgba(255,92,92,0.1), rgba(22,25,34,1), rgba(63,217,123,0.1), rgba(63,217,123,1))",
          }}
        />
        <span>+1.0</span>
      </div>
    </div>
  );
}
