import type {
  AnalysisAxesResponse,
  BacktestReportOut,
  BriefingResponse,
  CommodityDetail,
  CommodityRow,
  CompanyDetail,
  CompanyFundamentals,
  CompanyHoldingsOut,
  CompanyPriceHistory,
  CorrelationOut,
  DCFResultOut,
  EarningsBootstrapOut,
  EarningsPostmortemOut,
  EarningsRow,
  EventAttributionResponse,
  EventOut,
  FilingOut,
  HeatmapResponse,
  HypothesisTrackerSummary,
  JobsSnapshotOut,
  MacroRow,
  MacroSeriesDetail,
  NewsItemOut,
  OptionsSummary,
  PricePathSimulationOut,
  RedditPostOut,
  RegressionFitOut,
  ScatterResponse,
  SocialPostOut,
  SourceRunOut,
  TrendsQueryOut,
  TrendsSeriesOut,
  UniverseHoldingsOut,
  UniverseRow,
  UpcomingEarnings,
} from "./types";
import type { DateRange } from "./dateRange";
import { toQueryString } from "./dateRange";

const BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string, revalidate = 60): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    next: { revalidate },
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`${path} → ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

/** Appends ?start_date=&end_date= or &start_date=&end_date= to the given path. */
function withRange(path: string, range?: DateRange): string {
  const qs = toQueryString(range ?? {});
  if (!qs) return path;
  return path.includes("?") ? `${path}${qs}` : `${path}?${qs.slice(1)}`;
}

export const api = {
  briefing: () => get<BriefingResponse>("/api/briefing", 60),
  universe: () => get<UniverseRow[]>("/api/universe", 60),
  events: (limit = 20, range?: DateRange) =>
    get<EventOut[]>(withRange(`/api/events?limit=${limit}`, range), 30),
  upcomingEarnings: () => get<UpcomingEarnings[]>("/api/earnings/upcoming", 300),
  macro: () => get<MacroRow[]>("/api/macro", 300),
  company: (ticker: string) =>
    get<CompanyDetail>(`/api/companies/${ticker.toUpperCase()}`, 300),

  companyPrices: (ticker: string, days = 90) =>
    get<CompanyPriceHistory>(
      `/api/companies/${ticker.toUpperCase()}/prices?days=${days}`,
      120,
    ),

  companyFundamentals: (ticker: string) =>
    get<CompanyFundamentals>(
      `/api/companies/${ticker.toUpperCase()}/fundamentals`,
      600,
    ),

  commodities: (category?: string) =>
    get<CommodityRow[]>(
      `/api/commodities${category ? `?category=${encodeURIComponent(category)}` : ""}`,
      600,
    ),

  commodityDetail: (symbol: string, range?: DateRange) =>
    get<CommodityDetail>(
      withRange(`/api/commodities/${encodeURIComponent(symbol)}`, range),
      600,
    ),

  optionsSummary: (ticker: string, limit = 60) =>
    get<OptionsSummary>(
      `/api/options/${ticker.toUpperCase()}?limit=${limit}`,
      300,
    ),

  simulatePricePaths: (
    ticker: string,
    params: {
      horizon_days?: number;
      n_paths?: number;
      model?: "gbm" | "merton";
      fit_window_days?: number;
      seed?: number;
    } = {},
  ) => {
    const qs = new URLSearchParams();
    if (params.horizon_days) qs.set("horizon_days", String(params.horizon_days));
    if (params.n_paths) qs.set("n_paths", String(params.n_paths));
    if (params.model) qs.set("model", params.model);
    if (params.fit_window_days) qs.set("fit_window_days", String(params.fit_window_days));
    if (params.seed !== undefined) qs.set("seed", String(params.seed));
    const s = qs.toString();
    return get<PricePathSimulationOut>(
      `/api/simulate/price-paths/${ticker.toUpperCase()}${s ? `?${s}` : ""}`,
      60,
    );
  },

  simulateBacktest: () =>
    get<BacktestReportOut>("/api/simulate/backtest", 600),

  companyHoldings: (ticker: string) =>
    get<CompanyHoldingsOut>(
      `/api/holdings/${ticker.toUpperCase()}`,
      600,
    ),

  universeHoldings: () => get<UniverseHoldingsOut>("/api/holdings", 600),

  simulateDCF: (
    ticker: string,
    params: {
      n_simulations?: number;
      years_explicit?: number;
      wacc_mean?: number;
      wacc_std?: number;
      terminal_growth?: number;
      growth_override?: number;
      margin_override?: number;
      seed?: number;
    } = {},
  ) => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) qs.set(k, String(v));
    }
    const s = qs.toString();
    return get<DCFResultOut>(
      `/api/simulate/dcf/${ticker.toUpperCase()}${s ? `?${s}` : ""}`,
      300,
    );
  },

  simulateEarningsBootstrap: (
    ticker: string,
    params: {
      fiscal_period?: string;
      n_bootstrap?: number;
      tolerance?: number;
      seed?: number;
    } = {},
  ) => {
    const qs = new URLSearchParams();
    if (params.fiscal_period) qs.set("fiscal_period", params.fiscal_period);
    if (params.n_bootstrap) qs.set("n_bootstrap", String(params.n_bootstrap));
    if (params.tolerance !== undefined) qs.set("tolerance", String(params.tolerance));
    if (params.seed !== undefined) qs.set("seed", String(params.seed));
    const s = qs.toString();
    return get<EarningsBootstrapOut>(
      `/api/simulate/earnings-bootstrap/${ticker.toUpperCase()}${s ? `?${s}` : ""}`,
      300,
    );
  },

  news: (ticker?: string, limit = 50, range?: DateRange) =>
    get<NewsItemOut[]>(
      withRange(
        `/api/news?limit=${limit}${ticker ? `&ticker=${ticker.toUpperCase()}` : ""}`,
        range,
      ),
      120,
    ),

  social: (ticker?: string, limit = 50, range?: DateRange) =>
    get<SocialPostOut[]>(
      withRange(
        `/api/social?limit=${limit}${ticker ? `&ticker=${ticker.toUpperCase()}` : ""}`,
        range,
      ),
      120,
    ),

  reddit: (ticker?: string, limit = 50, range?: DateRange) =>
    get<RedditPostOut[]>(
      withRange(
        `/api/social/reddit?limit=${limit}${ticker ? `&ticker=${ticker.toUpperCase()}` : ""}`,
        range,
      ),
      120,
    ),

  filings: (ticker?: string, limit = 50, range?: DateRange) =>
    get<FilingOut[]>(
      withRange(
        `/api/filings?limit=${limit}${ticker ? `&ticker=${ticker.toUpperCase()}` : ""}`,
        range,
      ),
      300,
    ),

  jobs: (ticker?: string, limit = 30, range?: DateRange) =>
    get<JobsSnapshotOut[]>(
      withRange(
        `/api/jobs?limit=${limit}${ticker ? `&ticker=${ticker.toUpperCase()}` : ""}`,
        range,
      ),
      600,
    ),

  correlations: (target?: string, method?: string) => {
    const parts = [];
    if (target) parts.push(`target=${encodeURIComponent(target)}`);
    if (method) parts.push(`method=${encodeURIComponent(method)}`);
    const qs = parts.length ? `?${parts.join("&")}` : "";
    return get<CorrelationOut[]>(`/api/analysis/correlations${qs}`, 600);
  },

  sourceRuns: (limit = 30, range?: DateRange) =>
    get<SourceRunOut[]>(
      withRange(`/api/ops/source-runs?limit=${limit}`, range),
      30,
    ),

  earningsAll: (
    params: {
      ticker?: string;
      past_only?: boolean;
      upcoming_only?: boolean;
    } = {},
    range?: DateRange,
  ) => {
    const qs = new URLSearchParams();
    if (params.ticker) qs.set("ticker", params.ticker.toUpperCase());
    if (params.past_only) qs.set("past_only", "true");
    if (params.upcoming_only) qs.set("upcoming_only", "true");
    if (range?.from) qs.set("start_date", range.from);
    if (range?.to) qs.set("end_date", range.to);
    const s = qs.toString();
    return get<EarningsRow[]>(`/api/earnings${s ? `?${s}` : ""}`, 300);
  },

  hypothesesTracker: (range?: DateRange) =>
    get<HypothesisTrackerSummary>(
      withRange("/api/hypotheses", range),
      300,
    ),

  analysisAxes: () => get<AnalysisAxesResponse>("/api/analysis/axes", 3600),

  scatter: (feature: string, target: string, range?: DateRange) =>
    get<ScatterResponse>(
      withRange(
        `/api/analysis/scatter?feature=${encodeURIComponent(feature)}&target=${encodeURIComponent(target)}`,
        range,
      ),
      600,
    ),

  heatmap: (method: "pearson" | "spearman" = "pearson", range?: DateRange) =>
    get<HeatmapResponse>(
      withRange(`/api/analysis/heatmap?method=${method}`, range),
      600,
    ),

  regression: (range?: DateRange) =>
    get<RegressionFitOut[]>(withRange("/api/analysis/regression", range), 600),

  attribution: (earningsId: number, target = "eps_surprise_pct") =>
    get<EventAttributionResponse>(
      `/api/analysis/attribution/${earningsId}?target=${encodeURIComponent(target)}`,
      600,
    ),

  postmortem: (earningsId: number) =>
    get<EarningsPostmortemOut>(
      `/api/earnings/${earningsId}/postmortem`,
      600,
    ),

  trendsQueries: (params: { category?: string; ticker?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.category) qs.set("category", params.category);
    if (params.ticker) qs.set("ticker", params.ticker.toUpperCase());
    const s = qs.toString();
    return get<TrendsQueryOut[]>(`/api/trends${s ? `?${s}` : ""}`, 600);
  },

  trendsSeries: (queryId: number, range?: DateRange) =>
    get<TrendsSeriesOut>(
      withRange(`/api/trends/${queryId}`, range),
      600,
    ),

  macroSeries: async (seriesId: string, days = 365) => {
    const raw = await get<MacroSeriesDetail>(
      `/api/macro/${seriesId}?days=${days}`,
      600,
    );
    return {
      ...raw,
      observations: (raw.observations as unknown as {
        date: string;
        value: number | null;
      }[]),
    };
  },
};
