import { api } from "@/lib/api";
import { Shell } from "@/components/layout/Shell";
import { DateRangePicker } from "@/components/ui/DateRangePicker";
import { Panel } from "@/components/ui/Panel";
import { Pill, hypothesisTone } from "@/components/ui/Pill";
import { StatTile } from "@/components/ui/StatTile";
import {
  directionClass,
  fmtDate,
  fmtPct,
  fmtSigned,
} from "@/lib/format";
import { labelFor, rangeFromSearch } from "@/lib/dateRange";
import { INFO } from "@/lib/info";

export default async function HypothesesPage({
  searchParams,
}: {
  searchParams: Record<string, string | string[] | undefined>;
}) {
  const range = rangeFromSearch(searchParams);
  const [universe, tracker] = await Promise.all([
    api.universe(),
    api.hypothesesTracker(range).catch(() => ({
      total: 0, scored: 0, correct: 0, accuracy_pct: null, rows: [],
    })),
  ]);

  return (
    <Shell universe={universe}>
      <header className="mb-3 flex flex-wrap items-baseline gap-4 border-b border-border pb-2">
        <h1 className="font-serif text-2xl font-medium tracking-tight">Hypothesis Tracker</h1>
        <span className="text-[11px] uppercase tracking-[0.1em] text-fg-faint">
          Predicted vs actual · {labelFor(range)}
        </span>
        <DateRangePicker className="ml-auto" />
      </header>

      <div className="mb-3 grid grid-cols-1 gap-3 md:grid-cols-4">
        <StatTile
          label="Events Tracked"
          value={tracker.total}
          info={INFO.hypotheses_events_tracked}
        />
        <StatTile
          label="Scored"
          value={tracker.scored}
          delta="BEAT or MISS label present"
          info={INFO.hypotheses_scored}
        />
        <StatTile
          label="Correct"
          value={tracker.correct}
          valueClass="text-accent"
          delta={`of ${tracker.scored} confirmed`}
          info={INFO.hypotheses_correct}
        />
        <StatTile
          label="Accuracy"
          value={tracker.accuracy_pct !== null ? `${tracker.accuracy_pct}%` : "—"}
          valueClass={
            (tracker.accuracy_pct ?? 0) >= 60 ? "text-up"
              : (tracker.accuracy_pct ?? 0) < 50 ? "text-down"
              : "text-amber"
          }
          delta="Baseline 50% = coin flip"
          info={INFO.hypotheses_accuracy}
        />
      </div>

      <Panel
        title="Historical Predictions"
        meta="LASSO ATTRIBUTION — TOP DRIVERS PER EVENT"
        tight
        info={INFO.hypotheses_history}
      >
        <table className="w-full text-[11px] tabular-nums">
          <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
            <tr>
              <th className="border-b border-border px-3 py-1.5 text-left font-medium">Date</th>
              <th className="border-b border-border px-3 py-1.5 text-left font-medium">Ticker</th>
              <th className="border-b border-border px-3 py-1.5 text-right font-medium">Predicted</th>
              <th className="border-b border-border px-3 py-1.5 text-right font-medium">Actual</th>
              <th className="border-b border-border px-3 py-1.5 text-right font-medium">Surprise</th>
              <th className="border-b border-border px-3 py-1.5 text-right font-medium">Reaction</th>
              <th className="border-b border-border px-3 py-1.5 text-right font-medium">✓</th>
              <th className="border-b border-border px-3 py-1.5 text-left font-medium">Top drivers</th>
            </tr>
          </thead>
          <tbody>
            {tracker.rows.map((r, idx) => (
              <tr key={`${r.ticker}-${r.report_date}-${idx}`} className="hover:bg-panel-2 align-top">
                <td className="border-b border-border px-3 py-2">{fmtDate(r.report_date)}</td>
                <td className="border-b border-border px-3 py-2">
                  <strong className="font-semibold text-accent">{r.ticker}</strong>
                  <div className="text-[10px] text-fg-faint">{r.fiscal_period ?? "—"}</div>
                </td>
                <td className="border-b border-border px-3 py-2 text-right">
                  {r.hypothesis_label ? (
                    <Pill tone={hypothesisTone(r.hypothesis_label)}>
                      {r.hypothesis_label} {fmtSigned(r.hypothesis_score, 2)}
                    </Pill>
                  ) : (
                    <Pill>—</Pill>
                  )}
                </td>
                <td className="border-b border-border px-3 py-2 text-right">
                  {r.actual ? (
                    <Pill tone={r.actual === "BEAT" ? "green" : "red"}>{r.actual}</Pill>
                  ) : (
                    <Pill>PENDING</Pill>
                  )}
                </td>
                <td className={`border-b border-border px-3 py-2 text-right ${directionClass(r.eps_surprise_pct)}`}>
                  {r.eps_surprise_pct !== null ? fmtPct(r.eps_surprise_pct, { digits: 1 }) : "—"}
                </td>
                <td className={`border-b border-border px-3 py-2 text-right ${directionClass(r.post_earnings_1d_return)}`}>
                  {r.post_earnings_1d_return !== null
                    ? fmtPct(r.post_earnings_1d_return, { digits: 2 })
                    : "—"}
                </td>
                <td className="border-b border-border px-3 py-2 text-right">
                  {r.prediction_correct === true && <span className="text-up">✓</span>}
                  {r.prediction_correct === false && <span className="text-down">✗</span>}
                  {r.prediction_correct === null && <span className="text-fg-faint">—</span>}
                </td>
                <td className="border-b border-border px-3 py-2">
                  {r.top_drivers && r.top_drivers.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {r.top_drivers.slice(0, 4).map((d) => (
                        <span
                          key={d.feature}
                          className={[
                            "rounded-sm border px-1.5 py-0 text-[10px]",
                            d.contribution > 0
                              ? "border-[rgba(63,217,123,0.4)] text-up"
                              : d.contribution < 0
                              ? "border-[rgba(255,92,92,0.4)] text-down"
                              : "border-border-hot text-fg-dim",
                          ].join(" ")}
                          title={`${d.feature}\nvalue ${d.value.toFixed(3)} × coef ${d.coefficient.toFixed(3)}`}
                        >
                          {d.feature}{" "}
                          {d.contribution > 0 ? "+" : ""}
                          {d.contribution.toFixed(2)}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-[10px] text-fg-faint">
                      features missing
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
    </Shell>
  );
}
