import { api } from "@/lib/api";
import { Shell } from "@/components/layout/Shell";
import { SimulateTabs } from "./SimulateTabs";

const DEFAULT_TICKER = "CMG";
const DEFAULT_HORIZON = 30;
const DEFAULT_PATHS = 10_000;

export default async function SimulatePage({
  searchParams,
}: {
  searchParams: Record<string, string | string[] | undefined>;
}) {
  const ticker =
    typeof searchParams.ticker === "string" && searchParams.ticker.length > 0
      ? searchParams.ticker.toUpperCase()
      : DEFAULT_TICKER;

  const [universe, initialPrice, initialBootstrap, initialDCF] = await Promise.all([
    api.universe(),
    api.simulatePricePaths(ticker, {
      horizon_days: DEFAULT_HORIZON,
      n_paths: DEFAULT_PATHS,
      model: "gbm",
      seed: 42,
    }),
    api.simulateEarningsBootstrap(ticker, { seed: 42 }),
    api.simulateDCF(ticker, { seed: 42 }).catch(() => null),
  ]);

  return (
    <Shell universe={universe} activeTicker={ticker}>
      <header className="mb-3 flex flex-wrap items-baseline gap-4 border-b border-border pb-2">
        <h1 className="font-serif text-2xl font-medium tracking-tight">Simulations</h1>
        <span className="text-[11px] uppercase tracking-[0.1em] text-fg-faint">
          Monte Carlo price paths · earnings-reaction bootstrap · probabilistic DCF
        </span>
      </header>

      <div className="mb-3 border border-border-hot border-l-[3px] border-l-accent bg-gradient-to-br from-[rgba(212,255,63,0.04)] via-transparent to-transparent px-4 py-3.5">
        <div className="mb-1 text-[10px] uppercase tracking-[0.15em] text-accent">
          ◆ What this is, honestly
        </div>
        <div className="font-serif text-[13px] leading-[1.6] text-fg">
          <strong>Price paths</strong> fit GBM (or Merton at earnings) from recent
          daily closes. <strong>Bootstrap</strong> resamples actual post-earnings
          reactions from similar-score peer events. <strong>DCF</strong> Monte
          Carlos over growth × margin × WACC to produce a distribution of
          intrinsic value per share. None of this is a prediction — it&apos;s a
          distribution grounded in data. Each tab&apos;s caveats are called out
          inline.
        </div>
      </div>

      <SimulateTabs
        universe={universe}
        initialTicker={ticker}
        initialPrice={initialPrice}
        initialBootstrap={initialBootstrap}
        initialDCF={initialDCF}
      />
    </Shell>
  );
}
