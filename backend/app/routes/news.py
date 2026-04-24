from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Company, Institution, InstitutionalHolding, NewsItem
from ..schemas import NewsItemOut
from ._filters import apply_date_range

router = APIRouter(prefix="/api/news", tags=["news"])


def _serialize(
    n: NewsItem,
    ticker_by_company_id: dict[int, str],
    name_by_inst_id: dict[int, str],
) -> NewsItemOut:
    return NewsItemOut(
        news_id=n.news_id,
        ticker=ticker_by_company_id.get(n.company_id) if n.company_id is not None else None,
        institution_id=n.institution_id,
        institution_name=name_by_inst_id.get(n.institution_id) if n.institution_id is not None else None,
        source=n.source,
        url=n.url,
        published_at=n.published_at,
        fetched_at=n.fetched_at,
        headline=n.headline,
        publisher=n.publisher,
        sentiment_score=n.sentiment_score,
        relevance_score=n.relevance_score,
        topics=list(n.topics or []),
    )


@router.get("", response_model=list[NewsItemOut])
def list_news(
    db: Session = Depends(get_db),
    ticker: str | None = None,
    institution: str | None = Query(
        default=None,
        description="Filter by institution name (exact match).",
    ),
    institution_id: int | None = Query(default=None),
    holders_of: str | None = Query(
        default=None,
        description=(
            "Ticker whose top institutional holders we want news for. "
            "Returns news items tagged with any of those institutions."
        ),
    ),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[NewsItemOut]:
    q = db.query(NewsItem)

    if ticker:
        c = db.query(Company).filter(Company.ticker == ticker.upper()).one_or_none()
        if c is None:
            raise HTTPException(status_code=404, detail=f"Unknown ticker {ticker}")
        q = q.filter(NewsItem.company_id == c.company_id)

    if institution_id is not None:
        q = q.filter(NewsItem.institution_id == institution_id)
    elif institution is not None:
        inst = db.query(Institution).filter(Institution.name == institution).one_or_none()
        if inst is None:
            raise HTTPException(status_code=404, detail=f"Unknown institution {institution!r}")
        q = q.filter(NewsItem.institution_id == inst.institution_id)
    elif holders_of is not None:
        c = db.query(Company).filter(Company.ticker == holders_of.upper()).one_or_none()
        if c is None:
            raise HTTPException(status_code=404, detail=f"Unknown ticker {holders_of}")
        inst_ids = [
            row.institution_id
            for row in db.query(InstitutionalHolding.institution_id)
            .filter(InstitutionalHolding.company_id == c.company_id)
            .distinct()
            .all()
        ]
        if not inst_ids:
            return []
        q = q.filter(NewsItem.institution_id.in_(inst_ids))

    q = apply_date_range(q, NewsItem.fetched_at, start_date, end_date, is_datetime=True)
    rows = q.order_by(NewsItem.fetched_at.desc()).limit(limit).all()

    # Bulk-resolve company tickers + institution names for serialization
    company_ids = {n.company_id for n in rows if n.company_id is not None}
    inst_ids = {n.institution_id for n in rows if n.institution_id is not None}
    ticker_by_company_id: dict[int, str] = {}
    if company_ids:
        for cid, t in db.query(Company.company_id, Company.ticker).filter(
            Company.company_id.in_(company_ids)
        ):
            ticker_by_company_id[cid] = t
    name_by_inst_id: dict[int, str] = {}
    if inst_ids:
        for iid, n in db.query(Institution.institution_id, Institution.name).filter(
            Institution.institution_id.in_(inst_ids)
        ):
            name_by_inst_id[iid] = n

    return [_serialize(n, ticker_by_company_id, name_by_inst_id) for n in rows]
