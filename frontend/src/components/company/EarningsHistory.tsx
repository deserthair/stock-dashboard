import type { EarningsRow } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";
import { Pill, hypothesisTone } from "@/components/ui/Pill";
import { directionClass, fmtDate, fmtNum, fmtPct, fmtRevenue, fmtSigned } from "@/lib/format";

function reactionTone(reaction: string | null | undefined) {
  if (!reaction) return "default" as const;
  if (reaction === "beat_rally") return "green" as const;
  if (reaction === "miss_sell") return "red" as const;
  return "amber" as const;
}

export function EarningsHistory({ rows }: { rows: EarningsRow[] }) {
  const past = rows.filter((r) => r.eps_actual !== null && r.eps_actual !== undefined);
  if (past.length === 0) {
    return (
      <Panel title="Earnings History" meta="FINNHUB · EDGAR" tight>
        <div className="px-3 py-8 text-center text-[11px] text-fg-faint">
          No past earnings with actuals recorded yet for this ticker.
        </div>
      </Panel>
    );
  }
  // Hit rate for this ticker alone
  const scored = past.filter((r) => r.eps_beat !== null).length;
  const hits = past.filter((r) => r.eps_beat === true).length;
  const hitRate = scored > 0 ? Math.round((hits / scored) * 100) : null;

  return (
    <Panel
      title={`Earnings History · ${past.length} prints`}
      meta={
        hitRate !== null
          ? `BEAT RATE ${hitRate}% (${hits}/${scored})`
          : "FINNHUB · EDGAR"
      }
      tight
    >
      <table className="w-full text-[11px] tabular-nums">
        <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
          <tr>
            <th className="border-b border-border px-3 py-1.5 text-left font-medium">Date</th>
            <th className="border-b border-border px-3 py-1.5 text-left font-medium">Period</th>
            <th className="border-b border-border px-3 py-1.5 text-right font-medium">EPS Est</th>
            <th className="border-b border-border px-3 py-1.5 text-right font-medium">EPS Actual</th>
            <th className="border-b border-border px-3 py-1.5 text-right font-medium">Surprise</th>
            <th className="border-b border-border px-3 py-1.5 text-right font-medium">Rev Actual</th>
            <th className="border-b border-border px-3 py-1.5 text-right font-medium">1D</th>
            <th className="border-b border-border px-3 py-1.5 text-right font-medium">5D</th>
            <th className="border-b border-border px-3 py-1.5 text-right font-medium">Reaction</th>
            <th className="border-b border-border px-3 py-1.5 text-right font-medium">Hypothesis</th>
          </tr>
        </thead>
        <tbody>
          {past.map((e) => (
            <tr key={e.earnings_id} className="hover:bg-panel-2">
              <td className="border-b border-border px-3 py-1.5">{fmtDate(e.report_date)}</td>
              <td className="border-b border-border px-3 py-1.5 text-fg-dim">
                {e.fiscal_period ?? "—"}
              </td>
              <td className="border-b border-border px-3 py-1.5 text-right">
                {fmtNum(e.eps_estimate, 2)}
              </td>
              <td className="border-b border-border px-3 py-1.5 text-right">
                <span
                  className={
                    e.eps_beat
                      ? "text-up"
                      : e.eps_beat === false
                      ? "text-down"
                      : ""
                  }
                >
                  {fmtNum(e.eps_actual, 2)}
                </span>
              </td>
              <td
                className={`border-b border-border px-3 py-1.5 text-right ${directionClass(e.eps_surprise_pct)}`}
              >
                {e.eps_surprise_pct !== null ? fmtPct(e.eps_surprise_pct, { digits: 1 }) : "—"}
              </td>
              <td className="border-b border-border px-3 py-1.5 text-right">
                {fmtRevenue(e.revenue_actual)}
              </td>
              <td className={`border-b border-border px-3 py-1.5 text-right ${directionClass(e.post_earnings_1d_return)}`}>
                {e.post_earnings_1d_return !== null
                  ? fmtPct(e.post_earnings_1d_return, { digits: 2 })
                  : "—"}
              </td>
              <td className={`border-b border-border px-3 py-1.5 text-right ${directionClass(e.post_earnings_5d_return)}`}>
                {e.post_earnings_5d_return !== null
                  ? fmtPct(e.post_earnings_5d_return, { digits: 2 })
                  : "—"}
              </td>
              <td className="border-b border-border px-3 py-1.5 text-right">
                {e.reaction ? (
                  <Pill tone={reactionTone(e.reaction)}>{e.reaction}</Pill>
                ) : (
                  <Pill>—</Pill>
                )}
              </td>
              <td className="border-b border-border px-3 py-1.5 text-right">
                {e.hypothesis_score !== null ? (
                  <Pill tone={hypothesisTone(e.hypothesis_label)}>
                    {fmtSigned(e.hypothesis_score, 2)}
                  </Pill>
                ) : (
                  <Pill>—</Pill>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}
