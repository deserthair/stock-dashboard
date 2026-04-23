from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..models import Company
from ..schemas import UniverseRow

router = APIRouter(prefix="/api/universe", tags=["universe"])


@router.get("", response_model=list[UniverseRow])
def list_universe(db: Session = Depends(get_db)) -> list[UniverseRow]:
    companies = (
        db.query(Company)
        .options(joinedload(Company.signals))
        .order_by(Company.ticker)
        .all()
    )
    out: list[UniverseRow] = []
    for c in companies:
        s = c.signals
        out.append(
            UniverseRow(
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
        )
    return out
