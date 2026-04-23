from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ticker: str
    name: str
    segment: str | None = None


class UniverseRow(BaseModel):
    ticker: str
    name: str
    segment: str | None = None
    last_price: float | None = None
    change_1d_pct: float | None = None
    change_5d_pct: float | None = None
    change_30d_pct: float | None = None
    rs_vs_xly: float | None = None
    next_er_date: date | None = None
    next_er_time: str | None = None
    news_7d_count: int | None = None
    news_volume_pct_baseline: float | None = None
    sentiment_7d: float | None = None
    social_vol_z: float | None = None
    jobs_change_30d_pct: float | None = None
    hypothesis_label: str | None = None
    hypothesis_score: float | None = None


class StatSummary(BaseModel):
    universe_change_1d_pct: float
    spy_change_1d_pct: float
    up_count: int
    total_count: int
    events_24h_total: int
    events_24h_hi: int
    events_24h_md: int
    events_24h_lo: int
    earnings_next_14d: int
    next_earnings_label: str
    signal_strength: float
    features_active: int
    median_r: float


class BriefingSection(BaseModel):
    heading: str
    body: str


class BriefingOut(BaseModel):
    generated_at: datetime
    token_count: int
    sections: list[BriefingSection]


class EventOut(BaseModel):
    ticker: str
    event_type: str
    event_at: datetime
    severity: str
    source: str | None = None
    description: str
    time_label: str


class UpcomingEarnings(BaseModel):
    report_date: date
    time_of_day: str | None
    ticker: str
    fiscal_period: str | None
    eps_estimate: float | None
    revenue_estimate: float | None
    hypothesis_label: str | None
    hypothesis_score: float | None


class MacroRow(BaseModel):
    series_id: str
    label: str
    latest_value: float | None
    change_90d_pct: float | None
    change_label: str | None
    direction: str
    bar_width_pct: float


class CompanyDetail(BaseModel):
    ticker: str
    name: str
    segment: str | None
    market_cap_tier: str | None
    ir_url: str | None
    careers_url: str | None
    ceo_name: str | None
    cik: str | None
    signals: UniverseRow


class BriefingResponse(BaseModel):
    generated_at: datetime
    stats: StatSummary
    briefing: BriefingOut
    events: list[EventOut]
    universe: list[UniverseRow]
    macro: list[MacroRow]
    upcoming_earnings: list[UpcomingEarnings]


# ---------- new ----------


class NewsItemOut(BaseModel):
    news_id: int
    ticker: str | None
    source: str
    url: str
    published_at: datetime | None
    fetched_at: datetime
    headline: str
    publisher: str | None
    sentiment_score: float | None
    relevance_score: float | None
    topics: list[str]


class SocialPostOut(BaseModel):
    post_id: int
    ticker: str | None
    platform: str
    account: str | None
    posted_at: datetime | None
    content: str
    engagement: dict
    sentiment_score: float | None


class RedditPostOut(BaseModel):
    post_id: str
    ticker: str | None
    subreddit: str
    created_at: datetime
    title: str
    score: int
    num_comments: int
    url: str | None
    sentiment_score: float | None


class FilingOut(BaseModel):
    filing_id: int
    ticker: str
    filing_type: str
    filed_at: datetime
    primary_doc_url: str | None
    item_numbers: list[str]
    title: str | None


class JobsSnapshotOut(BaseModel):
    snapshot_date: date
    ticker: str
    total_count: int | None
    corporate_count: int | None
    by_department: dict
    by_location: dict


class CorrelationOut(BaseModel):
    feature_name: str
    target_name: str
    method: str
    n: int
    coefficient: float | None
    ci_low: float | None
    ci_high: float | None
    p_value: float | None
    p_adjusted: float | None


class FeatureVectorOut(BaseModel):
    earnings_id: int
    ticker: str
    report_date: date
    feature_version: str
    values: dict  # {feature_name: value}


class SourceRunOut(BaseModel):
    source_name: str
    started_at: datetime
    ended_at: datetime | None
    status: str
    rows_fetched: int
    error_msg: str | None


class PriceBar(BaseModel):
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: int | None


class ChartMarker(BaseModel):
    date: date
    severity: str
    source: str | None
    description: str
    event_type: str


class CompanyPriceHistory(BaseModel):
    ticker: str
    bars: list[PriceBar]
    markers: list[ChartMarker]


class EarningsRow(BaseModel):
    earnings_id: int
    ticker: str
    name: str | None
    report_date: date
    fiscal_period: str | None
    time_of_day: str | None
    eps_estimate: float | None
    eps_actual: float | None
    revenue_estimate: float | None
    revenue_actual: float | None
    eps_beat: bool | None
    eps_surprise_pct: float | None
    post_earnings_1d_return: float | None
    post_earnings_5d_return: float | None
    reaction: str | None
    hypothesis_score: float | None
    hypothesis_label: str | None


class HypothesisTrackerRow(BaseModel):
    ticker: str
    report_date: date
    fiscal_period: str | None
    hypothesis_score: float | None
    hypothesis_label: str | None
    actual: str | None             # BEAT / MISS based on eps_actual vs estimate
    reaction: str | None            # beat_rally / beat_sell / miss_rally / miss_sell
    eps_surprise_pct: float | None
    post_earnings_1d_return: float | None
    prediction_correct: bool | None


class HypothesisTrackerSummary(BaseModel):
    total: int
    scored: int
    correct: int
    accuracy_pct: float | None
    rows: list[HypothesisTrackerRow]


class MacroSeriesDetail(BaseModel):
    series_id: str
    label: str
    latest_value: float | None
    latest_date: date | None
    change_90d_pct: float | None
    direction: str
    observations: list[dict]        # {date, value}


# ---------- exploratory analysis ----------


class ScatterPointOut(BaseModel):
    ticker: str
    earnings_id: int
    report_date: str
    x: float
    y: float


class RegressionLineOut(BaseModel):
    slope: float
    intercept: float
    r_squared: float
    n: int
    x_min: float
    x_max: float
    pearson_r: float | None
    pearson_p: float | None
    spearman_r: float | None
    spearman_p: float | None
    ci_low_at_min: float | None
    ci_high_at_min: float | None
    ci_low_at_max: float | None
    ci_high_at_max: float | None


class ScatterResponse(BaseModel):
    feature: str
    target: str
    points: list[ScatterPointOut]
    line: RegressionLineOut | None


class HeatmapResponse(BaseModel):
    method: str
    features: list[str]
    matrix: list[list[float | None]]
    sample_sizes: list[list[int]]


class CoefficientOut(BaseModel):
    feature: str
    value: float
    abs_value: float


class RegressionFitOut(BaseModel):
    method: str
    target: str
    n: int
    features_used: list[str]
    intercept: float
    r_squared: float
    r_squared_loo: float | None
    rmse: float
    coefficients: list[CoefficientOut]
    note: str | None


class AnalysisAxesResponse(BaseModel):
    features: list[str]
    targets: list[str]
