import type { UpcomingEarnings } from "@/lib/types";
import { AnnotationBadge } from "@/components/ui/AnnotationBadge";
import { Panel } from "@/components/ui/Panel";
import { Pill, hypothesisTone } from "@/components/ui/Pill";
import { Tooltip } from "@/components/ui/Tooltip";
import { fmtDate, fmtNum, fmtRevenue, fmtSigned } from "@/lib/format";
import { annotate } from "@/lib/interpret";

export function UpcomingEarningsTable({
  rows,
}: {
  rows: UpcomingEarnings[];
}) {
  const snapshot = rows.map((r) => ({
    date: r.report_date,
    ticker: r.ticker,
    period: r.fiscal_period,
    eps_est: r.eps_estimate,
    rev_est: r.revenue_estimate,
    hypothesis: r.hypothesis_label,
    score: r.hypothesis_score,
  }));
  return (
    <Panel
      title="Upcoming Earnings · Next 21D"
      meta="FINNHUB"
      tight
      info={{
        title: "Upcoming Earnings · Next 21D",
        explanation:
          "A schedule of earnings reports coming up in the next 21 days for the companies we track.\n\nQuick glossary:\n• EPS = earnings per share. The company's profit divided by the number of shares.\n• Rev Est = analysts' estimate of total revenue (sales) for the quarter.\n• Period = which quarter is being reported (e.g. Q3 2025).\n• Hyp = our hypothesis score — a number from -1 to +1 estimating whether the report is likely to surprise positively (green) or negatively (red).\n\nStocks often move sharply right after these reports, so this is the calendar to watch.",
        dataSnapshot: `Upcoming earnings on screen (${rows.length}):\n${JSON.stringify(snapshot, null, 2)}`,
      }}
    >
      <table className="w-full text-[11px] tabular-nums">
        <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
          <tr>
            <th className="border-b border-border px-3 py-1.5 text-left font-medium">Date</th>
            <th className="border-b border-border px-3 py-1.5 text-left font-medium">Ticker</th>
            <th className="border-b border-border px-3 py-1.5 text-left font-medium">
              <Tooltip tip="Which fiscal quarter this report covers (e.g. Q3 2025).">
                <span className="cursor-help underline decoration-dotted decoration-fg-faint underline-offset-2">
                  Period
                </span>
              </Tooltip>
            </th>
            <th className="border-b border-border px-3 py-1.5 text-right font-medium">
              <Tooltip tip="Earnings per share — analysts' consensus estimate for this quarter.">
                <span className="cursor-help underline decoration-dotted decoration-fg-faint underline-offset-2">
                  EPS Est
                </span>
              </Tooltip>
            </th>
            <th className="border-b border-border px-3 py-1.5 text-right font-medium">
              <Tooltip tip="Revenue (total sales) consensus estimate for this quarter.">
                <span className="cursor-help underline decoration-dotted decoration-fg-faint underline-offset-2">
                  Rev Est
                </span>
              </Tooltip>
            </th>
            <th className="border-b border-border px-3 py-1.5 text-right font-medium">
              <Tooltip tip="Our hypothesis score (-1 to +1). Positive = we lean Bullish into the print.">
                <span className="cursor-help underline decoration-dotted decoration-fg-faint underline-offset-2">
                  Hyp
                </span>
              </Tooltip>
            </th>
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
                  <span className="inline-flex items-center">
                    <Pill tone={hypothesisTone(r.hypothesis_label)}>
                      {fmtSigned(r.hypothesis_score, 2)}
                    </Pill>
                    <AnnotationBadge ann={annotate("hypothesis_score", r.hypothesis_score)} />
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}
