import type {
  AnalysisAxesResponse,
  BriefingResponse,
  CompanyDetail,
  CompanyPriceHistory,
  CorrelationOut,
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
  RedditPostOut,
  RegressionFitOut,
  ScatterResponse,
  SocialPostOut,
  SourceRunOut,
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
