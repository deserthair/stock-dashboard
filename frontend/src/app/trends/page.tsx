import { api } from "@/lib/api";
import { Shell } from "@/components/layout/Shell";
import { DateRangePicker } from "@/components/ui/DateRangePicker";
import { Panel } from "@/components/ui/Panel";
import { TrendsCard } from "@/components/trends/TrendsSparkline";
import { labelFor, rangeFromSearch } from "@/lib/dateRange";
import type { TrendsSeriesOut } from "@/lib/types";

const CATEGORIES: { key: "company" | "menu" | "segment" | "macro"; title: string; sub: string }[] = [
  { key: "segment", title: "Food-industry segments",       sub: "fast casual · QSR · casual dining · delivery" },
  { key: "macro",   title: "Consumer-behavior queries",    sub: "restaurant inflation · dining out · fast food prices" },
  { key: "menu",    title: "Signature menu items",         sub: "protein bowl · pumpkin spice · bloomin' onion" },
  { key: "company", title: "Per-ticker brand queries",     sub: "Chipotle · Starbucks · Cava · …" },
];

export default async function TrendsPage({
  searchParams,
}: {
  searchParams: Record<string, string | string[] | undefined>;
}) {
  const range = rangeFromSearch(searchParams);
  const [universe, queries] = await Promise.all([
    api.universe(),
    api.trendsQueries().catch(() => []),
  ]);

  // Fetch the series for every query in parallel.
  const series = await Promise.all(
    queries.map((q) => api.trendsSeries(q.query_id, range).catch(() => null)),
  );
  const seriesByCat = new Map<string, TrendsSeriesOut[]>();
  for (let i = 0; i < queries.length; i++) {
    const s = series[i];
    if (!s) continue;
    const cat = queries[i].category;
    if (!seriesByCat.has(cat)) seriesByCat.set(cat, []);
    seriesByCat.get(cat)!.push(s);
  }

  return (
    <Shell universe={universe}>
      <header className="mb-3 flex flex-wrap items-baseline gap-4 border-b border-border pb-2">
        <h1 className="font-serif text-2xl font-medium tracking-tight">Google Trends</h1>
        <span className="text-[11px] uppercase tracking-[0.1em] text-fg-faint">
          {queries.length} queries · {labelFor(range)}
        </span>
        <DateRangePicker className="ml-auto" />
      </header>

      {queries.length === 0 ? (
        <Panel title="No trends ingested yet">
          <p className="text-[11px] text-fg-dim">
            Run <code>python -m ingest.sources.trends</code> (with{" "}
            <code>pytrends</code> installed) or re-seed to populate demo data.
          </p>
        </Panel>
      ) : (
        <div className="space-y-6">
          {CATEGORIES.map((c) => {
            const rows = seriesByCat.get(c.key) ?? [];
            if (rows.length === 0) return null;
            // Sort by 90d change so the movers surface at the top.
            rows.sort((a, b) => (b.change_90d_pct ?? 0) - (a.change_90d_pct ?? 0));
            return (
              <section key={c.key}>
                <div className="mb-2 flex items-baseline gap-2">
                  <h2 className="font-serif text-[18px] font-medium tracking-tight">
                    {c.title}
                  </h2>
                  <span className="text-[10px] uppercase tracking-[0.15em] text-fg-faint">
                    {c.sub}
                  </span>
                </div>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {rows.map((t) => (
                    <TrendsCard key={t.query.query_id} series={t} />
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </Shell>
  );
}
