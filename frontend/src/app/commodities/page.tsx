import { api } from "@/lib/api";
import { Shell } from "@/components/layout/Shell";
import { DateRangePicker } from "@/components/ui/DateRangePicker";
import { Panel } from "@/components/ui/Panel";
import { Pill } from "@/components/ui/Pill";
import { CommoditySparkline } from "@/components/commodities/CommoditySparkline";
import { directionClass, fmtPct } from "@/lib/format";
import { labelFor, rangeFromSearch } from "@/lib/dateRange";

const CATEGORY_ORDER: { key: string; title: string; sub: string }[] = [
  { key: "protein",  title: "Protein futures",  sub: "live cattle · feeder cattle · lean hogs · poultry PPI" },
  { key: "grain",    title: "Grain futures",    sub: "corn · soybeans · wheat — inputs to feed + flour" },
  { key: "produce",  title: "Produce (PPI)",    sub: "lettuce · tomatoes — no tradable futures, BLS index" },
  { key: "soft",     title: "Soft commodities", sub: "coffee · sugar · orange juice" },
  { key: "dairy",    title: "Dairy futures",    sub: "Class III milk" },
  { key: "energy",   title: "Energy futures",   sub: "WTI crude — fuel + logistics proxy" },
];

export default async function CommoditiesPage({
  searchParams,
}: {
  searchParams: Record<string, string | string[] | undefined>;
}) {
  const range = rangeFromSearch(searchParams);
  const [universe, list] = await Promise.all([
    api.universe(),
    api.commodities().catch(() => []),
  ]);

  // Pull the detail (observations) for every symbol so we can sparkline them.
  const details = await Promise.all(
    list.map((row) => api.commodityDetail(row.meta.symbol, range).catch(() => null)),
  );
  const bySymbol = new Map(
    details
      .map((d, i) => (d ? [list[i].meta.symbol, d] as const : null))
      .filter((x): x is [string, typeof details[number] & {}] => x !== null),
  );

  return (
    <Shell universe={universe}>
      <header className="mb-3 flex flex-wrap items-baseline gap-4 border-b border-border pb-2">
        <h1 className="font-serif text-2xl font-medium tracking-tight">Commodities</h1>
        <span className="text-[11px] uppercase tracking-[0.1em] text-fg-faint">
          {list.length} markets · {labelFor(range)}
        </span>
        <DateRangePicker className="ml-auto" />
      </header>

      {list.length === 0 ? (
        <Panel title="No commodity data yet">
          <p className="text-[11px] text-fg-dim">
            Run <code>python -m ingest.sources.commodities</code> (needs{" "}
            <code>yfinance</code> for futures and <code>FRED_API_KEY</code> for
            BLS PPI series) or re-seed for demo data.
          </p>
        </Panel>
      ) : (
        <div className="space-y-5">
          {CATEGORY_ORDER.map((c) => {
            const rows = list.filter((r) => r.meta.category === c.key);
            if (rows.length === 0) return null;
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
                  {rows.map((row) => {
                    const detail = bySymbol.get(row.meta.symbol);
                    const obs = detail?.observations ?? [];
                    return (
                      <Panel
                        key={row.meta.symbol}
                        title={row.meta.label}
                        meta={`${row.meta.symbol} · ${row.meta.unit ?? ""}`}
                        tight
                      >
                        <div className="flex items-baseline gap-3 px-3 py-2">
                          <div className="font-serif text-[22px] font-medium tabular-nums">
                            {row.latest !== null && row.latest !== undefined
                              ? row.latest.toFixed(2)
                              : "—"}
                          </div>
                          <span className="text-[10px] uppercase tracking-[0.15em] text-fg-faint">
                            latest
                          </span>
                          <span className="ml-auto text-[11px] tabular-nums">
                            <span className={directionClass(row.change_30d_pct)}>
                              30d {fmtPct(row.change_30d_pct, { digits: 1 })}
                            </span>{" "}
                            <span className="text-fg-faint">·</span>{" "}
                            <span className={directionClass(row.change_90d_pct)}>
                              90d {fmtPct(row.change_90d_pct, { digits: 1 })}
                            </span>{" "}
                            <span className="text-fg-faint">·</span>{" "}
                            <span className={directionClass(row.change_1y_pct)}>
                              1y {fmtPct(row.change_1y_pct, { digits: 1 })}
                            </span>
                          </span>
                        </div>
                        <div className="px-3 py-2">
                          <CommoditySparkline
                            data={obs}
                            width={320}
                            height={56}
                            color={
                              row.change_90d_pct !== null && row.change_90d_pct > 0
                                ? "#3fd97b"
                                : row.change_90d_pct !== null && row.change_90d_pct < 0
                                ? "#ff5c5c"
                                : "#5cd5ff"
                            }
                          />
                        </div>
                        <div className="flex flex-wrap gap-1 border-t border-border px-3 py-2 text-[10px] text-fg-faint">
                          <span className="uppercase tracking-[0.15em]">Exposure:</span>
                          {row.meta.exposure.length > 0 ? (
                            row.meta.exposure.map((t) => (
                              <Pill key={t} tone="default">
                                {t}
                              </Pill>
                            ))
                          ) : (
                            <span>—</span>
                          )}
                        </div>
                      </Panel>
                    );
                  })}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </Shell>
  );
}
