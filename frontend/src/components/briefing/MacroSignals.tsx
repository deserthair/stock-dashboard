import type { MacroRow } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";

export function MacroSignals({ rows }: { rows: MacroRow[] }) {
  return (
    <Panel title="Macro Signals · 90D" meta="FRED" tight>
      {rows.map((r) => (
        <div
          key={r.series_id}
          className="grid grid-cols-[140px_1fr_60px] items-center gap-2.5 px-3 py-1.5 text-[11px] hover:bg-panel-2"
        >
          <span className="text-fg-dim">{r.label}</span>
          <div className="feat-bar-track">
            <span className="feat-bar-center" />
            <span
              className={`feat-bar-fill ${r.direction === "down" ? "neg" : "pos"}`}
              style={{ width: `${r.bar_width_pct}%` }}
            />
          </div>
          <span
            className={`text-right tabular-nums ${
              r.direction === "up"
                ? "text-up"
                : r.direction === "down"
                ? "text-down"
                : "text-fg-dim"
            }`}
          >
            {r.change_label ?? "—"}
          </span>
        </div>
      ))}
    </Panel>
  );
}
