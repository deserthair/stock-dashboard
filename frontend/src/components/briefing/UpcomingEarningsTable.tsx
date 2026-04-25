import type { UpcomingEarnings } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";
import { Pill, hypothesisTone } from "@/components/ui/Pill";
import { fmtDate, fmtNum, fmtRevenue, fmtSigned } from "@/lib/format";

export function UpcomingEarningsTable({
  rows,
}: {
  rows: UpcomingEarnings[];
}) {
  return (
    <Panel
      title="Upcoming Earnings · Next 21D"
      meta="FINNHUB"
      tight
      info={{
        title: "Upcoming Earnings · Next 21D",
        explanation:
          "A schedule of earnings reports coming up in the next 21 days for the companies we track.\n\nQuick glossary:\n• EPS = earnings per share. The company's profit divided by the number of shares.\n• Rev Est = analysts' estimate of total revenue (sales) for the quarter.\n• Period = which quarter is being reported (e.g. Q3 2025).\n• Hyp = our hypothesis score — a number from -1 to +1 estimating whether the report is likely to surprise positively (green) or negatively (red).\n\nStocks often move sharply right after these reports, so this is the calendar to watch.",
      }}
    >
      <table className="w-full text-[11px] tabular-nums">
        <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
          <tr>
            <th className="border-b border-border px-3 py-1.5 text-left font-medium">Date</th>
            <th className="border-b border-border px-3 py-1.5 text-left font-medium">Ticker</th>
            <th className="border-b border-border px-3 py-1.5 text-left font-medium">Period</th>
            <th className="border-b border-border px-3 py-1.5 text-right font-medium">EPS Est</th>
            <th className="border-b border-border px-3 py-1.5 text-right font-medium">Rev Est</th>
            <th className="border-b border-border px-3 py-1.5 text-right font-medium">Hyp</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.ticker}-${r.report_date}`} className="hover:bg-panel-2">
              <td className="border-b border-border px-3 py-1.5">
                {fmtDate(r.report_date)} {r.time_of_day ?? ""}
              </td>
              <td className="border-b border-border px-3 py-1.5">
                <strong className="font-semibold text-accent">{r.ticker}</strong>
              </td>
              <td className="border-b border-border px-3 py-1.5 text-fg-dim">
                {r.fiscal_period ?? "—"}
              </td>
              <td className="border-b border-border px-3 py-1.5 text-right">
                {fmtNum(r.eps_estimate, 2)}
              </td>
              <td className="border-b border-border px-3 py-1.5 text-right">
                {fmtRevenue(r.revenue_estimate)}
              </td>
              <td className="border-b border-border px-3 py-1.5 text-right">
                {r.hypothesis_score === null ? (
                  <Pill>—</Pill>
                ) : (
                  <Pill tone={hypothesisTone(r.hypothesis_label)}>
                    {fmtSigned(r.hypothesis_score, 2)}
                  </Pill>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}
