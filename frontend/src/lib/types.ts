// Hand-written type mirrors of backend/app/schemas.py. Once the backend is
// running locally, regenerate with `npm run gen:types` to produce
// `api-types.ts` from the OpenAPI spec and switch imports to that file.

export interface UniverseRow {
  ticker: string;
  name: string;
  segment: string | null;
  last_price: number | null;
  change_1d_pct: number | null;
  change_5d_pct: number | null;
  change_30d_pct: number | null;
  rs_vs_xly: number | null;
  next_er_date: string | null;
  next_er_time: string | null;
  news_7d_count: number | null;
  news_volume_pct_baseline: number | null;
  sentiment_7d: number | null;
  social_vol_z: number | null;
  jobs_change_30d_pct: number | null;
  hypothesis_label: string | null;
  hypothesis_score: number | null;
}

export interface StatSummary {
  universe_change_1d_pct: number;
  spy_change_1d_pct: number;
  up_count: number;
  total_count: number;
  events_24h_total: number;
  events_24h_hi: number;
  events_24h_md: number;
  events_24h_lo: number;
  earnings_next_14d: number;
  next_earnings_label: string;
  signal_strength: number;
  features_active: number;
  median_r: number;
}

export interface BriefingSection {
  heading: string;
  body: string;
}

export interface BriefingOut {
  generated_at: string;
  token_count: number;
  sections: BriefingSection[];
}

export type Severity = "hi" | "md" | "lo";

export interface EventOut {
  ticker: string;
  event_type: string;
  event_at: string;
  severity: Severity;
  source: string | null;
  description: string;
  time_label: string;
}

export interface UpcomingEarnings {
  report_date: string;
  time_of_day: string | null;
  ticker: string;
  fiscal_period: string | null;
  eps_estimate: number | null;
  revenue_estimate: number | null;
  hypothesis_label: string | null;
  hypothesis_score: number | null;
}

export interface MacroRow {
  series_id: string;
  label: string;
  latest_value: number | null;
  change_90d_pct: number | null;
  change_label: string | null;
  direction: "up" | "down" | "flat";
  bar_width_pct: number;
}

export interface CompanyDetail {
  ticker: string;
  name: string;
  segment: string | null;
  market_cap_tier: string | null;
  ir_url: string | null;
  careers_url: string | null;
  ceo_name: string | null;
  signals: UniverseRow;
}

export interface BriefingResponse {
  generated_at: string;
  stats: StatSummary;
  briefing: BriefingOut;
  events: EventOut[];
  universe: UniverseRow[];
  macro: MacroRow[];
  upcoming_earnings: UpcomingEarnings[];
}
