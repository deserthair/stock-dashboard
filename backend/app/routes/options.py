from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Company, OptionsSnapshot
from ..schemas import OptionsSnapshotOut, OptionsSummary

router = APIRouter(prefix="/api/options", tags=["options"])


def _to_out(o: OptionsSnapshot, ticker: str) -> OptionsSnapshotOut:
    return OptionsSnapshotOut(
        company_id=o.company_id,
        ticker=ticker,
        obs_date=o.obs_date,
        expiry=o.expiry,
        underlying_price=o.underlying_price,
        atm_iv=o.atm_iv,
        total_call_volume=o.total_call_volume,
        total_put_volume=o.total_put_volume,
        total_call_oi=o.total_call_oi,
        total_put_oi=o.total_put_oi,
        put_call_volume_ratio=o.put_call_volume_ratio,
        put_call_oi_ratio=o.put_call_oi_ratio,
    )


@router.get("/{ticker}", response_model=OptionsSummary)
def get_options_summary(
    ticker: str,
    db: Session = Depends(get_db),
    limit: int = Query(default=60, ge=1, le=365),
) -> OptionsSummary:
    c = db.query(Company).filter(Company.ticker == ticker.upper()).one_or_none()
    if c is None:
        raise HTTPException(status_code=404, detail=f"Unknown ticker {ticker}")
    rows = (
        db.query(OptionsSnapshot)
        .filter(OptionsSnapshot.company_id == c.company_id)
        .order_by(OptionsSnapshot.obs_date.desc())
        .limit(limit)
        .all()
    )
    # Oldest-first for chart rendering
    rows_asc = list(reversed(rows))
    latest = rows_asc[-1] if rows_asc else None

    iv_trend_30d = None
    pc_trend_30d = None
    if latest is not None and len(rows_asc) >= 2:
        cutoff = latest.obs_date - timedelta(days=30)
        ref = next(
            (r for r in reversed(rows_asc) if r.obs_date <= cutoff),
            None,
        )
        if ref is not None:
            if ref.atm_iv and latest.atm_iv:
                iv_trend_30d = round((latest.atm_iv / ref.atm_iv - 1) * 100, 2)
            if ref.put_call_volume_ratio and latest.put_call_volume_ratio:
                pc_trend_30d = round(
                    (latest.put_call_volume_ratio / ref.put_call_volume_ratio - 1) * 100, 2
                )

    return OptionsSummary(
        ticker=c.ticker,
        latest=_to_out(latest, c.ticker) if latest else None,
        iv_trend_30d_pct=iv_trend_30d,
        pc_vol_trend_30d_pct=pc_trend_30d,
        history=[_to_out(r, c.ticker) for r in rows_asc],
    )
