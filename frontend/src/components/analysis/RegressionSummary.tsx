import type { RegressionFitOut } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";
import { fmtSigned } from "@/lib/format";

function fmtR2(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return v.toFixed(3);
}

function fitTone(v: number | null | undefined): string {
  if (v === null || v === undefined) return "text-fg-dim";
  if (v >= 0.2) return "text-up";
  if (v <= 0) return "text-down";
  return "text-amber";
}

export function RegressionSummary({ fits }: { fits: RegressionFitOut[] }) {
  if (fits.length === 0) {
    return (
      <Panel title="Regression">
        <p className="text-[11px] text-fg-dim">
          Not enough feature rows to fit yet. Run the features worker and
          backfill actuals on past earnings to populate this.
        </p>
      </Panel>
    );
  }

  const grouped = new Map<string, RegressionFitOut[]>();
  for (const f of fits) {
    if (!grouped.has(f.target)) grouped.set(f.target, []);
    grouped.get(f.target)!.push(f);
  }

  return (
    <div className="space-y-3">
      {[...grouped.entries()].map(([target, group]) => (
        <Panel key={target} title={`Regression · target = ${target}`} meta={`${group.length} fits`} tight>
          <div className="grid grid-cols-1 gap-3 p-3 md:grid-cols-2">
            {group.map((f) => (
              <div key={`${f.method}-${f.target}`} className="border border-border bg-panel-2 p-3">
                <div className="flex items-baseline gap-2">
                  <span className="font-mono text-[11px] uppercase tracking-[0.1em] text-accent">
                    {f.method}
                  </span>
                  <span className="text-[10px] text-fg-faint">n = {f.n}</span>
                  {f.note && (
                    <span className="ml-auto text-[10px] text-amber">{f.note}</span>
                  )}
                </div>

                <div className="mt-2 grid grid-cols-3 gap-2 text-[11px]">
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.1em] text-fg-faint">R² in-sample</div>
                    <div className={`font-serif text-[18px] ${fitTone(f.r_squared)}`}>
                      {fmtR2(f.r_squared)}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.1em] text-fg-faint">R² LOO</div>
                    <div
                      className={`font-serif text-[18px] ${fitTone(f.r_squared_loo)}`}
                      title="Leave-one-out cross-validated R²"
                    >
                      {fmtR2(f.r_squared_loo)}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.1em] text-fg-faint">RMSE</div>
                    <div className="font-serif text-[18px] text-fg-dim">
                      {f.rmse.toFixed(3)}
                    </div>
                  </div>
                </div>

                <div className="mt-3 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
                  Top 5 coefficients
                </div>
                <ul className="mt-1 divide-y divide-border text-[11px] tabular-nums">
                  {f.coefficients.slice(0, 5).map((c) => (
                    <li key={c.feature} className="flex items-center justify-between py-1">
                      <span className="truncate text-fg-dim" title={c.feature}>
                        {c.feature}
                      </span>
                      <span className={c.value >= 0 ? "text-up" : "text-down"}>
                        {fmtSigned(c.value, 3)}
                      </span>
                    </li>
                  ))}
                </ul>
                <div className="mt-2 text-[10px] text-fg-faint">
                  intercept: {fmtSigned(f.intercept, 3)} · {f.features_used.length} features retained
                </div>
              </div>
            ))}
          </div>
        </Panel>
      ))}
    </div>
  );
}
