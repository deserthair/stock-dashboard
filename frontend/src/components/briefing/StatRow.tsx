import type { StatSummary } from "@/lib/types";
import { StatTile } from "@/components/ui/StatTile";
import { fmtPct } from "@/lib/format";

export function StatRow({ stats }: { stats: StatSummary }) {
  const snapshot = `Current values: ${JSON.stringify(stats, null, 2)}`;
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
        info={{
          title: "Universe Δ 1D",
          explanation:
            "Think of the 'universe' as our basket of restaurant stocks we watch. This number is the average price change of all those stocks today, in percent.\n\nA positive number means most are up; a negative number means most are down. We compare it to SPY (an ETF that tracks the whole S&P 500) so you can tell whether restaurants are doing better or worse than the broader market today. The 'X / Y up' tells you how many stocks in the basket finished positive.",
          dataSnapshot: snapshot,
        }}
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
        info={{
          title: "Events · 24h",
          explanation:
            "An 'event' is anything newsworthy that happened to one of our companies in the last 24 hours: an earnings report, a press release, a social-media spike, a big filing, etc.\n\nWe tag each event by severity:\n• HI (high) — likely to move the stock or change the story.\n• MD (medium) — worth a look.\n• LO (low) — background noise we still log.\n\nThe big number is the total count; the colored numbers split it by severity.",
          dataSnapshot: snapshot,
        }}
      />
      <StatTile
        label="Earnings · 14D"
        value={stats.earnings_next_14d}
        delta={stats.next_earnings_label}
        info={{
          title: "Earnings · 14D",
          explanation:
            "How many of the companies we track are scheduled to report their quarterly earnings in the next 14 days.\n\nAn 'earnings report' is when a public company tells the world how much money it made last quarter. Stocks often move sharply right after these reports, so it's useful to know which ones are coming up. The list below the number shows the next few tickers and their report dates.",
          dataSnapshot: snapshot,
        }}
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
        info={{
          title: "Signal Strength",
          explanation:
            "A single 0-to-1 score that tells you how reliable our predictive 'signals' look right now.\n\nA 'feature' is something we measure (news volume, hiring trends, social-media buzz, etc.). For each feature we measure how strongly it correlates with future returns — that's the 'r' value (closer to 1 or -1 = stronger relationship; 0 = no relationship).\n\n'Features active' = how many features currently have enough data. 'Median r' = the typical correlation across them. Higher overall score = the signals are pulling in a consistent direction.",
          dataSnapshot: snapshot,
        }}
      />
    </div>
  );
}
