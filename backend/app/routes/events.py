from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Event
from ..schemas import EventOut

router = APIRouter(prefix="/api/events", tags=["events"])


def _time_label(event_at: datetime, now: datetime) -> str:
    if event_at.date() == now.date():
        return event_at.strftime("%H:%M")
    if event_at.date() == (now - timedelta(days=1)).date():
        return "Yd " + event_at.strftime("%H:%M")
    return event_at.strftime("%m/%d %H:%M")


@router.get("", response_model=list[EventOut])
def list_events(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=200),
) -> list[EventOut]:
    rows = db.query(Event).order_by(Event.event_at.desc()).limit(limit).all()
    now = datetime.utcnow()
    # Anchor "now" to the latest event date so demo time-labels stay relative.
    anchor = max((r.event_at for r in rows), default=now)
    return [
        EventOut(
            ticker=r.ticker_label,
            event_type=r.event_type,
            event_at=r.event_at,
            severity=r.severity,
            source=r.source,
            description=r.description,
            time_label=_time_label(r.event_at, anchor),
        )
        for r in rows
    ]
