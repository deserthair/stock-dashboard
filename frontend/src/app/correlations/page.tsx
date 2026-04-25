import { api } from "@/lib/api";
import { CorrelationLab } from "@/components/analysis/CorrelationLab";
import { Heatmap } from "@/components/analysis/Heatmap";
import { RegressionSummary } from "@/components/analysis/RegressionSummary";
import { Shell } from "@/components/layout/Shell";
import { DateRangePicker } from "@/components/ui/DateRangePicker";
import { Panel } from "@/components/ui/Panel";
import { fmtSigned } from "@/lib/format";
import { labelFor, rangeFromSearch } from "@/lib/dateRange";
import { INFO } from "@/lib/info";

const DEFAULT_FEATURE = "news_sentiment_mean_30d";
const DEFAULT_TARGET = "eps_surprise_pct";

export default async function CorrelationsPage({
  searchParams,
}: {
  searchParams: Record<string, string | string[] | undefined>;
}) {
  const range = rangeFromSearch(searchParams);
  const [universe, axes, scatter, heatmap, regressions, correlations] = await Promise.all([
    api.universe(),
    api.analysisAxes().catch(() => ({ features: [], targets: [] })),
    api
      .scatter(DEFAULT_FEATURE, DEFAULT_TARGET, range)
      .catch(() => ({
        feature: DEFAULT_FEATURE,
        target: DEFAULT_TARGET,
        points: [],
        line: null,
      })),
    api.heatmap("pearson", range).catch(() => ({
      method: "pearson",
      features: [],
      matrix: [],
      sample_sizes: [],
    })),
    api.regression(range).catch(() => []),
    api.correlations().catch(() => []),
  ]);

  return (
    <Shell universe={universe}>
      <header className="mb-3 flex flex-wrap items-baseline gap-4 border-b border-border pb-2">
        <h1 className="font-serif text-2xl font-medium tracking-tight">
          Correlation Lab
        </h1>
        <span className="text-[11px] uppercase tracking-[0.1em] text-fg-faint">
          Scatter · heatmap · OLS vs Lasso · {labelFor(range)}
        </span>
        <DateRangePicker className="ml-auto" />
      </header>

      <div className="mb-3 grid grid-cols-1 gap-3 xl:grid-cols-[1.4fr_1fr]">
        <CorrelationLab
          axes={axes}
          initialFeature={DEFAULT_FEATURE}
          initialTarget={DEFAULT_TARGET}
          initial={scatter}
        />

        <Panel
          title="Feature × Feature Heatmap"
          meta={heatmap.method.toUpperCase()}
          info={INFO.correlations_heatmap}
        >
          {heatmap.features.length === 0 ? (
            <p className="text-[11px] text-fg-dim">
              Not enough feature rows. Populate <code>features_earnings</code>.
            </p>
          ) : (
            <Heatmap data={heatmap} />
          )}
        </Panel>
      </div>

      <div className="mb-3">
        <RegressionSummary fits={regressions} />
      </div>

      <Panel
        title={`Ranked Univariate Correlations (${correlations.length})`}
        meta="ORDER: p_adjusted ↑"
        tight
        info={INFO.correlations_table}
      >
        {correlations.length === 0 ? (
          <p className="px-3 py-8 text-center text-[11px] text-fg-faint">
            Run <code>python -m analysis.correlation</code> to populate this table
            after feature vectors exist.
          </p>
        ) : (
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
        )}
      </Panel>
    </Shell>
  );
}
