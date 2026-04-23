import { api } from "@/lib/api";
import { Shell } from "@/components/layout/Shell";
import { Panel } from "@/components/ui/Panel";
import { Pill, hypothesisTone } from "@/components/ui/Pill";
import { StatTile } from "@/components/ui/StatTile";
import {
  directionClass,
  fmtDate,
  fmtPct,
  fmtSigned,
} from "@/lib/format";

export const revalidate = 300;

export default async function HypothesesPage() {
  const [universe, tracker] = await Promise.all([
    api.universe(),
    api.hypothesesTracker().catch(() => ({
      total: 0, scored: 0, correct: 0, accuracy_pct: null, rows: [],
    })),
  ]);

  return (
    <Shell universe={universe}>
      <header className="mb-3 flex items-baseline gap-4 border-b border-border pb-2">
        <h1 className="font-serif text-2xl font-medium tracking-tight">Hypothesis Tracker</h1>
        <span className="text-[11px] uppercase tracking-[0.1em] text-fg-faint">
          Predicted vs actual · running accuracy
        </span>
      </header>

      <div className="mb-3 grid grid-cols-1 gap-3 md:grid-cols-4">
        <StatTile label="Events Tracked" value={tracker.total} />
        <StatTile label="Scored" value={tracker.scored} delta="BEAT or MISS label present" />
        <StatTile
          label="Correct"
          value={tracker.correct}
          valueClass="text-accent"
          delta={`of ${tracker.scored} confirmed`}
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
        />
      </div>

      <Panel title="Historical Predictions" meta="ALL EVENTS" tight>
        <table className="w-full text-[11px] tabular-nums">
          <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
            <tr>
              <th className="border-b border-border px-3 py-1.5 text-left font-medium">Date</th>
              <th className="border-b border-border px-3 py-1.5 text-left font-medium">Ticker</th>
              <th className="border-b border-border px-3 py-1.5 text-left font-medium">Period</th>
              <th className="border-b border-border px-3 py-1.5 text-right font-medium">Predicted</th>
              <th className="border-b border-border px-3 py-1.5 text-right font-medium">Actual</th>
              <th className="border-b border-border px-3 py-1.5 text-right font-medium">Surprise</th>
              <th className="border-b border-border px-3 py-1.5 text-right font-medium">Reaction</th>
              <th className="border-b border-border px-3 py-1.5 text-right font-medium">Correct?</th>
            </tr>
          </thead>
          <tbody>
            {tracker.rows.map((r, idx) => (
              <tr key={`${r.ticker}-${r.report_date}-${idx}`} className="hover:bg-panel-2">
                <td className="border-b border-border px-3 py-1.5">{fmtDate(r.report_date)}</td>
                <td className="border-b border-border px-3 py-1.5">
                  <strong className="font-semibold text-accent">{r.ticker}</strong>
                </td>
                <td className="border-b border-border px-3 py-1.5 text-fg-dim">
                  {r.fiscal_period ?? "—"}
                </td>
                <td className="border-b border-border px-3 py-1.5 text-right">
                  {r.hypothesis_label ? (
                    <Pill tone={hypothesisTone(r.hypothesis_label)}>
                      {r.hypothesis_label} {fmtSigned(r.hypothesis_score, 2)}
                    </Pill>
                  ) : (
                    <Pill>—</Pill>
                  )}
                </td>
                <td className="border-b border-border px-3 py-1.5 text-right">
                  {r.actual ? (
                    <Pill tone={r.actual === "BEAT" ? "green" : "red"}>{r.actual}</Pill>
                  ) : (
                    <Pill>PENDING</Pill>
                  )}
                </td>
                <td className={`border-b border-border px-3 py-1.5 text-right ${directionClass(r.eps_surprise_pct)}`}>
                  {r.eps_surprise_pct !== null ? fmtPct(r.eps_surprise_pct, { digits: 1 }) : "—"}
                </td>
                <td className={`border-b border-border px-3 py-1.5 text-right ${directionClass(r.post_earnings_1d_return)}`}>
                  {r.post_earnings_1d_return !== null
                    ? fmtPct(r.post_earnings_1d_return, { digits: 2 })
                    : "—"}
                </td>
                <td className="border-b border-border px-3 py-1.5 text-right">
                  {r.prediction_correct === true && (
                    <span className="text-up">✓</span>
                  )}
                  {r.prediction_correct === false && (
                    <span className="text-down">✗</span>
                  )}
                  {r.prediction_correct === null && (
                    <span className="text-fg-faint">—</span>
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
