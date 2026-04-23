import { api } from "@/lib/api";
import { Shell } from "@/components/layout/Shell";
import { Panel } from "@/components/ui/Panel";
import { fmtSigned } from "@/lib/format";

export const revalidate = 600;

export default async function CorrelationsPage() {
  const [universe, correlations] = await Promise.all([
    api.universe(),
    api.correlations().catch(() => []),
  ]);

  return (
    <Shell universe={universe}>
      <header className="mb-3 flex items-baseline gap-4 border-b border-border pb-2">
        <h1 className="font-serif text-2xl font-medium tracking-tight">
          Correlations
        </h1>
        <span className="text-[11px] uppercase tracking-[0.1em] text-fg-faint">
          Univariate · Feature vs Target
        </span>
      </header>

      {correlations.length === 0 ? (
        <Panel title="No correlations computed yet">
          <p className="text-[11px] text-fg-dim">
            Feature vectors and correlations are computed daily from earnings
            history. Once at least 6 completed earnings events have sufficient
            prior data, the <code>analysis.correlation</code> worker will
            populate this view with Pearson + Spearman coefficients, bootstrap
            95% CIs, and Benjamini-Hochberg-adjusted p-values.
          </p>
        </Panel>
      ) : (
        <Panel title={`${correlations.length} results`} meta="ORDER: p_adjusted ↑" tight>
          <table className="w-full text-[11px] tabular-nums">
            <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
              <tr>
                <th className="border-b border-border px-3 py-1.5 text-left font-medium">Feature</th>
                <th className="border-b border-border px-3 py-1.5 text-left font-medium">Target</th>
                <th className="border-b border-border px-3 py-1.5 text-left font-medium">Method</th>
                <th className="border-b border-border px-3 py-1.5 text-right font-medium">n</th>
                <th className="border-b border-border px-3 py-1.5 text-right font-medium">r</th>
                <th className="border-b border-border px-3 py-1.5 text-right font-medium">95% CI</th>
                <th className="border-b border-border px-3 py-1.5 text-right font-medium">p</th>
                <th className="border-b border-border px-3 py-1.5 text-right font-medium">p-adj</th>
              </tr>
            </thead>
            <tbody>
              {correlations.map((c, i) => (
                <tr
                  key={`${c.feature_name}-${c.target_name}-${c.method}-${i}`}
                  className="hover:bg-panel-2"
                >
                  <td className="border-b border-border px-3 py-1.5">{c.feature_name}</td>
                  <td className="border-b border-border px-3 py-1.5">{c.target_name}</td>
                  <td className="border-b border-border px-3 py-1.5 text-fg-dim">{c.method}</td>
                  <td className="border-b border-border px-3 py-1.5 text-right">{c.n}</td>
                  <td className="border-b border-border px-3 py-1.5 text-right">
                    {fmtSigned(c.coefficient, 3)}
                  </td>
                  <td className="border-b border-border px-3 py-1.5 text-right text-fg-dim">
                    [{fmtSigned(c.ci_low, 2)}, {fmtSigned(c.ci_high, 2)}]
                  </td>
                  <td className="border-b border-border px-3 py-1.5 text-right">
                    {c.p_value !== null ? c.p_value.toFixed(3) : "—"}
                  </td>
                  <td className={`border-b border-border px-3 py-1.5 text-right ${
                    (c.p_adjusted ?? 1) < 0.05 ? "text-accent" : "text-fg-dim"
                  }`}>
                    {c.p_adjusted !== null ? c.p_adjusted.toFixed(3) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      )}
    </Shell>
  );
}
