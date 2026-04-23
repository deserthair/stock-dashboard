from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..models import Company, Earnings
from ..schemas import UpcomingEarnings

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
