import type { StatSummary } from "@/lib/types";
import { StatTile } from "@/components/ui/StatTile";
import { fmtPct } from "@/lib/format";

export function StatRow({ stats }: { stats: StatSummary }) {
  return (
    <div className="mb-3 grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
      <StatTile
        label="Universe Δ 1D"
        value={fmtPct(stats.universe_change_1d_pct)}
        valueClass={stats.universe_change_1d_pct >= 0 ? "text-up" : "text-down"}
        delta={
          <>
            vs SPY {fmtPct(stats.spy_change_1d_pct)} ·{" "}
            {stats.up_count}/{stats.total_count} up
          </>
        }
      />
      <StatTile
        label="Events · 24h"
        value={stats.events_24h_total}
        delta={
          <>
            <span className="text-up">{stats.events_24h_hi} HI</span>
            {" · "}
            <span className="text-amber">{stats.events_24h_md} MD</span>
            {" · "}
            <span className="text-fg-dim">{stats.events_24h_lo} LO</span>
          </>
        }
      />
      <StatTile
        label="Earnings · 14D"
        value={stats.earnings_next_14d}
        delta={stats.next_earnings_label}
      />
      <StatTile
        label="Signal Strength"
        value={stats.signal_strength.toFixed(2)}
        valueClass="text-accent"
        delta={
          <>
            {stats.features_active} features active · median r=
            {stats.median_r.toFixed(2)}
          </>
        }
      />
    </div>
  );
}
