from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..models import Company
from ..schemas import CompanyDetail, UniverseRow

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("/{ticker}", response_model=CompanyDetail)
def get_company(ticker: str, db: Session = Depends(get_db)) -> CompanyDetail:
    c = (
        db.query(Company)
        .options(joinedload(Company.signals))
        .filter(Company.ticker == ticker.upper())
        .one_or_none()
    )
    if c is None:
        raise HTTPException(status_code=404, detail=f"Unknown ticker {ticker}")
    s = c.signals
    signals = UniverseRow(
        ticker=c.ticker,
        name=c.name,
        segment=c.segment,
        last_price=s.last_price if s else None,
        change_1d_pct=s.change_1d_pct if s else None,
        change_5d_pct=s.change_5d_pct if s else None,
        change_30d_pct=s.change_30d_pct if s else None,
        rs_vs_xly=s.rs_vs_xly if s else None,
        next_er_date=s.next_er_date if s else None,
        next_er_time=s.next_er_time if s else None,
        news_7d_count=s.news_7d_count if s else None,
        news_volume_pct_baseline=s.news_volume_pct_baseline if s else None,
        sentiment_7d=s.sentiment_7d if s else None,
        social_vol_z=s.social_vol_z if s else None,
        jobs_change_30d_pct=s.jobs_change_30d_pct if s else None,
        hypothesis_label=s.hypothesis_label if s else None,
        hypothesis_score=s.hypothesis_score if s else None,
    )
    return CompanyDetail(
        ticker=c.ticker,
        name=c.name,
        segment=c.segment,
        market_cap_tier=c.market_cap_tier,
        ir_url=c.ir_url,
        careers_url=c.careers_url,
        ceo_name=c.ceo_name,
        signals=signals,
    )
