from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import MacroSeries
from ..schemas import MacroRow

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
