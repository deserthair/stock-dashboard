from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import MacroObservation, MacroSeries
from ..schemas import MacroRow, MacroSeriesDetail

router = APIRouter(prefix="/api/macro", tags=["macro"])


@router.get("", response_model=list[MacroRow])
def list_macro(db: Session = Depends(get_db)) -> list[MacroRow]:
    rows = db.query(MacroSeries).order_by(MacroSeries.series_id).all()
    # Preserve insertion order for the feature-bar panel.
    order = [
        "PBEEFUSDM", "WPU0211", "PWHEAMTUSDM", "GASREGW",
        "UMCSENT", "CES7072200003", "UNRATE", "DGS10",
    ]
    by_id = {r.series_id: r for r in rows}
    ordered = [by_id[k] for k in order if k in by_id] + [
        r for r in rows if r.series_id not in order
    ]
    return [
        MacroRow(
            series_id=r.series_id,
            label=r.label,
            latest_value=r.latest_value,
            change_90d_pct=r.change_90d_pct,
            change_label=r.change_label,
            direction=r.direction,
            bar_width_pct=r.bar_width_pct,
        )
        for r in ordered
    ]


@router.get("/{series_id}", response_model=MacroSeriesDetail)
def get_macro_series(
    series_id: str,
    db: Session = Depends(get_db),
    days: int = Query(default=365, ge=30, le=3650),
) -> MacroSeriesDetail:
    meta = db.get(MacroSeries, series_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Unknown series {series_id}")
    cutoff = date.today() - timedelta(days=days)
    obs = (
        db.query(MacroObservation)
        .filter(
            MacroObservation.series_id == series_id,
            MacroObservation.obs_date >= cutoff,
        )
        .order_by(MacroObservation.obs_date)
        .all()
    )
    return MacroSeriesDetail(
        series_id=meta.series_id,
        label=meta.label,
        latest_value=meta.latest_value,
        latest_date=meta.latest_date,
        change_90d_pct=meta.change_90d_pct,
        direction=meta.direction,
        observations=[
            {"date": o.obs_date.isoformat(), "value": float(o.value) if o.value is not None else None}
            for o in obs
        ],
    )
