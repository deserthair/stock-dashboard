import { api } from "@/lib/api";
import { Shell } from "@/components/layout/Shell";
import { SimulatePanel } from "./SimulatePanel";

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

  const [universe, initialPrice, initialBootstrap] = await Promise.all([
    api.universe(),
    api.simulatePricePaths(ticker, {
      horizon_days: DEFAULT_HORIZON,
      n_paths: DEFAULT_PATHS,
      model: "gbm",
      seed: 42,
    }),
    api.simulateEarningsBootstrap(ticker, { seed: 42 }),
  ]);

  return (
    <Shell universe={universe} activeTicker={ticker}>
      <header className="mb-3 flex flex-wrap items-baseline gap-4 border-b border-border pb-2">
        <h1 className="font-serif text-2xl font-medium tracking-tight">Simulations</h1>
        <span className="text-[11px] uppercase tracking-[0.1em] text-fg-faint">
          Monte Carlo price paths · earnings-reaction bootstrap
        </span>
      </header>

      <div className="mb-3 border border-border-hot border-l-[3px] border-l-accent bg-gradient-to-br from-[rgba(212,255,63,0.04)] via-transparent to-transparent px-4 py-3.5">
        <div className="mb-1 text-[10px] uppercase tracking-[0.15em] text-accent">
          ◆ What this is, honestly
        </div>
        <div className="font-serif text-[13px] leading-[1.6] text-fg">
          <strong>Monte Carlo paths</strong> fit a log-normal return
          distribution (μ, σ) from recent daily closes and project forward.
          The <strong>Merton</strong> variant injects a log-normal jump
          at each scheduled earnings date using the latest options-implied
          move. The <strong>bootstrap</strong> resamples actual
          post-earnings reactions from peer events with similar hypothesis
          scores. None of this is a prediction — it&apos;s a distribution
          grounded in the data you already have. GBM assumes constant
          volatility and ignores fat tails; the implied-move jump is the
          market&apos;s expectation, not a floor or ceiling.
        </div>
      </div>

      <SimulatePanel
        universe={universe}
        initialTicker={ticker}
        initialPrice={initialPrice}
        initialBootstrap={initialBootstrap}
      />
    </Shell>
  );
}
