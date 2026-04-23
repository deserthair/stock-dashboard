"""Compute earnings outcomes: beat/miss + post-earnings 1D/5D returns.

For every past earnings event with both estimate + actual values recorded,
computes the reaction classification:
  beat_rally  — EPS beat & stock up 1D
  beat_sell   — EPS beat & stock down 1D
  miss_rally  — EPS miss & stock up 1D
  miss_sell   — EPS miss & stock down 1D

Returns are computed from close(T-1) vs close(T+1) or close(T+5). Stores
nothing directly; callers either serialize on the fly or persist via the
existing earnings row.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Earnings, PriceDaily


@dataclass
class EarningsOutcome:
    earnings_id: int
    report_date: date
    eps_estimate: float | None
    eps_actual: float | None
    revenue_estimate: float | None
    revenue_actual: float | None
    eps_beat: bool | None
    revenue_beat: bool | None
    eps_surprise_pct: float | None
    post_earnings_1d_return: float | None
    post_earnings_5d_return: float | None
    reaction: str | None


def _price_at(s: Session, company_id: int, d: date) -> float | None:
    # Grab the first close >= d (handles weekends / holidays).
    row = (
        s.query(PriceDaily)
        .filter(PriceDaily.company_id == company_id, PriceDaily.trade_date >= d)
        .order_by(PriceDaily.trade_date)
        .first()
    )
    return float(row.close) if row and row.close else None


def _price_before(s: Session, company_id: int, d: date) -> float | None:
    row = (
        s.query(PriceDaily)
        .filter(PriceDaily.company_id == company_id, PriceDaily.trade_date <= d)
        .order_by(PriceDaily.trade_date.desc())
        .first()
    )
    return float(row.close) if row and row.close else None


def compute(s: Session, e: Earnings) -> EarningsOutcome:
    eps_beat: bool | None = None
    revenue_beat: bool | None = None
    if e.eps_actual is not None and e.eps_estimate is not None:
        eps_beat = e.eps_actual > e.eps_estimate
    if e.revenue_actual is not None and e.revenue_estimate is not None:
        revenue_beat = e.revenue_actual > e.revenue_estimate

    report = e.report_date
    pre = _price_before(s, e.company_id, report - timedelta(days=1))
    post_1d = _price_at(s, e.company_id, report + timedelta(days=1))
    post_5d = _price_at(s, e.company_id, report + timedelta(days=5))

    r_1d = (
        round((post_1d / pre - 1.0) * 100, 2)
        if pre and post_1d
        else None
    )
    r_5d = (
        round((post_5d / pre - 1.0) * 100, 2)
        if pre and post_5d
        else None
    )

    reaction = None
    if eps_beat is not None and r_1d is not None:
        reaction = (
            "beat_rally" if eps_beat and r_1d > 0
            else "beat_sell" if eps_beat and r_1d <= 0
            else "miss_rally" if not eps_beat and r_1d > 0
            else "miss_sell"
        )

    return EarningsOutcome(
        earnings_id=e.earnings_id,
        report_date=e.report_date,
        eps_estimate=e.eps_estimate,
        eps_actual=e.eps_actual,
        revenue_estimate=e.revenue_estimate,
        revenue_actual=e.revenue_actual,
        eps_beat=eps_beat,
        revenue_beat=revenue_beat,
        eps_surprise_pct=e.eps_surprise_pct,
        post_earnings_1d_return=r_1d,
        post_earnings_5d_return=r_5d,
        reaction=reaction,
    )


def compute_for_company(s: Session, company_id: int) -> list[EarningsOutcome]:
    earnings = (
        s.query(Earnings)
        .filter(Earnings.company_id == company_id)
        .order_by(Earnings.report_date.desc())
        .all()
    )
    return [compute(s, e) for e in earnings]


def compute_all(s: Session) -> list[EarningsOutcome]:
    return [compute(s, e) for e in s.query(Earnings).order_by(Earnings.report_date.desc()).all()]
