from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from analysis.outcomes import compute as compute_outcome

from ..db import get_db
from ..models import Company, CompanySignal, Earnings
from ..schemas import EarningsRow, UpcomingEarnings
from ._filters import apply_date_range

router = APIRouter(prefix="/api/earnings", tags=["earnings"])


@router.get("/upcoming", response_model=list[UpcomingEarnings])
def upcoming(
    db: Session = Depends(get_db),
    within_days: int = Query(default=21, ge=1, le=180),
) -> list[UpcomingEarnings]:
    # Use the latest report_date in the DB as "today" so demo data stays visible
    # when the real-world date drifts past the seeded window.
    latest = db.query(Earnings).order_by(Earnings.report_date.desc()).first()
    if latest is None:
        return []
    anchor = min(latest.report_date, date.today())
    rows = (
        db.query(Earnings)
        .options(joinedload(Earnings.company))
        .filter(
            Earnings.report_date >= anchor,
            Earnings.report_date <= anchor + timedelta(days=within_days * 4),
        )
        .order_by(Earnings.report_date)
        .all()
    )
    out: list[UpcomingEarnings] = []
    for r in rows:
        out.append(
            UpcomingEarnings(
                report_date=r.report_date,
                time_of_day=r.time_of_day,
                ticker=r.company.ticker if r.company else "?",
                fiscal_period=r.fiscal_period,
                eps_estimate=r.eps_estimate,
                revenue_estimate=r.revenue_estimate,
                hypothesis_label=(
                    "BEAT" if (r.hypothesis_score or 0) > 0.2
                    else "MISS" if (r.hypothesis_score or 0) < -0.2
                    else "MIXED" if r.hypothesis_score is not None
                    else None
                ),
                hypothesis_score=r.hypothesis_score,
            )
        )
    return out


def _revenue_label(value: float | None) -> str:
    if value is None:
        return "—"
    if value >= 1e9:
        return f"{value / 1e9:.2f}B"
    if value >= 1e6:
        return f"{value / 1e6:.0f}M"
    return f"{value:,.0f}"


@router.get("", response_model=list[EarningsRow])
def list_earnings(
    db: Session = Depends(get_db),
    ticker: str | None = None,
    past_only: bool = False,
    upcoming_only: bool = False,
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
) -> list[EarningsRow]:
    """Calendar view: one row per earnings event with outcome if available."""
    q = (
        db.query(Earnings, Company)
        .join(Company, Company.company_id == Earnings.company_id)
    )
    if ticker:
        q = q.filter(Company.ticker == ticker.upper())
    if past_only:
        q = q.filter(Earnings.report_date <= date.today())
    if upcoming_only:
        q = q.filter(Earnings.report_date >= date.today())
    q = apply_date_range(q, Earnings.report_date, start_date, end_date, is_datetime=False)
    rows = q.order_by(Earnings.report_date.desc()).limit(limit).all()

    # Pull company_signals for hypothesis context on upcoming rows.
    sig_by_id = {
        s.company_id: s for s in db.query(CompanySignal).all()
    }

    out: list[EarningsRow] = []
    for e, company in rows:
        oc = compute_outcome(db, e)
        sig = sig_by_id.get(e.company_id)
        out.append(
            EarningsRow(
                earnings_id=e.earnings_id,
                ticker=company.ticker,
                name=company.name,
                report_date=e.report_date,
                fiscal_period=e.fiscal_period,
                time_of_day=e.time_of_day,
                eps_estimate=e.eps_estimate,
                eps_actual=e.eps_actual,
                revenue_estimate=e.revenue_estimate,
                revenue_actual=e.revenue_actual,
                eps_beat=oc.eps_beat,
                eps_surprise_pct=oc.eps_surprise_pct,
                post_earnings_1d_return=oc.post_earnings_1d_return,
                post_earnings_5d_return=oc.post_earnings_5d_return,
                reaction=oc.reaction,
                hypothesis_score=(
                    e.hypothesis_score
                    if e.hypothesis_score is not None
                    else (sig.hypothesis_score if sig else None)
                ),
                hypothesis_label=sig.hypothesis_label if sig else None,
            )
        )
    return out
