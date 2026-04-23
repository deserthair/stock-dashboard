from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..models import Briefing, Company, Earnings, Event
from ..schemas import (
    BriefingOut,
    BriefingResponse,
    BriefingSection,
    EventOut,
    MacroRow,
    StatSummary,
    UniverseRow,
    UpcomingEarnings,
)
from . import earnings as earnings_route
from . import events as events_route
from . import macro as macro_route
from . import universe as universe_route

router = APIRouter(prefix="/api/briefing", tags=["briefing"])


@router.get("", response_model=BriefingResponse)
def get_briefing(db: Session = Depends(get_db)) -> BriefingResponse:
    # Underlying data
    universe = universe_route.list_universe(db)
    # Pass explicit Nones for the new range params — Query(default=None)
    # defaults only resolve via FastAPI's request machinery.
    events = events_route.list_events(
        db, start_date=None, end_date=None, limit=12
    )
    macro = macro_route.list_macro(db)
    upcoming = earnings_route.upcoming(db, within_days=21)

    # Briefing prose
    b = db.query(Briefing).order_by(Briefing.generated_at.desc()).first()
    if b is None:
        raise HTTPException(status_code=404, detail="No briefing available. Run seed.py.")
    briefing = BriefingOut(
        generated_at=b.generated_at,
        token_count=b.token_count,
        sections=[BriefingSection(**s) for s in b.sections],
    )

    # Derived stats
    up = [row for row in universe if (row.change_1d_pct or 0) > 0]
    universe_change = (
        sum((row.change_1d_pct or 0) for row in universe) / len(universe)
        if universe else 0.0
    )
    sev_counts = {"hi": 0, "md": 0, "lo": 0}
    for e in events:
        sev_counts[e.severity] = sev_counts.get(e.severity, 0) + 1

    # Next 3 earnings label
    next_three = upcoming[:3]
    next_label = " · ".join(
        f"{u.ticker} {u.report_date.strftime('%m/%d')}" for u in next_three
    )

    stats = StatSummary(
        universe_change_1d_pct=round(universe_change, 2),
        spy_change_1d_pct=0.21,  # Will be computed from SPY ingest once wired.
        up_count=len(up),
        total_count=len(universe),
        events_24h_total=len(events),
        events_24h_hi=sev_counts.get("hi", 0),
        events_24h_md=sev_counts.get("md", 0),
        events_24h_lo=sev_counts.get("lo", 0),
        earnings_next_14d=sum(
            1 for u in upcoming
            if (u.report_date - upcoming[0].report_date).days <= 14
        ) if upcoming else 0,
        next_earnings_label=next_label,
        signal_strength=0.64,
        features_active=4,
        median_r=0.31,
    )

    return BriefingResponse(
        generated_at=b.generated_at,
        stats=stats,
        briefing=briefing,
        events=events,
        universe=universe,
        macro=macro,
        upcoming_earnings=upcoming,
    )
