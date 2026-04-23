from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CommodityMeta, CommodityPrice
from ..schemas import (
    CommodityDetail,
    CommodityMetaOut,
    CommodityPricePoint,
    CommodityRow,
)
from ._filters import apply_date_range

router = APIRouter(prefix="/api/commodities", tags=["commodities"])


def _pct_change(rows: list[CommodityPrice], days: int) -> float | None:
    """Latest close vs close `days` ago."""
    if len(rows) < 2:
        return None
    latest = rows[-1]
    if latest.close is None or latest.close == 0:
        return None
    cutoff = latest.trade_date - timedelta(days=days)
    ref = next(
        (r.close for r in reversed(rows) if r.trade_date <= cutoff and r.close is not None),
        None,
    )
    if ref is None or ref == 0:
        return None
    return round((latest.close / ref - 1) * 100, 2)


def _to_meta(m: CommodityMeta) -> CommodityMetaOut:
    return CommodityMetaOut(
        symbol=m.symbol,
        label=m.label,
        category=m.category,
        unit=m.unit,
        exposure=list(m.exposure or []),
        source=m.source,
        series_id=m.series_id,
    )


@router.get("", response_model=list[CommodityRow])
def list_commodities(
    db: Session = Depends(get_db),
    category: str | None = Query(default=None),
) -> list[CommodityRow]:
    metas = db.query(CommodityMeta)
    if category:
        metas = metas.filter(CommodityMeta.category == category)
    out: list[CommodityRow] = []
    for m in metas.order_by(CommodityMeta.category, CommodityMeta.label).all():
        rows = (
            db.query(CommodityPrice)
            .filter(CommodityPrice.symbol == m.symbol)
            .order_by(CommodityPrice.trade_date)
            .all()
        )
        latest = rows[-1] if rows else None
        out.append(
            CommodityRow(
                meta=_to_meta(m),
                latest=latest.close if latest else None,
                latest_date=latest.trade_date if latest else None,
                change_30d_pct=_pct_change(rows, 30),
                change_90d_pct=_pct_change(rows, 90),
                change_1y_pct=_pct_change(rows, 365),
            )
        )
    return out


@router.get("/{symbol:path}", response_model=CommodityDetail)
def get_commodity(
    symbol: str,
    db: Session = Depends(get_db),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> CommodityDetail:
    m = db.get(CommodityMeta, symbol)
    if m is None:
        raise HTTPException(status_code=404, detail=f"Unknown commodity {symbol}")
    q = db.query(CommodityPrice).filter(CommodityPrice.symbol == symbol)
    q = apply_date_range(q, CommodityPrice.trade_date, start_date, end_date, is_datetime=False)
    rows = q.order_by(CommodityPrice.trade_date).all()
    latest = rows[-1] if rows else None
    return CommodityDetail(
        meta=_to_meta(m),
        observations=[
            CommodityPricePoint(trade_date=r.trade_date, close=r.close) for r in rows
        ],
        latest=latest.close if latest else None,
        latest_date=latest.trade_date if latest else None,
        change_30d_pct=_pct_change(rows, 30),
        change_90d_pct=_pct_change(rows, 90),
        change_1y_pct=_pct_change(rows, 365),
    )
