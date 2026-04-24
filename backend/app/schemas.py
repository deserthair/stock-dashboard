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
    institution_id: int | None = None
    institution_name: str | None = None
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
    # Top per-feature contributions to the predicted eps_surprise_pct for
    # this event (sign + magnitude; only the 5 largest-|contribution| ones).
    top_drivers: list["FeatureContribution"] = []


class FeatureContribution(BaseModel):
    feature: str
    value: float
    coefficient: float
    contribution: float


class EventAttributionResponse(BaseModel):
    earnings_id: int
    ticker: str
    report_date: date
    target: str
    prediction: float
    intercept: float
    r_squared: float
    contributions: list[FeatureContribution]


class EarningsPostmortemOut(BaseModel):
    earnings_id: int
    ticker: str
    report_date: date
    fiscal_period: str | None
    generated_at: datetime
    model: str
    token_count: int
    headline: str
    narrative: str
    tags: list[str]


class TrendsQueryOut(BaseModel):
    query_id: int
    query: str
    label: str
    category: str
    ticker: str | None
    last_fetched_at: datetime | None


class TrendsObservationOut(BaseModel):
    obs_date: date
    value: float | None
    ratio_to_mean: float | None


class TrendsSeriesOut(BaseModel):
    query: TrendsQueryOut
    observations: list[TrendsObservationOut]
    latest: float | None
    change_30d_pct: float | None
    change_90d_pct: float | None


class FundamentalRow(BaseModel):
    period_end: date
    fiscal_period: str | None
    revenue: float | None
    gross_profit: float | None
    operating_income: float | None
    net_income: float | None
    eps_diluted: float | None
    total_assets: float | None
    total_debt: float | None
    total_equity: float | None
    operating_cash_flow: float | None
    capex: float | None
    free_cash_flow: float | None
    dividends_per_share: float | None
    invested_capital: float | None
    nopat: float | None
    roic: float | None


class QualityMetricsOut(BaseModel):
    revenue_ttm: float | None
    net_income_ttm: float | None
    eps_ttm: float | None
    fcf_ttm: float | None
    book_value: float | None
    dividends_per_share_ttm: float | None

    revenue_yoy_pct: float | None
    eps_yoy_pct: float | None
    equity_yoy_pct: float | None
    fcf_yoy_pct: float | None
    dividend_yoy_pct: float | None

    revenue_cagr_3y_pct: float | None
    eps_cagr_3y_pct: float | None
    equity_cagr_3y_pct: float | None
    fcf_cagr_3y_pct: float | None

    roic_latest_pct: float | None
    roic_ttm_pct: float | None
    dividend_yield_pct: float | None

    quarters_available: int
    years_of_history: float


class CompanyFundamentals(BaseModel):
    ticker: str
    last_price: float | None
    metrics: QualityMetricsOut
    quarterly: list[FundamentalRow]


# ---------- commodities ----------


class CommodityMetaOut(BaseModel):
    symbol: str
    label: str
    category: str
    unit: str | None
    exposure: list[str]
    source: str
    series_id: str | None


class CommodityRow(BaseModel):
    meta: CommodityMetaOut
    latest: float | None
    latest_date: date | None
    change_30d_pct: float | None
    change_90d_pct: float | None
    change_1y_pct: float | None


class CommodityPricePoint(BaseModel):
    trade_date: date
    close: float | None


class CommodityDetail(BaseModel):
    meta: CommodityMetaOut
    observations: list[CommodityPricePoint]
    latest: float | None
    latest_date: date | None
    change_30d_pct: float | None
    change_90d_pct: float | None
    change_1y_pct: float | None


# ---------- options ----------


class OptionsSnapshotOut(BaseModel):
    company_id: int
    ticker: str
    obs_date: date
    expiry: date | None
    underlying_price: float | None
    atm_iv: float | None
    total_call_volume: int | None
    total_put_volume: int | None
    total_call_oi: int | None
    total_put_oi: int | None
    put_call_volume_ratio: float | None
    put_call_oi_ratio: float | None


class OptionsSummary(BaseModel):
    ticker: str
    latest: OptionsSnapshotOut | None
    iv_trend_30d_pct: float | None           # % change in ATM IV
    pc_vol_trend_30d_pct: float | None       # % change in put/call ratio
    history: list[OptionsSnapshotOut]


# ---------- simulation ----------


class QuantileBandOut(BaseModel):
    day_offset: int
    obs_date: date
    p05: float
    p25: float
    p50: float
    p75: float
    p95: float


class HistogramBinOut(BaseModel):
    low: float
    high: float
    count: int


class TerminalStatsOut(BaseModel):
    expected_value: float
    p05: float
    p25: float
    p50: float
    p75: float
    p95: float
    prob_positive_return: float
    prob_down_10pct: float
    prob_up_10pct: float


class PricePathSimulationOut(BaseModel):
    ticker: str
    model: str
    start_price: float
    start_date: date
    horizon_days: int
    n_paths: int
    annual_drift_pct: float
    annual_volatility_pct: float
    fit_window_days: int
    fit_observations: int
    bands: list[QuantileBandOut]
    terminal_histogram: list[HistogramBinOut]
    terminal_stats: TerminalStatsOut
    earnings_dates_in_window: list[date]
    jump_sigma_at_earnings: float | None
    notes: list[str]


class PeerEventOut(BaseModel):
    earnings_id: int
    ticker: str
    report_date: date
    fiscal_period: str | None
    hypothesis_score: float | None
    actual_1d_return: float | None
    eps_surprise_pct: float | None


class BootstrapQuantilesOut(BaseModel):
    p05: float
    p25: float
    p50: float
    p75: float
    p95: float
    mean: float
    stdev: float


class EarningsBootstrapOut(BaseModel):
    target_ticker: str
    target_hypothesis_score: float | None
    target_fiscal_period: str | None
    method: str
    score_tolerance: float | None
    n_peers: int
    n_bootstrap: int
    peers: list[PeerEventOut]
    histogram: list[HistogramBinOut]
    quantiles: BootstrapQuantilesOut
    prob_positive_return: float
    prob_up_2pct: float
    prob_down_2pct: float
    notes: list[str]


class DCFStatsOut(BaseModel):
    mean: float
    p05: float
    p25: float
    p50: float
    p75: float
    p95: float
    stdev: float


class InstitutionOut(BaseModel):
    institution_id: int
    name: str
    kind: str
    website: str | None
    x_handle: str | None
    cik: str | None
    aum_usd: float | None


class InstitutionalHoldingRow(BaseModel):
    as_of_date: date
    institution: InstitutionOut
    ticker: str
    shares: int | None
    value_usd: float | None
    pct_of_outstanding: float | None
    shares_change: int | None
    pct_change: float | None
    source: str


class InsiderTransactionRow(BaseModel):
    txn_id: int
    ticker: str
    insider_name: str
    insider_title: str | None
    insider_is_officer: bool
    insider_is_director: bool
    transaction_date: date
    filed_at: datetime | None
    transaction_type: str
    shares: int | None
    price: float | None
    value_usd: float | None
    shares_owned_after: int | None
    is_10b5_1: bool


class InsiderNetFlow(BaseModel):
    ticker: str
    window_days: int
    net_shares: int
    net_value_usd: float
    buy_shares: int
    buy_value_usd: float
    sell_shares: int
    sell_value_usd: float
    transaction_count: int


class CompanyHoldingsOut(BaseModel):
    ticker: str
    as_of_date: date | None
    total_institutional_pct: float | None    # sum of top-N %
    total_institutions: int
    holdings: list[InstitutionalHoldingRow]
    insider_transactions_90d: list[InsiderTransactionRow]
    insider_net_flow_90d: InsiderNetFlow


class UniverseHoldingsRow(BaseModel):
    ticker: str
    name: str
    total_institutional_pct: float | None
    top_holder_name: str | None
    top_holder_pct: float | None
    biggest_buyer_name: str | None
    biggest_buyer_delta_shares: int | None
    biggest_seller_name: str | None
    biggest_seller_delta_shares: int | None
    insider_net_shares_90d: int
    insider_net_value_90d: float


class UniverseHoldingsOut(BaseModel):
    as_of_date: date | None
    rows: list[UniverseHoldingsRow]
    top_institutions: list[InstitutionOut]   # most-common across universe


class BacktestPredictionOut(BaseModel):
    model: str
    earnings_id: int
    ticker: str
    report_date: date
    hypothesis_score: float | None
    predicted: float
    predicted_p25: float | None
    predicted_p75: float | None
    predicted_p05: float | None
    predicted_p95: float | None
    actual: float
    inside_50: bool | None
    inside_90: bool | None


class BacktestModelSummaryOut(BaseModel):
    model: str
    n: int
    correlation_r: float | None
    direction_accuracy: float | None
    median_abs_error: float | None
    bias: float | None
    coverage_50: float | None
    coverage_90: float | None


class BacktestReportOut(BaseModel):
    models: list[BacktestModelSummaryOut]
    predictions: list[BacktestPredictionOut]
    n_events_evaluated: int
    n_events_candidates: int
    notes: list[str]


class DCFResultOut(BaseModel):
    ticker: str
    current_price: float | None
    n_simulations: int
    n_valid: int
    years_explicit: int
    shares_diluted: float | None

    revenue_growth_mean_pct: float
    revenue_growth_std_pct: float
    fcf_margin_mean_pct: float
    fcf_margin_std_pct: float
    wacc_mean_pct: float
    wacc_std_pct: float
    terminal_growth_pct: float

    intrinsic_value_stats: DCFStatsOut
    intrinsic_value_histogram: list[HistogramBinOut]
    prob_undervalued: float | None
    margin_of_safety_at_p50_pct: float | None

    fit_quarters: int
    notes: list[str]


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
