import { api } from "@/lib/api";
import { Shell } from "@/components/layout/Shell";
import { DateRangePicker } from "@/components/ui/DateRangePicker";
import { Panel } from "@/components/ui/Panel";
import { Pill, hypothesisTone } from "@/components/ui/Pill";
import {
  directionClass,
  fmtDate,
  fmtNum,
  fmtPct,
  fmtRevenue,
  fmtSigned,
} from "@/lib/format";
import { labelFor, rangeFromSearch } from "@/lib/dateRange";

export default async function EarningsPage({
  searchParams,
}: {
  searchParams: Record<string, string | string[] | undefined>;
}) {
  const range = rangeFromSearch(searchParams);
  const [universe, earnings] = await Promise.all([
    api.universe(),
    api.earningsAll({}, range).catch(() => []),
  ]);

  const now = new Date().toISOString().slice(0, 10);
  const upcoming = earnings.filter((e) => e.report_date >= now).sort((a, b) =>
    a.report_date.localeCompare(b.report_date),
  );
  const past = earnings.filter((e) => e.report_date < now);

  return (
    <Shell universe={universe}>
      <header className="mb-3 flex flex-wrap items-baseline gap-4 border-b border-border pb-2">
        <h1 className="font-serif text-2xl font-medium tracking-tight">Earnings Calendar</h1>
        <span className="text-[11px] uppercase tracking-[0.1em] text-fg-faint">
          {upcoming.length} upcoming · {past.length} past · {labelFor(range)}
        </span>
        <DateRangePicker className="ml-auto" />
      </header>

      <Panel title={`Upcoming · Next ${upcoming.length}`} meta="FINNHUB" tight>
        <table className="w-full text-[11px] tabular-nums">
          <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
            <tr>
              <Th>Date</Th>
              <Th>Ticker</Th>
              <Th>Period</Th>
              <Th align="right">EPS Est</Th>
              <Th align="right">Rev Est</Th>
              <Th align="right">Hypothesis</Th>
            </tr>
          </thead>
          <tbody>
            {upcoming.map((e) => (
              <tr key={e.earnings_id} className="hover:bg-panel-2">
                <td className="border-b border-border px-3 py-1.5">
                  {fmtDate(e.report_date)} {e.time_of_day ?? ""}
                </td>
                <td className="border-b border-border px-3 py-1.5">
                  <strong className="font-semibold text-accent">{e.ticker}</strong>
                </td>
                <td className="border-b border-border px-3 py-1.5 text-fg-dim">
                  {e.fiscal_period ?? "—"}
                </td>
                <td className="border-b border-border px-3 py-1.5 text-right">
                  {fmtNum(e.eps_estimate, 2)}
                </td>
                <td className="border-b border-border px-3 py-1.5 text-right">
                  {fmtRevenue(e.revenue_estimate)}
                </td>
                <td className="border-b border-border px-3 py-1.5 text-right">
                  {e.hypothesis_score === null ? (
                    <Pill>—</Pill>
                  ) : (
                    <Pill tone={hypothesisTone(e.hypothesis_label)}>
                      {e.hypothesis_label ?? "—"} {fmtSigned(e.hypothesis_score, 2)}
                    </Pill>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <Panel title={`Past · ${past.length}`} meta="REPORTED" tight>
        <table className="w-full text-[11px] tabular-nums">
          <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
            <tr>
              <Th>Date</Th>
              <Th>Ticker</Th>
              <Th>Period</Th>
              <Th align="right">EPS Est</Th>
              <Th align="right">EPS Actual</Th>
              <Th align="right">Surprise</Th>
              <Th align="right">1D</Th>
              <Th align="right">5D</Th>
              <Th align="right">Reaction</Th>
            </tr>
          </thead>
          <tbody>
            {past.map((e) => (
              <tr key={e.earnings_id} className="hover:bg-panel-2">
                <td className="border-b border-border px-3 py-1.5">{fmtDate(e.report_date)}</td>
                <td className="border-b border-border px-3 py-1.5">
                  <strong className="font-semibold text-accent">{e.ticker}</strong>
                </td>
                <td className="border-b border-border px-3 py-1.5 text-fg-dim">
                  {e.fiscal_period ?? "—"}
                </td>
                <td className="border-b border-border px-3 py-1.5 text-right">
                  {fmtNum(e.eps_estimate, 2)}
                </td>
                <td className="border-b border-border px-3 py-1.5 text-right">
                  <span className={e.eps_beat ? "text-up" : e.eps_beat === false ? "text-down" : ""}>
                    {fmtNum(e.eps_actual, 2)}
                  </span>
                </td>
                <td className={`border-b border-border px-3 py-1.5 text-right ${directionClass(e.eps_surprise_pct)}`}>
                  {e.eps_surprise_pct !== null ? fmtPct(e.eps_surprise_pct, { digits: 1 }) : "—"}
                </td>
                <td className={`border-b border-border px-3 py-1.5 text-right ${directionClass(e.post_earnings_1d_return)}`}>
                  {e.post_earnings_1d_return !== null ? fmtPct(e.post_earnings_1d_return, { digits: 2 }) : "—"}
                </td>
                <td className={`border-b border-border px-3 py-1.5 text-right ${directionClass(e.post_earnings_5d_return)}`}>
                  {e.post_earnings_5d_return !== null ? fmtPct(e.post_earnings_5d_return, { digits: 2 }) : "—"}
                </td>
                <td className="border-b border-border px-3 py-1.5 text-right">
                  {e.reaction ? <Pill tone={
                    e.reaction.startsWith("beat_rally") ? "green" :
                    e.reaction.startsWith("miss_sell") ? "red" : "amber"
                  }>{e.reaction}</Pill> : <Pill>—</Pill>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
    </Shell>
  );
}

function Th({ children, align }: { children: React.ReactNode; align?: "right" }) {
  return (
    <th className={`border-b border-border px-3 py-1.5 font-medium ${align === "right" ? "text-right" : "text-left"}`}>
      {children}
    </th>
  );
}
