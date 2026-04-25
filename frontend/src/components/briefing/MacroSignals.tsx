import type { MacroRow } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";

export function MacroSignals({ rows }: { rows: MacroRow[] }) {
  return (
    <Panel
      title="Macro Signals · 90D"
      meta="FRED"
      tight
      info={{
        title: "Macro Signals · 90D",
        explanation:
          "Big-picture economic indicators that affect restaurant stocks: things like consumer spending, food prices, gas prices, employment, and interest rates.\n\nEach row shows how that indicator has changed over the last 90 days. The bar in the middle is a visual: filling to the right (green) means it went up, to the left (red) means it went down.\n\nWhy it matters: if gas is expensive and confidence is low, people eat out less. If wages are rising fast, restaurant labor costs go up. We pull these from FRED, the Fed's free economic-data service.",
      }}
    >
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
