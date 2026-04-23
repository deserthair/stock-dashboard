from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import TrendsObservation, TrendsQuery
from ..schemas import TrendsObservationOut, TrendsQueryOut, TrendsSeriesOut
from ._filters import apply_date_range

router = APIRouter(prefix="/api/trends", tags=["trends"])


def _compute_change(obs: list[TrendsObservation], days: int) -> float | None:
    """Percent change in Trends index from `days` ago to the latest point."""
    if len(obs) < 2:
        return None
    latest = obs[-1]
    if latest.value is None or latest.value == 0:
        return None
    cutoff = latest.obs_date - timedelta(days=days)
    ref = next(
        (o.value for o in reversed(obs) if o.obs_date <= cutoff and o.value is not None),
        None,
    )
    if ref is None or ref == 0:
        return None
    return round((latest.value / ref - 1) * 100, 1)


@router.get("", response_model=list[TrendsQueryOut])
def list_queries(
    db: Session = Depends(get_db),
    category: str | None = Query(default=None),
    ticker: str | None = Query(default=None),
) -> list[TrendsQueryOut]:
    q = db.query(TrendsQuery)
    if category:
        q = q.filter(TrendsQuery.category == category)
    if ticker:
        q = q.filter(TrendsQuery.ticker == ticker.upper())
    rows = q.order_by(TrendsQuery.category, TrendsQuery.query).all()
    return [
        TrendsQueryOut(
            query_id=r.query_id,
            query=r.query,
            label=r.label,
            category=r.category,
            ticker=r.ticker,
            last_fetched_at=r.last_fetched_at,
        )
        for r in rows
    ]


@router.get("/{query_id}", response_model=TrendsSeriesOut)
def get_series(
    query_id: int,
    db: Session = Depends(get_db),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> TrendsSeriesOut:
    q = db.get(TrendsQuery, query_id)
    if q is None:
        raise HTTPException(status_code=404, detail=f"Unknown query_id {query_id}")
    obs_q = db.query(TrendsObservation).filter(TrendsObservation.query_id == query_id)
    obs_q = apply_date_range(
        obs_q, TrendsObservation.obs_date, start_date, end_date, is_datetime=False
    )
    obs = obs_q.order_by(TrendsObservation.obs_date).all()

    latest = obs[-1].value if obs else None
    return TrendsSeriesOut(
        query=TrendsQueryOut(
            query_id=q.query_id,
            query=q.query,
            label=q.label,
            category=q.category,
            ticker=q.ticker,
            last_fetched_at=q.last_fetched_at,
        ),
        observations=[
            TrendsObservationOut(
                obs_date=o.obs_date,
                value=o.value,
                ratio_to_mean=o.ratio_to_mean,
            )
            for o in obs
        ],
        latest=latest,
        change_30d_pct=_compute_change(obs, 30),
        change_90d_pct=_compute_change(obs, 90),
    )
