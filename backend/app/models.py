from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


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
    time_of_day: Mapped[str | None] = mapped_column(String(4))  # BMO / AMC
    eps_estimate: Mapped[float | None] = mapped_column(Float)
    eps_actual: Mapped[float | None] = mapped_column(Float)
    revenue_estimate: Mapped[float | None] = mapped_column(Float)
    revenue_actual: Mapped[float | None] = mapped_column(Float)
    eps_surprise_pct: Mapped[float | None] = mapped_column(Float)
    hypothesis_score: Mapped[float | None] = mapped_column(Float)

    company: Mapped[Company] = relationship(back_populates="earnings")


class Event(Base):
    __tablename__ = "events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.company_id"))
    ticker_label: Mapped[str] = mapped_column(String(16))
    event_type: Mapped[str] = mapped_column(String(32))
    event_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    severity: Mapped[str] = mapped_column(String(4), default="lo")  # hi / md / lo
    source: Mapped[str | None] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(String(512))

    company: Mapped[Company | None] = relationship(back_populates="events")


class MacroSeries(Base):
    __tablename__ = "macro_series"

    series_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    label: Mapped[str] = mapped_column(String(64))
    latest_value: Mapped[float | None] = mapped_column(Float)
    change_90d_pct: Mapped[float | None] = mapped_column(Float)
    change_label: Mapped[str | None] = mapped_column(String(16))
    direction: Mapped[str] = mapped_column(String(4), default="flat")  # up / down / flat
    bar_width_pct: Mapped[float] = mapped_column(Float, default=0.0)


class CompanySignal(Base):
    """Denormalized per-company row that powers the universe matrix."""

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

    company: Mapped[Company] = relationship(back_populates="signals")


class Briefing(Base):
    __tablename__ = "briefings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    sections: Mapped[list] = mapped_column(JSON)  # list of {heading, body}
