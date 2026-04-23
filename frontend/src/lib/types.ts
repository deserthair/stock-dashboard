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

export interface NewsItemOut {
  news_id: number;
  ticker: string | null;
  source: string;
  url: string;
  published_at: string | null;
  fetched_at: string;
  headline: string;
  publisher: string | null;
  sentiment_score: number | null;
  relevance_score: number | null;
  topics: string[];
}

export interface SocialPostOut {
  post_id: number;
  ticker: string | null;
  platform: string;
  account: string | null;
  posted_at: string | null;
  content: string;
  engagement: Record<string, number | string>;
  sentiment_score: number | null;
}

export interface RedditPostOut {
  post_id: string;
  ticker: string | null;
  subreddit: string;
  created_at: string;
  title: string;
  score: number;
  num_comments: number;
  url: string | null;
  sentiment_score: number | null;
}

export interface FilingOut {
  filing_id: number;
  ticker: string;
  filing_type: string;
  filed_at: string;
  primary_doc_url: string | null;
  item_numbers: string[];
  title: string | null;
}

export interface JobsSnapshotOut {
  snapshot_date: string;
  ticker: string;
  total_count: number | null;
  corporate_count: number | null;
  by_department: Record<string, number>;
  by_location: Record<string, number>;
}

export interface CorrelationOut {
  feature_name: string;
  target_name: string;
  method: string;
  n: number;
  coefficient: number | null;
  ci_low: number | null;
  ci_high: number | null;
  p_value: number | null;
  p_adjusted: number | null;
}

export interface SourceRunOut {
  source_name: string;
  started_at: string;
  ended_at: string | null;
  status: string;
  rows_fetched: number;
  error_msg: string | null;
}

export interface PriceBar {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
}

export interface ChartMarker {
  date: string;
  severity: "hi" | "md" | "lo";
  source: string | null;
  description: string;
  event_type: string;
}

export interface CompanyPriceHistory {
  ticker: string;
  bars: PriceBar[];
  markers: ChartMarker[];
}

export interface EarningsRow {
  earnings_id: number;
  ticker: string;
  name: string | null;
  report_date: string;
  fiscal_period: string | null;
  time_of_day: string | null;
  eps_estimate: number | null;
  eps_actual: number | null;
  revenue_estimate: number | null;
  revenue_actual: number | null;
  eps_beat: boolean | null;
  eps_surprise_pct: number | null;
  post_earnings_1d_return: number | null;
  post_earnings_5d_return: number | null;
  reaction: string | null;
  hypothesis_score: number | null;
  hypothesis_label: string | null;
}

export interface HypothesisTrackerRow {
  ticker: string;
  report_date: string;
  fiscal_period: string | null;
  hypothesis_score: number | null;
  hypothesis_label: string | null;
  actual: string | null;
  reaction: string | null;
  eps_surprise_pct: number | null;
  post_earnings_1d_return: number | null;
  prediction_correct: boolean | null;
}

export interface HypothesisTrackerSummary {
  total: number;
  scored: number;
  correct: number;
  accuracy_pct: number | null;
  rows: HypothesisTrackerRow[];
}

export interface MacroObservation {
  date: string;
  value: number | null;
}

export interface MacroSeriesDetail {
  series_id: string;
  label: string;
  latest_value: number | null;
  latest_date: string | null;
  change_90d_pct: number | null;
  direction: "up" | "down" | "flat";
  observations: MacroObservation[];
}
