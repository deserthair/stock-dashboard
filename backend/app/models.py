from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


# ---------- company + market data ----------


class Company(Base):
    __tablename__ = "companies"

    company_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(8), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    segment: Mapped[str | None] = mapped_column(String(64))
    market_cap_tier: Mapped[str | None] = mapped_column(String(32))
    ir_url: Mapped[str | None] = mapped_column(String(256))
    careers_url: Mapped[str | None] = mapped_column(String(256))
    x_handle: Mapped[str | None] = mapped_column(String(64))
    ceo_name: Mapped[str | None] = mapped_column(String(128))
    cik: Mapped[str | None] = mapped_column(String(16))  # SEC CIK, 10-digit padded
    pr_page_url: Mapped[str | None] = mapped_column(String(256))
    is_benchmark: Mapped[bool] = mapped_column(Boolean, default=False)

    prices: Mapped[list["PriceDaily"]] = relationship(back_populates="company")
    earnings: Mapped[list["Earnings"]] = relationship(back_populates="company")
    events: Mapped[list["Event"]] = relationship(back_populates="company")
    signals: Mapped["CompanySignal"] = relationship(
        back_populates="company", uselist=False
    )


class PriceDaily(Base):
    __tablename__ = "prices_daily"

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.company_id"), primary_key=True
    )
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[float | None] = mapped_column(Float)
    high: Mapped[float | None] = mapped_column(Float)
    low: Mapped[float | None] = mapped_column(Float)
    close: Mapped[float | None] = mapped_column(Float)
    adj_close: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[int | None] = mapped_column(Integer)

    company: Mapped[Company] = relationship(back_populates="prices")


class Earnings(Base):
    __tablename__ = "earnings"

    earnings_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.company_id"))
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_period: Mapped[str | None] = mapped_column(String(16))
    time_of_day: Mapped[str | None] = mapped_column(String(4))
    eps_estimate: Mapped[float | None] = mapped_column(Float)
    eps_actual: Mapped[float | None] = mapped_column(Float)
    revenue_estimate: Mapped[float | None] = mapped_column(Float)
    revenue_actual: Mapped[float | None] = mapped_column(Float)
    eps_surprise_pct: Mapped[float | None] = mapped_column(Float)
    hypothesis_score: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (UniqueConstraint("company_id", "report_date", name="uq_earnings_co_date"),)

    company: Mapped[Company] = relationship(back_populates="earnings")


class Event(Base):
    __tablename__ = "events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.company_id"))
    ticker_label: Mapped[str] = mapped_column(String(16))
    event_type: Mapped[str] = mapped_column(String(32))
    event_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    severity: Mapped[str] = mapped_column(String(4), default="lo")
    source: Mapped[str | None] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(String(512))
    source_ref: Mapped[str | None] = mapped_column(String(256))  # FK-ish external id

    company: Mapped[Company | None] = relationship(back_populates="events")


# ---------- macro ----------


class MacroSeries(Base):
    """Metadata + latest aggregate for each FRED series (drives the macro panel)."""

    __tablename__ = "macro_series"

    series_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    label: Mapped[str] = mapped_column(String(64))
    latest_value: Mapped[float | None] = mapped_column(Float)
    latest_date: Mapped[date | None] = mapped_column(Date)
    change_90d_pct: Mapped[float | None] = mapped_column(Float)
    change_label: Mapped[str | None] = mapped_column(String(16))
    direction: Mapped[str] = mapped_column(String(4), default="flat")
    bar_width_pct: Mapped[float] = mapped_column(Float, default=0.0)


class MacroObservation(Base):
    """Full time series; one row per (series_id, date)."""

    __tablename__ = "macro_observations"

    series_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    obs_date: Mapped[date] = mapped_column(Date, primary_key=True)
    value: Mapped[float | None] = mapped_column(Float)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------- news + social + emails ----------


class NewsItem(Base):
    __tablename__ = "news"

    news_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.company_id"))
    source: Mapped[str] = mapped_column(String(32))  # google_rss / pr_page / email_alert
    url: Mapped[str] = mapped_column(String(512))
    url_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    headline: Mapped[str] = mapped_column(String(512))
    body: Mapped[str | None] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(String(128))
    sentiment_score: Mapped[float | None] = mapped_column(Float)
    sentiment_confidence: Mapped[float | None] = mapped_column(Float)
    relevance_score: Mapped[float | None] = mapped_column(Float)
    topics: Mapped[list] = mapped_column(JSON, default=list)


class RedditPost(Base):
    __tablename__ = "reddit_posts"

    post_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    subreddit: Mapped[str] = mapped_column(String(64))
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.company_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    title: Mapped[str] = mapped_column(String(512))
    body: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(512))
    score: Mapped[int] = mapped_column(Integer, default=0)
    num_comments: Mapped[int] = mapped_column(Integer, default=0)
    ticker_mentions: Mapped[list] = mapped_column(JSON, default=list)
    sentiment_score: Mapped[float | None] = mapped_column(Float)


class SocialPost(Base):
    __tablename__ = "social_posts"

    post_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.company_id"))
    platform: Mapped[str] = mapped_column(String(16))  # reddit / x / ig / linkedin
    account: Mapped[str | None] = mapped_column(String(128))
    external_id: Mapped[str | None] = mapped_column(String(64), index=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    content: Mapped[str] = mapped_column(Text)
    engagement: Mapped[dict] = mapped_column(JSON, default=dict)
    sentiment_score: Mapped[float | None] = mapped_column(Float)
    is_company_official: Mapped[bool] = mapped_column(Boolean, default=False)


class EmailMessage(Base):
    __tablename__ = "email_messages"

    message_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    from_addr: Mapped[str | None] = mapped_column(String(256))
    subject: Mapped[str | None] = mapped_column(String(512))
    received_at: Mapped[datetime] = mapped_column(DateTime)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    body_text: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str | None] = mapped_column(String(32))  # google_alert / sa / x / reddit_digest / ir
    ticker_mentions: Mapped[list] = mapped_column(JSON, default=list)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)


# ---------- filings + jobs + weather ----------


class Filing(Base):
    __tablename__ = "filings"

    filing_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.company_id"))
    filing_type: Mapped[str] = mapped_column(String(16))  # 10-K / 10-Q / 8-K / DEF 14A
    accession_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    filed_at: Mapped[datetime] = mapped_column(DateTime)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    primary_doc_url: Mapped[str | None] = mapped_column(String(512))
    item_numbers: Mapped[list] = mapped_column(JSON, default=list)  # 8-K items
    title: Mapped[str | None] = mapped_column(String(256))


class JobsSnapshot(Base):
    __tablename__ = "jobs_snapshots"

    snapshot_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.company_id"))
    snapshot_date: Mapped[date] = mapped_column(Date)
    total_count: Mapped[int | None] = mapped_column(Integer)
    corporate_count: Mapped[int | None] = mapped_column(Integer)
    by_department: Mapped[dict] = mapped_column(JSON, default=dict)
    by_location: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("company_id", "snapshot_date", name="uq_jobs_co_date"),
    )


class WeatherObservation(Base):
    __tablename__ = "weather_observations"

    station_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    obs_date: Mapped[date] = mapped_column(Date, primary_key=True)
    tavg_f: Mapped[float | None] = mapped_column(Float)
    tmax_f: Mapped[float | None] = mapped_column(Float)
    tmin_f: Mapped[float | None] = mapped_column(Float)
    prcp_in: Mapped[float | None] = mapped_column(Float)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TrendsQuery(Base):
    """Metadata for a Google Trends search term we track."""

    __tablename__ = "trends_queries"

    query_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(32))   # company / menu / macro / segment
    ticker: Mapped[str | None] = mapped_column(String(8))
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime)


class TrendsObservation(Base):
    """One data point per (query, week).

    Google Trends normalizes interest to [0, 100] within the window of the
    request, so absolute values are only meaningful within a single series.
    We store `ratio_to_mean` so queries become comparable after the fact."""

    __tablename__ = "trends_observations"

    query_id: Mapped[int] = mapped_column(
        ForeignKey("trends_queries.query_id"), primary_key=True
    )
    obs_date: Mapped[date] = mapped_column(Date, primary_key=True)
    value: Mapped[float | None] = mapped_column(Float)
    ratio_to_mean: Mapped[float | None] = mapped_column(Float)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CommodityMeta(Base):
    """Metadata for a tracked food/energy commodity."""

    __tablename__ = "commodity_meta"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    label: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(32))   # protein / grain / dairy / soft / energy
    unit: Mapped[str | None] = mapped_column(String(16))
    exposure: Mapped[list] = mapped_column(JSON, default=list)  # tickers most exposed
    source: Mapped[str] = mapped_column(String(16), default="yfinance")
    series_id: Mapped[str | None] = mapped_column(String(32))  # when source='fred'


class CommodityPrice(Base):
    """Daily close for a tracked commodity (futures settle or FRED series)."""

    __tablename__ = "commodity_prices"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    close: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[int | None] = mapped_column(Integer)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OptionsSnapshot(Base):
    """Daily aggregated options snapshot per underlying.

    Captures front-expiry ATM IV, total call/put volume and open interest,
    and put/call ratios. One row per (company, obs_date)."""

    __tablename__ = "options_snapshots"

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.company_id"), primary_key=True
    )
    obs_date: Mapped[date] = mapped_column(Date, primary_key=True)
    expiry: Mapped[date | None] = mapped_column(Date)
    underlying_price: Mapped[float | None] = mapped_column(Float)
    atm_iv: Mapped[float | None] = mapped_column(Float)
    total_call_volume: Mapped[int | None] = mapped_column(Integer)
    total_put_volume: Mapped[int | None] = mapped_column(Integer)
    total_call_oi: Mapped[int | None] = mapped_column(Integer)
    total_put_oi: Mapped[int | None] = mapped_column(Integer)
    put_call_volume_ratio: Mapped[float | None] = mapped_column(Float)
    put_call_oi_ratio: Mapped[float | None] = mapped_column(Float)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Fundamental(Base):
    """Quarterly financial statement line items per company.

    One row per (company, fiscal_period_end). Source of truth for the
    quality metrics (ROIC, growth rates, dividend yield) rendered on
    the Company page Financials tab."""

    __tablename__ = "fundamentals"

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.company_id"), primary_key=True
    )
    period_end: Mapped[date] = mapped_column(Date, primary_key=True)
    fiscal_period: Mapped[str | None] = mapped_column(String(16))

    # Income statement
    revenue: Mapped[float | None] = mapped_column(Float)
    gross_profit: Mapped[float | None] = mapped_column(Float)
    operating_income: Mapped[float | None] = mapped_column(Float)
    net_income: Mapped[float | None] = mapped_column(Float)
    eps_diluted: Mapped[float | None] = mapped_column(Float)
    shares_diluted: Mapped[float | None] = mapped_column(Float)

    # Balance sheet
    total_assets: Mapped[float | None] = mapped_column(Float)
    total_debt: Mapped[float | None] = mapped_column(Float)
    total_equity: Mapped[float | None] = mapped_column(Float)

    # Cash flow
    operating_cash_flow: Mapped[float | None] = mapped_column(Float)
    capex: Mapped[float | None] = mapped_column(Float)
    free_cash_flow: Mapped[float | None] = mapped_column(Float)

    # Shareholder return
    dividends_paid: Mapped[float | None] = mapped_column(Float)
    dividends_per_share: Mapped[float | None] = mapped_column(Float)

    # Derived (precomputed at ingest)
    invested_capital: Mapped[float | None] = mapped_column(Float)
    nopat: Mapped[float | None] = mapped_column(Float)
    roic: Mapped[float | None] = mapped_column(Float)

    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source: Mapped[str] = mapped_column(String(32), default="yfinance")


# ---------- features + analytics ----------


class EarningsFeature(Base):
    __tablename__ = "features_earnings"

    feature_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    earnings_id: Mapped[int] = mapped_column(ForeignKey("earnings.earnings_id"))
    feature_version: Mapped[str] = mapped_column(String(16), default="v0")
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    return_30d: Mapped[float | None] = mapped_column(Float)
    volatility_30d: Mapped[float | None] = mapped_column(Float)
    volume_trend_30d: Mapped[float | None] = mapped_column(Float)
    rs_30d: Mapped[float | None] = mapped_column(Float)

    news_sentiment_mean_30d: Mapped[float | None] = mapped_column(Float)
    news_sentiment_trend_30d: Mapped[float | None] = mapped_column(Float)
    news_volume_30d: Mapped[int | None] = mapped_column(Integer)
    news_volume_z: Mapped[float | None] = mapped_column(Float)

    social_sentiment_mean_30d: Mapped[float | None] = mapped_column(Float)
    social_volume_30d: Mapped[int | None] = mapped_column(Integer)

    jobs_count_change_90d: Mapped[float | None] = mapped_column(Float)
    jobs_corporate_change_90d: Mapped[float | None] = mapped_column(Float)

    filings_8k_count_30d: Mapped[int | None] = mapped_column(Integer)
    filings_exec_change: Mapped[bool | None] = mapped_column(Boolean)

    beef_change_90d: Mapped[float | None] = mapped_column(Float)
    chicken_change_90d: Mapped[float | None] = mapped_column(Float)
    wheat_change_90d: Mapped[float | None] = mapped_column(Float)
    gas_change_90d: Mapped[float | None] = mapped_column(Float)
    cons_sentiment_level: Mapped[float | None] = mapped_column(Float)
    cons_sentiment_change_90d: Mapped[float | None] = mapped_column(Float)
    unemployment_change_90d: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (
        UniqueConstraint(
            "earnings_id", "feature_version", name="uq_features_earn_ver"
        ),
    )


class Correlation(Base):
    __tablename__ = "correlations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feature_name: Mapped[str] = mapped_column(String(64))
    target_name: Mapped[str] = mapped_column(String(64))
    method: Mapped[str] = mapped_column(String(16))  # pearson / spearman
    n: Mapped[int] = mapped_column(Integer)
    coefficient: Mapped[float | None] = mapped_column(Float)
    ci_low: Mapped[float | None] = mapped_column(Float)
    ci_high: Mapped[float | None] = mapped_column(Float)
    p_value: Mapped[float | None] = mapped_column(Float)
    p_adjusted: Mapped[float | None] = mapped_column(Float)
    feature_version: Mapped[str] = mapped_column(String(16), default="v0")
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------- operational ----------


class SourceRun(Base):
    """Health tracking for each ingest run."""

    __tablename__ = "source_runs"

    run_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(16), default="running")  # running / success / failed / skipped
    rows_fetched: Mapped[int] = mapped_column(Integer, default=0)
    error_msg: Mapped[str | None] = mapped_column(Text)


# ---------- denormalized signal row (drives universe matrix) ----------


class CompanySignal(Base):
    __tablename__ = "company_signals"

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.company_id"), primary_key=True
    )
    last_price: Mapped[float | None] = mapped_column(Float)
    change_1d_pct: Mapped[float | None] = mapped_column(Float)
    change_5d_pct: Mapped[float | None] = mapped_column(Float)
    change_30d_pct: Mapped[float | None] = mapped_column(Float)
    rs_vs_xly: Mapped[float | None] = mapped_column(Float)
    next_er_date: Mapped[date | None] = mapped_column(Date)
    next_er_time: Mapped[str | None] = mapped_column(String(4))
    news_7d_count: Mapped[int | None] = mapped_column(Integer)
    news_volume_pct_baseline: Mapped[float | None] = mapped_column(Float)
    sentiment_7d: Mapped[float | None] = mapped_column(Float)
    social_vol_z: Mapped[float | None] = mapped_column(Float)
    jobs_change_30d_pct: Mapped[float | None] = mapped_column(Float)
    hypothesis_label: Mapped[str | None] = mapped_column(String(16))
    hypothesis_score: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped[Company] = relationship(back_populates="signals")


class Briefing(Base):
    __tablename__ = "briefings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    sections: Mapped[list] = mapped_column(JSON)


class EarningsPostmortem(Base):
    """Narrative explanation of a past earnings event.

    One row per earnings event (keyed by earnings_id). Regenerating an
    existing row replaces the old narrative; the event's raw features and
    outcome remain on the earnings + features_earnings tables."""

    __tablename__ = "earnings_postmortems"

    earnings_id: Mapped[int] = mapped_column(
        ForeignKey("earnings.earnings_id"), primary_key=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    model: Mapped[str] = mapped_column(String(64))
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    headline: Mapped[str] = mapped_column(String(256))
    narrative: Mapped[str] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSON, default=list)
