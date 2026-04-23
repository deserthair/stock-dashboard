import type {
  BriefingResponse,
  CompanyDetail,
  CompanyPriceHistory,
  CorrelationOut,
  EarningsRow,
  EventOut,
  FilingOut,
  HypothesisTrackerSummary,
  JobsSnapshotOut,
  MacroRow,
  MacroSeriesDetail,
  NewsItemOut,
  RedditPostOut,
  SocialPostOut,
  SourceRunOut,
  UniverseRow,
  UpcomingEarnings,
} from "./types";

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

export const api = {
  briefing: () => get<BriefingResponse>("/api/briefing", 60),
  universe: () => get<UniverseRow[]>("/api/universe", 60),
  events: (limit = 20) => get<EventOut[]>(`/api/events?limit=${limit}`, 30),
  upcomingEarnings: () => get<UpcomingEarnings[]>("/api/earnings/upcoming", 300),
  macro: () => get<MacroRow[]>("/api/macro", 300),
  company: (ticker: string) =>
    get<CompanyDetail>(`/api/companies/${ticker.toUpperCase()}`, 300),

  companyPrices: (ticker: string, days = 90) =>
    get<CompanyPriceHistory>(
      `/api/companies/${ticker.toUpperCase()}/prices?days=${days}`,
      120,
    ),

  news: (ticker?: string, limit = 50) =>
    get<NewsItemOut[]>(
      `/api/news?limit=${limit}${ticker ? `&ticker=${ticker.toUpperCase()}` : ""}`,
      120,
    ),

  social: (ticker?: string, limit = 50) =>
    get<SocialPostOut[]>(
      `/api/social?limit=${limit}${ticker ? `&ticker=${ticker.toUpperCase()}` : ""}`,
      120,
    ),

  reddit: (ticker?: string, limit = 50) =>
    get<RedditPostOut[]>(
      `/api/social/reddit?limit=${limit}${ticker ? `&ticker=${ticker.toUpperCase()}` : ""}`,
      120,
    ),

  filings: (ticker?: string, limit = 50) =>
    get<FilingOut[]>(
      `/api/filings?limit=${limit}${ticker ? `&ticker=${ticker.toUpperCase()}` : ""}`,
      300,
    ),

  jobs: (ticker?: string, limit = 30) =>
    get<JobsSnapshotOut[]>(
      `/api/jobs?limit=${limit}${ticker ? `&ticker=${ticker.toUpperCase()}` : ""}`,
      600,
    ),

  correlations: (target?: string, method?: string) => {
    const parts = [];
    if (target) parts.push(`target=${encodeURIComponent(target)}`);
    if (method) parts.push(`method=${encodeURIComponent(method)}`);
    const qs = parts.length ? `?${parts.join("&")}` : "";
    return get<CorrelationOut[]>(`/api/analysis/correlations${qs}`, 600);
  },

  sourceRuns: (limit = 30) =>
    get<SourceRunOut[]>(`/api/ops/source-runs?limit=${limit}`, 30),

  earningsAll: (params: { ticker?: string; past_only?: boolean; upcoming_only?: boolean } = {}) => {
    const qs = new URLSearchParams();
    if (params.ticker) qs.set("ticker", params.ticker.toUpperCase());
    if (params.past_only) qs.set("past_only", "true");
    if (params.upcoming_only) qs.set("upcoming_only", "true");
    const s = qs.toString();
    return get<EarningsRow[]>(`/api/earnings${s ? `?${s}` : ""}`, 300);
  },

  hypothesesTracker: () =>
    get<HypothesisTrackerSummary>("/api/hypotheses", 300),

  macroSeries: async (seriesId: string, days = 365) => {
    const raw = await get<MacroSeriesDetail>(
      `/api/macro/${seriesId}?days=${days}`,
      600,
    );
    // observations is typed as list[dict] upstream — narrow it here.
    return {
      ...raw,
      observations: (raw.observations as unknown as {
        date: string;
        value: number | null;
      }[]),
    };
  },
};
