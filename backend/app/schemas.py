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
    signals: UniverseRow


class BriefingResponse(BaseModel):
    generated_at: datetime
    stats: StatSummary
    briefing: BriefingOut
    events: list[EventOut]
    universe: list[UniverseRow]
    macro: list[MacroRow]
    upcoming_earnings: list[UpcomingEarnings]
